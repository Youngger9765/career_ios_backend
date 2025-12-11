"""Codeer Chat Session Pool Manager"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from app.services.codeer_client import CodeerClient

logger = logging.getLogger(__name__)


class CodeerSessionPool:
    """Session pool for reusing Codeer chat sessions"""

    def __init__(self, ttl_seconds: int = 7200):
        self.sessions: Dict[str, dict] = {}
        self.ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()

    async def get_or_create_session(
        self, session_id: str, client: CodeerClient, agent_id: Optional[str] = None
    ) -> dict:
        """Get existing session or create new one

        Args:
            session_id: Session identifier
            client: CodeerClient instance
            agent_id: Optional agent ID to use for new chat sessions

        Returns:
            Chat session dictionary
        """
        async with self._lock:
            if session_id in self.sessions:
                data = self.sessions[session_id]
                age = datetime.now() - data["created_at"]

                # CRITICAL: Check if agent_id matches (prevent agent mismatch errors)
                stored_agent_id = data.get("agent_id")
                if stored_agent_id != agent_id:
                    logger.warning(
                        f"Session {session_id} agent mismatch: stored={stored_agent_id}, "
                        f"requested={agent_id}. Creating new session."
                    )
                    del self.sessions[session_id]
                elif age < timedelta(seconds=self.ttl_seconds):
                    logger.info(
                        f"Reusing Codeer session {session_id} with agent {agent_id}"
                    )
                    return data["chat"]
                else:
                    logger.info(f"Session {session_id} expired, creating new")
                    del self.sessions[session_id]

            logger.info(
                f"Creating new Codeer session {session_id} with agent {agent_id}"
            )
            chat = await client.create_chat(
                name=f"Session-{session_id}", agent_id=agent_id
            )

            self.sessions[session_id] = {
                "chat": chat,
                "agent_id": agent_id,  # Store agent_id to prevent mismatches
                "created_at": datetime.now(),
            }

            return chat

    def get_stats(self) -> dict:
        """Get session statistics"""
        return {
            "active_sessions": len(self.sessions),
            "ttl_seconds": self.ttl_seconds,
        }


_codeer_session_pool: Optional[CodeerSessionPool] = None


def get_codeer_session_pool() -> CodeerSessionPool:
    """Get global session pool singleton"""
    global _codeer_session_pool
    if _codeer_session_pool is None:
        _codeer_session_pool = CodeerSessionPool(ttl_seconds=7200)
    return _codeer_session_pool
