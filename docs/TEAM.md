# Phân công 6 người trong 4 tuần

Owner điều phối: TV6. Kế hoạch giả định **12 giờ/người/tuần**, 48 giờ/người, tổng 288 giờ; chưa phải cam kết thời gian thực của từng thành viên. Ngày 1 thay TV1–TV6 bằng tên và xác nhận quỹ giờ. Nếu thiếu giờ, cắt trang trí/UI phụ và thí nghiệm mở rộng trước; giữ ba mô hình, dữ liệu, test độc lập.

Lịch tính từ 04/11/2026: tuần 1 ngày 04–10/11, tuần 2 ngày 11–17/11, tuần 3 ngày 18–24/11, tuần 4 ngày 25/11–01/12. Nếu bắt đầu khác ngày, dời lịch tại **file này**; ngày 1/3/7/14/21/28 trong spec là mốc tương đối.

Phạm vi chung: căn hộ tại TP.HCM theo địa giới hiện hành và giá rao gần thời điểm snapshot, theo [SPEC](SPEC.md). TV1 bàn giao danh mục khu vực có nguồn/version; mọi thành viên dùng cùng danh mục và hợp đồng trong README, không tự lọc về phạm vi địa lý cũ.

<a id="checklist"></a>
## Checklist tiến độ của từng thành viên

**Nguồn tiến độ để người và AI đọc trực tiếp là các ô trong file này.** Không cần truy cập GitHub để biết mục nào đã đánh dấu xong. Cập nhật nền ngày 04/11/2026 theo code và PR đã kiểm chứng; các mục chưa tick cần owner rà soát, không hàm ý mọi code nền đều chưa có. Tiến độ chỉ đúng với commit/nhánh đang đọc: AI cần kiểm tra `git status` và đồng bộ theo quy trình trước khi tiếp tục.

**Cách cập nhật:** làm xong thì đổi `- [ ]` thành `- [x]` trong đúng mục của mình, thêm bằng chứng ngắn (PR đã merge, lệnh/run hoặc review), cập nhật “Bước tiếp / Chặn”, rồi commit cùng thay đổi liên quan qua PR. Giữ mã nhiệm vụ ổn định để AI đối chiếu. Với PR chưa merge, giữ ô phần tích hợp trống và ghi link PR đang chờ; không tick việc thị trường chỉ vì test fixture pass.

**AI tiếp nhận:** đọc mục vai trò → tìm ô chưa tick đầu tiên đáp ứng phụ thuộc → đọc evidence/issue/code tương ứng → triển khai một lát cắt. Nếu code đã có nhưng chưa nghiệm thu thì kiểm tra lại thay vì viết lại. GitHub Issues giữ thảo luận và status từng ticket; không duy trì thêm checklist vai trò trên issue. Các tracker #9–#14 được thay bằng checklist Markdown này.

