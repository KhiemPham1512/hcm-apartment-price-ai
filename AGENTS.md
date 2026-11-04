# Hướng dẫn làm việc

- Trao đổi tiếng Việt, ngắn gọn; tự thực hiện các bước đã được phép, chỉ hỏi khi thiếu quyết định thiết yếu hoặc có hành động không thể hoàn tác ngoài phạm vi.
- Đọc README trước. Chỉ giữ `docs/SPEC.md` cho yêu cầu, `docs/TEAM.md` cho phân công. README giữ hợp đồng, thuật ngữ, quyết định, research và hướng dẫn. Không tạo tài liệu/helper rời rồi bỏ đó; chuyển nội dung còn cần và xóa file tạm sau khi dùng.
- Giữ nguyên nguồn người dùng cung cấp, dữ liệu và thay đổi không thuộc tác vụ. Không xóa dựa trên suy đoán. Không commit raw data, PII, nhãn test, binary model, secrets hoặc môi trường cục bộ.
- Dùng skills khi phù hợp, ưu tiên yêu cầu tự chủ và tài liệu gọn của người dùng. Không tạo lại GLOSSARY/ADR/research notes riêng; thuật ngữ và quyết định đã ở README.

## Agent skills

### Issue tracker

GitHub Issues khi repo khả dụng; trước đó dùng backlog trong TEAM. Spec ở SPEC, không có bản sao trong `.scratch/`.

### Domain docs

Đọc mục thuật ngữ và quyết định trong README; cập nhật ở đó khi khái niệm thay đổi.

## GitHub: giảm xung đột cho nhóm 6 người

- Một nhánh tích hợp `main`; không thêm `develop` trong 4 tuần. Bootstrap repo rỗng có thể có một commit nền; sau đó làm qua PR.
- Một issue/một owner triển khai/một nhánh ngắn hạn: `feat/<issue>-<slug>`, `fix/<issue>-<slug>`, `docs/<issue>-<slug>`, `chore/<issue>-<slug>`.
- Trước bắt đầu: fetch, tạo nhánh từ `origin/main`. Trước PR: fetch rồi merge `origin/main` vào nhánh cá nhân. Không rewrite lịch sử đã chia sẻ hoặc force-push nhánh chung.
- Mở draft PR sớm, ghi phạm vi/file đang giữ. Không cùng ghi một file chung mà chưa phối hợp owner; người khác đề xuất qua review. Không format toàn repo trong PR tính năng.
- Owner: TV1 dữ liệu; TV2 shared features/linear/poly; TV3 tree/analysis; TV4 HTTP; TV5 frontend; TV6 root config/README/CI. Đổi interface phải có producer và consumer review.
- Conflict: đọc cả hai thay đổi, tích hợp đúng ý nghĩa, chạy lại kiểm tra phần giao; không checkout ours/theirs hàng loạt hoặc reset/clean phá dữ liệu.
- PR cần CI xanh và ít nhất một reviewer khác tác giả; squash merge sau review. Nếu protection chưa bật, không nói quy tắc đã được GitHub cưỡng chế. Không bịa username/assignee của thành viên chưa cung cấp.
- GitHub Issue giữ status/trao đổi/PR; TEAM giữ phân công/mốc. Không tạo tracker bản sao có trạng thái khác.

## AI và kiểm chứng

- Giá rao bán hiện tại không phải giá giao dịch hoặc dự báo tương lai. Synthetic data chỉ dùng test, không được phát hành như giá thị trường.
- Schema dùng chung, thay contract/code/tests cùng PR. Không tune bằng test, không lấy metric cũ cho artifact đã refit, không sửa timestamp để qua freshness gate.
- Test hành vi: strict inputs, không rò nhãn, split nhóm rời, ba mô hình, metric đúng đơn vị, parity offline/HTTP, model chưa duyệt/quá hạn.
- Báo chính xác phần đã chạy và phần bị chặn. Không nói đã tạo repo/push/bật protection/cài hooks khi chưa kiểm chứng.
