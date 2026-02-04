# Minnesota Conciliation Court Case Agent

A multi-agent legal assistant web application with persistent memory to help Minnesotans prepare Conciliation Court cases end-to-end, featuring collaborative agent analysis, document generation, and iterative case refinement.

## Architecture Overview

The application uses a Python FastAPI backend with React frontend, OpenAI agents, PostgreSQL with embeddings for memory, and a hybrid rules system combining static Minnesota court rules with RAG for case law.

- **Backend**: FastAPI, SQLAlchemy, Alembic, OpenAI, Tavily Search
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Database**: PostgreSQL 15+ with pgvector for embeddings
- **Agents**: Intake, Research, Document Analysis, Strategy, Drafting (orchestrated workflow)

## Prerequisites

- **Python 3.11+**
- **Node 18+**
- **PostgreSQL 15+**
- **npm** or **yarn**

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
| TAVILY_API_KEY   | Tavily Search API key               | tvly-...                         |
| SECRET_KEY       | JWT secret (min 32 chars)           | your-secret-key-32-chars-min     |
| FRONTEND_URL     | Frontend origin(s) for CORS         | http://localhost:5173            |
| ENVIRONMENT      | development / staging / production  | development                      |

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

## Development notes

- Backend API is prefixed at `/api` when proxied from Vite (see `frontend/vite.config.ts`).
- Health check: `GET /health` returns `{"status": "healthy"}`.
- Authentication and case routes are planned for Phase 2+.

## License

MIT (or specify your license)
