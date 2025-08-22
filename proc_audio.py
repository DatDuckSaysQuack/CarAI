"""Audio capture process with AEC3 and streaming VAD."""

from __future__ import annotations

import json
import multiprocessing as mp
import queue
import time

import numpy as np
import sounddevice as sd

from audio.aec3 import AEC3
from audio.vad import StreamingVAD, rms_db
from common.bounded_queue import BoundedQueue
from common.types import AudioFrame, VadSegment

RATE = 16000
FRAME_MS = 20
SAMPLES = RATE // 1000 * FRAME_MS
BYTES = SAMPLES * 2
Q_MAX_FRAMES = 100
SEG_MAX_MS = 30000


def run(q_audio_frames: BoundedQueue, q_vad_segments: BoundedQueue, q_aec_farend: BoundedQueue,
        ctrl: mp.Manager().dict) -> None:
    """Entry point for the audio process."""

    vad = StreamingVAD()
    aec = AEC3()
    state = "MUTED"
    noise_ema = -90.0
    voiced_ms = 0
    silence_ms = 0
    seg_pcm = bytearray()
    seg_start = None

    def callback(indata, frames, time_info, status):  # pragma: no cover - realtime path
        nonlocal noise_ema, voiced_ms, silence_ms, seg_pcm, seg_start, state
        pcm = bytes(indata[:, 0].astype(np.int16))
        try:
            far = q_aec_farend.get_nowait()
        except queue.Empty:
            far = b"\x00" * BYTES
        pcm = aec.process(pcm, far)
        level = rms_db(pcm)
        aframe = AudioFrame(id=ctrl["frame_id"], ts=time.time(), rms_db=level, pcm=pcm)
        ctrl["frame_id"] += 1
        q_audio_frames.put(aframe)

        if ctrl.get("state") in {"MUTED", "ARMED"}:
            noise_ema = 0.95 * noise_ema + 0.05 * level

        if not vad.is_voiced(pcm):
            voiced = False
        else:
            voiced = True

        snr = level - noise_ema
        if not voiced:
            silence_ms += FRAME_MS
            voiced_ms = 0
        else:
            voiced_ms += FRAME_MS
            silence_ms = 0
            if seg_start is None:
                seg_start = aframe.id

        seg_pcm.extend(pcm)

        if state == "ARMED" and voiced and snr >= 6.0 and voiced_ms >= 250:
            state = "LISTENING"
            ctrl["state"] = "LISTENING"

        sil_th = ctrl.get("silence_ms", 500)
        if state == "LISTENING" and (silence_ms >= sil_th or voiced_ms >= SEG_MAX_MS):
            seg = VadSegment(
                start_id=seg_start or 0,
                end_id=aframe.id,
                dur_ms=int(voiced_ms + silence_ms),
                snr_db=float(snr),
                pcm=bytes(seg_pcm),
            )
            q_vad_segments.put(seg)
            seg_pcm.clear()
            seg_start = None
            state = "THINKING"
            ctrl["state"] = "THINKING"
            voiced_ms = 0
            silence_ms = 0

    with sd.InputStream(
        samplerate=RATE,
        channels=1,
        dtype="int16",
        blocksize=SAMPLES,
        callback=callback,
    ):
        while True:  # main health loop
            time.sleep(5)
            msg = {
                "topic": "sys.health",
                "mod": "audio",
                "q_audio": q_audio_frames.qsize(),
                "q_vad": q_vad_segments.qsize(),
                "drops": {
                    "audio": q_audio_frames.drop_ct.value,
                    "vad": q_vad_segments.drop_ct.value,
                },
                "erle_db": aec.erle(),
                "state": ctrl.get("state"),
                "ts": time.time(),
            }
            print(json.dumps(msg, separators=(",", ":")))
