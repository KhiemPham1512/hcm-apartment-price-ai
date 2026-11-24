**XÂY DỰNG VÀ ĐÁNH GIÁ MÔ HÌNH LINEAR REGRESSION VÀ POLYNOMIAL REGRESSION**

**1. Mô hình Linear Regression (M1)**

**1.1. Cơ sở lý thuyết**

Linear Regression (hồi quy tuyến tính) là thuật toán học máy có giám sát được sử dụng để dự đoán biến mục tiêu liên tục dựa trên mối quan hệ tuyến tính giữa các đặc trưng đầu vào.

Trong đề tài, Linear Regression được sử dụng để ước tính giá rao bán căn hộ tại Thành phố Hồ Chí Minh dựa trên các đặc trưng của bất động sản.

Phương trình tổng quát của mô hình:

ŷ = β₀ + β₁x₁ + β₂x₂ + ... + βₙxₙ

Trong đó:

\- ŷ: Giá rao bán căn hộ dự đoán.

\- β₀: Hệ số chặn.

\- βᵢ: Hệ số hồi quy của đặc trưng thứ i.

\- xᵢ: Giá trị đặc trưng đầu vào.

\- n: Số lượng đặc trưng.

Mô hình sử dụng phương pháp bình phương tối thiểu (Ordinary Least Squares – OLS) để xác định các hệ số hồi quy sao cho tổng bình phương sai số giữa giá trị thực tế và giá trị dự đoán đạt giá trị nhỏ nhất.

**1.2. Triển khai mô hình**

Linear Regression được triển khai bằng thư viện Scikit-learn, kết hợp với Pipeline và ColumnTransformer để thống nhất quá trình tiền xử lý và huấn luyện.

Quy trình xử lý bao gồm:

\- Sử dụng SimpleImputer với chiến lược median để xử lý giá trị thiếu của các đặc trưng số.

\- Sử dụng StandardScaler để chuẩn hóa đặc trưng số.

\- Sử dụng OneHotEncoder để mã hóa đặc trưng khu vực.

\- Kết hợp các đặc trưng đã xử lý và huấn luyện bằng LinearRegression.

Ưu điểm của Linear Regression là cấu trúc đơn giản, dễ triển khai và chi phí tính toán tương đối thấp. Tuy nhiên, mô hình có khả năng biểu diễn hạn chế đối với các mối quan hệ phi tuyến và không có ràng buộc đảm bảo giá dự đoán luôn dương.

**2. Mô hình Polynomial Regression (M2)**

**2.1. Cơ sở lý thuyết**

Polynomial Regression (hồi quy đa thức) là phương pháp mở rộng Linear Regression bằng cách bổ sung các thành phần đa thức của đặc trưng đầu vào nhằm tăng khả năng biểu diễn các mối quan hệ phi tuyến.

Phương trình hồi quy đa thức bậc hai đối với một biến độc lập:

ŷ = β₀ + β₁x + β₂x²

Đối với nhiều biến độc lập, mô hình có thể bổ sung bình phương của từng đặc trưng và tích giữa các cặp đặc trưng.

Ví dụ, với hai đặc trưng số x₁ và x₂, phép biến đổi đa thức bậc hai tạo ra tập đặc trưng:

\[x₁, x₂, x₁², x₁x₂, x₂²\]

Việc bổ sung các thành phần đa thức giúp mô hình có khả năng biểu diễn những mối quan hệ phức tạp hơn so với Linear Regression thông thường.

**2.2. Triển khai mô hình**

Trong đề tài, Polynomial Regression được triển khai với bậc đa thức bằng 2 thông qua cấu hình:

PolynomialFeatures(

degree=2,

include_bias=False

)

Quy trình tiền xử lý đặc trưng số được thực hiện theo thứ tự:

SimpleImputer → PolynomialFeatures → StandardScaler.

Đặc trưng khu vực được mã hóa riêng bằng OneHotEncoder. Sau đó, các đặc trưng được kết hợp và đưa vào LinearRegression để thực hiện huấn luyện.

Mặc dù Polynomial Regression có khả năng biểu diễn quan hệ phi tuyến theo các biến đầu vào, thuật toán ước lượng cuối cùng vẫn là Linear Regression. Do đó, mô hình vẫn tồn tại hạn chế về khả năng đảm bảo đầu ra dương.

**3. Kết quả đánh giá thực nghiệm**

