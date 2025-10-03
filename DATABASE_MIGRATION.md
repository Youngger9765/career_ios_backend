# Database Migration 自動化指南

## ✅ 已完成設置

### 1. Alembic 自動化配置
- ✅ 初始化 Alembic
- ✅ 配置 `alembic/env.py` 自動偵測所有 models
- ✅ 使用環境變數 `DATABASE_URL_DIRECT` 連接資料庫
- ✅ 自動載入 17 個資料表模型

### 2. 自動化管理腳本
**檔案**: `scripts/manage_db.py`

### 3. 當前狀態
- ✅ **Alembic 版本**: `d90dfbb1ef85`
- ✅ **資料庫**: Supabase `ehvgueyrxpvkleqidkdu`
- ✅ **已建立表格**: 18 個（含 alembic_version）

---

## 📋 資料表清單（17 個 Models）

### 諮商系統（7 個）
1. `users` - 用戶（諮商師等）
2. `visitors` - 來訪者
3. `cases` - 個案
4. `sessions` - 會談
5. `reports` - 報告
6. `jobs` - 異步任務
7. `reminders` - 提醒事項

### RAG 系統（10 個）
1. `agents` - AI Agent
2. `agent_versions` - Agent 版本
3. `documents` - 文件
4. `chunks` - 文本片段
5. `embeddings` - 向量嵌入
6. `datasources` - 資料來源
7. `collections` - 文件集合
8. `collection_items` - 集合項目
9. `chat_logs` - 對話記錄
10. `pipeline_runs` - Pipeline 執行記錄

---

## 🚀 使用方式

### 方式一：自動化腳本（推薦）

#### 1. 檢查當前狀態
```bash
python scripts/manage_db.py check
```

**輸出**:
- Alembic 版本表狀態
- Models 偵測到的表格
- 資料庫中實際存在的表格

#### 2. 完全自動化（生成 + 執行）
```bash
python scripts/manage_db.py auto
```

**功能**:
- 自動檢查資料庫狀態
- 如有現存表格，提示選擇重置或標記
- 自動生成 migration
- 自動執行 migration

#### 3. 單獨操作

**生成 migration**:
```bash
python scripts/manage_db.py generate
```

**執行 migration**:
```bash
python scripts/manage_db.py upgrade
```

**重置 Alembic 版本表**:
```bash
python scripts/manage_db.py reset
```

---

### 方式二：Alembic 命令行

#### 1. 檢查當前版本
```bash
alembic current
```

#### 2. 生成 migration（從 models 自動偵測變更）
```bash
alembic revision --autogenerate -m "描述訊息"
```

#### 3. 執行 migration
```bash
# 升級到最新版本
alembic upgrade head

# 降級一個版本
alembic downgrade -1

# 降級到特定版本
alembic downgrade <版本號>
```

#### 4. 查看 migration 歷史
```bash
alembic history
```

---

## 🔄 常見工作流程

### A. 新增或修改 Model

1. **編輯 Model 檔案**
   ```python
   # app/models/example.py
   class Example(Base, BaseModel):
       __tablename__ = "examples"

       id = Column(String, primary_key=True)
       name = Column(String, nullable=False)
       # 新增欄位
       description = Column(Text)
   ```

2. **自動生成 migration**
   ```bash
   python scripts/manage_db.py generate
   # 或
   alembic revision --autogenerate -m "add description to example"
   ```

3. **檢查生成的 migration 檔案**
   ```bash
   # 查看 alembic/versions/ 目錄下的最新檔案
   ls -lt alembic/versions/
   ```

4. **執行 migration**
   ```bash
   python scripts/manage_db.py upgrade
   # 或
   alembic upgrade head
   ```

### B. 首次設置新環境

```bash
# 1. 確保 .env 有正確的資料庫連線
DATABASE_URL=postgresql://...
DATABASE_URL_DIRECT=postgresql://...  # 用於 migration

# 2. 完全自動化
python scripts/manage_db.py auto
```

### C. 資料庫已有表格（手動建立的）

**情況**: 資料庫有手動建立的表格，需要讓 Alembic 接管

```bash
# 1. 檢查狀態
python scripts/manage_db.py check

# 2. 標記當前資料庫狀態為最新版本（不執行 migration）
alembic stamp head

# 3. 之後的變更就可以正常生成 migration
```

---

## 📁 專案結構

```
career_ios_backend/
├── alembic/                    # Alembic 配置目錄
│   ├── env.py                  # 環境設定（已配置自動載入 models）
│   ├── script.py.mako          # Migration 模板
│   └── versions/               # Migration 版本檔案
│       └── d90dfbb1ef85_initial_schema_from_models.py
├── alembic.ini                 # Alembic 配置檔
├── scripts/
│   └── manage_db.py           # 資料庫管理自動化腳本 ✨
├── app/
│   ├── models/                # SQLAlchemy Models
│   │   ├── user.py
│   │   ├── visitor.py
│   │   ├── case.py
│   │   ├── session.py
│   │   ├── report.py
│   │   ├── job.py
│   │   ├── reminder.py
│   │   ├── agent.py
│   │   ├── document.py
│   │   ├── collection.py
│   │   ├── chat.py
│   │   └── pipeline.py
│   └── core/
│       └── database.py        # Base & SessionLocal
└── .env                       # 資料庫連線設定
```

