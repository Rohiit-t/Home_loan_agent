import { useState, useCallback, useRef, useEffect } from "react";

const WS_URL = "ws://127.0.0.1:8000/chat";
const RECONNECT_DELAY_MS = 2000;
const WATCHDOG_INTERVAL_MS = 1500;
const USER_ID_PREFIX = "USR";

// Monotonic counter — guarantees unique ordered IDs even for rapid bursts
let msgCounter = 1;
function nextId() { return msgCounter++; }
function createReadableUserId() {
  return `${USER_ID_PREFIX}-${crypto.randomUUID()}`;
}

/**
 * Extract a human-readable string from a custom stream event payload.
 */
function extractStreamMessage(data) {
  if (!data) return "";
  if (typeof data === "string") return data.trim();
  for (const key of ["msg", "ui_message", "message", "text", "content", "status"]) {
    if (typeof data[key] === "string" && data[key].trim()) return data[key].trim();
  }
  for (const val of Object.values(data)) {
    if (typeof val === "string" && val.trim()) return val.trim();
  }
  const raw = JSON.stringify(data);
  return raw !== "{}" ? raw : "";
}

function isHiddenInternal(text) {
  return text.trim().toLowerCase().startsWith("intent:");
}

const WELCOME = "Welcome! Please share your email address to continue your home loan application.";

