AGENTS.md — PLAIN TEXT SPEC FOR CODEX
Version: 1.0
Companion to: CARAI VOICE SUBSYSTEM — PLAIN TEXT SPEC

PURPOSE
Define every agent/process in the CarAI system, its inputs/outputs, contracts, events, health signals, and startup/shutdown order. Keep messages simple JSON over a local event bus (multiprocessing queues or MQTT). Everything below is copy-paste friendly (no markup).

GLOBAL PRINCIPLES

Single owner for state transitions: the ORCHESTRATOR.

Processes are isolated (multiprocessing). Audio I/O runs in its own process.

All inter-process messages are single-line JSON. No binary except PCM in base64 or raw bytes on internal queues.

Queues are bounded with drop-oldest policy. Every drop increments a counter.

Health telemetry every 5 s from each agent.

Safety-first: when vehicle is moving, replies are capped and chatter is reduced.

EVENT BUS AND TOPICS

Transport options:

Local mode: multiprocessing.Queues (default)

MQTT mode (optional): localhost broker; topics mirror below

Topic names (strings in the "topic" field of JSON):
audio.frame
vad.segment
asr.partial
asr.final
llm.request
llm.tokens
llm.done
tts.command
tts.event
vision.frame.meta
vision.sign
vision.lane
dms.state
obd.pid
control.toggle
control.state
sys.health
memory.query
memory.results
memory.save
diary.entry
safety.alert
calib.profile
config.update

All timestamps are float seconds (time.time()). All durations in ms.

ORCHESTRATOR AGENT

Role:

Single asyncio loop. Owns the conversation state machine and routes events.

Applies driving guardrails (token caps, barge-in policy).

Maintains global config (loaded from car_profile.json + overrides).

Inputs:

asr.final, llm.tokens, llm.done, tts.event, vad.segment, safety.alert, obd.pid, vision.sign, dms.state, control.toggle, sys.health, memory.results

Outputs:

llm.request, tts.command, control.state, memory.query, memory.save, diary.entry, sys.health

State machine (no wake word; USB toggle):

States: MUTED -> ARMED -> LISTENING -> THINKING -> SPEAKING -> ARMED

Events: toggle_on/off, speech_start/end, asr_final, llm_first_token, llm_done, tts_start/stop, safety_timeout

Safety caps: max_listen_ms=30000; while driving (speed_kmh>0) cap llm max_tokens<=150

Config keys in memory:

noise_ref_db, base_silence_ms, end_k, vad_mode, speed_kmh, driving(bool)

Health fields (every 5 s):
{ "topic":"sys.health","mod":"orchestrator","state":"ARMED","q_audio":12,"q_vad":0,"drops":{"audio":0,"vad":0},"first_token_ms":620 }

AUDIO AGENT (proc_audio)

Role:

Capture 20 ms PCM frames at 16 kHz mono

AEC3 near/far processing

Streaming VAD and segmenting

Emits audio.frame and vad.segment

Tracks ERLE dB

Inputs:

q_aec_farend (20 ms TTS chunks), control.state (armed/muted), config.update

Outputs:

audio.frame, vad.segment, sys.health

Key constants:

RATE=16000, FRAME_MS=20, FRAME_SAMPLES=320, FRAME_BYTES=640

q_audio_frames max 100 (2 s), q_vad_segments max 10

Start-of-speech: >=250 ms voiced AND SNR>=+6 dB

End-of-speech: silence_ms = clamp(500 + k*(noise_floor - ref), 300, 1500); +200 ms when speed>80

Health:
{ "topic":"sys.health","mod":"audio","erle_db":22.3,"q_audio":10,"q_vad":0,"drops":{"audio":0,"vad":0} }

ASR AGENT (proc_asr)

Role:

Consume vad.segment, stream audio to ASR engine

Emit asr.partial and asr.final

Inputs:

vad.segment, config.update

Outputs:

asr.partial, asr.final, sys.health

Contract:

asr.partial is optional; asr.final must always be emitted per segment

Include confidence 0..1

Example:
{ "topic":"asr.final","text":"navigate to home","conf":0.86,"ts":1724341112.12 }

Health:
{ "topic":"sys.health","mod":"asr","segments_in":12,"partials_out":8,"finals_out":12 }

LLM AGENT (proc_llm)

Role:

Single in-flight request worker

Build prompt (optionally retrieves memory), stream tokens, respect token cap when driving

Inputs:

llm.request (from orchestrator), memory.results, config.update

Outputs:

llm.tokens (delta stream), llm.done, memory.query (optional), sys.health

Contract:

First streamed token timestamp reported as llm_first_token_ms

When driving==true, enforce max_tokens<=150

Example request:
{ "topic":"llm.request","prompt":"...", "max_tokens":150, "context":[ {"quote":"...","ts":...} ] }

Health:
{ "topic":"sys.health","mod":"llm","first_token_ms":620,"tps":12.4,"inflight":0 }

TTS AGENT (proc_tts)

Role:

Convert text to 20 ms PCM chunks

Play audio and duplicate chunks to AEC far-end queue

Emit tts.event start/stop

Inputs:

tts.command

Outputs:

tts.event, sys.health, q_aec_farend (raw frames to audio agent)

Contract:

For "speak" commands, must emit start then stop

16 kHz S16LE 20 ms frame cadence

Example:
Input: { "topic":"tts.command","kind":"speak","text":"Okay, setting a timer." }
Output: { "topic":"tts.event","type":"start","ts":... } then chunks then { "topic":"tts.event","type":"stop","ts":... }

Health:
{ "topic":"sys.health","mod":"tts","queue":0,"speaking":false }

VISION AGENT (proc_vision)

Role:

Acquire frames from cameras (USB UVC)

Run detection/segmentation on Hailo-8/8L or iGPU

Emit normalized events (signs, lanes, obstacles)

Inputs:

config.update

Outputs:

vision.frame.meta, vision.sign, vision.lane, sys.health

Normalization for signs:
{ "topic":"vision.sign","kind":"speed_limit","value":50,"conf":0.92,"bbox":[x,y,w,h],"ts":... }

Normalization for driver monitoring:
{ "topic":"dms.state","eyes_on":true,"blink_rate_hz":0.23,"perclos":0.18,"distracted":false,"ts":... }

Health:
{ "topic":"sys.health","mod":"vision","fps":30.2,"backend":"hailo8l","drops":0 }

OBD AGENT (proc_obd)

Role:

Read vehicle speed, RPM, and other PIDs via OBD-II

Provide speed_kmh to orchestrator and audio (for adaptive hangover)

Inputs:

config.update

Outputs:

obd.pid, sys.health

Message:
{ "topic":"obd.pid","pid":"SPEED","value_kmh":97.2,"ts":... }

Health:
{ "topic":"sys.health","mod":"obd","pids": ["SPEED","RPM"],"last":1724342222.33 }

MEMORY AGENT (proc_memory)

Role:

Ephemeral session scratchpad (notified by orchestrator) and searchable transcript store

Vector search or SQLite FTS over transcripts

Strict write policy for long-term saves

Inputs:

memory.query, memory.save, asr.final, config.update

Outputs:

memory.results, sys.health

Contracts:

Do not auto-save rambling; store only when orchestrator flags a category (preference, constraint, contact, todo, car fact, safety note) or user says “bookmark”

Transcript store keeps full text with timestamps for RAG

Examples:
Query: { "topic":"memory.query","q":"tire pressure we discussed last week","k":5 }
Results: { "topic":"memory.results","hits":[ {"quote":"...","ts":...}, ... ] }

Health:
{ "topic":"sys.health","mod":"memory","docs":1024,"index_size_mb":85 }

SAFETY AGENT (proc_safety)

Role:

Evaluate signals (speed, dms.state, vision.sign) and enforce guardrails

Emit safety.alert and recommendations to orchestrator

Inputs:

obd.pid, dms.state, vision.sign, config.update

Outputs:

safety.alert, sys.health

Examples:
{ "topic":"safety.alert","kind":"distracted","level":"warn","detail":"gaze off road 2.1s","ts":... }
{ "topic":"safety.alert","kind":"speed_limit","level":"info","detail":"limit 50, current 62","ts":... }

Health:
{ "topic":"sys.health","mod":"safety","alerts_5m":2 }

DIARY/LOG AGENT (proc_diary)

Role:

Append session events and summaries (short, structured)

Rotate logs, persist health snapshots and acceptance-test results

Inputs:

diary.entry, sys.health (from others)

Outputs:

none (writes to disk)

Entry:
{ "topic":"diary.entry","kind":"session","text":"Session 7: streaming VAD stable; AEC wired; barge-in at 180 ms.","ts":... }

CONTROL AGENT (proc_control)

Role:

USB HID listener for mic-mute toggle; LED/beeper feedback

Emits control.toggle and mirrors system mute

Inputs:

none (low-level HID hook), control.state (to sync LED)

Outputs:

control.toggle, sys.health

Example:
{ "topic":"control.toggle","state":"on","ts":... }
{ "topic":"control.toggle","state":"off","ts":... }

CALIBRATION AGENT (proc_calib)

Role:

One-minute wizard to learn noise_ref_db, base_silence_ms, vad_mode

Writes car_profile.json and emits calib.profile

Inputs:

audio.frame (passive), config.update

Outputs:

calib.profile, diary.entry

Profile:
{ "topic":"calib.profile","noise_ref_db":-45.0,"base_silence_ms":500,"vad_mode":2,"aec":{"drift_comp":true} }

CONFIGURATION AND OVERRIDES

Config precedence:

car_profile.json (generated by calibration)

environment variables (e.g., CARAI_MAX_LISTEN_MS, CARAI_REPLY_TOKENS_WHILE_MOVING)

runtime config.update events

config.update example:
{ "topic":"config.update","keys":{"base_silence_ms":600,"end_k":18,"reply_tokens_drive":120},"ts":... }

STARTUP ORDER AND SHUTDOWN

Startup sequence:

DIARY, MEMORY, SAFETY, OBD start

ORCHESTRATOR starts asyncio loop (state=MUTED)

CONTROL starts; emits initial control.state (muted)