**3.1. Dữ liệu và phương pháp đánh giá**

Kết quả thực nghiệm được sử dụng từ lần đánh giá chính thức run-001, công bố ngày 24/11/2026.

Bộ dữ liệu TiniX, revision ca3fedc, gồm 203.537 dòng sau xử lý, tương ứng với 37.172 nhóm bất động sản.

Dữ liệu được phân chia theo nhóm bất động sản nhằm hạn chế hiện tượng rò rỉ dữ liệu giữa các tập huấn luyện và kiểm thử.

**Bảng 1. Phân chia dữ liệu run-001**

| **Tập dữ liệu** | **Số nhóm** | **Tỷ lệ** |
|-----------------|-------------|-----------|
| Training        | 26.020      | 70%       |
| Validation      | 5.576       | 15%       |
| Testing         | 5.576       | 15%       |
| Tổng cộng       | 37.172      | 100%      |

*Nguồn: reports/run-001/selection.json.*

Các mô hình được so sánh thông qua ba chỉ số chính:

\- RMSE: Căn bậc hai của trung bình bình phương sai số, nhạy cảm với các sai số lớn.

\- MAE: Trung bình sai số tuyệt đối giữa giá thực tế và giá dự đoán.

\- R²: Hệ số xác định, phản ánh mức độ biến thiên của biến mục tiêu được giải thích bởi mô hình.

Ngoài ra, hệ thống ghi nhận số lượng dự đoán không hợp lệ, cụ thể là các trường hợp giá dự đoán nhỏ hơn hoặc bằng 0.

**3.2. Kết quả trên tập Validation**

**Bảng 2. Kết quả đánh giá trên tập Validation**

| **Chỉ số**      | **M1 – Linear** | **M2 – Polynomial** |
|-----------------|-----------------|---------------------|
| RMSE (tỷ đồng)  | 8,511           | 8,431               |
| MAE (tỷ đồng)   | 4,226           | 4,154               |
| R²              | 0,5442          | 0,5528              |
| Dự đoán ≤ 0     | 220             | 188                 |
| Số mẫu đánh giá | 5.576           | 5.576               |

*Nguồn: reports/run-001/selection.json.*

Kết quả cho thấy Polynomial Regression đạt RMSE khoảng 8,43 tỷ đồng, thấp hơn Linear Regression với RMSE khoảng 8,51 tỷ đồng.

Tuy nhiên, mức cải thiện tương đối nhỏ. Trong quá trình lựa chọn mô hình, Decision Tree đạt RMSE validation thấp nhất, khoảng 6,90 tỷ đồng, nên được lựa chọn trước khi thực hiện đánh giá trên tập Test.

**3.3. Kết quả trên tập Test**

**Bảng 3. Kết quả đánh giá chính thức run-001**

| **Chỉ số**      | **M1 – Linear** | **M2 – Polynomial** |
|-----------------|-----------------|---------------------|
| RMSE (tỷ đồng)  | 7,8893          | 7,8706              |
| MAE (tỷ đồng)   | 4,1320          | 4,0713              |
| R²              | 0,5562          | 0,5583              |
| Dự đoán ≤ 0     | 280             | 242                 |
| Số mẫu đánh giá | 5.576           | 5.576               |

*Nguồn: reports/run-001/evaluation.json.*

Linear Regression đạt RMSE khoảng 7,89 tỷ đồng và MAE khoảng 4,13 tỷ đồng. Trong khi đó, Polynomial Regression đạt RMSE khoảng 7,87 tỷ đồng và MAE khoảng 4,07 tỷ đồng.

Hệ số xác định R² của cả hai mô hình đều xấp xỉ 0,56, cho thấy hai mô hình giải thích được khoảng 56% mức độ biến thiên của giá rao bán trên tập Test.

Tuy nhiên, R² bằng 0,56 không có nghĩa là mô hình dự đoán chính xác 56%. Các chỉ số RMSE và MAE cho thấy sai số dự đoán của hai mô hình vẫn còn lớn.

**3.4. Khoảng tin cậy Bootstrap 95%**

Hệ thống sử dụng phương pháp Percentile Bootstrap với 1.000 lần lấy mẫu lại theo nhóm bất động sản và random seed bằng 42 để đánh giá mức độ bất định của các chỉ số sai số.

**Bảng 4. Khoảng tin cậy Bootstrap 95% trên tập Test**

