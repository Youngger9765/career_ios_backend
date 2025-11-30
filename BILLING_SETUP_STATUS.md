# GCP Billing Monitor - 当前配置状态

**生成时间**: 2025-11-30

---

## ✅ 已完成

### 1. 代码部署
- ✅ **Main 分支**: Billing monitor 已部署
- ✅ **Staging 分支**: Billing monitor 已部署
- ✅ **依赖安装**: `google-cloud-bigquery ^3.14.0` 已添加
- ✅ **模块验证**: 所有 billing 模块导入成功

### 2. 配置文件
- ✅ **Admin API Key**: `0iaiIHuIbnqwiEOKINaZKUzpykAbtnLJjdZpFyeSU_Q`
- ✅ **.env 配置**: GCP Billing 部分已添加
  ```bash
  GCS_PROJECT=groovy-iris-473015-h3
  BILLING_DATASET_ID=billing_export
  BILLING_TABLE_ID=gcp_billing_export_resource_v1_012E4D_01ACF3_0FF7FC
  API_ADMIN_KEY=0iaiIHuIbnqwiEOKINaZKUzpykAbtnLJjdZpFyeSU_Q
  ```

### 3. 自动化脚本
- ✅ **setup_gcp_billing.sh**: 一键设置 GCP 资源
- ✅ **check_billing_config.sh**: 验证配置状态
- ✅ **BILLING_QUICK_START.md**: 快速开始指南

---

## ⚠️ 需要用户完成

### 1. GCP 账户权限 (必须)
**问题**: 当前登录账户 `youngtsai@junyiacademy.org` 无权访问项目 `groovy-iris-473015-h3`

**解决方案**:
```bash
# 选项 A: 使用有权限的账户登录
gcloud auth login
# 然后选择有权限访问 groovy-iris-473015-h3 的 Google 账户

# 选项 B: 添加当前账户到项目 (需要项目 Owner 权限)
# 在 GCP Console → IAM 中添加 youngtsai@junyiacademy.org
```

### 2. Gmail SMTP 配置 (必须)
**问题**: `.env` 中 SMTP 配置使用占位符

**解决方案**:
1. **生成 Gmail App Password**:
   - 访问: https://myaccount.google.com/apppasswords
   - 创建应用密码，命名为 "GCP Billing Monitor"
   - 复制 16 位密码

2. **更新 `.env` 文件**:
   ```bash
   SMTP_USER=你的gmail@gmail.com
   SMTP_PASSWORD=16位app密码(去掉空格)
   FROM_EMAIL=你的gmail@gmail.com
   BILLING_REPORT_EMAIL=dev02@example.com
   ```

### 3. BigQuery Billing Export 配置 (必须)
**状态**: 未验证（因 GCP 权限问题）

**步骤**:
1. 访问: https://console.cloud.google.com/billing/012E4D-01ACF3-0FF7FC/export
2. 点击 "BigQuery export" → "Detailed usage cost" → "EDIT SETTINGS"
3. 选择:
   - Project: `groovy-iris-473015-h3`
   - Dataset: `billing_export` (会自动创建)
4. 点击 "SAVE"
5. ⏱️ **等待 24-48 小时**数据开始流入

---

## 🚀 完成权限配置后执行

### Step 1: 启用必要的 GCP APIs
```bash
gcloud config set project groovy-iris-473015-h3
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable run.googleapis.com
```

### Step 2: 运行自动化设置脚本
```bash
./setup_gcp_billing.sh
```
**脚本会自动**:
- 创建 Service Account (`billing-monitor`)
- 授予 BigQuery 权限
- 创建 Cloud Scheduler job

### Step 3: 本地测试
```bash
# 启动服务器
poetry run uvicorn app.main:app --reload

# 测试 API
curl -X GET "http://localhost:8000/api/v1/billing/report" \
  -H "X-Admin-Key: 0iaiIHuIbnqwiEOKINaZKUzpykAbtnLJjdZpFyeSU_Q"

# 测试邮件发送
curl -X POST "http://localhost:8000/api/v1/billing/send-report" \
  -H "X-Admin-Key: 0iaiIHuIbnqwiEOKINaZKUzpykAbtnLJjdZpFyeSU_Q"
```

### Step 4: 部署到 Cloud Run
```bash
gcloud run deploy career-backend \
  --source . \
  --region us-central1 \
  --service-account billing-monitor@groovy-iris-473015-h3.iam.gserviceaccount.com \
  --set-env-vars "GCS_PROJECT=groovy-iris-473015-h3,BILLING_DATASET_ID=billing_export,BILLING_TABLE_ID=gcp_billing_export_resource_v1_012E4D_01ACF3_0FF7FC" \
  --set-secrets "API_ADMIN_KEY=billing-admin-key:latest,OPENAI_API_KEY=openai-api-key:latest,SMTP_PASSWORD=smtp-password:latest" \
  --allow-unauthenticated
```

