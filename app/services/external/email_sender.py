"""
Email Sender Service - Send HTML email reports
"""
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List

from app.utils.tenant import get_tenant_url_path

logger = logging.getLogger(__name__)


class EmailSenderService:
    """Send HTML email reports via Gmail SMTP or SendGrid"""

    def __init__(self):
        from app.core.config import settings

        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER or ""
        self.smtp_password = settings.SMTP_PASSWORD or ""
        self.from_email = settings.FROM_EMAIL or self.smtp_user
        self.default_to_email = settings.BILLING_REPORT_EMAIL
        self.app_url = settings.APP_URL

    async def send_password_reset_email(
        self,
        to_email: str,
        verification_code: str,
        counselor_name: str = None,
        tenant_id: str = "career",
        source: str | None = None,
    ) -> bool:
        """
        Send password reset email with 6-digit verification code

        Args:
            to_email: Recipient email
            verification_code: 6-digit verification code
            counselor_name: Optional counselor name for personalization
            tenant_id: Tenant ID for customizing email content
            source: Request source ('app' or 'web') - kept for compatibility

        Returns:
            True if sent successfully
        """
        # Tenant name mapping
        tenant_names = {
            "career": "Career",
            "island": "浮島",
            "island_parents": "浮島親子",
        }
        tenant_name = tenant_names.get(tenant_id, "Career")

        subject = f"Password Reset Verification Code - {tenant_name}"

        html_body = self._generate_password_reset_html(
            counselor_name or "User", verification_code, tenant_name
        )

        try:
            return await self._send_email(to_email, subject, html_body)
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
            raise

    async def send_verification_email(
        self,
        to_email: str,
        verification_token: str,
        tenant_id: str = "career",
    ) -> bool:
        """
        Send email verification email

        Args:
            to_email: Recipient email
            verification_token: Email verification token
            tenant_id: Tenant ID for customizing email content

        Returns:
            True if sent successfully
        """
        # Tenant name mapping
        tenant_names = {
            "career": "Career",
            "island": "浮島",
            "island_parents": "浮島親子",
        }
        tenant_name = tenant_names.get(tenant_id, "Career")

        subject = f"Verify Your Email - {tenant_name}"

        # Generate verification URL
        tenant_url_path = get_tenant_url_path(tenant_id)
        if tenant_url_path:
            verify_path = f"/{tenant_url_path}/verify-email"
        else:
            verify_path = "/verify-email"

        verify_url = f"{self.app_url}{verify_path}?token={verification_token}"

        html_body = self._generate_verification_html(to_email, verify_url, tenant_name)

        try:
            return await self._send_email(to_email, subject, html_body)
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
            raise

    async def send_billing_report(
        self,
        report_data: Dict[str, Any],
        to_email: str = None,
    ) -> bool:
        """
        Send billing report email

        Args:
            report_data: Report data from billing_analyzer
            to_email: Recipient email (defaults to configured email)

        Returns:
            True if sent successfully
        """
        to_email = to_email or self.default_to_email

        # Generate HTML email
        subject = self._generate_subject(report_data)
        html_body = self._generate_html_body(report_data)

        try:
            return await self._send_email(to_email, subject, html_body)
        except Exception as e:
            logger.error(f"Failed to send billing report email: {e}")
            raise

    def _generate_password_reset_html(
        self, counselor_name: str, verification_code: str, tenant_name: str = "Career"
    ) -> str:
        """Generate password reset email HTML with verification code"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Password Reset Verification Code</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #1a73e8;
            font-size: 24px;
            margin-bottom: 20px;
        }}
        .content {{
            margin: 20px 0;
            font-size: 16px;
        }}
        .code-container {{
            text-align: center;
            margin: 30px 0;
            padding: 30px;
            background-color: #f8f9fa;
            border-radius: 8px;
        }}
        .verification-code {{
            font-size: 20px;
            font-weight: bold;
            letter-spacing: 4px;
            color: #1a73e8;
            font-family: 'Courier New', monospace;
        }}
        .code-label {{
            font-size: 14px;
            color: #666;
            margin-top: 10px;
        }}
        .warning {{
            margin-top: 30px;
            padding: 15px;
            background-color: #fef7e0;
            border-left: 4px solid #f9ab00;
            border-radius: 4px;
            font-size: 14px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            font-size: 12px;
            color: #666;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Password Reset Verification Code</h1>

        <div class="content">
            <p>Hi {counselor_name},</p>

            <p>We received a request to reset your password for your <strong>{tenant_name}</strong> account.</p>

            <p>Use the verification code below to reset your password. This code will expire in 10 minutes.</p>
        </div>

        <div class="code-container">
            <div class="verification-code">{verification_code}</div>
            <div class="code-label">Enter this code in the app</div>
        </div>

        <div class="warning">
            <p><strong>Security Notice:</strong></p>
            <ul style="margin: 10px 0 0 20px;">
                <li>If you didn't request this password reset, please ignore this email.</li>
                <li>Never share this code with anyone.</li>
                <li>This code will expire in 10 minutes for your security.</li>
                <li>The code can only be used once.</li>
            </ul>
        </div>

        <div class="footer">
            <p>{tenant_name} Platform</p>
            <p>This is an automated email. Please do not reply.</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _generate_verification_html(
        self, email: str, verify_url: str, tenant_name: str = "Career"
    ) -> str:
        """Generate email verification HTML"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #1a73e8;
            font-size: 24px;
            margin-bottom: 20px;
        }}
        .content {{
            margin: 20px 0;
            font-size: 16px;
        }}
        .button-container {{
            text-align: center;
            margin: 30px 0;
        }}
        .verify-button {{
            display: inline-block;
            background-color: #000000 !important;
            color: #ffffff !important;
            text-decoration: none;
            padding: 14px 32px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 16px;
        }}
        .verify-button:hover {{
            background-color: #333333 !important;
        }}
        .info {{
            margin-top: 30px;
            padding: 15px;
            background-color: #e8f4fd;
            border-left: 4px solid #1a73e8;
            border-radius: 4px;
            font-size: 14px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            font-size: 12px;
            color: #666;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Verify Your Email Address</h1>

        <div class="content">
            <p>Welcome to <strong>{tenant_name}</strong>!</p>

            <p>Thank you for registering with us. To complete your registration and activate your account, please verify your email address.</p>

            <p>Click the button below to verify your email. This link will expire in 24 hours.</p>
        </div>

        <div class="button-container">
            <a href="{verify_url}" class="verify-button">Verify Email</a>
        </div>

        <div class="info">
            <p><strong>What happens next?</strong></p>
            <ul style="margin: 10px 0 0 20px;">
                <li>Click the verification button above</li>
                <li>Your account will be activated immediately</li>
                <li>You can then log in and start using our services</li>
            </ul>
        </div>

        <div class="content" style="margin-top: 30px; font-size: 14px; color: #666;">
            <p>If you didn't create an account with {tenant_name}, you can safely ignore this email.</p>
        </div>

        <div class="footer">
            <p>{tenant_name} Platform</p>
            <p>This is an automated email. Please do not reply.</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _generate_subject(self, report_data: Dict[str, Any]) -> str:
        """Generate email subject"""
        report_date = datetime.fromisoformat(report_data["report_date"]).strftime(
            "%Y-%m-%d"
        )
        summary = report_data.get("summary", {})
        total_cost = summary.get("total_cost", 0)
        currency = summary.get("currency", "USD")

        return f"GCP Cost Report - Last 7 Days - {report_date} (${total_cost:.2f} {currency})"

    def _generate_html_body(self, report_data: Dict[str, Any]) -> str:
        """Generate HTML email body"""
        summary = report_data.get("summary", {})
        cost_data = report_data.get("cost_data", [])
        ai_insights = report_data.get("ai_insights", {})

        # Build top services table
        top_services = self._get_top_services(cost_data, limit=10)
        services_table = self._build_services_table(top_services)

        # Build daily trend chart (ASCII art table)
        daily_trend = self._get_daily_trend(cost_data)
        trend_table = self._build_trend_table(daily_trend)

        # Format AI insights
        ai_analysis = ai_insights.get("analysis_text", "無分析資料")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GCP Cost Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #1a73e8;
            border-bottom: 3px solid #1a73e8;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #1a73e8;
            margin-top: 30px;
        }}
        .summary {{
            background-color: #e8f0fe;
            border-left: 4px solid #1a73e8;
            padding: 15px;
            margin: 20px 0;
        }}
        .summary-item {{
            display: flex;
            justify-content: space-between;
            margin: 8px 0;
        }}
        .summary-label {{
            font-weight: 600;
        }}
        .summary-value {{
            color: #1a73e8;
            font-weight: bold;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background-color: #1a73e8;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .positive {{
            color: #0f9d58;
            font-weight: bold;
        }}
        .negative {{
            color: #ea4335;
            font-weight: bold;
        }}
        .ai-insights {{
            background-color: #fef7e0;
            border-left: 4px solid #f9ab00;
            padding: 15px;
            margin: 20px 0;
            white-space: pre-wrap;
            font-size: 14px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            font-size: 12px;
            color: #666;
            text-align: center;
        }}
        .trend-bar {{
            background-color: #1a73e8;
            height: 20px;
            display: inline-block;
            margin-right: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>GCP Cost Report - Last 7 Days</h1>

        <div class="summary">
            <h2>Summary</h2>
            <div class="summary-item">
                <span class="summary-label">Total Cost:</span>
                <span class="summary-value">${summary.get('total_cost', 0):.2f} {summary.get('currency', 'USD')}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Daily Average:</span>
                <span class="summary-value">${summary.get('avg_daily', 0):.2f} {summary.get('currency', 'USD')}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Services Count:</span>
                <span class="summary-value">{summary.get('services_count', 0)}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Date Range:</span>
                <span class="summary-value">{summary.get('date_range', {}).get('start', 'N/A')} to {summary.get('date_range', {}).get('end', 'N/A')}</span>
            </div>
        </div>

        <h2>Top Services by Cost</h2>
        {services_table}

        <h2>Daily Cost Trend</h2>
        {trend_table}

        <h2>AI Insights & Recommendations</h2>
        <div class="ai-insights">
{ai_analysis}
        </div>

        <div class="footer">
            <p>Report generated at: {datetime.fromisoformat(report_data['report_date']).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <p>GCP Billing Monitor | Powered by OpenAI</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _get_top_services(self, cost_data: List[Dict], limit: int = 10) -> List[Dict]:
        """Aggregate costs by service and return top N"""
        service_costs = {}

        for item in cost_data:
            service = item["service"]
            cost = item["cost"]

            if service not in service_costs:
                service_costs[service] = {
                    "service": service,
                    "total_cost": 0,
                    "currency": item["currency"],
                    "data_points": [],
                }

            service_costs[service]["total_cost"] += cost
            service_costs[service]["data_points"].append(item)

        # Sort by total cost descending
        sorted_services = sorted(
            service_costs.values(), key=lambda x: x["total_cost"], reverse=True
        )

        return sorted_services[:limit]

    def _build_services_table(self, top_services: List[Dict]) -> str:
        """Build HTML table for top services"""
        if not top_services:
            return "<p>No data available</p>"

        rows = []
        for i, svc in enumerate(top_services, 1):
            # Calculate average change
            changes = [
                d.get("change_pct")
                for d in svc["data_points"]
                if d.get("change_pct") is not None
            ]
            avg_change = sum(changes) / len(changes) if changes else 0
            change_class = (
                "positive" if avg_change < 0 else "negative" if avg_change > 0 else ""
            )
            change_sign = "+" if avg_change > 0 else ""

            rows.append(
                f"""
                <tr>
                    <td>{i}</td>
                    <td>{svc['service']}</td>
                    <td>${svc['total_cost']:.2f} {svc['currency']}</td>
                    <td class="{change_class}">{change_sign}{avg_change:.1f}%</td>
                </tr>
            """
            )

        return f"""
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Service</th>
                    <th>Total Cost</th>
                    <th>Avg Change</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
        """

    def _get_daily_trend(self, cost_data: List[Dict]) -> List[Dict]:
        """Aggregate costs by date"""
        daily_costs = {}

        for item in cost_data:
            date = item["date"]
            cost = item["cost"]

            if date not in daily_costs:
                daily_costs[date] = {
                    "date": date,
                    "total_cost": 0,
                    "currency": item["currency"],
                }

            daily_costs[date]["total_cost"] += cost

        # Sort by date
        sorted_daily = sorted(daily_costs.values(), key=lambda x: x["date"])

        return sorted_daily

    def _build_trend_table(self, daily_trend: List[Dict]) -> str:
        """Build HTML table for daily trend"""
        if not daily_trend:
            return "<p>No data available</p>"

        # Calculate max cost for bar chart scaling
        max_cost = max(d["total_cost"] for d in daily_trend) if daily_trend else 1

        rows = []
        for day in daily_trend:
            bar_width = int((day["total_cost"] / max_cost) * 300)  # Max 300px
            rows.append(
                f"""
                <tr>
                    <td>{day['date']}</td>
                    <td>${day['total_cost']:.2f} {day['currency']}</td>
                    <td>
                        <div class="trend-bar" style="width: {bar_width}px;"></div>
                    </td>
                </tr>
            """
            )

        return f"""
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Total Cost</th>
                    <th>Trend</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
        """

    async def _send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """
        Send email via SMTP

        Args:
            to_email: Recipient email
            subject: Email subject
            html_body: HTML email body

        Returns:
            True if sent successfully
        """
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials not configured, skipping email send")
            return False

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to_email

        # Attach HTML body
        html_part = MIMEText(html_body, "html", "utf-8")
        msg.attach(html_part)

        # Send via SMTP
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Billing report email sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise


# Singleton instance
email_sender = EmailSenderService()
