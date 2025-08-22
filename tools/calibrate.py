"""Simple calibration wizard for capturing noise profile."""

from __future__ import annotations

import json
import time

import numpy as np
import sounddevice as sd

from audio.vad import rms_db

RATE = 16000
FRAME_MS = 20
SAMPLES = RATE // 1000 * FRAME_MS
DURATION = 60


def main() -> None:
    pcm = sd.rec(int(RATE * DURATION), samplerate=RATE, channels=1, dtype="int16")
    sd.wait()
    arr = pcm[:, 0].astype(np.int16)
    level = rms_db(arr.tobytes())
    profile = {
        "noise_ref_db": level,
        "vad_mode": 2,
        "base_silence_ms": 500,
        "aec": {"drift_comp": True},
    }
    with open("car_profile.json", "w") as f:
        json.dump(profile, f, indent=2)
    print(json.dumps({"topic": "calib.profile", **profile}))


if __name__ == "__main__":
    main()