### Step 5: 验证 Cloud Scheduler
```bash
# 手动触发
gcloud scheduler jobs run daily-billing-report --location=us-central1

# 查看状态
gcloud scheduler jobs describe daily-billing-report --location=us-central1
```

---

## 📊 API Endpoints

| Endpoint | Method | 功能 | Headers |
|----------|--------|------|---------|
| `/api/v1/billing/report` | GET | 返回 JSON 报告 | `X-Admin-Key: 0iaiI...` |
| `/api/v1/billing/send-report` | POST | 发送邮件报告 | `X-Admin-Key: 0iaiI...` |
| `/api/v1/billing/costs/7days` | GET | 原始费用数据 | `X-Admin-Key: 0iaiI...` |

---

## 📁 相关文件

| 文件 | 用途 |
|------|------|
| `BILLING_QUICK_START.md` | 3 分钟快速开始指南 |
| `setup_gcp_billing.sh` | 自动化 GCP 设置脚本 |
| `check_billing_config.sh` | 配置验证脚本 |
| `docs/BILLING_MONITOR_SETUP.md` | 完整设置文档 (573 行) |
| `docs/BILLING_MONITOR_DEPLOYMENT_CHECKLIST.md` | 部署检查清单 (389 行) |
| `docs/BILLING_MONITOR_README.md` | 架构和功能说明 (383 行) |

---

## 🎯 完成后的效果

每天早上 9:00 (台北时间)，`dev02@example.com` 会收到包含以下内容的 HTML 邮件：

### 📧 邮件内容预览
```
GCP Cost Report - Last 7 Days - 2025-11-30 ($123.45 USD)

┌─────────────────────────────────────┐
│ Summary                             │
│ • Total Cost: $123.45 USD           │
│ • Daily Average: $17.64 USD         │
│ • Services Count: 15                │
│ • Date Range: 2025-11-23 to 11-30  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Top Services by Cost                │
│ 1. Cloud Run        $45.00  +12.5%  │
│ 2. BigQuery         $30.00   -5.2%  │
│ 3. Cloud SQL        $25.00   +8.0%  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Daily Cost Trend                    │
│ 2025-11-30  $18.50  ████████        │
│ 2025-11-29  $17.20  ███████         │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ AI Insights & Recommendations       │
│ • 趋势: 费用上升 5%                 │
│ • 热点: Cloud Run 增长 12.5%        │
│ • 建议: 考虑使用预留实例            │
│ • 行动: 检查自动扩展设置            │
└─────────────────────────────────────┘
```

---

## 💰 预估成本

| 服务 | 用量 | 月成本 |
|------|------|--------|
| BigQuery Queries | ~30 次/月 | $0.30 |
| Cloud Scheduler | 1 job | $0.10 |
| Cloud Run | 最小流量 | $0.30 |
| OpenAI API | 30 reports | $0.60 |
| **总计** | | **~$1.30/月** |

---

## 🐛 故障排除

### 问题: BigQuery 找不到数据
```bash
# 检查 billing export 配置
# 访问: https://console.cloud.google.com/billing/XXX/export

# 验证数据
bq query --use_legacy_sql=false \
  "SELECT COUNT(*) FROM \`groovy-iris-473015-h3.billing_export.gcp_billing_export_*\`"
```

### 问题: 邮件发送失败
```bash
# 测试 SMTP 连接
python3 -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-gmail@gmail.com', 'your-app-password')
print('✅ SMTP connection successful')
"
```

### 问题: Cloud Scheduler 未触发
```bash
# 查看 logs
gcloud logging read "resource.type=cloud_scheduler_job" --limit 10
```

---

## ✅ 验证清单

- [ ] GCP 账户有项目权限
- [ ] BigQuery billing export 已配置
- [ ] `.env` 文件 SMTP 配置完整
- [ ] 运行 `./check_billing_config.sh` 全绿
- [ ] 本地测试 API 成功
- [ ] 邮件发送成功
- [ ] Cloud Run 已部署
- [ ] Cloud Scheduler 已创建并测试

---

**下一步**: 完成上述 "需要用户完成" 部分后，运行:
```bash
./check_billing_config.sh
```

---

**版本**: v1.0.0
**最后更新**: 2025-11-30
