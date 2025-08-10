"""Simple CLI demo for transcribing an audio file using the ASR service."""

import argparse
from pathlib import Path

from .service import decode_audio, get_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe a WAV file")
    parser.add_argument("audio", type=Path, help="path to 16kHz 16-bit mono WAV file")
    args = parser.parse_args()

    audio_bytes = args.audio.read_bytes()
    audio = decode_audio(audio_bytes)
    segments, _ = get_model().transcribe(audio)
    text = "".join(seg.text for seg in segments).strip()
    print(text)


if __name__ == "__main__":
    main()
