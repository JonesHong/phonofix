# 打包與依賴規格（避免使用者踩坑）

## 1) optional dependencies（建議）

你們專案目前是「預設安裝全部語言支援」，但仍建議每個語言都維持一個 group，原因：
- 使用者可以精準安裝（例如只要某語言）
- INSTALL_HINT 能提供清楚指引（包含 extras 名稱）

新增語言時：
- 在 `pyproject.toml` 的 `[project.optional-dependencies]` 增加一個 group（例如 `ko = [...]`）
- 在 `src/phonofix/languages/{language}/__init__.py` 定義：
  - `{LANG}_INSTALL_HINT`：告訴使用者應安裝哪個 extras
  - `INSTALL_HINT = {LANG}_INSTALL_HINT`：統一對外

## 2) backend 的 ImportError 規格

當使用者未安裝語言依賴時：
- backend 必須丟出 `ImportError(INSTALL_HINT)`（訊息要可直接照做）
- 不要讓使用者看到第三方庫的原始 ImportError（可作為 `from exc` 的 cause）

## 3) 為什麼模板不放進 `src/`

如果把模板放在 `src/phonofix/languages/`：
- 會被打包進 wheel（使用者會看到）
- 可能被 IDE/使用者誤用（import 到 template）
- 增加維護成本與認知負擔

因此模板放在 `templates/` 是刻意的：它是開發者文件，不是產品功能。

