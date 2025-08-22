"""TTS process that plays audio and feeds AEC far-end."""

from __future__ import annotations

import json
import queue
import time

import numpy as np
import sounddevice as sd

from common.bounded_queue import BoundedQueue
from common.types import TtsEvent

RATE = 16000
FRAME_MS = 20
SAMPLES = RATE // 1000 * FRAME_MS


def run(q_cmd: BoundedQueue, q_events: BoundedQueue, q_aec_farend: BoundedQueue) -> None:
    """Entry point for the TTS process.

    Audio is written to a single continuous :class:`OutputStream`. Each 20 ms
    chunk is duplicated to the AEC far-end queue.
    """

    def speak(stream: sd.OutputStream, text: str) -> None:
        pcm = np.zeros(SAMPLES, dtype=np.int16)
        ts = time.time()
        q_events.put(TtsEvent(kind="start", ts=ts))
        print(json.dumps({"topic": "tts.event", "type": "start", "ts": ts}))
        words = text.split() or [""]
        for _ in words:
            stream.write(pcm)
            q_aec_farend.put(bytes(pcm))
        ts = time.time()
        q_events.put(TtsEvent(kind="stop", ts=ts))
        print(json.dumps({"topic": "tts.event", "type": "stop", "ts": ts}))

    with sd.OutputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=SAMPLES) as stream:
        while True:
            try:
                cmd = q_cmd.get(timeout=0.1)
            except queue.Empty:
                continue
            if cmd.get("kind") == "speak":
                speak(stream, cmd.get("text", ""))
