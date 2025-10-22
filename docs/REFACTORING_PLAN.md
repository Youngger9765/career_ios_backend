# rag_report.py 重構計劃

**日期**: 2025-10-22
**目標**: 重構 1009 行的 `rag_report.py`，消除重複邏輯，提升可測試性和可維護性
**原則**: TDD + 漸進式重構 + 向後兼容

---

## 📊 現狀分析

### 問題診斷

**rag_report.py (1009 行)**
```
├── 重複邏輯 (60% overlap)
│   ├── generate_report_stream() L152-501 (SSE streaming)
│   └── generate_report() L503-1008 (Direct JSON)
│       └── Duplicate: parse, RAG search, report gen, dialogue extract
│
├── 職責混亂 (違反 SRP)
│   ├── API routing (FastAPI)
│   ├── Transcript parsing (LLM prompts)
│   ├── RAG search (SQL queries)
│   ├── Report generation (LLM prompts)
│   ├── Format conversion (HTML/Markdown)
│   └── Validation (quality grading)
│
└── 硬編碼 prompts (500+ lines)
    ├── Parse prompt (L177-199, L526-548) - 重複 2 次
    ├── Legacy report prompt (L671-726)
    ├── Enhanced report prompt (L729-837)
    └── Dialogue extraction prompt (L420-438, L869-887) - 重複 2 次
```

### 測試覆蓋現狀

✅ **已有測試 (Integration Tests)**
- `tests/integration/test_legacy_formats.py` (3 tests)
- `tests/integration/test_enhanced_formats.py` (3 tests)
- Coverage: API endpoint 層級

❌ **缺少測試 (Unit Tests)**
- Transcript parsing logic
- RAG retrieval logic
- Prompt building logic
- Format conversion logic

---

## 🎯 重構策略

### 採用方案: 漸進式重構 (3 Phases)

**Phase 1: 基礎重構 (低風險)** ⭐ 當前階段
- 提取 `TranscriptParser` service
- 提取 `RAGRetriever` service
- 消除 `generate_report()` 和 `generate_report_stream()` 重複邏輯

**Phase 2: Prompts 分離 (中風險)**
- 提取 prompts 到 `app/prompts/` 模組
- Template-based prompt generation

**Phase 3: 模式分離 (高價值)**
- `LegacyReportGenerator` class
- `EnhancedReportGenerator` class

---

## 📋 Phase 1 詳細計劃 (TDD Red-Green-Refactor)

### Step 1: TranscriptParser 提取

#### 1.1 RED - 寫測試
```python
# tests/unit/test_transcript_parser.py

async def test_parse_transcript_basic_info():
    """Test extracting basic client info from transcript"""
    parser = TranscriptParser(openai_service)
    transcript = "Cl: 我28歲，在科技公司當工程師..."

    result = await parser.parse(transcript)

    assert result["client_info"]["age"] == "28"
    assert "工程師" in result["client_info"]["occupation"]

async def test_parse_transcript_main_concerns():
    """Test extracting main concerns"""
    # ...

async def test_parse_transcript_invalid_json_fallback():
    """Test fallback when LLM returns invalid JSON"""
    # ...
```

**Expected**: 測試失敗 (TranscriptParser 不存在) ❌ RED

#### 1.2 GREEN - 實作 Service
```python
# app/services/transcript_parser.py

class TranscriptParser:
    """解析逐字稿，提取關鍵資訊"""

    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    async def parse(self, transcript: str) -> dict:
        """
        Parse transcript and extract key information

        Returns:
            {
                "client_info": {...},
                "main_concerns": [...],
                "counseling_goals": [...],
                "counselor_techniques": [...],
                "session_content": "...",
                "counselor_self_evaluation": "..."
            }
        """
        # 從 rag_report.py L526-578 提取邏輯
        # ...
```

**Expected**: 測試通過 ✅ GREEN

#### 1.3 REFACTOR - 使用新 Service
```python
# app/api/rag_report.py (修改)

from app.services.transcript_parser import TranscriptParser

@router.post("/generate")
async def generate_report(...):
    parser = TranscriptParser(openai_service)
    parsed_data = await parser.parse(request.transcript)  # 使用新 service
    # 刪除舊的 L526-578 重複代碼
    # ...
```

**Expected**: 所有測試保持 GREEN ✅

---

### Step 2: RAGRetriever 提取

#### 2.1 RED - 寫測試
```python
# tests/unit/test_rag_retriever.py

async def test_search_theories_returns_results(mock_db):
    """Test RAG retrieval returns theories"""
    retriever = RAGRetriever(openai_service)

    theories = await retriever.search(
        query="職涯轉換",
        top_k=5,
        threshold=0.25,
        db=mock_db
    )

    assert len(theories) > 0
    assert "text" in theories[0]
    assert "document" in theories[0]
    assert "score" in theories[0]

async def test_search_theories_no_results_raises():
    """Test RAG fails when no theories found"""
    # ...
```

**Expected**: 測試失敗 ❌ RED

#### 2.2 GREEN - 實作 Service
```python
# app/services/rag_retriever.py

class RAGRetriever:
    """RAG 理論檢索服務"""

    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    async def search(
        self,
        query: str,
        top_k: int,
        threshold: float,
        db: AsyncSession
    ) -> List[dict]:
        """
        Search for relevant theories using RAG

        Returns:
            [
                {"text": "...", "document": "...", "score": 0.85},
                ...
            ]

        Raises:
            HTTPException: If no theories found
        """
        # 從 rag_report.py L586-629 提取邏輯
        # ...
```

**Expected**: 測試通過 ✅ GREEN

