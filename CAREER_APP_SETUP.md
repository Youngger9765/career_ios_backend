# Career App (career-app-473015) 部署設定

## 🚀 新專案設定

### 專案資訊
- **專案 ID**: `career-app-473015`
- **專案名稱**: career-app
- **帳戶**: `dev02@careercreator.tw`
- **區域**: `us-central1`

### 已完成設定
- ✅ 啟用 APIs: Cloud Run, Cloud Build, Artifact Registry
- ✅ 建立 Artifact Registry: `career-app-backend`
- ✅ 建立 Service Account: `career-app-sa@career-app-473015.iam.gserviceaccount.com`
- ✅ 設定權限: artifactregistry.writer, run.developer, iam.serviceAccountUser

## ⚠️ 組織政策限制

此專案有以下組織政策限制：
1. ❌ **不允許建立 Service Account 金鑰** - 需要使用 Workload Identity Federation
2. ❌ **不允許 public access (allUsers)** - 需要認證才能訪問服務

## 💰 最便宜的 Cloud Run 設定

```yaml
# 已在 .github/workflows/deploy.yml 中設定
--memory=128Mi        # 最小記憶體
--cpu=1              # Gen1 最小 CPU
--min-instances=0    # 冷啟動（節省成本）
--max-instances=1    # 限制最大實例
--concurrency=1000   # 允許高並發
--cpu-throttling     # CPU 節流以節省成本
```

### 成本估算
- **零流量時**: $0/月（min-instances=0）
- **低流量時**: ~$1-5/月
- **中流量時**: ~$10-20/月

## 🔑 GitHub Actions 設定

### 方法 1: Workload Identity Federation (推薦)

由於組織政策不允許建立 Service Account 金鑰，需要設定 Workload Identity Federation：

```bash
# 1. 建立 Workload Identity Pool
gcloud iam workload-identity-pools create github-pool \
  --location=global \
  --display-name="GitHub Actions Pool"

# 2. 建立 Provider
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global \
  --workload-identity-pool=github-pool \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# 3. 綁定 Service Account
gcloud iam service-accounts add-iam-policy-binding \
  career-app-sa@career-app-473015.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/868102453617/locations/global/workloadIdentityPools/github-pool/attribute.repository/Youngger9765/career_ios_backend"
```

### 方法 2: 使用個人帳戶 (臨時方案)

如果 Workload Identity 設定複雜，可以臨時使用個人帳戶：

```bash
# 在 GitHub Secrets 設定:
# GCP_CREDENTIALS: 使用 gcloud auth application-default print-access-token 的結果
```

## 📝 環境變數更新

### .env 檔案已更新
```env
GCS_PROJECT=career-app-473015
GCS_BUCKET=career-app-audio
CLOUD_RUN_SERVICE_ACCOUNT=career-app-sa@career-app-473015.iam.gserviceaccount.com
GCP_PROJECT=career-app-473015
```

### GitHub Actions workflow 已更新
```yaml
PROJECT_ID: career-app-473015
SERVICE_NAME: career-app-backend
REGISTRY: us-central1-docker.pkg.dev
IMAGE_NAME: career-app-backend/app
```

## 🌐 服務訪問

由於組織政策限制，服務需要認證才能訪問：

### 測試服務
```bash
# 獲取 ID token
TOKEN=$(gcloud auth print-identity-token)

# 訪問服務
curl -H "Authorization: Bearer $TOKEN" \
  https://career-app-backend-868102453617.us-central1.run.app/health
```

### 為特定用戶授權
```bash
gcloud run services add-iam-policy-binding career-app-backend \
  --region=us-central1 \
  --member="user:dev02@careercreator.tw" \
  --role=roles/run.invoker
```

## 📊 切換專案指令

```bash
# 切換到 career-app
gcloud config set account dev02@careercreator.tw
gcloud config set project career-app-473015

# 切換回 career-backed
gcloud config set account purpleice9765@msn.com
gcloud config set project career-backed
```

## 🎯 下一步

1. **設定 Workload Identity Federation** 以啟用 GitHub Actions 自動部署
2. **建立 Cloud Storage Bucket** 用於儲存音檔
3. **設定認證機制** 讓授權用戶可以訪問服務
4. **監控成本** 確保維持在最低成本運行

## 💡 注意事項

- 此專案有嚴格的組織政策限制
- 無法使用 Service Account 金鑰
- 無法設定 public access
- 需要為每個用戶單獨授權訪問權限
- 建議使用 Firebase Auth 或 Identity Platform 進行用戶認證

---

**當前服務 URL**: `https://career-app-backend-868102453617.us-central1.run.app`
**狀態**: 需要認證才能訪問