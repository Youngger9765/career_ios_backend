"""
Backfill script: Generate markdown for existing reports

Usage:
    python scripts/backfill_report_markdown.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.report import Report
from app.utils.report_formatters import create_formatter
from sqlalchemy import select


def backfill_markdown():
    """Generate markdown for all existing reports that don't have it"""
    db = SessionLocal()
    formatter = create_formatter("markdown")

    try:
        # Find reports without markdown
        result = db.execute(
            select(Report).where(
                (Report.content_json.isnot(None))
                & (Report.content_markdown.is_(None))
            )
        )
        reports = result.scalars().all()

        print(f"Found {len(reports)} reports to backfill")

        for i, report in enumerate(reports, 1):
            try:
                # Generate markdown from content_json
                if report.content_json:
                    report.content_markdown = formatter.format(report.content_json)

                # Generate markdown from edited_content_json if exists
                if report.edited_content_json:
                    report.edited_content_markdown = formatter.format(report.edited_content_json)

                db.commit()
                print(f"[{i}/{len(reports)}] Updated report {report.id}")

            except Exception as e:
                print(f"[{i}/{len(reports)}] Error updating report {report.id}: {e}")
                db.rollback()
                continue

        print(f"\n✅ Backfill complete! Updated {len(reports)} reports")

    except Exception as e:
        print(f"❌ Error during backfill: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    backfill_markdown()
