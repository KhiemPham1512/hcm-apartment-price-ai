# Dữ liệu riêng tư (luôn áp dụng)

- Không commit raw data, PII, nhãn test/`holdout.csv`/`splits.csv`, registry thật, model binary, secrets.
- Không gửi những thứ trên ra dịch vụ ngoài, gồm cả agy-worker, tra web và công cụ bên thứ ba. Việc cần chúng thì Claude tự xử lý hoặc hỏi chủ repo.
- Fixture synthetic dùng để test kỹ thuật thì được; không gọi nó là dữ liệu thị trường.
