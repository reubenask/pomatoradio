#!/usr/bin/env python3
"""Compress the current drops/today/anytime/ takes into web/samples/ for
the site's fallback rotation, and write the manifest the JS reads to know
they exist.

    python3 scripts/publish_drops_to_web.py

Source files are already cleaned and leveled by clean_voice.sh (-16 LUFS);
this only compresses to 128k mp3 to match the music samples already in
web/samples/, filed under drops- so a filename never collides with a track.
"""

from __future__ import annotations

import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "drops" / "today" / "anytime"
SAMPLES = ROOT / "web" / "samples"


def main() -> None:
    SAMPLES.mkdir(parents=True, exist_ok=True)
    manifest = []
    for src in sorted(SRC.glob("*.wav")):
        dest = SAMPLES / f"drop-{src.stem}.mp3"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
             "-ac", "2", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "128k",
             str(dest)],
            check=True, capture_output=True)
        manifest.append({"file": dest.name})
        print(f"  {src.stem:<12} -> {dest.name}  ({dest.stat().st_size/1e6:.2f} MB)")

    (SAMPLES / "drops-manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n  {len(manifest)} drops published")


if __name__ == "__main__":
    main()
