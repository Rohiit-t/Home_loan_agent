import uuid
import os
import sys
from typing import Any, Dict, Iterable, Tuple

import streamlit as st
from langchain_core.messages import HumanMessage
from langgraph.types import Command

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.backend.graph.main import build_graph

st.set_page_config(page_title="Home Loan Assistant", page_icon="🏠", layout="centered")
st.title("🏠 Home Loan Assistant")

WELCOME_MESSAGE = "Welcome! Please share your email address to continue your home loan application."


@st.cache_resource
def get_graph():
    return build_graph()


def _generate_user_id() -> str:
    return f"user_{uuid.uuid4().hex[:10]}"


def _ensure_user_id() -> str:
    user_id = st.session_state.get("user_id")
    if not user_id:
        user_id = _generate_user_id()
        st.session_state.user_id = user_id
    return user_id


def _unpack_updates(data: Any) -> Iterable[Tuple[str, Any]]:
    if isinstance(data, list):
        for item in data:
            if isinstance(item, (tuple, list)) and len(item) == 2 and item[0] != "__interrupt__":
                yield item[0], item[1]
    elif isinstance(data, dict):
        for key, value in data.items():
            if key != "__interrupt__":
                yield key, value


def _node_label(node_name: str) -> str:
    return node_name.replace("_", " ").title()


def _append_event(text: str) -> None:
    st.session_state.chat_log.append({"kind": "event", "text": text})


def _append_bot(text: str) -> None:
    st.session_state.chat_log.append({"kind": "bot", "text": text})


def _append_user(text: str) -> None:
    st.session_state.chat_log.append({"kind": "user", "text": text})


def _extract_interrupt_message(payload: Any) -> str:
    if isinstance(payload, dict):
        return payload.get("message") or str(payload)
    return str(payload)


def _is_hidden_internal_message(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized.startswith("intent:")


def _is_human_message(message: Any) -> bool:
    if isinstance(message, HumanMessage):
        return True
    message_type = getattr(message, "type", "")
    return str(message_type).lower() == "human"


def _is_duplicate_bot_message(message_type: str, text: str) -> bool:
    fingerprint = f"{message_type}:{text.strip()}"
    if fingerprint in st.session_state.seen_bot_fingerprints:
        return True
    st.session_state.seen_bot_fingerprints.add(fingerprint)
    return False


def _extract_stream_message(data: Any) -> str:
    if isinstance(data, dict):
        for key in ("msg", "ui_message", "message"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""
    return str(data).strip()


def run_stream(input_or_command: Any) -> None:
    graph = get_graph()
    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    for chunk in graph.stream(
        input_or_command,
        config=config,
        stream_mode=["updates", "custom"],
        version="v2",
    ):
        kind = chunk.get("type")

        if kind == "custom":
            data = chunk.get("data", {})
            if isinstance(data, dict) and data.get("replay"):
                continue

            stream_msg = _extract_stream_message(data)
            if stream_msg:
                _append_event(stream_msg)

        elif kind == "updates":
            for node_name, diff in _unpack_updates(chunk.get("data", {})):
                if not isinstance(diff, dict):
                    continue

                messages = diff.get("messages", [])
                if isinstance(messages, list):
                    for message in messages:
                        if _is_human_message(message):
                            continue

                        content = getattr(message, "content", None)
                        if content:
                            text = str(content).strip()
                            message_type = str(getattr(message, "type", "assistant")).lower()
                            if (
                                text
                                and not _is_hidden_internal_message(text)
                                and not _is_duplicate_bot_message(message_type, text)
                            ):
                                _append_bot(text)

    snapshot = graph.get_state(config)
    st.session_state.waiting = False
    st.session_state.interrupt_payload = None

    if snapshot.next and snapshot.tasks:
        interrupts = snapshot.tasks[0].interrupts
        if interrupts:
            payload = interrupts[0].value
            st.session_state.waiting = True
            st.session_state.interrupt_payload = payload
            _append_event(f"[interrupt] {_extract_interrupt_message(payload)}")


for key, value in {
    "thread_id": f"loan-chat-{uuid.uuid4()}",
    "user_id": _generate_user_id(),
    "chat_log": [],
    "waiting": False,
    "interrupt_payload": None,
    "seen_bot_fingerprints": set(),
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

if not st.session_state.chat_log:
    _append_bot(WELCOME_MESSAGE)


with st.sidebar:
    st.markdown("### Session")
    st.caption(f"User ID: {st.session_state.user_id}")
    st.code(st.session_state.thread_id)
    if st.button("New Chat", use_container_width=True):
        st.session_state.thread_id = f"loan-chat-{uuid.uuid4()}"
        st.session_state.user_id = _generate_user_id()
        st.session_state.chat_log = []
        st.session_state.waiting = False
        st.session_state.interrupt_payload = None
        st.session_state.seen_bot_fingerprints = set()
        st.rerun()


for item in st.session_state.chat_log:
    kind = item.get("kind")
    text = item.get("text", "")

    if kind == "user":
        with st.chat_message("user"):
            st.markdown(text)
    elif kind == "bot":
        with st.chat_message("assistant"):
            st.markdown(text)
    else:
        st.markdown(f"<div style='color:#94a3b8;font-size:0.9rem;'>⚙️ {text}</div>", unsafe_allow_html=True)


if st.session_state.waiting:
    interrupt_message = _extract_interrupt_message(st.session_state.interrupt_payload)
    st.info(f"Waiting for input: {interrupt_message}")
    user_input = st.chat_input("Reply to continue...")
    if user_input:
        _append_user(user_input)
        run_stream(Command(resume=user_input))
        st.rerun()
else:
    user_input = st.chat_input("Ask or share details (e.g. 'I uploaded PAN')")
    if user_input:
        _append_user(user_input)
        run_stream({
            "user_id": _ensure_user_id(),
            "messages": [HumanMessage(content=user_input)],
        })
        st.rerun()