#!/usr/bin/env python3
"""
Gemini Implicit Caching 性能测试 - 累积性逐字稿
测试 1-10 分钟的累积逐字稿分析，验证缓存效果
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict

import httpx

# API Configuration
API_BASE_URL = "https://career-app-api-staging-kxaznpplqq-uc.a.run.app/api/v1"
REALTIME_ENDPOINT = f"{API_BASE_URL}/realtime/analyze"

# 逐字稿数据：模拟连续 10 分钟的亲子教养咨询
CONVERSATION_MINUTES = {
    1: """诊商师：今天想聊些什么呢？
家长：最近跟孩子的关系变得很紧张。他在学校总是跟同学起冲突，老师也反映他上课不专心。
诊商师：听起来你很担心孩子在学校的适应问题。可以多说一些吗？
家长：对，我真的很担心。他以前不是这样的，升上国中之后就变了。每天回家都不愿意跟我说话。
诊商师：升上国中确实是个大转变。你说他不愿意跟你说话，那你们之间的互动是什么样子呢？
家长：就是我问他今天怎么样，他就说"还好"，然后就关在房间里。我想跟他聊聊，他就很不耐烦。""",
    2: """诊商师：你刚提到他会不耐烦，那时候你的感受是什么？
家长：我觉得很受伤，也有点生气。我明明是关心他，他为什么要这样对我？
诊商师：这个感受很真实。那你通常会怎么回应他的不耐烦呢？
家长：我会忍不住说"你这是什么态度？我是你妈妈耶！"然后我们就会吵起来。
诊商师：我理解那个当下你的感受。吵架之后呢？
家长：他就会摔门回房间，有时候会摔东西。我也很生气，但又觉得很无力。""",
    3: """诊商师：听起来这样的互动让你们都很不舒服。你希望跟孩子的关系是什么样子呢？
家长：我希望他能理解我是为他好，也希望我们能好好沟通，不要总是吵架。
诊商师：这是很好的目标。那我们来想想，有没有什么时候你们的互动是比较顺利的？
家长：嗯...好像是周末的时候，我们一起吃饭或看电影，气氛会比较好。
诊商师：那很棒！那些时候你们都在做什么呢？
家长：就是放松地聊天，不会提到功课或学校的事。他会跟我分享他喜欢的游戏或YouTuber。""",
    4: """诊商师：所以当不讨论学校和功课时，你们的关系是比较好的。
家长：对，但平日就很难避免谈这些问题。他的成绩一直在退步，我不可能不管啊。
诊商师：我理解你的担心。那我们可以试着想想，有没有方法在关心他的学业时，不会引发冲突？
家长：我也想知道该怎么做。我试过很多方法了，但都没用。
诊商师：可以分享一下你试过哪些方法吗？
家长：我试过跟他好好讲道理，告诉他现在不好好读书，以后会后悔。但他就说"我知道了"，然后还是一样。""",
    5: """诊商师：听起来讲道理对他来说可能效果有限。那有没有试过其他方式？
家长：我也试过奖励，比如说考到多少分就买东西给他。但他好像也不太在意。
诊商师：我注意到你提到他"好像也不太在意"，能说说是什么让你觉得他不在意吗？
家长：因为他还是没有认真读书啊。有时候我会检查他的功课，发现他都没做，或者只是随便写写。
诊商师：当你发现他没有认真做功课时，你会怎么做？
家长：我会很生气，然后叫他重写。但他就会说太累了，明天再写。结果明天还是一样。""",
    6: """诊商师：这样重复的循环一定让你感到很挫折。
家长：对，我真的不知道该怎么办了。有时候我会想，是不是我哪里做错了？
诊商师：听到你这样说，我感受到你的自我怀疑和压力。作为父母，想要孩子好是很自然的。
家长：对啊，我就是希望他能过得好。但现在感觉我越努力，他越反抗。
诊商师：你提到"越反抗"，可以具体说说是什么样的情况吗？
家长：比如说，我要求他晚上十点前要睡觉，他会故意拖到十一点、十二点。我说不能玩手机，他就偷偷玩。""",
    7: """诊商师：听起来他在用这些行为来表达什么。你觉得他可能想表达什么呢？
家长：我不知道耶...可能是他觉得我管太多？
诊商师：有可能。青春期的孩子通常会开始想要更多的自主权。
家长：但是我不管的话，他就会更放纵啊！
诊商师：我理解你的担心。那我们可以想想，有没有可能在给他一些自主权的同时，又能让他学会负责任？
家长：这...我不太确定要怎么做。能给我一些具体的建议吗？""",
    8: """诊商师：当然。不过在给建议之前，我想先了解一下，你觉得孩子现在最需要什么？
