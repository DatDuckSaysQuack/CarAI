from __future__ import annotations

"""Pydantic models shared across CarAI processes.

These models mirror the message schema defined in AGENTS.md.
"""

from pydantic import BaseModel


class AudioFrame(BaseModel):
    """20 ms chunk of near-end audio."""

    id: int
    ts: float
    rms_db: float
    pcm: bytes


class VadSegment(BaseModel):
    """Voiced segment emitted by the VAD."""

    start_id: int
    end_id: int
    dur_ms: int
    snr_db: float
    pcm: bytes


class AsrEvent(BaseModel):
    """Partial or final ASR result."""

    kind: str  # "partial" | "final"
    text: str
    conf: float


class TtsEvent(BaseModel):
    """TTS start/stop notification."""

    kind: str  # "start" | "stop"
    ts: float
