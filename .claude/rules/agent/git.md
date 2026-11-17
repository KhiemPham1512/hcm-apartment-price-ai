# Git và GitHub (chế độ A: nhóm 6 người, PR vào main)

Đây là nguồn chuẩn quy tắc Git của repo; README và TEAM trỏ về đây.

- Một nhánh tích hợp `main`, không có `develop`. Không push trực tiếp lên `main`; không force-push; không rewrite lịch sử đã chia sẻ.
- Mỗi phạm vi một owner, một nhánh ngắn hạn: `feat/<slug>`, `fix/<slug>`, `docs/<slug>`, `chore/<slug>`. Không bắt buộc số issue, không tạo issue mới. Fetch rồi tạo nhánh từ `origin/main`; trước PR merge `origin/main` vào nhánh.
- **Quyền của Claude** (chủ repo cho phép 14/11/2026): tự commit, đổi nhánh, push `origin <nhánh không phải main>` khi đã kiểm chứng. Hook toàn máy chặn push main, force, xóa nhánh remote, `reset --hard`, `clean -f`, `branch -D`, `checkout .`. **Merge cần chủ repo duyệt rõ ràng**; quyền mở PR không phải quyền merge.
- Commit: message `<loại>: <hành động + phạm vi>`; stage đường dẫn cụ thể, không `git add -A`, không force-add file bị ignore; không commit `.env`, secrets, dữ liệu cục bộ, `.claude/settings.local.json`.
- Mở draft PR sớm, ghi phạm vi/file đang giữ. Không ghi vào file chung khi chưa phối hợp owner; người khác đề xuất qua review. Không format cả repo trong PR tính năng. Dùng skill `pr` cho nội dung PR.
- Owner: TV1 dữ liệu; TV2 shared features/linear/poly; TV3 tree/analysis; TV4 HTTP; TV5 frontend; TV6 root config/README/CI. Đổi interface phải có producer và consumer review.
- Conflict: đọc cả hai thay đổi, tích hợp đúng ý nghĩa, chạy lại kiểm tra phần giao nhau; không checkout ours/theirs hàng loạt. PR xếp chồng: sau khi PR dưới được squash, đổi base PR trên sang `main` và merge `origin/main` vào nhánh.
- PR cần CI xanh. Chủ repo duyệt từng PR; không bắt buộc reviewer GitHub nhưng vẫn tự kiểm code và phần giao nhau, không bỏ phê duyệt model/dữ liệu độc lập. Squash merge khi đã được phép; nếu policy chặn thì chỉ dùng quyền admin theo ủy quyền, không tắt policy. Chưa xác minh cấu hình branch protection.
- Trước khi xin merge: giải thích thay đổi, nhánh đích, CI, giới hạn, ảnh hưởng triển khai. Phân biệt ba trạng thái: trên nhánh / đã merge vào main / đã xác minh triển khai.
- TEAM giữ phân công, mốc và checklist; cập nhật đúng ô, evidence, bước tiếp/blocker trong cùng PR. Không bịa username/assignee thành viên. Không tạo bản checklist thứ hai.
