#!/usr/bin/env python3
"""One-off: apply Reuben's by-ear genre corrections to the catalog.

    python3 scripts/reassign_shows.py

Everything up to now was placed by title/tempo guesswork — this is the
first pass that reflects someone actually listening. Updates both
web/samples/manifest.json (by title, keyed off the show field) and the
physical copies in music/<show>/ (moved between folders so the real
station's placement matches the site's).
"""

from __future__ import annotations

import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "web" / "samples" / "manifest.json"
MUSIC = ROOT / "music"

# title -> new show. Only entries that actually change are listed;
# anything not here keeps its current show.
REASSIGN = {
    "Dusty Highway": "country",
    "Shoulder Lane Drift": "country",
    "Follow The Rhythm": "afrofriday",
    "Velvet Circuit": "hiphop",
    "Low Voltage Blue": "hiphop",
    "Velvet After Hours": "smallhours",
    "Last Call Neon": "smallhours",
    "Blue Smoke Loop": "slowroll",
    "Ashtray Hours": "slowroll",
    "Late Night Receipt": "saturdaysoul",
    "Closing Tab": "saturdaysoul",
    "Backroom Clean": "hiphop",
    "Back Door Exit": "hiphop",
    "One Drop Nostalgia": "firstlight",
    "干杯": "hiphop",
    "No More Games": "afrofriday",
    "We Don't Lose": "trap",
    "Believe": "afrofriday",
    "So Naa": "afrofriday",
}


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    moved = 0
    for entry in manifest:
        new_show = REASSIGN.get(entry["title"])
        if not new_show or new_show == entry["show"]:
            continue
        old_show = entry["show"]

        for show_dir in MUSIC.iterdir():
            if not show_dir.is_dir() or show_dir.name != old_show:
                continue
            for f in show_dir.glob(f"* - {entry['title']}.mp3"):
                dest_dir = MUSIC / new_show
                dest_dir.mkdir(exist_ok=True)
                shutil.move(str(f), str(dest_dir / f.name))
                print(f"  moved file: {f.name}  ({old_show} -> {new_show})")

        entry["show"] = new_show
        moved += 1
        print(f"  {entry['title']:<24} {old_show:<14} -> {new_show}")

    MANIFEST.write_text(json.dumps(manifest, indent=2))
    print(f"\n  {moved} tracks reassigned")


if __name__ == "__main__":
    main()
