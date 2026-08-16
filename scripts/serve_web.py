#!/usr/bin/env python3
"""Serve the Pomato FM player page.

    python3 scripts/serve_web.py          # http://localhost:8080
    python3 scripts/serve_web.py --port 9000

Three routes, and that's the whole server:

  /                 the player page (web/index.html)
  /nowplaying.txt   whatever Liquidsoap last wrote there
  /status.json      Icecast's status, proxied

The proxy exists so the page can read listener counts without a cross-origin
request. Icecast lives on :8000, the page on :8080 — fetching status directly
would need CORS headers Icecast doesn't send by default. Proxying it through
here makes it same-origin and the problem disappears.

Audio is different: an <audio> element may load cross-origin freely, so the
stream itself is pulled straight from :8000 with no proxying.

Local development only — binds to loopback, single-threaded, no auth.
"""

from __future__ import annotations

import argparse
import datetime as dt
import http.server
import json
import pathlib
import re
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
ICECAST_STATUS = "http://localhost:8000/status-json.xsl"

# ---------------------------------------------------------------- the schedule
#
# Computed here, on the station's clock, because that is the only clock that
# means anything. There is one stream, so every listener hears the same audio at
# the same instant no matter where they are — a listener in London at 9am is
# hearing whatever the station is playing at *its* 9am, not theirs. If the page
# worked this out from the browser clock it would confidently name a show that
# isn't playing.
#
# ⚠ Mirrors the switch in station.liq. Change one, change the other.
SHOWS = {
    "firstlight":    ("first light",    "morning"),
    "slowroll":      ("slow roll",      "morning"),
    "midday":        ("midday",         "afternoon"),
    "longafternoon": ("long afternoon", "afternoon"),
    "slowdrive":     ("slow drive",     "evening"),
    "nightgarage":   ("night garage",   "evening"),
    "smallhours":    ("small hours",    "night"),
    "afrofriday":    ("afro friday",    "evening"),
    "saturdaysoul":  ("saturday soul",  "morning"),
    "hiphop":        ("hip hop hours",  "afternoon"),
    "trap":          ("trap",           "evening"),
    "househours":    ("house hours",    "night"),
    "sundayfolk":    ("sunday folk",    "morning"),
    "country":       ("country",        "afternoon"),
    "sundaynight":   ("sunday night",   "night"),
}


def show_at(when: dt.datetime) -> str:
    h = when.hour
    w = when.isoweekday()          # 1 = Monday … 7 = Sunday, same as Liquidsoap

    if w == 5 and h >= 17:
        return "afrofriday"
    if w == 6:
        if h < 6:
            return "afrofriday"    # Friday night runs past midnight
        if h < 12:
            return "saturdaysoul"
        if h < 18:
            return "hiphop"
        if h < 22:
            return "trap"
        return "househours"
    if w == 7:
        if h < 6:
            return "househours"    # Saturday night, same idea
        if h < 14:
            return "sundayfolk"
        if h < 22:
            return "country"
        return "sundaynight"
    if w == 1 and h < 6:
        return "sundaynight"       # Sunday night runs past midnight

    if h < 6:
        return "smallhours"
    if h < 10:
        return "firstlight"
    if h < 12:
        return "slowroll"
    if h < 14:
        return "midday"
    if h < 17:
        return "longafternoon"
    if h < 20:
        return "slowdrive"
    if h < 23:
        return "nightgarage"
    return "smallhours"


