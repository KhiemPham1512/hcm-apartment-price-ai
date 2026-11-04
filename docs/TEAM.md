# Phân công 6 người trong 4 tuần

Owner điều phối: TV6. Kế hoạch giả định **12 giờ/người/tuần**, 48 giờ/người, tổng 288 giờ; chưa phải cam kết thời gian thực của từng thành viên. Ngày 1 thay TV1–TV6 bằng tên và xác nhận quỹ giờ. Nếu thiếu giờ, cắt trang trí/UI phụ và thí nghiệm mở rộng trước; giữ ba mô hình, dữ liệu, test độc lập.

Lịch tính từ 04/11/2026: tuần 1 ngày 04–10/11, tuần 2 ngày 11–17/11, tuần 3 ngày 18–24/11, tuần 4 ngày 25/11–01/12. Nếu bắt đầu khác ngày, dời lịch tại **file này**; ngày 1/3/7/14/21/28 trong spec là mốc tương đối.

## Người, công nghệ và phạm vi sở hữu

| Thành viên | Trách nhiệm chính | Công nghệ phải dùng/học | Thư mục/file sở hữu khi triển khai | Người dự phòng / reviewer |
| --- | --- | --- | --- | --- |
| TV1 — Data Engineer | Nguồn có phép, dữ liệu hiện tại, chuẩn hóa đơn vị, nhóm trùng, dataset card | Python, pandas, CSV/Parquet, pytest; đọc license và timestamps | `ml/data.py`, `ml/schema.py`, manifests; đổi schema cần TV2+TV4 review | TV6 audit; TV2 kiểm tra feature |
| TV2 — ML Linear/Polynomial | Shared preprocessing, baseline, Linear/Polynomial, chọn validation và orchestration training | NumPy, scikit-learn Pipeline/ColumnTransformer, OHE, scaler, PolynomialFeatures, pytest, matplotlib | `ml/models.py`, `ml/train.py`; file factory chung TV2 giữ | TV3 review numerical; TV6 freeze |
| TV3 — ML Tree/Explainability | Decision Tree, tuning có giới hạn, importance, ablation, phân tích lỗi | DecisionTreeRegressor, permutation_importance, pandas, matplotlib/seaborn, pytest | Module analysis tạo khi nhận issue; đổi cây trong `ml/models.py` phối hợp TV2 trước | TV2 review fairness; TV6 phản biện |
| TV4 — Backend/Serving | API đúng contract, pipeline dùng chung, model loading/readiness, freshness và bảo mật | FastAPI, Pydantic, Uvicorn, joblib trusted loading, pytest/TestClient | `backend/`, API schema snapshot, `../README.md#api`, `../README.md#bao-mat` | TV6 review quyền; TV5 review consumer |
| TV5 — Frontend/Demo | Form, metadata-driven input, kết quả, trang so sánh/giới hạn, trạng thái lỗi | React, TypeScript, Vite, CSS, HTTP fetch, Playwright smoke | `frontend/`; fixtures API public, tài liệu demo UI | TV4 review contract; TV6 acceptance |
| TV6 — Tech Lead/Evaluation/QA | SSOT, rubric, split/test độc lập, release gate, tích hợp, báo cáo và demo | Git/PR, Python/pytest, metrics, environment locks, CI; Docker tùy chọn | `ml/evaluate.py`, `ml/release.py`, integration checks, root config, kiến trúc/ADR/runbook | TV4 review release; mọi owner review phần mình |

TV6 không được trở thành người sửa toàn bộ code thay nhóm. Mỗi owner viết kiểm tra mảng mình, bàn giao chạy được và đóng góp báo cáo. Khoảng 180/288 giờ dự kiến dành cho dữ liệu/ML/đánh giá/đóng gói AI; đây là phân bổ ưu tiên, không phải giờ đã làm.

## Nhiệm vụ đề xuất cho bạn: TV6 — tích hợp và kiểm định xuyên suốt

