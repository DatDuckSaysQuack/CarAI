"""Async orchestrator managing the CarAI state machine."""

from __future__ import annotations

import asyncio
import json
import multiprocessing as mp
import time
from typing import Dict

from common.bounded_queue import BoundedQueue
from common.types import AsrEvent, TtsEvent, VadSegment

STATES = ["MUTED", "ARMED", "LISTENING", "THINKING", "SPEAKING"]


async def orchestrate(q_vad: BoundedQueue, q_asr_in: BoundedQueue, q_asr_out: BoundedQueue,
                      q_llm_in: BoundedQueue, q_llm_out: BoundedQueue,
                      q_tts_cmd: BoundedQueue, q_tts_evt: BoundedQueue,
                      q_toggle: BoundedQueue, ctrl: Dict[str, any]) -> None:
    state = "MUTED"
    ctrl["state"] = state
    while True:
        await asyncio.sleep(0.05)
        try:
            tog = q_toggle.get_nowait()
        except Exception:
            tog = None
        if tog:
            state = "ARMED" if tog.get("state") == "on" else "MUTED"
            ctrl["state"] = state
        try:
            seg: VadSegment = q_vad.get_nowait()
        except Exception:
            seg = None
        if seg:
            state = "THINKING"
            ctrl["state"] = state
            q_asr_in.put(seg)
            continue
        try:
            evt: AsrEvent = q_asr_out.get_nowait()  # type: ignore[arg-type]
        except Exception:
            evt = None
        if evt:
            q_llm_in.put(evt)
            continue
        try:
            tok = q_llm_out.get_nowait()
        except Exception:
            tok = None
        if tok and tok.get("topic") == "llm.done":
            state = "SPEAKING"
            ctrl["state"] = state
            q_tts_cmd.put({"kind": "speak", "text": ""})
        try:
            tevt: TtsEvent = q_tts_evt.get_nowait()  # type: ignore[arg-type]
        except Exception:
            tevt = None
        if tevt and tevt.kind == "stop":
            state = "ARMED"
            ctrl["state"] = state


async def heartbeat(ctrl: Dict[str, any]) -> None:
    while True:
        await asyncio.sleep(5)
        msg = {
            "topic": "sys.health",
            "mod": "orchestrator",
            "state": ctrl.get("state"),
            "ts": time.time(),
        }
        print(json.dumps(msg, separators=(",", ":")))


def run(q_vad: BoundedQueue, q_asr_in: BoundedQueue, q_asr_out: BoundedQueue,
        q_llm_in: BoundedQueue, q_llm_out: BoundedQueue,
        q_tts_cmd: BoundedQueue, q_tts_evt: BoundedQueue,
        q_toggle: BoundedQueue, ctrl: mp.Manager().dict) -> None:
    loop = asyncio.get_event_loop()
    loop.create_task(orchestrate(q_vad, q_asr_in, q_asr_out, q_llm_in, q_llm_out,
                                 q_tts_cmd, q_tts_evt, q_toggle, ctrl))
    loop.create_task(heartbeat(ctrl))
    loop.run_forever()
