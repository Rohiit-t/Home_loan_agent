# Home Loan React Frontend

React + Vite frontend for the Home Loan assistant with 3D hero scene (`three`, `@react-three/fiber`, `@react-three/drei`) and realtime chat via WebSocket.

## Backend connectivity

- WebSocket route expected: `/chat`
- Default URL used by frontend: `ws://127.0.0.1:8000/chat`
- Override with env var:

```bash
VITE_WS_URL=ws://127.0.0.1:8000/chat
```

The app supports these payload patterns:
- Normal chat: `{ "thread_id": "...", "message": "..." }`
- Resume interrupt: `{ "thread_id": "...", "resume": ... }`
- JSON upload: `{ "thread_id": "...", "type": "file_upload", "data": {...} }`

## Run locally

From this folder:

```bash
npm install
npm run dev
```

## Start backend (from project root)

```powershell
uvicorn app.backend.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Then open Vite URL (typically `http://127.0.0.1:5173`).

## Build

```bash
npm run build
```
