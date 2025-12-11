#!/usr/bin/env python3
"""
List all Codeer published agents with their IDs and models

Usage:
    poetry run python scripts/list_codeer_agents.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.codeer_client import CodeerClient  # noqa: E402


async def main():
    """List all Codeer agents"""
    print("🔍 Fetching Codeer agents...\n")

    async with CodeerClient() as client:
        try:
            agents = await client.list_published_agents()

            if not agents:
                print("❌ No agents found!")
                return

            print(f"✅ Found {len(agents)} agents:\n")
            print("=" * 80)

            for i, agent in enumerate(agents, 1):
                agent_id = agent.get("id", "N/A")
                name = agent.get("name", "Unnamed")
                llm_model = agent.get("llm_model", "Unknown")
                created_at = agent.get("created_at", "N/A")

                print(f"\n{i}. {name}")
                print(f"   ID: {agent_id}")
                print(f"   Model: {llm_model}")
                print(f"   Created: {created_at}")
                print("-" * 80)

            print("\n" + "=" * 80)
            print("\n📋 Configuration template for .env:\n")

            # Generate .env template
            for agent in agents:
                name = agent.get("name", "")
                agent_id = agent.get("id", "")
                llm_model = agent.get("llm_model", "")

                # Try to extract model type from name or llm_model
                if "claude" in name.lower() or "claude" in llm_model.lower():
                    print(f"CODEER_AGENT_CLAUDE_SONNET={agent_id}  # {name}")
                elif "gemini" in name.lower() or "gemini" in llm_model.lower():
                    print(f"CODEER_AGENT_GEMINI_FLASH={agent_id}  # {name}")
                elif "gpt" in name.lower() or "gpt" in llm_model.lower():
                    print(f"CODEER_AGENT_GPT5_MINI={agent_id}  # {name}")

        except Exception as e:
            print(f"❌ Error: {e}")
            return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
