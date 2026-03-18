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
from typing import Dict, Any
import asyncio
import json
import uuid
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import logging

from app.backend.graph import build_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Home Loan Application API",
    description="WebSocket API for processing home loan applications using LangGraph workflow",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store
sessions: Dict[str, Dict[str, Any]] = {}

graph = None


@app.on_event("startup")
async def startup_event():
    """Initialize graph on startup."""
    global graph
    logger.info("Building LangGraph workflow...")
    graph = build_graph()
    logger.info("Graph built successfully!")


# ==================== Helpers ====================


def get_session_config(session_id: str, thread_id: str) -> Dict[str, Any]:
    """Get config for LangGraph execution."""
    return {
        "configurable": {
            "thread_id": thread_id
        }
    }


async def handle_create_session(websocket: WebSocket, data: dict):
    """
    Handle session creation over WebSocket.
    Expects: {"action": "create_session", "user_id": "...", "user_email": "..."}
    """
    try:
        session_id = str(uuid.uuid4())
        user_id = data.get("user_id") or f"user_{uuid.uuid4().hex[:8]}"
        thread_id = f"thread_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        session_data = {
            "session_id": session_id,
            "thread_id": thread_id,
            "user_id": user_id,
            "user_email": data.get("user_email"),
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
        sessions[session_id] = session_data

        # Initialize graph state
        config = get_session_config(session_id, thread_id)
        initial_state = {
            "user_id": user_id,
            "messages": []
        }

        user_email = data.get("user_email")
        if user_email:
            initial_state["personal_info"] = {"email": user_email}

        graph.update_state(config, initial_state, as_node="__start__")

        logger.info(f"Created session {session_id} for user {user_id}")

        await websocket.send_json({
            "type": "session_created",
            "session_id": session_id,
            "thread_id": thread_id,
            "user_id": user_id,
            "created_at": session_data["created_at"],
            "message": "Session created successfully"
        })

    except Exception as e:
        logger.error(f"Error creating session: {str(e)}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "content": f"Failed to create session: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })


async def handle_send_message(websocket: WebSocket, data: dict):
    """
    Handle user message and stream graph execution over WebSocket.
    Expects: {"action": "send_message", "session_id": "...", "message": "..."}

    Sends real-time chunks:
      {"type": "yield",    "content": "..."}   — progress/node execution messages
      {"type": "message",  "content": "..."}   — AI response messages
      {"type": "state",    "field": "...", "value": ...}  — state changes
      {"type": "complete", "data": {...}}       — graph run finished
      {"type": "error",    "content": "..."}   — error occurred
    """
    session_id = data.get("session_id")
    user_message = data.get("message", "")

    try:
        session = sessions.get(session_id)
        if not session:
            await websocket.send_json({
                "type": "error",
                "content": "Session not found",
                "timestamp": datetime.now().isoformat()
            })
            return

        session["last_activity"] = datetime.now().isoformat()

        thread_id = session["thread_id"]
        config = get_session_config(session_id, thread_id)

        # Get current state to track new messages
        snapshot = graph.get_state(config)

        input_state = {"messages": [HumanMessage(content=user_message)]}

        seen_messages = set()
        prev_msg_count = len(snapshot.values.get("messages", [])) if snapshot.values else 0

        logger.info(f"Starting stream for session {session_id}")

        # Run synchronous graph.stream in a thread and collect all chunks
        all_chunks = await asyncio.to_thread(
            lambda: list(graph.stream(input_state, config, stream_mode="values"))
        )

        for state in all_chunks:
            # Check for new messages (including yield messages)
            if "messages" in state:
                messages = state["messages"]
                if len(messages) > prev_msg_count:
                    for msg in messages[prev_msg_count:]:
                        if isinstance(msg, AIMessage):
                            content = msg.content
                            msg_hash = hash(content)

                            if msg_hash not in seen_messages:
                                seen_messages.add(msg_hash)

                                # Determine message type
                                is_yield = any(indicator in content for indicator in [
                                    "Analyzing", "Extracting", "Processing",
                                    "Checking", "Calculating", "Saving",
                                    "Preparing", "Sending", "Finding information"
                                ]) and len(content) < 150

                                chunk_type = "yield" if is_yield else "message"

                                await websocket.send_json({
                                    "type": chunk_type,
                                    "content": content,
                                    "timestamp": datetime.now().isoformat()
                                })

                    prev_msg_count = len(messages)

            # Send state updates for key changes
            if "intent" in state and state["intent"]:
                await websocket.send_json({
                    "type": "state",
                    "field": "intent",
                    "value": state["intent"]
                })

            if "all_documents_uploaded" in state and state.get("all_documents_uploaded"):
                await websocket.send_json({
                    "type": "state",
                    "field": "all_documents_uploaded",
                    "value": True
                })

            if "all_loan_details_provided" in state and state.get("all_loan_details_provided"):
                await websocket.send_json({
                    "type": "state",
                    "field": "all_loan_details_provided",
                    "value": True
                })

            if "application_saved" in state and state.get("application_saved"):
                await websocket.send_json({
                    "type": "state",
                    "field": "application_saved",
                    "value": True
                })

        # Get final state
        final_snapshot = await asyncio.to_thread(lambda: graph.get_state(config))

        await websocket.send_json({
            "type": "complete",
            "data": {
                "current_stage": final_snapshot.values.get("current_stage") if final_snapshot.values else None,
                "is_paused": bool(final_snapshot.next),
                "next_nodes": list(final_snapshot.next) if final_snapshot.next else [],
                "paused_reason": final_snapshot.values.get("paused_reason") if final_snapshot.values else None,
                "documents_uploaded": len(final_snapshot.values.get("uploaded_documents", {})) if final_snapshot.values else 0,
                "all_documents_uploaded": final_snapshot.values.get("all_documents_uploaded", False) if final_snapshot.values else False,
                "all_loan_details_provided": final_snapshot.values.get("all_loan_details_provided", False) if final_snapshot.values else False,
                "application_saved": final_snapshot.values.get("application_saved", False) if final_snapshot.values else False
            }
        })

        logger.info(f"Stream completed for session {session_id}")

    except Exception as e:
        logger.error(f"Error in handle_send_message: {str(e)}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "content": str(e),
            "timestamp": datetime.now().isoformat()
        })


# ==================== Endpoints ====================


@app.get("/health")
async def health_check():
    """Health check endpoint (HTTP — used by Streamlit before opening WebSocket)."""
    return {
        "status": "healthy",
        "graph_status": "loaded" if graph else "not_loaded",
        "active_sessions": len(sessions)
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Single WebSocket endpoint for all client-server communication.

    Client sends JSON messages with an "action" field:
      - {"action": "create_session", "user_id": "...", "user_email": "..."}
      - {"action": "send_message", "session_id": "...", "message": "..."}

    Server responds with JSON messages with a "type" field:
      - {"type": "session_created", ...}
      - {"type": "yield", "content": "..."}
      - {"type": "message", "content": "..."}
      - {"type": "state", "field": "...", "value": ...}
      - {"type": "complete", "data": {...}}
      - {"type": "error", "content": "..."}
    """
    await websocket.accept()
    logger.info("WebSocket connection established")

    try:
        while True:
            # Wait for client message
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid JSON",
                    "timestamp": datetime.now().isoformat()
                })
                continue

            action = data.get("action")

            if action == "create_session":
                await handle_create_session(websocket, data)

            elif action == "send_message":
                await handle_send_message(websocket, data)

            else:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Unknown action: {action}",
                    "timestamp": datetime.now().isoformat()
                })

    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "content": str(e),
                "timestamp": datetime.now().isoformat()
            })
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