| **Chỉ số**     | **M1 – Linear** | **M2 – Polynomial** |
|----------------|-----------------|---------------------|
| RMSE (tỷ đồng) | 7,21–8,65       | 7,23–8,61           |
| MAE (tỷ đồng)  | 3,98–4,33       | 3,91–4,26           |

*Nguồn: trường bootstrap trong reports/run-001/evaluation.json.*

Khoảng tin cậy của hai mô hình chồng lấn đáng kể. Kết hợp với mức chênh lệch RMSE nhỏ, kết quả chưa cung cấp đủ bằng chứng để khẳng định Polynomial Regression vượt trội rõ rệt so với Linear Regression.

Tuy nhiên, sự chồng lấn khoảng tin cậy không thay thế cho kiểm định thống kê trực tiếp về chênh lệch hiệu năng giữa hai mô hình.

**4. Phân tích nguyên nhân xuất hiện dự đoán nhỏ hơn hoặc bằng 0**

Theo kết quả đánh giá chính thức run-001, Linear Regression có 280 trường hợp dự đoán giá nhỏ hơn hoặc bằng 0, trong khi Polynomial Regression có 242 trường hợp.

**Bảng 5. Thống kê dự đoán không hợp lệ**

| **Chỉ tiêu**               | **Linear** | **Polynomial** |
|----------------------------|------------|----------------|
| Tổng số mẫu Test           | 5.576      | 5.576          |
| Số dự đoán ≤ 0             | 280        | 242            |
| Tỷ lệ dự đoán không hợp lệ | 5,02%      | 4,34%          |

*Nguồn: reports/run-001/evaluation.json.*

Hiện tượng này có thể được giải thích thông qua các nguyên nhân sau.

**4.1. Mô hình không có ràng buộc đầu ra dương**

Linear Regression sử dụng phương trình hồi quy có miền giá trị đầu ra là tập số thực. Do đó, mô hình có thể tạo ra giá trị âm hoặc bằng 0 khi tổng các thành phần trong phương trình hồi quy không dương.

Mặc dù giá rao bán căn hộ trong dữ liệu hợp lệ luôn lớn hơn 0, thuật toán hồi quy tuyến tính không có cơ chế bắt buộc giá trị dự đoán phải thỏa mãn điều kiện này.

Đây là nguyên nhân trực tiếp về mặt toán học khiến mô hình có thể tạo ra các kết quả dự đoán không phù hợp với thực tế.

**4.2. Ảnh hưởng của sự chênh lệch giá bất động sản**

Dữ liệu bất động sản có sự chênh lệch lớn giữa các phân khúc giá. Trong tập Test, giá rao bán ở nhóm giá cao nhất có thể lên tới 180 tỷ đồng.

Do phương pháp bình phương tối thiểu sử dụng bình phương sai số, những trường hợp có sai số lớn có thể ảnh hưởng mạnh đến quá trình xác định hệ số hồi quy.

Điều này có thể khiến mô hình chưa biểu diễn tốt các căn hộ thuộc phân khúc giá thấp và làm xuất hiện những giá trị dự đoán không dương.

**4.3. Polynomial Regression vẫn sử dụng Linear Regression**

Mặc dù Polynomial Regression bổ sung các thành phần đa thức bậc hai, thuật toán ước lượng cuối cùng vẫn là Linear Regression.

Việc bổ sung các đặc trưng đa thức chỉ làm tăng khả năng biểu diễn quan hệ phi tuyến, không tạo ra ràng buộc đảm bảo đầu ra luôn lớn hơn 0.

Kết quả thực nghiệm cho thấy Polynomial Regression giảm được 38 trường hợp dự đoán không hợp lệ so với Linear Regression, tương ứng mức giảm khoảng 13,57%. Tuy nhiên, mô hình vẫn chưa loại bỏ hoàn toàn hiện tượng này.

Những giải thích trên dựa trên đặc điểm toán học của thuật toán và kết quả quan sát được. Chưa có thí nghiệm riêng để xác định nguyên nhân cụ thể của từng trường hợp dự đoán không hợp lệ.

**5. Giải thích vì sao Polynomial Regression gần như không tốt hơn Linear Regression**

**5.1. So sánh mức độ cải thiện**

**Bảng 6. Mức cải thiện của Polynomial so với Linear trên tập Test**