AUDIO starts (AEC3 ready), TTS starts (idle), ASR starts (idle), LLM starts (idle)

VISION starts (cameras), CALIB may run on demand

ORCHESTRATOR publishes sys.health heartbeat

Graceful shutdown:

ORCHESTRATOR sends stop signals; TTS finishes current utterance; AUDIO closes stream; queues drained or dropped with counters logged

DIARY writes final summary

ERROR HANDLING AND WATCHDOGS

Each agent must catch exceptions, emit sys.health with {"error":"string"} then attempt restart after backoff (1, 2, 4, 8 s)

ORCHESTRATOR monitors last heartbeat time per agent; if >10 s, emit safety.alert kind="agent_down" and try restart

If AUDIO dies, force MUTED state and alert

If TTS is stuck >5 s after llm.done, send tts.stop and log "tts_barge_timeout"

PRIVACY AND DATA RETENTION

Do not store raw audio by default

Store transcripts in rolling files (max N days) unless user says “bookmark”

When user says “forget that”, ORCHESTRATOR issues memory.delete (optional) and diary entry

PERFORMANCE TARGETS (P95)

Capture -> VAD decision latency < 150 ms

Barge-in: TTS stop < 200 ms after speech start

Time to first token (short replies) <= 700 ms

ERLE >= 20 dB during overlap

Vision (signs) >= 20 FPS road cam on Hailo-8L

DMS >= 25 FPS, PERCLOS stable

ACCEPTANCE SEQUENCES

A) Normal request

control.toggle on -> state ARMED

User speaks -> vad.segment

asr.final -> llm.request (max_tokens depends on driving)

llm.tokens -> tts.command

tts.event start/stop -> back to ARMED

B) Barge-in

tts.event start

User speaks -> ORCHESTRATOR sends tts.stop immediately

New vad.segment -> asr.final -> llm.request

C) Vision-triggered reminder

vision.sign speed_limit=50; obd.pid speed=62

SAFETY emits safety.alert speed_limit

ORCHESTRATOR synthesizes short cue -> tts.command

D) Memory bookmark

User says “bookmark that tire pressure”

ORCHESTRATOR emits memory.save {category:"car_fact", text:"..."}; diary.entry logged

MESSAGE SCHEMA QUICK REFERENCE

audio.frame
{ "topic":"audio.frame","id":123456,"ts":..., "rms_db":-43.2, "pcm_s16le":"<bytes 640>" }

vad.segment
{ "topic":"vad.segment","start_id":..., "end_id":..., "dur_ms":1400, "snr_db":9.1, "pcm":"<bytes>" }

asr.partial
{ "topic":"asr.partial","text":"...", "conf":0.73, "ts":... }

asr.final
{ "topic":"asr.final","text":"...", "conf":0.87, "ts":... }

llm.request
{ "topic":"llm.request","prompt":"...", "max_tokens":150, "context":[{"quote":"...","ts":...}] }

llm.tokens
{ "topic":"llm.tokens","first_token_ms":620, "tps":12.4, "delta":"..." }

llm.done
{ "topic":"llm.done","reason":"stop|length|error", "ts":... }

tts.command
{ "topic":"tts.command","kind":"speak","text":"..." }

tts.event
{ "topic":"tts.event","type":"start|stop","ts":... }

vision.sign
{ "topic":"vision.sign","kind":"speed_limit","value":50,"conf":0.92,"bbox":[x,y,w,h],"ts":... }

dms.state
{ "topic":"dms.state","eyes_on":true,"blink_rate_hz":0.23,"perclos":0.18,"distracted":false,"ts":... }

obd.pid
{ "topic":"obd.pid","pid":"SPEED","value_kmh":97.2,"ts":... }

control.toggle
{ "topic":"control.toggle","state":"on|off","ts":... }

sys.health
{ "topic":"sys.health","mod":"audio|asr|llm|tts|vision|obd|safety|orchestrator|memory|diary|control","...": "...", "ts":... }

memory.query
{ "topic":"memory.query","q":"...", "k":5, "ts":... }

memory.results
{ "topic":"memory.results","hits":[{"quote":"...","ts":...}], "ts":... }

memory.save
{ "topic":"memory.save","category":"preference|constraint|contact|todo|car_fact|safety","text":"...","ts":... }

diary.entry
{ "topic":"diary.entry","kind":"session|event|error","text":"...","ts":... }

RUNTIME SWITCHES (ENV)

CARAI_QUEUE_AUDIO_MAX=100
CARAI_QUEUE_VAD_MAX=10
CARAI_MAX_LISTEN_MS=30000
CARAI_DRIVE_REPLY_TOKENS=150
CARAI_BASE_SIL_MS=500
CARAI_END_K=20

NOTES TO IMPLEMENTERS

Do not block the PortAudio callback. Push frames and return.

Align AEC near/far frames exactly at 20 ms cadence.

Use monotonic time for internal timing and latency measurements.

Treat every queue full as a backpressure_event; auto-mute for 1 s if necessary.

Keep logs structured; avoid prints except JSON.

END OF AGENTS.md PLAIN TEXT SPEC
