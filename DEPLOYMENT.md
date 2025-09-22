# Career Backend - Cloud Run 部署指南

## 已完成的設定

### ✅ GCP 專案設定
- 專案 ID: `career-backed`
- 已啟用 APIs: Cloud Build, Cloud Run, Artifact Registry
- Artifact Registry: `us-central1-docker.pkg.dev/career-backed/career-backend`
- Service Account: `career-backend-sa@career-backed.iam.gserviceaccount.com`

### ✅ CI/CD 設定
- GitHub Actions 工作流程: `.github/workflows/deploy.yml`
- Cloud Build 配置: `cloudbuild.yaml`
- 環境設定: `.env`

## 部署步驟

### 1. 設定 GitHub Secrets

在 GitHub Repository Settings > Secrets and variables > Actions 中新增：

```
GCP_SA_KEY: (Service Account JSON Key)
```

取得 Service Account Key：
```bash
gcloud iam service-accounts keys create key.json \
  --iam-account=career-backend-sa@career-backed.iam.gserviceaccount.com
```

### 2. 推送程式碼觸發部署

```bash
git add .
git commit -m "Setup CI/CD pipeline"
git push origin main
```

### 3. 手動部署（測試用）

```bash
# 建構並部署
gcloud builds submit --config cloudbuild.yaml .
```

### 4. 檢查部署狀態

```bash
# 查看 Cloud Run 服務
gcloud run services list --region=us-central1

# 查看服務 URL
gcloud run services describe career-backend-api \
  --region=us-central1 \
  --format='value(status.url)'

# 查看日誌
gcloud logs tail --follow --resource-type=cloud_run_revision
```

## 環境變數設定

### 生產環境需要更新：

1. **SECRET_KEY**: 產生隨機 32 字符密鑰
2. **DATABASE_URL**: Cloud SQL 連線字串
3. **OPENAI_API_KEY**: OpenAI API 金鑰
4. **GCS_BUCKET**: Cloud Storage bucket 名稱

### 更新環境變數：

```bash
gcloud run services update career-backend-api \
  --region=us-central1 \
  --set-env-vars="SECRET_KEY=your-new-secret-key"
```

## 監控與日誌

### 查看應用日誌：
```bash
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=career-backend-api" --limit=50
```

### 查看 Cloud Build 歷史：
```bash
gcloud builds list --limit=10
```

### 設定告警：
- Cloud Run 服務錯誤率
- 回應時間
- 記憶體使用量

## 安全設定

### 建議設定：
1. 啟用 VPC Connector（如需要連接 Cloud SQL）
2. 設定最小權限的 IAM 角色
3. 啟用 Cloud Armor（WAF）
4. 設定自定義網域和 SSL

## 成本優化

### 目前設定：
- 最小實例：0（冷啟動）
- 最大實例：10
- CPU：1
- 記憶體：1Gi

### 調整建議：
```bash
gcloud run services update career-backend-api \
  --region=us-central1 \
  --min-instances=1 \  # 避免冷啟動
  --max-instances=5 \  # 控制成本
  --cpu=0.5 \          # 降低 CPU
  --memory=512Mi       # 降低記憶體
```

## 故障排除

### 常見問題：

1. **建構失敗**：檢查 `cloudbuild.yaml` 和 `Dockerfile`
2. **部署失敗**：檢查 IAM 權限和環境變數
3. **服務無回應**：檢查 PORT 環境變數（應為 8080）
4. **認證錯誤**：檢查 Service Account 金鑰

### 健康檢查：
```bash
curl https://your-service-url/health
```

## 開發流程

1. 本地開發：`make dev`
2. 測試：`make test`
3. 推送到 GitHub：觸發自動部署
4. 確認部署：檢查 Cloud Run 服務狀態

---

🎯 **部署完成後，你的服務將可在以下位置訪問：**
- API: `https://career-backend-api-[hash]-uc.a.run.app`
- 健康檢查: `https://career-backend-api-[hash]-uc.a.run.app/health`
- API 文件: `https://career-backend-api-[hash]-uc.a.run.app/docs`