#### 2.3 REFACTOR - 使用新 Service
```python
# app/api/rag_report.py (修改)

from app.services.rag_retriever import RAGRetriever

@router.post("/generate")
async def generate_report(...):
    retriever = RAGRetriever(openai_service)
    theories = await retriever.search(
        query=search_query,
        top_k=request.top_k,
        threshold=request.similarity_threshold,
        db=db
    )  # 使用新 service
    # 刪除舊的 L586-629 重複代碼
    # ...
```

**Expected**: 所有測試保持 GREEN ✅

---

### Step 3: DialogueExtractor 提取

#### 3.1 RED - 寫測試
```python
# tests/unit/test_dialogue_extractor.py

async def test_extract_dialogues_2_speakers():
    """Test extracting key dialogues for 2-person session"""
    extractor = DialogueExtractor(openai_service)
    transcript = "Co: 你好\nCl: 我想討論轉職..."

    dialogues = await extractor.extract(transcript, num_participants=2)

    assert len(dialogues) >= 5
    assert len(dialogues) <= 10
    assert dialogues[0]["speaker"] in ["speaker1", "speaker2"]
```

**Expected**: 測試失敗 ❌ RED

#### 3.2 GREEN - 實作 Service
```python
# app/services/dialogue_extractor.py

class DialogueExtractor:
    """提取關鍵對話片段"""

    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    async def extract(
        self,
        transcript: str,
        num_participants: int
    ) -> List[dict]:
        """Extract 5-10 key dialogue excerpts"""
        # 從 rag_report.py L869-906 提取邏輯
        # ...
```

**Expected**: 測試通過 ✅ GREEN

---

### Step 4: 消除重複邏輯

#### 4.1 重構目標
```python
# 現在: generate_report_stream() 和 generate_report() 重複 60% 代碼

# 重構後:
async def generate_report_stream(...):
    """SSE streaming - 調用 generate_report() 並包裝成 stream"""
    # 只負責 streaming 邏輯
    result = await generate_report(...)  # 復用核心邏輯
    # yield SSE events
    # ...

async def generate_report(...):
    """核心報告生成邏輯 - 單一職責"""
    parser = TranscriptParser(openai_service)
    retriever = RAGRetriever(openai_service)
    extractor = DialogueExtractor(openai_service)

    # Step 1: Parse
    parsed_data = await parser.parse(transcript)

    # Step 2: RAG search
    theories = await retriever.search(...)

    # Step 3: Generate report (LLM call)
    report_content = await _generate_with_llm(...)

    # Step 4: Extract dialogues
    dialogues = await extractor.extract(...)

    # Step 5: Build response
    return {...}
```

#### 4.2 驗證
```bash
# 跑所有測試
pytest tests/integration/test_legacy_formats.py -v
pytest tests/integration/test_enhanced_formats.py -v
pytest tests/unit/ -v

# Expected: 所有測試 GREEN ✅
```

---

## 🔍 驗收標準

### Phase 1 完成條件

✅ **功能要求**
- [ ] API 行為不變 (向後兼容)
- [ ] 所有 integration tests 通過
- [ ] 新增 unit tests 覆蓋率 > 80%

✅ **代碼品質**
- [ ] `rag_report.py` 行數 < 600 行 (從 1009 減少)
- [ ] 無重複邏輯 (DRY)
- [ ] 符合 SRP (Single Responsibility Principle)

✅ **測試覆蓋**
- [ ] `TranscriptParser` - 3+ unit tests
- [ ] `RAGRetriever` - 3+ unit tests
- [ ] `DialogueExtractor` - 3+ unit tests
- [ ] All tests GREEN

---

## 🚀 執行時間表

| Step | 任務 | 預估時間 | TDD 階段 |
|------|------|---------|---------|
| 1.1 | TranscriptParser tests | 30 min | RED ❌ |
| 1.2 | TranscriptParser service | 45 min | GREEN ✅ |
| 1.3 | Refactor rag_report.py | 30 min | GREEN ✅ |
| 2.1 | RAGRetriever tests | 30 min | RED ❌ |
| 2.2 | RAGRetriever service | 45 min | GREEN ✅ |
| 2.3 | Refactor rag_report.py | 30 min | GREEN ✅ |
| 3.1 | DialogueExtractor tests | 30 min | RED ❌ |
| 3.2 | DialogueExtractor service | 30 min | GREEN ✅ |
| 3.3 | Refactor rag_report.py | 30 min | GREEN ✅ |
| 4 | 消除重複邏輯 | 60 min | GREEN ✅ |
| 5 | 全面測試驗證 | 30 min | GREEN ✅ |

**總計**: ~6 小時

---

## 🛡️ 風險管理

### 風險識別

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| 破壞現有 API 行為 | 高 | Integration tests 保護 |
| LLM prompt 改動影響結果 | 中 | 逐步遷移，保留舊 prompts |
| 測試覆蓋不足 | 中 | 先寫測試再重構 (TDD) |
| 重構時間超出預期 | 低 | 分階段進行，可隨時停止 |

### 回滾計劃

如果重構失敗：
1. Git revert 到重構前
2. 所有變更都在 feature branch 進行
3. Integration tests 作為安全網

---

## 📚 參考文檔

- **TDD Workflow**: `CLAUDE.md` L68-123
- **Testing Strategy**: `CLAUDE.md` L199-222
- **Current Test Files**:
  - `tests/integration/test_legacy_formats.py`
  - `tests/integration/test_enhanced_formats.py`

---

**原則**:
> "Code without tests is legacy code. Tests without passing are todos. Commits without hooks are technical debt."
> — CLAUDE.md L250

**Red-Green-Refactor 循環**: 每個步驟都嚴格遵循 TDD
