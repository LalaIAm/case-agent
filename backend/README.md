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

## Session lifecycle and endpoints

Sessions organize work per case. Lifecycle: **create** → **active** → **completed**.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cases/{case_id}/sessions` | List all sessions for a case |
| POST | `/api/cases/{case_id}/sessions` | Create a new session (auto-increment number, status=active) |
| GET | `/api/cases/{case_id}/sessions/{session_id}` | Get a specific session (validates case ownership) |
| PUT | `/api/cases/{case_id}/sessions/{session_id}` | Update session (e.g. status, completed_at) |
| GET | `/api/cases/{case_id}/sessions/{session_id}/summary` | Session metadata + memory block counts by type |
| GET | `/api/cases/{case_id}/active-session` | Get current active session (404 if none) |
| GET | `/api/memory/sessions/{session_id}/context` | Memory blocks for a session (optional `block_types` filter) |

**Session context scoping:** Use `GET /api/memory/sessions/{session_id}/context` to retrieve memory blocks for a single session. Use `GET /api/memory/cases/{case_id}/context` for case-wide (all sessions) context. The Case Advisor can be given an optional `session_id` when sending a message to scope advice to that session’s context.

**Example: switch session and get summary**

```bash
# Get active session
curl -s -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/cases/<case_id>/active-session"

# Get session summary (block counts)
curl -s -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/cases/<case_id>/sessions/<session_id>/summary"

# Mark session completed
curl -s -X PUT -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  "http://localhost:8000/api/cases/<case_id>/sessions/<session_id>" \
  -d '{"status":"completed","completed_at":"2025-02-05T12:00:00Z"}'
```

## Endpoint documentation

Full endpoint docs will be added as routes are implemented. Use `/docs` for interactive API exploration.
