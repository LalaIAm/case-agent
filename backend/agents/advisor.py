"""
Conversational advisor: context-aware chat using memory and OpenAI streaming.
"""
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database.models import ConversationMessage
from backend.memory.memory_manager import MemoryManager
from backend.memory.utils import format_memory_context

ADVISOR_SYSTEM_PROMPT = """You are a legal advisor for Minnesota Conciliation Court cases. Provide clear, actionable advice based on the case context. Ask clarifying questions when needed. Suggest next steps and identify gaps in the case."""

CONTEXT_MAX_CHARS = 28000  # ~8k tokens at ~3.5 chars/token


class ConversationalAdvisor:
    """Provides context-aware conversational advice using case memory and OpenAI."""

    def __init__(self, db: AsyncSession, case_id: UUID, user_id: UUID) -> None:
        self._db = db
        self._case_id = case_id
        self._user_id = user_id

    def _get_openai_client(self) -> AsyncOpenAI:
        settings = get_settings()
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    def _get_memory_manager(self) -> MemoryManager:
        return MemoryManager(self._db)

    async def get_suggested_questions(self, limit: int = 5) -> List[str]:
        """Return content of memory blocks of type 'question' for this case."""
        blocks = await self._get_memory_manager().get_case_context(
            self._case_id, block_types=["question"], limit=limit
        )
        return [b.content.strip() for b in blocks if b.content and b.content.strip()]

    async def get_conversation_history(self, limit: int = 20) -> List[ConversationMessage]:
        """Retrieve recent messages for context, oldest-first for chat order."""
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.case_id == self._case_id)
            .order_by(ConversationMessage.created_at.asc())
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().unique().all())

    async def build_context(self, query: Optional[str] = None) -> tuple[str, List[str]]:
        """
        Build context string from memory. If query is provided, use semantic search;
        otherwise use get_case_context. Returns (context_string, list of block types used).
        Truncates to stay within token limits.
        """
        manager = self._get_memory_manager()
        if query and query.strip():
            blocks_with_scores = await manager.search_similar_blocks(
                query=query.strip(),
                case_id=self._case_id,
                limit=30,
            )
            blocks = [b for b, _ in blocks_with_scores]
        else:
            blocks = await manager.get_case_context(
                self._case_id,
                block_types=None,
                limit=50,
            )
        if not blocks:
            return "", []
        types_used = list({b.block_type for b in blocks})
        context = format_memory_context(blocks)
        if len(context) > CONTEXT_MAX_CHARS:
            context = context[:CONTEXT_MAX_CHARS] + "\n\n[Context truncated.]"
        return context, types_used

    async def generate_response_stream(
        self, user_message: str, include_context: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Create user message record, build context, call OpenAI streaming, yield chunks,
        then save assistant message.
        """
        user_msg = ConversationMessage(
            case_id=self._case_id,
            role="user",
            content=user_message.strip(),
        )
        self._db.add(user_msg)
        await self._db.flush()
        await self._db.refresh(user_msg)

        context_str = ""
        context_used: List[str] = []
        if include_context:
            context_str, context_used = await self.build_context(user_message.strip())
        conversation = await self.get_conversation_history(limit=20)
        messages: List[Dict[str, str]] = []
        if context_str:
            messages.append(
                {
                    "role": "system",
                    "content": ADVISOR_SYSTEM_PROMPT
                    + "\n\n## Case context (use this to inform your advice)\n\n"
                    + context_str,
                }
            )
        else:
            messages.append({"role": "system", "content": ADVISOR_SYSTEM_PROMPT})
        for msg in conversation:
            messages.append({"role": msg.role, "content": msg.content})

        settings = get_settings()
        client = self._get_openai_client()
        full_content: List[str] = []
        stream = await client.chat.completions.create(
            model=getattr(settings, "AGENT_MODEL", "gpt-4-turbo-preview"),
            messages=messages,
            stream=True,
            temperature=getattr(settings, "AGENT_TEMPERATURE", 0.7),
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                piece = chunk.choices[0].delta.content
                full_content.append(piece)
                yield piece

        response_text = "".join(full_content)
        assistant_msg = ConversationMessage(
            case_id=self._case_id,
            role="assistant",
            content=response_text,
            metadata_={"context_used": context_used} if context_used else None,
        )
        self._db.add(assistant_msg)
        await self._db.flush()
        await self._db.commit()

    async def trigger_reanalysis(
        self, agent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Return status payload for re-analysis. The router should schedule
        execute_workflow_background or execute_agent_background and then return this.
        """
        if agent_name:
            return {"status": "accepted", "agent_name": agent_name, "message": "Agent started"}
        return {"status": "accepted", "message": "Workflow started"}
