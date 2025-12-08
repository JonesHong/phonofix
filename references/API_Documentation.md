# TPS Translation API Documentation

## 1. 單句翻譯 (Single Text Translation)

用於翻譯單段文字，支援自動快取、AI 優化與多種翻譯服務商選擇。

### Endpoint
`POST /api/v1/translate`

### Request Body (JSON)

| 欄位名稱 | 類型 | 必填 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- | :--- |
| `text` | string | 是 | - | 要翻譯的原始文字。 |
| `target_lang` | string | 是 | - | 目標語言代碼 (例如: `zh-tw`, `en`, `ja`)。 |
| `source_lang` | string | 否 | `null` | 來源語言代碼。若未提供則自動偵測。 |
| `format` | string | 否 | `plain` | 文字格式，可選 `plain` 或 `html`。 |
| `enable_refinement` | boolean | 否 | `false` | 是否啟用 AI 優化翻譯結果 (通常使用 GPT-4o-mini)。 |
| `preferred_provider` | string | 否 | `auto` | 指定翻譯服務商。可選: `auto`, `deepl`, `openai`, `google`。 |

### Example Request

```json
{
  "text": "Hello, world!",
  "target_lang": "zh-tw",
  "enable_refinement": true,
  "preferred_provider": "openai"
}
```

### Response (JSON)

```json
{
  "success": true,
  "data": {
    "text": "你好，世界！",
    "provider": "openai",
    "is_refined": true,
    "is_cached": false
  },
  "error": null
}
```

---

## 2. 文件翻譯 (File Translation)

用於上傳並翻譯純文字檔案 (.txt, .md, .json, .csv)，系統會讀取內容並進行翻譯。

### Endpoint
`POST /api/v1/translate/file`

### Request (Multipart/Form-Data)

| 欄位名稱 | 類型 | 必填 | 說明 |
| :--- | :--- | :--- | :--- |
| `file` | File | 是 | 要翻譯的檔案 (支援 UTF-8 編碼的文字檔)。 |
| `target_lang` | string | 是 | 目標語言代碼 (例如: `zh-tw`)。 |
| `source_lang` | string | 否 | 來源語言代碼。 |
| `enable_refinement` | boolean | 否 | 是否啟用 AI 優化 (預設 `false`)。 |
| `preferred_provider` | string | 否 | 指定翻譯服務商 (預設 `auto`)。 |

### Example Request (cURL)

```bash
curl -X POST "http://localhost:8000/api/v1/translate/file" \
  -F "file=@document.txt" \
  -F "target_lang=zh-tw" \
  -F "enable_refinement=true"
```

### Response (JSON)

```json
{
  "success": true,
  "data": {
    "text": "這是翻譯後的文件內容...",
    "provider": "deepl",
    "is_refined": false,
    "is_cached": false
  },
  "error": null
}
```
