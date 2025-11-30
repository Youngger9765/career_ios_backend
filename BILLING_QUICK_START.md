# GCP Billing Monitor - Quick Start Guide

## ⚡ 3 分钟快速设置

### 📋 前置准备

1. **GCP 项目**: `groovy-iris-473015-h3` ✅ (已配置)
2. **Billing Account**: `012E4D-01ACF3-0FF7FC`
3. **Gmail 账号**: 用于发送邮件报告

---

## 🚀 Step 1: 配置 BigQuery Billing Export

### 在 GCP Console 手动操作 (必须)

1. **访问 Billing Export 页面**:
   ```
   https://console.cloud.google.com/billing/012E4D-01ACF3-0FF7FC/export
   ```

2. **配置 BigQuery 导出**:
   - 点击 "BigQuery export" 标签
   - 找到 "Detailed usage cost" 部分
   - 点击 "EDIT SETTINGS"
   - **Project**: `groovy-iris-473015-h3`
   - **Dataset**: `billing_export` (会自动创建)
   - 点击 "SAVE"

3. **验证配置**:
   - ✅ 表格会自动创建为: `gcp_billing_export_resource_v1_012E4D_01ACF3_0FF7FC`
   - ⏱️ 数据需要 24-48 小时才会开始流入
   - 💡 可以先用空数据测试 API

---

## 🔧 Step 2: 配置 Gmail SMTP

### 生成 Gmail App Password

1. **访问 Google Account**:
   ```
   https://myaccount.google.com/apppasswords
   ```

2. **创建 App Password**:
   - App name: `GCP Billing Monitor`
   - 点击 "Create"
   - 复制 16 位密码 (例如: `abcd efgh ijkl mnop`)

3. **更新 `.env` 文件**:
   ```bash
   SMTP_USER=your-gmail@gmail.com
   SMTP_PASSWORD=abcdefghijklmnop  # 去掉空格
   FROM_EMAIL=your-gmail@gmail.com
   BILLING_REPORT_EMAIL=dev02@example.com
   ```

---

## 🤖 Step 3: 运行自动化设置脚本

### 一键设置 Service Account + Cloud Scheduler

```bash
# 确保已登录 gcloud
gcloud auth login
gcloud config set project groovy-iris-473015-h3

# 运行设置脚本
./setup_gcp_billing.sh
```

### 脚本会自动完成:
- ✅ 启用必要的 GCP APIs
- ✅ 创建 Service Account (`billing-monitor`)
- ✅ 授予 BigQuery 权限
- ✅ 创建 Cloud Scheduler job (每天 9 AM 发送报告)

---

## 🧪 Step 4: 本地测试

### 测试 API 是否工作

```bash
# 1. 启动本地服务器
poetry run uvicorn app.main:app --reload

# 2. 测试获取 JSON 报告
curl -X GET "http://localhost:8000/api/v1/billing/report" \
  -H "X-Admin-Key: 0iaiIHuIbnqwiEOKINaZKUzpykAbtnLJjdZpFyeSU_Q"

# 3. 测试发送邮件报告
curl -X POST "http://localhost:8000/api/v1/billing/send-report" \
  -H "X-Admin-Key: 0iaiIHuIbnqwiEOKINaZKUzpykAbtnLJjdZpFyeSU_Q"
```

### 预期结果:
- ✅ JSON 报告包含 `summary`, `cost_data`, `ai_insights`
- ✅ 邮件发送到 `dev02@example.com`
- ✅ HTML 邮件包含成本分析和 AI 建议

---

## 📅 Step 5: 手动触发 Cloud Scheduler (可选)

### 立即测试定时任务

```bash
# 手动运行一次 scheduler job
gcloud scheduler jobs run daily-billing-report --location=us-central1

# 查看执行结果
gcloud scheduler jobs describe daily-billing-report --location=us-central1
```

---

## 🎯 验证清单

- [ ] BigQuery billing export 已配置
- [ ] `.env` 文件有 SMTP 配置
- [ ] Admin API Key 已生成: `0iaiIHuIbnqwiEOKINaZKUzpykAbtnLJjdZpFyeSU_Q`
- [ ] 本地测试 API 成功
- [ ] 邮件发送成功
- [ ] Cloud Scheduler 已创建
- [ ] 手动触发 scheduler 成功

---

## 📊 API Endpoints

| Endpoint | Method | 功能 | 认证 |
|----------|--------|------|------|
| `/api/v1/billing/report` | GET | 返回 JSON 报告 | X-Admin-Key |
| `/api/v1/billing/send-report` | POST | 发送邮件报告 | X-Admin-Key |
| `/api/v1/billing/costs/7days` | GET | 原始费用数据 | X-Admin-Key |

---

## 💰 成本估算

| 服务 | 用量 | 月成本 |
|------|------|--------|
| BigQuery | ~30 queries/月 | $0.30 |
| Cloud Scheduler | 1 job | $0.10 |
| Cloud Run | 最小流量 | $0.30 |
| OpenAI API | 30 reports | $0.60 |
| **总计** | | **~$1.30/月** |

---

## 🐛 常见问题

### Q: BigQuery 找不到数据？
**A**: 等待 48 小时让数据流入。可以先测试 API 结构。

### Q: 邮件发送失败？
**A**: 检查：
1. Gmail App Password 是否正确 (16 位，无空格)
2. SMTP_PORT=587
3. 防火墙是否允许 587 端口

### Q: Scheduler 未触发？
**A**:
```bash
# 查看 logs
gcloud scheduler jobs describe daily-billing-report --location=us-central1
```

---

## 📚 详细文档

- **完整设置**: `docs/BILLING_MONITOR_SETUP.md`
- **部署清单**: `docs/BILLING_MONITOR_DEPLOYMENT_CHECKLIST.md`
- **架构说明**: `docs/BILLING_MONITOR_README.md`

---

## 🎉 完成后

每天早上 9 点 (台北时间)，`dev02@example.com` 会收到包含以下内容的邮件：
- 📊 过去 7 天总费用
- 📈 Top 10 费用最高的服务
- 📉 每日费用趋势图
- 🤖 AI 成本分析和优化建议

---

**版本**: v1.0.0
**最后更新**: 2025-11-30
