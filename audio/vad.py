"""WebRTC VAD helpers and a streaming VAD wrapper."""

from __future__ import annotations

import collections
import math
from typing import Deque

import numpy as np
import webrtcvad


def rms_db(pcm: bytes) -> float:
    """Return RMS level in dBFS for a 16-bit PCM buffer."""

    if not pcm:
        return -math.inf
    arr = np.frombuffer(pcm, dtype=np.int16)
    if not arr.size:
        return -math.inf
    rms = np.sqrt(np.mean(np.square(arr.astype(np.float32))))
    if rms <= 0:
        return -math.inf
    return 20 * math.log10(rms / 32768.0)


class StreamingVAD:
    """Streaming VAD based on WebRTC VAD.

    The object consumes 20 ms PCM frames and exposes ``is_voiced`` to
    evaluate speech. A simple ring buffer keeps the most recent frames to
    enable leading audio capture.
    """

    def __init__(self, mode: int = 2, frame_ms: int = 20, sample_rate: int = 16000) -> None:
        self.vad = webrtcvad.Vad(mode)
        self.frame_ms = frame_ms
        self.sample_rate = sample_rate
        self.frame_bytes = sample_rate // 1000 * frame_ms * 2
        self.buffer: Deque[bytes] = collections.deque(maxlen=1000 // frame_ms)

    def is_voiced(self, pcm: bytes) -> bool:
        if len(pcm) != self.frame_bytes:
            raise ValueError("unexpected frame size")
        self.buffer.append(pcm)
        return self.vad.is_speech(pcm, self.sample_rate)
