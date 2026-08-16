#!/usr/bin/env python3
"""One-off: sort trials/trial music/ into show subfolders, matching the
final (post-reassignment) placement in manifest.json — not a re-guess.

    python3 scripts/organize_trials_folder.py

Every file currently in trials/trial music/ has already been imported by
one of the batch scripts (import_trial_music.py, import_artist_tracks.py,
import_labeled_music.py, import_trap_batch2.py, import_house_batch.py,
import_folk_batch.py, import_folk_batch2.py). This is just the source
filename -> title mapping from all seven, combined, so the raw folder can
mirror the same by-show organization music/ already has — using whatever
show the title ended up in after reassign_shows.py corrected the first
batch, not the original guess.
"""

from __future__ import annotations

import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "trials" / "trial music"
MANIFEST = ROOT / "web" / "samples" / "manifest.json"

# source filename -> title, combined from every import script's TRACKS list
FILE_TO_TITLE = {
    # import_trial_music.py (titles as renamed by rename_trial_titles.py)
    "First_Light_Unfolding_2026-08-14T152702.wav": "First Light Unfolding",
    "Early_Morning_Stillness_2026-08-14T155855.wav": "Early Morning Stillness",
    "Sable Palm Drift.mp3": "Sable Palm Drift",
    "Sable Palm Drift_1.mp3": "Palm Line Horizon",
    "Blue Room Swing.mp3": "Blue Room Swing",
    "Blue Room Swing_1.mp3": "Corner Booth Sway",
    "Dusty Highway.mp3": "Dusty Highway",
    "Dusty Highway_1.mp3": "Shoulder Lane Drift",
    "Follow_The_Rhythm_2026-08-14T160753.wav": "Follow The Rhythm",
    "Velvet Circuit.mp3": "Velvet Circuit",
    "Velvet Circuit_1.mp3": "Low Voltage Blue",
    "Velvet After Hours.mp3": "Velvet After Hours",
    "Velvet After Hours_1.mp3": "Last Call Neon",
    "Blue Smoke Loop.mp3": "Blue Smoke Loop",
    "Blue Smoke Loop_1.mp3": "Ashtray Hours",
    "Late Night Receipt.mp3": "Late Night Receipt",
    "Late Night Receipt_1.mp3": "Closing Tab",
    "Backroom Clean.mp3": "Backroom Clean",
    "Backroom Clean_1.mp3": "Back Door Exit",
    "One_Drop_Nostalgia_2026-08-14T150916.wav": "One Drop Nostalgia",
    # import_artist_tracks.py
    "干杯.wav": "干杯",
    "分不开.mp3": "分不开",
    "No More Games.wav": "No More Games",
    "We Don't Lose.wav": "We Don't Lose",
    "Believe.wav": "Believe",
    "2 on 2.wav": "2 on 2",
    "So Naa.wav": "So Naa",
    "Brandish_150bpm.wav": "Brandish",
    # import_labeled_music.py
    "Golden Hour Groove_afro.mp3": "Golden Hour Groove",
    "Midnight Pulse_house msic.mp3": "Midnight Pulse",
    "Midnight Pulse_trap&Housemix.mp3": "Midnight Pulse (Trap Mix)",
    "Midnight Wax Pocket_hiphop.mp3": "Midnight Wax Pocket",
    "Midnight Wax Pocket_1_hiphop.mp3": "Wax Pocket After Dark",
    "Palm Groove_afro.mp3": "Palm Groove",
    "Palm Groove_1_afro.mp3": "Coastal Palm Sway",
    "Palmwine Neon_afro.mp3": "Palmwine Neon",
    "Velvet Loop_hiphop.mp3": "Velvet Loop",
    "Velvet Loop_1_hiphop.mp3": "Amber Loop Drift",
    "Velvet Smoke Loop_trap.mp3": "Velvet Smoke Loop",
    # import_trap_batch2.py
    "Chrome Habit_trap.mp3": "Chrome Habit",
    "Chrome Habit_1_trap.mp3": "Static Habit",
    "Chrome Pulse_trap.mp3": "Chrome Pulse",
    "Chrome Pulse_1_trap.mp3": "Neon Pulse Drift",
    "Velvet Rim_trap.mp3": "Velvet Rim",
    "Velvet Rim_1_trap.mp3": "Low Rim Static",
    # import_house_batch.py
    "Put it on_house.wav": "Put It On",
    "Redlight_house.wav": "Redlight",
    "Skyline_house.wav": "Skyline",
    "Sunrise_house.wav": "Sunrise",
    "helper_house.wav": "Helper",
    "midnight call_house.wav": "Midnight Call",
    "not the same _house.wav": "Not The Same",
    # import_folk_batch.py
    "Blue Jean Porch_folk.mp3": "Blue Jean Porch",
    "Blue Jean Porch_1_folk.mp3": "Porch Light Waltz",
    "Heather on the Hill_folk.mp3": "Heather on the Hill",
    "Heather on the Hill_1_folk.mp3": "Wildflower Hill",
    "How the Whole Thing Grows_folk.mp3": "How the Whole Thing Grows",
    "How the Whole Thing Grows _folk.mp3": "Roots and Rafters",
    # import_folk_batch2.py
    "Bus Stop Apricot- _folk.mp3": "Bus Stop Apricot",
    "Bus Stop Apricot_1 _folk.mp3": "Apricot Lane Bench",
    "Golden Hour Promise _folk.mp3": "Golden Hour Promise",
    "Golden Hour Promise- _folk.mp3": "Amber Hour Vow",
    "Lantern Study _folk.mp3": "Lantern Study",
    "Lantern Study_1 _folk.mp3": "Lantern Glow Sketch",
    "Morning Light – _folk.mp3": "Morning Light",
    "Morning Light- _folk.mp3": "First Light Hymn",
}


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    title_to_show = {e["title"]: e["show"] for e in manifest}

    moved, unmapped, untracked = 0, [], []
    for f in sorted(SRC.iterdir()):
        if not f.is_file() or f.name == ".DS_Store":
            continue
        title = FILE_TO_TITLE.get(f.name)
        if title is None:
            unmapped.append(f.name)
            continue
        show = title_to_show.get(title)
        if show is None:
            untracked.append((f.name, title))
            continue
        dest_dir = SRC / show
        dest_dir.mkdir(exist_ok=True)
        shutil.move(str(f), str(dest_dir / f.name))
        moved += 1
        print(f"  {show:<14} {f.name}")

    print(f"\n  {moved} files sorted into show subfolders")
    if unmapped:
        print(f"  {len(unmapped)} file(s) with no known mapping (left in place):")
        for n in unmapped:
            print(f"    {n}")
    if untracked:
        print(f"  {len(untracked)} file(s) mapped to a title not currently in manifest.json:")
        for n, t in untracked:
            print(f"    {n} -> {t!r}")


if __name__ == "__main__":
    main()
