# HCM Apartment Price AI — hướng dẫn cho AI agent

Đồ án nhóm 6 người: ước tính **giá rao bán** căn hộ TP.HCM (Linear, Polynomial, Decision Tree so với baseline), đánh giá holdout độc lập, phục vụ qua FastAPI và demo bằng frontend React. Trao đổi tiếng Việt, ngắn gọn. Tự làm các bước đã được phép; chỉ hỏi khi thiếu một quyết định thiết yếu hoặc khi hành động không thể hoàn tác và nằm ngoài phạm vi.

## Lệnh

```powershell
$py = ".venv/Scripts/python.exe"
& $py -m pytest -q          # toàn bộ test; nếu Temp bị chặn, dùng --basetemp với một thư mục mới trong .local-artifacts/ rồi xóa thư mục đó
& $py -m ruff check .
& $py -m pip check
& $py -m ml.train --help; & $py -m ml.freeze --help; & $py -m ml.registry --help; & $py -m ml.evaluate --help
```

Dùng `gh` cho PR/CI. Có thể đọc README, rồi `ml/schema.py` → `data.py` → `models.py` → `train.py` → `freeze.py` → `registry.py` → `evaluate.py` → `backend/service.py` → `app.py`; `tests/` mô tả hành vi mong đợi.

## Nguồn chuẩn

- README trước: hợp đồng, thuật ngữ, quyết định, research, hướng dẫn. `docs/SPEC.md`: yêu cầu. `docs/TEAM.md`: phân công và checklist theo thành viên. Không tạo tài liệu/helper rời rồi bỏ đó; chuyển nội dung còn cần vào đúng chỗ, xóa file tạm sau khi dùng.
- `handoff.md` ở root là bản chụp nối phiên, chỉ lưu local (không commit), không thay nguồn chuẩn.
- Giữ nguyên nguồn người dùng cung cấp, dữ liệu và thay đổi không thuộc tác vụ. Không xóa dựa trên suy đoán. Không commit raw data, PII, nhãn test, binary model, secrets hoặc môi trường cục bộ.
- Không tạo lại GLOSSARY/ADR/research notes riêng; thuật ngữ và quyết định nằm trong README.

### Theo dõi việc

Checklist nghiệm thu theo thành viên nằm trực tiếp trong `docs/TEAM.md`. Theo chỉ dẫn chủ repo: làm trực tiếp theo phạm vi được giao, không tạo issue mới. Issue cũ chỉ để giữ lịch sử/thảo luận; không chép checklist vai trò sang issue.

## Quy trình cho mỗi vòng công việc

1. **Đọc ngữ cảnh, chốt phạm vi.** Đọc README, CLAUDE.md, `handoff.md` nếu có, SPEC, phần vai trò liên quan trong TEAM và issue/thảo luận. Đối chiếu với code, Git/PR và bằng chứng hiện có. Chọn việc ưu tiên trong phạm vi đã giao, xác định kết quả và tiêu chí nghiệm thu; không tự nhận cả backlog, không làm thay owner khác. Khi thuật ngữ/quy tắc thay đổi hoặc còn mơ hồ, dùng skill `domain-modeling` và ghi kết luận vào README.
2. **Chuẩn bị nhánh, kiểm thử từng hành vi.** Fetch, tạo nhánh riêng từ `origin/main`, ghi SHA base để review. Với thay đổi hành vi, dùng skill `tdd`: chọn public interface mà bên gọi thực sự dùng, viết một test, chạy để thấy nó fail vì hành vi còn thiếu, sửa tối thiểu rồi chạy đến GREEN trước lát tiếp theo. Lỗi setup/môi trường không phải bằng chứng RED. Thay đổi chỉ có tài liệu thì kiểm tra diff, tính nhất quán và tham chiếu, không cần test hành vi.
3. **Triển khai nhỏ, giữ thiết kế rõ.** Dùng `codebase-design` khi cần thiết kế module: interface nhỏ, giấu chi tiết phức tạp, đặt quy tắc ở nơi chịu trách nhiệm. Giữ HTTP mỏng, dùng chung pipeline ML; không thêm abstraction, trường dữ liệu hay tính năng suy đoán. Chỉ mock ranh giới bên ngoài khi cần, không mock nội bộ để test xanh. Chạy test tập trung trong lúc làm; khi xong chạy regression và các kiểm tra bắt buộc theo README. Test nghiệp vụ/hồi quy chính thức nằm trong `tests/`, cùng PR với code. Với UI, kiểm tra hành vi, bàn phím, trạng thái tải/lỗi/rỗng và hiển thị trên màn hình nhỏ/lớn.
4. **Review và sửa đến khi đạt.** Review toàn bộ diff so với SHA base theo hai trục: chuẩn repo và yêu cầu/tiêu chí nghiệm thu (skill `code-review`). Giải quyết các phát hiện quan trọng rồi chạy lại các kiểm tra bị ảnh hưởng. Bug khó: dùng `diagnosing-bugs` (tái hiện, thu nhỏ, kiểm từng giả thuyết, sửa nguyên nhân) và thêm test hồi quy fail trước bản sửa. Chỉ refactor khi đã GREEN.
5. **Hoàn tất và bàn giao.** Cập nhật contract trong README, đúng checklist/evidence/bước tiếp trong TEAM khi có thay đổi tương ứng; không tick cả mục nếu mới xong một phần kỹ thuật. PR ghi vấn đề, hành vi sau khi sửa, phạm vi, kiểm chứng và giới hạn. Gom các cập nhật tài liệu/QA nhỏ vào thay đổi liên quan; không mở PR riêng cho từng kết quả kiểm tra. Stage đường dẫn cụ thể, không force-add hàng loạt. Trước merge, giải thích thay đổi, nhánh đích, CI, giới hạn, ảnh hưởng triển khai, rồi chờ người dùng duyệt rõ ràng. Quyền mở PR không phải quyền merge.
6. **Giữ ngữ cảnh, dọn phần tạm, tiếp tục.** Cập nhật `handoff.md` với mục tiêu, nhánh, SHA base/HEAD, PR/trạng thái, bằng chứng kiểm tra, quyết định còn hiệu lực, phụ thuộc và việc tiếp theo. Phân biệt local, đã merge và đã xác minh triển khai. Dọn artifact đúng phạm vi bên dưới. Tiếp tục việc độc lập trong phạm vi đã giao khi còn chờ phụ thuộc; không trộn tính năng mới vào nhánh chưa xong, không tự merge để đi tiếp.

