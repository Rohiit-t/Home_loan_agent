import { useState, useEffect, useCallback } from "react";
import LandingPage from "./components/LandingPage";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";
import StatusBar from "./components/StatusBar";
import useWebSocket from "./hooks/useWebSocket";
import "./index.css";

function useHashRoute() {
  const [route, setRoute] = useState(window.location.hash || "#/");
  useEffect(() => {
    const onHashChange = () => setRoute(window.location.hash || "#/");
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  const navigate = useCallback((hash) => { window.location.hash = hash; }, []);
  return { route, navigate };
}

function ChatPage() {
  const { messages, status, isWaiting, interruptPayload, isProcessing, currentStage, threadId, sendMessage, resetChat } = useWebSocket();

  return (
    <div className="app-shell">
      <StatusBar status={status} threadId={threadId} onNewChat={resetChat} currentStage={currentStage} />
      <main className="main-area">
        <header className="top-bar">
          <div className="top-bar-left">
            <a href="#/" className="top-bar-back" title="Back to Home">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </a>
            <h1 className="top-bar-title">
              <span className="logo-icon">🏠</span> Home Loan Assistant
            </h1>
          </div>
          <div className="top-bar-right">
            {isProcessing && <span className="processing-badge">⚡ Processing</span>}
            <span className={`top-bar-badge ${status === "connected" ? "badge-ok" : ""}`}>
              {status === "connected" ? "Live" : "Offline"}
            </span>
          </div>
        </header>

        <ChatWindow messages={messages} isProcessing={isProcessing} isWaiting={isWaiting} interruptPayload={interruptPayload} />
        <ChatInput onSend={sendMessage} isProcessing={isProcessing} isWaiting={isWaiting} />
      </main>
    </div>
  );
}

export default function App() {
  const { route, navigate } = useHashRoute();
  if (route === "#/chat") return <ChatPage />;
  return <LandingPage onStart={() => navigate("#/chat")} />;
}
