from fastapi import FastAPI, WebSocket
import asyncio
import json

app = FastAPI()


@app.websocket("/chat")
async def chat_endpoint(websocket: WebSocket):

    await websocket.accept()

    while True:

        # receive user query
        data = await websocket.receive_text()
        payload = json.loads(data)

        user_message = payload["message"]

        print("User:", user_message)

        # simulate graph execution streaming
        responses = [
            "Intent classified...\n",
            "Collecting loan information...\n",
            "Calculating financial risk...\n",
            "Calculating EMI...\n",
            "Saving application...\n",
            "Loan application processed successfully."
        ]

        for msg in responses:

            await websocket.send_text(
                json.dumps({"message": msg})
            )

            await asyncio.sleep(1)

        # final message
        await websocket.send_text(
            json.dumps({
                "message": "\nDone.",
                "end": True
            })
        )