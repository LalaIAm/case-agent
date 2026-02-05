"""
Hybrid rule retrieval: static rules + semantic search over rule vector store.
"""
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import Rule
from backend.database.schemas import RuleRead
from backend.memory.embeddings import EmbeddingService

from .rag_store import RuleVectorStore
from .static_rules import search_static_rules


class RuleRetriever:
    """Combines static rule lookup and semantic search over stored rules."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._store = RuleVectorStore(session)
        self._embedding_service = EmbeddingService()

    async def search_rules(
        self,
        query: str,
        rule_types: Optional[List[str]] = None,
        limit: int = 10,
        min_similarity: Optional[float] = 0.7,
    ) -> List[Tuple[Rule, float]]:
        """
        Semantic search using pgvector cosine similarity.
        Returns (Rule, similarity_score) tuples ordered by similarity descending.
        """
        query_embedding = await self._embedding_service.generate_embedding(query)
        qv = str(query_embedding)
        params: Dict[str, Any] = {"qv": qv, "limit": limit}
        sql = """
            SELECT id, rule_type, source, title, content, embedding, metadata_, created_at, updated_at,
                   (1 - (embedding <=> CAST(:qv AS vector))) AS similarity
            FROM public.rules
            WHERE embedding IS NOT NULL
        """
        if rule_types:
            sql += " AND rule_type = ANY(:rule_types)"
            params["rule_types"] = rule_types
        if min_similarity is not None:
            sql += " AND (1 - (embedding <=> CAST(:qv AS vector))) >= :min_sim"
            params["min_sim"] = min_similarity
        sql += " ORDER BY embedding <=> CAST(:qv AS vector) ASC LIMIT :limit"

        result = await self._session.execute(text(sql), params)
        rows = result.mappings().all()
        out: List[Tuple[Rule, float]] = []
        for row in rows:
            rule = await self._store.get_rule(row["id"])
            if rule:
                out.append((rule, float(row["similarity"])))
        return out

    async def get_relevant_rules(
        self,
        query: str,
        rule_types: Optional[List[str]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Return formatted rule data with similarity scores for agent consumption."""
        pairs = await self.search_rules(
            query=query,
            rule_types=rule_types,
            limit=limit,
        )
        return [
            {
                "rule_type": r.rule_type,
                "source": r.source,
                "title": r.title,
                "content": r.content,
                "metadata_": r.metadata_,
                "similarity": score,
            }
            for r, score in pairs
        ]

    async def get_jurisdiction_rules(self) -> List[Rule]:
        """Return rules with rule_type statute and jurisdiction-related metadata."""
        stmt = (
            select(Rule)
            .where(Rule.rule_type == "statute")
            .where(
                Rule.metadata_.astext.isnot(None),
            )
        )
        result = await self._session.execute(stmt)
        rules = list(result.scalars().unique().all())
        jurisdiction = []
        for r in rules:
            meta = r.metadata_ or {}
            if isinstance(meta, dict):
                cat = meta.get("category")
                if cat == "jurisdiction":
                    jurisdiction.append(r)
        return jurisdiction

    async def get_procedure_rules(
        self, procedure_type: Optional[str] = None
    ) -> List[Rule]:
        """Return procedure rules, optionally filtered by procedure_type in metadata."""
        stmt = select(Rule).where(Rule.rule_type == "procedure")
        result = await self._session.execute(stmt)
        rules = list(result.scalars().unique().all())
        if not procedure_type:
            return rules
        filtered = []
        for r in rules:
            meta = r.metadata_ or {}
            if isinstance(meta, dict):
                pt = meta.get("procedure_type")
                if pt == procedure_type:
                    filtered.append(r)
        return filtered

    async def hybrid_search(
        self,
        query: str,
        include_static: bool = True,
        include_case_law: bool = True,
        limit: int = 10,
    ) -> Dict[str, List[Any]]:
        """
        Combine keyword search over static rules and semantic search over vector store.
        Returns {"static_rules": [...], "case_law": [...]}.
        """
        static_rules: List[Any] = []
        case_law: List[Any] = []
        if include_static:
            static_rules = search_static_rules(query)
            if limit:
                static_rules = static_rules[:limit]
        if include_case_law:
            pairs = await self.search_rules(
                query=query,
                rule_types=["case_law", "interpretation"],
                limit=limit,
                min_similarity=None,
            )
            case_law = [
                {"rule": RuleRead.model_validate(r).model_dump(), "similarity": score}
                for r, score in pairs
            ]
        return {"static_rules": static_rules, "case_law": case_law}
