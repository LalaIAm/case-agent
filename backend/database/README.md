# Database Layer

Async database layer for the Minnesota Conciliation Court Case Agent using SQLAlchemy 2.0, PostgreSQL, and pgvector for embeddings.

## Schema Overview

```mermaid
erDiagram
    User ||--o{ Case : owns
    Case ||--o{ CaseSession : has
    Case ||--o{ Document : contains
    Case ||--o{ AgentRun : tracks
    Case ||--o{ GeneratedDocument : produces
    CaseSession ||--o{ MemoryBlock : stores

    User {
        uuid id PK
        string email UK
        string hashed_password
        boolean is_active
        boolean is_verified
        timestamp created_at
    }

    Case {
        uuid id PK
        uuid user_id FK
        string title
        text description
        string status
        timestamp created_at
        timestamp updated_at
    }

    CaseSession {
        uuid id PK
        uuid case_id FK
        int session_number
        timestamp started_at
        timestamp completed_at
        string status
    }

    MemoryBlock {
        uuid id PK
        uuid session_id FK
        string block_type
        text content
        vector embedding
        json metadata_
        timestamp created_at
    }

    Document {
        uuid id PK
        uuid case_id FK
        string filename
        string file_path
        string file_type
        int file_size
        text extracted_text
        vector embedding
        timestamp uploaded_at
        boolean processed
    }

    AgentRun {
        uuid id PK
        uuid case_id FK
        string agent_name
        string status
        text reasoning
        json result
        timestamp started_at
        timestamp completed_at
        text error_message
    }

    GeneratedDocument {
        uuid id PK
        uuid case_id FK
        string document_type
        text content
        string file_path
        int version
        timestamp generated_at
    }
```

## Models

- **User**: Authenticated users; owns cases.
- **Case**: A conciliation court case; has sessions, documents, agent runs, and generated documents.
- **CaseSession**: A conversation/session within a case; stores memory blocks.
- **MemoryBlock**: Facts, evidence, strategy, rules, or questions with optional 1536-dim embeddings for semantic search.
- **Document**: Uploaded files (PDF, images, etc.) with optional extracted text and embeddings.
- **AgentRun**: Tracks agent executions (intake, research, document, strategy, drafting) and their results.
- **GeneratedDocument**: Generated outputs (statement of claim, hearing script, advice) with versioning.

Relationships use cascade deletes where appropriate (e.g., deleting a Case removes its sessions, documents, agent runs, and generated documents).

## pgvector Setup

PostgreSQL must have the [pgvector](https://github.com/pgvector/pgvector) extension installed.

- **Local**: Install pgvector for your OS (e.g., `apt install postgresql-16-pgvector` on Debian/Ubuntu).
- **Docker**: Use an image that includes pgvector (e.g., `ankane/pgvector`).
- The extension is enabled automatically in migrations via `CREATE EXTENSION IF NOT EXISTS vector`.

## Migration Commands

Run all commands from the **backend** directory (where `alembic.ini` lives).

```bash
# Create a new migration (after changing models)
alembic revision --autogenerate -m "description"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current revision
alembic current
```

## Environment

Set `DATABASE_URL` in `.env` (see `backend/.env.example`). Use the standard PostgreSQL URL; the app uses `postgresql+asyncpg://` for async connections. Example:

```
DATABASE_URL=postgresql://user:password@localhost:5432/case_agent
```

## Running Migrations in Different Environments

- **Development**: From `backend/`, run `alembic upgrade head` after pulling or changing models.
- **CI/CD**: Run the same command as part of your deploy or release pipeline.
- **Offline**: Use `alembic upgrade head --sql` to generate SQL and apply it manually if needed.
