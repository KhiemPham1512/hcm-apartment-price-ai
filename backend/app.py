"""Read-only inference API. By default no market model is loaded."""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.service import ServingError, ServingModel, load_approved
from ml.schema import SCHEMA_VERSION, ApartmentFeatures

logger = logging.getLogger(__name__)


def error_response(code, message, request_id, status, details=None):
    return JSONResponse(
        {
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
                "details": details or {},
            }
        },
        status_code=status,
    )


class BodyGuard:
    """Bound body while streaming, including requests without Content-Length."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        scope.setdefault("state", {})["request_id"] = uuid4().hex
        request_id = scope["state"]["request_id"]
        if scope["method"] == "POST":
            headers = dict(scope["headers"])
            media = headers.get(b"content-type", b"").split(b";", 1)[0].strip().lower()
            if media != b"application/json":
                response = error_response(
                    "unsupported_media_type", "Yêu cầu JSON.", request_id, 415
                )
                return await response(scope, receive, send)
            chunks, total = [], 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > 16 * 1024:
                    response = error_response(
                        "request_too_large", "Body vượt giới hạn.", request_id, 413
                    )
                    return await response(scope, receive, send)
                chunks.append(chunk)
                if not message.get("more_body", False):
                    break
            delivered = False
            original_receive = receive

            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
                return await original_receive()

            receive = replay
        return await self.app(scope, receive, send)


def create_app(model: ServingModel | None = None, clock=None) -> FastAPI:
    app = FastAPI(title="HCM Apartment Price AI", version="0.1.0")
    app.state.model = model
    app.state.clock = clock or (lambda: datetime.now(timezone.utc))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.add_middleware(BodyGuard)

    @app.exception_handler(ServingError)
    async def serving_error(request: Request, exc: ServingError):
        return error_response(
            exc.code, exc.message, request.state.request_id, exc.status, exc.details
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        return error_response(
            "invalid_input", "Dữ liệu đầu vào không hợp lệ.", request.state.request_id, 422
        )

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        logger.error("request_failed request_id=%s", request.state.request_id)
        return error_response("internal_error", "Lỗi nội bộ.", request.state.request_id, 500)

    def require_model() -> ServingModel:
        if app.state.model is None:
            raise ServingError("model_unavailable", "Chưa có mô hình được duyệt.")
        return app.state.model

    @app.get("/health/live")
    def live():
        return {"status": "live"}

    @app.get("/health/ready")
    def ready():
        require_model().require_ready(app.state.clock())
        return {"status": "ready"}

    @app.get("/api/v1/metadata")
    def metadata():
        if app.state.model is None:
            return {
                "serving_status": "unavailable",
                "schema_version": SCHEMA_VERSION,
                "model_id": None,
                "data_as_of": None,
                "supported_districts": [],
                "feature_schema": ApartmentFeatures.model_json_schema(),
            }
        return app.state.model.metadata(app.state.clock())

    @app.post("/api/v1/predictions")
    def predict(features: ApartmentFeatures, request: Request):
        return {
            **require_model().predict(features, app.state.clock()),
            "request_id": request.state.request_id,
        }

    @app.get("/api/v1/report")
    def report():
        model = require_model()
        if model.report is None:
            raise ServingError("model_unavailable", "Chưa có báo cáo được duyệt.")
        return model.report

    return app


def configured_app():
    directory = os.environ.get("MODEL_DIR")
    model = None
    if directory:
        try:
            model = load_approved(Path(directory))
        except Exception:
            logger.error("Approved model could not be loaded; prediction remains unavailable")
    return create_app(model)


app = configured_app()
