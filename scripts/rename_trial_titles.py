#!/usr/bin/env python3
"""One-off: give the "(A)/(B)" trial tracks distinct titles.

No real station repeats a title with "(A)" next to it — that reads as a
glitch, not two songs. Retags and renames both the local music/ copy and the
tracked web/samples/ copy, and rewrites manifest.json (adding duration, which
the client-side rotation needs) in one pass. Re-run only if the batch changes.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
MUSIC = ROOT / "music"
SAMPLES = ROOT / "web" / "samples"

# old title (as currently tagged/named) -> new title
RENAME = {
    "Sable Palm Drift (A)": "Sable Palm Drift",
    "Sable Palm Drift (B)": "Palm Line Horizon",
    "Blue Room Swing (A)": "Blue Room Swing",
    "Blue Room Swing (B)": "Corner Booth Sway",
    "Dusty Highway (A)": "Dusty Highway",
    "Dusty Highway (B)": "Shoulder Lane Drift",
    "Velvet Circuit (A)": "Velvet Circuit",
    "Velvet Circuit (B)": "Low Voltage Blue",
    "Velvet After Hours (A)": "Velvet After Hours",
    "Velvet After Hours (B)": "Last Call Neon",
    "Blue Smoke Loop (A)": "Blue Smoke Loop",
    "Blue Smoke Loop (B)": "Ashtray Hours",
    "Late Night Receipt (A)": "Late Night Receipt",
    "Late Night Receipt (B)": "Closing Tab",
    "Backroom Clean (A)": "Backroom Clean",
    "Backroom Clean (B)": "Back Door Exit",
}


def slug(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def duration(path: pathlib.Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout
    return round(float(out.strip() or 0), 1)


def retag(src: pathlib.Path, dest: pathlib.Path, title: str) -> None:
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
         "-c", "copy", "-metadata", f"title={title}", "-metadata", "artist=Pomato Radio",
         str(dest)],
        check=True, capture_output=True)
    if dest != src:
        src.unlink()


def main() -> None:
    manifest_path = SAMPLES / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    for old, new in RENAME.items():
        old_slug = slug(old)
        new_slug = slug(new)

        web_src = SAMPLES / f"{old_slug}.mp3"
        web_dest = SAMPLES / f"{new_slug}.mp3"
        retag(web_src, web_dest, new)

        for show_dir in MUSIC.iterdir():
            if not show_dir.is_dir():
                continue
            cand = show_dir / f"Pomato Radio - {old}.mp3"
            if cand.exists():
                retag(cand, show_dir / f"Pomato Radio - {new}.mp3", new)
                break

        print(f"  {old:<28} -> {new}")

    for entry in manifest:
        entry["title"] = RENAME.get(entry["title"], entry["title"])
        entry["file"] = slug(entry["title"]) + ".mp3"
        entry["duration"] = duration(SAMPLES / entry["file"])

    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n  manifest rewritten, {len(manifest)} tracks, durations added")


if __name__ == "__main__":
    main()
