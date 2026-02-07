"""
Fix historical emotion analysis model names in session_analysis_logs

Problem:
- All Emotion API logs are incorrectly marked as "gemini-3-flash-preview"
- Should be "gemini-flash-lite-latest"

Detection:
- analysis_result->>'analysis_type' = 'emotion_feedback'

This script:
1. Identifies affected records
2. Shows preview of changes
3. Updates model_name to correct value
4. Logs all changes for audit trail

Created: 2025-02-07
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def preview_changes():
    """Preview records that will be updated"""
    query = """
        SELECT
            id,
            model_name,
            analysis_result->>'analysis_type' as analysis_type,
            analyzed_at
        FROM session_analysis_logs
        WHERE model_name = 'gemini-3-flash-preview'
          AND analysis_result->>'analysis_type' = 'emotion_feedback'
        ORDER BY analyzed_at DESC
        LIMIT 10;
    """

    with engine.connect() as conn:
        result = conn.execute(text(query))
        records = result.fetchall()

        if not records:
            logger.info("✅ No records need to be fixed")
            return 0

        logger.info(f"Found {len(records)} records to fix (showing first 10):")
        logger.info("-" * 80)
        for record in records:
            logger.info(
                f"ID: {record.id} | Model: {record.model_name} | "
                f"Type: {record.analysis_type} | Date: {record.analyzed_at}"
            )
        logger.info("-" * 80)

        # Get total count
        count_query = """
            SELECT COUNT(*)
            FROM session_analysis_logs
            WHERE model_name = 'gemini-3-flash-preview'
              AND analysis_result->>'analysis_type' = 'emotion_feedback';
        """
        total_result = conn.execute(text(count_query))
        total_count = total_result.scalar()

        logger.info(f"Total records to update: {total_count}")
        return total_count


def fix_emotion_model_names():
    """Update incorrect model names for emotion analysis logs"""
    update_query = """
        UPDATE session_analysis_logs
        SET model_name = 'gemini-flash-lite-latest'
        WHERE model_name = 'gemini-3-flash-preview'
          AND analysis_result->>'analysis_type' = 'emotion_feedback';
    """

    with engine.connect() as conn:
        result = conn.execute(text(update_query))
        conn.commit()
        updated_count = result.rowcount

        logger.info(f"✅ Updated {updated_count} records")
        return updated_count


def verify_fix():
    """Verify the fix was applied correctly"""
    query = """
        SELECT
            model_name,
            analysis_result->>'analysis_type' as analysis_type,
            COUNT(*) as count
        FROM session_analysis_logs
        WHERE analysis_result->>'analysis_type' = 'emotion_feedback'
        GROUP BY model_name, analysis_result->>'analysis_type'
        ORDER BY count DESC;
    """

    with engine.connect() as conn:
        result = conn.execute(text(query))
        records = result.fetchall()

        logger.info("\n📊 Verification - Emotion analysis model distribution:")
        logger.info("-" * 80)
        for record in records:
            logger.info(
                f"Model: {record.model_name} | Type: {record.analysis_type} | Count: {record.count}"
            )
        logger.info("-" * 80)

        # Check for any remaining incorrect records
        check_query = """
            SELECT COUNT(*)
            FROM session_analysis_logs
            WHERE model_name = 'gemini-3-flash-preview'
              AND analysis_result->>'analysis_type' = 'emotion_feedback';
        """
        check_result = conn.execute(text(check_query))
        remaining_count = check_result.scalar()

        if remaining_count > 0:
            logger.warning(f"⚠️  {remaining_count} records still have incorrect model name!")
            return False
        else:
            logger.info("✅ All emotion analysis records have correct model name")
            return True


def main():
    """Main execution flow"""
    logger.info("=" * 80)
    logger.info("Fix Emotion Model Names Script")
    logger.info("=" * 80)

    # Step 1: Preview changes
    logger.info("\n[Step 1] Previewing changes...")
    total_count = preview_changes()

    if total_count == 0:
        logger.info("No changes needed. Exiting.")
        return

    # Step 2: Confirm with user
    logger.info(f"\n[Step 2] Ready to update {total_count} records")
    response = input("Continue? (yes/no): ").strip().lower()

    if response != "yes":
        logger.info("Update cancelled by user")
        return

    # Step 3: Apply fix
    logger.info("\n[Step 3] Applying fix...")
    updated_count = fix_emotion_model_names()

    # Step 4: Verify
    logger.info("\n[Step 4] Verifying fix...")
    success = verify_fix()

    if success:
        logger.info("\n✅ Migration completed successfully")
        logger.info(f"Total records updated: {updated_count}")
    else:
        logger.error("\n❌ Migration completed with warnings")


if __name__ == "__main__":
    main()