Đi tới: [TV1](#checklist-tv1) · [TV2](#checklist-tv2) · [TV3](#checklist-tv3) · [TV4](#checklist-tv4) · [TV5](#checklist-tv5) · [TV6](#checklist-tv6)

<a id="checklist-tv1"></a>
### TV1 — Dữ liệu và nguồn

**Bước tiếp / Chặn:** Xác minh nguồn/quyền dùng và quyết định GO/NO-GO cùng TV6. Chưa có dataset/mapping thị trường được duyệt trong repo.

#### Tuần 1

- [ ] **TV1-01** Xác minh nguồn/quyền dùng và ghi evidence, revision, thời điểm giá/active, phạm vi TP.HCM hiện hành (P01).
- [ ] **TV1-02** Chốt mapping khu vực có nguồn, ngày hiệu lực, version/hash; đối chiếu schema cùng TV2/TV4.
- [ ] **TV1-03** Chuẩn hóa CSV/card, audit bán/thuê/đơn vị/timestamps và thống kê mẫu; bàn giao GO/NO-GO ngày 3 cho TV6.

#### Tuần 2

- [ ] **TV1-04** Hoàn thiện grouping từ dữ liệu thô, audit nhóm nghi trùng và chọn đại diện (P02).
- [ ] **TV1-05** Bàn giao split đề xuất, seed/hash và kiểm tra nhóm rời cho TV6; không đưa nhãn test lên GitHub.
- [ ] **TV1-06** Bàn giao snapshot/card bất biến cho TV2/TV3; báo missingness, khu vực thiếu nhóm và tập trung dự án.

#### Tuần 3

- [ ] **TV1-07** Bàn giao snapshot refresh và thống kê shift/độ phủ; ghi rõ ngày quan sát giá và active evidence.
- [ ] **TV1-08** Cùng TV6 rà soát lịch sử nhóm đã dùng fit/tune/test để chuẩn bị test phát hành mới.

#### Tuần 4

- [ ] **TV1-09** Xác minh lại quyền dùng, mapping, độ mới và còn rao gần ngày demo.
- [ ] **TV1-10** Chốt dataset card/audit cuối, viết phần nguồn và dữ liệu trong báo cáo; reviewer xác nhận bàn giao.

<a id="checklist-tv2"></a>
### TV2 — Shared features, Linear và Polynomial

**Bước tiếp / Chặn:** Rà soát code nền và nhận snapshot/card/split đã duyệt; fixture chỉ dùng kiểm thử kỹ thuật.

#### Tuần 1

- [ ] **TV2-01** Rà soát và bàn giao shared feature pipeline; loại nhãn/ID/giá suy từ nhãn khỏi X, optional null đúng contract (P03).
- [ ] **TV2-02** Kiểm tra preprocessing chỉ fit train; baseline median và Linear fit/predict qua cùng interface.
- [ ] **TV2-03** Chạy CSV sạch → candidate bằng lệnh tái lập, ghi config/seed/hash và kết quả validation; fixture không gọi là dữ liệu thị trường.

#### Tuần 2

- [ ] **TV2-04** Hoàn thiện Polynomial bậc 2 và ngân sách cấu hình theo protocol (P04).
- [ ] **TV2-05** So baseline/Linear/Polynomial/Tree trên cùng split; chỉ chọn cấu hình/winner bằng validation.
- [ ] **TV2-06** Khóa feature set/config/candidate cùng TV6 trước khi mở test; bàn giao phiên bản môi trường và artifact hashes.

#### Tuần 3

- [ ] **TV2-07** Bàn giao đúng pipeline đã khóa cho TV6 đánh giá; không refit rồi dùng metric cũ.
- [ ] **TV2-08** Cùng TV4 kiểm tra inference qua package chung và parity offline/HTTP, không sao chép preprocessing.

#### Tuần 4

- [ ] **TV2-09** Chạy lại quy trình refresh đúng cấu hình được duyệt, giữ lịch sử từng run.
- [ ] **TV2-10** Viết phần Linear/Polynomial, công thức, kết quả và giới hạn; bàn giao lệnh chạy lại được reviewer xác nhận.

<a id="checklist-tv3"></a>
### TV3 — Decision Tree và giải thích

**Bước tiếp / Chặn:** Chốt interface và kế hoạch importance với TV2; số liệu thị trường chờ dữ liệu được duyệt.

#### Tuần 1

- [ ] **TV3-01** Cùng TV1 kiểm tra EDA, độ phủ và tập trung dự án; biểu đồ có n/kỳ/đơn vị.
- [ ] **TV3-02** Thống nhất interface cây với TV2, chạy Decision Tree ban đầu trên fixture đúng contract.
- [ ] **TV3-03** Chốt kế hoạch tuning, importance và ablation trước khi xem test.

#### Tuần 2

- [ ] **TV3-04** Tuning cây trong ngân sách đã chốt, giữ cùng split và feature set với các mô hình khác.
- [ ] **TV3-05** Chạy permutation importance trên cột gốc và ablation diện tích/vị trí trên validation.
- [ ] **TV3-06** Bàn giao config cây đã khóa, log validation, script/figures tái lập và giới hạn tương quan.

#### Tuần 3

- [ ] **TV3-07** Sau freeze, phân tích residual/lỗi theo nhóm bằng kết quả TV6 cho phép; không chọn lại mô hình theo test.
- [ ] **TV3-08** Đối chiếu độ phức tạp/overfit và robustness giữa ba mô hình; nêu cả kết quả yếu.

#### Tuần 4

- [ ] **TV3-09** Chốt biểu đồ so sánh/importance/case sai lớn gắn run/hash và đơn vị.
- [ ] **TV3-10** Viết phần cây/giải thích, chuẩn bị trả lời giới hạn và bàn giao được TV2 + TV6 review.

<a id="checklist-tv4"></a>
### TV4 — Backend và serving

**Bước tiếp / Chặn:** Rà soát contract với TV5; test kỹ thuật đã có, serving thị trường chờ artifact approved.

#### Tuần 1

- [ ] **TV4-01** Rà soát API/OpenAPI, metadata-driven schema và envelope lỗi; bàn giao request/response mẫu cho TV5 (P06).
- [ ] **TV4-02** Kiểm tra strict input/null/bounds/field lạ và khu vực không hỗ trợ.
- [ ] **TV4-03** Bàn giao live/ready/metadata/predictions/report với trường hợp thiếu model, không có fallback giá giả.

#### Tuần 2

- [ ] **TV4-04** Kiểm tra trusted loader, checksum/manifest, candidate/synthetic bị chặn khi phục vụ thị trường.
- [ ] **TV4-05** Cùng TV2/TV6 kiểm tra parity offline/HTTP và output âm/NaN/Inf.
- [ ] **TV4-06** Kiểm tra stale/biên freshness bằng clock inject, metadata vẫn xem được khi stale.

#### Tuần 3

- [ ] **TV4-07** Hoàn thiện và đo giới hạn public: body/rate/concurrency/timeout, CORS/proxy và lỗi 429; không tuyên bố đã có trước khi kiểm chứng.
- [ ] **TV4-08** Review bảo mật: không upload/retrain/raw/model-download, không log PII/secrets; cùng TV6 kiểm tra release gates (P11).

#### Tuần 4

- [ ] **TV4-09** Smoke artifact cuối, ngày dữ liệu và rollback chỉ tới model còn hợp lệ.
- [ ] **TV4-10** Bàn giao local startup/runbook và phần API trong báo cáo; nếu deploy, ghi URL/commit và bằng chứng smoke thực.

<a id="checklist-tv5"></a>
### TV5 — Frontend và demo

**Bước tiếp / Chặn:** Nhận contract/metadata từ TV4, bắt đầu form và các trạng thái bằng mock có nhãn rõ; hiện chưa có frontend.

#### Tuần 1

- [ ] **TV5-01** Nhận metadata/OpenAPI và mẫu lỗi từ TV4; chốt form/kết quả/report tối thiểu.
- [ ] **TV5-02** Dựng form theo metadata, optional null đúng nghĩa, khu vực lấy từ API (P07).
- [ ] **TV5-03** Làm loading/empty/error/unavailable với mock ghi nhãn rõ và một request API thật.

#### Tuần 2

- [ ] **TV5-04** Nối predictions thật; hiển thị tổng giá VND, đơn giá/m², ngày dữ liệu, area basis và warnings.
- [ ] **TV5-05** Xử lý 422/503/stale/mạng lỗi; không hiện giá từ mock/cache khi server từ chối.
- [ ] **TV5-06** Nối report tổng hợp gồm baseline + ba mô hình, metric đúng đơn vị/n; không tính metric từ raw (P08).

#### Tuần 3

- [ ] **TV5-07** Kiểm tra màn hình nhỏ, khả năng dùng form và thông báo lỗi.
- [ ] **TV5-08** Viết/chạy Playwright smoke valid/invalid/unavailable/stale cùng TV4/TV6, lưu evidence gắn phiên bản.

#### Tuần 4

- [ ] **TV5-09** Chốt demo theo artifact/report cuối; công bố rõ giới hạn và phần chưa đủ điều kiện.
- [ ] **TV5-10** Bàn giao hướng dẫn UI, ảnh/video có ngày/model và phần frontend trong báo cáo; diễn tập cùng TV6.

<a id="checklist-tv6"></a>
### TV6 — Tích hợp, kiểm định và phát hành

**Bước tiếp / Chặn:** Bản khóa candidate đã merge qua [PR #19](https://github.com/KhiemPham1512/hcm-apartment-price-ai/pull/19). Đang kiểm tra contract schema/features trước đọc holdout theo [issue #20](https://github.com/KhiemPham1512/hcm-apartment-price-ai/issues/20), TDD qua CLI freeze/evaluate đã được chủ repo xác nhận. Cổng dữ liệu, rubric/quỹ giờ và đánh giá thị trường vẫn chờ bàn giao thực tế; chưa tick nghiệm thu TV6-04/05/06/07. Registry lịch sử tiếp xúc dữ liệu vẫn chưa có.

#### Tuần 1

- [ ] **TV6-01** Xác nhận rubric, tên/quỹ giờ của 6 người, lịch và issue triển khai; không bịa GitHub username.
- [x] **TV6-02** Checklist Markdown cho AI đã tích hợp qua [PR #17](https://github.com/KhiemPham1512/hcm-apartment-price-ai/pull/17), CI xanh.
- [x] **TV6-03** P09 đã review/merge: cài môi trường sạch, smoke package ngoài repo, parity schema, pytest/Ruff/pip check và CI — [PR #8](https://github.com/KhiemPham1512/hcm-apartment-price-ai/pull/8), 58 test pass; chỉ là kiểm chứng kỹ thuật.
- [ ] **TV6-04** Cùng TV1 review nguồn/card/mapping/audit và ghi quyết định GO/NO-GO.

#### Tuần 2

- [ ] **TV6-05** Kiểm tra baseline + ba mô hình cùng split, nhóm rời, hashes và protocol. Guard contract schema/features đang triển khai ở [issue #20](https://github.com/KhiemPham1512/hcm-apartment-price-ai/issues/20); chưa có candidate thị trường để nghiệm thu toàn mục.
- [ ] **TV6-06** Review freeze candidate/config/winner trước khi mở test; giữ lịch sử tiếp xúc dữ liệu. Cơ chế bản khóa kỹ thuật đã merge qua [PR #19](https://github.com/KhiemPham1512/hcm-apartment-price-ai/pull/19); chưa phải review candidate thị trường hay registry đầy đủ.

#### Tuần 3

- [ ] **TV6-07** Chạy đánh giá độc lập B0/M1/M2/M3 từ candidate freeze, metric đúng đơn vị/n/run/hash (P10).
- [ ] **TV6-08** Cùng TV4 kiểm tra parity offline/HTTP, model thiếu/chưa duyệt/quá hạn và security/release gates (P11).
- [ ] **TV6-09** Hoàn thiện release/registry và reviewer độc lập; chỉ duyệt khi đủ gate, không tự duyệt PR của mình.

#### Tuần 4

- [ ] **TV6-10** Kiểm tra snapshot/test mới chưa lộ khi refresh và freshness gần demo; quyết định có phát hành.
- [ ] **TV6-11** Tổng hợp báo cáo/slide/evidence; cùng nhóm diễn tập hai lượt có tình huống lỗi và người dự phòng (P12).
- [ ] **TV6-12** Chốt gói nộp code/lock/config/báo cáo/video gắn phiên bản, ghi chính xác các giới hạn và blocker.

#### Nền kỹ thuật đã kiểm chứng

- [x] **TV6-13** Guard P10 từ chối candidate thiếu mô hình, winner/split/holdout sai; đã merge [PR #4](https://github.com/KhiemPham1512/hcm-apartment-price-ai/pull/4). Phần đánh giá thị trường độc lập ở TV6-07 vẫn chưa hoàn tất.

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

### 48 giờ đầu: làm gì trước, ai kiểm tra?

| Thứ tự | Người làm | Hoàn tất khi |
| --- | --- | --- |
| Ngày 1: chốt phạm vi và nhận việc | Cả nhóm, TV6 điều phối | Đối chiếu rubric, điền tên/quỹ giờ thực vào TEAM; mỗi người có issue và phạm vi file |
| Ngày 1: dựng môi trường | Mỗi người, TV6 hỗ trợ P09 | Cài theo README, pytest/Ruff/pip check; API live và metadata xem được |
| Ngày 1–2: thử điểm rủi ro | TV1 nguồn; TV2/TV3 pipeline; TV4/TV5 contract | TV1 đưa evidence hoặc blocker; các owner còn lại chạy fixture có nhãn rõ, không chờ dữ liệu để kiểm tra interface |
| Cuối ngày 2: tích hợp ngắn | TV6 cùng các owner | Một máy khác chạy lại lệnh bàn giao; ghi lỗi/owner trên issue, chuẩn bị gate dữ liệu ngày 3 |

Mốc này là hướng dẫn thực hiện, không phải báo cáo các việc đã xong. Vướng một lỗi quá một giờ làm việc thì ghi lệnh tái hiện, kết quả mong đợi/thực tế và nhờ reviewer dự phòng trên issue; không gửi dữ liệu riêng hoặc secrets.

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

### Bàn giao tối thiểu giữa các owner

| Bên giao → bên nhận | Gói cần nhận | Bên nhận kiểm tra |
| --- | --- | --- |
| TV1 → TV2/TV3/TV6 | CSV/card, quyền dùng, mapping version/hash và audit trong kho nội bộ | Schema/đơn vị/freshness, nhóm trùng và GO/NO-GO |
| TV2/TV3 → TV6 | Candidate, split/config/hash, validation và lệnh tái lập | Đủ baseline + ba mô hình; freeze trước test, không refit rồi giữ metric cũ |
| TV6 → TV4 | Báo cáo test và gói approved sau review theo README | Đúng hash/schema/model, parity offline/HTTP và stale/unavailable |
| TV4 → TV5 | OpenAPI/metadata, request/response/error mẫu đúng phiên bản | Cùng field/đơn vị; UI không hardcode khu vực và không fallback giá giả |
| TV5 + các owner → TV6 | Demo, hướng dẫn chạy và evidence PR/CI | Máy khác chạy lại được, thiếu mạng/model có thông báo đúng; diễn tập trước nộp |

Mỗi bàn giao ghi commit/run, lệnh chạy, kết quả và blocker trên issue/PR. “Code đã viết”, “test local đạt”, “CI đạt” và “đã deploy được xác minh” là các mức bằng chứng khác nhau. Gói dữ liệu/model riêng không đính vào issue public.

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
| P09 Contract/CI/environment checks — [issue #7](https://github.com/KhiemPham1512/hcm-apartment-price-ai/issues/7) | TV6 | Không | Cài package từ môi trường sạch, smoke ngoài repo, schema parity, pytest/Ruff/pip check và CI |
| P10 Independent evaluation — [issue #3: bảo vệ holdout](https://github.com/KhiemPham1512/hcm-apartment-price-ai/issues/3) | TV6 | Fixture trước; P03/P04/P05 freeze để đo thật | B0/M1/M2/M3 test, artifact evidence |
| P11 Security/integration release | TV4 + TV6 | P06/P07/P10 | Release gates và reviewer pass |
| P12 Refresh/demo/report | Cả nhóm, TV6 điều phối | P01–P11 | Độ mới kiểm tra lại, báo cáo/diễn tập, giới hạn công bố |

Đây là danh mục phân công; khi nhận việc tạo GitHub Issue theo [quy ước](../AGENTS.md), link mã Pxx ở đây, không sao chép hợp đồng. Checklist nghiệm thu và bước tiếp/blocker theo vai trò nằm ở [đầu file](#checklist); issue giữ chi tiết ticket, phạm vi file đang giữ và PR liên quan. Trước khi AI nhận việc, thành viên xác định TV nào và issue nào; không giao cả backlog như một ticket.


<a id="github-workflow"></a>
## Làm việc trên GitHub: nhánh riêng → Pull Request → review → merge

Nguồn chuẩn quy tắc là [AGENTS.md](../AGENTS.md). **Không commit công việc trực tiếp trên `main`, không chạy `git push origin main` và không force-push.** `main` chỉ nhận thay đổi qua PR được review. Đây là quy tắc làm việc của nhóm; chưa xác minh GitHub branch protection đã cưỡng chế nó.

**1. Nhận issue và chốt phạm vi.** Một issue, một owner triển khai, một nhánh. Ghi vai trò TV, yêu cầu, file sẽ sửa và phụ thuộc trên issue; kiểm tra PR đang mở để tránh hai người cùng sửa file chung. Chưa có issue thì tạo issue trước, không bắt đầu bằng việc sửa tất cả backlog.

**2. Tạo nhánh từ bản `main` mới nhất.** Chạy tại root repo. Ví dụ dùng issue #123 và nhánh `feat/123-ten-viec`; thay số và tên theo công việc thật. Dùng `fix/`, `docs/` hoặc `chore/` nếu phù hợp.

```powershell
git status
git fetch origin
git switch -c feat/123-ten-viec origin/main
```

`git status` phải sạch trước khi chuyển sang việc khác. Nếu còn thay đổi, hoàn tất trên nhánh đang làm hoặc phối hợp owner; không dùng reset/clean để bỏ qua. Không cần tự merge local `main` trước khi tạo nhánh từ `origin/main`.

**3. Làm việc và kiểm tra.** AI đọc tài liệu + issue + code/test liên quan theo [README](../README.md). Với tính năng, làm RED → GREEN; giữ test nghiệp vụ trong `tests/`, dọn test tạm/cache, không tạo thư mục root mới. Kiểm tra trước commit:

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
git diff --check
git status
```

**4. Commit và push nhánh riêng.** Stage đúng file của issue, đọc diff đã stage, không đưa dữ liệu, nhãn holdout, model binary hay secrets vào Git. Ví dụ dưới stage một file; thay đường dẫn và thông điệp theo thay đổi thật.

```powershell
git add ml/evaluate.py
git diff --cached
git commit -m "fix: validate frozen evaluation inputs"
git push -u origin feat/123-ten-viec
```

**5. Mở draft Pull Request sớm.** Trên GitHub chọn **base: main**, **compare: nhánh của bạn**, bấm **Create draft pull request**. Hoặc dùng GitHub CLI sau khi đăng nhập `gh auth login`:

```powershell
gh pr create --base main --head feat/123-ten-viec --draft --fill
```

Sửa mô tả PR để có vấn đề đã giải quyết, file đang giữ, bằng chứng test và `Closes #123`. Draft cho nhóm biết phạm vi đang làm; chưa coi đó là công việc đã hoàn tất. Commit/push tiếp trên cùng nhánh sẽ cập nhật cùng PR, không tạo PR mới cho mỗi commit.

**6. Đồng bộ trước review cuối.** Đứng trên nhánh cá nhân, cập nhật `main` bằng merge, không rewrite lịch sử:

```powershell
git fetch origin
git merge origin/main
```

Nếu conflict, đọc cả hai thay đổi và phối hợp owner, sửa đúng ý nghĩa rồi `git add` các file đã giải quyết và `git commit` để kết thúc merge. Không nhận hàng loạt ours/theirs. Chạy lại test phần giao, rồi `git push` nhánh hiện tại.

**7. Review và merge PR.** Khi hoàn tất, chuyển draft sang **Ready for review**. Cần CI xanh và ít nhất một reviewer khác tác giả; đổi interface cần producer và consumer review. Người có quyền merge chọn **Squash and merge** trên GitHub sau review; không thay bước này bằng push local lên `main`. Khi PR đã merge, issue liên kết được đóng; PR còn mở thì chưa phải bản tích hợp.

**8. Nhận việc kế tiếp.** Kiểm tra working tree sạch, `git fetch origin`, rồi tạo nhánh mới từ `origin/main` như bước 2. Không tiếp tục làm việc mới trên nhánh PR cũ đã merge. Đọc và cập nhật checklist Markdown của vai trò trong TEAM; chi tiết từng ticket tiếp tục ở issue/PR.

### Quyền sửa file chung

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

TEAM giữ phân công/mốc và checklist nghiệm thu theo thành viên; GitHub Issue giữ status/trao đổi/PR của từng ticket triển khai. Không tạo bản checklist vai trò hoặc file ghi chú có trạng thái khác. Đóng issue triển khai khi kết quả đã được kiểm tra và tích hợp qua PR; tài liệu thiết kế không đồng nghĩa tính năng đã xong.
