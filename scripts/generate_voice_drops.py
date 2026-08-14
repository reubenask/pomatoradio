#!/usr/bin/env python3
"""Generate every drop in your cloned voice and file it by show.

    export ELEVENLABS_API_KEY=...
    export ELEVENLABS_VOICE_ID=...

    python3 scripts/generate_voice_drops.py --dry-run     # costs nothing
    python3 scripts/generate_voice_drops.py
    python3 scripts/generate_voice_drops.py --only firstlight
    python3 scripts/generate_voice_drops.py --force       # redo existing

Reads the numbered scripts straight out of drops/SCRIPTS.md and maps each one
to its show and kind by position — the same numbering you recorded to. Existing
files are skipped unless --force, so an interrupted run costs nothing to resume.

**Output is level-matched, not cleaned.** clean_voice.sh exists to rescue phone
recordings: EQ, de-essing, compression, gating. Running any of that over TTS
output makes it worse — there is no room tone to gate and no proximity to
correct. All that's needed is the same -16 LUFS the recorded drops sit at, so
the host doesn't change volume between a generated line and a recorded one.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "drops" / "SCRIPTS.md"

WEEKDAY = ["firstlight", "slowroll", "midday", "longafternoon",
           "slowdrive", "nightgarage", "smallhours"]
WEEKEND = ["afrofriday", "saturdaysoul", "hiphop", "trap",
           "househours", "sundayfolk", "country"]
WK_KINDS = ["greeting", "staytuned", "break", "back", "handover"]
WE_KINDS = ["greeting", "staytuned", "handover"]

TARGET_LUFS = -16          # matches the recorded drops

# Words the model guesses wrong, rewritten phonetically on the way to the API.
# The scripts stay readable; only what's spoken changes.
#
# Substitution rather than SSML phoneme tags because eleven_multilingual_v2 —
# the default model here — doesn't support them. Phoneme tags need flash_v2 or
# v3. Respelling works on every model, which makes it the safer mechanism.
SAY_AS = {
    "Pomato": "Pommayto",          # po-MAY-to, following 'tomato'
}


def phonetic(text: str) -> str:
    for word, spoken in SAY_AS.items():
        text = re.sub(rf"\b{re.escape(word)}\b", spoken, text)
    return text


def plan() -> dict[int, tuple[str, str]]:
    out, n = {}, 1
    for show in WEEKDAY:
        for kind in WK_KINDS:
            out[n] = (show, kind); n += 1
    for show in WEEKEND:
        for kind in WE_KINDS:
            out[n] = (show, kind); n += 1
    return out


def parse_scripts() -> dict[int, str]:
    """Pull the numbered lines out of SCRIPTS.md.

    Each is '**12. stay tuned** — text…' and runs until a blank line, so the
    text can wrap across lines in the source without breaking."""
    text = SCRIPTS.read_text()
    found = {}
    for m in re.finditer(
            r"^\*\*(\d+)\.\s*[a-z ]+\*\*\s*—\s*(.+?)(?=\n\s*\n|\n\*\*\d+\.|\n#|\Z)",
            text, re.M | re.S):
        num = int(m.group(1))
        body = re.sub(r"\s+", " ", m.group(2)).strip()
        found[num] = body
    return found


def speak(text: str, key: str, voice: str, model: str) -> bytes:
    body = {
        "text": text,
        "model_id": model,
        # Stability 0.5 keeps a station ident consistent take to take; too low
        # and the same line read twice drifts in tone. Style stays modest —
        # high style values start performing, which is wrong for continuity.
        "voice_settings": {
            "stability": 0.50,
            "similarity_boost": 0.85,
            "style": 0.15,
            "use_speaker_boost": True,
        },
    }
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
        data=json.dumps(body).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def normalise(raw: bytes, dest: pathlib.Path) -> None:
    """Two-pass loudness to -16 LUFS. Level only — no EQ, no compression."""
    tmp = pathlib.Path(tempfile.mkstemp(suffix=".mp3")[1])
    tmp.write_bytes(raw)
    try:
        measured = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-i", str(tmp),
             "-af", f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=7:print_format=json",
             "-f", "null", "/dev/null"],
            capture_output=True, text=True).stderr
        blob = re.search(r"\{[^{}]*input_i[^{}]*\}", measured, re.S)
        if blob:
            d = json.loads(blob.group(0))
            f = (f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=7"
                 f":measured_I={d['input_i']}:measured_TP={d['input_tp']}"
                 f":measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}"
                 f":offset={d['target_offset']}:linear=true")
        else:
            f = f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=7"
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(tmp),
             "-af", f"{f},aresample=44100", "-ac", "2", "-c:a", "pcm_s16le", str(dest)],
            check=True, capture_output=True)
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="regenerate existing files")
    ap.add_argument("--only", help="one show only")
    ap.add_argument("--model", default=os.environ.get("ELEVENLABS_MODEL",
                                                      "eleven_multilingual_v2"))
    args = ap.parse_args()

    mapping, scripts = plan(), parse_scripts()
    missing = sorted(set(mapping) - set(scripts))
    if missing:
        print(f"  note: no script text found for {missing}", file=sys.stderr)

    jobs = []
    for num, (show, kind) in sorted(mapping.items()):
        if args.only and show != args.only:
            continue
        if num not in scripts:
            continue
        dest = ROOT / "drops" / "today" / show / f"{num:02d}-{kind}.wav"
        jobs.append((num, show, kind, scripts[num], dest))

    todo = [j for j in jobs if args.force or not j[4].exists()]
    chars = sum(len(j[3]) for j in todo)

    print(f"  {len(jobs)} drops in scope, {len(todo)} to generate, "
          f"{len(jobs)-len(todo)} already present")
    print(f"  {chars:,} characters  (~{chars/1000:.1f}k credits)\n")

    if args.dry_run:
        for num, show, kind, text, _ in todo[:8]:
            print(f"  {num:>2} {show}/{kind}: {text[:60]}…")
        if len(todo) > 8:
            print(f"  … and {len(todo)-8} more")
        return 0

    key = os.environ.get("ELEVENLABS_API_KEY")
    voice = os.environ.get("ELEVENLABS_VOICE_ID")
    if not key or not voice:
        print("Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID.", file=sys.stderr)
        return 1

    done = failed = 0
    for num, show, kind, text, dest in todo:
        try:
            audio = speak(phonetic(text), key, voice, args.model)
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:200]
            print(f"  {num:>2} {show}/{kind}  HTTP {e.code}: {detail}", file=sys.stderr)
            failed += 1
            if e.code in (401, 402):        # bad key or out of credits — stop
                break
            continue
        except Exception as e:
            print(f"  {num:>2} {show}/{kind}  {e}", file=sys.stderr)
            failed += 1
            continue

        normalise(audio, dest)
        print(f"  {num:>2} {show}/{kind:<10} {dest.stat().st_size/1e6:4.1f} MB")
        done += 1

    print(f"\n  generated {done}, failed {failed}")
    if done:
        print("  levels matched to the recorded drops at -16 LUFS")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