**Một nhiệm vụ chính:** giữ luồng dữ liệu → huấn luyện → đánh giá độc lập → API → demo chạy lại được. Vai trò này đi qua sản phẩm của cả năm người còn lại, giúp bạn hiểu điểm bàn giao và tiếp quản khi có người trễ. Đây là đề xuất, chưa gán bạn vào username hay thay owner hiện có.

| Mốc | Bạn trực tiếp làm | Bằng chứng cần nhận từ thành viên |
| --- | --- | --- |
| Ngày 1–3 | Cài môi trường, chạy pytest/Ruff, đọc schema; cùng TV1 kiểm tra nguồn, đơn vị, timestamps và nhóm trùng | CSV/card hợp lệ, quyền dùng, audit và quyết định GO/NO-GO |
| Ngày 7 | Chạy lại một luồng từ CSV sạch đến candidate; đối chiếu đầu vào API | TV1 bàn giao dữ liệu; TV2 bàn giao pipeline, selection và hash split |
| Ngày 14 | Kiểm tra cả Linear/Polynomial/Tree cùng split; khóa cấu hình trước khi mở holdout | TV2/TV3 bàn giao config và validation; không đổi winner theo test |
| Ngày 21 | Chạy `ml.evaluate` sau freeze; cùng TV4 so kết quả offline/HTTP, thiếu model và stale | Bảng baseline + ba mô hình, artifact đúng hash; test HTTP pass |
| Ngày 28 | Cùng TV5 chạy demo, xác minh ngày dữ liệu và báo cáo; diễn tập trên máy bạn | Demo thật hoặc trạng thái chưa sẵn sàng rõ ràng; hướng dẫn chạy lại |

Đọc code theo thứ tự: `ml/schema.py` → `ml/data.py` → `ml/models.py` → `ml/train.py` → `ml/evaluate.py` → `backend/service.py` → `backend/app.py` → `tests/`. Chạy từng bước theo [README](../README.md), không cần viết lại toàn bộ phần của thành viên khác.

Khi một thành viên trễ: ghi blocker ở GitHub Issue, thống nhất chuyển owner và phạm vi file trước khi tiếp quản; lấy đầu vào/đầu ra đã chốt làm điểm bắt đầu. Ưu tiên nguồn dữ liệu hợp lệ và baseline xuyên suốt; cắt trang trí hoặc thí nghiệm phụ trước. TV1 là phụ thuộc đầu tiên: chưa có nguồn đạt chuẩn thì báo NO-GO phần giá hiện tại, không dùng dữ liệu giả để cứu demo. Giữ holdout độc lập: nếu bạn phải tune thay TV2/TV3, nhờ reviewer khác đánh giá và ghi rõ mọi lần đã xem nhãn; không gọi holdout đã dùng để tune là test độc lập.

## Tuần 1 — khóa dữ liệu và một lát cắt chạy xuyên suốt

| Người | Việc cụ thể | Đầu ra cuối tuần / cách nghiệm thu |
| --- | --- | --- |
| TV1 | Ngày 1 thẩm định nguồn/quyền/ngày tin và thời điểm giá; ngày 2 parser + audit; ngày 3 gate dữ liệu. Sau GO, chuẩn hóa, grouping và đề xuất split theo protocol | Dataset card, raw/clean hashes, thống kê loại dòng, danh mục khu vực có nguồn, grouping audit; TV6 duyệt theo spec |
| TV2 | Trước có data làm fixture ẩn danh; thiết kế `features.py`; B0 và M1; M2 skeleton. Không chờ crawler | Pipeline fit/predict được; test cột nhãn bị loại, imputer không học ngoài train; config và validation log |
| TV3 | EDA cùng TV1; thiết kế interface cây giống M1; chạy M3 ban đầu; kiểm tra mất cân bằng dự án | EDA có n/kỳ/đơn vị; baseline cây chưa tuyên bố winner; kế hoạch importance |
| TV4 | Pydantic và route skeleton; metadata/error envelope; loader mock cho test; kết nối artifact B0/M1 khi đủ điều kiện | Contract tests, health/ready, strict inputs; API smoke cùng offline prediction. Không gắn nhãn mock thành hiện tại |
| TV5 | Form và report layout với mock đúng contract; hiển thị đơn vị, ngày và lỗi; không tự hardcode district | Luồng UI mock và một request thật; loading/empty/stale/invalid states nhìn được |
| TV6 | Xác nhận rubric, tên/quỹ giờ; environment và repo conventions; kiểm tra data gate; giữ split/test; tích hợp baseline | Một lệnh pipeline demo theo hướng dẫn, biên bản GO/NO-GO, split hash, task board có owner |

