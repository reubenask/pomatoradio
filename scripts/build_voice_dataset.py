#!/usr/bin/env python3
"""Assemble a voice-cloning training set from the raw takes.

    python3 scripts/build_voice_dataset.py
    python3 scripts/build_voice_dataset.py --minutes 6 --out sources/voice-training

Two decisions are baked in, and both matter more than they look:

**Raw, not cleaned.** It reads Audio_recorded/, never drops/today/. The cleaned
drops have been compressed, gated, de-essed and limited — a clone trained on
those learns the processing as part of your voice, and then clean_voice.sh
applies it a second time on the way out.

**The best takes, not all of them.** An instant clone wants a few minutes of
your most consistent audio. Feeding it everything, including the quieter and
noisier takes, pulls the model toward the average of your session rather than
the best of it. This ranks by noise floor and level consistency, then stops
once it has enough.

Output is trimmed and peak-matched only — deliberately no EQ, compression or
noise reduction, because those are exactly what you don't want cloned.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import statistics
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# ElevenLabs' own spec for cloning material: -23 to -18 dB RMS, true peak -3 dB.
TARGET_PEAK = -3.0
MIN_SAMPLE = 30          # PVC rejects anything shorter
MERGE_TARGET = 60        # comfortably clear of the minimum


def probe(path: pathlib.Path) -> dict | None:
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
         "-af", "volumedetect,astats=metadata=1", "-f", "null", "/dev/null"],
        capture_output=True, text=True).stderr
    try:
        mean = float(re.search(r"mean_volume: (-?[\d.]+)", r).group(1))
        peak = float(re.search(r"max_volume: (-?[\d.]+)", r).group(1))
    except AttributeError:
        return None
    nf = re.search(r"Noise floor dB: (-?[\d.]+)", r)
    flat = re.search(r"Flat factor: ([\d.]+)", r)
    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.strip()
    return {
        "path": path, "mean": mean, "peak": peak,
        "floor": float(nf.group(1)) if nf else -40.0,
        "flat": float(flat.group(1)) if flat else 0.0,
        "dur": float(dur or 0),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=5.0,
                    help="how much audio to select (default 5)")
    ap.add_argument("--src", default="Audio_recorded")
    ap.add_argument("--out", default="sources/voice-training")
    ap.add_argument("--merge", action="store_true",
                    help="join takes into 60s+ samples for Professional Voice Cloning, "
                         "which rejects anything under 30 seconds")
    ap.add_argument("--all", action="store_true",
                    help="use every usable take, ignoring --minutes (for PVC, where "
                         "total runtime is what matters)")
    args = ap.parse_args()

    src = ROOT / args.src
    files = sorted(src.glob("*.m4a")) + sorted(src.glob("*.wav"))
    if not files:
        print(f"No takes in {src}", file=sys.stderr)
        return 1

    print(f"  measuring {len(files)} takes…")
    stats = [s for s in (probe(f) for f in files) if s]
    med_mean = statistics.median(s["mean"] for s in stats)

    # Lower noise floor is better; closer to the session's typical level is
    # better. Clipped takes are dropped outright — a clone will learn the
    # distortion.
    for s in stats:
        s["score"] = (-s["floor"]) - abs(s["mean"] - med_mean) * 2
        # A peak touching full scale is not distortion — a *run* of samples
        # pinned there is. Judging on peak alone discarded takes that were
        # perfectly clean, which matters when you're counting minutes toward a
        # cloning minimum.
        s["clipped"] = s["flat"] > 0
    picked, total = [], 0.0
    for s in sorted(stats, key=lambda x: -x["score"]):
        if s["clipped"] or s["dur"] < 6:
            continue
        picked.append(s)
        total += s["dur"]
        if not args.all and total >= args.minutes * 60:
            break

    out = ROOT / args.out
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    print(f"\n  {'take':>6} {'floor':>7} {'mean':>7} {'len':>6}")
    print("  " + "-" * 30)
    # Keep 0.6s at each end rather than 0.2s. Across 50-odd takes the
    # difference is well over a minute of material, and a natural pause before
    # and after a line is honest training data — the clone should learn how you
    # actually breathe into a sentence, not a hard cut into speech.
    TRIM = ("silenceremove=start_periods=1:start_duration=0.1:start_silence=0.6:"
            "start_threshold=-45dB:detection=rms,areverse,"
            "silenceremove=start_periods=1:start_duration=0.1:start_silence=0.6:"
            "start_threshold=-45dB:detection=rms,areverse")

    for s in picked:
        dest = out / f"{s['path'].stem}.wav"

        # Peak-normalise to -3 dBFS, ElevenLabs' stated target, by measuring
        # then applying a flat gain. A limiter would reshape the dynamics, and
        # any dynamics processing here is learned as part of the voice.
        m = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-i", str(s["path"]),
             "-af", f"{TRIM},volumedetect", "-f", "null", "/dev/null"],
            capture_output=True, text=True).stderr
        found = re.search(r"max_volume: (-?[\d.]+)", m)
        gain = (TARGET_PEAK - float(found.group(1))) if found else 0.0

        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(s["path"]),
             "-af", f"{TRIM},volume={gain:.2f}dB",
             "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(dest)],
            check=True, capture_output=True)
        print(f"  {s['path'].stem:>6} {s['floor']:7.1f} {s['mean']:7.1f} {s['dur']:6.1f}s  {gain:+5.1f} dB")

    if args.merge:
        merge_samples(out)

    files = sorted(out.glob("*.wav"))
    mb = sum(p.stat().st_size for p in files) / 1e6
    print(f"\n  {len(files)} samples, {total/60:.1f} min, {mb:.1f} MB")
    print(f"  → {out}")

    if total < 30 * 60:
        print(f"\n  Professional Voice Cloning needs 30 min total; you have "
              f"{total/60:.1f}. Use Instant Voice Cloning, which only needs 1-2 min,"
              f"\n  or record another {(30*60-total)/60:.0f} min and come back to PVC.")
    else:
        print("\n  Enough for Professional Voice Cloning.")
    print("  Skipped: clipped takes and anything under 6 seconds.")
    return 0


def merge_samples(out: pathlib.Path) -> None:
    """Join the trimmed takes into ~60s samples.

    Professional Voice Cloning rejects any sample under 30 seconds, and these
    takes are 7-25s each. Merging is only about clearing that gate — it adds no
    audio, so it cannot help with the separate 30-minute total requirement.
    A short gap between takes stops words running together."""
    takes = sorted(out.glob("*.wav"))
    if not takes:
        return

    def dur(p):
        return float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout or 0)

    groups, cur, acc = [], [], 0.0
    for t in takes:
        cur.append(t)
        acc += dur(t)
        if acc >= MERGE_TARGET:
            groups.append(cur)
            cur, acc = [], 0.0
    if cur:                                   # tail: fold into the last group so
        if groups and acc < MIN_SAMPLE:       # nothing lands under the minimum
            groups[-1] += cur
        else:
            groups.append(cur)

    merged = out / "merged"
    merged.mkdir(exist_ok=True)
    print(f"\n  merging into {len(groups)} samples of {MERGE_TARGET}s or more:")
    for i, g in enumerate(groups, 1):
        lst = merged / f"list{i}.txt"
        lst.write_text("".join(f"file '{p.resolve()}'\n" for p in g))
        dest = merged / f"sample-{i:02d}.wav"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-f", "concat", "-safe", "0", "-i", str(lst),
             "-af", "apad=pad_dur=0.35", "-ar", "44100", "-ac", "1",
             "-c:a", "pcm_s16le", str(dest)],
            check=True, capture_output=True)
        lst.unlink()
        print(f"    sample-{i:02d}.wav  {dur(dest):5.1f}s  ({len(g)} takes)")

    for t in takes:
        t.unlink()
    for p in merged.glob("*.wav"):
        p.replace(out / p.name)
    merged.rmdir()


if __name__ == "__main__":
    raise SystemExit(main())
