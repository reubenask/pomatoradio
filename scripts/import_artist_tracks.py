#!/usr/bin/env python3
"""One-off: bring Reuben's own tracks from trials/trial music/ into rotation.

    python3 scripts/import_artist_tracks.py

Different case from import_trial_music.py's AI-generated instrumentals:
these are real songs with an actual artist, so they go in the weekend
genre shows (built for exactly this) rather than the weekday dayparts
(built for wordless background listening under voice drops, which a vocal
track fights). Placement below is by ear-of-the-title and measured tempo
(aubio) — genre is a guess from the title/tempo, not something derived from
the audio itself, since these aren't instrumentals a mood can be read off
of by BPM alone. Flagged for the artist to correct if any land wrong.

Same treatment as the last batch: two-pass loudnorm to -16 LUFS, tagged and
renamed to the station's "Artist - Title" convention, a full-quality copy
into music/<show>/ (untracked, local only) and a 128k copy into
web/samples/ for the site's preview rotation.
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

ARTIST = "Reuben ASK"
TARGET_I, TARGET_TP, TARGET_LRA = -16, -1.5, 7

# (source filename, show, display title, web-safe slug for non-ASCII titles)
TRACKS = [
    ("干杯.wav", "saturdaysoul", "干杯", "ganbei"),
    ("分不开.mp3", "saturdaysoul", "分不开", "fenbukai"),
    ("No More Games.wav", "saturdaysoul", "No More Games", None),
    ("We Don't Lose.wav", "hiphop", "We Don't Lose", None),
    ("Believe.wav", "hiphop", "Believe", None),
    ("2 on 2.wav", "hiphop", "2 on 2", None),
    ("So Naa.wav", "any", "So Naa", None),
    ("Brandish_150bpm.wav", "trap", "Brandish", None),
]


def slug(text: str) -> str:
    s = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")
    return s


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

    for fname, show, title, web_slug in TRACKS:
        src = SRC / fname
        f = loudnorm_filter(src)
        station_name = f"{ARTIST} - {title}.mp3"
        web_name = (web_slug or slug(title)) + ".mp3"

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
        bpm = subprocess.run(["aubio", "tempo", "-i", str(web_dest)],
                              capture_output=True, text=True).stdout.strip().splitlines()
        bpm = float(bpm[-1].split()[0]) if bpm else 0.0

        manifest = [e for e in manifest if e["file"] != web_name]
        manifest.append({"show": show, "title": title, "file": web_name,
                          "duration": round(dur, 1), "bpm": round(bpm, 1)})

        mb = web_dest.stat().st_size / 1e6
        print(f"  {show:<12} {title:<16} bpm={bpm:5.1f}  -> {web_name}  ({mb:.1f} MB)")

    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n  manifest updated, {len(manifest)} tracks total")


if __name__ == "__main__":
    main()
