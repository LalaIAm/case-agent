"""
Standalone script to populate the rules vector store with static Minnesota rules.
Run from project root: python -m backend.rules.init_rules
"""
import asyncio

from backend.database.engine import AsyncSessionLocal
from backend.rules.rag_store import RuleVectorStore


async def initialize_rules() -> None:
    """Create async session, run initialize_static_rules, commit."""
    async with AsyncSessionLocal() as session:
        store = RuleVectorStore(session)
        count = await store.initialize_static_rules()
        await session.commit()
        print(f"Initialized {count} static rules.")


if __name__ == "__main__":
    asyncio.run(initialize_rules())
