# TV4 — Review PR #51

Ngày đối chiếu: 24/11/2026  
Repository: https://github.com/KhiemPham1512/hcm-apartment-price-ai  
PR: https://github.com/KhiemPham1512/hcm-apartment-price-ai/pull/51  
Commit merge: `8f1be08`  
Trạng thái GitHub: Merged vào `main` ngày 23/11/2026.

## 1. Phạm vi PR

PR #51 bổ sung rate limit, capacity, CORS và trusted proxy handling vào `backend/app.py`, cập nhật README và tests. Không đổi tên endpoint hoặc request schema dự đoán.

## 2. Kết quả review

| Hạng mục | Kết quả |
|---|---|
| Token bucket theo IP | Có; burst mặc định 5, refill 30 request/phút |
| Rate limit response | HTTP 429, `rate_limited`, có `Retry-After` |
| Concurrent inference | Có lock và giới hạn mặc định 4 slot; vượt giới hạn trả 429 `prediction_capacity_exceeded` |
| Body guard | Giới hạn JSON body 16 KiB |
| CORS | Exact origin allowlist; mặc định localhost:5173 và 127.0.0.1:5173 |
| Wildcard CORS | `*` bị từ chối |
| Trusted proxy | Chỉ đọc `X-Forwarded-For` nếu peer trực tiếp thuộc `TRUSTED_PROXY_CIDRS` |
| Invalid proxy CIDR | Bị từ chối khi tạo app |
| Timeout | Ngân sách mặc định 5 giây, nhưng chỉ kiểm tra sau khi inference kết thúc |
| API contract | Không đổi route; thêm lỗi 429/503 cho giới hạn/capacity/timeout |

## 3. Bằng chứng công khai trên PR

Phần Evidence của PR ghi:
- `tests/test_api.py`: 26 passed.
- Toàn bộ test suite: 156 passed.
- Ruff, pip check và diff check đạt.
- GitHub ghi nhận 1 check passed.
- PR được merge vào `main`.
- Không có formal review từ reviewer khác hiển thị trên PR.

Đây là bằng chứng được ghi trên GitHub PR, không phải lần chạy lại trên máy người nhận tài liệu.

## 4. Findings / giới hạn còn lại

### F1 — Rate limit theo process
Token bucket nằm trong dict của từng process, không chia sẻ giữa worker/replica. Khi triển khai nhiều worker, mỗi worker có quota riêng. Khuyến nghị đặt API gateway/reverse proxy có rate limit tập trung phía trước.

### F2 — Bộ nhớ rate-limit tăng theo số IP
Dict lưu trạng thái theo IP khác nhau và không có cơ chế dọn entry cũ. Với demo nhỏ có thể chấp nhận; triển khai public lâu dài cần TTL/LRU hoặc gateway quản lý quota.

### F3 — Chưa có stress test concurrency thực
Test hiện có kiểm tra capacity bằng `max_concurrent_predictions=0`, chưa chứng minh 4 request inference chạy đồng thời được kiểm soát chính xác trong tải đa luồng. Cần thêm test đồng bộ hóa bằng barrier/event và test nhiều request thực.

### F4 — Timeout không phải hard timeout
Code đo thời gian trước/sau `predict()`. Nếu inference chạy lâu, tác vụ vẫn tiếp tục cho đến khi trả về; sau đó API mới trả `503 prediction_timeout`. Muốn hard deadline cần worker/process riêng có khả năng terminate hoặc hạ tầng inference có timeout cưỡng bức.

### F5 — CORS không phải xác thực
Allowlist CORS chỉ kiểm soát browser cross-origin. Nó không thay thế authentication/authorization và không chặn curl hoặc client ngoài browser.

### F6 — Cấu hình proxy phải chính xác
Nếu `TRUSTED_PROXY_CIDRS` bỏ trống hoặc sai, peer sẽ được dùng làm client IP. Nếu mọi request đi qua một proxy mà proxy chưa khai báo, người dùng có thể bị gom chung bucket. Chỉ khai báo CIDR của proxy do nhóm kiểm soát.

## 5. Kết luận review

Kết luận: **Chấp nhận cho demo/local với các giới hạn đã công bố; chưa đủ bằng chứng để tuyên bố hard timeout, multi-worker global rate limit hoặc production load protection.**

PR #51 đã merged nên đây là post-merge technical review, không phải formal GitHub approval/review event. Không cần thay đổi API endpoint hoặc request/response contract thành công để TV5 tích hợp.

## 6. Cấu hình vận hành

PowerShell:

```powershell
$env:CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
# Chỉ đặt nếu thực sự chạy sau proxy; thay bằng CIDR proxy thật:
$env:TRUSTED_PROXY_CIDRS = "10.0.0.0/24"
```

Không sao chép CIDR ví dụ nếu hạ tầng thực tế không dùng dải đó. Local trực tiếp không cần cấu hình trusted proxy.

