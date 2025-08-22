from __future__ import annotations

import multiprocessing as mp

from common.bounded_queue import BoundedQueue
import proc_asr
import proc_audio
import proc_llm
import proc_orchestrator
import proc_toggle
import proc_tts


def main() -> None:
    manager = mp.Manager()
    ctrl = manager.dict()
    ctrl["frame_id"] = 0

    q_audio = BoundedQueue(100)
    q_vad = BoundedQueue(10)
    q_aec_farend = BoundedQueue(100)
    q_asr_in = BoundedQueue(10)
    q_asr_out = BoundedQueue(50)
    q_llm_in = BoundedQueue(50)
    q_llm_out = BoundedQueue(50)
    q_tts_cmd = BoundedQueue(50)
    q_tts_evt = BoundedQueue(50)
    q_toggle = BoundedQueue(10)

    procs = [
        mp.Process(target=proc_audio.run, args=(q_audio, q_vad, q_aec_farend, ctrl)),
        mp.Process(target=proc_asr.run, args=(q_asr_in, q_asr_out)),
        mp.Process(target=proc_llm.run, args=(q_llm_in, q_llm_out, ctrl)),
        mp.Process(target=proc_tts.run, args=(q_tts_cmd, q_tts_evt, q_aec_farend)),
        mp.Process(target=proc_orchestrator.run,
                   args=(q_vad, q_asr_in, q_asr_out, q_llm_in, q_llm_out,
                         q_tts_cmd, q_tts_evt, q_toggle, ctrl)),
        mp.Process(target=proc_toggle.run, args=(q_toggle,)),
    ]

    for p in procs:
        p.start()

    for p in procs:
        p.join()


if __name__ == "__main__":
    main()