---

## 🔑 環境變數設定

**`.env` 檔案**:
```bash
# 應用連線（使用 Pooler - port 6543）
DATABASE_URL=postgresql://postgres.ehvgueyrxpvkleqidkdu:i8Eiszr9JAmKAlnh@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres

# Migration 連線（使用 Direct - port 5432）
DATABASE_URL_DIRECT=postgresql://postgres:i8Eiszr9JAmKAlnh@db.ehvgueyrxpvkleqidkdu.supabase.co:5432/postgres
```

**差異**:
- `DATABASE_URL`: 連接池模式（Pooler），適合應用程式
- `DATABASE_URL_DIRECT`: 直連模式（Direct），適合 migration 和管理操作

---

## ⚠️ 注意事項

### 1. Migration 前檢查
- ✅ 確認 `.env` 設定正確
- ✅ 檢查 Models 定義完整
- ✅ Review 自動生成的 migration 檔案

### 2. 生產環境
```bash
# 先在 staging 環境測試
alembic upgrade head

# 確認無誤後再部署到生產環境

# 如需回滾
alembic downgrade -1
```

### 3. 團隊協作
- 每次 pull 代碼後檢查是否有新的 migration
- 執行 `alembic upgrade head` 同步資料庫
- Commit migration 檔案到版本控制

### 4. Alembic vs 手動 SQL
- ✅ **使用 Alembic**: 自動偵測、版本控制、可回滾
- ❌ **手動 SQL**: 需要手動維護、難以回滾、容易出錯

---

## 🎯 最佳實踐

### 1. 開發流程
```bash
# 1. 修改 Model
vim app/models/example.py

# 2. 自動生成 migration
python scripts/manage_db.py generate

# 3. 檢查生成的 migration
cat alembic/versions/<最新版本>.py

# 4. 執行 migration
python scripts/manage_db.py upgrade

# 5. 驗證結果
python scripts/manage_db.py check
```

### 2. Migration 訊息規範
```bash
# 好的訊息
alembic revision --autogenerate -m "add email_verified to users"
alembic revision --autogenerate -m "create reports table"
alembic revision --autogenerate -m "add index on sessions.created_at"

# 不好的訊息
alembic revision --autogenerate -m "update"
alembic revision --autogenerate -m "fix"
```

### 3. 定期備份
```bash
# 在執行重大 migration 前備份資料庫
# Supabase 提供自動備份，也可以手動備份
```

---

## 📊 Migration 執行結果

### 當前狀態（已完成）

**Alembic 版本**: `d90dfbb1ef85_initial_schema_from_models.py`

**建立的表格**: ✅ 18/18
- ✅ users
- ✅ visitors
- ✅ cases
- ✅ sessions
- ✅ reports
- ✅ jobs
- ✅ reminders
- ✅ agents
- ✅ agent_versions
- ✅ documents
- ✅ chunks
- ✅ embeddings
- ✅ datasources
- ✅ collections
- ✅ collection_items
- ✅ chat_logs
- ✅ pipeline_runs
- ✅ alembic_version（版本控制表）

**資料庫**: Supabase `ehvgueyrxpvkleqidkdu` ✅

---

## 🔧 故障排除

### 問題 1: Can't locate revision
```bash
ERROR: Can't locate revision identified by 'xxx'
```

**解決**:
```bash
# 重置 Alembic 版本表
python scripts/manage_db.py reset

# 重新生成並執行
python scripts/manage_db.py auto
```

### 問題 2: 資料表已存在
```bash
ERROR: relation "xxx" already exists
```

**解決**:
```bash
# 標記當前狀態為最新（不執行 SQL）
alembic stamp head
```

### 問題 3: 無法連接資料庫
```bash
ERROR: could not connect to server
```

**檢查**:
- `.env` 中的 `DATABASE_URL_DIRECT` 是否正確
- 網路連線是否正常
- Supabase 專案是否 active

---

## 📚 延伸閱讀

- [Alembic 官方文檔](https://alembic.sqlalchemy.org/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)
- [Supabase Database](https://supabase.com/docs/guides/database)

---

## ✅ 總結

**完全自動化的 Database Migration 系統已建立！**

使用一個命令即可：
```bash
python scripts/manage_db.py auto
```

功能：
- ✅ 自動偵測 Models 變更
- ✅ 自動生成 Migration
- ✅ 自動執行到 Supabase
- ✅ 版本控制與回滾
- ✅ 完整的狀態檢查

**不再需要手動編寫 SQL！** 🎉
