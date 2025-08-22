"""LLM process handling single in-flight requests."""

from __future__ import annotations

import json
import multiprocessing as mp
import queue
import time

from common.bounded_queue import BoundedQueue
from common.types import AsrEvent


def run(q_in: BoundedQueue, q_out: BoundedQueue, ctrl: mp.Manager().dict) -> None:
    """Consume ASR final events and emit LLM token streams."""

    while True:
        try:
            evt: AsrEvent = q_in.get(timeout=0.1)  # type: ignore[arg-type]
        except queue.Empty:
            continue
        prompt = evt.text
        first_token_ts = None
        for token in prompt.split():
            if first_token_ts is None:
                first_token_ts = time.time()
                msg = {
                    "topic": "llm.tokens",
                    "first_token_ms": int((time.time() - first_token_ts) * 1000),
                    "tps": 0.0,
                    "delta": token,
                }
            else:
                msg = {"topic": "llm.tokens", "delta": token}
            q_out.put(msg)
            print(json.dumps(msg, separators=(",", ":")))
            time.sleep(0.05)
        done = {"topic": "llm.done", "reason": "stop", "ts": time.time()}
        q_out.put(done)
        print(json.dumps(done, separators=(",", ":")))