**Ngày 3 quyết định chung:** không có dữ liệu hiện tại đạt điều kiện thì chuyển backlog sang giải quyết nguồn hoặc báo chưa đủ điều kiện, không lén thay bằng data cũ. TV4/TV5 vẫn làm contract/mocks và kiểm thử trong lúc chờ, nhưng không coi phần current estimate đã hoàn thành.

## Tuần 2 — hoàn thành ba mô hình, không mở test để tune

| Người | Việc cụ thể | Bàn giao |
| --- | --- | --- |
| TV1 | Audit false duplicates/giá thuê/đơn vị; kiểm tra snapshot refresh; schema tests và missingness | Data pipeline ổn định, manifest không sửa ngược snapshot cũ |
| TV2 | M1/M2 đủ pipeline; B0, tổng hợp validation; khóa feature/config theo protocol | Bảng validation thực, config candidate và danh sách môi trường |
| TV3 | Tuning M3 trong ngân sách; importance và ablation trên validation; so complexity | Figures tái lập được, tree config, ghi hạn chế tương quan/overfit |
| TV4 | Load artifact dùng chung, readiness/freshness, giới hạn body/request, output guard | Test schema/stale/unavailable và API prediction bằng pipeline offline |
| TV5 | Kết nối API thật, định dạng tiền, chart từ report tổng hợp, responsive cơ bản | Form → kết quả → báo cáo không dùng số giả; mock tách khỏi production |
| TV6 | Review split và protocol; khóa candidate selection ngày 14; contract drift checks, viết cấu trúc báo cáo | Freeze record có hashes và reviewer; test chưa dùng chọn cấu hình |

## Tuần 3 — kiểm định độc lập và tích hợp

| Người | Việc cụ thể | Bàn giao |
| --- | --- | --- |
| TV1 | Cung cấp snapshot cập nhật theo data contract; báo shift/độ phủ và dữ liệu test mới chưa lộ | Refresh manifest và audit, không trộn các phiên bản |
| TV2 | Đóng gói đúng pipeline đã khóa, hỗ trợ TV6 tái lập; giải thích M1/M2 và sai số | Candidate artifact, config, model-card phương pháp |
| TV3 | Phân tích residual theo nhóm sau khi khóa; đối chiếu cây/linear/poly, kiểm tra robustness | Đồ thị có đơn vị/n; kết luận không nhân quả, không tune theo test |
| TV4 | Tích hợp approved artifact, lỗi và rate/concurrency; kiểm tra không lộ dữ liệu | Release smoke và security checks; không có write endpoints |
| TV5 | Hoàn thiện ngày dữ liệu, cảnh báo ngoài train range, stale và báo cáo lịch sử | Playwright luồng valid/error/stale, demo trên màn hình nhỏ |
| TV6 | Chạy test độc lập cuối theo protocol cho B0/M1/M2/M3; quyết định có phát hành; kiểm tra máy sạch | `reports/<run_id>/`, release checklist đã ký review; nếu fail chỉ công bố báo cáo |

## Tuần 4 — cập nhật gần ngày demo, báo cáo và diễn tập

| Người | Việc cụ thể | Bàn giao |
| --- | --- | --- |
| TV1 | Xác minh snapshot gần demo, tính còn rao và quyền dùng; chốt data card | Nguồn dữ liệu/manifest cuối, ngày dữ liệu thật |
| TV2 | Chạy lại pipeline đúng config đã duyệt; giải thích công thức OLS/poly; hỗ trợ tái lập | Lệnh train và dependency lock; không “tune lần cuối” bằng test |
| TV3 | Chốt biểu đồ so sánh, importance, case sai lớn; chuẩn bị trả lời vì sao không deep learning | Phần phân tích AI có cả hạn chế và kết quả kém |
| TV4 | Kiểm tra API với artifact cuối, khả năng rollback, local startup không phụ thuộc mạng | Release runbook và smoke evidence |
| TV5 | Chốt UI và demo kịch bản; video từ phiên bản thật, ghi ngày; không thêm tính năng | Demo có kết quả thật và lỗi minh bạch; slide UI ngắn |
| TV6 | Tái đánh giá refresh theo protocol; tổng hợp báo cáo/slide; diễn tập 2 lượt và đóng scope | Evidence bundle, tag/release nội bộ nếu đủ gate, người dự phòng chạy demo |

