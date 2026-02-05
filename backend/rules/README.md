# Rules System

Three-layer architecture for Minnesota Conciliation Court rules and case law:

1. **Static rules** – Minnesota Conciliation Court rules from MN Statutes Chapter 491A, embedded in code for exact lookup and keyword search.
2. **RAG vector store** – Rules (statutes, procedure, case law, interpretation) stored in PostgreSQL with pgvector embeddings for semantic search.
3. **Hybrid retrieval** – Combines static keyword matching with vector similarity search for comprehensive coverage.

## Minnesota Conciliation Court Coverage

Static rules cover:

- **Jurisdiction**: Monetary limits ($20,000 general, $4,000 consumer credit), excluded actions (real estate, defamation, class actions, injunctions, evictions, medical malpractice).
- **Procedures**: Filing, service of process, informal hearings, no jury, court administrator assistance.
- **Appeals**: Right to appeal, trial de novo, deadlines.
- **Judgments**: Payment plans (max 1 year), enforcement, interest.
- **Fees**: Filing fees, fee waiver, service fees.
- **Representation**: Self-representation, corporate representation, optional attorney.

## API Endpoints

All endpoints require authentication (`current_active_user`).

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/rules/search` | Semantic search over rules. Body: `RuleSearch` (query, rule_types?, limit?, min_similarity?). Returns `{ "results": [{ "rule": RuleRead, "similarity": float }] }`. |
| GET | `/api/rules/jurisdiction` | List jurisdiction-related rules. Returns `List[RuleRead]`. |
| GET | `/api/rules/procedures` | List procedure rules. Query: `procedure_type` (optional). Returns `List[RuleRead]`. |
| POST | `/api/rules/hybrid-search` | Static + case law search. Body: `RuleSearch` + `include_static`, `include_case_law`. Returns `{ "static_rules": [...], "case_law": [...] }`. |
| GET | `/api/rules/{rule_id}` | Get one rule by ID. Returns `RuleRead` or 404. |
| POST | `/api/rules` | Create a rule (admin/future). Body: `RuleCreate`. Returns `RuleRead` (201). |

### Example: Search

```bash
curl -X POST http://localhost:8000/api/rules/search \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "monetary limit jurisdiction", "limit": 5}'
```

### Example: Hybrid search

```bash
curl -X POST http://localhost:8000/api/rules/hybrid-search \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "filing fee", "include_static": true, "include_case_law": false, "limit": 10}'
```

## Adding Rules to the Vector Store

1. Use the init script to load static Minnesota rules (one-time):

   ```bash
   python -m backend.rules.init_rules
   ```

2. To add custom case law or interpretations, call `RuleVectorStore.add_rule()` (or `add_rules_batch()`) with `rule_type` one of: `statute`, `procedure`, `case_law`, `interpretation`. The store generates embeddings via the shared `EmbeddingService` (OpenAI text-embedding-3-small).

## Hybrid Search Strategy

- **Static**: Keyword search over `MINNESOTA_CONCILIATION_RULES` (title, content, id). No embedding call.
- **Case law**: Semantic search over the `rules` table filtered by `rule_type` in (`case_law`, `interpretation`), ordered by cosine similarity.
- Results are returned under `static_rules` and `case_law`; the API does not deduplicate across the two.

## Embedding Model and Similarity

- Model: **text-embedding-3-small** (1536 dimensions), same as memory and documents.
- Similarity: Cosine; stored and queried as `1 - (embedding <=> query_vector)`. Default minimum similarity for search is configurable via `RULES_SIMILARITY_THRESHOLD` (default 0.7).

## Optional environment variables

Add to `.env` if you want to override defaults:

- `RULES_SIMILARITY_THRESHOLD` (float, default `0.7`) – minimum similarity for rule matching.
- `RULES_MAX_RESULTS` (int, default `10`) – default limit for rule search results.
