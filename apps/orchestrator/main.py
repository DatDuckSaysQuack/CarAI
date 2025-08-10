from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Car AI Orchestrator")


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.get("/health")
async def health() -> dict[str, str]:
    """Basic liveness probe."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Echo the provided message.

    This stub mimics an interaction with a local LLM. It will be replaced with
    a real model in later iterations.
    """
    return ChatResponse(response=f"Echo: {req.message}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
