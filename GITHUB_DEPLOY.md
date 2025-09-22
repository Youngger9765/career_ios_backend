# GitHub Actions CI/CD 部署到 Cloud Run

## 🚀 純 GitHub Actions 部署流程

### 已完成設定
- ✅ GitHub Actions workflow (`.github/workflows/deploy.yml`)
- ✅ Artifact Registry repository
- ✅ Service Account 權限
- ✅ 環境變數配置

### 部署步驟

#### 1. 產生 Service Account Key
```bash
gcloud iam service-accounts keys create key.json \
  --iam-account=career-backend-sa@career-backed.iam.gserviceaccount.com

# 查看 JSON 內容
cat key.json
```

#### 2. 設定 GitHub Secret
1. 前往 GitHub Repository → Settings → Secrets and variables → Actions
2. 點擊 "New repository secret"
3. Name: `GCP_SA_KEY`
4. Value: 貼上完整的 `key.json` 內容

#### 3. 推送程式碼觸發部署
```bash
git add .
git commit -m "Setup GitHub Actions CI/CD"
git push origin main
```

#### 4. 監控部署
- 前往 GitHub → Actions 查看部署進度
- 部署完成後會顯示服務 URL

## 🎯 部署流程說明

### GitHub Actions 會執行：
1. **建構 Docker 映像檔**
   - 使用專案的 `Dockerfile`
   - 標記為 `commit-sha` 和 `latest`

2. **推送到 Artifact Registry**
   - 目標：`us-central1-docker.pkg.dev/career-backed/career-backend/app`

3. **部署到 Cloud Run**
   - 服務名稱：`career-backend-api`
   - 區域：`us-central1`
   - 設定：1GB RAM, 1 CPU, 0-10 實例

4. **執行健康檢查**
   - 確認 `/health` 端點正常回應

### 環境變數
自動設定的環境變數：
- `MOCK_MODE=true`
- `DEBUG=false`
- `GCS_PROJECT=career-backed`

## 📱 部署後的服務網址

部署完成後，你的服務將可在以下網址訪問：

```
https://career-backend-api-[random-hash]-uc.a.run.app
```

### 主要頁面：
- **📱 主應用**: `/static/index.html` - 錄音管理介面
- **📊 Pipeline**: `/static/pipeline.html` - 處理流程展示
- **📚 API 文件**: `/docs` - Swagger UI
- **❤️ 健康檢查**: `/health` - 服務狀態

## 🔧 自定義部署設定

### 修改 Cloud Run 設定
編輯 `.github/workflows/deploy.yml` 中的 flags：

```yaml
flags: |
  --allow-unauthenticated
  --port=8080
  --memory=512Mi          # 降低記憶體
  --cpu=0.5              # 降低 CPU
  --min-instances=1      # 避免冷啟動
  --max-instances=5      # 控制成本
```

### 新增環境變數
```yaml
--set-env-vars=MOCK_MODE=true,DEBUG=false,SECRET_KEY=your-secret-key
```

## 🐛 故障排除

### 常見問題：

1. **GitHub Actions 失敗**
   - 檢查 `GCP_SA_KEY` secret 是否正確設定
   - 確認 Service Account 有足夠權限

2. **Docker 建構失敗**
   - 檢查 `Dockerfile` 語法
   - 確認相依套件在 `requirements.txt` 中

3. **Cloud Run 部署失敗**
   - 檢查映像檔是否成功推送到 Artifact Registry
   - 確認 Service Account 有 `run.developer` 權限

4. **服務無法訪問**
   - 確認 `--allow-unauthenticated` 設定
   - 檢查防火牆規則

### 查看日誌：
```bash
# Cloud Run 服務日誌
gcloud logs tail --follow \
  --filter="resource.type=cloud_run_revision AND resource.labels.service_name=career-backend-api"

# 特定服務狀態
gcloud run services describe career-backend-api --region=us-central1
```

## 🎉 完成！

推送程式碼後，GitHub Actions 會自動：
1. 建構 → 推送 → 部署
2. 約 3-5 分鐘完成整個流程
3. 在 Actions 頁面顯示部署結果和服務 URL

---

**下一步**: 推送程式碼到 GitHub，然後在 Actions 頁面觀看自動部署！