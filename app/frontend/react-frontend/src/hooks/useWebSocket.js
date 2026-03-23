import { useState, useCallback, useRef, useEffect } from "react";

const WS_URL = (import.meta.env.VITE_WS_URL || "ws://127.0.0.1:8000/chat").trim();
const RECONNECT_DELAY_MS = 2000;
const WATCHDOG_INTERVAL_MS = 1500;

// Monotonic counter — guarantees unique ordered IDs even for rapid bursts
let msgCounter = 1;
function nextId() { return msgCounter++; }

/**
 * Extract a human-readable string from a custom stream event payload.
 * Tries known keys first, then scans all string values, then JSON stringify.
 * Never returns empty string for a non-empty payload.
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

  // Use refs where possible to avoid stale closures and prevent
  // useEffect from re-running due to dependency chain changes.
  const threadIdRef      = useRef(`loan-chat-${crypto.randomUUID()}`);
  const wsRef            = useRef(null);
  const seenFP           = useRef(new Set());
  const mountedRef       = useRef(true);
  const reconnectTimer   = useRef(null);
  const isResettingRef   = useRef(false);
  const connectRef       = useRef(null);   // forward-ref so handlePacket can call connect

  /* ─── helpers ─────────────────────────────────────────── */
  const addMessage = useCallback((msg) => {
    if (!mountedRef.current) return;
    setMessages((prev) => [...prev, { id: nextId(), ...msg }]);
  }, []);

  const isDuplicateBot = useCallback((text) => {
    const fp = `bot:${text.trim()}`;
    if (seenFP.current.has(fp)) return true;
    seenFP.current.add(fp);
    return false;
  }, []);

  /* ─── message router ───────────────────────────────────── */
  // NOTE: handlePacket is stable — wraps mutable refs, not useState values.
  const handlePacket = useCallback((packet) => {
    const { event, data = {} } = packet;

    if (event === "custom") {
      if (data?.replay) return;
      const text = extractStreamMessage(data);
      const type = (data?.type || "").trim().toLowerCase();
      if (text) {
        addMessage({ kind: type === "warning" ? "warning" : "event", text });
      }

    } else if (event === "updates") {
      if (data?.current_stage) setCurrentStage(data.current_stage);
      if (Array.isArray(data?.messages)) {
        for (const raw of data.messages) {
          const text = String(raw).trim();
          if (text && !isHiddenInternal(text) && !isDuplicateBot(text)) {
            addMessage({ kind: "bot", text });
          }
        }
      }

    } else if (event === "interrupt") {
      // Show the interrupt card — do NOT also add a duplicate event chip.
      setIsWaiting(true);
      setInterruptPayload(data);
      setIsProcessing(false);

    } else if (event === "done") {
      // Graph finished a full turn (no interrupt).
      if (data?.current_stage) setCurrentStage(data.current_stage);
      setIsWaiting(false);
      setInterruptPayload(null);
      setIsProcessing(false);

    } else if (event === "end") {
      // "end" = server finished streaming this turn.
      // isProcessing is cleared here; isWaiting remains until "done" or user resumes.
      setIsProcessing(false);

    } else if (event === "error") {
      addMessage({ kind: "error", text: data?.message || "Backend error" });
      setIsProcessing(false);
      setIsWaiting(false);
    }
  }, [addMessage, isDuplicateBot]);

  /* ─── connect ──────────────────────────────────────────── */
  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    const ws = wsRef.current;
    // Don't open a new connection if one is already alive
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

    newWs.onerror = () => {
      // Will always be followed by onclose — no need to handle here separately
    };

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

  // Keep forward-ref current so the onclose timer always calls the latest `connect`
  useEffect(() => { connectRef.current = connect; }, [connect]);

  /* ─── lifecycle ────────────────────────────────────────── */
  useEffect(() => {
    mountedRef.current = true;
    connect();

    // Watchdog: forcefully sync status to actual ws.readyState every 1.5 s.
    // Catches silent drops (e.g. SIGKILL) where onclose may be delayed.
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
        wsRef.current.onclose = null;  // prevent rogue reconnects on unmount
        wsRef.current.close();
      }
    };
  }, []); // ← empty deps: run once on mount, stable via refs

  /* ─── send a message ───────────────────────────────────── */
  const sendMessage = useCallback(({ text = "", jsonDocument = null, isResume = false } = {}) => {
    // Optimistically show user message before network call
    if (text.trim())   addMessage({ kind: "user", text: text.trim() });
    if (jsonDocument)  addMessage({ kind: "user", text: `📎 Uploaded: ${jsonDocument._fileName || "document.json"}` });

    // Build backend payload
    const payload = { thread_id: threadIdRef.current };
    let normalized;
    if (jsonDocument) {
      const { _fileName, ...docData } = jsonDocument;
      normalized = { type: "file_upload", data: docData };
    } else {
      normalized = { type: "text", message: text.trim() };
    }
    if (isResume) payload.resume = normalized;
    else Object.assign(payload, normalized);

    // Guard: socket must be OPEN
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      addMessage({ kind: "error", text: "Backend not connected. Please wait for reconnection and try again." });
      connectRef.current?.();
      return;
    }

    setIsProcessing(true);
    // When resuming an interrupt, clear the waiting state immediately on send
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
  }, [addMessage]);

  /* ─── new chat ─────────────────────────────────────────── */
  const resetChat = useCallback(() => {
    isResettingRef.current = true;
    threadIdRef.current = `loan-chat-${crypto.randomUUID()}`;
    seenFP.current = new Set();
    setMessages([{ id: nextId(), kind: "bot", text: WELCOME }]);
    setIsWaiting(false);
    setInterruptPayload(null);
    setIsProcessing(false);
    setCurrentStage(null);
    // Deliberately keep the existing WebSocket open — just switch thread_id
    isResettingRef.current = false;
  }, []);

  return {
    messages, status, isWaiting, interruptPayload,
    isProcessing, currentStage,
    threadId: threadIdRef.current,
    sendMessage, resetChat,
  };
}
