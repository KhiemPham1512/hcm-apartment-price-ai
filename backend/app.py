"""Read-only inference API. By default no market model is loaded."""

import logging
import math
import os
import threading
import time
from datetime import datetime, timezone
from ipaddress import ip_address, ip_network
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.service import ServingError, ServingModel, load_approved
from ml.schema import SCHEMA_VERSION, ApartmentFeatures

logger = logging.getLogger(__name__)
LOCAL_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def error_response(code, message, request_id, status, details=None, headers=None):
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
        headers=headers,
    )


def cors_origins() -> list[str]:
    origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
    if any("*" in origin for origin in origins):
        raise ValueError("Wildcard CORS origins are not allowed")
    return origins or LOCAL_ORIGINS


def trusted_proxies():
    raw = os.environ.get("TRUSTED_PROXY_CIDRS", "")
    return [ip_network(c.strip(), strict=False) for c in raw.split(",") if c.strip()]


def client_ip(request: Request, proxies) -> str:
    """Peer address; X-Forwarded-For counts only when the direct peer is a declared proxy."""
    peer = request.client.host if request.client else "unknown"
    try:
        peer_ip = ip_address(peer)
    except ValueError:
        return peer
    if not any(peer_ip in net for net in proxies):
        return peer
    hops = request.headers.get("x-forwarded-for", "").split(",")
    for hop in reversed([h.strip() for h in hops if h.strip()]):
        try:
            ip = ip_address(hop)
        except ValueError:
            return peer
        if not any(ip in net for net in proxies):
            return str(ip)
    return peer


class TokenBuckets:
    """Per-client token bucket.

    shortcut: in-process dict that grows with distinct IPs and is not shared across workers;
    fine for the demo, put a gateway in front for a public multi-worker deployment.
    """

    def __init__(self, capacity: int, per_minute: float):
        self.capacity, self.rate = capacity, per_minute / 60
        self.state: dict[str, tuple[float, float]] = {}
        self.lock = threading.Lock()

    def take(self, key: str) -> int:
        """0 when allowed, else whole seconds until a token is available."""
        now = time.monotonic()
        with self.lock:
            tokens, last = self.state.get(key, (float(self.capacity), now))
            tokens = min(self.capacity, tokens + (now - last) * self.rate)
            if tokens >= 1:
                self.state[key] = (tokens - 1, now)
                return 0
            self.state[key] = (tokens, now)
            return max(1, math.ceil((1 - tokens) / self.rate)) if self.rate else 60


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


def create_app(
    model: ServingModel | None = None,
    clock=None,
    *,
    rate_limit_capacity: int = 5,
    rate_limit_per_minute: float = 30,
    max_concurrent_predictions: int = 4,
    prediction_timeout_seconds: float = 5.0,
) -> FastAPI:
    app = FastAPI(title="HCM Apartment Price AI", version="0.1.0")
    app.state.model = model
    app.state.clock = clock or (lambda: datetime.now(timezone.utc))
    buckets = TokenBuckets(rate_limit_capacity, rate_limit_per_minute)
    proxies = trusted_proxies()
    slots = {"in_use": 0, "lock": threading.Lock()}
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.add_middleware(BodyGuard)

    @app.exception_handler(ServingError)
    async def serving_error(request: Request, exc: ServingError):
        retry = exc.details.get("retry_after_seconds")
        return error_response(
            exc.code,
            exc.message,
            request.state.request_id,
            exc.status,
            exc.details,
            {"Retry-After": str(retry)} if retry else None,
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

    def rate_limit(request: Request):
        wait = buckets.take(client_ip(request, proxies))
        if wait:
            raise ServingError(
                "rate_limited", "Quá nhiều yêu cầu.", 429, {"retry_after_seconds": wait}
            )

    @app.post("/api/v1/predictions", dependencies=[Depends(rate_limit)])
    def predict(features: ApartmentFeatures, request: Request):
        with slots["lock"]:
            if slots["in_use"] >= max_concurrent_predictions:
                raise ServingError(
                    "prediction_capacity_exceeded",
                    "Hệ thống đang bận.",
                    429,
                    {"retry_after_seconds": 1},
                )
            slots["in_use"] += 1
        try:
            started = time.monotonic()
            result = require_model().predict(features, app.state.clock())
            # Python cannot kill a running inference, so the budget is checked after it returns.
            if time.monotonic() - started >= prediction_timeout_seconds:
                raise ServingError("prediction_timeout", "Dự đoán vượt thời gian cho phép.")
        finally:
            with slots["lock"]:
                slots["in_use"] -= 1
        return {**result, "request_id": request.state.request_id}

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
