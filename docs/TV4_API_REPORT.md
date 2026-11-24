# TV4 — API/Serving report (bản dùng cho báo cáo nhóm)

## 1. Vai trò Backend/Serving

TV4 xây dựng lớp HTTP bằng FastAPI, kiểm tra dữ liệu đầu vào bằng Pydantic, nạp pipeline đã được phê duyệt từ thư mục nội bộ đáng tin cậy, kiểm tra tính hợp lệ/độ mới của model và cung cấp endpoint read-only cho frontend TV5.

Quá trình huấn luyện, đánh giá và phát hành chạy offline. API không huấn luyện lại model trong mỗi request, không nhận upload model/CSV, không cung cấp raw data, không cho người dùng tự chọn đường dẫn model hoặc tải artifact.

## 2. API endpoints

Base API: `/api/v1`

| Method | Endpoint | Mục đích | Khi chưa có artifact approved |
|---|---|---|---|
| GET | `/health/live` | Kiểm tra process còn chạy | 200 |
| GET | `/health/ready` | Kiểm tra model approved và freshness | 503 |
| GET | `/api/v1/metadata` | Schema, feature, supported districts và trạng thái serving | 200, `serving_status=unavailable` |
| POST | `/api/v1/predictions` | Dự đoán một căn hộ | 503 `model_unavailable` |
| GET | `/api/v1/report` | Đọc báo cáo aggregate gắn với artifact approved | 503 nếu chưa có report approved |

OpenAPI có thể xem tại `/openapi.json`; Swagger UI tại `/docs`.

## 3. Request dự đoán

Hai trường bắt buộc: `area_m2`, `district_code`. Các trường `bedrooms`, `bathrooms`, `floor_level` là optional và có thể là `null`. Mã khu vực phải lấy từ `supported_districts` trong metadata.

```json
{
  "area_m2": 70,
  "district_code": "<code-from-metadata>",
  "bedrooms": 2,
  "bathrooms": 2,
  "floor_level": null
}
```

Client không gửi `asking_price_vnd`, giá/m², model path, URL, địa chỉ chi tiết hoặc thông tin người bán. API từ chối field lạ, boolean/numeric string không đúng kiểu, giá trị ngoài hard bounds và district không hỗ trợ.

## 4. Response và lỗi

Response thành công khi có model approved, còn hạn và đầu ra hữu hạn/dương: có `request_id`, `predicted_price_vnd`, `predicted_price_per_m2_vnd`, `target`, `model_id`, `run_id`, `dataset_version`, `schema_version`, thông tin ngày dữ liệu và warnings.

Các lỗi quan trọng:
- 413 `request_too_large`: body vượt 16 KiB.
- 415 `unsupported_media_type`: POST không phải JSON.
- 422 `invalid_input` / `unsupported_district`: input không hợp lệ hoặc khu vực không hỗ trợ.
- 429 `rate_limited`: vượt token bucket, có `Retry-After`.
- 429 `prediction_capacity_exceeded`: hết slot inference, có `Retry-After`.
- 503 `model_unavailable`: thiếu artifact approved hoặc load thất bại.
- 503 `stale_model`: dữ liệu quá hạn.
- 503 `prediction_unavailable`: output lỗi/không hữu hạn/không dương.
- 503 `prediction_timeout`: inference vượt ngân sách thời gian (được phát hiện sau khi hàm kết thúc).
- 500 `internal_error`: lỗi không dự kiến, không trả traceback cho client.

Tất cả lỗi dùng envelope `error.code`, `error.message`, `error.request_id`, `error.details`.

## 5. Rate limit, concurrency, CORS và proxy (PR #51)

PR #51 đã merge vào `main` ngày 23/11/2026, commit `8f1be08`.

- Token bucket mặc định: burst 5; tốc độ refill 30 request/phút/client IP.
- Concurrent prediction mặc định tối đa 4 slot.
- Body JSON tối đa 16 KiB.
- CORS mặc định cho `http://localhost:5173` và `http://127.0.0.1:5173`; có thể cấu hình bằng `CORS_ORIGINS`; wildcard bị từ chối.
- `X-Forwarded-For` chỉ được tin khi peer trực tiếp thuộc CIDR đã khai báo trong `TRUSTED_PROXY_CIDRS`.
- Rate limit và concurrency là per-process; không chia sẻ giữa nhiều worker/replica.
- Timeout 5 giây là post-check; không cưỡng bức terminate inference đang chạy.
- CORS không phải authentication.

