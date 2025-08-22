"""USB HID mute toggle process."""

from __future__ import annotations

import json
import time

from pynput import keyboard

from common.bounded_queue import BoundedQueue


def run(q_toggle: BoundedQueue) -> None:
    """Listen for F24 key presses and emit control.toggle events."""

    state = "off"

    def on_press(key: keyboard.Key | keyboard.KeyCode) -> None:  # pragma: no cover - hardware path
        nonlocal state
        if key == keyboard.Key.f24:
            state = "on" if state == "off" else "off"
            msg = {"topic": "control.toggle", "state": state, "ts": time.time()}
            q_toggle.put(msg)
            print(json.dumps(msg, separators=(",", ":")))

    with keyboard.Listener(on_press=on_press) as listener:  # pragma: no cover
        listener.join()
