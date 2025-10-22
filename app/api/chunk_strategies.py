"""Chunk Strategies API - Chunk 策略管理"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/rag/evaluation/chunk-strategies", tags=["chunk-strategies"]
)


# Schemas
class ChunkStrategyCreate(BaseModel):
    name: str
    type: str  # recursive, parent_child, normal, semantic, sliding_window
    chunk_size: int
    chunk_overlap: int
    description: Optional[str] = None
    is_default: bool = False


class ChunkStrategyUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None


class ChunkStrategyResponse(BaseModel):
    id: str
    name: str
    type: str
    chunk_size: int
    chunk_overlap: int
    description: Optional[str]
    is_default: bool
    created_at: str


# In-memory storage (replace with database in production)
_strategies_store = {}


def get_all_strategies():
    """Get all chunk strategies as a list (helper for UI rendering)"""
    _init_default_strategies()
    return list(_strategies_store.values())


def _init_default_strategies():
    """Initialize default chunk strategies"""
    if not _strategies_store:
        defaults = [
            {
                "id": str(uuid.uuid4()),
                "name": "Recursive-小型",
                "type": "recursive",
                "chunk_size": 200,
                "chunk_overlap": 40,
                "description": "遞迴切割，適合精細檢索",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Recursive-中型",
                "type": "recursive",
                "chunk_size": 400,
                "chunk_overlap": 80,
                "description": "遞迴切割，平衡大小，適合大多數場景",
                "is_default": True,
                "created_at": datetime.now().isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Recursive-大型",
                "type": "recursive",
                "chunk_size": 800,
                "chunk_overlap": 160,
                "description": "遞迴切割，保留更多上下文",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Parent-Child-標準",
                "type": "parent_child",
                "chunk_size": 400,
                "chunk_overlap": 0,
                "description": "父子文檔結構，適合階層式檢索",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Normal-快速",
                "type": "normal",
                "chunk_size": 300,
                "chunk_overlap": 50,
                "description": "一般切割，處理速度快",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Semantic-智能",
                "type": "semantic",
                "chunk_size": 500,
                "chunk_overlap": 100,
                "description": "基於語義切割，保持語意完整性",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
            },
        ]
        for strategy in defaults:
            _strategies_store[strategy["id"]] = strategy


# API Endpoints
@router.get("/", response_model=List[ChunkStrategyResponse])
async def list_chunk_strategies():
    """獲取所有 chunk 策略"""
    _init_default_strategies()
    return list(_strategies_store.values())


@router.get("/{strategy_id}", response_model=ChunkStrategyResponse)
async def get_chunk_strategy(strategy_id: str):
    """獲取特定 chunk 策略"""
    _init_default_strategies()

    if strategy_id not in _strategies_store:
        raise HTTPException(status_code=404, detail="策略不存在")

    return _strategies_store[strategy_id]


@router.post("/", response_model=ChunkStrategyResponse)
async def create_chunk_strategy(strategy_data: ChunkStrategyCreate):
    """建立新的 chunk 策略"""
    _init_default_strategies()

    # Validate chunk size
    if strategy_data.chunk_size < 50:
        raise HTTPException(status_code=400, detail="Chunk size 必須大於 50")

    # If setting as default, unset other defaults
    if strategy_data.is_default:
        for strategy in _strategies_store.values():
            strategy["is_default"] = False

    strategy = {
        "id": str(uuid.uuid4()),
        "name": strategy_data.name,
        "type": strategy_data.type,
        "chunk_size": strategy_data.chunk_size,
        "chunk_overlap": strategy_data.chunk_overlap,
        "description": strategy_data.description,
        "is_default": strategy_data.is_default,
        "created_at": datetime.now().isoformat(),
    }

    _strategies_store[strategy["id"]] = strategy
    return strategy


@router.put("/{strategy_id}", response_model=ChunkStrategyResponse)
async def update_chunk_strategy(strategy_id: str, strategy_data: ChunkStrategyUpdate):
    """更新 chunk 策略"""
    _init_default_strategies()

    if strategy_id not in _strategies_store:
        raise HTTPException(status_code=404, detail="策略不存在")

    strategy = _strategies_store[strategy_id]

    # Update fields
    if strategy_data.name is not None:
        strategy["name"] = strategy_data.name
    if strategy_data.type is not None:
        strategy["type"] = strategy_data.type
    if strategy_data.chunk_size is not None:
        if strategy_data.chunk_size < 50:
            raise HTTPException(status_code=400, detail="Chunk size 必須大於 50")
        strategy["chunk_size"] = strategy_data.chunk_size
    if strategy_data.chunk_overlap is not None:
        strategy["chunk_overlap"] = strategy_data.chunk_overlap
    if strategy_data.description is not None:
        strategy["description"] = strategy_data.description
    if strategy_data.is_default is not None:
        if strategy_data.is_default:
            # Unset other defaults
            for s in _strategies_store.values():
                s["is_default"] = False
        strategy["is_default"] = strategy_data.is_default

    return strategy


@router.delete("/{strategy_id}")
async def delete_chunk_strategy(strategy_id: str):
    """刪除 chunk 策略"""
    _init_default_strategies()

    if strategy_id not in _strategies_store:
        raise HTTPException(status_code=404, detail="策略不存在")

    # Check if it's being used (implement check when integrated with experiments)
    # For now, allow deletion

    del _strategies_store[strategy_id]

    return {"success": True, "message": "策略已刪除"}
