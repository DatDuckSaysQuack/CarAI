import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from apps.orchestrator.main import app

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_chat_echo():
    res = client.post("/chat", json={"message": "hi"})
    assert res.status_code == 200
    assert res.json()["response"] == "Echo: hi"
