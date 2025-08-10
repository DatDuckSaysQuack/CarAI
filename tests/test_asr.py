import sys
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

from apps.asr.main import app
import apps.asr.main as asr_main
import apps.asr.service as service


class DummySegment:
    def __init__(self, text: str):
        self.text = text


def test_transcribe_endpoint(monkeypatch):
    def fake_get_model():
        class Model:
            def transcribe(self, audio):
                return [DummySegment("hello world")], None
        return Model()

    monkeypatch.setattr(service, "get_model", fake_get_model)
    monkeypatch.setattr(asr_main, "get_model", fake_get_model)
    monkeypatch.setattr(asr_main, "decode_audio", lambda _: np.zeros(16000, dtype="float32"))

    client = TestClient(app)
    res = client.post("/transcribe", files={"file": ("test.wav", b"fake")})
    assert res.status_code == 200
    assert res.json()["text"] == "hello world"
