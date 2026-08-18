#!/usr/bin/env python3
"""One-off: import the firstlight/slowroll batch — 42 files dropped
directly into trials/trial music/firstlight/ and .../slowroll/ (the show
folder itself was the placement decision this time, no guessing needed).

Two were byte-identical duplicates (checksummed, not just same-name) and
are skipped entirely. Of the 40 unique tracks, most shared a title with at
least one other file — up to 8 different takes all called "Summer Bounce",
and "Sunshine in the Groove" spanning both shows at 7 takes total — so
nearly every track needed a distinct name, not just the usual couple of
pairs.

    python3 scripts/import_firstlight_slowroll_batch.py
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
MUSIC = ROOT / "music"
SAMPLES = ROOT / "web" / "samples"

ARTIST = "Pomato Radio"
TARGET_I, TARGET_TP, TARGET_LRA = -16, -1.5, 7

# (source path relative to trials/trial music/, show, title)
TRACKS = [
    ("firstlight/Palm Shade Bounce.mp3", "firstlight", "Palm Shade Bounce"),
    ("firstlight/Summer Bounce.mp3", "firstlight", "Summer Bounce"),
    ("firstlight/Summer Bounce copy.mp3", "firstlight", "Sunbaked Bounce"),
    ("firstlight/Summer Bounce copy 2.mp3", "firstlight", "Summer Porch Bounce"),
    ("firstlight/Summer Bounce copy 3.mp3", "firstlight", "Golden Summer Skip"),
    ("firstlight/Summer Bounce (1).mp3", "firstlight", "Summer Sway"),
    ("firstlight/Summer Bounce (1) copy.mp3", "firstlight", "Midday Bounce"),
    ("firstlight/Summer Bounce (1) copy 2.mp3", "firstlight", "Summer Haze Bounce"),
    ("firstlight/Summer Bounce (1) copy 3.mp3", "firstlight", "Barefoot Summer Bounce"),
    ("firstlight/Sunlight on the Vinyl.mp3", "firstlight", "Sunlight on the Vinyl"),
    ("firstlight/Sunlight on the Vinyl (1).mp3", "firstlight", "Vinyl in the Sun"),
    ("firstlight/Sunlit Brass.mp3", "firstlight", "Sunlit Brass"),
    ("firstlight/Sunlit Brass (1).mp3", "firstlight", "Brass in the Morning Light"),
    ("firstlight/Sunlit Groove.mp3", "firstlight", "Sunlit Groove"),
    ("firstlight/Sunlit Groove copy.mp3", "firstlight", "Morning Groove Drift"),
    ("firstlight/Sunshine in the Groove.mp3", "firstlight", "Sunshine in the Groove"),
    ("firstlight/Sunshine in the Groove (1).mp3", "firstlight", "Groove in the Sunshine"),

    ("slowroll/Groove in the Static.mp3", "slowroll", "Groove in the Static"),
    ("slowroll/Midnight Palm Circuit.mp3", "slowroll", "Midnight Palm Circuit"),
    ("slowroll/Palm Shade Bounce.mp3", "slowroll", "Palm Frond Sway"),
    ("slowroll/Palm Shade Bounce (1).mp3", "slowroll", "Shaded Palm Groove"),
    ("slowroll/Pocket Full of Dust.mp3", "slowroll", "Pocket Full of Dust"),
    ("slowroll/Pocket Full of Dust (1).mp3", "slowroll", "Dust in My Pocket"),
    ("slowroll/Sun Juice Swing.mp3", "slowroll", "Sun Juice Swing"),
    ("slowroll/Sunday Morning Jazz.mp3", "slowroll", "Sunday Morning Jazz"),
    ("slowroll/Sunday Morning Static (1).mp3", "slowroll", "Sunday Morning Static"),
    ("slowroll/Sunlit Pocket Change.mp3", "slowroll", "Sunlit Pocket Change"),
    ("slowroll/Sunlit Pocket Change (1).mp3", "slowroll", "Pocket Change in the Sun"),
    ("slowroll/Sunlit Vinyl Drip.mp3", "slowroll", "Sunlit Vinyl Drip"),
    ("slowroll/Sunlit Vinyl Drip (1).mp3", "slowroll", "Vinyl Drip Roll"),
    ("slowroll/Sunshine Static.mp3", "slowroll", "Sunshine Static"),
    ("slowroll/Sunshine Static (1).mp3", "slowroll", "Static in the Sunshine"),
    ("slowroll/Sunshine in the Groove.mp3", "slowroll", "Sunny Groove Roll"),
    ("slowroll/Sunshine in the Groove (1).mp3", "slowroll", "Groove and Sunbeams"),
    ("slowroll/Sunshine in the Groove (2).mp3", "slowroll", "Sunlit Roll"),
    ("slowroll/Sunshine in the Groove (3).mp3", "slowroll", "Sun-Kissed Groove"),
    ("slowroll/Sunshine in the Groove 2.mp3", "slowroll", "Golden Groove Roll"),
    ("slowroll/Sunshine in the Static.mp3", "slowroll", "Sunshine in the Static"),
    ("slowroll/Sunshine in the Static (1).mp3", "slowroll", "Sunny Static Roll"),
    ("slowroll/Wobble Alley Groove.mp3", "slowroll", "Wobble Alley Groove"),
]

# Byte-identical to another file in TRACKS (checksummed) — never imported,
# left in place in trials/ for reference.
SKIPPED = [
    "slowroll/Palm Shade Bounce (2).mp3",   # == Palm Shade Bounce (1).mp3
    "slowroll/Sunday Morning Static.mp3",   # == Sunday Morning Static (1).mp3
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
    src_root = ROOT / "trials" / "trial music"
    for show in {t[1] for t in TRACKS}:
        (MUSIC / show).mkdir(parents=True, exist_ok=True)
    SAMPLES.mkdir(parents=True, exist_ok=True)

    manifest_path = SAMPLES / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []

    for rel, show, title in TRACKS:
        src = src_root / rel
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
        print(f"  {show:<10} {title:<26} bpm={bpm:5.1f}  -> {web_name}  ({mb:.1f} MB)")

    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n  manifest updated, {len(manifest)} tracks total")
    print(f"  {len(SKIPPED)} true duplicates skipped: {', '.join(SKIPPED)}")


if __name__ == "__main__":
    main()
