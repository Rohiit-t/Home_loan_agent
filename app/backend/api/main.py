import json
import logging
import uuid
import hashlib
from typing import Any, Dict, Iterable, Tuple

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from starlette.websockets import WebSocketState
from fastapi.middleware.cors import CORSMiddleware

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

email_to_phone: Dict[str, str] = {}


class SavePhoneRequest(BaseModel):
    uid: str
    email: str
    phone_number: str


@app.post("/save-phone")
async def save_phone(req: SavePhoneRequest):
    """Store a verified phone number mapped to a user's email."""
    email_to_phone[req.email.lower()] = req.phone_number
    logger.info("Phone saved: email=%s phone=%s uid=%s", req.email, req.phone_number, req.uid)
    return {"status": "ok", "email": req.email, "phone_number": req.phone_number}


@app.get("/get-phone")
async def get_phone(email: str):
    """Check if an email has a verified phone number."""
    phone = email_to_phone.get(email.lower())
    if phone:
        return {"status": "ok", "phone_number": phone}
    return {"status": "not_found", "phone_number": None}

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
    email = str(payload.get("email") or "").strip()

    personal_info = {}
    if email:
        personal_info["email"] = email
        phone = email_to_phone.get(email.lower())
        if phone:
            personal_info["phone"] = phone

    if payload_type == "file_upload":
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ValueError("file_upload payload requires 'data' as JSON object")
        result = {
            "user_id": user_id,
            "user_query": None,
            "uploaded_docs": data,
            "intent": None,
        }
        if personal_info:
            result["personal_info"] = personal_info
        return result

    if payload_type == "text":
        message = str(payload.get("message") or "").strip()
        if not message:
            raise ValueError("text payload requires non-empty 'message'")
        result = {
            "user_id": user_id,
            "user_query": message,
            "uploaded_docs": None,
            "intent": None,
            "messages": [HumanMessage(content=message)],
        }
        if personal_info:
            result["personal_info"] = personal_info
        return result

    raise ValueError("payload type must be either 'text' or 'file_upload'")


def _get_pending_interrupt_payload(thread_id: str) -> Any:
    """Return current pending interrupt payload for a thread, if any."""
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)

    tasks = getattr(snapshot, "tasks", None) or []
    for task in tasks:
        interrupts = getattr(task, "interrupts", None) or []
        if interrupts:
            return interrupts[0].value

    return None


async def run_graph(ws: WebSocket, graph_input: Any, thread_id: str) -> str:
    logger.info("[thread=%s] graph execution started", thread_id)
    config = {"configurable": {"thread_id": thread_id}}

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
                current_stage = diff.get("current_stage")
                stage_value = current_stage if isinstance(current_stage, str) and current_stage.strip() else None

                new_messages = []
                for item in bot_messages:
                    if item["id"] not in sent_msg_ids:
                        sent_msg_ids.add(item["id"])
                        new_messages.append(item)

                if not new_messages and not stage_value:
                    continue

                update_payload = {
                    "node": node_name,
                    "keys": list(diff.keys()),
                    "messages": [item["text"] for item in new_messages],
                    "bot_messages": new_messages,
                }
                if stage_value:
                    update_payload["current_stage"] = stage_value

                await ws.send_json({
                    "event": "updates",
                    "data": update_payload,
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

                pending_interrupt = _get_pending_interrupt_payload(thread_id)
                if pending_interrupt is None:
                    logger.warning(
                        "[conn=%s][thread=%s] stale resume ignored: no pending interrupt",
                        connection_id,
                        thread_id,
                    )
                    await ws.send_json({
                        "event": "error",
                        "data": {
                            "message": (
                                "This chat step is no longer active on the server (likely due to a backend reload). "
                                "Please click 'Start New Application' to continue."
                            )
                        },
                    })
                    await ws.send_json({"event": "end", "data": {"result": "stale_resume"}})
                    continue

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
