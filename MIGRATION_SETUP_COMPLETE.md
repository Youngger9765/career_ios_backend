# ✅ Database Migration 自動化設置完成

## 🎉 完成項目

### 1. ✅ Alembic 自動化配置
- **位置**: `alembic/`
- **配置檔**: `alembic.ini`
- **環境設定**: `alembic/env.py`（已配置自動載入所有 17 個 models）

### 2. ✅ 自動化管理腳本
- **檔案**: `scripts/manage_db.py`
- **功能**:
  - 檢查資料庫狀態
  - 自動生成 migration
  - 自動執行 migration
  - 重置 Alembic 版本表

### 3. ✅ Makefile 快捷指令
- `make db-check` - 檢查資料庫狀態
- `make db-auto` - 🚀 完全自動化
- `make db-generate` - 生成 migration
- `make db-upgrade` - 執行 migration
- `make db-reset` - 重置版本表

### 4. ✅ 資料庫已建立完成
- **資料庫**: Supabase `ehvgueyrxpvkleqidkdu`
- **Alembic 版本**: `d90dfbb1ef85`
- **表格數量**: 18 個（含版本表）

---

## 📊 已建立的資料表（17 個 Models）

### 諮商系統（7 個）✅
1. ✅ `users` - 用戶（諮商師等）
2. ✅ `visitors` - 來訪者
3. ✅ `cases` - 個案
4. ✅ `sessions` - 會談
5. ✅ `reports` - 報告
6. ✅ `jobs` - 異步任務
7. ✅ `reminders` - 提醒事項

### RAG 系統（10 個）✅
1. ✅ `agents` - AI Agent
2. ✅ `agent_versions` - Agent 版本
3. ✅ `documents` - 文件
4. ✅ `chunks` - 文本片段
5. ✅ `embeddings` - 向量嵌入
6. ✅ `datasources` - 資料來源
7. ✅ `collections` - 文件集合
8. ✅ `collection_items` - 集合項目
9. ✅ `chat_logs` - 對話記錄
10. ✅ `pipeline_runs` - Pipeline 執行記錄

---

## 🚀 使用方式

### 方式一：Alembic 命令（推薦用於專案開發）

#### 1. 檢查當前版本
```bash
alembic current
```

#### 2. 自動生成 migration（從 models 偵測變更）
```bash
alembic revision --autogenerate -m "描述訊息"
```

**範例**:
```bash
# 新增欄位
alembic revision --autogenerate -m "add email_verified to users"

# 新增表格
alembic revision --autogenerate -m "create notifications table"

# 新增索引
alembic revision --autogenerate -m "add index on sessions.created_at"
```

#### 3. 執行 migration
```bash
# 升級到最新版本
alembic upgrade head

# 降級一個版本
alembic downgrade -1

# 查看歷史
alembic history
```

### 方式二：自動化腳本（推薦用於快速操作）

```bash
# 檢查狀態
python scripts/manage_db.py check

# 完全自動化（生成 + 執行）
python scripts/manage_db.py auto

# 單獨操作
python scripts/manage_db.py generate
python scripts/manage_db.py upgrade
```

### 方式三：Makefile（最簡單）

```bash
# 檢查
make db-check

# 自動化
make db-auto

# 單獨操作
make db-generate
make db-upgrade
```

---

## 🔄 開發工作流程

### A. 修改 Model 後自動同步資料庫

1. **編輯 Model**
   ```python
   # app/models/user.py
   class User(Base, BaseModel):
       __tablename__ = "users"

       # ... 現有欄位

       # 新增欄位
       email_verified = Column(Boolean, default=False)
   ```

2. **自動生成 migration**
   ```bash
   alembic revision --autogenerate -m "add email_verified to users"
   ```

3. **檢查生成的檔案**
   ```bash
   # 查看最新的 migration
   cat alembic/versions/<最新版本>.py
   ```

4. **執行 migration**
   ```bash
   alembic upgrade head
   ```

5. **驗證**
   ```bash
   alembic current
   # 或
   python scripts/manage_db.py check
   ```

### B. 全新環境設置

