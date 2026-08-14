#!/usr/bin/env python3
"""Fetch free-to-broadcast music from the Internet Archive netlabels collection
and file it by show.

    python3 scripts/fetch_music.py --per-show 5           # a taste of everything
    python3 scripts/fetch_music.py --show smallhours -n 40
    python3 scripts/fetch_music.py --per-show 30 --allow-nc

Netlabels are labels that release music free online; the Archive mirrors about
61,000 licensed items. Every track keeps its licence and attribution in the
file's own tags, and gets a line in CREDITS.md.

**Licences.** By default this only takes tracks you could still play if the
station ever earned money: CC0, public domain, CC BY, BY-SA, BY-ND. Roughly
four in five netlabel releases are NonCommercial, so --allow-nc opens up far
more music — at the cost of having to strip it all out later if you monetise.
NoDerivatives is fine either way: broadcasting a track doesn't derive from it.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "pomato-radio/1.0 (personal internet radio)"}

# What each show is hunting for. Netlabel subject tags are inconsistent, so
# these are deliberately broad — the licence filter and your ears do the rest.
SHOWS = {
    "firstlight":    ["ambient", "piano", "calm"],
    "slowroll":      ["jazz", "downtempo", "trip hop"],
    "midday":        ["chillout", "lounge", "electronica"],
    "longafternoon": ["minimal", "drone", "ambient"],
    "slowdrive":     ["downtempo", "dub", "chillout"],
    "nightgarage":   ["house", "techno", "electro"],
    "smallhours":    ["ambient", "drone", "field recording"],
    "afrofriday":    ["afrobeat", "afro", "percussion"],
    "saturdaysoul":  ["soul", "funk", "rnb"],
    "hiphop":        ["hip hop", "instrumental hip hop", "beats"],
    "trap":          ["trap", "bass", "hip hop"],
    "househours":    ["house", "deep house", "dance"],
    "sundayfolk":    ["folk", "acoustic", "guitar"],
    "country":       ["country", "americana", "bluegrass"],
}

SAFE = ["publicdomain", "/zero/", "/by/", "/by-sa/", "/by-nd/"]
NC = ["/by-nc/", "/by-nc-sa/", "/by-nc-nd/"]

AUDIO = (".mp3", ".ogg", ".flac", ".m4a", ".wav")


def get(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def licence_ok(url: str, allow_nc: bool) -> bool:
    u = (url or "").lower()
    if not u:
        return False
    if any(k in u for k in SAFE):
        return True
    return allow_nc and any(k in u for k in NC)


def search(term: str, rows: int, page: int = 1):
    q = f'collection:netlabels AND mediatype:audio AND subject:"{term}" AND licenseurl:[* TO *]'
    url = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode({
        "q": q, "rows": rows, "page": page, "output": "json",
        "sort[]": "downloads desc",
    }) + "&fl[]=identifier&fl[]=title&fl[]=creator&fl[]=licenseurl"
    try:
        return get(url)["response"]["docs"]
    except Exception as e:
        print(f"    search failed for {term!r}: {e}", file=sys.stderr)
        return []


def pick_track(identifier: str):
    """Smallest reasonable audio file in the item — netlabel items are often
    whole albums, and one representative track beats a 200MB download."""
    try:
        meta = get(f"https://archive.org/metadata/{identifier}")
    except Exception:
        return None
    # Prefer mp3: ffmpeg's Ogg muxer silently drops metadata under -c copy, so
    # an .ogg arrives untagged and the player has nothing to name it with.
    best = None
    for f in meta.get("files", []):
        name = f.get("name", "")
        low = name.lower()
        if not low.endswith(AUDIO):
            continue
        try:
            size = int(f.get("size", 0))
        except (TypeError, ValueError):
            continue
        if not (1_000_000 < size < 25_000_000):      # skip clips and 30-min sets
            continue
        rank = 0 if low.endswith(".mp3") else 1
        cand = (rank, size, name, f.get("title") or pathlib.Path(name).stem)
        if best is None or cand[:2] < best[:2]:
            best = cand
    return (best[2], best[1], best[3]) if best else None


def clean(s: str) -> str:
    s = re.sub(r"[^\w\s.-]", "", str(s or "")).strip()
    return re.sub(r"\s+", " ", s)[:70] or "untitled"


def pretty_title(raw: str, artist: str) -> str:
    """Netlabel filenames are catalogue numbers, not titles — 'pcr089_02_emil_
    davydov_sketch_no2' is what you get. This is what the player shows, so it's
    worth unpicking: separators to spaces, leading catalogue and track numbers
    dropped, and the artist's own name removed when it's repeated in the file."""
    t = re.sub(r"\.[a-z0-9]{2,4}$", "", str(raw or ""), flags=re.I)
    t = re.sub(r"[_\-]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    # Leading catalogue codes (pcr089, ORE013) and track numbers (02, 09.)
    t = re.sub(r"^([a-z]{2,5}\s?\d{2,5}\s+)+", "", t, flags=re.I)
    t = re.sub(r"^\d{1,3}[\s.]+", "", t)
    t = re.sub(r"^\d{1,3}(?=[A-Za-z])", "", t)      # '09Ubuibi' — no separator

    # The artist's name often repeats inside the filename.
    for part in [artist] + artist.split():
        if len(part) > 3:
            t = re.sub(rf"\b{re.escape(part)}\b", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -.")

    if not t or len(t) < 2:
        t = re.sub(r"[_\-]+", " ", str(raw or "untitled")).strip()
    return clean(t.title())


def fetch(show: str, want: int, allow_nc: bool, dry: bool) -> int:
    dest = ROOT / "music" / show
    dest.mkdir(parents=True, exist_ok=True)
    have = {p.stem.lower() for p in dest.glob("*.*")}
    got = 0

    for term in SHOWS[show]:
        if got >= want:
            break
        for doc in search(term, rows=want * 6):
            if got >= want:
                break
            if not licence_ok(doc.get("licenseurl", ""), allow_nc):
                continue

            artist = clean(doc.get("creator") or "Unknown")
            album = clean(doc.get("title") or doc["identifier"])
            picked = pick_track(doc["identifier"])
            if not picked:
                continue
            name, size, title = picked
            title = pretty_title(title, artist)
            stem = f"{artist} - {title}"
            if stem.lower() in have:
                continue

            out = dest / (stem + pathlib.Path(name).suffix.lower())
            print(f"    {stem[:58]:<58} {size/1e6:5.1f} MB")
            if dry:
                got += 1
                have.add(stem.lower())
                continue

            url = f"https://archive.org/download/{doc['identifier']}/{urllib.parse.quote(name)}"
            tmp = out.with_suffix(out.suffix + ".part")
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as fh:
                    while chunk := r.read(1 << 16):
                        fh.write(chunk)
            except Exception as e:
                print(f"      download failed: {e}", file=sys.stderr)
                tmp.unlink(missing_ok=True)
                continue

            # Tag it, so the player names the track and the credit travels with
            # the file rather than living only in CREDITS.md.
            tagged = out.with_suffix(".tagged" + out.suffix)
            r = subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(tmp),
                 "-c", "copy",
                 "-metadata", f"artist={artist}",
                 "-metadata", f"title={title}",
                 "-metadata", f"album={album}",
                 "-metadata", f"license={doc.get('licenseurl','')}",
                 "-metadata", f"comment=via archive.org/details/{doc['identifier']}",
                 str(tagged)],
                capture_output=True)
            if r.returncode == 0:
                tagged.replace(out)
                tmp.unlink(missing_ok=True)
            else:
                tmp.replace(out)                      # keep it, just untagged
                tagged.unlink(missing_ok=True)

            credit(show, artist, title, doc)
            have.add(stem.lower())
            got += 1
            time.sleep(0.4)                           # be polite to the Archive
    return got


def credit(show, artist, title, doc):
    f = ROOT / "music" / "CREDITS.md"
    if not f.exists():
        f.write_text(
            "# Credits\n\nEvery track here is used under the licence shown. "
            "CC BY and BY-SA require this attribution — keep this file with the "
            "station, and credit artists on air where you can.\n\n"
            "| show | artist | track | licence | source |\n"
            "|---|---|---|---|---|\n")
    lic = (doc.get("licenseurl", "") or "").replace("http://", "https://")
    with f.open("a") as fh:
        fh.write(f"| {show} | {artist} | {title} | {lic} | "
                 f"https://archive.org/details/{doc['identifier']} |\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", choices=sorted(SHOWS))
    ap.add_argument("--per-show", type=int, default=0)
    ap.add_argument("-n", type=int, default=5)
    ap.add_argument("--allow-nc", action="store_true",
                    help="include NonCommercial tracks (more choice, blocks monetising)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    shows = [args.show] if args.show else sorted(SHOWS)
    want = args.per_show or args.n
    total = 0
    for s in shows:
        print(f"\n  {s}  (want {want})")
        total += fetch(s, want, args.allow_nc, args.dry_run)
    print(f"\n  {total} tracks{' (dry run)' if args.dry_run else ''}")
    if not args.dry_run and total:
        print("  credits appended to music/CREDITS.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
