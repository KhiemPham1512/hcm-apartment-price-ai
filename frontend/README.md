# Frontend — TV5

Ứng dụng giao diện người dùng được xây dựng bằng React, TypeScript và Vite, tích hợp với API FastAPI hiện có. Thư mục `frontend/` thuộc phạm vi phụ trách của TV5.

## 1. Yêu cầu môi trường

- Node.js và npm.
- Python 3.12 và môi trường ảo của dự án.
- Các thư viện backend đã được cài đặt theo hướng dẫn trong README ở thư mục gốc.

## 2. Chạy ứng dụng trên máy cá nhân

**Terminal 1 — Khởi động backend**

Mở PowerShell tại thư mục gốc dự án:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Khởi động frontend**

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Mở trình duyệt tại:

`http://127.0.0.1:5173`

Vite Proxy chuyển tiếp các yêu cầu `/api` và `/health` đến backend tại `http://127.0.0.1:8000`.

Nếu muốn sử dụng địa chỉ API khác, cấu hình biến `VITE_API_BASE_URL` trong file `frontend/.env`. Ví dụ:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 3. Kiểm tra kết nối backend

Khi backend đang chạy, mở một cửa sổ PowerShell khác:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/api/v1/metadata
```

Kiểm tra các trường `serving_status` và `supported_districts` trong kết quả metadata.

Giao diện lấy dữ liệu khu vực và trạng thái mô hình trực tiếp từ API. Không tự tạo danh sách khu vực hoặc sử dụng dữ liệu kiểm thử làm dữ liệu thay thế khi chạy thực tế.

## 4. Build và kiểm thử giao diện

Thực hiện tại thư mục `frontend/`:

```powershell
npm install
npx playwright install chromium
npm run build
npm run test:e2e
```

Bộ E2E thông thường sử dụng dữ liệu fixture tổng hợp để kiểm thử giao diện trong các tình huống xác định. Dữ liệu fixture chỉ phục vụ kiểm thử, không được sử dụng làm dữ liệu thay thế trong ứng dụng thực tế.

**Chạy smoke test với backend thật:**

Giữ backend hoạt động ở Terminal 1, sau đó chạy:

```powershell
E2E_BACKEND=1 npx playwright test e2e/integration.spec.ts   # PowerShell: $env:E2E_BACKEND=1; npx playwright test e2e/integration.spec.ts
```

Smoke test kiểm tra phản hồi metadata từ backend thật thông qua Vite Proxy và xác minh trạng thái nút dự đoán theo trạng thái phục vụ của mô hình.

Test không tự tạo mô hình hoặc tạo kết quả dự đoán giả.

## 5. Chức năng và quy tắc tích hợp API

- Gọi `GET /api/v1/metadata` khi khởi động ứng dụng.
- Tạo danh sách khu vực từ `supported_districts` do API cung cấp.
- Tạo các trường nhập liệu từ `feature_schema.properties`.
- Sử dụng tiêu đề, mô tả, trường bắt buộc và giới hạn số liệu theo metadata khi có.
- Các trường số không bắt buộc nếu để trống sẽ được gửi dưới dạng JSON `null`.
- Chỉ gọi `POST /api/v1/predictions` khi `serving_status` là `ready`.
- Hiển thị tổng giá, đơn giá/m², ngày dữ liệu, snapshot nguồn, area basis, phiên bản schema, dataset, model và cảnh báo do API trả về.
- Lấy báo cáo tùy chọn từ `GET /api/v1/report`.
- Không tự tính lại các chỉ số đánh giá mô hình ở frontend.
- Hiển thị lỗi 422, 503, dữ liệu hết hạn và lỗi kết nối mạng.
- Không giữ lại giá dự đoán cũ hoặc giá giả khi yêu cầu thất bại.

## 6. Trạng thái mô hình và giới hạn

- `ready`: Mô hình sẵn sàng phục vụ dự đoán khi metadata và khu vực hỗ trợ hợp lệ.
- `stale`: Mô hình có dữ liệu đã quá hạn, chức năng dự đoán bị vô hiệu hóa.
- `unavailable`: Chưa có mô hình khả dụng, chức năng dự đoán bị vô hiệu hóa.

Ứng dụng chỉ cung cấp dự đoán khi backend xác nhận có mô hình hợp lệ, được phê duyệt và còn hạn sử dụng.

Các kết quả từ fixture Playwright chỉ chứng minh hành vi giao diện, không chứng minh độ chính xác của giá thị trường hoặc trạng thái phê duyệt mô hình.

## 7. Bằng chứng kiểm thử và bàn giao

Khi ghi nhận bằng chứng mới, cần lưu:

- Ngày thực hiện kiểm thử.
- Branch và commit đang sử dụng.
- Trạng thái mô hình từ backend.
- Kết quả smoke test.
- Kết quả kiểm thử E2E.
- Kết quả build production.

Không mô tả kết quả dự đoán từ fixture là dự đoán giá thị trường thực tế.

Demo cuối cùng với mô hình được phê duyệt cần có bằng chứng bàn giao từ TV6 và kết quả tích hợp backend tương ứng.