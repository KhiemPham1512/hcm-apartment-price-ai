# Quy trình làm việc (luôn áp dụng)

## Phân loại trước khi làm

Phân loại yêu cầu: ML/data, backend/API, frontend, bug, refactor, review, tài liệu hay chỉ hỏi đáp; chỉ dùng skill và quality gate phù hợp. Việc nhỏ hiển nhiên không cần vòng thiết kế dài. Thiếu skill thì làm theo nguyên tắc tương đương và nói rõ, không tự cài, không nhận là đã dùng.

## Vòng công việc cho thay đổi có hành vi

1. **Nắm ngữ cảnh.** README → `handoff.md` → SPEC → phần vai trò trong TEAM → code/test liên quan. Chọn việc trong phạm vi được giao, ghi tiêu chí nghiệm thu; không nhận cả backlog, không làm thay owner khác. Thuật ngữ/quy tắc đổi hoặc mơ hồ: `domain-modeling`, ghi kết luận vào README.
2. **Nhánh và test trước.** Fetch, nhánh từ `origin/main`, ghi SHA base. `tdd`: một test qua public interface thật, chạy thấy đỏ đúng lý do hành vi còn thiếu (lỗi setup không phải RED), sửa tối thiểu tới xanh rồi mới sang lát tiếp. Chỉ có tài liệu thì kiểm diff, nhất quán, tham chiếu.
3. **Triển khai nhỏ.** `codebase-design` khi thiết kế module: interface nhỏ, quy tắc đặt đúng chỗ. HTTP mỏng, dùng chung pipeline ML; không thêm abstraction, trường dữ liệu hay tính năng suy đoán. Mock chỉ ở ranh giới ngoài. Test chính thức ở `tests/`, cùng PR. UI: kiểm bàn phím, trạng thái tải/lỗi/rỗng, màn hình nhỏ/lớn.
4. **Review và sửa.** `code-review` toàn diff so với SHA base: chuẩn repo và yêu cầu. Bug khó: `diagnosing-bugs`, thêm test hồi quy đỏ trước. Refactor chỉ khi đã xanh.
5. **Hoàn tất.** Cập nhật README (contract) và TEAM (ô, evidence, bước tiếp/blocker); không tick cả mục khi mới xong phần kỹ thuật. PR ghi vấn đề, hành vi sau sửa, phạm vi, kiểm chứng, giới hạn (skill `pr`). Gom cập nhật tài liệu/QA nhỏ vào PR liên quan, không mở PR lẻ.
6. **Giữ ngữ cảnh.** Cập nhật `handoff.md` (skill `update-handoff`), dọn artifact theo `.claude/policies/cleanup.md`, tiếp tục việc độc lập khi còn chờ phụ thuộc. Không trộn tính năng mới vào nhánh chưa xong.

## Báo cáo sau mỗi vòng

Tiếng Việt, đủ rõ cho người mới: đã làm gì và giải quyết việc gì; kiểm tra nào đã chạy thật (fail thì dán lỗi); giới hạn còn lại; trạng thái tách riêng (trên nhánh / PR / đã merge / đã triển khai); bước tiếp theo kèm 1 câu vì sao cần và tác dụng.

## Chỉ dừng hỏi khi

Merge, deploy, xóa ngoài phạm vi dọn dẹp, sửa lịch sử git, thao tác phá hủy dữ liệu, mở rộng phạm vi hoặc đụng file của owner khác, hoặc thiếu quyết định thiết yếu. Còn lại tự chủ làm tiếp.
