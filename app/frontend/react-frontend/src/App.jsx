import { useState, useEffect, useCallback } from "react";
import { useAuth } from "./context/AuthContext.jsx";
import LandingPage from "./components/LandingPage";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";
import StatusBar from "./components/StatusBar";
import PhoneVerification from "./components/PhoneVerification";
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

/* ─── Sign-In Screen ──────────────────────────────────── */
function SignInPage({ onSignIn, authActionLoading, authError }) {
  return (
    <div className="signin-page">
      <div className="signin-card">
        <div className="signin-logo">🏠</div>
        <h1 className="signin-title">HomeLoan<span className="signin-accent">AI</span></h1>
        <p className="signin-subtitle">AI-Powered Home Loan Processing</p>
        <button className="signin-google-btn" onClick={onSignIn} disabled={authActionLoading}>
          <svg className="signin-google-icon" viewBox="0 0 24 24" width="20" height="20">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
          </svg>
          {authActionLoading ? "Signing in..." : "Sign in with Google"}
        </button>
        {authError && <p className="signin-error">{authError}</p>}
        <p className="signin-hint">Sign in to start your home loan application</p>
      </div>
    </div>
  );
}

/* ─── Chat Page ───────────────────────────────────────── */
function ChatPage({ userEmail, userLabel, onSignOut }) {
  const { messages, status, isWaiting, interruptPayload, isProcessing, currentStage, userId, threadId, sendMessage, resetChat } = useWebSocket(userEmail);

  return (
    <div className="app-shell">
      <StatusBar status={status} userId={userId} threadId={threadId} onNewChat={resetChat} currentStage={currentStage} />
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
            <span className="top-bar-user" title={userLabel}>{userLabel}</span>
            <button className="top-bar-signout-btn" onClick={onSignOut}>Sign Out</button>
          </div>
        </header>

        <ChatWindow messages={messages} isProcessing={isProcessing} isWaiting={isWaiting} interruptPayload={interruptPayload} />
        {currentStage === "completed" ? (
          <div className="completion-bottom-banner">
            <div className="completion-icon">✅</div>
            <div className="completion-content">
              <h3 className="completion-title">Application Process Completed Successfully</h3>
              <p className="completion-msg">Your home loan application has been submitted . The bank will contact with you soon.</p>
            </div>
            <button className="new-app-btn" onClick={resetChat}>Start New Application</button>
          </div>
        ) : currentStage === "failed_unemployed" ? (
          <div className="failure-bottom-banner">
            <div className="failure-icon">🚫</div>
            <div className="failure-content">
              <h3 className="failure-title">Application Closed</h3>
              <p className="failure-msg">As per current bank rules, we currently do not process home loan applications for unemployed applicants.</p>
            </div>
            <button className="new-app-btn" onClick={resetChat}>Start New Application</button>
          </div>
        ) : currentStage === "failed_max_retries" ? (
          <div className="failure-bottom-banner">
            <div className="failure-icon">❌</div>
            <div className="failure-content">
              <h3 className="failure-title">Application Process Unsuccessful</h3>
              <p className="failure-msg">Maximum retry attempts reached. Please start a new application.</p>
            </div>
            <button className="new-app-btn" onClick={resetChat}>Start New Application</button>
          </div>
        ) : (
          <ChatInput
            onSend={sendMessage}
            isProcessing={isProcessing}
            isWaiting={isWaiting}
            interruptPayload={interruptPayload}
            currentStage={currentStage}
          />
        )}
      </main>
    </div>
  );
}

/* ─── Root App ────────────────────────────────────────── */
export default function App() {
  const { route, navigate } = useHashRoute();
  const { user, loading, phoneLinked, authActionLoading, authError, signInWithGoogle, signOut } = useAuth();

  if (loading) {
    return (
      <div className="signin-page">
        <div className="signin-card">
          <div className="signin-logo">🏠</div>
          <p className="signin-subtitle">Loading...</p>
        </div>
      </div>
    );
  }

  // Not signed in → show sign-in page
  if (!user) {
    return (
      <SignInPage
        onSignIn={signInWithGoogle}
        authActionLoading={authActionLoading}
        authError={authError}
      />
    );
  }

  // Signed in but phone NOT linked → force phone verification
  // Block access to landing page and chat until phone is verified
  if (!phoneLinked) {
    return (
      <PhoneVerification
        onVerified={() => navigate("#/")}
      />
    );
  }

  // Signed in AND phone linked → normal app flow
  const userEmail = user.email || "";
  const userLabel = user.displayName || user.email || "Signed in user";

  const handleSignOut = async () => {
    await signOut();
    navigate("#/");
  };

  if (route === "#/chat") {
    return <ChatPage userEmail={userEmail} userLabel={userLabel} onSignOut={handleSignOut} />;
  }
  return <LandingPage onStart={() => navigate("#/chat")} />;
}
