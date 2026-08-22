#!/usr/bin/env python3
"""One-off: import the first slowdrive batch — 21 files dropped into
trials/trial music/slow drive/, 2000s R&B style. All 21 checksummed
genuinely distinct — no true duplicates this time — but several shared a
title, including a 4-way "Midnight Drive" cluster, so every duplicate
group was renamed distinct. "Midnight Groove" and "Velvet After Hours"
were also already taken by existing tracks in other shows, so those base
takes were renamed too.

Fills the previously-empty slowdrive show (17:00-20:00 weekdays, rush
hour). Playback already orders each show's pool ascending by bpm.

    python3 scripts/import_slowdrive_batch.py
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "trials" / "trial music" / "slow drive"
MUSIC = ROOT / "music"
SAMPLES = ROOT / "web" / "samples"

ARTIST = "Pomato Radio"
TARGET_I, TARGET_TP, TARGET_LRA = -16, -1.5, 7
SHOW = "slowdrive"

# (source filename, title)
TRACKS = [
    ("After The Dial.mp3", "After The Dial"),

    ("After The Replay.mp3", "After The Replay"),
    ("After The Replay_1.mp3", "Replaying After Hours"),

    ("Late Night Silk.mp3", "Late Night Silk"),

    ("Midnight Drive.mp3", "Midnight Drive"),
    ("Midnight Drive (1).mp3", "Late Night Drive"),
    ("Midnight Drive (2).mp3", "Slow Midnight Drive"),
    ("Midnight Drive (3).mp3", "Drive Through Midnight"),

    ("Midnight Groove.mp3", "Highway Midnight Groove"),

    ("Midnight in the Blue Room.mp3", "Midnight in the Blue Room"),

    ("Midnight in the Room.mp3", "Midnight in the Room"),
    ("Midnight in the Room (1).mp3", "Alone in the Room at Midnight"),

    ("Slow Velvet Drip.mp3", "Slow Velvet Drip"),

    ("Velvet After Hours.mp3", "Velvet at Last Light"),
    ("Velvet After Hours_1.mp3", "Velvet Hours Fading"),

    ("Velvet Replay.mp3", "Velvet Replay"),
    ("Velvet Replay_1.mp3", "Replay in Velvet"),

    ("Velvet Sidewalk.mp3", "Velvet Sidewalk"),
    ("Velvet Sidewalk_1.mp3", "Sidewalk in Velvet"),

    ("Velvet Turnaround.mp3", "Velvet Turnaround"),
    ("Velvet Turnaround_1.mp3", "Turnaround in Velvet"),
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
        print(f"  {title:<30} bpm={bpm:5.1f}  -> {web_name}  ({mb:.1f} MB)")

    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n  manifest updated, {len(manifest)} tracks total")


if __name__ == "__main__":
    main()
