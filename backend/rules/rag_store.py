"""
Vector store manager for rules (case law and precedents) with pgvector embeddings.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import Rule
from backend.memory.embeddings import EmbeddingService

from .static_rules import MINNESOTA_CONCILIATION_RULES, STATUTE_REFERENCES


class RuleVectorStore:
    """Manages rule CRUD and vector embeddings using EmbeddingService."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._embedding_service = EmbeddingService()

    async def add_rule(
        self,
        rule_type: str,
        source: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Rule:
        """Create a rule with generated embedding and persist."""
        embedding = await self._embedding_service.generate_embedding(content)
        rule = Rule(
            rule_type=rule_type,
            source=source,
            title=title,
            content=content,
            embedding=embedding,
            metadata_=metadata or {},
        )
        self._session.add(rule)
        await self._session.flush()
        await self._session.refresh(rule)
        return rule

    async def add_rules_batch(
        self, rules: List[Dict[str, Any]]
    ) -> List[Rule]:
        """Bulk insert rules with batch embedding generation."""
        if not rules:
            return []
        contents = []
        for r in rules:
            content = r.get("content") or (r.get("title") or "") + " " + (r.get("source") or "")
            contents.append(content)
        embeddings = await self._embedding_service.generate_embeddings(contents)
        created: List[Rule] = []
        for r, emb in zip(rules, embeddings):
            rule = Rule(
                rule_type=r.get("rule_type", "statute"),
                source=r.get("source", ""),
                title=r.get("title", ""),
                content=r.get("content", ""),
                embedding=emb,
                metadata_=r.get("metadata_") or r.get("metadata") or {},
            )
            self._session.add(rule)
            created.append(rule)
        await self._session.flush()
        for rule in created:
            await self._session.refresh(rule)
        return created

    async def get_rule(self, rule_id: UUID) -> Optional[Rule]:
        """Retrieve a single rule by ID."""
        result = await self._session.execute(select(Rule).where(Rule.id == rule_id))
        return result.scalar_one_or_none()

    async def update_rule(
        self,
        rule_id: UUID,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Rule]:
        """Update rule content and metadata, regenerate embedding."""
        rule = await self.get_rule(rule_id)
        if not rule:
            return None
        rule.content = content.strip()
        if metadata is not None:
            rule.metadata_ = metadata
        rule.embedding = await self._embedding_service.generate_embedding(rule.content)
        await self._session.flush()
        await self._session.refresh(rule)
        return rule

    async def delete_rule(self, rule_id: UUID) -> bool:
        """Remove a rule by ID."""
        rule = await self.get_rule(rule_id)
        if not rule:
            return False
        await self._session.delete(rule)
        await self._session.flush()
        return True

    async def initialize_static_rules(self) -> int:
        """
        Load Minnesota Conciliation Court static rules into the vector store
        if not already present. Returns count of rules added.
        """
        result = await self._session.execute(
            select(Rule).where(
                Rule.rule_type == "statute",
                Rule.source.like("MN Stat.%"),
            ).limit(1)
        )
        if result.scalar_one_or_none() is not None:
            return 0
        # Map static rule category to rule_type so /procedures and /jurisdiction return correct rules
        category_to_rule_type: Dict[str, str] = {
            "procedures": "procedure",
            "jurisdiction": "statute",
            "appeals": "statute",
            "judgments": "statute",
            "fees": "statute",
            "representation": "statute",
        }
        to_add: List[Dict[str, Any]] = []
        for category, rules in MINNESOTA_CONCILIATION_RULES.items():
            rule_type = category_to_rule_type.get(category, "statute")
            for r in rules:
                rule_id = r.get("id", "")
                source = STATUTE_REFERENCES.get(rule_id, "MN Stat. § 491A")
                to_add.append({
                    "rule_type": rule_type,
                    "source": source,
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                    "metadata_": dict(r.get("metadata_") or {}, category=category),
                })
        if not to_add:
            return 0
        await self.add_rules_batch(to_add)
        return len(to_add)
