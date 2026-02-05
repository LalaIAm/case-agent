# Frontend – Minnesota Conciliation Court Case Agent

React + TypeScript + Vite frontend for the Minnesota Conciliation Court Case Agent.

## Prerequisites

- Node 20.19+ (or 22.12+)

## Component structure

- **`src/components/`** – Reusable UI components (e.g. `AgentStatus`, `AdvisorTab`, `SessionSelector`, `SessionHistory`, `SessionContextIndicator`, `SessionMetadata`)
- **`src/pages/`** – Route pages (Intake, CaseDashboard, CaseDetail, etc.)
- **`src/hooks/`** – Custom hooks (`useCase`, `useAgents`, `useMemory`)
- **`src/services/`** – API client, WebSocket client
- **`src/utils/sessionStorage.ts`** – Persist active session per case in localStorage

## Session management UI

- **SessionSelector** – Dropdown to switch session, “All Sessions” option, “Mark as Completed” for the active session.
- **SessionHistory** – Timeline of sessions in the Overview tab; expand for block counts, “View Context” to switch.
- **SessionContextIndicator** – Sticky banner showing current session (e.g. “Viewing Session 3 of 5”) and quick actions.
- **SessionMetadata** – Card with session details, block breakdown, and actions (Complete, View Memory Blocks, Export).

**User guide:** From the case detail page you can create a session (New Session), switch context (SessionSelector or Session History → View Context), and complete a session (Mark as Completed). The Case Advisor tab uses the selected session’s context when “Session-only context” is checked; otherwise it uses case-wide context. Session selection is persisted per case in localStorage.

## Routing (Phase 11)

React Router will be configured in `App.tsx` with routes for intake, case dashboard, document viewer, and advisor. Auth wrapper will protect authenticated routes.

## State management

State is managed via React hooks and context. Planned: case state, agent progress, user session. No global store (Redux/Zustand) in initial setup.

## Tailwind conventions

- Content paths: `./index.html`, `./src/**/*.{js,ts,jsx,tsx}`
- Theme: legal/professional blues and grays (see `tailwind.config.js`)
- Utilities: `@tailwind base/components/utilities` in `index.css`
