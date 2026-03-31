import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";

const FEATURES = [
  {
    icon: "📄",
    title: "Smart Document Processing",
    desc: "Upload Aadhaar, PAN, ITR documents and our AI verifies them instantly.",
  },
  {
    icon: "🤖",
    title: "AI-Powered Assessment",
    desc: "Get real-time eligibility checks, CIBIL score analysis, and risk evaluation.",
  },
  {
    icon: "💰",
    title: "EMI Calculator",
    desc: "Detailed loan repayment breakdown with year-wise amortization schedule.",
  },
  {
    icon: "⚡",
    title: "Real-Time Streaming",
    desc: "Watch every step of your application processed live with instant feedback.",
  },
];

const STEPS = [
  { num: "01", label: "Share your details" },
  { num: "02", label: "Upload documents" },
  { num: "03", label: "Get instant assessment" },
  { num: "04", label: "Receive loan offer" },
];

export default function LandingPage({ onStart }) {
  const { user, signOut } = useAuth();
  const [visible, setVisible] = useState(false);
  const [activeFeature, setActiveFeature] = useState(0);

  useEffect(() => {
    // Trigger entrance animations
    requestAnimationFrame(() => setVisible(true));

    // Auto-cycle features
    const interval = setInterval(() => {
      setActiveFeature((prev) => (prev + 1) % FEATURES.length);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={`landing ${visible ? "landing--visible" : ""}`}>
      {/* Navigation */}
      <nav className="landing-nav">
        <div className="landing-nav-brand">
          <span className="nav-logo">🏠</span>
          <span className="nav-title">HomeLoan<span className="nav-accent">AI</span></span>
        </div>
        {user && (
          <div className="landing-nav-user">
            <span className="nav-user-email">{user.displayName || user.email}</span>
            <button className="nav-signout-btn" onClick={signOut}>Sign Out</button>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <section className="hero">
        <div className="hero-badge">✨ AI-Powered Home Loan Processing</div>
        <h1 className="hero-title">
          Your Dream Home
          <br />
          <span className="hero-gradient">Starts Here</span>
        </h1>
        <p className="hero-subtitle">
          Experience the future of home loan applications. Our AI assistant guides you
          through every step — from document verification to loan approval — all in real time.
        </p>

        <button className="cta-button" onClick={onStart}>
          <span className="cta-text">Start Your Application</span>
          <span className="cta-arrow">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="5" y1="12" x2="19" y2="12" />
              <polyline points="12 5 19 12 12 19" />
            </svg>
          </span>
          <span className="cta-glow" />
        </button>

        <p className="hero-hint">No paperwork. No branch visits. 100% digital.</p>
      </section>

      {/* Steps */}
      <section className="steps-section">
        <h2 className="section-title">How It Works</h2>
        <div className="steps-track">
          {STEPS.map((step, i) => (
            <div className="step-card" key={i}>
              <span className="step-num">{step.num}</span>
              <span className="step-label">{step.label}</span>
              {i < STEPS.length - 1 && <div className="step-connector" />}
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="features-section">
        <h2 className="section-title">Intelligent Features</h2>
        <div className="features-grid">
          {FEATURES.map((f, i) => (
            <div
              className={`feature-card ${i === activeFeature ? "feature-card--active" : ""}`}
              key={i}
              onMouseEnter={() => setActiveFeature(i)}
            >
              <div className="feature-icon">{f.icon}</div>
              <h3 className="feature-title">{f.title}</h3>
              <p className="feature-desc">{f.desc}</p>
              <div className="feature-shine" />
            </div>
          ))}
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="bottom-cta">
        <div className="bottom-cta-card">
          <h2>Ready to get started?</h2>
          <p>Join thousands of applicants who got their home loan approved with AI assistance.</p>
          <button className="cta-button cta-button--secondary" onClick={onStart}>
            <span className="cta-text">Begin Application →</span>
            <span className="cta-glow" />
          </button>
        </div>
      </section>

      <footer className="landing-footer">
        <p>Built with <strong>LangGraph</strong> & <strong>React</strong> • AI-powered home loan processing</p>
      </footer>
    </div>
  );
}
