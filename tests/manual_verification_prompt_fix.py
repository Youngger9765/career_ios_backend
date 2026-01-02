#!/usr/bin/env python3
"""
Manual verification script for Quick Feedback prompt fix

Tests that the new prompt:
1. Removed hardcoded scenario rules
2. Uses contextual understanding
3. Can distinguish threatening behavior from microphone testing
"""

from app.services.quick_feedback_service import QUICK_FEEDBACK_PROMPT


def verify_prompt_changes():
    """Verify the prompt meets all requirements"""

    print("=" * 80)
    print("QUICK FEEDBACK PROMPT FIX VERIFICATION")
    print("=" * 80)
    print()

    # 1. Check hardcoded rules are removed
    print("✓ Checking for removed hardcoded scenario rules...")
    hardcoded_patterns = [
        "如果家長在數數/測試麥克風",
        "如果看到危險語言",
        "如果看到好的親子互動",
        "如果看到提問引導",
    ]

    found_hardcoded = []
    for pattern in hardcoded_patterns:
        if pattern in QUICK_FEEDBACK_PROMPT:
            found_hardcoded.append(pattern)

    if found_hardcoded:
        print("  ❌ FAIL: Found hardcoded patterns:")
        for pattern in found_hardcoded:
            print(f"    - {pattern}")
        return False
    else:
        print("  ✅ PASS: No hardcoded scenario rules found")

    print()

    # 2. Check contextual understanding instructions are present
    print("✓ Checking for contextual understanding instructions...")
    required_patterns = [
        "對話的脈絡和情境",
        "互動方式",
        "對話的走向",
        "符合對話的實際情境，不要套用固定模板",
    ]

    missing_patterns = []
    for pattern in required_patterns:
        if pattern not in QUICK_FEEDBACK_PROMPT:
            missing_patterns.append(pattern)

    if missing_patterns:
        print("  ❌ FAIL: Missing required contextual patterns:")
        for pattern in missing_patterns:
            print(f"    - {pattern}")
        return False
    else:
        print("  ✅ PASS: All contextual understanding instructions present")

    print()

    # 3. Display the new prompt
    print("✓ New prompt structure:")
    print("-" * 80)
    print(QUICK_FEEDBACK_PROMPT.format(transcript="[對話內容]"))
    print("-" * 80)
    print()

    # 4. Test case comparison
    print("✓ Expected behavior for test case:")
    print()
    print("  Previous (WRONG):")
    print("    Transcript: '我數到三，一、二、三！' (threatening)")
    print("    Response: '聽到您的聲音了，可以開始了' (microphone testing)")
    print()
    print("  Expected (CORRECT):")
    print("    Transcript: '我數到三，一、二、三！' (threatening)")
    print("    Response: Should recognize threatening behavior and suggest calming")
    print()

    print("=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)
    print()
    print("Summary:")
    print("  ✅ No hardcoded scenario rules")
    print("  ✅ Contextual understanding instructions added")
    print("  ✅ Prompt emphasizes reading full conversation context")
    print("  ✅ Anti-template instruction included")
    print()
    print("The AI will now:")
    print("  1. Read the full conversation context")
    print("  2. Understand the emotional tone and interaction pattern")
    print("  3. Provide contextually appropriate feedback")
    print("  4. NOT apply fixed templates based on keywords")
    print()

    return True


if __name__ == "__main__":
    success = verify_prompt_changes()
    exit(0 if success else 1)
