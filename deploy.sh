#!/bin/bash

# 部署腳本 - 在本地執行，不需要 Service Account Key

echo "🚀 開始部署到 groovy-iris-473015-h3..."

# 設定變數
PROJECT_ID="groovy-iris-473015-h3"
SERVICE_NAME="career-app-api"
REGION="us-central1"
REGISTRY="us-central1-docker.pkg.dev"
IMAGE_NAME="career-app/app"
IMAGE_TAG=${1:-$(git rev-parse --short HEAD)}
FULL_IMAGE="${REGISTRY}/${PROJECT_ID}/${IMAGE_NAME}:${IMAGE_TAG}"

# 確認登入狀態
echo "📌 當前帳戶："
gcloud config get-value account

echo "📌 當前專案："
gcloud config get-value project

# 建構 Docker 映像
echo "🔨 建構 Docker 映像..."
docker build -t ${FULL_IMAGE} .

# 配置 Docker 認證
echo "🔐 配置 Docker 認證..."
gcloud auth configure-docker ${REGISTRY} --quiet

# 推送映像到 Artifact Registry
echo "📤 推送映像到 Artifact Registry..."
docker push ${FULL_IMAGE}

# 部署到 Cloud Run
echo "🚀 部署到 Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image=${FULL_IMAGE} \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --memory=128Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=1 \
  --concurrency=1000 \
  --cpu-throttling \
  --port=8080 \
  --no-allow-unauthenticated \
  --set-env-vars=MOCK_MODE=true,DEBUG=false,GCS_PROJECT=${PROJECT_ID}

# 顯示服務 URL
echo "✅ 部署完成！"
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --format='value(status.url)')

echo "🌐 服務 URL: ${SERVICE_URL}"
echo "📝 測試指令: curl -H \"Authorization: Bearer \$(gcloud auth print-identity-token)\" ${SERVICE_URL}/health"