# Career Backend - groovy-iris-473015-h3 專案設定

## 🚀 專案資訊

- **專案 ID**: `groovy-iris-473015-h3`
- **專案名稱**: career-app
- **組織**: careercreator.tw (ID: 736839403226)
- **帳戶**: `dev02@careercreator.tw`
- **服務 URL**: `https://career-backend-api-978304030758.us-central1.run.app`

## ✅ 已完成設定

1. **APIs 啟用**:
   - Cloud Run
   - Cloud Build
   - Artifact Registry

2. **Artifact Registry**:
   - Repository: `us-central1-docker.pkg.dev/groovy-iris-473015-h3/career-backend`

3. **Service Account**:
   - `career-backend-sa@groovy-iris-473015-h3.iam.gserviceaccount.com`
   - 權限: artifactregistry.writer, run.developer, iam.serviceAccountUser

4. **Cloud Run 服務**:
   - 名稱: `career-backend-api`
   - 最小配置 (128Mi RAM, 1 CPU)

## ⚠️ 組織政策限制

因為在 careercreator.tw 組織下，有以下限制：

1. **❌ 無法建立 Service Account Key**
   - 政策: `constraints/iam.disableServiceAccountKeyCreation`
   - 影響: GitHub Actions 需要其他認證方式

2. **❌ 無法設定 Public Access (allUsers)**
   - 政策: 組織安全政策
   - 影響: 服務需要認證才能訪問

## 🔐 GitHub Actions 解決方案

### 方案 1: 使用 Cloud Build (推薦)
在專案內使用 Cloud Build 不需要 Service Account Key：

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'us-central1-docker.pkg.dev/groovy-iris-473015-h3/career-backend/app', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'us-central1-docker.pkg.dev/groovy-iris-473015-h3/career-backend/app']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'career-backend-api'
      - '--image=us-central1-docker.pkg.dev/groovy-iris-473015-h3/career-backend/app'
      - '--region=us-central1'
```

### 方案 2: 使用個人 Access Token (臨時)
```bash
# 生成 token
gcloud auth print-access-token

# 在 GitHub Secrets 設定 GCP_ACCESS_TOKEN
# 修改 workflow 使用 token 認證
```

### 方案 3: Workload Identity Federation
設定較複雜但最安全，詳見 Google 文檔。

## 💰 成本優化設定

```yaml
# 最便宜的 Cloud Run 配置
--memory=128Mi        # 最小記憶體
--cpu=1              # Gen1 最小 CPU
--min-instances=0    # 無閒置成本
--max-instances=1    # 限制擴展
--concurrency=1000   # 高並發
--cpu-throttling     # CPU 節流
```

**預估成本**:
- 零流量: **$0/月**
- 低流量: **$1-5/月**
- 中流量: **$10-20/月**

## 📝 環境變數 (.env)

```env
# Google Cloud
GCS_PROJECT=groovy-iris-473015-h3
GCS_BUCKET=career-backend-audio
CLOUD_RUN_SERVICE_ACCOUNT=career-backend-sa@groovy-iris-473015-h3.iam.gserviceaccount.com
GCP_PROJECT=groovy-iris-473015-h3
```

## 📋 GitHub Actions Workflow

已更新 `.github/workflows/deploy.yml`:

```yaml
env:
  PROJECT_ID: groovy-iris-473015-h3
  SERVICE_NAME: career-backend-api
  REGION: us-central1
  REGISTRY: us-central1-docker.pkg.dev
  IMAGE_NAME: career-backend/app
```

## 🚨 重要提醒

1. **無法使用 GitHub Actions 直接部署**（除非設定 Workload Identity）
2. **服務需要認證才能訪問**
3. **建議使用 Cloud Build 進行 CI/CD**

## 🎯 下一步建議

1. **設定 Cloud Build 觸發器**：
   ```bash
   gcloud builds triggers create github \
     --repo-name=career_ios_backend \
     --repo-owner=Youngger9765 \
     --branch-pattern="^master$" \
     --build-config=cloudbuild.yaml
   ```

2. **測試服務（需要認證）**：
   ```bash
   # 獲取 token
   TOKEN=$(gcloud auth print-identity-token)
   
   # 訪問服務
   curl -H "Authorization: Bearer $TOKEN" \
     https://career-backend-api-978304030758.us-central1.run.app/health
   ```

3. **授權特定用戶訪問**：
   ```bash
   gcloud run services add-iam-policy-binding career-backend-api \
     --region=us-central1 \
     --member="user:dev02@careercreator.tw" \
     --role=roles/run.invoker
   ```

## 💡 建議

由於組織政策限制，如果需要更靈活的部署方式，可以考慮：
1. 使用個人專案（如之前的 career-backed）
2. 請組織管理員調整政策
3. 使用 Cloud Build 而非 GitHub Actions

---

**專案狀態**: ✅ 已設定完成，但需要解決 CI/CD 認證問題