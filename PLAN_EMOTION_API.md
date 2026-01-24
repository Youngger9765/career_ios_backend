# Emotion Analysis API - Implementation Plan

**Version**: 1.0
**Date**: 2026-01-25
**Author**: Claude (based on Allen's requirements)
**Tenant**: island_parents

---

## 1. Overview

### 1.1 Purpose
實作即時情緒分析 API，根據對話內容和目標句子，判斷情緒層級（綠燈/黃燈/紅燈）並提供引導語。

### 1.2 Key Requirements (Allen's Spec)
- **Response Time**: < 3 秒（前端 timeout 10 秒）
- **Model**: models/gemini-flash-lite-latest
- **Input**: context (對話上下文) + target (目標句子)
- **Output**: level (1/2/3) + hint (引導語，≤17 字)
- **Format**: LLM 回應格式為 `數字|引導語`

---

## 2. API Design

### 2.1 Endpoint
```
POST /api/v1/sessions/{session_id}/emotion-feedback
```

### 2.2 Request Schema
```python
class EmotionFeedbackRequest(BaseModel):
    context: str  # 對話上下文（可能包含多輪對話）
    target: str   # 要分析的目標句子

    class Config:
        json_schema_extra = {
            "example": {
                "context": "小明：我今天考試不及格\n媽媽：你有認真準備嗎？",
                "target": "你就是不用功！"
            }
        }
```

### 2.3 Response Schema
```python
class EmotionFeedbackResponse(BaseModel):
    level: int  # 1=綠燈（良好）, 2=黃燈（警告）, 3=紅燈（危險）
    hint: str   # 引導語，最多 17 字

    class Config:
        json_schema_extra = {
            "example": {
                "level": 3,
                "hint": "試著同理孩子的挫折感"
            }
        }
```

### 2.4 Error Responses
- `400 Bad Request`: 缺少必要參數或格式錯誤
- `404 Not Found`: Session 不存在
- `500 Internal Server Error`: LLM 呼叫失敗或解析錯誤
- `504 Gateway Timeout`: LLM 回應超過 3 秒

---

## 3. LLM Integration

### 3.1 Model Configuration
```python
model_name = "models/gemini-flash-lite-latest"
temperature = 0  # 確保穩定輸出
max_output_tokens = 50  # 足夠產生 "數字|引導語" 格式
```

### 3.2 System Prompt (根據 Allen 的規格)
```
你是親子溝通專家，負責即時分析家長對話的情緒狀態。
請根據對話上下文和目標句子，評估情緒層級並提供簡短引導。

情緒層級定義：
1. 綠燈（良好）：語氣平和、具同理心、建設性溝通
2. 黃燈（警告）：語氣稍顯急躁、帶有責備但未失控
3. 紅燈（危險）：語氣激動、攻擊性強、可能傷害親子關係

回應格式（嚴格遵守）：
數字|引導語

規則：
- 數字必須是 1, 2, 或 3
- 引導語必須 ≤17 字（中文字符）
- 用 | 分隔數字和引導語
- 引導語要具體、可行、同理

範例：
3|試著同理孩子的挫折感
2|深呼吸，用平和語氣重述
1|很好的同理心表達
```

### 3.3 User Prompt Template
```python
def build_user_prompt(context: str, target: str) -> str:
    return f"""
對話上下文：
{context}

目標句子（需分析）：
{target}

請評估目標句子的情緒層級並提供引導語。
"""
```

### 3.4 Response Parsing Logic
```python
def parse_llm_response(response: str) -> tuple[int, str]:
    """
    解析 LLM 回應：數字|引導語

    Returns:
        (level, hint)

    Raises:
        ValueError: 格式錯誤
    """
    parts = response.strip().split('|')

    if len(parts) != 2:
        raise ValueError(f"Invalid format: expected 'number|text', got '{response}'")

    # Parse level
    level_str, hint = parts
    try:
        level = int(level_str)
    except ValueError:
        raise ValueError(f"Invalid level: expected integer, got '{level_str}'")

    if level not in [1, 2, 3]:
        raise ValueError(f"Invalid level: expected 1/2/3, got {level}")

    # Validate hint length (17 chars max)
    if len(hint) > 17:
        raise ValueError(f"Hint too long: {len(hint)} chars (max 17)")

    return level, hint
```

---

## 4. Error Handling Strategy

### 4.1 LLM Call Failures
```python
try:
    response = await gemini_client.generate_content(...)
except asyncio.TimeoutError:
    raise HTTPException(status_code=504, detail="LLM response timeout (>3s)")
except Exception as e:
    logger.error(f"LLM call failed: {e}")
    raise HTTPException(status_code=500, detail="LLM service unavailable")
```

### 4.2 Parsing Failures
```python
try:
    level, hint = parse_llm_response(llm_response)
except ValueError as e:
    logger.error(f"Failed to parse LLM response: {e}")
    # Fallback: 黃燈 + 通用引導語
    level = 2
    hint = "請試著用平和語氣溝通"
```

### 4.3 Session Validation
```python
session = await db.get_session(session_id)
if not session:
    raise HTTPException(status_code=404, detail="Session not found")
```

---

## 5. Performance Optimization

### 5.1 Timeout Configuration
```python
# FastAPI endpoint timeout
@router.post("/sessions/{session_id}/emotion-feedback", timeout=3.0)

# Gemini client timeout
gemini_client.timeout = 2.5  # 留 0.5 秒給解析和回應
```

### 5.2 Caching Strategy (Optional)
- **Not recommended** for real-time emotion analysis (每次對話都是獨特的)
- 如果未來需要，可考慮 cache key = hash(context + target)

### 5.3 Monitoring
```python
import time

start_time = time.time()
# ... LLM call ...
elapsed = time.time() - start_time

logger.info(f"Emotion analysis took {elapsed:.2f}s")
if elapsed > 3.0:
    logger.warning(f"Slow response: {elapsed:.2f}s")
```

---

## 6. Testing Strategy

### 6.1 Test Scenarios

#### Scenario 1: 綠燈（良好溝通）
```python
async def test_green_light():
    response = await client.post(
        "/api/v1/sessions/test-session-id/emotion-feedback",
        json={
            "context": "小明：我今天很開心\n媽媽：發生什麼好事了？",
            "target": "媽媽願意聽你分享，真好"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["level"] == 1
    assert len(data["hint"]) <= 17
```

#### Scenario 2: 黃燈（警告）
```python
async def test_yellow_light():
    response = await client.post(
        "/api/v1/sessions/test-session-id/emotion-feedback",
        json={
            "context": "小明：作業我不會寫\n媽媽：你上課有認真聽嗎？",
            "target": "你怎麼又不會？"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["level"] == 2
    assert len(data["hint"]) <= 17
```

#### Scenario 3: 紅燈（危險）
```python
async def test_red_light():
    response = await client.post(
        "/api/v1/sessions/test-session-id/emotion-feedback",
        json={
            "context": "小明：我考試不及格\n媽媽：你有認真準備嗎？",
            "target": "你就是不用功！笨死了！"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["level"] == 3
    assert len(data["hint"]) <= 17
```

#### Scenario 4: 格式錯誤
```python
async def test_invalid_format():
    response = await client.post(
        "/api/v1/sessions/test-session-id/emotion-feedback",
        json={
            "context": "",  # 空白 context
            "target": "測試"
        }
    )
    assert response.status_code == 400
```

#### Scenario 5: Session 不存在
```python
async def test_session_not_found():
    response = await client.post(
        "/api/v1/sessions/non-existent-id/emotion-feedback",
        json={
            "context": "測試",
            "target": "測試"
        }
    )
    assert response.status_code == 404
```

### 6.2 Performance Tests
```python
async def test_response_time():
    import time
    start = time.time()

    response = await client.post(
        "/api/v1/sessions/test-session-id/emotion-feedback",
        json={
            "context": "小明：今天好累\n媽媽：早點休息吧",
            "target": "你辛苦了，早點睡"
        }
    )

    elapsed = time.time() - start
    assert elapsed < 3.0, f"Response took {elapsed:.2f}s (max 3s)"
```

---

## 7. Implementation Checklist

### Phase 1: Core Implementation
- [ ] 建立 API endpoint (`app/routers/emotion.py`)
- [ ] 定義 Request/Response schemas (`app/models/emotion.py`)
- [ ] 實作 Gemini Flash Lite Latest 整合 (`app/services/gemini_emotion.py`)
- [ ] 實作 System/User prompt 組裝
- [ ] 實作回應解析邏輯 (`parse_llm_response`)

### Phase 2: Error Handling & Validation
- [ ] 加入 timeout 處理（3 秒）
- [ ] 加入 LLM 呼叫錯誤處理
- [ ] 加入解析失敗 fallback 機制
- [ ] 加入 session 驗證
- [ ] 加入 hint 長度驗證（≤17 字）

### Phase 3: Testing
- [ ] 撰寫綠燈場景測試
- [ ] 撰寫黃燈場景測試
- [ ] 撰寫紅燈場景測試
- [ ] 撰寫格式錯誤測試
- [ ] 撰寫 session 不存在測試
- [ ] 撰寫效能測試（<3 秒）

### Phase 4: Documentation & Deployment
- [ ] 更新 IOS_GUIDE_PARENTS.md（Section 2.4: Emotion Analysis API）
- [ ] 更新 OpenAPI docs（自動生成）
- [ ] 部署到 staging 環境
- [ ] 前端整合測試

---

## 8. File Structure

```
app/
├── routers/
│   └── emotion.py              # API endpoint
├── models/
│   └── emotion.py              # Pydantic schemas
├── services/
│   └── gemini_emotion.py       # Gemini integration
└── utils/
    └── emotion_parser.py       # Response parsing logic

tests/
└── integration/
    └── test_emotion_api.py     # Integration tests
```

---

## 9. Risk Mitigation

### 9.1 LLM 回應不穩定
**Risk**: LLM 可能產生非預期格式
**Mitigation**:
- Fallback to level=2 + 通用引導語
- 記錄所有解析失敗案例，定期檢討 prompt

### 9.2 回應速度過慢
**Risk**: LLM 回應 >3 秒
**Mitigation**:
- 使用 models/gemini-flash-lite-latest (fastest variant)
- maxOutputTokens=50 (限制輸出長度)
- 前端 timeout=10 秒（給予緩衝）

### 9.3 Hint 長度超過限制
**Risk**: LLM 產生超過 17 字的引導語
**Mitigation**:
- System prompt 明確要求 ≤17 字
- 解析時驗證長度，超過則截斷並記錄
- 定期檢視並優化 prompt

---

## 10. Success Criteria

✅ **API 功能完整**:
- [ ] 正確判斷綠燈/黃燈/紅燈
- [ ] Hint 長度 ≤17 字
- [ ] 回應時間 <3 秒（95th percentile）

✅ **錯誤處理健全**:
- [ ] 所有錯誤情境都有對應處理
- [ ] Fallback 機制正常運作

✅ **測試覆蓋完整**:
- [ ] 所有情境都有測試
- [ ] 測試通過率 100%

✅ **文件完整**:
- [ ] IOS_GUIDE_PARENTS.md 已更新
- [ ] OpenAPI docs 正確顯示

---

## 11. Next Steps

1. **Review this plan** with the team
2. **Create GitHub Issue** (using git-issue-pr-flow agent)
3. **Start TDD implementation** (using tdd-orchestrator agent)
4. **Follow TODO.md** for step-by-step execution

---

**End of Plan**
