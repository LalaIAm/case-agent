# WebSocket Agent Monitoring – Manual Testing Checklist

Use this checklist when verifying real-time agent status over **Socket.IO** (path `/ws/agents`, query `caseId` + `token`).

- [ ] **Connection**: Socket.IO client connects with valid JWT (token in query); status shows "Live" (green dot).
- [ ] **Reconnection**: After a brief network interruption, client reconnects (socket.io handles reconnection).
- [ ] **Invalid/expired token**: With expired or invalid token, connection is rejected; user may be redirected to login.
- [ ] **Unauthorized case**: With valid token but no access to the case, connection is rejected and an error message is shown.
- [ ] **Multiple tabs**: Open the same case in multiple browser tabs; all tabs receive the same agent/workflow updates.
- [ ] **Workflow progression**: Run agents and confirm workflow moves through Intake → Research → Document Analysis → Strategy → Drafting; progress bar and diagram update in real time.
- [ ] **Agent failure**: If an agent fails, error state is shown (red, failed step) and notification appears.
- [ ] **Responsiveness**: On narrow viewports, workflow diagram switches to vertical layout; all controls remain usable.
- [ ] **Accessibility**: Tab through controls; use screen reader to confirm status and notifications are announced.
- [ ] **Loading/empty states**: Initial load shows "Connecting to agent monitoring…"; when no activity, "No agent activity yet" with Run Agents CTA is shown.
