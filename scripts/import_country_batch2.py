#!/usr/bin/env python3
"""One-off: import the second country batch — 18 files, 4 duplicate-title
families (one with 8 members). Every file checksummed distinct — no true
duplicates this time, unlike the sundaynight batch.

    python3 scripts/import_country_batch2.py
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "trials" / "trial music" / "country"
MUSIC = ROOT / "music"
SAMPLES = ROOT / "web" / "samples"

ARTIST = "Pomato Radio"
TARGET_I, TARGET_TP, TARGET_LRA = -16, -1.5, 7
SHOW = "country"

TRACKS = [
    ("Dust Bowl Dance.mp3", "Dust Bowl Dance"),
    ("Dust Bowl Dance (1).mp3", "Dust Bowl Reel"),
    ("Dust Bowl Dance Party.mp3", "Dust Bowl Dance Party"),
    ("Dust Bowl Dance Party (1).mp3", "Barnyard Dust Party"),
    ("Dust and Diamonds.mp3", "Dust and Diamonds"),
    ("Dust and Diamonds (1).mp3", "Diamonds in the Dust Road"),
    ("Dust and Diamonds 2.mp3", "Rhinestone Dust"),
    ("Dust and Diamonds (1) 2.mp3", "Diamond Dust Waltz"),
    ("Dust on the Highway.mp3", "Dust on the Highway"),
    ("Dust on the Highway (1).mp3", "Highway Dust Trail"),
    ("Dust on the Highway (2).mp3", "Backroad Dust Cloud"),
    ("Dust on the Highway (3).mp3", "Dust and Gravel Road"),
    ("Dust on the Highway (4).mp3", "Long Dusty Mile"),
    ("Dust on the Highway (5).mp3", "Windshield Dust"),
    ("Dust on the Highway (6).mp3", "Tailwind Dust"),
    ("Dust on the Highway (7).mp3", "Dust Behind the Wheels"),
    ("Dust on the Porch.mp3", "Dust on the Porch"),
    ("Dust on the Porch (1).mp3", "Porch Step Dust"),
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
        print(f"  {title:<26} bpm={bpm:5.1f}  -> {web_name}  ({mb:.1f} MB)")

    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n  manifest updated, {len(manifest)} tracks total")


if __name__ == "__main__":
    main()