Nếu thiếu skill, thực hiện quy trình tương ứng và báo giới hạn, không tự cài hay nhận là đã dùng. Áp dụng skill theo bản chất công việc. Hướng dẫn người dùng và hợp đồng hiện hành của repo được ưu tiên.

Sau mỗi vòng, báo ngắn gọn bằng tiếng Việt: đã thay đổi gì và giải quyết việc gì, kiểm tra nào thực sự đã chạy, giới hạn còn lại, trạng thái PR/merge/triển khai, bước tiếp theo kèm lý do và phụ thuộc. Viết đủ rõ cho người mới; không chỉ liệt kê file hoặc số test.

## Tự chủ và bảo toàn workspace

- Tự đọc, sửa, kiểm tra và hoàn thiện việc đã giao; không dừng ở đề xuất hay hỏi lại các bước hiển nhiên đã được phép. Merge PR cần duyệt riêng; không dùng quyền tự chủ để vượt quy tắc Git.
- Được dọn file/helper/log tạm do agent tạo cho tác vụ, sau khi đã đọc, xác nhận hết tác dụng và chuyển thông tin còn cần vào đúng tài liệu hoặc handoff. File tạm đặt trong `.local-artifacts/` (gitignored). Không tạo thư mục root chỉ để phục vụ quy trình.
- Trước khi xóa thư mục tạm: kiểm tra toàn bộ nội dung, resolve đường dẫn tuyệt đối, xác nhận nằm trong workspace và đúng phạm vi; không đi qua symlink/junction. Không xóa theo tuổi file, wildcard rộng hoặc `git clean` cả repo.
- Giữ handoff hiện hành, nguồn tham khảo người dùng cung cấp, đề gốc (`docs/detai.docx`, local), source, docs, tests, môi trường, credentials và dữ liệu có sẵn. File chưa rõ giá trị hoặc không do tác vụ tạo thì giữ lại; hỏi trước nếu thật sự cần xóa.

## GitHub: giảm xung đột cho nhóm 6 người

- Một nhánh tích hợp `main`, không có `develop`. Không push trực tiếp lên `main`; mọi thay đổi đi từ nhánh riêng qua PR. Không force-push.
- Mỗi phạm vi có một owner và một nhánh ngắn hạn: `feat/<slug>`, `fix/<slug>`, `docs/<slug>`, `chore/<slug>`. Trước khi bắt đầu: fetch, tạo nhánh từ `origin/main`. Trước PR: fetch rồi merge `origin/main` vào nhánh. Không rewrite lịch sử đã chia sẻ.
- Mở draft PR sớm, ghi phạm vi/file đang giữ. Không ghi vào file chung khi chưa phối hợp với owner; người khác đề xuất qua review. Không format cả repo trong PR tính năng.
- Owner: TV1 dữ liệu; TV2 shared features/linear/poly; TV3 tree/analysis; TV4 HTTP; TV5 frontend; TV6 root config/README/CI. Đổi interface phải có cả producer và consumer review.
- Conflict: đọc cả hai thay đổi, tích hợp đúng ý nghĩa, chạy lại kiểm tra phần giao nhau; không checkout ours/theirs hàng loạt, không reset/clean phá dữ liệu.
- PR cần CI xanh. Chủ repo duyệt từng PR trước merge; không bắt buộc reviewer GitHub. Vẫn tự kiểm tra code và phần giao nhau; không bỏ phê duyệt model/dữ liệu độc lập. Squash merge khi đã được phép; nếu policy chặn, chỉ dùng quyền admin theo ủy quyền, không tắt policy. Không bịa username/assignee của thành viên.
- TEAM giữ phân công/mốc và checklist theo thành viên; cập nhật đúng ô, evidence và bước tiếp/blocker trong cùng PR. Không tạo bản checklist thứ hai.

## AI và kiểm chứng

- Giá rao bán hiện tại không phải giá giao dịch hay dự báo tương lai. Synthetic data chỉ dùng để test, không phát hành như giá thị trường.
- Schema dùng chung: đổi contract/code/tests trong cùng PR. Không tune bằng test, không dùng metric cũ cho artifact đã refit, không sửa timestamp để qua freshness gate.
- Test hành vi gồm: strict inputs, không rò nhãn, split nhóm rời, ba mô hình, metric đúng đơn vị, parity offline/HTTP, model chưa duyệt/quá hạn.
- Báo chính xác phần đã chạy và phần bị chặn. Không nói đã tạo repo/push/bật protection/cài hooks khi chưa kiểm chứng.
