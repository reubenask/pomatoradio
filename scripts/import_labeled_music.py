#!/usr/bin/env python3
"""One-off: import the second AI-generated batch — labeled by genre in the
source filename this time, so no title/tempo guesswork on placement.

    python3 scripts/import_labeled_music.py

Same treatment as scripts/import_trial_music.py: two-pass loudnorm to -16
LUFS, tagged and renamed to "Artist - Title", full-quality copy into
music/<show>/ (untracked, local), 128k copy into web/samples/ with an entry
appended to manifest.json.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "trials" / "trial music"
MUSIC = ROOT / "music"
SAMPLES = ROOT / "web" / "samples"

ARTIST = "Pomato Radio"
TARGET_I, TARGET_TP, TARGET_LRA = -16, -1.5, 7

# (source filename, show, display title)
TRACKS = [
    ("Golden Hour Groove_afro.mp3", "afrofriday", "Golden Hour Groove"),
    ("Midnight Pulse_house msic.mp3", "househours", "Midnight Pulse"),
    ("Midnight Pulse_trap&Housemix.mp3", "trap", "Midnight Pulse (Trap Mix)"),
    ("Midnight Wax Pocket_hiphop.mp3", "hiphop", "Midnight Wax Pocket"),
    ("Midnight Wax Pocket_1_hiphop.mp3", "hiphop", "Wax Pocket After Dark"),
    ("Palm Groove_afro.mp3", "afrofriday", "Palm Groove"),
    ("Palm Groove_1_afro.mp3", "afrofriday", "Coastal Palm Sway"),
    ("Palmwine Neon_afro.mp3", "afrofriday", "Palmwine Neon"),
    ("Velvet Loop_hiphop.mp3", "hiphop", "Velvet Loop"),
    ("Velvet Loop_1_hiphop.mp3", "hiphop", "Amber Loop Drift"),
    ("Velvet Smoke Loop_trap.mp3", "trap", "Velvet Smoke Loop"),
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
    for show in {t[1] for t in TRACKS}:
        (MUSIC / show).mkdir(parents=True, exist_ok=True)
    SAMPLES.mkdir(parents=True, exist_ok=True)

    manifest_path = SAMPLES / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []

    for fname, show, title in TRACKS:
        src = SRC / fname
        f = loudnorm_filter(src)
        station_name = f"{ARTIST} - {title}.mp3"
        web_name = slug(title) + ".mp3"

        station_dest = MUSIC / show / station_name
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
        manifest.append({"show": show, "title": title, "file": web_name,
                          "duration": round(dur, 1), "bpm": round(bpm, 1)})

        mb = web_dest.stat().st_size / 1e6
        print(f"  {show:<12} {title:<26} bpm={bpm:5.1f}  -> {web_name}  ({mb:.1f} MB)")

    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n  manifest updated, {len(manifest)} tracks total")


if __name__ == "__main__":
    main()
