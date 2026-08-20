#!/usr/bin/env python3
"""One-off: import the first longafternoon batch — 40 files dropped into
trials/trial music/Long Afternoon/. Nine were byte-identical duplicates
(checksummed) and are skipped. Of the 31 unique tracks, most shared a
title with at least one other file (up to 4 takes each of "Midnight
Pulse" and "Beneath the Static"), so nearly every one needed a distinct
name. "Midnight Pulse" itself was also already taken by an existing
househours track, so the base take here was renamed too.

Fills the previously-empty longafternoon show (14:00-17:00 weekdays).
Playback already orders each show's pool ascending by bpm.

    python3 scripts/import_longafternoon_batch.py
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "trials" / "trial music" / "Long Afternoon"
MUSIC = ROOT / "music"
SAMPLES = ROOT / "web" / "samples"

ARTIST = "Pomato Radio"
TARGET_I, TARGET_TP, TARGET_LRA = -16, -1.5, 7
SHOW = "longafternoon"

# (source filename, title)
TRACKS = [
    ("Beneath the Static.mp3", "Beneath the Static"),
    ("Beneath the Static (1).mp3", "Static Undertow"),
    ("Beneath the Static (2).mp3", "Beneath the Hum"),
    ("Beneath the Static (3).mp3", "Low Static Drift"),
    ("Beneath the Static (4).mp3", "Static and Silence"),
    ("Beneath the Static (5).mp3", "Sinking Static"),

    ("Beneath the Surface.mp3", "Beneath the Surface"),
    ("Beneath the Surface (1).mp3", "Just Below the Surface"),

    ("Fading Into Silence.mp3", "Fading Into Silence"),

    ("Midnight Pulse.mp3", "Long Afternoon Pulse"),
    ("Midnight Pulse (1).mp3", "Faint Pulse at Midnight"),
    ("Midnight Pulse (3).mp3", "Pulse in the Dark"),
    ("Midnight Pulse (6).mp3", "Slow Midnight Pulse"),

    ("Negative Space.mp3", "Negative Space"),
    ("Negative Space (1).mp3", "Room for Negative Space"),
    ("Negative Space (2).mp3", "Negative Space Drift"),
    ("Negative Space (3).mp3", "Quiet Negative Space"),

    ("Quiet After Rain.mp3", "Quiet After Rain"),
    ("Quiet After Rain (2).mp3", "Stillness After Rain"),
    ("Quiet After Rain (3).mp3", "After the Rain Settles"),

    ("Rainy Window Drift.mp3", "Rainy Window Drift"),
    ("Slow Needle Drift.mp3", "Slow Needle Drift"),

    ("Static Between Stars.mp3", "Static Between Stars"),
    ("Static Between Stars (1).mp3", "Faint Static Between Stars"),
    ("Static Between Stars (2).mp3", "Static Among the Stars"),
    ("Static Between Stars (4).mp3", "Distant Static Field"),

    ("Still Water Loop.mp3", "Still Water Loop"),
    ("Still Water Loop (1).mp3", "Still Water Drift"),

    ("Submerged Pulse.mp3", "Submerged Pulse"),
    ("Submerged Pulse (1).mp3", "Pulse Below the Surface"),

    ("Velvet Dust Tape.mp3", "Velvet Dust Tape"),
]

# Byte-identical to another file in TRACKS (checksummed) — never imported,
# left in place in trials/ for reference.
SKIPPED = [
    "Beneath the Surface (2).mp3",  # == Beneath the Surface (1).mp3
    "Beneath the Static (6).mp3",   # == Beneath the Static (4).mp3
    "Quiet After Rain (1).mp3",     # == Quiet After Rain.mp3
    "Velvet Dust Tape (1).mp3",     # == Velvet Dust Tape.mp3
    "Midnight Pulse (2).mp3",       # == Midnight Pulse (1).mp3
    "Midnight Pulse (8).mp3",       # == Midnight Pulse (1).mp3
    "Midnight Pulse (4).mp3",       # == Midnight Pulse (3).mp3
    "Midnight Pulse (5).mp3",       # == Midnight Pulse (3).mp3
    "Midnight Pulse (7).mp3",       # == Midnight Pulse (3).mp3
]


def slug(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def loudnorm_filter(src: pathlib.Path) -> str:
    measured = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(src),
         "-af", f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json",
         "-f", "null", "/dev/null"],
        capture_output=True, text=True).stderr
    blob = re.search(r"\{[^{}]*input_i[^{}]*\}", measured, re.S)
    if not blob:
        return f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}"
    d = json.loads(blob.group(0))
    return (f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}"
            f":measured_I={d['input_i']}:measured_TP={d['input_tp']}"
            f":measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}"
            f":offset={d['target_offset']}:linear=true")


def main() -> None:
    (MUSIC / SHOW).mkdir(parents=True, exist_ok=True)
    SAMPLES.mkdir(parents=True, exist_ok=True)

    manifest_path = SAMPLES / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []

    for fname, title in TRACKS:
        src = SRC / fname
        f = loudnorm_filter(src)
        station_name = f"{ARTIST} - {title}.mp3"
        web_name = slug(title) + ".mp3"

        station_dest = MUSIC / SHOW / station_name
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
             "-af", f"{f},aresample=44100", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "192k",
             "-metadata", f"artist={ARTIST}", "-metadata", f"title={title}",
             str(station_dest)],
            check=True, capture_output=True)

        web_dest = SAMPLES / web_name
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
             "-af", f"{f},aresample=44100", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "128k",
             "-metadata", f"artist={ARTIST}", "-metadata", f"title={title}",
             str(web_dest)],
            check=True, capture_output=True)

        dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(web_dest)], capture_output=True, text=True).stdout or 0)
        bpm_out = subprocess.run(["aubio", "tempo", "-i", str(web_dest)],
                                  capture_output=True, text=True).stdout.strip().splitlines()
        bpm = float(bpm_out[-1].split()[0]) if bpm_out else 0.0

        manifest = [e for e in manifest if e["file"] != web_name]
        manifest.append({"show": SHOW, "title": title, "file": web_name,
                          "duration": round(dur, 1), "bpm": round(bpm, 1)})

        mb = web_dest.stat().st_size / 1e6
        print(f"  {title:<28} bpm={bpm:5.1f}  -> {web_name}  ({mb:.1f} MB)")

    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n  manifest updated, {len(manifest)} tracks total")
    print(f"  {len(SKIPPED)} true duplicates skipped: {', '.join(SKIPPED)}")


if __name__ == "__main__":
    main()
