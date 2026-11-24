# HCM Apartment Price AI — hướng dẫn cho Claude Code

Đồ án nhóm 6 người: ước tính **giá rao bán** căn hộ TP.HCM bằng Linear, Polynomial, Decision Tree (so với baseline), đánh giá holdout độc lập, phục vụ qua FastAPI, demo bằng React. Trả lời bằng tiếng Việt, ngắn gọn, đủ rõ cho người mới.

## Lệnh

```powershell
$py = ".venv/Scripts/python.exe"
& $py -m pytest -q          # Temp bị chặn → --basetemp=.local-artifacts/<thư mục mới>, xóa sau
& $py -m ruff check .
& $py -m pip check
& $py -m ml.train --help    # tương tự: ml.freeze, ml.registry, ml.evaluate, ml.release
```

Dùng `gh` cho PR/CI. Frontend ở `frontend/` (React/Vite/Playwright, của TV5): xem `frontend/README.md`.

## Cấu trúc mã

`ml/` schema, data, models, train, freeze, registry, evaluate, release · `backend/` FastAPI và nạp gói approved · `frontend/` UI · `tests/` test chính thức · `docs/SPEC.md` yêu cầu · `docs/TEAM.md` phân công + checklist · `GLOSSARY.md` thuật ngữ (nguồn duy nhất cho nghĩa từ) · `README.md` hợp đồng và quyết định (chưa tách ADR).

## Việc LUÔN làm (chi tiết ở `.claude/rules/`, cục bộ của chủ repo, tự nạp)

- Bắt đầu: đọc README, rồi `handoff.md` (chỉ file này). Nhắn `update` → cập nhật handoff (skill `update-handoff`).
- Thay đổi hành vi: TDD, đỏ đúng lý do rồi xanh. Trước bàn giao: `code-review`.
- Git: nhánh từ `origin/main`, PR vào `main`, CI xanh. Merge chỉ khi chủ repo duyệt rõ ràng; không push main, không force-push. Xem `rules/agent/git.md`.
- Không commit raw data, PII, nhãn test, model binary, secrets. Không tạo issue; checklist ở `docs/TEAM.md`.
- Trước khi xóa file/thư mục: đọc `.claude/policies/cleanup.md`.

## Mở khi cần (không tự nạp)

`.claude/policies/cleanup.md` · cục bộ của chủ repo, có thể không có: `.claude/README.md` (mục lục), `.claude/references/decision-log.md`, `handoff-tried.md` (thí nghiệm đã có kết luận), `handoff-reference.md`, `handoff-archive.md` (chỉ grep).
