#!/usr/bin/env python3
"""One-off: bring trials/trial music/ into the station and onto the site.

Run once against this batch. Not meant to be a general tool — the mapping
below is a manual, by-ear-of-the-title categorisation of these 16 specific
tracks, not something that generalises to the next batch.

    python3 scripts/import_trial_music.py

For each track: two-pass loudnorm to -16 LUFS (matching the voice drops, so
nothing jumps in level when the show changes), tagged and renamed to the
"Artist - Title" convention the station falls back to, dropped into its show
folder in music/ (untracked, local only), and a second, more compressed copy
written to web/samples/ for the site's feedback player.
"""

from __future__ import annotations

import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "trials" / "trial music"
MUSIC = ROOT / "music"
SAMPLES = ROOT / "web" / "samples"

TARGET_I, TARGET_TP, TARGET_LRA = -16, -1.5, 7

# (source filename, show folder, display title, take label or "")
TRACKS = [
    ("First_Light_Unfolding_2026-08-14T152702.wav", "firstlight", "First Light Unfolding", ""),
    ("Early_Morning_Stillness_2026-08-14T155855.wav", "firstlight", "Early Morning Stillness", ""),
    ("Sable Palm Drift.mp3", "firstlight", "Sable Palm Drift", "A"),
    ("Sable Palm Drift_1.mp3", "firstlight", "Sable Palm Drift", "B"),

    ("Blue Room Swing.mp3", "slowroll", "Blue Room Swing", "A"),
    ("Blue Room Swing_1.mp3", "slowroll", "Blue Room Swing", "B"),

    ("Dusty Highway.mp3", "slowdrive", "Dusty Highway", "A"),
    ("Dusty Highway_1.mp3", "slowdrive", "Dusty Highway", "B"),

    ("Follow_The_Rhythm_2026-08-14T160753.wav", "nightgarage", "Follow The Rhythm", ""),
    ("Velvet Circuit.mp3", "nightgarage", "Velvet Circuit", "A"),
    ("Velvet Circuit_1.mp3", "nightgarage", "Velvet Circuit", "B"),
    ("Velvet After Hours.mp3", "nightgarage", "Velvet After Hours", "A"),
    ("Velvet After Hours_1.mp3", "nightgarage", "Velvet After Hours", "B"),

    ("Blue Smoke Loop.mp3", "smallhours", "Blue Smoke Loop", "A"),
    ("Blue Smoke Loop_1.mp3", "smallhours", "Blue Smoke Loop", "B"),
    ("Late Night Receipt.mp3", "smallhours", "Late Night Receipt", "A"),
    ("Late Night Receipt_1.mp3", "smallhours", "Late Night Receipt", "B"),

    ("Backroom Clean.mp3", "any", "Backroom Clean", "A"),
    ("Backroom Clean_1.mp3", "any", "Backroom Clean", "B"),
    ("One_Drop_Nostalgia_2026-08-14T150916.wav", "any", "One Drop Nostalgia", ""),
]


def loudnorm_filter(src: pathlib.Path) -> str:
    measured = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(src),
         "-af", f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json",
         "-f", "null", "/dev/null"],
        capture_output=True, text=True).stderr
    blob = re.search(r"\{[^{}]*input_i[^{}]*\}", measured, re.S)
    if not blob:
        return f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}"
    import json
    d = json.loads(blob.group(0))
    return (f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}"
            f":measured_I={d['input_i']}:measured_TP={d['input_tp']}"
            f":measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}"
            f":offset={d['target_offset']}:linear=true")


def slug(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def main() -> None:
    for show in {t[1] for t in TRACKS}:
        (MUSIC / show).mkdir(parents=True, exist_ok=True)
    SAMPLES.mkdir(parents=True, exist_ok=True)

    manifest = []
    for fname, show, title, take in TRACKS:
        src = SRC / fname
        f = loudnorm_filter(src)
        display = f"{title} ({take})" if take else title
        station_name = f"Pomato Radio - {display}.mp3"
        web_name = slug(f"{title}-{take}" if take else title) + ".mp3"

        station_dest = MUSIC / show / station_name
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
             "-af", f"{f},aresample=44100", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "192k",
             "-metadata", "artist=Pomato Radio", "-metadata", f"title={display}",
             str(station_dest)],
            check=True, capture_output=True)

        web_dest = SAMPLES / web_name
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
             "-af", f"{f},aresample=44100", "-ac", "2", "-c:a", "libmp3lame", "-b:a", "128k",
             "-metadata", "artist=Pomato Radio", "-metadata", f"title={display}",
             str(web_dest)],
            check=True, capture_output=True)

        mb = web_dest.stat().st_size / 1e6
        print(f"  {show:<12} {display:<32} -> {web_name}  ({mb:.1f} MB)")
        manifest.append({"show": show, "title": display, "file": web_name})

    import json
    (SAMPLES / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n  {len(manifest)} tracks processed")


if __name__ == "__main__":
    main()
