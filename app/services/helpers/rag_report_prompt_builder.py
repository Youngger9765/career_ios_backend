"""
RAG Report Prompt Builder
Large prompt construction logic extracted from RAGReportService
"""
from typing import Any, Dict


def build_legacy_prompt(
    parsed_data: Dict[str, Any],
    context: str,
    rag_instruction: str,
) -> str:
    """Build legacy 5-section report prompt

    Args:
        parsed_data: Parsed transcript data
        context: Theory context string
        rag_instruction: RAG citation instruction

    Returns:
        Legacy report prompt
    """
    main_concerns = parsed_data.get("main_concerns", [])
    techniques = parsed_data.get("counselor_techniques", [])

    return f"""{rag_instruction}

你是一位專業的職涯諮詢督導。請根據以下資訊生成個案報告：

**案主基本資料：**
- 姓名（化名）：{parsed_data.get('client_name', '未提供')}
- 性別：{parsed_data.get('gender', '未提及')}
- 年齡：{parsed_data.get('age', '未提及')}
- 部門/職業（學校科系）：{parsed_data.get('occupation', '未提及')}
- 學歷：{parsed_data.get('education', '未提及')}
- 現居地：{parsed_data.get('location', '未提及')}
- 經濟狀況：{parsed_data.get('economic_status', '未提及')}
- 家庭關係：{parsed_data.get('family_relations', '未提及')}
- 其他重要資訊：{', '.join(parsed_data.get('other_info', []))}

**晤談內容概述：**
{parsed_data.get('session_content', '')}

**主訴問題：**
{', '.join(main_concerns)}

**晤談目標：**
{', '.join(parsed_data.get('counseling_goals', []))}

**使用的諮詢技巧：**
{', '.join(techniques)}

**相關理論參考：**
{context}

請生成結構化的個案報告，包含以下部分：

【主訴問題】
個案說的，此次想要討論的議題

【成因分析】
諮詢師您認為，個案為何會有這些主訴問題，請結合引用的理論 [1], [2] 等進行分析

【晤談目標（移動主訴）】
諮詢師對個案諮詢目標的假設，須與個案確認

【介入策略】
諮詢師判斷會需要帶個案做的事，結合理論說明

【目前成效評估】
上述目標和策略達成的狀況如何，目前打算如何修正

重要提醒：
1. ⚠️ 每個段落必須有實質內容，每段至少寫5-8句完整的段落文字，絕對不可只寫「-」、「無」、「待評估」或留空
2. 每個段落都要深入分析，提供具體的觀察、推論和建議
3. 請使用專業、客觀、具同理心的語氣
4. 適當引用理論文獻 [1], [2] 等
5. 不要使用 markdown 格式（如 ##, ###, **, - 等符號）
6. 使用【標題】的格式來區分段落
7. 內容直接書寫成段落，不要用項目符號或短句
"""


