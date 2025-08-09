# AGENTS.md
# High-level instructions for an AI coding agent to build, test, and ship this project.

## Mission
Build a voice-driven “Car AI” that runs on a Raspberry Pi 5 (64-bit Raspberry Pi OS / Debian Bookworm).
I describe goals in plain language; you implement code, tests, docs, and automation and keep iterating until
the end-to-end system works on the Pi.

**Non-negotiables**
- Target: Raspberry Pi 5, `linux/arm64`, Debian Bookworm (Raspberry Pi OS 64-bit).
- Prefer **fully local** processing (offline by default). If cloud access is needed, make it an explicit opt-in.
- Keep CPU/RAM use light. Use **quantized** models where possible.
- Everything must run as **systemd services** and/or **Docker Compose** on the Pi.
- Provide **mocks** so core logic can run in CI without hardware attached.
- Write clear docs: simple commands, no jargon.

---

## Repo layout (create this)
```
/apps
  /orchestrator           # main app that routes speech↔logic↔tools (Python)
  /asr                    # speech-to-text (Whisper: faster-whisper or whisper.cpp)
  /tts                    # text-to-speech (Piper preferred)
  /vision                 # camera pipeline + object/traffic-sign detection
  /signs                  # traffic-sign classifier (GTSRB-based or similar)
  /driver_monitoring      # eye/attention/drowsiness (MediaPipe/OpenCV)
  /obd                    # OBD-II / CAN abstraction (python-OBD, python-can/SocketCAN)
  /memory                 # vector memory (FAISS + SQLite) and retrieval helpers
  /ui                     # lightweight local web UI + settings (FastAPI + HTMX or simple React)
/infra
  /docker                 # Dockerfiles, Compose, scripts
  /ci                     # GitHub Actions workflows (arm64 builds, tests)
/tests                    # unit, integration, and hardware-mock tests
/config                   # .env templates, YAML configs
/docs                     # user docs with screenshots
```

---

## Tech choices (defaults, unless overridden)
- **Python 3.11+** for apps. Keep modules isolated with virtualenv/uv or Docker.
- **ASR**: `faster-whisper` (CPU) with `tiny` or `small` models; fall back to `whisper.cpp` if memory tight.
- **TTS**: `piper` with a lightweight voice (<<< FILL preferred language/voice >>>).
- **Vision**: OpenCV pipeline + a tiny detector (YOLOv8n/YOLOv9n converted to **TFLite/ONNX** quantized) for speed.
- **Signs**: use a compact GTSRB-based classifier (quantized). Provide labels + confidence thresholds.
- **Driver monitoring**: MediaPipe/BlazeFace or OpenCV DNN for face/eyes; compute PERCLOS/attention heuristics.
- **OBD**:
  - ELM327 (USB/BLE): `python-OBD`.
  - CAN HAT: `python-can` via **SocketCAN** (`can0`).
  - Provide a unified `obd_api.py` with the same interface for both backends.
- **Memory**: FAISS (CPU, flat or HNSW) + SQLite for metadata. Provide simple `mem.add()` / `mem.query()`.
- **Orchestrator**:
  - Primary “chat brain”: **Phi-3 Mini (4K Instruct)** running **locally via llama.cpp**, quantized (Q4_0 or Q4_K_M) for Raspberry Pi 5.
  - Use the local LLM by default. Cloud LLMs (OpenAI/Anthropic) are **optional** and only used if `ALLOW_CLOUD=1`.
  - Provide a thin Python client that streams tokens from llama.cpp’s server (or bindings) and exposes a simple `/chat` API.
- **Packaging**: Docker **and** native scripts. Default to Docker Compose.

---

## Environment & hardware assumptions
- OS: Raspberry Pi OS 64-bit (Bookworm), kernel 6.x.
- Audio in: ALSA (USB mic or Pi mic array). Audio out: ALSA (3.5mm or USB).
- Camera: libcamera (CSI) **or** USB UVC. Provide both pipelines.
- OBD: one of:
  - `ELM327` USB/BLE dongle, serial device auto-detect.
  - CAN HAT on `can0` (SocketCAN).
