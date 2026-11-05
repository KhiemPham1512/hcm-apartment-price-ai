# Hướng dẫn làm việc

- Trao đổi tiếng Việt, ngắn gọn; tự thực hiện các bước đã được phép, chỉ hỏi khi thiếu quyết định thiết yếu hoặc có hành động không thể hoàn tác ngoài phạm vi.
- Đọc README trước. Chỉ giữ `docs/SPEC.md` cho yêu cầu, `docs/TEAM.md` cho phân công. README giữ hợp đồng, thuật ngữ, quyết định, research và hướng dẫn. Không tạo tài liệu/helper rời rồi bỏ đó; chuyển nội dung còn cần và xóa file tạm sau khi dùng.
- Giữ nguyên nguồn người dùng cung cấp, dữ liệu và thay đổi không thuộc tác vụ. Không xóa dựa trên suy đoán. Không commit raw data, PII, nhãn test, binary model, secrets hoặc môi trường cục bộ.
- Dùng skills khi phù hợp, ưu tiên yêu cầu tự chủ và tài liệu gọn của người dùng. Không tạo lại GLOSSARY/ADR/research notes riêng; thuật ngữ và quyết định đã ở README.

## Agent skills

### Issue tracker

Checklist nghiệm thu theo thành viên nằm trực tiếp trong `docs/TEAM.md` để AI đọc từ checkout. GitHub Issues giữ từng ticket triển khai, thảo luận và liên kết PR; không sao chép checklist vai trò sang issue. Spec ở SPEC, không có bản sao trong `.scratch/`.

### Domain docs

Đọc mục thuật ngữ và quyết định trong README; cập nhật ở đó khi khái niệm thay đổi.

## Quy trình cho mỗi vòng công việc

1. **Đọc ngữ cảnh, chốt phạm vi.** Đọc README trước, rồi AGENTS, `handoff.md` nếu có, SPEC, phần vai trò liên quan trong TEAM và issue/thảo luận. Đối chiếu với code, Git/PR và bằng chứng hiện có; handoff là bản chụp nối phiên, không thay nguồn chuẩn. Chọn việc ưu tiên trong phạm vi đã giao, xác định kết quả và tiêu chí nghiệm thu; không tự nhận toàn bộ backlog hoặc làm thay owner khác. Khi thuật ngữ/quy tắc thay đổi hay còn mơ hồ, dùng `domain-modeling` nếu có và ghi kết luận vào README.

2. **Chuẩn bị nhánh, kiểm thử từng hành vi.** Fetch và tạo nhánh riêng từ `origin/main` theo quy tắc Git bên dưới; ghi SHA base để review. Với thay đổi hành vi, dùng `tdd` nếu có: chọn public interface thực tế mà bên gọi sử dụng, viết một test, chạy để thấy lỗi do hành vi còn thiếu, sửa tối thiểu rồi chạy đến GREEN trước lát tiếp theo. Lỗi setup/môi trường không phải bằng chứng RED. Tái sử dụng interface và phạm vi kiểm thử đã được chấp thuận, không xin lại phép cho cùng việc. Thay đổi chỉ có tài liệu thì kiểm tra diff, tính nhất quán và tham chiếu, không tạo test hành vi hình thức.

3. **Triển khai nhỏ, giữ thiết kế rõ.** Dùng `codebase-design` khi cần thiết kế module: interface nhỏ, che giấu chi tiết phức tạp, tập trung quy tắc ở nơi chịu trách nhiệm. Giữ HTTP mỏng, dùng chung pipeline ML; không thêm abstraction, trường dữ liệu hoặc tính năng suy đoán. Test qua public interface phù hợp, chỉ mock ranh giới bên ngoài khi cần, không mock nội bộ để làm test xanh. Chạy test tập trung trong quá trình làm; khi xong chạy regression và kiểm tra bắt buộc phù hợp theo README. Giữ test nghiệp vụ/hồi quy chính thức trong `tests/`, cùng PR với code. Với UI, dùng skill phù hợp và kiểm tra hành vi, bàn phím, trạng thái tải/lỗi/rỗng và hiển thị trên màn hình nhỏ/lớn.

4. **Review và sửa đến khi đạt.** Review toàn bộ diff so với SHA base theo hai trục: chuẩn repo và yêu cầu/tiêu chí nghiệm thu. Dùng `code-review` khi phù hợp; giải quyết phát hiện quan trọng rồi chạy lại kiểm tra bị ảnh hưởng. Khi gặp bug khó, dùng `diagnosing-bugs` nếu có: tái hiện, thu nhỏ tình huống, kiểm tra từng giả thuyết và sửa nguyên nhân; thêm test hồi quy thất bại trước bản sửa. Refactor khi test đã GREEN, rồi review và kiểm tra lại phần thay đổi. Với lỗi tài liệu, sửa và đối chiếu tính nhất quán.

5. **Hoàn tất thay đổi và bàn giao.** Cập nhật contract trong README và đúng checklist/evidence/bước tiếp trong TEAM khi có thay đổi tương ứng; không tick hoàn thành toàn mục nếu mới xong một phần kỹ thuật. PR ghi vấn đề, hành vi sau sửa, issue, phạm vi, kiểm chứng và giới hạn. Gom cập nhật tài liệu/QA nhỏ vào thay đổi liên quan hoặc một đợt tài liệu có phạm vi rõ; không mở PR riêng cho từng kết quả kiểm tra. Yêu cầu rõ của người dùng về PR được ưu tiên. Stage đường dẫn cụ thể, không force-add hàng loạt. Trước merge, giải thích thay đổi, nhánh đích, CI/review, giới hạn và ảnh hưởng triển khai rồi chờ người dùng duyệt rõ ràng; quyền triển khai hoặc mở PR không phải quyền merge.

