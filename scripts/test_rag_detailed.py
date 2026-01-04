#!/usr/bin/env python3
"""
Test RAG Integration with Detailed Career Transcript

This script tests whether RAG can be triggered with a longer, more detailed
career-related conversation.
"""

import httpx

STAGING_URL = "https://career-app-api-staging-kxaznpplqq-uc.a.run.app"
API_ENDPOINT = f"{STAGING_URL}/api/v1/realtime/analyze"

# More detailed career-related transcript
detailed_transcript = """
諮詢師：你提到想要轉職，能多說一些你目前的想法嗎？
案主：我在目前公司工作了五年，但覺得職涯發展遇到瓶頸。我想要轉換到科技業，但不知道怎麼開始。
諮詢師：聽起來你對職涯發展有些焦慮。你有考慮過需要具備哪些能力嗎？
案主：我知道需要學習新的技能，但更困擾的是履歷要怎麼寫才能突顯我的優勢。我過去的工作經驗似乎和科技業不太相關。
諮詢師：你提到履歷撰寫的困擾，這是很多轉職者都會遇到的問題。
案主：對，我也不知道面試時該怎麼說明為什麼想轉職。我怕面試官覺得我只是不滿意現在的工作而已。
諮詢師：轉職動機的說明確實很重要。你有想過自己的職涯價值觀是什麼嗎？
案主：我希望能夠做有意義的工作，也想要有更好的發展空間和學習機會。但我不確定這樣的動機在面試時說出來會不會太理想化。
"""

speakers = [
    {"speaker": "counselor", "text": "你提到想要轉職，能多說一些你目前的想法嗎？"},
    {
        "speaker": "client",
        "text": "我在目前公司工作了五年，但覺得職涯發展遇到瓶頸。我想要轉換到科技業，但不知道怎麼開始。",
    },
    {
        "speaker": "counselor",
        "text": "聽起來你對職涯發展有些焦慮。你有考慮過需要具備哪些能力嗎？",
    },
    {
        "speaker": "client",
        "text": "我知道需要學習新的技能，但更困擾的是履歷要怎麼寫才能突顯我的優勢。我過去的工作經驗似乎和科技業不太相關。",
    },
    {
        "speaker": "counselor",
        "text": "你提到履歷撰寫的困擾，這是很多轉職者都會遇到的問題。",
    },
    {
        "speaker": "client",
        "text": "對，我也不知道面試時該怎麼說明為什麼想轉職。我怕面試官覺得我只是不滿意現在的工作而已。",
    },
    {
        "speaker": "counselor",
        "text": "轉職動機的說明確實很重要。你有想過自己的職涯價值觀是什麼嗎？",
    },
    {
        "speaker": "client",
        "text": "我希望能夠做有意義的工作，也想要有更好的發展空間和學習機會。但我不確定這樣的動機在面試時說出來會不會太理想化。",
    },
]

payload = {
    "transcript": detailed_transcript,
    "speakers": speakers,
    "time_range": "0:00-1:00",
}

print("=" * 80)
print("Testing RAG Integration with Detailed Career Transcript")
print("=" * 80)
print("\n📤 Sending request with detailed career conversation...")
print(f"\nTranscript length: {len(detailed_transcript)} chars")
print(f"Number of speakers: {len(speakers)}")
print(
    "\nCareer keywords in transcript: 轉職, 履歷, 面試, 職涯, 價值觀, 發展, 能力, 優勢, 技能\n"
)

try:
    response = httpx.post(API_ENDPOINT, json=payload, timeout=30.0)

    if response.status_code == 200:
        data = response.json()

        print("=" * 80)
        print("✅ Response received successfully")
        print("=" * 80)

        print("\n📝 Summary:")
        print(f"  {data['summary']}")

        print(f"\n⚠️  Alerts ({len(data['alerts'])} items):")
        for i, alert in enumerate(data["alerts"], 1):
            print(f"  [{i}] {alert}")

        print(f"\n💡 Suggestions ({len(data['suggestions'])} items):")
        for i, suggestion in enumerate(data["suggestions"], 1):
            print(f"  [{i}] {suggestion}")

        rag_sources = data.get("rag_sources", [])
        print(f"\n📚 RAG Sources ({len(rag_sources)} items):")

        if rag_sources:
            print("\n✅ RAG INTEGRATION WORKING! Sources found:")
            for i, source in enumerate(rag_sources, 1):
                print(f"\n  [{i}] {source['title']}")
                print(f"      Score: {source['score']:.2f}")
                print(f"      Content: {source['content'][:200]}...")
        else:
            print("\n⚠️  No RAG sources found")
            print("    Possible reasons:")
            print("    1. Similarity scores below threshold (0.7)")
            print("    2. Knowledge base documents don't match this topic well")
            print("    3. Embedding/search issue")

        print("\n" + "=" * 80)
        print("Test completed")
        print("=" * 80)

    else:
        print(f"❌ Request failed: HTTP {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"❌ Error: {e}")
