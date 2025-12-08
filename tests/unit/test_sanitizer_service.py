"""Unit tests for SanitizerService - 文字脫敏服務測試"""

import pytest

from app.services.sanitizer_service import SanitizerService


class TestSanitizerService:
    """測試文字脫敏服務的各種功能"""

    @pytest.fixture
    def sanitizer(self):
        """建立 SanitizerService 實例"""
        return SanitizerService()

    def test_sanitize_id_card(self, sanitizer):
        """測試身分證字號遮蔽"""
        text = "我的身分證字號是 A123456789，請幫我保密"
        result = sanitizer.sanitize_text(text)

        assert (
            result["sanitized_text"]
            == "我的身分證字號是 [已遮蔽身分證字號]，請幫我保密"
        )
        assert result["count"] == 1
        assert "id_card" in result["found_items"]
        assert result["found_items"]["id_card"] == ["A123456789"]

    def test_sanitize_phone_number(self, sanitizer):
        """測試手機號碼遮蔽"""
        text = "請打給我 0912345678 或 0987654321"
        result = sanitizer.sanitize_text(text)

        assert "[已遮蔽手機號碼]" in result["sanitized_text"]
        assert result["count"] == 2
        assert "phone" in result["found_items"]
        assert len(result["found_items"]["phone"]) == 2

    def test_sanitize_landline(self, sanitizer):
        """測試市話遮蔽"""
        text = "公司電話 02-12345678 或 0212345678"
        result = sanitizer.sanitize_text(text)

        assert "[已遮蔽市話]" in result["sanitized_text"]
        assert result["count"] == 2
        assert "landline" in result["found_items"]

    def test_sanitize_email(self, sanitizer):
        """測試 Email 遮蔽"""
        text = "請聯絡 john.doe@example.com 或 test@gmail.com"
        result = sanitizer.sanitize_text(text)

        assert "[已遮蔽電子郵件]" in result["sanitized_text"]
        assert result["count"] == 2
        assert "email" in result["found_items"]
        assert "john.doe@example.com" in result["found_items"]["email"]

    def test_sanitize_credit_card(self, sanitizer):
        """測試信用卡號遮蔽"""
        text = "信用卡號 1234 5678 9012 3456 或 1234-5678-9012-3456"
        result = sanitizer.sanitize_text(text)

        assert "[已遮蔽信用卡號]" in result["sanitized_text"]
        assert result["count"] == 2
        assert "credit_card" in result["found_items"]

    def test_sanitize_address_number(self, sanitizer):
        """測試地址門牌號碼遮蔽"""
        text = "住在台北市100號和200號之間"
        result = sanitizer.sanitize_text(text)

        assert "[已遮蔽門牌]" in result["sanitized_text"]
        assert result["count"] == 2
        assert "address_number" in result["found_items"]

    def test_sanitize_multiple_sensitive_data(self, sanitizer):
        """測試多種敏感資料同時出現"""
        text = """
        案主資料：
        姓名：王小明
        身分證：A123456789
        電話：0912345678
        Email：wang@example.com
        地址：台北市100號
        """
        result = sanitizer.sanitize_text(text)

        # 應該要遮蔽多種資料
        assert result["count"] >= 4  # 至少 4 種敏感資料
        assert "id_card" in result["found_items"]
        assert "phone" in result["found_items"]
        assert "email" in result["found_items"]
        assert "address_number" in result["found_items"]

        # 原始資料不應該出現
        assert "A123456789" not in result["sanitized_text"]
        assert "0912345678" not in result["sanitized_text"]
        assert "wang@example.com" not in result["sanitized_text"]

    def test_sanitize_with_mask_mode(self, sanitizer):
        """測試部分遮蔽模式"""
        text = "身分證 A123456789"
        result = sanitizer.sanitize_text(text, mask_mode="mask")

        # 應該保留前後各2字元，中間用星號遮蔽
        # A123456789 (10字元) -> A1******89 (前2後2，中間6個星號)
        assert "A1******89" in result["sanitized_text"]
        assert result["count"] == 1
        # 確認原始資料被遮蔽
        assert "A123456789" not in result["sanitized_text"]

    def test_sanitize_with_remove_mode(self, sanitizer):
        """測試完全移除模式"""
        text = "手機 0912345678 請記得"
        result = sanitizer.sanitize_text(text, mask_mode="remove")

        # 敏感資料應該被完全移除
        assert "0912345678" not in result["sanitized_text"]
        assert result["sanitized_text"] == "手機  請記得"
        assert result["count"] == 1

    def test_sanitize_text_no_sensitive_data(self, sanitizer):
        """測試沒有敏感資料的文字"""
        text = "這是一段普通的對話，沒有任何敏感資訊"
        result = sanitizer.sanitize_text(text)

        assert result["sanitized_text"] == text
        assert result["count"] == 0
        assert result["found_items"] == {}

    def test_sanitize_empty_text(self, sanitizer):
        """測試空字串"""
        text = ""
        result = sanitizer.sanitize_text(text)

        assert result["sanitized_text"] == ""
        assert result["count"] == 0
        assert result["found_items"] == {}

    def test_sanitize_session_transcript(self, sanitizer):
        """測試會談逐字稿專用方法"""
        transcript = """
        諮詢師：請問您的聯絡方式？
        案主：我的電話是 0912345678，email 是 test@example.com
        諮詢師：好的，已記錄
        """

        sanitized_text, metadata = sanitizer.sanitize_session_transcript(transcript)

        # 檢查敏感資料被遮蔽
        assert "0912345678" not in sanitized_text
        assert "test@example.com" not in sanitized_text

        # 檢查 metadata
        assert metadata["removed_count"] == 2
        assert "phone" in metadata["removed_types"]
        assert "email" in metadata["removed_types"]
        assert metadata["phone_count"] == 1
        assert metadata["email_count"] == 1
        assert metadata["original_length"] > 0
        assert metadata["sanitized_length"] > 0

    def test_sanitize_preserves_context(self, sanitizer):
        """測試遮蔽後保留上下文"""
        text = "案主提到他的身分證是 A123456789，感到很困擾"
        result = sanitizer.sanitize_text(text)

        # 應該保留上下文文字
        assert "案主提到他的身分證是" in result["sanitized_text"]
        assert "，感到很困擾" in result["sanitized_text"]
        # 但敏感資料應該被遮蔽
        assert "A123456789" not in result["sanitized_text"]

    def test_sanitize_multiple_occurrences_same_data(self, sanitizer):
        """測試同一個敏感資料出現多次"""
        text = "電話 0912345678 請記得，再說一次 0912345678"
        result = sanitizer.sanitize_text(text)

        # 兩次出現都應該被遮蔽
        assert result["sanitized_text"].count("[已遮蔽手機號碼]") == 2
        assert result["count"] == 2

    def test_sanitize_edge_case_short_string(self, sanitizer):
        """測試短字串的遮蔽（mask mode）"""
        text = "卡號 1234"
        result = sanitizer.sanitize_text(text, mask_mode="mask")

        # 短於4字元的應該全部遮蔽
        if result["count"] > 0:
            assert "*" in result["sanitized_text"]

    def test_patterns_are_compiled(self, sanitizer):
        """測試所有 pattern 都已編譯"""
        assert len(sanitizer.patterns) == 6
        assert all(hasattr(p, "findall") for p in sanitizer.patterns.values())

    def test_replacements_match_patterns(self, sanitizer):
        """測試所有 pattern 都有對應的 replacement"""
        assert sanitizer.patterns.keys() == sanitizer.replacements.keys()


