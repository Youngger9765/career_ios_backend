#!/usr/bin/env python3
"""
Test multi-agent configuration

Verifies that:
1. All agent IDs are properly configured
2. Agent selector function works correctly
3. Each configured agent can be accessed

Usage:
    poetry run python scripts/test_multi_agent_config.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings  # noqa: E402
from app.services.codeer_client import CodeerClient, get_codeer_agent_id  # noqa: E402


def test_config():
    """Test that agent IDs are configured"""
    print("=" * 80)
    print("📋 CONFIGURATION TEST")
    print("=" * 80)

    agents = {
        "CODEER_DEFAULT_AGENT": settings.CODEER_DEFAULT_AGENT,
        "CODEER_AGENT_CLAUDE_SONNET": settings.CODEER_AGENT_CLAUDE_SONNET,
        "CODEER_AGENT_GEMINI_FLASH": settings.CODEER_AGENT_GEMINI_FLASH,
        "CODEER_AGENT_GPT5_MINI": settings.CODEER_AGENT_GPT5_MINI,
    }

    configured = []
    missing = []

    for name, value in agents.items():
        if value:
            configured.append(f"✅ {name}: {value}")
        else:
            missing.append(f"❌ {name}: Not configured")

    print("\n📝 Configured agents:")
    for item in configured:
        print(f"  {item}")

    if missing:
        print("\n⚠️  Missing agents:")
        for item in missing:
            print(f"  {item}")
        print("\n💡 To configure missing agents:")
        print("  1. Create agents at https://app.codeer.ai/agents")
        print("  2. Run: poetry run python scripts/list_codeer_agents.py")
        print("  3. Update .env with agent IDs")
    else:
        print("\n✅ All agents configured!")

    print("\n" + "=" * 80)
    return len(missing) == 0


def test_agent_selector():
    """Test agent selector function"""
    print("\n📋 AGENT SELECTOR TEST")
    print("=" * 80)

    test_cases = [
        ("claude-sonnet", "Claude Sonnet 4.5"),
        ("claude", "Claude Sonnet 4.5"),
        ("gemini-flash", "Gemini 2.5 Flash"),
        ("gemini", "Gemini 2.5 Flash"),
        ("gpt5-mini", "GPT-5 Mini"),
        ("gpt5", "GPT-5 Mini"),
        ("gpt", "GPT-5 Mini"),
    ]

    all_passed = True

    for model, description in test_cases:
        try:
            agent_id = get_codeer_agent_id(model)
            if agent_id:
                print(f"✅ {model:15s} → {agent_id[:16]}... ({description})")
            else:
                print(f"⚠️  {model:15s} → No agent ID configured ({description})")
                all_passed = False
        except Exception as e:
            print(f"❌ {model:15s} → ERROR: {e}")
            all_passed = False

    # Test invalid model
    print("\n🧪 Testing invalid model:")
    try:
        agent_id = get_codeer_agent_id("invalid-model")
        print(f"❌ Should have raised error, but got: {agent_id}")
        all_passed = False
    except Exception as e:
        print(f"✅ Correctly rejected invalid model: {e}")

    print("\n" + "=" * 80)
    return all_passed


async def test_agent_access():
    """Test actual API access to configured agents"""
    print("\n📋 AGENT ACCESS TEST")
    print("=" * 80)

    all_passed = True

    # Test each configured agent
    agents_to_test = []

    if settings.CODEER_AGENT_CLAUDE_SONNET:
        agents_to_test.append(("claude-sonnet", "Claude Sonnet 4.5"))
    if settings.CODEER_AGENT_GEMINI_FLASH:
        agents_to_test.append(("gemini-flash", "Gemini 2.5 Flash"))
    if settings.CODEER_AGENT_GPT5_MINI:
        agents_to_test.append(("gpt5-mini", "GPT-5 Mini"))

    if not agents_to_test:
        print("⚠️  No agents configured to test")
        print("\n💡 Configure agents in .env to test API access")
        return False

    for model, description in agents_to_test:
        try:
            agent_id = get_codeer_agent_id(model)
            print(f"\n🧪 Testing {description} ({model})...")
            print(f"   Agent ID: {agent_id}")

            async with CodeerClient() as client:
                # Try to create a test chat
                chat = await client.create_chat(name=f"Test-{model}", agent_id=agent_id)
                print(f"   ✅ Successfully created chat: {chat.get('id')}")

        except Exception as e:
            print(f"   ❌ Failed to access agent: {e}")
            all_passed = False

    print("\n" + "=" * 80)
    return all_passed


async def main():
    """Run all tests"""
    print("\n🔍 Multi-Agent Configuration Test")
    print("=" * 80)
    print()

    # Run tests
    config_ok = test_config()
    selector_ok = test_agent_selector()
    access_ok = await test_agent_access()

    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 80)
    print(f"{'Configuration Test:':<25} {'✅ PASSED' if config_ok else '❌ FAILED'}")
    print(f"{'Agent Selector Test:':<25} {'✅ PASSED' if selector_ok else '❌ FAILED'}")
    print(
        f"{'Agent Access Test:':<25} {'✅ PASSED' if access_ok else '⚠️  SKIPPED/FAILED'}"
    )
    print("=" * 80)

    if config_ok and selector_ok and access_ok:
        print("\n🎉 All tests passed! Multi-agent configuration is ready.")
        return 0
    elif config_ok and selector_ok:
        print("\n⚠️  Configuration OK, but some agents not yet published.")
        print(
            "   Run when agents are ready: poetry run python scripts/test_multi_agent_config.py"
        )
        return 0
    else:
        print("\n❌ Some tests failed. Please fix configuration.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
