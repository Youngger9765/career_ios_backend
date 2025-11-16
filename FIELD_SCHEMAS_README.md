# Field Schemas API 使用說明

## 概述

這個 API 提供租戶特定的表單欄位配置，讓 iOS 應用程式可以動態生成表單。

## API 端點

### 1. 取得 Client 表單配置

```http
GET /api/v1/field-schemas/client
```

**需要認證**: 是

**Response 範例**:

```json
{
  "form_type": "client",
  "tenant_id": "career",
  "sections": [
    {
      "title": "基本資料",
      "description": "個案基本資訊",
      "order": 1,
      "fields": [
        {
          "key": "name",
          "label": "姓名",
          "type": "text",
          "required": true,
          "placeholder": "請輸入真實姓名",
          "help_text": "使用者的真實姓名",
          "order": 1
        },
        {
          "key": "email",
          "label": "電子郵件地址",
          "type": "email",
          "required": true,
          "placeholder": "example@email.com",
          "help_text": "用於諮詢室或紀錄的連結",
          "order": 2
        },
        {
          "key": "gender",
          "label": "性別",
          "type": "single_select",
          "required": true,
          "options": ["男", "女", "其他", "不透露"],
          "order": 4
        }
      ]
    }
  ]
}
```

### 2. 取得 Case 表單配置

```http
GET /api/v1/field-schemas/case
```

**需要認證**: 是

**Response 範例**:

```json
{
  "form_type": "case",
  "tenant_id": "career",
  "sections": [
    {
      "title": "個案基本資訊",
      "description": "個案編號與狀態",
      "order": 1,
      "fields": [
        {
          "key": "case_number",
          "label": "個案編號",
          "type": "text",
          "required": true,
          "placeholder": "自動生成",
          "help_text": "系統自動生成，格式：CASE0001",
          "order": 1
        },
        {
          "key": "status",
          "label": "個案狀態",
          "type": "single_select",
          "required": true,
          "options": ["active", "completed", "suspended", "referred"],
          "default_value": "active",
          "order": 2
        }
      ]
    }
  ]
}
```

### 3. 通用端點（依類型取得配置）

```http
GET /api/v1/field-schemas/{form_type}
```

**Path Parameters**:
- `form_type`: "client" 或 "case"

## 欄位類型 (FieldType)

| 類型 | 說明 | 用途 |
|------|------|------|
| `text` | 純文字輸入 | 姓名、地址等 |
| `email` | Email 輸入 | Email 地址 |
| `phone` | 電話號碼 | 手機號碼 |
| `date` | 日期選擇器 | 生日、日期 |
| `single_select` | 單選下拉選單 | 性別、學歷等 |
| `multi_select` | 多選選單 | 興趣、技能等 |
| `textarea` | 多行文字 | 備註、說明等 |
| `number` | 數字輸入 | 年齡、年資等 |
| `boolean` | 是/否選擇 | 開關選項 |

## 租戶差異

### Career 租戶
- 重點在職涯諮詢相關欄位
- 包含：身分選項（學生/社會新鮮人/轉職者等）
- 包含：職涯現況、現職資訊

### Island 租戶
- 重點在心理諮商相關欄位
- 較重視隱私保護（可使用代號）
- 包含：身心狀態、精神醫療史等

## iOS 整合範例

```swift
// 1. 取得表單配置
let response = await api.get("/api/v1/field-schemas/client")
let schema = try JSONDecoder().decode(FormSchema.self, from: response)

// 2. 根據配置動態生成表單
for section in schema.sections.sorted(by: { $0.order < $1.order }) {
    // 建立 section UI
    let sectionView = createSection(title: section.title)

    for field in section.fields.sorted(by: { $0.order < $1.order }) {
        // 根據 field.type 建立對應的輸入元件
        switch field.type {
        case "text":
            let textField = createTextField(field)
        case "single_select":
            let picker = createPicker(field)
        case "date":
            let datePicker = createDatePicker(field)
        // ... 其他類型
        }
    }
}

// 3. 驗證表單
func validate(formData: [String: Any], schema: FormSchema) -> [String] {
    var errors: [String] = []

    for section in schema.sections {
        for field in section.fields where field.required {
            if formData[field.key] == nil || formData[field.key] as? String == "" {
                errors.append("\(field.label) 為必填欄位")
            }
        }
    }

    return errors
}
```

## 欄位配置說明

### 必填欄位 (Client)
- name: 姓名
- email: Email
- phone: 電話
- gender: 性別
- birth_date: 生日
- identity_option: 身分選項
- current_status: 目前現況

### 選填欄位 (Client)
- education: 學歷
- current_job: 現職
- career_status: 職涯現況
- has_consultation_history: 過往諮詢經驗
- has_mental_health_history: 心理/精神醫療史
- location: 居住地
- notes: 備註

### 配置檔案位置

- **Schema 定義**: `app/schemas/field_config.py`
- **租戶配置**: `app/config/field_configs.py`
- **API 端點**: `app/api/field_schemas.py`

## 新增租戶

要為新租戶新增配置：

1. 編輯 `app/config/field_configs.py`
2. 建立新的 section 列表（如 `NEW_TENANT_CLIENT_SECTIONS`）
3. 在 `FIELD_CONFIGS` 字典中新增：

```python
FIELD_CONFIGS = {
    "career": { ... },
    "island": { ... },
    "new_tenant": {
        "client": FormSchema(
            form_type="client",
            tenant_id="new_tenant",
            sections=NEW_TENANT_CLIENT_SECTIONS,
        ),
        "case": FormSchema(
            form_type="case",
            tenant_id="new_tenant",
            sections=NEW_TENANT_CASE_SECTIONS,
        ),
    },
}
```

## 測試

```bash
# 使用 curl 測試（需先登入取得 token）
curl -X GET "http://localhost:8080/api/v1/field-schemas/client" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

curl -X GET "http://localhost:8080/api/v1/field-schemas/case" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```
