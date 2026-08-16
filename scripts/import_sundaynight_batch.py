#!/usr/bin/env python3
"""One-off: import the first sundaynight batch — 18 files in trials/trial
music/sunday night/, one true duplicate (Paper Cup Moon / Paper Cup Moon
(1), byte-identical — checksummed to confirm) skipped, and five
duplicate-title groups renamed distinct, including one actual quadruple
(Midnight Velvet had four differently-named copies, all genuinely
different audio).

    python3 scripts/import_sundaynight_batch.py

Fills music/sundaynight/ and drops/today/sundaynight/'s music side — the
show added for the previously-unoccupied Sun 22:00 - Mon 06:00 slot.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "trials" / "trial music" / "sunday night"
MUSIC = ROOT / "music"
SAMPLES = ROOT / "web" / "samples"

ARTIST = "Pomato Radio"
TARGET_I, TARGET_TP, TARGET_LRA = -16, -1.5, 7
SHOW = "sundaynight"

# (source filename, title) — Paper Cup Moon (1).mp3 deliberately omitted,
# byte-identical to Paper Cup Moon.mp3
TRACKS = [
    ("Leave the Door Wide Open.mp3", "Leave the Door Wide Open"),
    ("Midnight Velvet.mp3", "Midnight Velvet"),
    ("Midnight Velvet (1).mp3", "Velvet After Midnight"),
    ("Midnight Velvet copy.mp3", "Velvet Hour Reprise"),
    ("Midnight Velvet (1) copy.mp3", "Deep Velvet Glow"),
    ("Midnight in Your Arms.mp3", "Midnight in Your Arms"),
    ("Midnight in Your Arms (1).mp3", "Wrapped in Midnight"),
    ("Moonlit Undertow.mp3", "Moonlit Undertow"),
    ("Moonlit Undertow (1).mp3", "Undertow After Hours"),
    ("Paper Cup Moon.mp3", "Paper Cup Moon"),
    ("Silk On My Collar.mp3", "Silk On My Collar"),
    ("Silk On My Collar_1.mp3", "Silk Undone"),
    ("Silk On My Pillow.mp3", "Silk On My Pillow"),
    ("Silk On My Pillow_1.mp3", "Pillow Talk Slow"),
    ("Velvet On My Sleeve.mp3", "Velvet On My Sleeve"),
    ("Velvet Till Dawn.mp3", "Velvet Till Dawn"),
    ("Velvet Till Dawn (1).mp3", "Dawn in Velvet"),
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
        print(f"  {title:<24} bpm={bpm:5.1f}  -> {web_name}  ({mb:.1f} MB)")

    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n  manifest updated, {len(manifest)} tracks total")


if __name__ == "__main__":
    main()