def build_enhanced_prompt(
    parsed_data: Dict[str, Any],
    context: str,
    rag_instruction: str,
) -> str:
    """Build enhanced 10-section report prompt

    Args:
        parsed_data: Parsed transcript data
        context: Theory context string
        rag_instruction: RAG citation instruction

    Returns:
        Enhanced report prompt with rationale examples
    """
    main_concerns = parsed_data.get("main_concerns", [])
    techniques = parsed_data.get("counselor_techniques", [])

    prompt = f"""{rag_instruction}

你是職涯諮詢督導，協助新手諮詢師撰寫個案概念化報告。

你的優勢：快速從大量文獻中找到最適合此個案的理論和策略。

【案主資料】
- 姓名（化名）：{parsed_data.get('client_name', '未提供')}
- 性別：{parsed_data.get('gender', '未提及')}
- 年齡：{parsed_data.get('age', '未提及')}
- 部門/職業：{parsed_data.get('occupation', '未提及')}
- 學歷：{parsed_data.get('education', '未提及')}
- 現居地：{parsed_data.get('location', '未提及')}
- 經濟狀況：{parsed_data.get('economic_status', '未提及')}
- 家庭關係：{parsed_data.get('family_relations', '未提及')}

【晤談摘要】
{parsed_data.get('session_content', '')}

【主訴】{', '.join(main_concerns)}
【目標】{', '.join(parsed_data.get('counseling_goals', []))}
【技巧】{', '.join(techniques)}

【相關理論文獻】（請在適當段落引用 [1], [2]）
{context}

⚠️ 重要：請嚴格按照以下結構生成個案報告，段落【二】到【十】都必須完整包含！

【一、案主基本資料】
根據逐字稿提取的資訊整理如下（若逐字稿未提及則省略該項）：
- 姓名（化名）：{parsed_data.get('client_name', '未提供')}
{f"- 性別：{parsed_data.get('gender')}" if parsed_data.get('gender') != '未提及' else ""}
{f"- 年齡：{parsed_data.get('age')}" if parsed_data.get('age') != '未提及' else ""}
{f"- 部門/職業：{parsed_data.get('occupation')}" if parsed_data.get('occupation') != '未提及' else ""}
{f"- 學歷：{parsed_data.get('education')}" if parsed_data.get('education') != '未提及' else ""}
{f"- 現居地：{parsed_data.get('location')}" if parsed_data.get('location') != '未提及' else ""}
{f"- 經濟狀況：{parsed_data.get('economic_status')}" if parsed_data.get('economic_status') != '未提及' else ""}
{f"- 家庭關係：{parsed_data.get('family_relations')}" if parsed_data.get('family_relations') != '未提及' else ""}

註：本段僅呈現逐字稿中提及的資訊。若資訊不完整，不影響後續專業分析的品質。

【二、主訴問題】
- 個案陳述：（個案原話中的困擾）
- 諮詢師觀察：（你在晤談中觀察到的議題）

【三、問題發展脈絡】
- 出現時間：（何時開始）
- 持續頻率：（多久發生一次）
- 影響程度：（對生活/工作的影響）

【四、求助動機與期待】
- 引發因素：（為何此時求助）
- 期待目標：（希望改善什麼）

【五、多層次因素分析】⭐ 核心段落（必須引用理論 [1][2]）
分析以下層次，並引用理論：
- 個人因素：（年齡/生涯階段、性格、能力）
- 人際因素：（家庭、社會支持）
- 環境因素：（職場/學校、經濟）
- 發展因素：（生涯成熟度、早期經驗）

⚠️ 引用格式要求：必須包含「理論名稱 + [數字]」，例如：
✅ 正確：「根據 Super 生涯發展理論 [1]，案主處於探索期...」
✅ 正確：「從社會認知職業理論 (SCCT) [2] 的觀點來看...」
❌ 錯誤：「根據理論 [1]」（缺少理論名稱）
❌ 錯誤：「根據文獻」（沒有數字引用）

【六、個案優勢與資源】
- 心理優勢：（情緒調適、動機）
- 社會資源：（支持系統）

【七、諮詢師的專業判斷】⭐ 核心段落（必須引用理論 [3][4]）
- 問題假設：（為何有這些困擾）
- 理論依據：（用什麼理論支持判斷）引用 [3][4]
- 理論取向：（採用的觀點）

⚠️ 引用格式要求：必須包含「理論名稱 + [數字]」，例如：
✅ 正確：「基於認知行為理論 [3]，我認為問題源於...」
✅ 正確：「從 Holland 類型論 [4] 的角度來看...」
❌ 錯誤：「根據理論 [3]」（缺少理論名稱）

【八、諮商目標與介入策略】⭐ 核心段落（必須引用 [5][6]）
- 諮商目標：（SMART 格式，具體可衡量）
- 介入技術：（使用的方法）引用 [5][6]
- 技術理由：（為何這技術適合此個案）
- 介入步驟：（執行順序）

⚠️ 引用格式要求：必須包含「理論名稱 + [數字]」，例如：
✅ 正確：「選擇敘事治療技術 [5]，因為此方法能幫助案主重新建構生涯故事...」
✅ 正確：「根據焦點解決短期治療 (SFBT) [6]，設定具體可達成的目標...」
❌ 錯誤：「理論 [5] 指出...」（缺少理論名稱）

【九、預期成效與評估】
- 短期指標：（3 個月內如何判斷進步）
- 長期指標：（6-12 個月目標）
- 可能調整：（什麼情況需改變策略）

【十、諮詢師自我反思】
{parsed_data.get('counselor_self_evaluation', '請反思本次晤談優點和可改進處')}

格式要求：
1. 必須包含上述所有段落，用【】標題
2. 第五、七、八段落必須引用理論，格式為「理論名稱 [數字]」
3. 每個引用必須完整說明理論名稱，例如「Super 生涯發展理論 [1]」而非「理論 [1]」
4. 引用時要說明為何此理論適用於個案
5. 不用 markdown（##, **, -）
6. 每段至少 3-5 句，內容充實且具體
7. 必須考慮多層次因素：生理、心理、社會、文化
"""

    # Add rationale examples for enhanced version
    from app.utils.prompt_enhancer import add_rationale_examples

    return add_rationale_examples(prompt)