| **Chỉ số**           | **Mức cải thiện**     |
|----------------------|-----------------------|
| RMSE                 | Giảm 18,78 triệu đồng |
| Tỷ lệ giảm RMSE      | 0,24%                 |
| MAE                  | Giảm 60,66 triệu đồng |
| Tỷ lệ giảm MAE       | 1,47%                 |
| R²                   | Tăng 0,00211          |
| Dự đoán không hợp lệ | Giảm 38 trường hợp    |

Mức cải thiện RMSE được xác định theo công thức:

I = \[(RMSE_M1 − RMSE_M2)/RMSE_M1\] × 100%

Thay số:

I = \[(7,8893 − 7,8706)/7,8893\] × 100%

I ≈ 0,24%.

Kết quả cho thấy Polynomial Regression chỉ cải thiện một phần nhỏ sai số so với Linear Regression, mặc dù có cấu trúc đặc trưng phức tạp hơn.

**5.2. Đặc trưng đa thức không bổ sung thông tin quan sát mới**

Polynomial Regression tạo ra các đặc trưng mới bằng cách biến đổi những đặc trưng đầu vào đã có, chẳng hạn như bình phương diện tích hoặc tích giữa các đặc trưng số.

Những phép biến đổi này giúp mở rộng khả năng biểu diễn của mô hình nhưng không bổ sung thông tin quan sát mới về bất động sản.

Nếu các đặc trưng ban đầu chưa phản ánh đầy đủ những yếu tố ảnh hưởng đến giá căn hộ, việc tăng số lượng đặc trưng đa thức không nhất thiết giúp cải thiện đáng kể hiệu quả dự đoán.

**5.3. Đặc trưng floor_level thiếu toàn bộ**

Trong bộ dữ liệu chính thức, đặc trưng floor_level bị thiếu toàn bộ và được ghi nhận trong selection.json như sau:

"uninformative_features": \[

"floor_level"

\]

Đặc trưng này được giữ lại dưới dạng cột hằng số nhằm duy trì cấu trúc đầu vào của hệ thống.

Do đó, việc tạo thêm các thành phần đa thức liên quan đến floor_level không cung cấp thêm thông tin giúp mô hình phân biệt giá giữa các căn hộ.

**5.4. Hạn chế trong việc biểu diễn tương tác giữa diện tích và khu vực**

Trong cấu trúc Pipeline hiện tại, PolynomialFeatures chỉ được áp dụng cho các đặc trưng dạng số, trong khi đặc trưng khu vực được xử lý riêng bằng OneHotEncoder.

Vì vậy, mô hình không trực tiếp tạo ra các thành phần tương tác đa thức giữa diện tích và khu vực.

Trong thực tế, ảnh hưởng của diện tích đến giá căn hộ có thể khác nhau giữa các khu vực. Đây là một hạn chế có thể giải thích vì sao việc mở rộng đặc trưng đa thức chưa mang lại mức cải thiện đáng kể.

**5.5. Khoảng tin cậy của hai mô hình chồng lấn**

Khoảng tin cậy Bootstrap 95% của RMSE đối với Linear Regression là 7,21–8,65 tỷ đồng, trong khi Polynomial Regression là 7,23–8,61 tỷ đồng.

Hai khoảng tin cậy chồng lấn đáng kể và mức cải thiện RMSE chỉ khoảng 0,24%.

Vì vậy, mặc dù Polynomial Regression đạt kết quả tốt hơn một chút trên tập Test, chưa có đủ bằng chứng để khẳng định mô hình này vượt trội rõ rệt so với Linear Regression.

Các nguyên nhân được trình bày là những giải thích phù hợp với cấu trúc mô hình và kết quả thực nghiệm, không phải kết luận nhân quả đã được kiểm chứng bằng các thí nghiệm riêng biệt.

**6. Minh chứng triển khai PR \#60**

**6.1. Nội dung triển khai**

Để hỗ trợ quá trình huấn luyện trên bộ dữ liệu lịch sử chính thức, TV2 đã thực hiện các thay đổi trong quy trình huấn luyện và tiền xử lý dữ liệu.

Các thay đổi chính bao gồm:

\- Hỗ trợ huấn luyện trên dữ liệu có snapshot_kind = historical.

\- Không dừng huấn luyện khi một đặc trưng số bị thiếu toàn bộ.

\- Giữ nguyên đặc trưng floor_level trong cấu trúc đầu vào.

\- Ghi nhận các đặc trưng không mang thông tin trong uninformative_features.