## Hướng dẫn bắt đầu cho từng người

**TV1:** Đọc research nguồn và data contract trước; không tải hàng loạt trước khi rõ quyền. Làm adapter từng nguồn, ghi fixture đơn vị/thuê/bán/time. Xuất CSV sạch + manifest + audit + split đề xuất. Không tự sửa nhãn giá để mô hình đẹp. Bàn giao cho TV2/TV3/TV6 qua snapshot version, không gửi “file cuối_v2_mới_nhất.csv”.

**TV2:** Đọc AI protocol, dùng fixture để thiết kế pipeline trước khi có data thật. Một interface chung `fit(X_train,y_train)` / `predict(X)`; tiền xử lý được serialize cùng model. Mọi số liệu phải có run ID. Chỉ dùng validation cho lựa chọn; hướng dẫn TV4 import package dùng chung, không chép preprocessing vào route.

**TV3:** Dùng đúng X/y và splits của TV2. Không tự loại outlier hoặc tạo split riêng cho cây. Plot importance trên cột gốc qua pipeline, kiểm tra biến tương quan, thêm ablation diện tích/vị trí. Bàn giao script tạo biểu đồ, không chỉ ảnh trong notebook. Hợp nhất interface với TV2 qua PR nhỏ.

**TV4:** Đọc data/API/security; triển khai validation và error envelope trước. Loader nạp duy nhất artifact đã duyệt; clock injectable để test stale. Phối hợp TV2 kiểm tra offline parity, TV5 kiểm tra response và TV6 kiểm tra release. Không mở retrain/upload để “tiện demo”.

**TV5:** Dùng metadata và generated client/types khi có; mock chỉ cho phát triển và ghi nhãn rõ. Không tự đặt giới hạn/đơn vị khác server, không lưu request có thông tin nhạy cảm. Trang kết quả nói “ước tính giá rao bán”, có ngày dữ liệu, giới hạn và trạng thái quá hạn. Nếu nhận 503 không hiện số giá từ mock hay cache cũ.

**TV6:** Tạo môi trường chung, bảo vệ test và giữ bản quyết định; review không thay owner triển khai. Chạy lại từ máy/môi trường khác, yêu cầu nguồn cho mọi biểu đồ và đối chiếu đề gốc. Chỉ mình giữ quyền phát hành chưa đủ: cần TV4 review release và một reviewer khác cho PR do TV6 viết.

## Luồng phụ thuộc và chống nghẽn

`TV1 source gate → TV1+TV6 frozen split → TV2/TV3 experiments → TV6 evaluation → TV4 serving → TV5 demo`. TV4/TV5 làm song song trên contract từ ngày 1; TV6 chuẩn bị tests/integration từ đầu. Không để TV5 đợi model mới viết form hoặc TV4 tự đoán schema.

Mỗi ngày làm việc cập nhật task: done / next / blocker kèm link PR/run. Họp tích hợp 20 phút hai lần/tuần; review trong một ngày làm việc. Không merge hai người sửa `features.py`/API schema cùng lúc mà chưa thống nhất owner. Nếu owner vắng, reviewer dự phòng tiếp nhận bằng task và thông báo nhóm.

## Backlog tối thiểu