- GPU: do not assume CUDA. Prefer CPU or ARM-friendly runtimes (NEON). If hardware accel is used, gate behind feature flags.

---

## Security & privacy
- **No analytics** or off-device telemetry by default.
- Store local data under `/var/lib/car-ai` on the Pi with appropriate permissions.
- Never write secrets to logs. Use `/config/.env` with an example template.

---

## Build targets

### A) Docker Compose (preferred)
- Produce `infra/docker/docker-compose.yml` with services:
  - `orchestrator`, `asr`, `tts`, `vision`, `signs`, `driver_monitoring`, `obd`, `ui`, `memory`, `llm` (llama.cpp server for Phi-3).
- Each service gets a minimal Dockerfile that builds for `linux/arm64`.
- Provide `Makefile` targets:
  - `make up` → build images (with `--platform linux/arm64`) and `docker compose up -d`
  - `make down` → stop
  - `make logs` → tail all logs
  - `make shell SERVICE=name` → enter container
- Volumes:
  - `/config` → bind to host `./config`
  - `/data` → host `/var/lib/car-ai`
  - `/models` → host `./models` for GGUF model files
- Resource limits (Compose): cap CPU/memory per service to prevent lockups on Pi.

### B) Native install (fallback)
- Create `infra/scripts/pi_install.sh` that:
  - Updates apt, installs system deps (python3, pip, venv, portaudio/alsa dev, libcamera, opencv deps, can-utils).
  - Creates venvs per app, installs Python deps.
  - Enables SocketCAN if selected.
- Create systemd units in `infra/systemd/`:
  - one per service + a `car-ai.target` that `Wants=` each service.
  - `car-ai.target` is what we enable at boot.

---

## CI/CD (GitHub Actions)
- Workflow: `.github/workflows/ci.yml`
  - Lint + unit tests.
  - Build **arm64** Docker images via `buildx` + `qemu-user-static`.
  - Run headless integration tests with hardware **mocks**.
  - On tag: push images to GHCR and attach artifacts (arm64 images + native wheels).
- Provide a second workflow `release.yml` to publish a compressed bundle and a “one-line curl | bash” installer for native mode.

---

## Configuration
- Provide `/config/.env.example` with:
  ```
  # Audio
  MIC_DEVICE=default
  SPEAKER_DEVICE=default

  # Camera
  CAMERA_BACKEND=libcamera   # options: libcamera|uvc
  CAMERA_DEVICE=/dev/video0

  # OBD
  OBD_BACKEND=elm327         # options: elm327|socketcan|mock
  OBD_SERIAL=/dev/ttyUSB0
  OBD_BAUD=38400
  CAN_IFACE=can0

  # AI
  ALLOW_CLOUD=0              # 0 local-only, 1 allow cloud calls
  LLM_BACKEND=llamacpp       # options: llamacpp|openai|anthropic
  LLM_MODEL=phi-3-mini-4k-instruct-q4_0.gguf
  LLM_CONTEXT=4096
  ASR_MODEL=whisper-small
  TTS_VOICE=<<< FILL >>>     # e.g., "en_US-amy-medium"
  ```

- Add `/config/profiles/` with presets:
  - `offline-fast.env` (tiny models, low latency)
  - `offline-quality.env` (small models)
  - `cloud-hq.env` (allows cloud calls)

---

## Orchestrator contract
- Input events:
  - `wake_word` (optional later), or push-to-talk from UI
  - `user_speech_transcript`
  - `vision_event` (e.g., sign detected, hazard)
  - `obd_event` (e.g., error code, speed)
  - `driver_state` (e.g., drowsy, inattentive)
- Output actions:
  - speak via TTS, show UI banner, log, store memory, trigger alerts.
- Provide a simple rule engine (YAML in `/config/rules.yaml`) the user can edit in plain text.

---

## Tests
- **Unit tests** for each module (pytest).
- **Hardware mocks**:
  - ALSA fake source/sink
  - libcamera/uvc dummy frames
  - OBD mock (ELM327 responses, SocketCAN loopback)
  - Vision/signs: canned images with expected detections
