import base64
import io
import os
import wave
from functools import lru_cache

import numpy as np
from faster_whisper import WhisperModel

MODEL_NAME = os.getenv("ASR_MODEL", "tiny.en")
MODELS_DIR = os.getenv("ASR_MODELS_DIR", "models/asr")

@lru_cache()
def get_model() -> WhisperModel:
    """Load and cache the ASR model."""
    return WhisperModel(MODEL_NAME, download_root=MODELS_DIR)


def decode_audio(audio_bytes: bytes) -> np.ndarray:
    """Decode 16kHz 16-bit mono WAV bytes into a float32 numpy array."""
    with wave.open(io.BytesIO(audio_bytes)) as wf:
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    return audio.astype("float32") / 32768.0


def b64_to_audio(data: str) -> np.ndarray:
    return decode_audio(base64.b64decode(data))
