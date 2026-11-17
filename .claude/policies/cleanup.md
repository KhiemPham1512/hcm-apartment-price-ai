# Dọn dẹp và bảo toàn workspace (đọc trước khi xóa)

**Được tự dọn:** file/thư mục tạm do agent tạo cho tác vụ đã xong (nháp, helper, log, output tái tạo được), **sau khi** đã đọc nội dung, xác nhận hết tác dụng và chuyển thông tin còn cần vào đúng tài liệu hoặc handoff. File tạm đặt trong `.local-artifacts/` (gitignored).

**Cách xóa:** đường dẫn tuyệt đối đã resolve, nằm trong workspace, không đi qua symlink/junction; thư mục thì kiểm toàn bộ nội dung và reparse point trước khi xóa đệ quy. Không wildcard rộng, không `git clean` toàn repo, không xóa theo tuổi file.

**Không bao giờ tự xóa:** source, docs, tests, `CLAUDE.md`/`.claude/`, môi trường `.venv`, credentials/`.env`, dữ liệu thật, `docs/detai.docx` (đề gốc, local), handoff hiện hành, nguồn tham khảo người dùng cung cấp, bằng chứng duy nhất còn cần cho review. File chưa rõ giá trị hoặc không do tác vụ tạo thì giữ và hỏi.

Không tạo tài liệu/helper rời rồi bỏ đó, không tạo thư mục root chỉ để phục vụ quy trình.
