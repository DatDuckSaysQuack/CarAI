# Car AI

A modular, voice-driven assistant for Raspberry Pi 5. This repository is
currently a scaffold that sets up basic service structure and tests.

## Quick start (development)

```bash
# Create environment config
cp config/.env.example config/.env

# Run the orchestrator (includes a stub LLM)
python apps/orchestrator/main.py
```

The orchestrator exposes a small FastAPI service with `/health` and `/chat`
endpoints. `/chat` currently echoes input messages and serves as a placeholder
for future LLM integration.

## Repository layout

See `AGENTS.md` for full project goals. Key directories:

- `apps/` – individual microservices (`asr`, `tts`, `orchestrator`, etc.).
- `config/` – environment files and profiles.
- `infra/` – Docker, CI and other deployment assets.
- `tests/` – unit tests (run with `pytest`).
- `docs/` – user documentation.

## Running tests

```bash
pytest
```
