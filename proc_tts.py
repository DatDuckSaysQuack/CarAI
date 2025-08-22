"""TTS process that plays audio and feeds AEC far-end."""

from __future__ import annotations

import json
import multiprocessing as mp
import queue
import time

import numpy as np
import sounddevice as sd

from common.types import TtsEvent

RATE = 16000
FRAME_MS = 20
SAMPLES = RATE // 1000 * FRAME_MS
BYTES = SAMPLES * 2


def run(q_cmd: mp.Queue, q_events: mp.Queue, q_aec_farend: mp.Queue) -> None:
    """Entry point for the TTS process."""

    def speak(text: str) -> None:
        pcm = np.zeros(SAMPLES, dtype=np.int16)
        ts = time.time()
        q_events.put(TtsEvent(kind="start", ts=ts))
        print(json.dumps({"topic": "tts.event", "type": "start", "ts": ts}))
        for _ in range(len(text.split())):
            sd.play(pcm, samplerate=RATE)
            q_aec_farend.put(bytes(pcm))
            sd.wait()
        ts = time.time()
        q_events.put(TtsEvent(kind="stop", ts=ts))
        print(json.dumps({"topic": "tts.event", "type": "stop", "ts": ts}))

    while True:
        try:
            cmd = q_cmd.get(timeout=0.1)
        except queue.Empty:
            continue
        if cmd.get("kind") == "speak":
            speak(cmd.get("text", ""))
