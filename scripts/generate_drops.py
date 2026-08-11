#!/usr/bin/env python3
"""Write one day's worth of voice drops, then speak them in your cloned voice.

Run it once each morning. It clears drops/today/ and refills it, so the station
picks up fresh material without a restart.

    python3 scripts/generate_drops.py              # today
    python3 scripts/generate_drops.py --day fri    # a specific weekday
    python3 scripts/generate_drops.py --dry-run    # write scripts, skip the TTS
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

import anthropic

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from tts import speak  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DROPS = ROOT / "drops" / "today"
MUSIC = ROOT / "music"
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
AUDIO_EXT = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".opus"}
# Must match the time-band folders station.liq switches on.
BANDS = [(6, "night"), (12, "morning"), (18, "afternoon"), (24, "evening")]


def band_for(hour: int) -> str:
    return next(name for cutoff, name in BANDS if hour < cutoff)

# One drop per kind, rotated across the day so the station never repeats a shape.
KINDS = {
    "station_id": "A station identification. Two sentences at most. Name the station.",
    "hour_note": "An observation tied to this specific hour of the day and how it feels.",
    "track_credit": "Credit artists from today's rotation by name. Say something true "
    "and specific about the music, not generic praise.",
    "musing": "One idea from the signature-content section, said out loud. This is the "
    "closest thing to a monologue and it still stays under 60 words.",
    "sign_off": "A handoff back to the music. One or two sentences.",
}

SCHEMA = {
    "type": "object",
    "properties": {
        "drops": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "hour": {"type": "integer"},
                    "kind": {"type": "string", "enum": sorted(KINDS)},
                    "text": {"type": "string"},
                },
                "required": ["hour", "kind", "text"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["drops"],
    "additionalProperties": False,
}


def artists_for(genre: str, limit: int = 40) -> list[str]:
    """Read artist names off today's library.

    Assumes the `Artist - Track.mp3` filename convention that most Creative
    Commons downloads already use. Anything without a dash is skipped rather
    than guessed at — a drop that credits the wrong artist is worse than one
    that credits nobody.
    """
    folder = MUSIC / genre
    if not folder.is_dir():
        return []
    names = []
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() in AUDIO_EXT and " - " in f.stem:
            artist = f.stem.split(" - ", 1)[0].strip()
            if artist and artist not in names:
                names.append(artist)
    return names[:limit]


def build_prompt(persona: str, day: str, cfg: dict, artists: list[str]) -> str:
    day_cfg = cfg["days"][day]
    slots = cfg["drop_slots"]
    kinds = "\n".join(f"- {name}: {desc}" for name, desc in KINDS.items())

    if artists:
        roster = (
            "Artists in today's rotation — these are the only names you may say "
            "on air, spelled exactly like this:\n"
            + "\n".join(f"- {a}" for a in artists)
        )
    else:
        roster = (
            "The library has no readable artist names today. Do not invent any. "
            "Write the track_credit drops so they work without naming anyone."
        )

    return f"""Here is the host's voice document for a 24/7 online radio station.

<persona>
{persona}
</persona>

Today is {day.upper()}. Today's music is **{day_cfg['genre']}**.
Programming note for the day: {day_cfg['vibe']}

{roster}

Write one spoken drop for each of these hours (24-hour clock): {slots}

A drop is what the host says between songs. It is read aloud over a music bed by
a cloned voice, so write for the ear: no headings, no lists, no stage directions,
no emoji, no brackets or placeholders, and no text the voice would have to spell
out. Contractions are good. Numbers spelled as words.

Rotate through these kinds across the day so no two consecutive drops have the
same shape:
{kinds}

Length: 15 to 55 words each. The 3am drop should be the shortest thing on the
station; the 9am and 6pm drops can be the longest.

Two things matter more than anything else:
- It has to sound like the persona document, not like a radio announcer.
- Each drop must be specific to its hour and to today's genre. A drop that would
  work equally well on any day at any hour is a failed drop — rewrite it.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", choices=WEEKDAYS, help="defaults to today")
    ap.add_argument("--dry-run", action="store_true", help="write .txt only, no audio")
    args = ap.parse_args()

    day = args.day or WEEKDAYS[dt.date.today().weekday()]
    cfg = json.loads((ROOT / "schedule.json").read_text())
    persona = (ROOT / "persona.md").read_text()
    artists = artists_for(cfg["days"][day]["genre"])

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model="claude-opus-5",
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": SCHEMA},
        },
        messages=[
            {"role": "user", "content": build_prompt(persona, day, cfg, artists)}
        ],
    )

    if response.stop_reason == "refusal":
        print("Model declined to write this batch. Check persona.md.", file=sys.stderr)
        return 1

    text = next(b.text for b in response.content if b.type == "text")
    drops = json.loads(text)["drops"]

    # Clear yesterday's generated drops, band by band. Anything you recorded
    # yourself and filed under anytime/ is left alone — this only owns what it
    # wrote.
    for _, band in BANDS:
        folder = DROPS / band
        folder.mkdir(parents=True, exist_ok=True)
        for stale in folder.iterdir():
            stale.unlink()

    for drop in sorted(drops, key=lambda d: d["hour"]):
        folder = DROPS / band_for(drop["hour"])
        stem = f"{drop['hour']:02d}-{drop['kind']}"
        (folder / f"{stem}.txt").write_text(drop["text"] + "\n")
        print(f"{folder.name}/{stem}  {drop['text']}")
        if not args.dry_run:
            speak(drop["text"], folder / f"{stem}.wav")

    print(f"\n{len(drops)} drops written to {DROPS}")
    if args.dry_run:
        print("Dry run — no audio. Read them, edit any .txt, then rerun without --dry-run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
