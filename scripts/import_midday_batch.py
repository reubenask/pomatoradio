#!/usr/bin/env python3
"""One-off: import the first midday batch — 31 files dropped into
trials/trial music/midday/. Five were byte-identical duplicates
(checksummed) and are skipped. Of the 26 unique tracks, six titles were
shared by more than one file (up to 4 takes of "Velvet Afternoon" and
4 of "Sunday Morning Shuffle"), so every one of those got a distinct name.

Fills the previously-empty midday show (12:00-14:00 weekdays). Playback
already orders each show's pool ascending by bpm (see web/index.html),
so no separate ordering step is needed here beyond tagging bpm correctly.

    python3 scripts/import_midday_batch.py
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "trials" / "trial music" / "midday"
MUSIC = ROOT / "music"
SAMPLES = ROOT / "web" / "samples"

ARTIST = "Pomato Radio"
TARGET_I, TARGET_TP, TARGET_LRA = -16, -1.5, 7
SHOW = "midday"

# (source filename, title)
TRACKS = [
    ("Afternoon in Blue.mp3", "Afternoon in Blue"),
    ("Backseat Boogie.mp3", "Backseat Boogie"),
    ("Backseat Boogie (1).mp3", "Backseat Boogie Reprise"),
    ("Chop Street Groove.mp3", "Chop Street Groove"),
    ("Lemon Daze.mp3", "Lemon Daze"),
    ("Lemon Daze (1).mp3", "Lemon Daze Drift"),
    ("Lunchtime Window.mp3", "Lunchtime Window"),
    ("Midnight Groove.mp3", "Midnight Groove"),
    ("Midnight in the Café.mp3", "Midnight in the Café"),
    ("Midnight in the Café (1).mp3", "Café Lights at Midnight"),
    ("Patio Bounce.mp3", "Patio Bounce"),
    ("Patio Bounce (1).mp3", "Patio Skip"),
    ("Pocket Groove.mp3", "Pocket Groove"),
    ("Sunday Morning Groove.mp3", "Sunday Morning Groove"),
    ("Sunday Morning Groove (1).mp3", "Sunday Morning Sway"),
    ("Sunday Morning Shuffle.mp3", "Sunday Morning Shuffle"),
    ("Sunday Morning Shuffle (1).mp3", "Sunday Shuffle Reprise"),
    ("Sunday Morning Shuffle (3).mp3", "Late Sunday Shuffle"),
    ("Sunday Morning Shuffle (4).mp3", "Sunday Shuffle Drift"),
    ("Sunlight Through the Window.mp3", "Sunlight Through the Window"),
    ("Velvet After Rain.mp3", "Velvet After Rain"),
    ("Velvet After Rain (1).mp3", "Rain-Soaked Velvet"),
    ("Velvet Afternoon.mp3", "Velvet Afternoon"),
    ("Velvet Afternoon (1).mp3", "Velvet Afternoon Glow"),
    ("Velvet Afternoon (2).mp3", "Afternoon in Velvet"),
    ("Velvet Afternoon (3).mp3", "Velvet Afternoon Drift"),
]

# Byte-identical to another file in TRACKS (checksummed) — never imported,
# left in place in trials/ for reference.
SKIPPED = [
    "Velvet Afternoon (4).mp3",        # == Velvet Afternoon.mp3
    "Sunday Morning Shuffle (2).mp3",  # == Sunday Morning Shuffle (1).mp3
    "Sunday Morning Groove (2).mp3",   # == Sunday Morning Groove.mp3
    "Sunday Morning Groove (3).mp3",   # == Sunday Morning Groove (1).mp3
    "Velvet Afternoon (5).mp3",        # == Velvet Afternoon (1).mp3
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