export default function useWebSocket() {
  const [messages, setMessages] = useState([{ id: nextId(), kind: "bot", text: WELCOME }]);
  const [status, setStatus] = useState("disconnected");
  const [isWaiting, setIsWaiting] = useState(false);
  const [interruptPayload, setInterruptPayload] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStage, setCurrentStage] = useState(null);

  const userIdRef        = useRef(createReadableUserId());
  const threadIdRef      = useRef(`loan-chat-${crypto.randomUUID()}`);
  const wsRef            = useRef(null);
  const mountedRef       = useRef(true);
  const reconnectTimer   = useRef(null);
  const isResettingRef   = useRef(false);
  const connectRef       = useRef(null);

  /**
   * PER-TURN DEDUP ONLY
   *
   * Dedup is scoped to ONE streaming turn (one sendMessage / resume round-trip).
   * Cleared at the start of every user action so that:
   *  - Within one turn, exact same text or same backend ID → suppressed (correct)
   *  - Across turns, same text (e.g. "I am a Home Loan Application assistant...")
   *    is allowed to appear again (correct — it IS a new response to a new query)
   *
   * The backend already prevents replayed old messages via:
   *  1. nodes.py: document_processing cherry-picks subgraph keys, no accumulated msgs leak
   *  2. main.py: per-turn sent_msg_ids with deterministic content-hash IDs
   */
  const turnSeenFP   = useRef(new Set());   // text fingerprints (current turn)
  const turnSeenIds  = useRef(new Set());   // backend msg IDs   (current turn)

  const resetTurnDedup = useCallback(() => {
    turnSeenFP.current  = new Set();
    turnSeenIds.current = new Set();
  }, []);

  /* ─── helpers ─────────────────────────────────────────── */
  const addMessage = useCallback((msg) => {
    if (!mountedRef.current) return;
    setMessages((prev) => [...prev, { id: nextId(), ...msg }]);
  }, []);

  /**
   * Returns true if a message should be SUPPRESSED (duplicate within this turn).
   */
  const isDuplicate = useCallback((text, messageId = null) => {
    const trimmed = text.trim();

    if (messageId) {
      if (turnSeenIds.current.has(messageId)) return true;
      turnSeenIds.current.add(messageId);
      // also register text fingerprint to catch cross-path dups (custom + updates)
      turnSeenFP.current.add(`bot:${trimmed}`);
      return false;
    }

    // No ID — text fingerprint only
    const fp = `bot:${trimmed}`;
    if (turnSeenFP.current.has(fp)) return true;
    turnSeenFP.current.add(fp);
    return false;
  }, []);

  /* ─── message router ───────────────────────────────────── */
  const handlePacket = useCallback((packet) => {
    const { event, data = {} } = packet;

    if (event === "custom") {
      if (data?.replay) return;
      const text = extractStreamMessage(data);
      const type = (data?.type || "").trim().toLowerCase();
      if (text && !isHiddenInternal(text)) {
        if (!isDuplicate(text)) {
          addMessage({ kind: type === "warning" ? "warning" : "event", text });
        }
      }

    } else if (event === "updates") {
      if (data?.current_stage) setCurrentStage(data.current_stage);
      const incoming = Array.isArray(data?.bot_messages) ? data.bot_messages : data?.messages;
      if (Array.isArray(incoming)) {
        for (const raw of incoming) {
          const text      = typeof raw === "string" ? raw.trim() : String(raw?.text || "").trim();
          const messageId = typeof raw === "object"  ? String(raw?.id  || "").trim() : "";
          if (text && !isHiddenInternal(text) && !isDuplicate(text, messageId || null)) {
            addMessage({ kind: "bot", text });
          }
        }
      }

    } else if (event === "interrupt") {
      setIsWaiting(true);
      setInterruptPayload(data);
      setIsProcessing(false);

    } else if (event === "done") {
      if (data?.current_stage) setCurrentStage(data.current_stage);
      setIsWaiting(false);
      setInterruptPayload(null);
      setIsProcessing(false);

    } else if (event === "end") {
      setIsProcessing(false);

    } else if (event === "error") {
      addMessage({ kind: "error", text: data?.message || "Backend error" });
      setIsProcessing(false);
      setIsWaiting(false);
    }
  }, [addMessage, isDuplicate]);

  /* ─── connect ──────────────────────────────────────────── */
  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    const ws = wsRef.current;
    if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) return;

    setStatus("connecting");
    const newWs = new WebSocket(WS_URL);
    wsRef.current = newWs;

    newWs.onopen = () => {
      if (!mountedRef.current) return;
      setStatus("connected");
      clearTimeout(reconnectTimer.current);
    };

    newWs.onmessage = (e) => {
      if (!mountedRef.current) return;
      try { handlePacket(JSON.parse(e.data)); }
      catch { /* ignore malformed */ }
    };

    newWs.onerror = () => {};

    newWs.onclose = () => {
      if (!mountedRef.current) return;
      wsRef.current = null;
      setStatus("disconnected");
      setIsProcessing(false);

      if (!isResettingRef.current) {
        reconnectTimer.current = setTimeout(() => connectRef.current?.(), RECONNECT_DELAY_MS);
      }
    };
  }, [handlePacket]);

  useEffect(() => { connectRef.current = connect; }, [connect]);

  /* ─── lifecycle ────────────────────────────────────────── */
  useEffect(() => {
    mountedRef.current = true;
    connect();

    const watchdog = setInterval(() => {
      if (!mountedRef.current) return;
      const rs = wsRef.current?.readyState;
      if      (rs === WebSocket.OPEN)       setStatus("connected");
      else if (rs === WebSocket.CONNECTING) setStatus("connecting");
      else                                  setStatus("disconnected");
    }, WATCHDOG_INTERVAL_MS);

    return () => {
      mountedRef.current = false;
      clearInterval(watchdog);
      clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, []);

  /* ─── send a message ───────────────────────────────────── */
  const sendMessage = useCallback(({ text = "", jsonDocument = null, isResume = false } = {}) => {
    // Reset per-turn dedup at the start of every new interaction
    resetTurnDedup();

    if (text.trim())   addMessage({ kind: "user", text: text.trim() });
    if (jsonDocument)  addMessage({ kind: "user", text: `📎 Uploaded: ${jsonDocument._fileName || "document.json"}` });

    const payload = {
      thread_id: threadIdRef.current,
      user_id: userIdRef.current,
    };
    let normalized;
    if (jsonDocument) {
      const { _fileName, ...docData } = jsonDocument;
      normalized = { type: "file_upload", data: docData };
    } else {
      normalized = { type: "text", message: text.trim() };
    }
    if (isResume) payload.resume = normalized;
    else Object.assign(payload, normalized);

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      addMessage({ kind: "error", text: "Backend not connected. Please wait for reconnection and try again." });
      connectRef.current?.();
      return;
    }

    setIsProcessing(true);
    if (isResume) {
      setIsWaiting(false);
      setInterruptPayload(null);
    }

    try {
      wsRef.current.send(JSON.stringify(payload));
    } catch (err) {
      addMessage({ kind: "error", text: `Send failed: ${err.message}` });
      setIsProcessing(false);
    }
  }, [addMessage, resetTurnDedup]);

  /* ─── new chat ─────────────────────────────────────────── */
  const resetChat = useCallback(() => {
    isResettingRef.current = true;
    userIdRef.current = createReadableUserId();
    threadIdRef.current = `loan-chat-${crypto.randomUUID()}`;
    resetTurnDedup();
    setMessages([{ id: nextId(), kind: "bot", text: WELCOME }]);
    setIsWaiting(false);
    setInterruptPayload(null);
    setIsProcessing(false);
    setCurrentStage(null);
    isResettingRef.current = false;
  }, [resetTurnDedup]);

  return {
    messages, status, isWaiting, interruptPayload,
    isProcessing, currentStage,
    userId: userIdRef.current,
    threadId: threadIdRef.current,
    sendMessage, resetChat,
  };
}
