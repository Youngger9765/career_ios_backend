# Realtime.py 重構計劃

**日期**: 2025-12-26
**當前狀態**: realtime.py = 1390 行（違反 CLAUDE.md 300 行限制）
**目標**: 拆分為 5 個模塊（4 個 service + 1 個 slim API）

---

## 📊 現況分析

### 檔案統計
```
總行數: 1390 lines
函數數: 12 functions
API 端點: 3 endpoints
```

### API 端點
1. `POST /analyze` - 即時分析（主要端點）
2. `POST /elevenlabs-token` - ElevenLabs token 生成
3. `POST /parents-report` - 家長對話報告

### 核心函數分類

#### 🔍 RAG 相關 (3 functions)
- `_detect_parenting_keywords(transcript)` - 檢測親子關鍵字
- `_detect_parenting_theory(title)` - 識別教養理論
- `_search_rag_knowledge(transcript, db, top_k, threshold)` - 向量搜尋

#### 🚦 Safety 評估 (1 function)
- `_assess_safety_level(transcript, speakers)` - 安全等級評估（滑動窗口）

#### 📝 Prompt 建構 (3 functions)
- `_build_annotated_transcript(transcript, speakers)` - 標註逐字稿
- `_build_emergency_prompt(transcript, rag_context)` - 緊急模式 prompt
- `_build_practice_prompt(transcript, speakers, rag_context)` - 練習模式 prompt

#### 🤖 LLM Provider (1 function)
- `_analyze_with_codeer(prompt, codeer_model, session_id)` - Codeer API 整合

#### 📊 Data Pipeline (1 function)
- `write_to_gbq_async(data)` - 寫入 BigQuery

#### 🎯 API Handlers (3 functions)
- `analyze_transcript(request, db)` - 主要分析端點
- `generate_elevenlabs_token()` - Token 生成
- `generate_parents_report(request, db)` - 報告生成

---

## 🎯 重構策略

### 模塊拆分計劃

```
realtime.py (1390 lines)
    ↓
┌──────────────────────────────────────────────┐
│ app/services/realtime_rag.py        (~150L) │  ← Step 1
├──────────────────────────────────────────────┤
│ app/services/realtime_safety.py     (~200L) │  ← Step 2
├──────────────────────────────────────────────┤
│ app/services/realtime_prompts.py    (~400L) │  ← Step 3
├──────────────────────────────────────────────┤
│ app/services/realtime_analysis.py   (~300L) │  ← Step 4
├──────────────────────────────────────────────┤
│ app/api/realtime.py (slim)          (~340L) │  ← Step 5
└──────────────────────────────────────────────┘
```

---

## 📋 詳細執行步驟

### Step 1: 提取 RAG 模塊 (~150 lines)

**目標檔案**: `app/services/realtime_rag.py`

#### 提取函數
```python
# Lines to extract from realtime.py:
- _detect_parenting_keywords() (lines 214-229)
- _detect_parenting_theory() (lines 231-263)
- _search_rag_knowledge() (lines 265-319)
```

#### 常量提取
```python
# PARENTING_KEYWORDS list (需要找到定義位置)
# 相關的 RAG 配置常量
```

#### 新檔案結構
```python
"""
RAG Knowledge Base Integration for Realtime Counseling
"""
from typing import List
from sqlalchemy.orm import Session
from app.schemas.realtime import RAGSource
from app.services.rag_chat_service import RAGChatService
import logging

logger = logging.getLogger(__name__)

# Constants
PARENTING_KEYWORDS = [...]

def detect_parenting_keywords(transcript: str) -> bool:
    """檢測親子教養關鍵字"""
    # 移除前綴 _，改為 public function
    pass

def detect_parenting_theory(title: str) -> str:
    """識別教養理論類別"""
    pass

async def search_rag_knowledge(
    transcript: str,
    db: Session,
    top_k: int = 3,
    similarity_threshold: float = 0.5
) -> List[RAGSource]:
    """向量搜尋親子教養知識庫"""
    pass
```

