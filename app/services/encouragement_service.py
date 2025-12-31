"""
Encouragement Service - 快速鼓勵訊息服務

提供基於規則的簡單鼓勵訊息，用於填補 AI 分析的等待時間。
iOS 客戶端可以每 10 秒輪詢，如果沒有新的 AI 分析，就顯示雞湯文。
"""

import datetime
from typing import Dict

# 危險關鍵字列表（觸發警告類訊息）
DANGER_KEYWORDS = [
    "打",
    "罵",
    "揍",
    "死",
    "威脅",
    "滾",
    "閉嘴",
    "煩",
    "不要你",
    "討厭",
    "丟掉",
    "扔掉",
]

# 提問關鍵字（觸發鼓勵類訊息）
QUESTION_KEYWORDS = ["？", "?", "嗎", "對不對", "好不好", "是不是"]


# 雞湯文句庫
ENCOURAGEMENT_MESSAGES = {
    "danger": [
        "深呼吸，保持冷靜",
        "先暫停一下，整理情緒",
        "記住，你是孩子的穩定錨",
        "情緒升高時，先照顧自己的感受",
        "溫和而堅定，是最好的方式",
    ],
    "question": [
        "好問題！繼續引導孩子思考",
        "開放式提問做得很好",
        "讓孩子有空間表達想法",
        "這樣問能幫助孩子反思",
        "繼續用提問引導對話",
    ],
    "neutral": [
        "做得很好，繼續保持",
        "你正在用心傾聽",
        "保持這個節奏",
        "注意孩子的反應",
        "維持溫和的語氣",
        "你在建立安全的對話空間",
        "繼續給孩子時間回應",
        "這樣的互動方向很好",
    ],
}


class EncouragementService:
    """快速鼓勵訊息服務（Rule-Based）"""

    def __init__(self):
        self.message_index = {"danger": 0, "question": 0, "neutral": 0}

    def get_encouragement(self, recent_transcript: str) -> Dict[str, str]:
        """
        根據最近的逐字稿生成鼓勵訊息

        Args:
            recent_transcript: 最近 10 秒的逐字稿

        Returns:
            {
                "message": "鼓勵訊息文字",
                "type": "danger|question|neutral",
                "timestamp": "當前時間"
            }
        """
        # 檢測危險關鍵字
        if self._contains_danger_keywords(recent_transcript):
            msg_type = "danger"
        # 檢測提問
        elif self._contains_question_keywords(recent_transcript):
            msg_type = "question"
        # 預設中性鼓勵
        else:
            msg_type = "neutral"

        # 從對應的句庫中輪流選擇（避免重複）
        message = self._get_next_message(msg_type)

        return {
            "message": message,
            "type": msg_type,
            "timestamp": datetime.datetime.now().isoformat(),
        }

    def _contains_danger_keywords(self, text: str) -> bool:
        """檢測是否包含危險關鍵字"""
        return any(keyword in text for keyword in DANGER_KEYWORDS)

    def _contains_question_keywords(self, text: str) -> bool:
        """檢測是否包含提問"""
        return any(keyword in text for keyword in QUESTION_KEYWORDS)

    def _get_next_message(self, msg_type: str) -> str:
        """從句庫中輪流取出訊息（避免重複）"""
        messages = ENCOURAGEMENT_MESSAGES[msg_type]
        index = self.message_index[msg_type]

        message = messages[index]

        # 更新索引（循環）
        self.message_index[msg_type] = (index + 1) % len(messages)

        return message


# 創建全局實例
encouragement_service = EncouragementService()
