"""
FastAPI Main Application for Home Loan LangGraph System

WebSocket-based real-time API that handles:
- Session management for loan applications
- Streaming responses with real-time yield messages
- Interrupt handling for human-in-the-loop workflows
- State management using LangGraph checkpoints
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict, Iterable, Tuple
from langgraph.types import Command
from starlette.websockets import WebSocketState
import asyncio
import hashlib
import json
import uuid
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import logging

from app.backend.graph import build_graph


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = build_graph()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("home-loan-ws")


def _unpack_updates(data: Any) -> Iterable[Tuple[str, Any]]:
    if isinstance(data, list):
        for item in data:
            if isinstance(item, (tuple, list)) and len(item) == 2 and item[0] != "__interrupt__":
                yield item[0], item[1]
    elif isinstance(data, dict):
        for key, value in data.items():
            if key != "__interrupt__":
                yield key, value


def _is_human_message(message: Any) -> bool:
    if isinstance(message, HumanMessage):
        return True
    message_type = getattr(message, "type", "")
    return str(message_type).lower() == "human"


def _extract_bot_messages(diff: Dict[str, Any], node_name: str) -> list[Dict[str, str]]:
    """Extract bot (non-human) messages from a node diff.

    Always generates a *deterministic* ID from the node name + content hash
    so the frontend can reliably deduplicate.  LangChain message IDs are
    random UUIDs and must NOT be forwarded as-is.
    """
    output: list[Dict[str, str]] = []
    messages = diff.get("messages", [])

    if not isinstance(messages, list):
        return output

    for message in messages:
        if _is_human_message(message):
            continue
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            text = content.strip()
            digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
            msg_id = f"{node_name}:{digest}"
            output.append({"id": msg_id, "text": text})

    return output


def _normalize_event_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    user_id = str(payload.get("user_id") or "").strip() or f"USR-{uuid.uuid4()}"
    payload_type = str(payload.get("type") or "").strip().lower()

    if payload_type == "file_upload":
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ValueError("file_upload payload requires 'data' as JSON object")
        return {
            "user_id": user_id,
            "user_query": None,
            "uploaded_docs": data,
            "intent": None,
        }

    if payload_type == "text":
        message = str(payload.get("message") or "").strip()
        if not message:
            raise ValueError("text payload requires non-empty 'message'")
        return {
            "user_id": user_id,
            "user_query": message,
            "uploaded_docs": None,
            "intent": None,
            "messages": [HumanMessage(content=message)],
        }

    raise ValueError("payload type must be either 'text' or 'file_upload'")


async def run_graph(ws: WebSocket, graph_input: Any, thread_id: str) -> str:
    logger.info("[thread=%s] graph execution started", thread_id)
    config = {"configurable": {"thread_id": thread_id}}

    # Per-turn dedup: track message IDs already sent in THIS streaming turn
    # so the same bot message is never forwarded twice.
    sent_msg_ids: set[str] = set()

    async for chunk in graph.astream(
        graph_input,
        config=config,
        stream_mode=["updates", "custom"],
        version="v2",
    ):
        kind = chunk.get("type")

        if kind == "custom":
            await ws.send_json({
                "event": "custom",
                "data": chunk.get("data", {}),
            })

        elif kind == "updates":
            for node_name, diff in _unpack_updates(chunk.get("data", {})):
                if not isinstance(diff, dict):
                    continue

                bot_messages = _extract_bot_messages(diff, node_name)

                # Filter out messages already sent in this turn
                new_messages = []
                for item in bot_messages:
                    if item["id"] not in sent_msg_ids:
                        sent_msg_ids.add(item["id"])
                        new_messages.append(item)

                if not new_messages:
                    continue

                await ws.send_json({
                    "event": "updates",
                    "data": {
                        "node": node_name,
                        "keys": list(diff.keys()),
                        "messages": [item["text"] for item in new_messages],
                        "bot_messages": new_messages,
                    },
                })

    snapshot = graph.get_state(config)

    if snapshot.next and snapshot.tasks:
        interrupts = snapshot.tasks[0].interrupts
        if interrupts:
            payload = interrupts[0].value
            await ws.send_json({
                "event": "interrupt",
                "data": payload,
            })
            logger.info("[thread=%s] interrupt emitted", thread_id)
            return "interrupt"

    final_values = snapshot.values or {}
    await ws.send_json({
        "event": "done",
        "data": {
            "user_id": final_values.get("user_id"),
            "current_stage": final_values.get("current_stage"),
            "all_documents_uploaded": final_values.get("all_documents_uploaded"),
            "all_loan_details_provided": final_values.get("all_loan_details_provided"),
            "email_sent": final_values.get("email_sent"),
        },
    })
    logger.info("[thread=%s] graph execution completed", thread_id)
    return "done"


@app.websocket("/chat")
async def chat(ws: WebSocket) -> None:
    connection_id = str(uuid.uuid4())[:8]
    await ws.accept()
    client = f"{ws.client.host}:{ws.client.port}" if ws.client else "unknown"
    logger.info("[conn=%s] websocket connected from %s", connection_id, client)

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)

            thread_id = str(msg.get("thread_id") or "loan-1")
            message_type = "resume" if "resume" in msg else "message"
            logger.info("[conn=%s][thread=%s] received %s payload", connection_id, thread_id, message_type)

            if "resume" in msg:
                resume_payload = msg["resume"]
                user_id = str(msg.get("user_id") or "").strip() or f"USR-{uuid.uuid4()}"
                if isinstance(resume_payload, dict):
                    resume_payload = {**resume_payload, "user_id": user_id}
                    normalized_resume = _normalize_event_payload(resume_payload)
                else:
                    text = str(resume_payload or "").strip()
                    normalized_resume = {
                        "user_id": user_id,
                        "user_query": text,
                        "uploaded_docs": None,
                        "intent": None,
                        "messages": [HumanMessage(content=text)] if text else [],
                    }
                result = await run_graph(ws, Command(resume=normalized_resume), thread_id)
            else:
                normalized = _normalize_event_payload(msg)
                result = await run_graph(ws, normalized, thread_id)

            await ws.send_json({"event": "end", "data": {"result": result}})
            logger.info("[conn=%s][thread=%s] stream ended with result=%s", connection_id, thread_id, result)

    except ValueError as exc:
        logger.warning("[conn=%s] invalid payload: %s", connection_id, exc)
        if ws.application_state == WebSocketState.CONNECTED:
            await ws.send_json({
                "event": "error",
                "data": {"message": str(exc)},
            })
    except WebSocketDisconnect:
        logger.info("[conn=%s] websocket disconnected by client", connection_id)
    except Exception as exc:
        logger.exception("[conn=%s] websocket handler error", connection_id)
        if ws.application_state == WebSocketState.CONNECTED:
            await ws.send_json({
                "event": "error",
                "data": {"message": str(exc)},
            })
    finally:
        if (
            ws.client_state == WebSocketState.CONNECTED
            and ws.application_state == WebSocketState.CONNECTED
        ):
            try:
                await ws.close()
            except RuntimeError:
                pass
        logger.info("[conn=%s] websocket closed", connection_id)
