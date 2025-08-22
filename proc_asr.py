"""ASR process streaming voiced segments to an ASR engine."""

from __future__ import annotations

import json
import multiprocessing as mp
import queue
import time

from common.types import AsrEvent, VadSegment


def run(q_segments: mp.Queue, q_events: mp.Queue) -> None:
    """Consume VAD segments and emit ASR events.

    This is a placeholder implementation that simply echoes the segment
    duration instead of performing real speech recognition.
    """

    while True:
        try:
            seg: VadSegment = q_segments.get(timeout=0.1)
        except queue.Empty:
            continue
        text = f"{seg.dur_ms} ms of audio"
        final = AsrEvent(kind="final", text=text, conf=0.0)
        q_events.put(final)
        msg = {"topic": "asr.final", "text": text, "conf": 0.0, "ts": time.time()}
        print(json.dumps(msg, separators=(",", ":")))
