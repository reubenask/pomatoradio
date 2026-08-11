#!/usr/bin/env python3
"""Turn drop text into audio.

Provider is chosen by the TTS_PROVIDER env var:

    say         macOS built-in voice. No account, no cost, sounds like a robot.
                Use this to test the pipeline before you clone anything.
    elevenlabs  Your cloned voice. Needs ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID.

Everything writes a 44.1kHz mono wav, which is what Liquidsoap wants.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile

PROVIDER = os.environ.get("TTS_PROVIDER", "say")


def speak(text: str, out: pathlib.Path) -> pathlib.Path:
    if PROVIDER == "elevenlabs":
        raw = _elevenlabs(text)
    elif PROVIDER == "say":
        raw = _macos_say(text)
    else:
        raise SystemExit(f"Unknown TTS_PROVIDER: {PROVIDER!r} (use 'say' or 'elevenlabs')")

    # Normalise to a single format so the station never chokes on a stray codec.
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
         "-ar", "44100", "-ac", "1", str(out)],
        check=True,
    )
    raw.unlink(missing_ok=True)
    return out


def _macos_say(text: str) -> pathlib.Path:
    tmp = pathlib.Path(tempfile.mkstemp(suffix=".aiff")[1])
    voice = os.environ.get("SAY_VOICE", "Daniel")
    subprocess.run(["say", "-v", voice, "-o", str(tmp), text], check=True)
    return tmp


def _elevenlabs(text: str) -> pathlib.Path:
    import urllib.error
    import urllib.request

    key = os.environ.get("ELEVENLABS_API_KEY")
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID")
    if not key or not voice_id:
        raise SystemExit("Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID.")

    body = {
        "text": text,
        "model_id": os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
        # Lower stability = more expressive. Radio drops want a little life in
        # them, but not so much that the voice drifts between takes.
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.80,
            "style": 0.20,
            "use_speaker_boost": True,
        },
    }
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        data=__import__("json").dumps(body).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            audio = resp.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"ElevenLabs {e.code}: {e.read().decode()[:400]}") from e

    tmp = pathlib.Path(tempfile.mkstemp(suffix=".mp3")[1])
    tmp.write_bytes(audio)
    return tmp
