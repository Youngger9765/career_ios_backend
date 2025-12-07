#!/usr/bin/env python3
"""
Database Management Script - 自動化 migration 管理

Usage:
    python scripts/manage_db.py check       # 檢查當前狀態
    python scripts/manage_db.py reset       # 重置 Alembic（清除版本表）
    python scripts/manage_db.py generate    # 從 models 自動生成 migration
    python scripts/manage_db.py upgrade     # 執行 migration
    python scripts/manage_db.py auto        # 自動：生成 + 執行
"""

import os
import subprocess
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import settings  # noqa: E402


def get_database_url():
    """Get the direct database URL for migrations"""
    return os.getenv("DATABASE_URL_DIRECT") or settings.DATABASE_URL


def check_alembic_table():
    """檢查 Alembic 版本表"""
    engine = create_engine(get_database_url())
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')"
            )
        )
        exists = result.scalar()

        if exists:
            version_result = conn.execute(
                text("SELECT version_num FROM alembic_version")
            )
            version = version_result.scalar()
            print("✅ Alembic 版本表存在")
            print(f"   當前版本: {version or '無'}")
            return version
        else:
            print("❌ Alembic 版本表不存在")
            return None


def check_models():
    """檢查所有 models"""
    from app.core.database import Base

    # Import all models

    tables = Base.metadata.tables.keys()
    print(f"\n📋 偵測到 {len(tables)} 個 Model 表格:")
    for table in sorted(tables):
        print(f"   - {table}")

    return tables


def reset_alembic():
    """重置 Alembic 版本表（保留資料表）"""
    engine = create_engine(get_database_url())
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        conn.commit()
    print("✅ Alembic 版本表已重置")


def check_existing_tables():
    """檢查資料庫中已存在的表"""
    engine = create_engine(get_database_url())
    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
            )
        )
        tables = [row[0] for row in result]

        if tables:
            print(f"\n📊 資料庫中現有 {len(tables)} 個表格:")
            for table in tables:
                print(f"   - {table}")
        else:
            print("\n📊 資料庫中沒有任何表格")

        return tables


def generate_migration(message="auto generated"):
    """生成 migration"""
    print(f"\n🔨 生成 migration: {message}")
    result = subprocess.run(
        ["alembic", "revision", "--autogenerate", "-m", message],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("✅ Migration 生成成功")
        print(result.stdout)
        return True
    else:
        print("❌ Migration 生成失敗")
        print(result.stderr)
        return False


def run_upgrade():
    """執行 migration"""
    print("\n⬆️  執行 migration upgrade")
    result = subprocess.run(
        ["alembic", "upgrade", "head"], capture_output=True, text=True
    )

    if result.returncode == 0:
        print("✅ Migration 執行成功")
        print(result.stdout)
        return True
    else:
        print("❌ Migration 執行失敗")
        print(result.stderr)
        return False


def stamp_head():
    """標記當前資料庫為最新版本（不執行 migration）"""
    print("\n📌 標記資料庫為最新版本")
    result = subprocess.run(
        ["alembic", "stamp", "head"], capture_output=True, text=True
    )

    if result.returncode == 0:
        print("✅ 標記成功")
        print(result.stdout)
        return True
    else:
        print("❌ 標記失敗")
        print(result.stderr)
        return False


def check():
    """檢查當前狀態"""
    print("=" * 60)
    print("🔍 檢查資料庫狀態")
    print("=" * 60)

    check_alembic_table()
    check_models()
    check_existing_tables()


def reset():
    """重置 Alembic"""
    print("=" * 60)
    print("🔄 重置 Alembic")
    print("=" * 60)

    confirm = input("⚠️  確定要重置 Alembic 版本表嗎？（保留資料表）[y/N]: ")
    if confirm.lower() == "y":
        reset_alembic()
        print(
            "\n💡 提示：現在可以執行 'python scripts/manage_db.py generate' 生成新的 migration"
        )
    else:
        print("❌ 取消重置")


def generate():
    """生成 migration"""
    print("=" * 60)
    print("🔨 生成 Migration")
    print("=" * 60)

    message = (
        input("Migration 訊息（按 Enter 使用預設）: ").strip()
        or "auto generated from models"
    )
    generate_migration(message)


def upgrade():
    """執行 migration"""
    print("=" * 60)
    print("⬆️  執行 Migration")
    print("=" * 60)

    run_upgrade()


def auto():
    """自動：生成 + 執行"""
    print("=" * 60)
    print("🤖 自動化 Migration")
    print("=" * 60)

    check()

    print("\n" + "=" * 60)
    existing_tables = check_existing_tables()

    if len(existing_tables) > 1:  # 除了 alembic_version 外有其他表
        print("\n⚠️  資料庫已有現存表格")
        print("建議選項:")
        print("  1. 執行 'reset' 清除 Alembic 版本後重新生成")
        print("  2. 執行 'stamp head' 標記當前狀態為最新版本")

        choice = input("\n選擇 [1/2/skip]: ").strip()
        if choice == "1":
            reset_alembic()
            if generate_migration("initial schema from models"):
                run_upgrade()
        elif choice == "2":
            stamp_head()
        else:
            print("❌ 跳過")
    else:
        print("\n✨ 資料庫是空的，開始自動化流程...")
        if generate_migration("initial schema from models"):
            run_upgrade()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "check":
        check()
    elif command == "reset":
        reset()
    elif command == "generate":
        generate()
    elif command == "upgrade":
        upgrade()
    elif command == "auto":
        auto()
    else:
        print(f"❌ 未知命令: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