\- Bổ sung kiểm thử cho các thay đổi trên.

Trong ml/models.py, bộ xử lý giá trị thiếu được điều chỉnh như sau:

SimpleImputer(

strategy="median",

keep_empty_features=True

)

Trong ml/train.py, các đặc trưng số bị thiếu toàn bộ được xác định bằng đoạn mã:

uninformative_features = \[

f for f in NUMERIC_FEATURES

if x_train\[f\].isna().all()

\]

Những thay đổi này giúp mô hình tiếp tục huấn luyện trên dữ liệu lịch sử mà không làm thay đổi cấu trúc đặc trưng đầu vào đã thống nhất.

**6.2. Minh chứng tích hợp mã nguồn**

Các thay đổi trong quy trình huấn luyện, tiền xử lý dữ liệu và kiểm thử đã được tích hợp thành công vào nhánh main thông qua Pull Request \#60.

**Bảng 7. Minh chứng tích hợp mã nguồn**

| **Nội dung**                | **Kết quả**                                 |
|-----------------------------|---------------------------------------------|
| Pull Request                | \#60                                        |
| Trạng thái                  | Merged                                      |
| Commit triển khai           | b76eb2a                                     |
| Merge commit                | 264f8c1                                     |
| Các file triển khai chính   | ml/models.py, ml/train.py, tests/test_ml.py |
| Kết quả kiểm thử toàn dự án | 186 passed                                  |
| GitHub Checks               | 1/1 passed                                  |

Các thay đổi được tích hợp bằng phương pháp cherry-pick, giữ nguyên thông tin tác giả của commit gốc. Những nội dung bổ sung và điều chỉnh mã nguồn được thực hiện trong các commit riêng biệt nhằm đảm bảo tính minh bạch và khả năng truy xuất lịch sử phát triển.

Kết quả kiểm thử được ghi nhận trong Pull Request \#60 cho thấy toàn bộ 186 trường hợp kiểm thử của dự án đều thành công tại thời điểm tích hợp.

Việc tích hợp thành công vào nhánh main là minh chứng cho quá trình hoàn thiện chức năng hỗ trợ huấn luyện trên dữ liệu lịch sử và xử lý các đặc trưng số bị thiếu toàn bộ.

**7. Kết luận**

Kết quả đánh giá chính thức run-001 cho thấy mô hình Linear Regression đạt RMSE khoảng 7,89 tỷ đồng, trong khi Polynomial Regression đạt RMSE khoảng 7,87 tỷ đồng. Hệ số xác định R² của cả hai mô hình đều xấp xỉ 0,56.

Mặc dù Polynomial Regression có khả năng biểu diễn các mối quan hệ phi tuyến thông qua các đặc trưng đa thức bậc hai, mức cải thiện RMSE so với Linear Regression chỉ khoảng 0,24%. Kết quả này cho thấy việc tăng độ phức tạp của mô hình chưa mang lại hiệu quả cải thiện đáng kể trên bộ dữ liệu nghiên cứu.

Bên cạnh đó, cả hai mô hình vẫn xuất hiện các dự đoán không hợp lệ, với 280 trường hợp đối với Linear Regression và 242 trường hợp đối với Polynomial Regression. Nguyên nhân trực tiếp về mặt toán học là cả hai mô hình đều sử dụng phương pháp hồi quy không có ràng buộc đảm bảo đầu ra luôn dương.

So với hai mô hình hồi quy, Decision Tree đạt kết quả tốt hơn trên tập Validation và tiếp tục thể hiện hiệu năng tốt hơn trên tập Test. Do đó, Decision Tree được lựa chọn làm mô hình có hiệu năng tốt nhất trong lần thực nghiệm run-001 dựa trên tiêu chí RMSE của tập Validation.

Về mặt triển khai, chức năng hỗ trợ huấn luyện trên dữ liệu lịch sử, xử lý đặc trưng số bị thiếu toàn bộ và các kiểm thử tương ứng đã được hoàn thiện và tích hợp thành công vào nhánh main thông qua Pull Request \#60.

Toàn bộ số liệu thực nghiệm được sử dụng từ kết quả đánh giá chính thức run-001, không thực hiện huấn luyện lại mô hình. Kết quả chỉ phản ánh hiệu năng của các mô hình trên bộ dữ liệu lịch sử và không đại diện cho giá thị trường hiện hành tại Thành phố Hồ Chí Minh.