#### realtime.py 更新
```python
# 添加 import
from app.services.realtime_rag import (
    detect_parenting_keywords,
    detect_parenting_theory,
    search_rag_knowledge
)

# 刪除舊函數定義
# 更新所有調用點（去掉 _ 前綴）
```

#### 測試指令
```bash
# 檢查檔案創建
ls -la app/services/realtime_rag.py
wc -l app/services/realtime_rag.py

# 執行測試
poetry run pytest tests/integration/test_realtime_api.py::test_realtime_analyze -v
```

---

### Step 2: 提取 Safety 模塊 (~200 lines)

**目標檔案**: `app/services/realtime_safety.py`

#### 提取函數
```python
# Lines to extract:
- _assess_safety_level() (lines 321-410)
```

#### 常量提取
```python
# Safety configuration (lines 43-52)
SAFETY_WINDOW_SPEAKER_TURNS = 10
SAFETY_WINDOW_CHARACTERS = 300
ANNOTATED_SAFETY_WINDOW_TURNS = 5

# Safety keywords (需要找到定義位置)
RED_KEYWORDS = [...]
YELLOW_KEYWORDS = [...]
GREEN_KEYWORDS = [...]
```

#### 新檔案結構
```python
"""
Safety Level Assessment for Realtime Counseling
"""
from typing import List, Dict
from app.schemas.realtime import SafetyLevel
import logging

logger = logging.getLogger(__name__)

# Configuration
SAFETY_WINDOW_SPEAKER_TURNS = 10
SAFETY_WINDOW_CHARACTERS = 300
ANNOTATED_SAFETY_WINDOW_TURNS = 5

# Safety keywords
RED_KEYWORDS = [...]
YELLOW_KEYWORDS = [...]
GREEN_KEYWORDS = [...]

def assess_safety_level(
    transcript: str,
    speakers: List[Dict]
) -> SafetyLevel:
    """評估安全等級（使用滑動窗口）"""
    pass

def get_analysis_interval(safety_level: SafetyLevel) -> int:
    """根據安全等級返回分析間隔（秒）"""
    intervals = {
        SafetyLevel.red: 15,
        SafetyLevel.yellow: 30,
        SafetyLevel.green: 60
    }
    return intervals.get(safety_level, 60)
```

#### realtime.py 更新
```python
from app.services.realtime_safety import (
    assess_safety_level,
    get_analysis_interval
)
```

#### 測試指令
```bash
wc -l app/services/realtime_safety.py
poetry run pytest tests/integration/test_realtime_api.py -v -k safety
```

---

### Step 3: 提取 Prompts 模塊 (~400 lines)

**目標檔案**: `app/services/realtime_prompts.py`

#### 提取函數
```python
# Lines to extract:
- _build_annotated_transcript() (lines 412-456)
- _build_emergency_prompt() (lines 458-537)
- _build_practice_prompt() (lines 539-656)
```

#### 常量提取
```python
# System instruction (lines 54-212)
CACHE_SYSTEM_INSTRUCTION = """..."""

# 所有 prompt template strings
```

#### 新檔案結構
```python
"""
Prompt Templates for Realtime Counseling Analysis
"""
from typing import List, Dict
from app.schemas.realtime import CounselingMode, RAGSource
import logging

logger = logging.getLogger(__name__)

# System instruction for caching
CACHE_SYSTEM_INSTRUCTION = """..."""

def build_annotated_transcript(
    transcript: str,
    speakers: List[Dict],
    window_turns: int = 5
) -> str:
    """建構標註的逐字稿（標記最近對話）"""
    pass

def build_emergency_prompt(
    transcript: str,
    rag_context: str
) -> str:
    """建構緊急模式 prompt"""
    pass

def build_practice_prompt(
    transcript: str,
    speakers: List[Dict],
    rag_context: str
) -> str:
    """建構練習模式 prompt"""
    pass

def build_parents_report_prompt(
    transcript: str,
    rag_context: str
) -> str:
    """建構家長報告 prompt"""
    pass
```