class TestSanitizerServiceRealWorldScenarios:
    """真實場景測試"""

    @pytest.fixture
    def sanitizer(self):
        return SanitizerService()

    def test_real_counseling_transcript(self, sanitizer):
        """測試真實諮詢逐字稿場景"""
        transcript = """
        諮詢師：首先，請問您的基本資料？
        案主：我叫王大明，身分證字號 B234567890，
              住在新北市50號，電話是 0923456789。
        諮詢師：您的困擾是什麼？
        案主：最近工作壓力很大，老闆一直打我的手機 0987654321，
              連我的個人信箱 wang.daming@gmail.com 都不放過。
              我的信用卡 5555-6666-7777-8888 都快刷爆了。
        """

        sanitized, metadata = sanitizer.sanitize_session_transcript(transcript)

        # 所有敏感資料都應該被遮蔽
        assert "B234567890" not in sanitized
        assert "0923456789" not in sanitized
        assert "0987654321" not in sanitized
        assert "wang.daming@gmail.com" not in sanitized
        assert "5555-6666-7777-8888" not in sanitized

        # 但對話內容應該保留
        assert "諮詢師：首先，請問您的基本資料？" in sanitized
        assert "案主：我叫王大明" in sanitized
        assert "最近工作壓力很大" in sanitized

        # metadata 應該正確記錄
        assert metadata["removed_count"] >= 6
        assert "id_card" in metadata["removed_types"]
        assert "phone" in metadata["removed_types"]
        assert "email" in metadata["removed_types"]
        assert "credit_card" in metadata["removed_types"]

    def test_mixed_format_phone_numbers(self, sanitizer):
        """測試不同格式的電話號碼"""
        text = "手機 0912-345-678、0912345678、09-12345678"
        result = sanitizer.sanitize_text(text)

        # 至少應該抓到標準格式的
        assert result["count"] >= 1
        assert "0912345678" not in result["sanitized_text"]

    def test_email_variations(self, sanitizer):
        """測試各種 email 格式"""
        text = """
        email: test@example.com
        Email: john.doe+tag@company.co.uk
        聯絡: user_name@sub.domain.com.tw
        """
        result = sanitizer.sanitize_text(text)

        assert result["count"] >= 3
        assert "test@example.com" not in result["sanitized_text"]
        assert "john.doe+tag@company.co.uk" not in result["sanitized_text"]
