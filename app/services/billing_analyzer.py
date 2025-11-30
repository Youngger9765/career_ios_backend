"""
Billing Analyzer Service - GCP Cost Analysis with AI
"""
import os
from datetime import datetime
from typing import Any, Dict, List

from google.cloud import bigquery

from app.services.openai_service import OpenAIService


class BillingAnalyzerService:
    """Analyze GCP billing data from BigQuery and generate AI insights"""

    def __init__(self):
        self.project_id = os.getenv("GCS_PROJECT", "groovy-iris-473015-h3")
        self.dataset_id = os.getenv("BILLING_DATASET_ID", "billing_export")
        self.table_id = os.getenv("BILLING_TABLE_ID", "gcp_billing_export")
        self._client = None  # Lazy initialization
        self.ai_service = OpenAIService()

    @property
    def client(self) -> bigquery.Client:
        """Lazy-load BigQuery client to avoid authentication errors in CI/testing"""
        if self._client is None:
            self._client = bigquery.Client(project=self.project_id)
        return self._client

    async def get_7_day_cost_trend(self) -> List[Dict[str, Any]]:
        """Query BigQuery for last 7 days cost trend"""
        query = f"""
        WITH daily_costs AS (
          SELECT
            DATE(usage_start_time) as usage_date,
            service.description as service_name,
            SUM(cost) as daily_cost,
            currency
          FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
          WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
            AND cost > 0
          GROUP BY usage_date, service_name, currency
          ORDER BY usage_date DESC, daily_cost DESC
        )
        SELECT
          usage_date,
          service_name,
          ROUND(daily_cost, 2) as cost,
          currency,
          ROUND(SAFE_DIVIDE(
            daily_cost - LAG(daily_cost) OVER (
              PARTITION BY service_name
              ORDER BY usage_date
            ),
            LAG(daily_cost) OVER (
              PARTITION BY service_name
              ORDER BY usage_date
            )
          ) * 100, 2) as pct_change
        FROM daily_costs
        ORDER BY usage_date DESC, cost DESC
        LIMIT 100;
        """

        query_job = self.client.query(query)
        results = query_job.result()

        return [
            {
                "date": str(row.usage_date),
                "service": row.service_name,
                "cost": float(row.cost),
                "currency": row.currency,
                "change_pct": float(row.pct_change) if row.pct_change else None,
            }
            for row in results
        ]

    async def get_summary_stats(self, cost_data: List[Dict]) -> Dict[str, Any]:
        """Calculate summary statistics"""
        if not cost_data:
            return {"total_cost": 0, "avg_daily": 0, "services_count": 0}

        total_cost = sum(item["cost"] for item in cost_data)
        unique_dates = len(set(item["date"] for item in cost_data))
        unique_services = len(set(item["service"] for item in cost_data))

        return {
            "total_cost": round(total_cost, 2),
            "avg_daily": round(total_cost / unique_dates, 2) if unique_dates > 0 else 0,
            "services_count": unique_services,
            "currency": cost_data[0]["currency"] if cost_data else "USD",
            "date_range": {
                "start": min(item["date"] for item in cost_data),
                "end": max(item["date"] for item in cost_data),
            },
        }

    async def analyze_with_ai(
        self, cost_data: List[Dict], summary: Dict
    ) -> Dict[str, Any]:
        """Use Gemini to analyze cost trends and provide insights"""

        # Build prompt
        prompt = f"""你是 GCP 成本分析專家。請分析以下 7 天的費用數據並提供洞見。

## 費用總覽
- 總費用: ${summary['total_cost']} {summary['currency']}
- 日均費用: ${summary['avg_daily']} {summary['currency']}
- 使用服務數: {summary['services_count']}
- 日期範圍: {summary['date_range']['start']} 至 {summary['date_range']['end']}

## 詳細數據
{self._format_cost_data_for_prompt(cost_data[:50])}

## 分析任務
請提供以下分析（使用繁體中文）：

1. **費用趨勢摘要**
   - 整體趨勢（上升/下降/穩定）
   - 主要變化日期

2. **成本熱點**
   - Top 3 最高費用服務
   - 哪些服務費用增長最快

3. **異常警示**
   - 是否有異常飆升（>50% 增長）
   - 可能的原因

4. **優化建議**
   - 3-5 個具體的成本優化建議
   - 預估可節省金額

5. **行動項目**
   - 需要立即檢查的項目（如有）
   - 建議的監控指標

請以清晰的 Markdown 格式輸出，包含表格和重點標示。
"""

        # Call OpenAI for analysis
        messages = [
            {
                "role": "system",
                "content": "你是 GCP 成本分析專家，專門分析雲端費用並提供優化建議。",
            },
            {"role": "user", "content": prompt},
        ]
        analysis = await self.ai_service.chat_completion(
            messages, temperature=0.3, max_tokens=2000
        )

        return {
            "analysis_text": analysis,
            "generated_at": datetime.utcnow().isoformat(),
            "data_points": len(cost_data),
        }

    def _format_cost_data_for_prompt(self, cost_data: List[Dict]) -> str:
        """Format cost data for AI prompt"""
        lines = ["| 日期 | 服務 | 費用 | 變化 |", "|------|------|------|------|"]

        for item in cost_data:
            change = (
                f"{item['change_pct']:+.1f}%"
                if item["change_pct"] is not None
                else "N/A"
            )
            lines.append(
                f"| {item['date']} | {item['service']} | ${item['cost']:.2f} | {change} |"
            )

        return "\n".join(lines)

    async def generate_full_report(self) -> Dict[str, Any]:
        """Generate complete billing report with AI analysis"""
        # 1. Fetch cost data
        cost_data = await self.get_7_day_cost_trend()

        # 2. Calculate summary
        summary = await self.get_summary_stats(cost_data)

        # 3. AI analysis
        ai_insights = await self.analyze_with_ai(cost_data, summary)

        return {
            "report_date": datetime.utcnow().isoformat(),
            "summary": summary,
            "cost_data": cost_data,
            "ai_insights": ai_insights,
        }


# Singleton instance
billing_analyzer = BillingAnalyzerService()
