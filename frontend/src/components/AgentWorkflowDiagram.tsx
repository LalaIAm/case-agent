/**
 * Horizontal stepper for agent workflow: Intake → Research → Document → Strategy → Drafting.
 */
const WORKFLOW_STEPS = [
  { id: 'intake', label: 'Intake', icon: '📝' },
  { id: 'research', label: 'Research', icon: '🔍' },
  { id: 'document', label: 'Document Analysis', icon: '📄' },
  { id: 'strategy', label: 'Strategy', icon: '⚖️' },
  { id: 'drafting', label: 'Drafting', icon: '✍️' },
] as const;

export interface AgentWorkflowDiagramProps {
  currentAgent: string | null;
  completedAgents: string[];
  workflowStatus: string;
}

function stepState(
  stepId: string,
  currentAgent: string | null,
  completedAgents: string[],
  workflowStatus: string
): 'completed' | 'current' | 'pending' | 'failed' {
  const completed = completedAgents.includes(stepId);
  const isCurrent = currentAgent === stepId;
  const failed = workflowStatus === 'failed' && isCurrent;
  if (failed) return 'failed';
  if (completed) return 'completed';
  if (isCurrent) return 'current';
  return 'pending';
}

export function AgentWorkflowDiagram({
  currentAgent,
  completedAgents,
  workflowStatus,
}: AgentWorkflowDiagramProps) {
  return (
    <div className="w-full" aria-label="Agent workflow">
      {/* Desktop: horizontal */}
      <div className="hidden sm:flex sm:items-center sm:justify-between">
        {WORKFLOW_STEPS.map((step, index) => {
          const state = stepState(
            step.id,
            currentAgent,
            completedAgents,
            workflowStatus
          );
          const isLast = index === WORKFLOW_STEPS.length - 1;
          return (
            <div
              key={step.id}
              className="flex flex-1 items-center"
              title={`${step.label} – ${state}`}
            >
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 text-lg transition-all ${
                    state === 'completed'
                      ? 'border-green-500 bg-green-500 text-white'
                      : state === 'current'
                        ? 'border-blue-500 bg-blue-500 text-white animate-pulse'
                        : state === 'failed'
                          ? 'border-red-500 bg-red-500 text-white'
                          : 'border-gray-300 bg-white text-gray-400'
                  }`}
                >
                  {state === 'completed' ? (
                    <span aria-hidden>✓</span>
                  ) : state === 'failed' ? (
                    <span aria-hidden>✕</span>
                  ) : (
                    <span aria-hidden>{step.icon}</span>
                  )}
                </div>
                <span
                  className={`mt-1 text-xs font-medium ${
                    state === 'current'
                      ? 'text-blue-600'
                      : state === 'completed'
                        ? 'text-green-700'
                        : state === 'failed'
                          ? 'text-red-700'
                          : 'text-gray-500'
                  }`}
                >
                  {step.label}
                </span>
              </div>
              {!isLast && (
                <div
                  className={`mx-1 h-0.5 flex-1 min-w-[8px] ${
                    completedAgents.includes(step.id)
                      ? 'bg-green-400'
                      : currentAgent === step.id
                        ? 'border-t-2 border-dashed border-blue-400'
                        : 'border-t border-dashed border-gray-300'
                  }`}
                  aria-hidden="true"
                />
              )}
            </div>
          );
        })}
      </div>
      {/* Mobile: vertical */}
      <div className="space-y-2 sm:hidden" role="list">
        {WORKFLOW_STEPS.map((step) => {
          const state = stepState(
            step.id,
            currentAgent,
            completedAgents,
            workflowStatus
          );
          return (
            <div
              key={step.id}
              role="listitem"
              className={`flex items-center gap-3 rounded-lg border px-3 py-2 ${
                state === 'current'
                  ? 'border-blue-400 bg-blue-50'
                  : state === 'completed'
                    ? 'border-green-200 bg-green-50'
                    : state === 'failed'
                      ? 'border-red-200 bg-red-50'
                      : 'border-gray-200 bg-gray-50'
              }`}
              role="listitem"
            >
              <div
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm ${
                  state === 'completed'
                    ? 'bg-green-500 text-white'
                    : state === 'current'
                      ? 'bg-blue-500 text-white animate-pulse'
                      : state === 'failed'
                        ? 'bg-red-500 text-white'
                        : 'bg-gray-200 text-gray-500'
                }`}
              >
                {state === 'completed' ? '✓' : state === 'failed' ? '✕' : step.icon}
              </div>
              <span
                className={`text-sm font-medium ${
                  state === 'current'
                    ? 'text-blue-700'
                    : state === 'completed'
                      ? 'text-green-700'
                      : state === 'failed'
                        ? 'text-red-700'
                        : 'text-gray-600'
                }`}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