家长：我觉得他需要知道读书的重要性，需要学会为自己的未来负责。
诊商师：这些都很重要。那从孩子的角度来看，你觉得他现在最需要什么呢？
家长：这...我没想过。他需要什么？
诊商师：或许我们可以试着想想，如果是你十几岁的时候，你最需要父母给你什么？
家长：嗯...我想想。我那时候很想要父母理解我，不要一直逼我。但我爸妈就是一直逼，所以我跟他们关系也不好。""",
    9: """诊商师：你刚才提到一个很重要的点。你那时候很想要父母理解你。
家长：对...我现在才发现，我好像在重复我父母对我的方式。
诊商师：能觉察到这一点很不容易。那现在回想起来，你希望当时的父母怎么对你？
家长：我希望他们能多听听我在想什么，而不是只在乎我的成绩。我希望他们知道我也很努力了，只是做不到他们的期待。
诊商师：这些话听起来好像也是你儿子可能想对你说的话。
家长：是吗...我从来没有想过他可能也跟我当年一样。""",
    10: """诊商师：那现在，如果我们试着站在孩子的角度，你觉得他可能需要什么？
家长：他可能需要我多听听他的想法，不要只是要求他做这个做那个。
诊商师：没错。那我们可以从这里开始尝试。比如说，今天回去之后，试着找一个轻松的时候，问问他最近过得怎么样，然后真心地听他说，不要急着给建议或评论。
家长：这...听起来很简单，但我担心他不愿意说。
诊商师：这是有可能的。建立信任需要时间。即使他一开始不愿意多说，只要你持续用这种态度，他会慢慢感受到的。
家长：好，我试试看。谢谢你今天的帮助，我好像比较知道可以怎么做了。""",
}


def build_cumulative_transcript(end_minute: int) -> str:
    """构造累积逐字稿（从第1分钟到第end_minute分钟）"""
    transcript_parts = []
    for minute in range(1, end_minute + 1):
        if minute in CONVERSATION_MINUTES:
            transcript_parts.append(CONVERSATION_MINUTES[minute])
    return "\n\n".join(transcript_parts)


async def analyze_minute(minute: int) -> Dict[str, Any]:
    """分析第N分钟的累积逐字稿"""
    print(f"\n{'='*60}")
    print(f"📊 测试第 {minute} 分钟（累积 1-{minute} 分钟对话）")
    print(f"{'='*60}")

    # 构造累积逐字稿
    cumulative_transcript = build_cumulative_transcript(minute)
    transcript_chars = len(cumulative_transcript)
    estimated_tokens = int(transcript_chars * 1.2)  # 中文约 1.2 tokens/char

    print(f"逐字稿长度: {transcript_chars} 字符")
    print(f"估算 tokens: {estimated_tokens}")

    # 构造请求
    request_data = {
        "transcript": cumulative_transcript,
        "speakers": [],  # 简化：不拆分 speakers
        "time_range": f"0:00-{minute}:00",
    }

    # 发送请求
    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                REALTIME_ENDPOINT,
                json=request_data,
                headers={"Content-Type": "application/json"},
            )

            elapsed_time = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                summary = result.get("summary", "")
                usage = result.get("usage_metadata", {})

                print("✅ 成功")
                print(f"⏱️  响应时间: {elapsed_time:.2f} 秒")
                print(f"📝 Summary: {summary}")
                print(f"📏 Summary 长度: {len(summary)} 字")

                # Print usage metadata if available
                if usage:
                    print(
                        f"🎯 Cached tokens: {usage.get('cached_content_token_count', 0)}"
                    )
                    print(f"📝 Prompt tokens: {usage.get('prompt_token_count', 0)}")
                    print(f"💬 Output tokens: {usage.get('candidates_token_count', 0)}")
                    total_tokens = usage.get("prompt_token_count", 0) + usage.get(
                        "candidates_token_count", 0
                    )
                    cache_ratio = (
                        (
                            usage.get("cached_content_token_count", 0)
                            / total_tokens
                            * 100
                        )
                        if total_tokens > 0
                        else 0
                    )
                    print(f"📊 Cache ratio: {cache_ratio:.1f}%")

                return {
                    "minute": minute,
                    "success": True,
                    "transcript_chars": transcript_chars,
                    "estimated_tokens": estimated_tokens,
                    "response_time": round(elapsed_time, 2),
                    "summary": summary,
                    "summary_length": len(summary),
                    "alerts_count": len(result.get("alerts", [])),
                    "suggestions_count": len(result.get("suggestions", [])),
                    "cached_tokens": usage.get("cached_content_token_count", 0),
                    "prompt_tokens": usage.get("prompt_token_count", 0),
                    "output_tokens": usage.get("candidates_token_count", 0),
                    "cache_ratio": round(cache_ratio, 1) if usage else 0,
                }
            else:
                elapsed_time = time.time() - start_time
                print(f"❌ 失败: HTTP {response.status_code}")
                print(f"错误: {response.text}")

                return {
                    "minute": minute,
                    "success": False,
                    "transcript_chars": transcript_chars,
                    "estimated_tokens": estimated_tokens,
                    "response_time": round(elapsed_time, 2),
                    "error": f"HTTP {response.status_code}",
                }

    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ 异常: {str(e)}")

        return {
            "minute": minute,
            "success": False,
            "transcript_chars": transcript_chars,
            "estimated_tokens": estimated_tokens,
            "response_time": round(elapsed_time, 2),
            "error": str(e),
        }


async def main():
    """主测试流程"""
    print("=" * 60)
    print("🚀 Gemini Implicit Caching 性能测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Endpoint: {REALTIME_ENDPOINT}")
    print("测试范围: 1-10 分钟（累积性逐字稿）")
    print("=" * 60)

    results = []

    # 逐分钟测试
    for minute in range(1, 11):
        result = await analyze_minute(minute)
        results.append(result)

        # 快速連續請求測試 implicit caching (間隔 < 1 秒)
        if minute < 10:
            await asyncio.sleep(0.1)

    # 保存结果
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "test_config": {
            "api_endpoint": REALTIME_ENDPOINT,
            "minutes_tested": 10,
            "test_type": "cumulative_transcript",
        },
        "results": results,
    }

    output_file = "cache_cumulative_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 结果已保存: {output_file}")

    # 打印汇总
    print("\n" + "=" * 60)
    print("📊 测试汇总")
    print("=" * 60)

    successful = [r for r in results if r["success"]]
    success_rate = len(successful) / len(results) * 100

    print(f"成功率: {len(successful)}/{len(results)} ({success_rate:.1f}%)")

    if successful:
        avg_time = sum(r["response_time"] for r in successful) / len(successful)
        min_time = min(r["response_time"] for r in successful)
        max_time = max(r["response_time"] for r in successful)

        print(f"平均响应时间: {avg_time:.2f} 秒")
        print(f"最快响应: {min_time:.2f} 秒")
        print(f"最慢响应: {max_time:.2f} 秒")

        # 速度趋势
        first_time = results[0]["response_time"]
        last_time = results[-1]["response_time"]
        if first_time > 0:
            improvement = ((first_time - last_time) / first_time) * 100
            print(f"\n🚀 速度改善: 第1分钟 vs 第10分钟 = {improvement:.1f}%")

    print("\n" + "=" * 100)
    print("详细结果表格（含 Cache 数据）:")
    print("=" * 100)
    print(
        f"{'分钟':<6} {'字符':<6} {'Tokens':<8} {'响应(秒)':<10} {'Cached':<8} {'Prompt':<8} {'Output':<8} {'Cache%':<8} {'状态':<6}"
    )
    print("-" * 100)

    for r in results:
        status = "✅" if r["success"] else "❌"
        cached = r.get("cached_tokens", 0)
        prompt = r.get("prompt_tokens", 0)
        output = r.get("output_tokens", 0)
        cache_pct = r.get("cache_ratio", 0)
        print(
            f"{r['minute']:<6} {r['transcript_chars']:<6} {r['estimated_tokens']:<8} "
            f"{r['response_time']:<10.2f} {cached:<8} {prompt:<8} {output:<8} {cache_pct:<8.1f} {status:<6}"
        )

    # Cache improvement analysis
    if successful and len(successful) >= 2:
        first_cache = results[0].get("cache_ratio", 0)
        last_cache = results[-1].get("cache_ratio", 0)
        print(
            f"\n🎯 Cache 改善: 第1分钟 {first_cache:.1f}% → 第10分钟 {last_cache:.1f}%"
        )


if __name__ == "__main__":
    asyncio.run(main())
