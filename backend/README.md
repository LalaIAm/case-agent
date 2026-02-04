# Backend – Minnesota Conciliation Court Case Agent

FastAPI backend for the Minnesota Conciliation Court Case Agent.

## API structure

- **`/`** – API info (name, version, docs URL)
- **`/health`** – Health check for load balancers
- **`/docs`** – Swagger UI (when running)

Planned routes (Phase 2+):

- `/api/auth` – Authentication (signup, login)
- `/api/cases` – Case management
- `/api/agents` – Agent orchestration
- `/api/memory` – Memory block operations

## Agent architecture

Agents live in `backend/agents/` and are orchestrated by the agent orchestrator (Phase 6):

| Agent           | Purpose                                                   |
|-----------------|-----------------------------------------------------------|
| Intake          | Extract facts, categorize dispute type                    |
| Research        | Minnesota rules, Tavily search, RAG for case law          |
| Document        | Process uploaded evidence (PDFs, images)                  |
| Strategy        | Develop case strategy, strengths/weaknesses               |
| Drafting        | Statement of Claim, hearing scripts, advice documents     |

## Database schema (Phase 2)

Tables will include: `users`, `cases`, `case_sessions`, `memory_blocks`, `documents`, `agent_runs`, `generated_documents`. See the main plan for schema details.

## Endpoint documentation

Full endpoint docs will be added as routes are implemented. Use `/docs` for interactive API exploration.