| Task | Owner | Phụ thuộc | Definition of Done |
| --- | --- | --- | --- |
| P01 Nguồn, quyền, freshness, audit | TV1 | Không | GO/NO-GO ngày 3 có evidence |
| P02 Clean/group/split/manifest | TV1 + TV6 duyệt | P01 | Data contract pass, group/time assertions, hashes |
| P03 Shared features và B0/M1 | TV2 | Fixture trước; P02 để đo thật | Pipeline + train-only preprocessing test |
| P04 Polynomial comparison | TV2 | P03 | Cấu hình theo protocol, validation report |
| P05 Tree và explanation | TV3 | P02/P03 interface | Cùng split, tuning budget, importance/ablation |
| P06 API contract và serving | TV4 | Fixture trước; candidate để parity | Strict validation, errors, freshness/output guards |
| P07 Form và kết quả | TV5 | API contract | Mock có nhãn + API thật + states |
| P08 Báo cáo web | TV5 | Report contract; P10 cho số thật | Không tính metric bằng mock hoặc raw |
| P09 Contract/CI/environment checks | TV6 | Không | Lock môi trường, schema parity, checks chạy được |
| P10 Independent evaluation — [issue #3: bảo vệ holdout](https://github.com/KhiemPham1512/hcm-apartment-price-ai/issues/3) | TV6 | Fixture trước; P03/P04/P05 freeze để đo thật | B0/M1/M2/M3 test, artifact evidence |
| P11 Security/integration release | TV4 + TV6 | P06/P07/P10 | Release gates và reviewer pass |
| P12 Refresh/demo/report | Cả nhóm, TV6 điều phối | P01–P11 | Độ mới kiểm tra lại, báo cáo/diễn tập, giới hạn công bố |

Đây là danh mục phân công; khi nhận việc tạo GitHub Issue theo [quy ước](../AGENTS.md), link mã Pxx ở đây, không sao chép hợp đồng. Tiến độ, blocker, phạm vi file đang giữ và PR liên quan nằm trên issue. Trước khi AI nhận việc, thành viên xác định TV nào và issue nào; không giao cả backlog như một ticket.


## Phong cách GitHub và quyền sửa file

Nguồn chuẩn quy tắc là [AGENTS.md](../AGENTS.md). Áp dụng trunk-based: `main` là nhánh tích hợp duy nhất, không thêm `develop` trong 4 tuần. Một issue/một owner/một nhánh ngắn hạn; mở draft PR sớm để cả nhóm biết file nào đang được sửa. Sau bootstrap không làm trực tiếp trên main.

| Người | Prefix nhánh | File chung phải phối hợp |
| --- | --- | --- |
| TV1 | `feat/<issue>-data-*` | Schema thay đổi phải có TV2+TV4 review |
| TV2 | `feat/<issue>-ml-*` | Shared preprocessing do TV2 giữ; TV3 import, không copy |
| TV3 | `feat/<issue>-tree-*` | Interface model thống nhất với TV2, không tự đổi split |
| TV4 | `feat/<issue>-api-*` | API thay đổi cần TV5 review consumer |
| TV5 | `feat/<issue>-web-*` | Không sửa schema/model để khớp UI một chiều |
| TV6 | `chore/<issue>-infra-*` hoặc `docs/<issue>-*` | Root config/README/CI do TV6 điều phối; không sửa thay tất cả owner |

Trước bắt đầu fetch và tạo nhánh từ origin/main; trước PR fetch rồi merge origin/main vào nhánh mình, giải conflict theo cả hai thay đổi và chạy kiểm tra. Không force-push nhánh chia sẻ, không nhận nguyên ours/theirs để bỏ xung đột. Không format cả repo trong PR tính năng.

PR cần một reviewer khác tác giả; đổi interface cần cả producer và consumer. CI xanh mới squash merge. Nếu protection chưa bật được, ghi rõ là quy ước vận hành chưa được GitHub cưỡng chế. Chưa biết username của 6 người thì TV1–TV6 là mã vai trò, không bịa assignee/reviewer.

TEAM giữ phân công/mốc; GitHub Issue giữ status/trao đổi/PR. Trong lúc repo chưa khả dụng, đánh dấu tiến độ ngay ở backlog phía trên, không tạo thêm tracker/file ghi chú. Đóng issue chỉ khi có code, kiểm tra và evidence; tài liệu thiết kế không đồng nghĩa tính năng đã xong.