Bằng chứng PR: 26 test API pass; 156 test toàn dự án pass; Ruff, pip check, diff check đạt; GitHub ghi nhận 1 check passed. PR không hiển thị formal review từ reviewer khác.

## 6. Vì sao demo không hiện giá?

**Câu trả lời ngắn để thuyết trình:**

“Demo không hiện giá không phải do API bị lỗi. Dataset nhóm đang dùng là dữ liệu lịch sử, khoảng 2025 đến 03/2026, không có bằng chứng các tin đó vẫn còn được rao bán và mức giá vẫn còn hiệu lực ở thời điểm demo. Vì vậy nhóm không được dùng model học từ snapshot lịch sử để trả một con số như giá hiện hành. Cổng phát hành `ml.release` từ chối candidate có `snapshot_kind=historical`, nên không tạo gói `approved`. Backend không nạp được model approved thì `/health/ready` và API dự đoán trả HTTP 503 `model_unavailable`/`unavailable`. Đây là hành vi đúng thiết kế để tránh gây hiểu nhầm cho người dùng. Nhóm vẫn có thể trình bày kết quả đánh giá học thuật trên dữ liệu lịch sử, nhưng phải ghi rõ khoảng thời gian và không gọi đó là giá hiện tại.”

### Nếu giảng viên hỏi tiếp

**Hỏi: Nhóm đã train được model chưa?**  
Đáp: Có. Nhóm đã chạy pipeline và đánh giá B0/M1/M2/M3 trên snapshot lịch sử run-001. Có kết quả đánh giá độc lập; tuy nhiên model đó không đủ điều kiện phát hành phục vụ giá hiện hành.

**Hỏi: Vì sao không cứ dùng model lịch sử để demo?**  
Đáp: Vì ngày đăng tin không chứng minh giá còn hiệu lực. Nếu hiển thị giá từ dữ liệu cũ như giá hôm nay, hệ thống sẽ đưa thông tin sai ngữ cảnh. Nhóm giữ freshness/release gate để ngăn việc đó.

**Hỏi: HTTP 503 có nghĩa là server chết?**  
Đáp: Không. `/health/live` vẫn có thể trả 200, `/api/v1/metadata` vẫn trả 200 với `serving_status=unavailable`. 503 ở readiness/predictions có nghĩa process chạy nhưng chưa có model đủ điều kiện phục vụ.

**Hỏi: Có thể xem kết quả nghiên cứu ở đâu?**  
Đáp: Kết quả run-001 nằm trong `reports/run-001/` và README, dùng nhãn “đánh giá trên dữ liệu lịch sử”. Endpoint `/api/v1/report` chỉ phục vụ report gắn với gói approved; vì run-001 là historical và không được release, endpoint này không được dùng để biến báo cáo lịch sử thành báo cáo serving hiện hành.

## 7. Bằng chứng và giới hạn nghiệm thu

Bằng chứng đọc được:
- `backend/app.py`: routes, rate limit, CORS, proxy, body guard và error handling.
- `backend/service.py`: Manifest, approved loader, SHA-256, freshness, output guard.
- `tests/test_api.py`: strict input, no-model behavior, parity, stale, loader, 429, CORS, proxy.
- `tests/test_release.py`: release gates, offline/HTTP parity, stale/tampered artifact, historical release rejection.
- `docs/TV4_RUNBOOK.md`: startup, environment variables, security limits, rollback procedure.
- PR #51: https://github.com/KhiemPham1512/hcm-apartment-price-ai/pull/51
- Current TEAM checklist: https://github.com/KhiemPham1512/hcm-apartment-price-ai/blob/main/docs/TEAM.md#checklist-tv4

Không tuyên bố deploy public, stress test đa luồng thực tế, hard timeout, global multi-worker rate limit hoặc rollback một artifact production đã được chứng minh. Hiện chưa có gói approved từ dữ liệu hiện hành.