- **Smoke test** script:
  - Start minimal stack, feed a short WAV, simulate “speed 50” sign frame, simulate OBD response; expect TTS response “speed limit is 50” and memory entry created.

---

## Commands (for humans)
- **Docker mode**
  ```
  cp config/.env.example config/.env
  make up
  make logs
  ```
  Open the UI at `http://<pi>:8080`

- **Native mode**
  ```
  sudo bash infra/scripts/pi_install.sh
  sudo systemctl enable car-ai.target
  sudo systemctl start car-ai.target
  journalctl -u orchestrator -f
  ```

- **Run local LLM server manually**
  ```
  mkdir -p models
  # Place phi-3-mini-4k-instruct-q4_0.gguf here or let the agent auto-download
  make llm-serve
  ```

---

## Agent tasks (do these in order)
1. **Bootstrap repo**: create the directories, README with quickstart, and this AGENTS.md.
2. **ASR**: implement `apps/asr` with a small REST/WebSocket API; unit tests; CLI demo script.
3. **TTS**: implement `apps/tts` with Piper; same API; ensure voices are downloadable/cached.
4. **Vision**: camera abstraction (libcamera + UVC), frame pipeline, object detector (tiny model, quantized).
5. **Signs**: classifier with labels; expose `/signs/detect` that returns sign + confidence.
6. **Driver monitoring**: face/eyes, PERCLOS/attention; thresholds + debounce; `/driver/status`.
7. **OBD**: unified API with backends (ELM327 + SocketCAN); `/obd/query?pid=...`; periodic sampling.
8. **Memory**: FAISS + SQLite wrapper; add/query with embeddings (local CPU).
9. **Orchestrator**:
   - Integrate **llama.cpp** (server mode) for Phi-3 Mini:
     - Download `phi-3-mini-4k-instruct-q4_0.gguf` to `./models/` (on-demand, with checksum).
     - Provide a Make target `make llm-serve` that starts llama.cpp server (binding to 127.0.0.1:8081).
     - Python client streams from `http://127.0.0.1:8081` and exposes `/chat`.
   - Keep cloud adapters behind `ALLOW_CLOUD`.
10. **UI**: simple web dashboard: mic PTT, live logs, toggles for offline/cloud, view recent events/memories.
11. **Infra**: Dockerfiles (arm64), Compose, Makefile; native installer; systemd units; CI workflows.
12. **Mocks & tests**: comprehensive mocks; a headless integration test in CI.
13. **Docs**: user guide with screenshots, “first run” wizard page in the UI to set basic options.
14. **Performance pass**: profile CPU/mem on Pi; adjust model sizes/quantization; document expected resource use.
15. **Release**: GitHub Release with arm64 images + native installer.

---

## Guardrails & approval
- Never enable cloud calls unless `ALLOW_CLOUD=1`.
- Before adding large models/assets (>200 MB), ask for approval or make them **on-demand downloads** with checksums.
- Do not change system network/firewall settings.
- For BLE pairing or serial permissions, document exact steps; do not guess.

---

## Success criteria (what “done” looks like)
- On a fresh Pi 5, user can:
  1) `make up` (Docker) **or** run the native installer,
  2) press a button in the UI, say “what’s the current speed limit?”, hold a printed **50** sign to the camera, and
  3) hear a spoken answer within 2–3 seconds on offline-fast profile.
- All services restart on failure and auto-start on boot.
- CI passes: unit + integration (with mocks). A demo video/gif lives in `/docs`.

---

## Open questions (agent: prompt the user for these; use sensible defaults meanwhile)
- **Language & voice** for TTS → <<< FILL >>>
- **ASR language(s)** → <<< FILL >>>
- **OBD hardware** → <<< FILL >>>
- **Camera**: CSI or USB? → <<< FILL >>>
- **Wake word** now or later? → <<< FILL >>>
- **Allow cloud LLM fallback?** → <<< FILL >>>
