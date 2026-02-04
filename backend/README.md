# Backend – Minnesota Conciliation Court Case Agent

FastAPI backend for the Minnesota Conciliation Court Case Agent.

## API structure

- **`/`** – API info (name, version, docs URL)
- **`/health`** – Health check for load balancers
- **`/docs`** – Swagger UI (when running)

## Authentication

JWT-based authentication is provided by FastAPI-Users. Use the `Authorization: Bearer <token>` header for protected routes.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create new user account |
| POST | `/api/auth/login` | Login and receive JWT token |
| POST | `/api/auth/logout` | Logout (invalidate token client-side) |
| GET | `/api/auth/me` | Get current user profile |
| PATCH | `/api/auth/me` | Update user profile |

**Example: Register**

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'
```

**Example: Login**

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=password123"
```

**Example: Get current user (with token)**

```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <your_jwt_token>"
```

Planned routes (Phase 2+):

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
