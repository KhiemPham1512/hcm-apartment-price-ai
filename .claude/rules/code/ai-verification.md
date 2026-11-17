---
paths:
  - "ml/**"
  - "backend/**"
  - "tests/**"
---
# AI và kiểm chứng (chỉ nạp khi đụng ml/, backend/, tests/)

- Giá rao bán hiện tại không phải giá giao dịch hay dự báo tương lai. Synthetic data chỉ dùng để test, không phát hành như giá thị trường.
- Schema dùng chung: đổi contract, code và tests trong cùng PR. Không tune bằng test, không dùng metric cũ cho artifact đã refit, không sửa timestamp để qua freshness gate.
- Test hành vi gồm: strict inputs, không rò nhãn, split nhóm rời, ba mô hình, metric đúng đơn vị, parity offline/HTTP, model chưa duyệt/quá hạn.
- Chuỗi gate: `train` (real bắt buộc registry, ghi fit/tune) → `freeze` → `reserve-test` → `evaluate` (real bắt buộc registry) → `release` (dùng chung `Manifest` của serving). Không bỏ qua bước nào, không tự phê duyệt model, không đổi winner theo kết quả test.
- Báo chính xác phần đã chạy và phần bị chặn. Không nói đã push/bật protection/cài hooks khi chưa kiểm chứng.