```bash
# 1. 確保 .env 配置正確
DATABASE_URL_DIRECT=postgresql://...

# 2. 執行自動化（推薦）
alembic upgrade head

# 或使用腳本
python scripts/manage_db.py auto
```

---

## 📁 專案結構

```
career_ios_backend/
├── alembic/                              # Alembic 配置
│   ├── env.py                           # ✅ 已配置自動載入 models
│   ├── script.py.mako                   # Migration 模板
│   └── versions/                        # Migration 檔案
│       └── d90dfbb1ef85_initial_schema_from_models.py  # ✅ 初始 migration
│
├── scripts/
│   └── manage_db.py                     # ✅ 自動化管理腳本
│
├── app/
│   ├── models/                          # ✅ 17 個 Models
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
│       └── database.py                  # Base & SessionLocal
│
├── alembic.ini                          # ✅ Alembic 配置檔
├── Makefile                             # ✅ 新增 db-* 指令
├── DATABASE_MIGRATION.md                # ✅ 完整使用文件
└── .env                                 # 資料庫連線設定
```

---

## 🔑 環境變數

**`.env` 必要設定**:
```bash
# 應用程式連線（使用 Pooler）
DATABASE_URL=postgresql://postgres.ehvgueyrxpvkleqidkdu:i8Eiszr9JAmKAlnh@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres

# Migration 連線（使用 Direct）
DATABASE_URL_DIRECT=postgresql://postgres:i8Eiszr9JAmKAlnh@db.ehvgueyrxpvkleqidkdu.supabase.co:5432/postgres
```

**差異**:
- `DATABASE_URL`: Pooler (port 6543) - 應用程式使用
- `DATABASE_URL_DIRECT`: Direct (port 5432) - Migration 使用

---

## 📝 重要提醒

### ✅ 優點：不再需要手動編寫 SQL
- 🚀 自動偵測 Models 變更
- 🔄 自動生成 Migration SQL
- ⬆️ 自動執行到資料庫
- 📜 完整版本控制
- ↩️ 支援回滾（downgrade）

### ⚠️ 注意事項
1. **每次修改 Model 後**：執行 `alembic revision --autogenerate`
2. **檢查生成的 migration**：確保 SQL 正確
3. **執行 migration**：`alembic upgrade head`
4. **團隊協作**：Pull 代碼後記得同步資料庫

### 🎯 最佳實踐
```bash
# 1. 修改 Model
vim app/models/example.py

# 2. 生成 migration
alembic revision --autogenerate -m "add new_field to example"

# 3. 檢查
cat alembic/versions/<最新>.py

# 4. 執行
alembic upgrade head

# 5. 驗證
alembic current
```

---

## 📚 相關文件

1. **`DATABASE_MIGRATION.md`** - 完整使用指南
2. **`scripts/manage_db.py`** - 自動化腳本
3. **`Makefile`** - 快捷指令
4. **`alembic/env.py`** - Alembic 配置

---

## ✅ 驗證結果

### 當前狀態（已完成）
```bash
$ alembic current
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
d90dfbb1ef85 (head)
```

### 資料庫表格
```sql
-- 18 個表格已建立（含 alembic_version）
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

✅ agent_versions
✅ agents
✅ alembic_version
✅ cases
✅ chat_logs
✅ chunks
✅ collection_items
✅ collections
✅ datasources
✅ documents
✅ embeddings
✅ jobs
✅ pipeline_runs
✅ reminders
✅ reports
✅ sessions
✅ users
✅ visitors
```

---

## 🎉 總結

**Database Migration 自動化系統已完全建立！**

### 使用一個命令即可：
```bash
alembic revision --autogenerate -m "your message"
alembic upgrade head
```

### 或更簡單：
```bash
make db-auto
```

**功能完整**:
- ✅ 自動偵測 17 個 Models
- ✅ 自動生成 Migration SQL
- ✅ 自動執行到 Supabase
- ✅ 版本控制與回滾
- ✅ 完整的狀態檢查

**不再需要手動編寫 SQL！** 🎉

---

## 📖 延伸閱讀

- [Alembic 官方文檔](https://alembic.sqlalchemy.org/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)
- [Supabase Database](https://supabase.com/docs/guides/database)
- 專案內文件: `DATABASE_MIGRATION.md`
