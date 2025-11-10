# Staging 環境 Cold Start 延遲分析

## 📊 測試結果

### 測試環境
- **服務**: `career-app-api-staging`
- **URL**: `https://career-app-api-staging-kxaznpplqq-uc.a.run.app`
- **測試時間**: 2025-11-10
- **部署版本**: `7e71bc1`

---

## ⏱️ API 回應時間

### 1. Login API (POST /api/auth/login)
```
Request 1: 200 - 2.468s
Request 2: 200 - 2.702s
Request 3: 200 - 2.669s

平均: ~2.6 秒
```

### 2. Get Reports API (GET /api/v1/reports)
```
Request 1: 200 - 3.104s
Request 2: 200 - 2.421s
Request 3: 200 - 2.757s

平均: ~2.8 秒
```

---

## 🔧 Cloud Run 配置 (ci.yml:161-163)

```yaml
--min-instances=0     # ⚠️ 關鍵：沒有流量時縮減到 0
--max-instances=1     # 最多 1 個實例
--memory=1Gi          # 記憶體 1GB
--cpu=1               # 1 個 CPU
--timeout=300         # 超時 5 分鐘
--concurrency=1000    # 每個實例可處理 1000 個並發請求
--cpu-throttling      # CPU throttling 啟用
```

---

## 🐌 Cold Start 問題分析

### 什麼是 Cold Start？

當 `min-instances=0` 時：
- **沒有流量** → Cloud Run 縮減到 0 個實例（省錢）
- **第一個請求進來** → 需要啟動新容器
- **Cold Start 延遲** = 容器啟動時間 + Python 載入時間 + FastAPI 初始化

### Cold Start 時間組成

```
總 Cold Start 時間 (~5-10 秒)
├── 容器啟動 (~2-3 秒)
│   ├── 拉取 Docker image
│   ├── 啟動容器
│   └── 網路配置
├── Python 環境載入 (~1-2 秒)
│   ├── Python runtime
│   ├── 載入依賴 (FastAPI, SQLAlchemy, etc.)
│   └── 初始化應用
└── 資料庫連接 (~1-2 秒)
    ├── 建立 connection pool
    └── 第一次查詢
```

### 當前觀察

**❌ 問題**：
- Login API: **2.6 秒** (理想應該 < 500ms)
- Get Reports: **2.8 秒** (理想應該 < 1s)
- 這些時間**包含** warm instance 的時間
- 如果是 cold start，可能需要 **5-10 秒**

**✅ 好消息**：
- 服務穩定運行
- 沒有 timeout 問題
- 後續請求會快很多 (warm instance)

---

## 💡 優化建議

### 選項 1: 設定 min-instances=1 (推薦用於 production)

**優點**：
- ✅ 消除 cold start 延遲
- ✅ 第一個請求也很快 (~500ms)
- ✅ 使用者體驗更好

**缺點**：
- ❌ 成本增加（24/7 運行一個實例）
- ❌ Staging 可能不需要

**修改方式**：
```yaml
# .github/workflows/ci.yml:161
--min-instances=1  # 改為 1
```

**成本估算**：
- 1 個實例 (1 vCPU, 1GB RAM)
- 約 $50-60/月 (視使用量)

---

### 選項 2: 使用 Cloud Run v2 + Startup CPU Boost

**優點**：
- ✅ Cold start 時 CPU 加倍
- ✅ 加快啟動速度
- ✅ min-instances=0 時仍有效

**修改方式**：
```yaml
gcloud run services update career-app-api-staging \
  --execution-environment=gen2 \
  --cpu-boost
```

---

### 選項 3: 優化 Docker Image

**當前 image 可能的問題**：
- 太多依賴
- 沒有使用 multi-stage build
- 沒有快取 Python packages

**優化步驟**：

1. **使用 slim Python image**
```dockerfile
FROM python:3.11-slim  # 不是 python:3.11
```

2. **Multi-stage build**
```dockerfile
# Build stage
FROM python:3.11 as builder
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt > requirements.txt

# Runtime stage
FROM python:3.11-slim
COPY --from=builder requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

3. **移除不必要的依賴**
```bash
# 檢查哪些 package 真的需要
poetry show --tree
```

---

### 選項 4: Lazy Loading

**延遲載入不常用的模組**：

```python
# app/main.py
from fastapi import FastAPI

app = FastAPI()

# ❌ 不要在啟動時載入所有 service
# from app.services.openai_service import OpenAIService

@app.get("/api/v1/reports")
def get_reports():
    # ✅ 只在真正需要時載入
    from app.services.openai_service import OpenAIService
    ...
```

---

### 選項 5: 預熱請求 (Warm-up Request)

**使用 Cloud Scheduler 定期發送請求**：

```bash
# 每 5 分鐘發送一次 health check
gcloud scheduler jobs create http staging-warmup \
  --schedule="*/5 * * * *" \
  --uri="https://career-app-api-staging.../health" \
  --http-method=GET
```

**成本**：幾乎免費

---

## 📈 建議的改進計畫

### Staging 環境 (當前)
```yaml
min-instances: 0        # 保持為 0（省錢）
optimization:
  - 優化 Docker image   # 減少啟動時間
  - 使用 CPU boost      # Cloud Run v2
  - Lazy loading        # 延遲載入
```

**預期改善**：Cold start 從 ~8s → ~3-4s

---

### Production 環境 (未來)
```yaml
min-instances: 1        # 設為 1（消除 cold start）
max-instances: 10       # 增加到 10（應對高流量）
cpu: 2                  # 2 vCPU
memory: 2Gi             # 2GB RAM
```

**預期效果**：
- 第一個請求：~500ms
- 後續請求：~200-300ms

---

## 🎯 立即可做的改進

1. **檢查 Docker image 大小**
   ```bash
   docker images | grep career-app
   ```

2. **Profile 啟動時間**
   ```python
   # app/main.py
   import time
   start = time.time()

   # ... 應用初始化 ...

   print(f"App startup time: {time.time() - start:.2f}s")
   ```

3. **移除不必要的依賴**
   ```bash
   poetry show | wc -l  # 檢查有多少依賴
   ```

---

## 📚 相關資源

- [Cloud Run Cold Start 最佳實踐](https://cloud.google.com/run/docs/tips/general#optimize_cold_start_time)
- [FastAPI Performance Tips](https://fastapi.tiangolo.com/deployment/concepts/)
- [Container Optimization](https://cloud.google.com/run/docs/tips/general#container)

---

## 🔍 監控建議

定期檢查 Cloud Run metrics：
- Cold start frequency
- Request latency (P50, P95, P99)
- Instance count
- CPU / Memory usage

**指令**：
```bash
gcloud run services describe career-app-api-staging \
  --region=us-central1 \
  --format="table(status.url, status.latestReadyRevision)"
```
