from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Car AI TTS")


class SpeakRequest(BaseModel):
    text: str


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/speak")
async def speak(_: SpeakRequest) -> dict[str, str]:
    """Pretend to convert text to speech."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
