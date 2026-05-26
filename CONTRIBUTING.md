# Contributing to phonofix

歡迎 contribution! 請先讀 plan v4 + SPEC.md 了解 v0.4.0 架構。

## PR Workflow

1. Fork + branch from `v0.4-dev` (主開發分支)
2. 確認 `SPEC.md` 沒被 PR 變動（spec frozen）— 若需動 spec 先開 issue 討論
3. 寫 test (TDD preferred)；既有 test 全綠 = baseline
4. `uv run ruff check .` + `uv run pytest tests/ -q` 全綠才開 PR
5. PR description 引用對應 issue + plan §章節
6. PR review by JonesHong; squash merge

## DCO (Developer Certificate of Origin)

每個 commit 必須含 `Signed-off-by: Your Name <email>` line:

```
git commit -s -m "your message"
```

代表你確認 contribution 是你的原創且可以授權給專案。

## Code Style

- Python 3.10+ (annotations + walrus + match where appropriate)
- ruff for lint + format
- Type hints everywhere (Pyright strict 不強制但建議)
- Docstring: Google style or NumPy style (一致即可)

## Issue Templates

開 issue 用以下 template:
- Bug: reproducer + expected vs actual + env (Python/OS/phonofix version)
- Feature: use case + proposed API + alternatives considered