#### realtime.py 更新
```python
from app.services.realtime_prompts import (
    build_annotated_transcript,
    build_emergency_prompt,
    build_practice_prompt,
    build_parents_report_prompt
)
```

#### 測試指令
```bash
wc -l app/services/realtime_prompts.py
poetry run pytest tests/integration/test_realtime_api.py::test_realtime_analyze -v
```

---

### Step 4: 提取 Analysis 模塊 (~300 lines)

**目標檔案**: `app/services/realtime_analysis.py`

#### 提取函數
```python
# Lines to extract:
- _analyze_with_codeer() (lines 676-872)
- write_to_gbq_async() (lines 658-674)
```

#### 新檔案結構
```python
"""
LLM Provider Integration and Data Pipeline for Realtime Analysis
"""
from typing import Dict, Optional
import httpx
import logging
from datetime import datetime, timezone

from app.services.gbq_service import gbq_service
from app.schemas.realtime import CodeerTokenMetadata

logger = logging.getLogger(__name__)

async def analyze_with_codeer(
    prompt: str,
    codeer_model: str,
    session_id: str
) -> Dict:
    """使用 Codeer API 進行分析"""
    pass

async def write_to_gbq_async(data: Dict) -> None:
    """非同步寫入 BigQuery"""
    pass

def parse_analysis_response(response_text: str) -> Dict:
    """解析 LLM 回應為結構化資料"""
    pass
```

#### realtime.py 更新
```python
from app.services.realtime_analysis import (
    analyze_with_codeer,
    write_to_gbq_async
)
```

#### 測試指令
```bash
wc -l app/services/realtime_analysis.py
poetry run pytest tests/integration/test_realtime_api.py -v
```

---

### Step 5: 清理 API 檔案 (~340 lines)

**目標**: realtime.py 保留 ≤400 行

#### 保留內容
```python
"""Realtime STT Counseling API"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Import from service modules
from app.services import (
    realtime_rag,
    realtime_safety,
    realtime_prompts,
    realtime_analysis
)
from app.services.gemini_service import GeminiService
from app.core.database import get_db
from app.schemas.realtime import (...)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/realtime", tags=["Realtime Counseling"])

# Initialize services
gemini_service = GeminiService()

# --- API Endpoints ---

@router.post("/analyze", response_model=RealtimeAnalyzeResponse)
async def analyze_transcript(
    request: RealtimeAnalyzeRequest,
    db: Session = Depends(get_db)
):
    """主要分析端點 - 協調各 service 模塊"""
    # 1. RAG search
    rag_sources = await realtime_rag.search_rag_knowledge(...)

    # 2. Safety assessment
    safety_level = realtime_safety.assess_safety_level(...)

    # 3. Build prompt
    prompt = realtime_prompts.build_practice_prompt(...)

    # 4. Analyze with LLM
    result = await realtime_analysis.analyze_with_codeer(...)

    # 5. Return response
    return RealtimeAnalyzeResponse(...)

@router.post("/elevenlabs-token")
async def generate_elevenlabs_token():
    """ElevenLabs token 生成"""
    pass

@router.post("/parents-report", response_model=ParentsReportResponse)
async def generate_parents_report(...):
    """家長對話報告生成"""
    pass
```

#### 測試指令
```bash
wc -l app/api/realtime.py  # Should be ~340 lines
poetry run pytest tests/integration/test_realtime_api.py -v  # All tests GREEN
poetry run ruff check app/api/realtime.py app/services/realtime_*.py
```

---

## ✅ 驗證檢查清單

### 每個步驟完成後檢查

- [ ] **檔案創建**: 新 service module 存在
  ```bash
  ls -la app/services/realtime_*.py
  ```

- [ ] **行數驗證**: 每個檔案符合限制
  ```bash
  wc -l app/services/realtime_*.py app/api/realtime.py
  ```

- [ ] **測試通過**: 所有整合測試 GREEN
  ```bash
  poetry run pytest tests/integration/test_realtime_api.py -v
  ```

