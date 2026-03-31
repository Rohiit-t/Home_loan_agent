import { useEffect, useRef, useState, useMemo } from "react";

/* ── Helpers ─────────────────────────────────────────── */
function extractInterruptText(payload) {
  if (!payload) return "";
  if (typeof payload === "object") return payload.message || JSON.stringify(payload);
  return String(payload);
}

/* ─────────────────────────────────────────────────────────
   ActivityLog — collapsible group of consecutive events
   Key insight: receives a stable `groupId` so React never
   unmounts/remounts it when new messages arrive.
───────────────────────────────────────────────────────── */
function ActivityLog({ events }) {
  // Open state MUST be stored at this level and must survive
  // parent re-renders.  We key by `groupId` (stable) not by
  // random value, so React reuses this component instance.
  const [open, setOpen] = useState(false);

  const count = events.length;
  const lastEvent = events[count - 1] || "";
  const cleanText = (t) =>
    String(t)
      .replace(/^\[.*?\]\s*/i, "")   // strip [tag] prefixes
      .replace(/^(?:⚙️|✅|⚠️|⏸️)\s*/u, "") // strip leading emoji
      .trim();

  return (
    <div className="activity-log">
      <button
        className={`activity-log-header ${open ? "activity-log-header--open" : ""}`}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="activity-log-pulse" />
        <span className="activity-log-label">Processing Steps</span>
        <span className="activity-log-summary">{cleanText(lastEvent)}</span>
        <span className="activity-log-badge">{count}</span>
        <span className={`activity-log-chevron ${open ? "activity-log-chevron--open" : ""}`}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </span>
      </button>

      {open && (
        <div className="activity-log-body">
          {events.map((text, i) => (
            <div key={i} className="activity-log-item">
              <span className="activity-log-item-dot" />
              <span className="activity-log-item-text">{cleanText(text)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Individual message renderers ────────────────────── */
function UserBubble({ text }) {
  return (
    <div className="msg-row msg-row--user">
      <div className="bubble bubble--user"><p>{text}</p></div>
      <div className="avatar avatar--user">U</div>
    </div>
  );
}

function BotBubble({ text }) {
  return (
    <div className="msg-row msg-row--bot">
      <div className="avatar avatar--bot">🏠</div>
      <div className="bubble bubble--bot">
        {text.split("\n").map((line, i) => (
          <p key={i}>{line || "\u00A0"}</p>
        ))}
      </div>
    </div>
  );
}

function WarningBanner({ text }) {
  return (
    <div className="msg-row msg-row--center">
      <div className="system-banner system-banner--warning">
        <span>⚠️</span><span>{text}</span>
      </div>
    </div>
  );
}

function ErrorBanner({ text }) {
  return (
    <div className="msg-row msg-row--center">
      <div className="system-banner system-banner--error">
        <span>❌</span><span>{text}</span>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="msg-row msg-row--bot">
      <div className="avatar avatar--bot">🏠</div>
      <div className="bubble bubble--bot typing-bubble">
        <div className="typing-dots"><span /><span /><span /></div>
      </div>
    </div>
  );
}

function InterruptCard({ payload }) {
  const msg = extractInterruptText(payload);
  return (
    <div className="interrupt-card">
      <div className="interrupt-card-inner">
        <span className="interrupt-card-icon">⏸️</span>
        <div>
          <span className="interrupt-card-label">Waiting for your input</span>
          <p className="interrupt-card-msg">{msg}</p>
        </div>
      </div>
      <div className="interrupt-card-glow" />
    </div>
  );
}

/* ─────────────────────────────────────────────────────────
   Main export
───────────────────────────────────────────────────────── */
export default function ChatWindow({ messages, isProcessing, isWaiting, interruptPayload }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isProcessing]);

  /*
   * Group consecutive "event" messages into ActivityLog blocks.
   *
   * FIX: Use the FIRST event message's `id` as the group key.
   * Because message IDs are assigned at creation time (stable),
   * React will REUSE the same ActivityLog component instance
   * even as more events are appended to the same group.
   * This preserves the `open` state across re-renders.
   */
  const groups = useMemo(() => {
    const result = [];
    let eventBuffer = [];       // text strings
    let eventGroupId = null;    // stable ID = first event's id

    function flushEvents() {
      if (eventBuffer.length) {
        result.push({
          type: "events",
          texts: [...eventBuffer],
          id: eventGroupId,     // ← stable, based on first event id
        });
        eventBuffer = [];
        eventGroupId = null;
      }
    }

    for (const msg of messages) {
      if (msg.kind === "event") {
        if (eventGroupId === null) eventGroupId = msg.id; // lock first id
        eventBuffer.push(msg.text);
      } else {
        flushEvents();
        result.push({ type: "msg", msg });
      }
    }
    flushEvents();
    return result;
  }, [messages]);

  return (
    <div className="chat-window">
      <div className="chat-messages">
        {groups.map((group) => {
          if (group.type === "events") {
            return (
              <ActivityLog
                key={group.id}        // stable → no unmount/remount
                events={group.texts}
              />
            );
          }
          const { msg } = group;
          if (msg.kind === "user")    return <UserBubble    key={msg.id} text={msg.text} />;
          if (msg.kind === "bot")     return <BotBubble     key={msg.id} text={msg.text} />;
          if (msg.kind === "warning") return <WarningBanner key={msg.id} text={msg.text} />;
          if (msg.kind === "error")   return <ErrorBanner   key={msg.id} text={msg.text} />;
          return null;
        })}

        {isProcessing && <TypingIndicator />}
        {isWaiting && interruptPayload && <InterruptCard payload={interruptPayload} />}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
