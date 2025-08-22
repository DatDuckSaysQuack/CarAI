"""Async orchestrator managing the CarAI state machine."""

from __future__ import annotations

import asyncio
import json
import multiprocessing as mp
import time
from typing import Dict

from common.types import AsrEvent, TtsEvent, VadSegment

STATES = ["MUTED", "ARMED", "LISTENING", "THINKING", "SPEAKING"]


async def orchestrate(q_vad: mp.Queue, q_asr_in: mp.Queue, q_asr_out: mp.Queue,
                      q_llm: mp.Queue, q_tts_cmd: mp.Queue, q_tts_evt: mp.Queue,
                      ctrl: Dict[str, any]) -> None:
    state = "MUTED"
    ctrl["state"] = state
    while True:
        await asyncio.sleep(0.05)
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
            q_llm.put(evt)
            continue
        try:
            tok = q_llm.get_nowait()
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


def run(q_vad: mp.Queue, q_asr_in: mp.Queue, q_asr_out: mp.Queue, q_llm: mp.Queue,
        q_tts_cmd: mp.Queue, q_tts_evt: mp.Queue, ctrl: mp.Manager().dict) -> None:
    loop = asyncio.get_event_loop()
    loop.create_task(orchestrate(q_vad, q_asr_in, q_asr_out, q_llm, q_tts_cmd, q_tts_evt, ctrl))
    loop.create_task(heartbeat(ctrl))
    loop.run_forever()
