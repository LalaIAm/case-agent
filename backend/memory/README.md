# Memory Layer

Persistent, searchable memory for the Minnesota Conciliation Court Case Agent. Memory blocks are stored per case session, embedded with OpenAI's `text-embedding-3-small` (1536 dimensions), and queried via pgvector cosine similarity.

## Architecture and Design

- **EmbeddingService** (`embeddings.py`): Generates 1536-dimensional vectors using OpenAI; supports single and batch calls with retries and text preprocessing.
- **MemoryManager** (`memory_manager.py`): CRUD for memory blocks, semantic search (cosine similarity), multi-session context, and block relationships via metadata.
- **Structured block types** (`case_blocks.py`): Typed Pydantic models for facts, evidence, strategy, rules, and questions; used to build metadata and validate content.
- **REST API** (`router.py`): Authenticated endpoints for creating, reading, updating, deleting blocks, semantic search, and case context.

All memory is scoped by **case session**; ownership is enforced via session → case → user.

## Block Types

| Type      | Purpose                    | Extra fields (in metadata / schemas) |
|-----------|----------------------------|--------------------------------------|
| **fact**  | Claims, counterclaims, timeline | `fact_type`, `date_occurred`, `parties_involved` |
| **evidence** | Documents, witnesses, physical | `evidence_type`, `document_id`, `relevance_score` |
| **strategy** | Legal/negotiation/procedural | `strategy_type`, `priority`, `dependencies` |
| **rule**  | Statutes, case law, court rules | `rule_source`, `citation`, `jurisdiction`, `applicability_score` |
| **question** | Open or answered questions | `question_type`, `answered`, `answer_content` |

Use `create_block_metadata(block_type, **kwargs)` to build the metadata dict for storage.

## API Endpoints

All routes are under `/api/memory` and require authentication.

| Method | Path | Description |
|--------|------|-------------|
| POST   | `/blocks` | Create block (`session_id`, `block_type`, `content`, `metadata_`) → 201 |
| GET    | `/blocks/{block_id}` | Get one block → 200, 404, 403 |
| GET    | `/sessions/{session_id}/blocks` | List blocks for session; optional `block_types` query |
| PUT    | `/blocks/{block_id}` | Update `content` and optional `metadata` (JSON body) |
| DELETE | `/blocks/{block_id}` | Delete block → 204, 404, 403 |
| POST   | `/search` | Semantic search; body: `query`, optional `block_types`, `limit`; query params: optional `session_id`, `case_id` |
| GET    | `/cases/{case_id}/context` | Multi-session context; query params: `block_types`, `limit` |

### Request/Response Examples

**Create block**

```json
POST /api/memory/blocks
{
  "session_id": "uuid",
  "block_type": "fact",
  "content": "Landlord failed to return security deposit within 21 days.",
  "metadata_": { "fact_type": "claim", "source": "user" }
}
→ 201 { "id", "session_id", "block_type", "content", "metadata_", "created_at" }
```

**Semantic search**

```json
POST /api/memory/search?case_id=uuid
{ "query": "security deposit deadline", "block_types": ["fact", "rule"], "limit": 10 }
→ 200 { "results": [ { "block": { ... }, "similarity": 0.89 }, ... ] }
```

## Semantic Search

- Query text is embedded with the same model as stored blocks; results are ranked by **cosine similarity** (1 − cosine distance).
- You can scope by `session_id` (single session) or `case_id` (all sessions for that case).
- Optional `min_similarity_threshold` in the manager can filter low-similarity hits; typical values are in the 0.5–0.8 range depending on use case.

## Multi-Session Context

`GET /cases/{case_id}/context` returns blocks from **all sessions** for the case, ordered by creation date (newest first). Use query params `block_types` and `limit` to narrow and cap results. Useful for agents that need full case history.

## Performance

- **Embedding latency**: Each block create/update and each search query call the OpenAI API; batch creation uses `generate_embeddings` where possible.
- **Vector search**: IVFFlat index on `embedding` with cosine ops; for very large tables, consider tuning `lists` or reindexing.

## Future Enhancements

- Hierarchical memory (summaries over time).
- Memory summarization to compress long sessions.
- Temporal decay or recency weighting for relevance.
