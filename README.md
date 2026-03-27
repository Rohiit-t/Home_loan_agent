# Home Loan LangGraph 🏠

AI-assisted home loan workflow with:
- **LangGraph backend** for stateful multi-step processing
- **FastAPI WebSocket API** for real-time streaming events
- **React + Vite frontend** for interactive chat UI

The system supports document intake, text extraction, loan detail collection, risk assessment, EMI breakdown, persistence (JSON + PostgreSQL), and async email notifications.

---

## Tech Stack

### Backend
- Python 3.10+
- LangGraph + LangChain
- FastAPI + Uvicorn (WebSocket endpoint)
- Pydantic
- PostgreSQL (`psycopg2-binary`)

### Frontend
- React 19
- Vite
- Native WebSocket client
- Three.js (`@react-three/fiber`, `@react-three/drei`) for landing visuals

---

## Current Architecture

### Core graph
- Graph builder: `app/backend/graph/main.py`
- State schema: `app/backend/graph/state.py`
- Main node logic: `app/backend/graph/nodes/agent.py`
- Document subgraph: `app/backend/graph/nodes/document_processing.py`

### API layer
- FastAPI WebSocket server: `app/backend/api/main.py`
- WebSocket route: `/chat`
- Streams:
  - `custom` events (status/warnings)
  - `updates` events (node updates + bot messages)
  - `interrupt` events (HITL pause)
  - `done` and `end`

### Frontend
- React app root: `app/frontend/react-frontend/src/App.jsx`
- WebSocket hook: `app/frontend/react-frontend/src/hooks/useWebSocket.js`
- Shows distinct completion/failure bottom banners:
  - `completed` → success banner
  - `failed_max_retries` → red failure banner

---

## Workflow Overview

1. `intent_classifier`
2. Route to one of:
   - `irrelevant_handler`
   - `homeloan_query`
   - `document_processing`
   - `text_info`
3. `state_evaluator`
4. If docs missing → `interrupt_handler` loop
5. If docs complete → `loan_details`
6. If loan details complete → `financial_risk`
7. `emi_calculator`
8. `save_json`
9. `save_db`
10. `email_notification`
11. `END`

---

## Retry & Failure Guardrails

The graph now has explicit max-retry guards to prevent infinite loops.

### Document collection loop
- Tracks `doc_retry_count`
- Max retries: `3`
- Invalid/irrelevant document attempts increment counter
- Any meaningful progress resets counter
- On max retries:
  - `current_stage = "failed_max_retries"`
  - Graph routes to `END`
  - Frontend shows failure banner with “Start New Application”

### Loan details loop
- Tracks `retry_count`
- Max retries: `3`
- If LLM extracts at least one valid loan detail, retry is **not** incremented
- Only irrelevant/invalid replies increment retry
- On max retries:
  - `current_stage = "failed_max_retries"`
  - Graph routes to `END`
  - Frontend shows failure banner with “Start New Application”

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (optional but recommended for DB persistence)
- OpenRouter API key

---

## Setup

### 1) Clone and create Python environment (Windows PowerShell)

```powershell
git clone <your-repo-url>
cd "Home loan-langGraph"
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2) Install backend dependencies

```powershell
pip install -r app/static/requirements.txt
```

### 3) Configure API key

Create `.env` in project root:

```env
OPENROUTER_API_KEY=your_openrouter_api_key
```

### 4) Frontend setup

```powershell
cd app/frontend/react-frontend
npm install
```

---

## Run the Project

### Terminal 1: Start backend API

```powershell
cd "Home loan-langGraph"
.\venv\Scripts\Activate.ps1
uvicorn app.backend.api.main:app --reload
```

Backend listens on `http://127.0.0.1:8000` and WebSocket on `ws://127.0.0.1:8000/chat`.

### Terminal 2: Start React frontend

```powershell
cd "Home loan-langGraph\app\frontend\react-frontend"
npm run dev
```

Open the Vite URL shown in terminal (usually `http://localhost:5173`).

---

## WebSocket Payload Format

### Send text

```json
{
  "type": "text",
  "message": "I need a loan of 50 lakhs for 20 years",
  "user_id": "USR-...",
  "thread_id": "loan-chat-..."
}
```

### Send document JSON

```json
{
  "type": "file_upload",
  "data": { "doc_type": "pan", "...": "..." },
  "user_id": "USR-...",
  "thread_id": "loan-chat-..."
}
```

### Resume interrupt

```json
{
  "resume": { "type": "text", "message": "Down payment is 10 lakhs" },
  "user_id": "USR-...",
  "thread_id": "loan-chat-..."
}
```

---

## Configuration

Edit `app/static/config.py` for:
- `MANDATORY_DOCS`
- `LTV_THRESHOLD`, `FOIR_THRESHOLD`, `MIN_CIBIL`
- `DEFAULT_INTEREST_RATE`
- `DATABASE_URL`
- SMTP settings for email notifications

> Note: move secrets (SMTP credentials, DB URL) to environment variables for production use.

---

## Testing

Project tests are in `app/tests/`.

Run all tests:

```powershell
cd "Home loan-langGraph"
.\venv\Scripts\Activate.ps1
pytest app/tests -q
```

Run a specific test:

```powershell
pytest app/tests/test_loan_details_interrupt.py -q
```

---

## Utility: Graph Visualization

Generate graph visualization/ASCII/Mermaid output:

```powershell
cd "Home loan-langGraph"
.\venv\Scripts\Activate.ps1
python visualize_graph.py
```

This can generate `graph_visualization.png` in project root.

---

## Project Structure

```text
Home loan-langGraph/
├── app/
│   ├── backend/
│   │   ├── api/
│   │   │   └── main.py
│   │   ├── graph/
│   │   │   ├── main.py
│   │   │   ├── state.py
│   │   │   └── nodes/
│   │   │       ├── agent.py
│   │   │       └── document_processing.py
│   │   ├── services/
│   │   │   └── email_services.py
│   │   └── util/
│   │       └── model.py
│   ├── frontend/
│   │   ├── react-frontend/
│   │   │   ├── src/
│   │   │   └── package.json
│   │   ├── src.py
│   │   └── terminal_based_frontend.py
│   ├── static/
│   │   ├── config.py
│   │   └── requirements.txt
│   └── tests/
├── saved_docs/
├── visualize_graph.py
└── README.md
```

---

## Notes

- Root README now reflects the **current React + FastAPI flow** (not only Streamlit).
- Legacy/alternate frontends still exist under `app/frontend/` (`src.py`, `terminal_based_frontend.py`, `without_api.py`).
- The backend uses LangGraph checkpointer memory for thread-scoped conversation state.

---

## License

Internal project / custom implementation.