- [ ] **Import 正確**: 沒有 import 錯誤
  ```bash
  python -c "from app.api import realtime"
  ```

- [ ] **Lint 通過**: Ruff 檢查無錯誤
  ```bash
  poetry run ruff check app/api/realtime.py app/services/realtime_*.py
  ```

### 全部完成後最終驗證

- [ ] **檔案數量**: 5 個檔案（4 service + 1 API）
- [ ] **總行數**: 原 1390 行拆分為 ~1390 行（分散在 5 個檔案）
- [ ] **API 檔案**: realtime.py ≤ 400 行（目標 ~340）
- [ ] **Service 檔案**: 每個 ≤ 400 行
- [ ] **測試覆蓋**: 所有現有測試保持 GREEN
- [ ] **功能完整**: 3 個 API 端點都正常運作
- [ ] **無 circular import**: 模塊間依賴清晰

---

## 🎯 成功標準

### 檔案大小目標

| 檔案 | 目標行數 | 最大限制 | 狀態 |
|------|---------|---------|------|
| realtime_rag.py | ~150 | 400 | ⏳ |
| realtime_safety.py | ~200 | 400 | ⏳ |
| realtime_prompts.py | ~400 | 400 | ⏳ |
| realtime_analysis.py | ~300 | 400 | ⏳ |
| realtime.py (API) | ~340 | 300* | ⏳ |

\* API 路由可接受 ≤400 行，但應盡量接近 300 行

### 測試要求

```bash
# 所有測試必須通過
poetry run pytest tests/integration/test_realtime_api.py -v

# 預期測試數量
- test_realtime_analyze: ✅
- test_realtime_analyze_gemini: ✅
- test_realtime_analyze_codeer_*: ✅
- test_parents_report: ✅
- (其他相關測試): ✅
```

---

## ⚠️ 注意事項

### TDD 安全網
- **每一步都要跑測試**
- **測試失敗立即停止**
- **不要一次改太多**

### Import 管理
- 避免 circular imports
- Service modules 不應相互 import
- 所有 service import 都在 API 層協調

### 向後兼容
- API 端點不變
- Request/Response schemas 不變
- 功能行為不變
- 只有內部結構重組

### 命名一致性
- 移除函數前綴 `_`（變為 public）
- 函數名保持 snake_case
- 模塊名使用 `realtime_` 前綴

---

## 📊 進度追蹤

| Step | 模塊 | 狀態 | 測試 | 備註 |
|------|------|------|------|------|
| 1 | realtime_rag.py | ⏳ 待執行 | - | RAG 搜尋與關鍵字檢測 |
| 2 | realtime_safety.py | ⏳ 待執行 | - | 安全等級評估 |
| 3 | realtime_prompts.py | ⏳ 待執行 | - | Prompt 模板建構 |
| 4 | realtime_analysis.py | ⏳ 待執行 | - | LLM Provider 整合 |
| 5 | realtime.py (slim) | ⏳ 待執行 | - | API 端點協調 |

**圖例**:
- ⏳ 待執行
- 🔄 進行中
- ✅ 已完成
- ❌ 失敗需修正

---

## 🚀 執行建議

### 一次一步
不要試圖一次完成所有步驟。每個步驟：
1. 提取函數到新模塊
2. 更新 import
3. 跑測試
4. 確認 GREEN
5. Commit
6. 繼續下一步

### Commit 策略
```bash
git add app/services/realtime_rag.py app/api/realtime.py
git commit -m "refactor: extract RAG module from realtime.py (Step 1/5)"

git add app/services/realtime_safety.py app/api/realtime.py
git commit -m "refactor: extract Safety module from realtime.py (Step 2/5)"

# ... 以此類推
```

### 回滾準備
如果某步驟失敗：
```bash
git diff  # 查看變更
git checkout -- app/api/realtime.py  # 還原檔案
# 修正問題後重試
```

---

**最後更新**: 2025-12-26
**文檔版本**: 1.0
**狀態**: 分析完成，等待執行
