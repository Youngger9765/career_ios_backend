"""API endpoints for agent management"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.agent import Agent, AgentVersion

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentCreate(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    status: str = "draft"


class AgentVersionCreate(BaseModel):
    config_json: dict
    created_by: Optional[str] = None


class AgentResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: Optional[str]
    status: str
    active_version_id: Optional[int]


class AgentVersionResponse(BaseModel):
    id: int
    agent_id: int
    version: int
    state: str
    config_json: dict


@router.get("/", response_model=List[AgentResponse])
async def list_agents(db: AsyncSession = Depends(get_db)):
    """List all agents"""

    try:
        result = await db.execute(select(Agent))
        agents = result.scalars().all()

        return [
            AgentResponse(
                id=agent.id,
                slug=agent.slug,
                name=agent.name,
                description=agent.description,
                status=agent.status,
                active_version_id=agent.active_version_id,
            )
            for agent in agents
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}") from e


@router.post("/", response_model=AgentResponse)
async def create_agent(agent_data: AgentCreate, db: AsyncSession = Depends(get_db)):
    """Create a new agent"""

    try:
        agent = Agent(
            slug=agent_data.slug,
            name=agent_data.name,
            description=agent_data.description,
            status=agent_data.status,
        )

        db.add(agent)
        await db.commit()
        await db.refresh(agent)

        return AgentResponse(
            id=agent.id,
            slug=agent.slug,
            name=agent.name,
            description=agent.description,
            status=agent.status,
            active_version_id=agent.active_version_id,
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}") from e


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Get agent by ID"""

    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()

        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        return AgentResponse(
            id=agent.id,
            slug=agent.slug,
            name=agent.name,
            description=agent.description,
            status=agent.status,
            active_version_id=agent.active_version_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}") from e


@router.get("/{agent_id}/versions", response_model=List[AgentVersionResponse])
async def list_agent_versions(agent_id: int, db: AsyncSession = Depends(get_db)):
    """List all versions for an agent"""

    try:
        result = await db.execute(select(AgentVersion).where(AgentVersion.agent_id == agent_id))
        versions = result.scalars().all()

        return [
            AgentVersionResponse(
                id=v.id,
                agent_id=v.agent_id,
                version=v.version,
                state=v.state,
                config_json=v.config_json,
            )
            for v in versions
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list versions: {str(e)}") from e
