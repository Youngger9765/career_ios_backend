"""
Test to show exact cost difference between before and after the fix

Run with: poetry run python tests/manual/test_cost_difference_before_after.py
"""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.session_analysis_log import SessionAnalysisLog
from app.models.session_usage import SessionUsage


async def calculate_costs():
    """Calculate costs with and without the fix"""
    engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""))

    with Session(engine) as db:
        now = datetime.now(timezone.utc)
        start_time_week = now - timedelta(days=7)

        print("=" * 80)
        print("COST COMPARISON: Before vs After Fix")
        print("=" * 80)
        print(f"Time Range: Last 7 days (from {start_time_week.strftime('%Y-%m-%d %H:%M:%S')})")
        print()

        # ============================================
        # ElevenLabs Cost (Same in both cases)
        # ============================================
        ELEVENLABS_RATE = 0.40 / 3600.0  # $0.40 per hour

        usage_query = select(SessionUsage).where(SessionUsage.created_at >= start_time_week)
        usage_records = db.execute(usage_query).scalars().all()

        total_seconds = sum(r.duration_seconds or 0 for r in usage_records)
        elevenlabs_cost = total_seconds * ELEVENLABS_RATE

        print(f"📊 ElevenLabs Cost (same in both cases):")
        print(f"   Sessions: {len(usage_records)}")
        print(f"   Duration: {total_seconds / 3600:.2f} hours")
        print(f"   Cost: ${elevenlabs_cost:.4f}")
        print()

        # ============================================
        # Gemini Cost - BEFORE FIX (ALL TIME - WRONG)
        # ============================================
        all_analysis = db.execute(select(SessionAnalysisLog)).scalars().all()
        gemini_cost_before = float(sum(log.estimated_cost_usd or 0 for log in all_analysis))

        print(f"🔴 Gemini Cost - BEFORE FIX (WRONG - includes all history):")
        print(f"   Analysis Logs: {len(all_analysis)}")
        print(f"   Cost: ${gemini_cost_before:.4f}")
        print()

        # ============================================
        # Gemini Cost - AFTER FIX (TIME FILTERED - CORRECT)
        # ============================================
        filtered_analysis = db.execute(
            select(SessionAnalysisLog).where(SessionAnalysisLog.analyzed_at >= start_time_week)
        ).scalars().all()
        gemini_cost_after = float(sum(log.estimated_cost_usd or 0 for log in filtered_analysis))

        print(f"✅ Gemini Cost - AFTER FIX (CORRECT - last 7 days only):")
        print(f"   Analysis Logs: {len(filtered_analysis)}")
        print(f"   Cost: ${gemini_cost_after:.4f}")
        print()

        # ============================================
        # TOTAL COST COMPARISON
        # ============================================
        total_before = elevenlabs_cost + gemini_cost_before
        total_after = elevenlabs_cost + gemini_cost_after
        difference = total_before - total_after
        inflation_pct = ((total_before / total_after - 1) * 100) if total_after > 0 else 0

        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total Cost BEFORE fix: ${total_before:.4f}")
        print(f"Total Cost AFTER fix:  ${total_after:.4f}")
        print(f"Difference:            ${difference:.4f}")
        print(f"Inflation:             {inflation_pct:.1f}%")
        print()

        # ============================================
        # BREAKDOWN BY DATE
        # ============================================
        print("=" * 80)
        print("BREAKDOWN: Where did the extra cost come from?")
        print("=" * 80)

        # Group analysis logs by date
        from collections import defaultdict

        logs_by_date = defaultdict(lambda: {"count": 0, "cost": 0.0})

        for log in all_analysis:
            date = log.analyzed_at.date()
            logs_by_date[date]["count"] += 1
            logs_by_date[date]["cost"] += float(log.estimated_cost_usd or 0)

        # Sort by date
        sorted_dates = sorted(logs_by_date.keys())

        # Show last 10 dates
        print(f"\nLast 10 dates with analysis logs:")
        for date in sorted_dates[-10:]:
            data = logs_by_date[date]
            is_in_range = (now.date() - date).days <= 7
            marker = "✅" if is_in_range else "❌"
            print(f"{marker} {date}: {data['count']:3d} logs, ${data['cost']:.4f}")

        # Calculate old data contribution
        old_dates = [d for d in sorted_dates if (now.date() - d).days > 7]
        old_logs_count = sum(logs_by_date[d]["count"] for d in old_dates)
        old_logs_cost = sum(logs_by_date[d]["cost"] for d in old_dates)

        print()
        print(f"❌ Old data (> 7 days): {old_logs_count} logs, ${old_logs_cost:.4f}")
        print(f"✅ Recent data (≤ 7 days): {len(filtered_analysis)} logs, ${gemini_cost_after:.4f}")
        print()

        # ============================================
        # RECOMMENDATIONS
        # ============================================
        print("=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        print()
        print("1. Deploy this fix to staging ASAP")
        print("2. Verify on staging dashboard that costs change when switching time ranges")
        print("3. Test all three endpoints: Top Users, User Segments, CSV Export")
        print("4. Deploy to production after verification")
        print()
        print("Expected behavior after fix:")
        print("- Selecting 'Today' should show only today's costs")
        print("- Selecting '7 Days' should show only last 7 days costs")
        print("- Selecting '30 Days' should show only last 30 days costs")
        print()


if __name__ == "__main__":
    asyncio.run(calculate_costs())