6. **Giữ ngữ cảnh, dọn phần tạm và tiếp tục.** Cập nhật handoff hiện có với mục tiêu, nhánh, SHA base/HEAD, PR/trạng thái hoặc ghi chưa mở PR, bằng chứng kiểm tra, quyết định còn hiệu lực, phụ thuộc và việc tiếp. Phân biệt local, đã merge và đã xác minh triển khai; merge không chứng minh deploy thành công. Handoff không trở thành checklist hoặc bản sao spec thứ hai. Sau khi giữ đủ thông tin cần thiết, dọn artifact đúng phạm vi bên dưới. Tiếp tục việc độc lập trong phạm vi đã giao khi còn phụ thuộc; không trộn tính năng mới vào nhánh chưa xong hoặc tự merge để đi tiếp.

Đọc `SKILL.md` khi dùng skill; nếu thiếu skill, thực hiện quy trình tương ứng và báo giới hạn, không tự cài hay nhận đã dùng. Áp dụng theo bản chất công việc, không ép mọi skill vào thay đổi tài liệu nhỏ. Hướng dẫn người dùng và hợp đồng hiện hành của repo được ưu tiên.

Sau mỗi vòng, báo ngắn gọn bằng tiếng Việt: đã thay đổi gì và giúp giải quyết việc gì, kiểm tra nào thực sự chạy, giới hạn còn lại, trạng thái PR/merge/triển khai nếu có và bước tiếp cùng phụ thuộc. Không chỉ liệt kê file hoặc số test.

## Tự chủ và bảo toàn workspace

- Tự đọc, sửa, kiểm tra và hoàn thiện công việc đã được giao; không dừng ở đề xuất hoặc hỏi lại các bước hiển nhiên đã được phép. Chỉ hỏi khi thiếu quyết định thiết yếu, cần mở rộng phạm vi hoặc có hành động không thể hoàn tác chưa được chấp thuận. Việc merge PR cần duyệt riêng như trên; không dùng quyền tự chủ để vượt quy tắc Git.
- Được dọn file/helper/log tạm do agent tạo cho tác vụ khi đã đọc, xác nhận hết tác dụng và chuyển thông tin còn cần vào tài liệu đúng chỗ hoặc handoff hiện có. Không tạo thêm tài liệu/context rời hoặc thư mục root chỉ để phục vụ quy trình.
- Trước xóa thư mục tạm, kiểm tra toàn bộ nội dung, resolve đường dẫn tuyệt đối và xác nhận nằm trong workspace, đúng phạm vi tác vụ; không đi qua symlink/junction ra ngoài. Không xóa theo tuổi file, wildcard rộng hoặc `git clean` toàn repo.
- Giữ handoff hiện hành, nguồn tham khảo người dùng cung cấp, đề gốc, source, docs, tests, skills, môi trường, credentials và dữ liệu có sẵn. Không xóa ngữ cảnh chỉ vì cũ; giữ bằng chứng duy nhất còn cần cho review hoặc phần đang chờ. File chưa rõ giá trị hoặc không do tác vụ tạo thì giữ lại; hỏi trước nếu thực sự cần xóa ngoài phạm vi đã được phép.

## GitHub: giảm xung đột cho nhóm 6 người

- Một nhánh tích hợp `main`; không thêm `develop` trong 4 tuần. Không push trực tiếp lên `main`: mọi thay đổi phải từ nhánh riêng và qua PR. Không dùng force-push để vượt quy trình.
- Một issue/một owner triển khai/một nhánh ngắn hạn: `feat/<issue>-<slug>`, `fix/<issue>-<slug>`, `docs/<issue>-<slug>`, `chore/<issue>-<slug>`.
- Trước bắt đầu: fetch, tạo nhánh từ `origin/main`. Trước PR: fetch rồi merge `origin/main` vào nhánh cá nhân. Không rewrite lịch sử đã chia sẻ hoặc force-push nhánh chung.
- Mở draft PR sớm, ghi phạm vi/file đang giữ. Không cùng ghi một file chung mà chưa phối hợp owner; người khác đề xuất qua review. Không format toàn repo trong PR tính năng.
- Owner: TV1 dữ liệu; TV2 shared features/linear/poly; TV3 tree/analysis; TV4 HTTP; TV5 frontend; TV6 root config/README/CI. Đổi interface phải có producer và consumer review.
- Conflict: đọc cả hai thay đổi, tích hợp đúng ý nghĩa, chạy lại kiểm tra phần giao; không checkout ours/theirs hàng loạt hoặc reset/clean phá dữ liệu.
- PR cần CI xanh và ít nhất một reviewer khác tác giả; squash merge sau review. Nếu protection chưa bật, không nói quy tắc đã được GitHub cưỡng chế. Không bịa username/assignee của thành viên chưa cung cấp.
- TEAM giữ phân công/mốc và checklist theo thành viên. Khi xong cập nhật đúng ô, evidence và bước tiếp/blocker trong cùng PR; GitHub Issue giữ status/trao đổi của từng ticket. Không tạo thêm bản checklist có trạng thái khác.

## AI và kiểm chứng

- Giá rao bán hiện tại không phải giá giao dịch hoặc dự báo tương lai. Synthetic data chỉ dùng test, không được phát hành như giá thị trường.
- Schema dùng chung, thay contract/code/tests cùng PR. Không tune bằng test, không lấy metric cũ cho artifact đã refit, không sửa timestamp để qua freshness gate.
- Test hành vi: strict inputs, không rò nhãn, split nhóm rời, ba mô hình, metric đúng đơn vị, parity offline/HTTP, model chưa duyệt/quá hạn.
- Báo chính xác phần đã chạy và phần bị chặn. Không nói đã tạo repo/push/bật protection/cài hooks khi chưa kiểm chứng.
