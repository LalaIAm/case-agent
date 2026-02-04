# Frontend – Minnesota Conciliation Court Case Agent

React + TypeScript + Vite frontend for the Minnesota Conciliation Court Case Agent.

## Component structure

- **`src/components/`** – Reusable UI components (e.g. `AgentStatus`, `AdvisorTab`)
- **`src/pages/`** – Route pages (Intake, CaseDashboard, etc.)
- **`src/hooks/`** – Custom hooks (`useCase`, `useAgents`, `useMemory`)
- **`src/services/`** – API client, WebSocket client

## Routing (Phase 11)

React Router will be configured in `App.tsx` with routes for intake, case dashboard, document viewer, and advisor. Auth wrapper will protect authenticated routes.

## State management

State is managed via React hooks and context. Planned: case state, agent progress, user session. No global store (Redux/Zustand) in initial setup.

## Tailwind conventions

- Content paths: `./index.html`, `./src/**/*.{js,ts,jsx,tsx}`
- Theme: legal/professional blues and grays (see `tailwind.config.js`)
- Utilities: `@tailwind base/components/utilities` in `index.css`
