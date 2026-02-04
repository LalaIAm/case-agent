---
name: Foundation Setup Implementation
overview: "Implement the complete foundational setup for the Minnesota Conciliation Court Case Agent: backend (FastAPI, config, dependencies, directory structure), frontend (Vite + React + TypeScript + Tailwind), environment templates, dependency files, Git/config, and documentation—exactly as specified in the plan."
todos: []
---

# Foundation Setup Implementation Plan

Execute the following in order. All paths and content are from the existing plan; no re-verification.

---

## 1. Backend directory and core files

**Create directory structure under `backend/`:**

- `backend/` with subdirs: `agents/`, `auth/`, `database/`, `database/migrations/`, `memory/`, `rules/`, `tools/`, `documents/`
- Add `__init__.py` in `backend/` and in each subdirectory listed above

**Create [backend/main.py](backend/main.py):**

- FastAPI app with title `"Minnesota Conciliation Court Case Agent"`
- CORS middleware using origins from env
- `/health` → `{"status": "healthy"}`
- `/` → API info
- Placeholder comment blocks for future route imports (auth, cases, agents, memory)

**Create [backend/config.py](backend/config.py):**

- Pydantic `BaseSettings` class `Settings` with: `DATABASE_URL`, `OPENAI_API_KEY`, `TAVILY_API_KEY`, `SECRET_KEY`, `FRONTEND_URL`, `ENVIRONMENT` (default `"development"`)
- `@lru_cache` on a getter; `get_settings()` returning cached instance
- Validation for required fields

**Create [backend/dependencies.py](backend/dependencies.py):**

- Import `get_settings` from config
- Placeholder DB session dependency (Phase 2)
- Placeholder current-user dependency (Phase 3)
- Docstrings for each dependency

---

## 2. Frontend directory and core files

**Create directory structure under `frontend/`:**

- `frontend/public/`, `frontend/src/`, `frontend/src/components/`, `frontend/src/pages/`, `frontend/src/hooks/`, `frontend/src/services/`
- Add `.gitkeep` in `components/`, `pages/`, `hooks/`, `services/`

**Create frontend config and entry files:**

- [frontend/index.html](frontend/index.html) – standard Vite entry HTML with root div
- [frontend/vite.config.ts](frontend/vite.config.ts) – `defineConfig`, React plugin, port 5173, proxy `/api` → `http://localhost:8000`, HMR
- [frontend/tsconfig.json](frontend/tsconfig.json) – target ES2020, module ESNext, `jsx: "react-jsx"`, `strict: true`, path alias `"@/*": ["./src/*"]`
- [frontend/tsconfig.node.json](frontend/tsconfig.node.json) – for Vite config
- [frontend/src/main.tsx](frontend/src/main.tsx) – ReactDOM render of App in StrictMode + index.css
- [frontend/src/App.tsx](frontend/src/App.tsx) – functional component, heading "Minnesota Conciliation Court Case Agent", placeholder comments for router/auth, Tailwind classes
- [frontend/src/index.css](frontend/src/index.css) – `@tailwind base/components/utilities`, basic reset/typography
- [frontend/src/vite-env.d.ts](frontend/src/vite-env.d.ts) – Vite client types reference
- [frontend/tailwind.config.js](frontend/tailwind.config.js) – content `["./index.html", "./src/**/*.{js,ts,jsx,tsx}"]`, theme extension (legal/professional blues, grays)
- [frontend/postcss.config.js](frontend/postcss.config.js) – tailwindcss + autoprefixer plugins
- [frontend/.eslintrc.cjs](frontend/.eslintrc.cjs) – extend React + TypeScript recommended, parser options, hooks and unused-vars rules

---

## 3. Environment configuration

- **[.env.example](.env.example)** (root): DATABASE_URL, OPENAI_API_KEY, TAVILY_API_KEY, SECRET_KEY, FRONTEND_URL, ENVIRONMENT (as in plan)
- **[backend/.env.example](backend/.env.example)**: same as root
- **[frontend/.env.example](frontend/.env.example)**: `VITE_API_URL=http://localhost:8000`

---

## 4. Python dependencies

- **[backend/requirements.txt](backend/requirements.txt)** – exact versions from plan (FastAPI, uvicorn, sqlalchemy, alembic, psycopg2-binary, asyncpg, openai, tavily-python, fastapi-users, python-jose, passlib, websockets, pypdf2, pdfplumber, pillow, reportlab, python-dotenv, pydantic, pydantic-settings)
- **[backend/pyproject.toml](backend/pyproject.toml)** – project name "case-agent-backend", version 0.1.0, same deps in `dependencies`, build-system setuptools, `[tool.pytest.ini_options]`, `[tool.black]`, `[tool.ruff]`

---

## 5. Frontend dependencies

- **[frontend/package.json](frontend/package.json)** – name "case-agent-frontend", version 0.1.0, scripts (dev, build, preview, lint), dependencies and devDependencies exactly as in plan (react, react-dom, react-router-dom, axios, socket.io-client, react-dropzone; types, eslint, vite, tailwind, etc.)

---

## 6. Git and ignore files

- **[.gitignore](.gitignore)** (root) – env files, Python artifacts, node_modules, dist, IDEs, DB files, logs, build (full list from plan)
- **[backend/.gitignore](backend/.gitignore) **– **pycache**, *.pyc, .env, venv, alembic.ini
- **[frontend/.gitignore](frontend/.gitignore)** – node_modules, dist, .env, .env.local

---

## 7. Documentation

- **[README.md](README.md)** – Project title, overview, architecture ref, prerequisites (Python 3.11+, Node 18+, PostgreSQL 15+), setup (clone, env, backend/frontend install, DB), running (uvicorn, npm run dev), env table, project structure tree, tech stack, development notes, license
- **[backend/README.md](backend/README.md)** – API structure, agent architecture ref, DB schema ref (Phase 2), endpoint docs (future)
- **[frontend/README.md](frontend/README.md)** – Component structure, routing (Phase 11), state management, Tailwind conventions

---

## 8. Verification (after all files exist)

- Confirm all backend `__init__.py` and directory layout
- In frontend: `npm install` (no errors)
- Confirm env templates and dependency versions
- Backend: `python -c "from backend.main import app"` or equivalent from `backend/` so FastAPI app imports
- Frontend: run `npm run dev` and confirm Vite starts

---

## File count summary

| Area | New files |
|------|-----------|
| Backend | 14 (main, config, dependencies, 8× **init**.py, requirements.txt, pyproject.toml, README, .gitignore, .env.example) |
| Frontend | 18 (index.html, package.json, tsconfig×2, vite.config, tailwind, postcss, eslintrc, main.tsx, App, index.css, vite-env.d.ts, 4× .gitkeep, README, .gitignore, .env.example) |
| Root | 3 (.env.example, .gitignore, README.md) |

Total: 35+ files. Execute in the order above; use the exact content from the user’s plan for every file.