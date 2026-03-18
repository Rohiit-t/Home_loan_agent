"""
Simplified Streamlit Chatbot Frontend for Home Loan Application.

Connects to FastAPI backend via WebSocket for real-time chat.
Clean, minimal UI — just a chatbot with beautiful styling.
"""

import streamlit as st
import requests
import json
from datetime import datetime
from websocket import create_connection, WebSocketException


# ==================== Configuration ====================

API_BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"


# ==================== Page Config ====================

st.set_page_config(
    page_title="Home Loan Assistant",
    page_icon="🏠",
    layout="centered",
)


# ==================== Custom CSS ====================

st.markdown("""
<style>
    /* Import modern font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    * { font-family: 'Inter', sans-serif; }

    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 0.5rem;
        max-width: 800px;
    }

    /* ── Header ── */
    .chat-header {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 40%, #2c5364 100%);
        color: white;
        padding: 1.4rem 1.8rem;
        border-radius: 16px;
        margin-bottom: 1.2rem;
        text-align: center;
        box-shadow: 0 8px 32px rgba(15, 32, 39, 0.25);
    }
    .chat-header h1 {
        margin: 0;
        font-size: 1.6rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    .chat-header p {
        margin: 0.35rem 0 0;
        font-size: 0.88rem;
        opacity: 0.75;
        font-weight: 400;
    }

    /* ── Chat bubbles ── */
    .msg-user {
        background: linear-gradient(135deg, #1a3a5c, #1e5799);
        color: #fff;
        padding: 0.75rem 1.1rem;
        border-radius: 18px 18px 4px 18px;
        margin: 0.5rem 0;
        max-width: 78%;
        margin-left: auto;
        font-size: 0.92rem;
        line-height: 1.55;
        box-shadow: 0 2px 8px rgba(30, 87, 153, 0.18);
    }
    .msg-ai {
        background: #ffffff;
        color: #1a1a2e;
        padding: 0.75rem 1.1rem;
        border-radius: 18px 18px 18px 4px;
        margin: 0.5rem 0;
        max-width: 82%;
        border: 1px solid #e8ecf1;
        font-size: 0.92rem;
        line-height: 1.55;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .msg-status {
        background: linear-gradient(90deg, #fffbeb, #fef3c7);
        color: #92400e;
        padding: 0.35rem 0.85rem;
        border-radius: 8px;
        margin: 0.25rem 0;
        font-size: 0.8rem;
        border-left: 3px solid #f59e0b;
        max-width: 70%;
    }

    /* ── Onboarding card ── */
    .onboard-card {
        background: #ffffff;
        border: 1px solid #e8ecf1;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    }
    .onboard-card h3 {
        margin: 0 0 0.4rem;
        font-weight: 600;
        color: #1a1a2e;
    }
    .onboard-card p {
        color: #64748b;
        font-size: 0.9rem;
        margin: 0 0 1.2rem;
    }

    /* ── Misc ── */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ==================== Session State ====================

def init_state():
    defaults = {
        "session_id": None,
        "thread_id": None,
        "user_id": None,
        "chat_history": [],   # [{"role": "user"/"assistant"/"status", "content": str}]
        "session_created": False,
        "ws": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ==================== WebSocket Helpers ====================

def check_backend():
    try:
        return requests.get(f"{API_BASE_URL}/health", timeout=5).status_code == 200
    except Exception:
        return False


def get_ws():
    ws = st.session_state.get("ws")
    if ws and ws.connected:
        return ws
    try:
        ws = create_connection(WS_URL, timeout=10)
        st.session_state.ws = ws
        return ws
    except Exception:
        st.session_state.ws = None
        return None


def close_ws():
    ws = st.session_state.get("ws")
    if ws:
        try:
            ws.close()
        except Exception:
            pass
        st.session_state.ws = None


def create_session(user_id: str):
    """Create a new session via WebSocket."""
    try:
        ws = get_ws()
        if not ws:
            return False, "Cannot connect to backend. Is the FastAPI server running?"
        ws.send(json.dumps({"action": "create_session", "user_id": user_id}))
        resp = json.loads(ws.recv())
        if resp.get("type") == "session_created":
            st.session_state.session_id = resp["session_id"]
            st.session_state.thread_id = resp["thread_id"]
            st.session_state.user_id = resp["user_id"]
            st.session_state.session_created = True
            return True, resp.get("message", "Session created")
        return False, resp.get("content", "Unknown error")
    except (WebSocketException, Exception) as e:
        close_ws()
        return False, str(e)


def send_message(message: str):
    """Send a chat message and collect all streamed response chunks."""
    chunks = []
    try:
        ws = get_ws()
        if not ws:
            return [{"type": "error", "content": "WebSocket not connected."}]
        ws.send(json.dumps({
            "action": "send_message",
            "session_id": st.session_state.session_id,
            "message": message,
        }))
        while True:
            raw = ws.recv()
            try:
                chunk = json.loads(raw)
                chunks.append(chunk)
                if chunk.get("type") in ("complete", "error"):
                    break
            except json.JSONDecodeError:
                continue
    except (WebSocketException, Exception) as e:
        close_ws()
        chunks.append({"type": "error", "content": str(e)})
    return chunks


def process_chunks(chunks):
    """Process WebSocket chunks into chat history entries."""
    for chunk in chunks:
        ctype = chunk.get("type", "")
        content = chunk.get("content", "")

        if ctype == "yield":
            st.session_state.chat_history.append({"role": "status", "content": f"⚡ {content}"})
        elif ctype == "message":
            st.session_state.chat_history.append({"role": "assistant", "content": content})
        elif ctype == "state":
            field = chunk.get("field", "")
            value = chunk.get("value")
            if field == "intent" and value:
                st.session_state.chat_history.append({"role": "status", "content": f"🎯 Intent: {value}"})
            elif field == "all_documents_uploaded" and value:
                st.session_state.chat_history.append({"role": "status", "content": "✅ All documents uploaded!"})
            elif field == "all_loan_details_provided" and value:
                st.session_state.chat_history.append({"role": "status", "content": "✅ All loan details collected!"})
            elif field == "application_saved" and value:
                st.session_state.chat_history.append({"role": "status", "content": "💾 Application saved!"})
        elif ctype == "error":
            st.session_state.chat_history.append({"role": "assistant", "content": f"⚠️ {content}"})
        # "complete" type — nothing to show, just marks end of stream


# ==================== UI Rendering ====================

def render_header():
    st.markdown(
        '<div class="chat-header">'
        '<h1>🏠 Home Loan Assistant</h1>'
        '<p>AI-powered chatbot to guide you through your loan application</p>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_messages():
    for msg in st.session_state.chat_history:
        role, content = msg["role"], msg["content"]
        if role == "user":
            st.markdown(f'<div class="msg-user">👤 {content}</div>', unsafe_allow_html=True)
        elif role == "assistant":
            st.markdown(f'<div class="msg-ai">🤖 {content}</div>', unsafe_allow_html=True)
        elif role == "status":
            st.markdown(f'<div class="msg-status">{content}</div>', unsafe_allow_html=True)


# ==================== Main App ====================

def main():
    render_header()

    # ── Backend health check ──
    if not check_backend():
        st.error("⚠️ Backend not reachable. Start it with: `python -m app.backend.api.main`")
        st.stop()

    # ── Onboarding (session not created yet) ──
    if not st.session_state.session_created:
        st.markdown(
            '<div class="onboard-card">'
            '<h3>Welcome! 👋</h3>'
            '<p>Enter your name to start your home loan application.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        with st.form("start_form"):
            name = st.text_input("Your Name", placeholder="e.g. John")
            started = st.form_submit_button("🚀 Start Chat", use_container_width=True)
            if started:
                uid = name.strip() or f"user_{datetime.now().strftime('%H%M%S')}"
                ok, msg = create_session(uid)
                if ok:
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": (
                            f"Hello **{uid}**! 🎉 I'm your Home Loan Assistant.\n\n"
                            "I'll walk you through:\n"
                            "1. Uploading documents (PAN, Aadhaar, ITR)\n"
                            "2. Collecting your personal & financial details\n"
                            "3. Loan details & risk assessment\n\n"
                            "Type anything to get started!"
                        ),
                    })
                    st.rerun()
                else:
                    st.error(f"Failed: {msg}")
        return

    # ── Chat interface ──
    render_messages()

    user_input = st.chat_input("Type your message…")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.spinner("🔄 Processing…"):
            chunks = send_message(user_input)
            process_chunks(chunks)
        st.rerun()

    # ── Reset button ──
    st.markdown("---")
    if st.button("🔄 New Application", use_container_width=True):
        close_ws()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


if __name__ == "__main__":
    main()
