# Minnesota Conciliation Court Case Agent

A multi-agent legal assistant web application with persistent memory to help Minnesotans prepare Conciliation Court cases end-to-end, featuring collaborative agent analysis, document generation, and iterative case refinement.

## Architecture Overview

The application uses a Python FastAPI backend with React frontend, OpenAI agents, PostgreSQL with embeddings for memory, and a hybrid rules system combining static Minnesota court rules with RAG for case law.

- **Backend**: FastAPI, SQLAlchemy, Alembic, OpenAI, Tavily Search (legal research, case law, precedents, statutes)
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Database**: PostgreSQL 15+ with pgvector for embeddings
- **Agents**: Intake, Research, Document Analysis, Strategy, Drafting (orchestrated workflow)

### Generated Court Documents

After the Drafting Agent runs, three document types are stored as text in the database: **Statement of Claim**, **Hearing Script**, and **Legal Advice**. You can generate PDFs on demand and download them via the documents API. The workflow is: agent drafting → store text in `GeneratedDocument` → call generate-pdf → download PDF. This keeps generation separate from the agent pipeline and supports regeneration and versioning without re-running the full workflow.

## Prerequisites

- **Python 3.11+**
- **Node 20.19+** (or **22.12+**)
- **PostgreSQL 15+**
- **npm** or **yarn**

Optional: use `.nvmrc` to align your local Node version with the frontend tooling.

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd case-agent
```

### 2. Environment configuration

Copy the example env file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your values. Key variables:

| Variable         | Description                         | Example                          |
|------------------|-------------------------------------|----------------------------------|
| DATABASE_URL     | PostgreSQL connection string        | postgresql://user:pass@localhost:5432/case_agent |
| OPENAI_API_KEY   | OpenAI API key for agents           | sk-...                           |
| TAVILY_API_KEY   | Tavily Search API key (required for research/tools) | tvly-...                         |
| SECRET_KEY       | JWT secret (min 32 chars)           | your-secret-key-32-chars-min     |
| FRONTEND_URL     | Frontend origin(s) for CORS         | http://localhost:5173            |
| ENVIRONMENT      | development / staging / production  | development                      |
| ENABLE_RATE_LIMITING | Enable API rate limiting        | true                             |
| LOG_LEVEL        | Logging level                       | INFO                             |
| SENTRY_DSN       | Optional Sentry DSN for errors      | (optional)                       |

### 3. Backend setup

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
```

### 4. Frontend setup

```bash
cd frontend
npm install
```

### 5. Database

Ensure PostgreSQL is running. Create a database and set `DATABASE_URL` in `.env`. Migrations (Alembic) will be applied in Phase 2.

## Running the application

### Backend

```bash
cd backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm run dev
```

App: http://localhost:5173

## Project structure

```
case-agent/
├── backend/
│   ├── agents/          # Intake, Research, Document, Strategy, Drafting agents
│   ├── auth/            # Authentication routes
│   ├── database/        # Models, migrations
│   │   └── migrations/  # Alembic migrations
│   ├── documents/       # Document generation (Statement of Claim, etc.)
│   ├── memory/          # Memory manager, embeddings, case blocks
│   ├── rules/           # Minnesota court rules, RAG store
│   ├── tools/           # Tavily search, etc.
│   ├── main.py          # FastAPI app entry
│   ├── config.py        # Settings
│   └── dependencies.py  # Dependency injection
├── frontend/
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   ├── pages/       # Route pages
│   │   ├── hooks/       # Custom React hooks
│   │   └── services/    # API client, WebSocket
│   └── public/
├── .env.example
├── .gitignore
└── README.md
```

## Tech stack

| Layer    | Technologies                                              |
|----------|-----------------------------------------------------------|
| Backend  | FastAPI, SQLAlchemy, Alembic, OpenAI, Tavily, FastAPI-Users |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, React Router     |
| Database | PostgreSQL 15+                                            |
| Tools    | axios, socket.io-client, react-dropzone                    |

## Generated Court Documents workflow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant DraftingAgent
    participant GeneratedDocument
    participant PDFGenerator
    participant FileSystem

    User->>API: POST /api/agents/execute (drafting)
    API->>DraftingAgent: Execute drafting agent
    DraftingAgent->>GeneratedDocument: Store text content (3 docs)
    DraftingAgent-->>API: Return document IDs
    API-->>User: Agent complete

    User->>API: POST /generated/{id}/generate-pdf
    API->>GeneratedDocument: Fetch document by ID
    GeneratedDocument-->>API: Return content + metadata
    API->>PDFGenerator: Generate PDF (statement_of_claim)
    PDFGenerator->>FileSystem: Write PDF file
    FileSystem-->>PDFGenerator: File path
    PDFGenerator-->>API: PDF path
    API->>GeneratedDocument: Update file_path
    API-->>User: Return document with PDF URL

    User->>API: GET /generated/{id}/download
    API->>GeneratedDocument: Verify ownership + file_path
    API->>FileSystem: Read PDF file
    FileSystem-->>API: PDF bytes
    API-->>User: Download PDF
```

### Example API calls for document generation

- Generate PDF for a generated document (after drafting):  
  `POST /api/documents/generated/{document_id}/generate-pdf`  
  Returns the document with `file_path` and `generation_time_ms`.

- Download the PDF:  
  `GET /api/documents/generated/{document_id}/download`  
  Returns the file as an attachment.

- List generated documents for a case:  
  `GET /api/documents/cases/{case_id}/generated`  
  Returns list with `has_pdf` and `download_url` for each.

All require authentication; the user must own the case.

## Error handling and rate limiting

- **Error format**: All API errors return JSON `{ "error": { "type", "message", "details", "request_id" } }`. See [docs/ERROR_HANDLING.md](docs/ERROR_HANDLING.md).
- **Rate limiting**: When `ENABLE_RATE_LIMITING` is true, endpoints are limited per client (e.g. 100/min). Health and root are exempt. 429 responses include `Retry-After`.
- **Agents**: Agent runs use a timeout (`AGENT_TIMEOUT_SECONDS`) and retries with exponential backoff on retryable failures.

## Accessibility

- Forms use labels, ARIA, and inline validation errors. See [docs/ACCESSIBILITY.md](docs/ACCESSIBILITY.md).
- Keyboard navigation is supported for lists and main actions; toasts and errors are announced to screen readers.

## Troubleshooting

- **401 on API calls**: Ensure you are logged in and the token is sent (`Authorization: Bearer <token>`). Check `frontend/vite.config.ts` proxy and `VITE_API_URL` if calling from a different origin.
- **429 Too Many Requests**: Wait for the time indicated in `Retry-After` or reduce request frequency.
- **Agent timeout**: Increase `AGENT_TIMEOUT_SECONDS` in backend config for long-running workflows.
- **WebSocket disconnect**: The client reconnects with backoff. Use the “Reconnect” control in the Agent Status tab if the connection fails.

## Development notes

- Backend API is prefixed at `/api` when proxied from Vite (see `frontend/vite.config.ts`).
- Health check: `GET /health` returns `{"status": "healthy"}`.
- Authentication and case routes are in use; use `current_active_user` for protected routes.

## License

MIT (or specify your license)
