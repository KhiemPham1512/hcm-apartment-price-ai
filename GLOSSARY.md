# Thuật ngữ — HCM Apartment Price AI

Nguồn duy nhất cho nghĩa của thuật ngữ trong dự án. Hợp đồng chi tiết (trường, ngưỡng, API) và các quyết định nằm ở [README](README.md). Dùng đúng từ ở đây trong code, test, PR và báo cáo; muốn đổi nghĩa thì sửa tại đây trong cùng PR.

## Dữ liệu và nhãn

| Thuật ngữ | Ý nghĩa trong dự án |
| --- | --- |
| Giá rao bán / giá giao dịch | Giá người bán chào / giá mua bán đã hoàn tất; dataset chỉ nhắm giá rao |
| Giá ước tính / đơn giá diện tích | Tổng giá mô hình suy ra / tổng giá chia m²; đơn giá suy từ nhãn không được đưa vào X |
| Tin rao / căn hộ / dự án | Một tin đăng / một căn cụ thể / cụm chung cư; cùng dự án chưa chắc cùng căn |
| Nhóm nghi trùng | Các tin có bằng chứng cùng căn, dùng để ngăn trùng qua các tập. Định danh là `property_group_id`, kiểu chuỗi, giữ số 0 đầu |
| Bản đại diện | Một tin được chọn cho mỗi nhóm nghi trùng, không dùng giá để chọn (ưu tiên tin quan sát giá mới nhất, rồi ngày đăng mới nhất) |
| Cách ly (quarantine) | Dòng dữ liệu không chắc nghĩa hoặc không hợp lệ bị loại khỏi tập sạch kèm mã lý do, ví dụ `non_sale_listing`, `unsupported_district`, `invalid_asking_price`; không tự sửa để giữ lại |
| Ngày dữ liệu | Mốc quan sát giá bảo thủ, khác ngày tải file hay ngày train |
| Cửa sổ dữ liệu / cửa sổ tin | Khoảng quan sát giá / khoảng ngày đăng; không thay thế lẫn nhau |
| Khu vực được hỗ trợ | Khu vực thuộc ranh giới nghiên cứu và đủ nhóm train theo hợp đồng |
| Dữ liệu thật / giả lập (`data_kind`) | Trường của dataset card: `real` là dữ liệu thị trường có nguồn; `synthetic` chỉ để test kỹ thuật, không bao giờ gọi là dữ liệu thị trường |

## Snapshot và phương án dữ liệu

| Thuật ngữ | Ý nghĩa trong dự án |
| --- | --- |
| Snapshot hiện hành (`snapshot_kind=current`) | Dữ liệu còn trong hạn công bố so với hôm nay (giá quan sát và snapshot không quá 7 ngày). Chỉ loại này được phát hành để phục vụ giá |
| Snapshot lịch sử (`snapshot_kind=historical`) | Dữ liệu cũ, được dùng để chạy pipeline và đánh giá. Bỏ kiểm tra tuổi nhưng giữ mọi kiểm tra khác. **Không bao giờ được phát hành**; báo cáo ghi rõ "đánh giá trên dữ liệu lịch sử" |
| Cổng GO / NO-GO | Quyết định của TV6 cùng TV1 về việc nguồn dữ liệu đủ điều kiện (quyền dùng, độ mới, số nhóm). NO-GO cho giá hiện hành nghĩa là chưa có giá để hiển thị |
| Phương án A / B | A: CSV hiện hành có quyền dùng và xác nhận tin còn bán. B (đang chọn): dùng snapshot lịch sử để đánh giá, giá hiện tại vẫn NO-GO |
| Đặc trưng không mang thông tin (`uninformative_features`) | Đặc trưng số thiếu toàn bộ ở tập train (ví dụ `floor_level` của TiniX). Giữ trong schema nhưng model coi là cột hằng; ghi tên trong candidate |

## Chia tập, đánh giá và mô hình

| Thuật ngữ | Ý nghĩa trong dự án |
| --- | --- |
| Train / validation / test | Fit tham số / chọn cấu hình / đánh giá độc lập sau freeze |
| Holdout | Tập test đã được đóng băng khi train (`holdout.csv`, có hash). Nhãn của nó không đưa lên GitHub và không dùng để chọn gì |
| B0 / M1 / M2 / M3 | B0: baseline median. M1: Linear Regression. M2: Polynomial bậc 2. M3: Decision Tree |
| Winner | Mô hình trong M1–M3 có validation RMSE thấp nhất; chênh dưới 1% thì chọn mô hình đơn giản hơn theo thứ tự M1 → M2 → M3. Không đổi theo kết quả test |
| RMSE / MAE / R² | Sai số bình phương trung bình căn và sai số tuyệt đối trung bình, đều tính bằng VND; R² không có đơn vị, có thể âm, không phải phần trăm dự đoán đúng |
| Nhóm chỉ mô tả (`descriptive_only`) | Nhóm sai số có n < 20: chỉ mô tả, không xếp hạng hay suy rộng |
| Khoảng bootstrap | Độ biến thiên của metric khi lấy mẫu lại theo nhóm tài sản trong test. Không phải khoảng dự đoán cho từng căn |

## Kiểm soát và phát hành

| Thuật ngữ | Ý nghĩa trong dự án |
| --- | --- |
| Candidate / approved | Ứng viên chưa được phục vụ / artifact qua kiểm định và review nội bộ |
| Bản khóa candidate (freeze record) | Bằng chứng phiên bản candidate và dữ liệu được người kiểm định ghi nhận trước đánh giá; không đồng nghĩa đã đánh giá hoặc được duyệt phát hành |
| Pool test (`test_pool`) | Tập nhóm chưa từng tiếp xúc được phép làm test mới; `split_groups` chỉ chọn nhóm test trong pool này |
| Registry lịch sử tiếp xúc / dành test mới | Sổ nhóm đã dùng cho fit, tune, phân tích nhãn hoặc đánh giá qua nhiều run / ghi nhận nhóm mới được dành cho test; việc dành không tự chứng minh test còn độc lập khi thực sự đánh giá |
| Gói phát hành | Thư mục `ml.release` tạo ra (`pipeline.joblib`, `manifest.json`, `report.json`) cho model winner đã đánh giá. API chỉ nạp gói `approved` |
| Trạng thái phục vụ (`serving_status`) | `ready`: có gói approved còn hạn. `stale`: dữ liệu quá 14 ngày. `unavailable`: chưa có gói hợp lệ. Hai trạng thái sau thì API không trả giá |
| Parity offline/HTTP | Giá API trả về bằng đúng giá pipeline chạy offline trên cùng gói và cùng đầu vào |
