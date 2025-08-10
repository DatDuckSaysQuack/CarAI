from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .service import b64_to_audio, decode_audio, get_model

app = FastAPI(title="Car AI ASR")


class TranscribeResponse(BaseModel):
    text: str


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(file: UploadFile = File(...)) -> TranscribeResponse:
    audio = decode_audio(await file.read())
    segments, _ = get_model().transcribe(audio)
    text = "".join(seg.text for seg in segments).strip()
    return TranscribeResponse(text=text)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    try:
        data = await ws.receive_text()
        audio = b64_to_audio(data)
        segments, _ = get_model().transcribe(audio)
        text = "".join(seg.text for seg in segments).strip()
        await ws.send_json({"text": text})
    except WebSocketDisconnect:
        pass
    finally:
        await ws.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
