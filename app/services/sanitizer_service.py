"""Text Sanitization Service - 脫敏處理"""

import re
from typing import Dict, Tuple


class SanitizerService:
    """文字脫敏服務 - 移除或遮蔽敏感資訊"""

    def __init__(self):
        # Patterns for sensitive information
        self.patterns = {
            "id_card": re.compile(r"[A-Z]\d{9}"),  # 台灣身分證字號
            "phone": re.compile(r"09\d{8}"),  # 手機號碼
            "landline": re.compile(r"0[2-8]-?\d{7,8}"),  # 市話
            "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),  # Email
            "credit_card": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),  # 信用卡號
            "address_number": re.compile(r"\d+號"),  # 地址門牌號碼
        }

        # Replacement strings
        self.replacements = {
            "id_card": "[已遮蔽身分證字號]",
            "phone": "[已遮蔽手機號碼]",
            "landline": "[已遮蔽市話]",
            "email": "[已遮蔽電子郵件]",
            "credit_card": "[已遮蔽信用卡號]",
            "address_number": "[已遮蔽門牌]",
        }

    def sanitize_text(self, text: str, mask_mode: str = "replace") -> Dict:
        """
        脫敏處理文字

        Args:
            text: 原始文字
            mask_mode: 遮蔽模式 ('replace' | 'mask' | 'remove')
                - replace: 以標籤取代 [已遮蔽XXX]
                - mask: 部分遮蔽 (e.g., A12****789)
                - remove: 完全移除

        Returns:
            {
                "sanitized_text": "脫敏後文字",
                "found_items": {"type": [matched_values]},
                "count": 總共移除的項目數
            }
        """
        sanitized = text
        found_items = {}
        total_count = 0

        for key, pattern in self.patterns.items():
            matches = pattern.findall(text)

            if matches:
                found_items[key] = matches
                total_count += len(matches)

                if mask_mode == "replace":
                    sanitized = pattern.sub(self.replacements[key], sanitized)

                elif mask_mode == "mask":
                    # 部分遮蔽 (保留前後各2字元)
                    for match in matches:
                        if len(match) > 4:
                            masked = match[:2] + "*" * (len(match) - 4) + match[-2:]
                        else:
                            masked = "*" * len(match)
                        sanitized = sanitized.replace(match, masked)

                elif mask_mode == "remove":
                    sanitized = pattern.sub("", sanitized)

        return {
            "sanitized_text": sanitized,
            "found_items": found_items,
            "count": total_count,
        }

    def sanitize_session_transcript(self, transcript: str) -> Tuple[str, Dict]:
        """
        專門用於會談逐字稿的脫敏處理

        Returns:
            (sanitized_text, metadata)
        """
        result = self.sanitize_text(transcript, mask_mode="replace")

        metadata = {
            "original_length": len(transcript),
            "sanitized_length": len(result["sanitized_text"]),
            "removed_count": result["count"],
            "removed_types": list(result["found_items"].keys()),
        }

        return result["sanitized_text"], metadata


# Service instance
sanitizer_service = SanitizerService()
