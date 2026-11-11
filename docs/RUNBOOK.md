# TV4 — Backend/Serving runbook

## 1. Phạm vi và trạng thái

Backend là API suy luận chỉ đọc. Không có upload, retrain, raw-data, model-download hay endpoint thay model. Không có artifact thị trường approved trong repository; vì vậy `/health/live` có thể trả 200 trong khi `/health/ready` và `POST /api/v1/predictions` trả 503 `model_unavailable`. Đây là hành vi đúng, không phải giá fallback.

## 2. Cài đặt local (Windows PowerShell)

Tại thư mục gốc repo:

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r .github/requirements-dev.lock
.venv/Scripts/python.exe -m pip install --no-deps --no-build-isolation -e .
.venv/Scripts/python.exe -m pytest -q
```

Nếu lock file cài đặt không tương thích môi trường, dừng và báo TV6; không tự bỏ lock khi ghi nhận kết quả nghiệm thu. Chạy API local:

```powershell
.venv/Scripts/python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Mở `http://127.0.0.1:8000/docs`, `http://127.0.0.1:8000/openapi.json`, `GET /health/live`, `GET /health/ready`, `GET /api/v1/metadata`.

## 3. Cấu hình serving

| Biến | Mặc định | Ý nghĩa |
|---|---:|---|
| `MODEL_DIR` | không đặt | Thư mục artifact do operator cấu hình; không nhận từ HTTP |
| `CORS_ORIGINS` | localhost:5173, 127.0.0.1:5173 | Danh sách origin phân cách bằng dấu phẩy; wildcard bị từ chối |
| `RATE_LIMIT_REQUESTS` | 30 | Số request/IP trong cửa sổ |
| `RATE_LIMIT_WINDOW_SECONDS` | 60 | Cửa sổ rate limit |
| `PREDICTION_CONCURRENCY` | 4 | Số inference đồng thời tối đa |
| `PREDICTION_QUEUE_TIMEOUT_SECONDS` | 1.0 | Thời gian tối đa chờ slot inference |
| `PREDICTION_TIMEOUT_SECONDS` | 5.0 | Thời gian chờ kết quả HTTP |

Rate limiter lưu trong bộ nhớ một tiến trình. Production nhiều worker/replica cần reverse proxy/WAF rate limiting dùng chung. Không bật proxy headers nếu chưa cấu hình trusted proxy. Chỉ expose HTTPS qua reverse proxy được quản trị; không public trực tiếp Uvicorn.

## 4. Quy trình artifact và rollback

1. TV6/TV2 bàn giao artifact trong thư mục nội bộ được kiểm soát quyền ghi.
2. Xác nhận `manifest.json` có `release_status=approved`, `data_kind=real`, `source_verified=true`, schema/feature đúng, freshness và evidence/reviewer hợp lệ.
3. `pipeline.joblib` phải là artifact được build/review trong trust boundary; đối chiếu SHA-256 manifest. Không lấy artifact từ người dùng hoặc URL.
4. Chạy test loader và smoke local trên bản sao artifact. Không sửa manifest để ép qua gate.
5. Chỉ sau khi TV6 phê duyệt mới cấu hình `MODEL_DIR` tới thư mục release bất biến và restart service.
6. Rollback chỉ trỏ tới thư mục release trước đó nếu loader xác minh thành công, manifest vẫn approved, `data_kind=real`, hash/schema hợp lệ và dữ liệu chưa stale tại thời điểm hiện tại. Nếu bản trước đã stale/rejected/tampered thì không rollback; giữ serving unavailable.
7. Lưu commit, model_id, run_id, dataset_version, hash, thời điểm triển khai và smoke evidence trong biên bản release.

Hiện repository không có `ml.release`, registry triển khai hay artifact thị trường approved; rollback tự động chưa được triển khai. Các bước trên là runbook vận hành thủ công, cần TV6 xác nhận trước khi release.

## 5. Kiểm tra trước bàn giao

```powershell
.venv/Scripts/python.exe -m pytest -q tests/test_api.py tests/test_contract.py tests/test_schema.py
.venv/Scripts/python.exe -m pytest -q
```

Smoke không có model: live=200; ready=503; metadata=200 với `serving_status=unavailable`; prediction=503 `model_unavailable`; không có trường giá dự đoán. Với artifact thật, kiểm tra ready=200, metadata `ready`, district hợp lệ, prediction HTTP/offline parity, ngày dữ liệu và output hữu hạn/dương. Kiểm tra stale tại biên 14 ngày và sau biên; metadata vẫn phải trả `stale`.

## 6. Log và dữ liệu

Không log request body, địa chỉ, số điện thoại, tên người bán, secrets hoặc raw data. API log lỗi nội bộ bằng request_id; không trả traceback. Giữ log và quyền truy cập theo chính sách vận hành của nhóm. Không ghi artifact/raw data vào Git.

## 7. Evidence TV4

Lưu ảnh/đầu ra test có timestamp và commit: Swagger/OpenAPI, live/ready/metadata, invalid input 422, unsupported district 422, body 413, media 415, rate 429 + Retry-After, timeout 503, stale metadata, output NaN/Inf/âm bị chặn, checksum/manifest rejection, offline/HTTP parity và smoke release (chỉ khi có artifact thật approved). Fixture synthetic chỉ chứng minh kỹ thuật, không chứng minh độ chính xác thị trường.
