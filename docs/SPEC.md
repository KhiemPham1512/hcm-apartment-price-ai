# MVP — HCM Apartment Price AI

Status: ready-for-agent. [Repository public](https://github.com/KhiemPham1512/hcm-apartment-price-ai); [README](../README.md) là nguồn chuẩn kỹ thuật; [TEAM](TEAM.md) giữ phân công. Tài liệu không đồng nghĩa mọi tính năng đã hoàn tất.

## Problem Statement

Nhóm 6 người cần hoàn thành đồ án AI trong 4 tuần: ước tính giá căn hộ **hiện tại** ở TPHCM, so sánh ba mô hình hồi quy và giải thích các đặc trưng. Nhãn tiếp cận được là giá rao bán, không phải giá giao dịch đã chốt. Đề gốc yêu cầu Linear Regression, Polynomial Regression, DecisionTreeRegressor, RMSE/R² trên test độc lập và phân tích đặc trưng.

Người dùng đồng ý thu hẹp căn hộ trong địa giới TPHCM trước sắp xếp 2025; TV6 vẫn cần đối chiếu rubric giảng viên về phạm vi nhà/đất của đề gốc.

## Solution

Pipeline có thể tái lập từ snapshot giá hiện hành được phép dùng: chuẩn hóa/audit/gộp trùng → split theo nhóm → baseline và ba mô hình → chọn validation → freeze → test độc lập → review artifact. API dùng cùng feature pipeline, từ chối model chưa được duyệt/quá hạn. Web demo nhỏ là bước tiếp theo; không thay phần nghiên cứu AI bằng làm UI.

## User Stories

1. Là người xem, tôi muốn biết đầu ra là giá rao hay giá giao dịch để hiểu đúng kết quả.
2. Là người xem, tôi muốn nhập diện tích/vị trí để ước tính tổng giá VND.
3. Là người xem, tôi muốn để trống thuộc tính chưa biết mà không bị coi là số 0.
4. Là người xem, tôi muốn chọn đúng khu vực được hỗ trợ.
5. Là người xem, tôi muốn thấy thời điểm quan sát giá và tuổi dữ liệu.
6. Là người xem, tôi muốn lỗi rõ khi input sai, model chưa có hoặc quá hạn.
7. Là người xem, tôi muốn xem đơn giá diện tích suy ra mà không nhầm thành feature có sẵn.
8. Là người xem, tôi muốn so sánh cả ba mô hình và baseline trên cùng tập test.
9. Là người xem, tôi muốn metric có đơn vị và n, không bị gọi R² là accuracy.
10. Là người xem, tôi muốn xem importance và giới hạn không nhân quả.
11. Là người làm data, tôi muốn lưu nguồn/quyền dùng/timestamps/active evidence.
12. Là người làm data, tôi muốn audit thuê/bán/đặt cọc/đơn vị và tin trùng.
13. Là người làm ML, tôi muốn dùng một feature pipeline cho train và inference.
14. Là người làm ML, tôi muốn chọn bằng validation và khóa trước test.
15. Là người kiểm định, tôi muốn group/split/seed/hash để bảo vệ tính độc lập.
16. Là người kiểm định, tôi muốn mỗi kết quả có run/dataset/model/schema version.
17. Là người vận hành, tôi muốn chặn synthetic/candidate artifact khi phục vụ thị trường.
18. Là người vận hành, tôi muốn không có public upload/retrain/download raw.
19. Là thành viên, tôi muốn đọc README/SPEC/TEAM và issue để biết phải làm gì.
20. Là thành viên, tôi muốn owner/nhánh/review interface rõ để giảm conflict.
21. Là giảng viên, tôi muốn chạy lại kết quả, thấy cả kết quả yếu và giới hạn.
22. Là nhóm, tôi muốn demo local và công bố đúng phần chưa đủ điều kiện.

## Implementation Decisions

Python 3.12 cho data/ML/API; scikit-learn, FastAPI/Pydantic; React/TS là phần UI tiếp theo. Một package feature/model dùng chung. File snapshots và artifact versioned, chưa thêm DB/auth/queue. Training/release offline, HTTP chỉ inference/aggregate.

Contract/đơn vị/bounds/freshness và quyền chỉ ở README/schema thực thi, không sao chép vào spec. Snapshot grouped holdout là chính; temporal chỉ khi có archive giá thật theo thời điểm quan sát. Không gọi ngày đăng cũ của tin đã sửa giá là lịch sử giá. Tách training-selection khỏi final evaluation, không refit âm thầm sau đo.

## Testing Decisions

Test hành vi ở seam dữ liệu → thí nghiệm và HTTP → pipeline dùng chung. Kiểm tra schema strict, loại target khỏi X, group disjoint/determinism, ba mô hình cùng split, preprocessing chỉ fit train, selection không dùng test, metric đúng đơn vị/nhãn hằng, model candidate/synthetic/stale và offline/HTTP parity. Dữ liệu giả chỉ kiểm tra kỹ thuật, không kết luận thị trường. UI bổ sung valid/error/stale smoke khi triển khai.

## Acceptance và tiến độ

| Mã | Điều kiện nghiệm thu |
| --- | --- |
| REQ-01 | Dự đoán tổng giá rao bằng đặc trưng hợp lệ, VND, parity offline/HTTP |
| REQ-02 | Baseline, Linear/Polynomial/Decision Tree cùng split và cấu hình lưu lại |
| REQ-03 | RMSE/R² test độc lập, có n/evaluation kind/hash/freeze |
| REQ-04 | Importance/ablation validation và giới hạn diễn giải |
| REQ-05 | Ngày dữ liệu thật, gate chưa có model và quá hạn |
| REQ-06 | Quyền dùng/active/timestamp có evidence và audit |
| REQ-07 | Demo và báo cáo valid/error/stale, không mock fallback |
| REQ-08 | Quyền/release/review/locks và khả năng tái lập |

Ngày 1 xác minh rubric/quỹ giờ/nguồn. Ngày 3 GO/NO-GO data: mục tiêu 1.000 mẫu, tối thiểu 500 nhóm, test tối thiểu 75 nhóm. Đây là ngưỡng tổ chức, không đảm bảo thống kê. Thiếu nguồn giá hiện tại/active/quyền dùng thì no-go tính năng hiện tại, không lách bằng dữ liệu cũ. Ngày 7 baseline xuyên suốt; ngày 14 ba mô hình/freeze; ngày 21 tích hợp/review; ngày 28 demo và kiểm tra lại độ mới.

## Out of Scope

Môi giới/thanh toán, tài khoản/admin web, crawler liên tục, dự báo thị trường tương lai, định giá pháp lý, bản đồ live, LLM/RAG/deep learning. Mô hình mở rộng không thay ba kỹ thuật bắt buộc.

## Further Notes — trạng thái thật

- Đã có nền: schema chung, CSV đã chuẩn hóa, đại diện nhóm/split, baseline + ba pipeline, chọn validation, CLI final evaluation riêng, HTTP schema/readiness/freshness/output guards; kiểm tra kỹ thuật bằng dữ liệu giả.
- Chưa có: dataset thị trường được duyệt, grouping từ raw/crawler, importance/ablation, release command/registry độc lập đầy đủ, UI, rate/concurrency/timeout public hoặc cloud deploy.
- CI Python đã chạy thành công trên PR #2; trạng thái mới nhất xem GitHub Actions, không suy từ lần chạy cũ. Quy tắc review cần được tuân thủ; branch protection chưa được xác minh. Test kỹ thuật không phải kết quả định giá thị trường.
- Spec chỉ giữ tại đây; GitHub Issue dẫn về yêu cầu tương ứng và giữ tiến độ/trao đổi, không duy trì bản spec thứ hai.