def schedule_now() -> dict:
    """Current show, and when the next one starts — on station time."""
    now = dt.datetime.now()
    current = show_at(now)

    # Boundaries only ever fall on the hour, so stepping by an hour finds the
    # changeover exactly. 48 covers the longest run (afrofriday, 13 hours) with
    # room to spare.
    nxt, at = current, None
    probe = now.replace(minute=0, second=0, microsecond=0)
    for _ in range(48):
        probe += dt.timedelta(hours=1)
        candidate = show_at(probe)
        if candidate != current:
            nxt, at = candidate, probe
            break

    # The server can just look, so the page never has to guess. Drop
    # web/label-<show>.png in and it appears on the next poll; without this the
    # page would probe for artwork that mostly doesn't exist and litter the
    # console with failed requests.
    art = ROOT / "web" / f"label-{current}.png"
    art_url = f"label-{current}.png" if art.exists() else "label.png"

    clip = ROOT / "web" / f"label-{current}.mp4"
    clip_url = f"label-{current}.mp4" if clip.exists() else "label.mp4"

    label, palette = SHOWS[current]
    return {
        "show": current,
        "label": label,
        "palette": palette,
        "art": art_url,
        "clip": clip_url,
        "station_time": now.strftime("%H:%M"),
        "station_tz": time.strftime("%Z") or "local",
        "station_offset_minutes": int(-time.timezone / 60 if not time.daylight
                                      else -time.altzone / 60),
        "next": {
            "show": nxt,
            "label": SHOWS[nxt][0],
            "at": at.strftime("%H:%M") if at else None,
        },
    }


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def do_GET(self):  # noqa: N802 - stdlib naming
        route = self.path.split("?", 1)[0]

        if route == "/":
            self.path = "/web/index.html"
        elif route in ("/label.png", "/label.mp4") or route.startswith("/samples/"):
            # The page uses relative asset paths so it also works when hosted
            # under a subpath (GitHub Pages serves projects from /<repo>/).
            # Served from / locally, those resolve to the root — map them back.
            self.path = "/web" + route
        elif route == "/status.json":
            return self._proxy_status()
        elif route == "/nowplaying.txt":
            return self._nowplaying()
        elif route == "/show.json":
            return self._send(json.dumps(schedule_now()).encode(), "application/json")

        # SimpleHTTPRequestHandler has never supported Range requests — it
        # always serves the whole file. Without a 206 response an <audio>
        # element reports itself as unseekable (seekable = [0,0]) even once
        # fully buffered, which silently breaks both the join-mid-track start
        # and the crossfade, since both work by setting currentTime. GitHub
        # Pages' CDN honours Range natively; this stands in for that locally.
        if self.headers.get("Range"):
            served = self._serve_range()
            if served:
                return
        return super().do_GET()

    def _serve_range(self) -> bool:
        fpath = pathlib.Path(self.translate_path(self.path))
        if not fpath.is_file():
            return False

        m = re.match(r"bytes=(\d*)-(\d*)", self.headers["Range"])
        size = fpath.stat().st_size
        if not m or not (m.group(1) or m.group(2)):
            return False

        if m.group(1):
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else size - 1
        else:                                    # "bytes=-500" = last 500 bytes
            start = max(0, size - int(m.group(2)))
            end = size - 1
        end = min(end, size - 1)

        if start >= size or start > end:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return True

        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(fpath)))
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with open(fpath, "rb") as f:
            f.seek(start)
            self.wfile.write(f.read(end - start + 1))
        return True

    def _proxy_status(self):
        try:
            with urllib.request.urlopen(ICECAST_STATUS, timeout=2) as r:
                body = r.read()
        except (urllib.error.URLError, TimeoutError, OSError):
            # Icecast isn't up. Not an error worth shouting about — the page
            # just shows "off air" until it is.
            body = json.dumps({"icestats": {"source": []}}).encode()
        self._send(body, "application/json")

    def _nowplaying(self):
        path = ROOT / "nowplaying.txt"
        body = path.read_bytes() if path.exists() else b""
        self._send(body, "text/plain; charset=utf-8")

    def _send(self, body: bytes, content_type: str):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()   # adds Cache-Control
        self.wfile.write(body)

    def end_headers(self):
        # Local dev server: never cache. Without this, replacing an asset in
        # place (label.png especially) leaves the browser showing the old file
        # with no obvious reason why, and you go looking for a bug in the CSS.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        # Advertised on every response, not just 206s — a browser that never
        # sees this on the plain 200 assumes Range isn't supported at all and
        # won't bother trying, which is exactly the failure mode this exists
        # to fix.
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def log_message(self, fmt, *args):
        # One line per request is noise when the page polls every 5 seconds.
        #
        # args[0] is the request line for normal logging but an HTTPStatus when
        # this is reached via log_error — and `"x" in HTTPStatus.NOT_FOUND`
        # raises TypeError, which killed the connection mid-404 and surfaced in
        # the browser as ERR_EMPTY_RESPONSE instead of a clean Not Found.
        first = str(args[0]) if args else ""
        if "/status.json" in first or "/nowplaying.txt" in first:
            return
        super().log_message(fmt, *args)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    args = ap.parse_args()

    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Pomato FM player  →  http://localhost:{args.port}")
    print("Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
