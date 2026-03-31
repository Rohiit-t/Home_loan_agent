const STAGES = [
  { id: "awaiting_documents", label: "Documents", icon: "📄" },
  { id: "employment_status_collection", label: "Employment", icon: "🧾" },
  { id: "loan_details_collection", label: "Loan Details", icon: "💰" },
  { id: "existing_emi_collection", label: "Existing EMI", icon: "🏦" },
  { id: "financial_risk_check", label: "Risk Check", icon: "📊" },
  { id: "saving_data", label: "Complete", icon: "✅" },
];

const STAGE_ALIAS = {
  awaiting_employment_status: "employment_status_collection",
  awaiting_loan_details: "loan_details_collection",
  awaiting_existing_emi_choice: "existing_emi_collection",
  awaiting_existing_emi_details: "existing_emi_collection",
  emi_calculation: "saving_data",
};

function StageTracker({ currentStage }) {
  const normalizedStage = STAGE_ALIAS[currentStage] || currentStage;
  const isCompleted = normalizedStage === "completed";
  const activeIndex = isCompleted
    ? STAGES.length
    : STAGES.findIndex((s) => s.id === normalizedStage);

  return (
    <div className="stage-tracker">
      {STAGES.map((stage, i) => {
        const isDone = isCompleted || i < activeIndex;
        const isActive = !isCompleted && i === activeIndex;
        return (
          <div key={stage.id} className="stage-item">
            <div className={`stage-dot ${isDone ? "stage-dot--done" : isActive ? "stage-dot--active" : ""}`}>
              {isDone ? "✓" : stage.icon}
            </div>
            <span className={`stage-label ${isActive ? "stage-label--active" : isDone ? "stage-label--done" : ""}`}>
              {stage.label}
            </span>
            {i < STAGES.length - 1 && (
              <div className={`stage-line ${isDone ? "stage-line--done" : ""}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function StatusBar({ status, userId, threadId, onNewChat, currentStage }) {
  const dotClass =
    status === "connected" ? "status-dot status-dot--green"
    : status === "connecting" ? "status-dot status-dot--yellow"
    : "status-dot status-dot--red";

  const label =
    status === "connected" ? "Connected"
    : status === "connecting" ? "Connecting..."
    : "Disconnected";

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="sidebar-brand-logo">🏠</div>
        <div>
          <h2 className="sidebar-brand-title">HomeLoan<span className="brand-ai">AI</span></h2>
          <p className="sidebar-brand-sub">Application Assistant</p>
        </div>
      </div>

      <div className="sidebar-divider" />

      {/* Status */}
      <div className="sidebar-section">
        <p className="sidebar-section-label">Backend</p>
        <div className="status-row">
          <span className={dotClass} />
          <span className="status-label">{label}</span>
        </div>
      </div>

      {/* Application Progress */}
      <div className="sidebar-section">
        <p className="sidebar-section-label">Application Progress</p>
        <StageTracker currentStage={currentStage} />
      </div>

      <div className="sidebar-spacer" />

      {/* Session */}
      <div className="sidebar-section">
        <p className="sidebar-section-label">Session</p>
        <code className="session-id">{userId}</code>
        <code className="session-id">{threadId}</code>
      </div>

      <button className="new-chat-btn" onClick={onNewChat}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        New Chat
      </button>

      <p className="sidebar-footer">Powered by <strong>LangGraph</strong></p>
    </aside>
  );
}
