#!/usr/bin/env python3
"""Turn Icecast's access log into a readable listener report.

    python3 scripts/listener_report.py
    python3 scripts/listener_report.py --log /path/to/icecast-access.log
    python3 scripts/listener_report.py --since 2026-08-14

Icecast logs one line per connection to a mount, and the last field is how
many seconds that connection lasted — logged when it ends, so a listener
still connected when the log was read won't show up yet. Only counts GET
/radio.mp3: SOURCE lines are Liquidsoap pushing audio in, not a listener
pulling it out, and would otherwise inflate the count.

::1 and 127.0.0.1 are almost certainly you testing locally, not an actual
listener — flagged separately rather than silently dropped, since a
legitimate loopback listener isn't impossible, just unlikely.
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOCAL_IPS = {"::1", "127.0.0.1"}

LINE_RE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) [^"]*" '
    r'(?P<status>\d+) (?P<bytes>\S+) "[^"]*" "(?P<agent>[^"]*)" (?P<duration>\d+)$'
)
TS_FMT = "%d/%b/%Y:%H:%M:%S %z"


def fmt_secs(s: float) -> str:
    s = int(s)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=str(ROOT / "logs" / "icecast-access.log"))
    ap.add_argument("--mount", default="/radio.mp3")
    ap.add_argument("--since", help="YYYY-MM-DD, only count connections from this date on")
    args = ap.parse_args()

    log = pathlib.Path(args.log)
    if not log.exists():
        print(f"No log at {log} — nothing's connected to Icecast yet.", file=sys.stderr)
        return 1

    since = dt.datetime.strptime(args.since, "%Y-%m-%d").date() if args.since else None

    sessions = []
    for line in log.read_text(errors="replace").splitlines():
        m = LINE_RE.match(line)
        if not m or m["method"] != "GET" or m["path"] != args.mount:
            continue
        when = dt.datetime.strptime(m["ts"], TS_FMT)
        if since and when.date() < since:
            continue
        sessions.append({
            "ip": m["ip"], "when": when, "duration": int(m["duration"]),
            "agent": m["agent"], "local": m["ip"] in LOCAL_IPS,
        })

    if not sessions:
        print(f"No completed connections to {args.mount} in {log.name}"
              + (f" since {since}" if since else "") + ".")
        print("(A listener still connected when the log was checked won't show up "
              "until they disconnect — Icecast logs duration at the end.)")
        return 0

    real = [s for s in sessions if not s["local"]]
    local = [s for s in sessions if s["local"]]

    def summarize(label: str, rows: list) -> None:
        if not rows:
            return
        durations = [r["duration"] for r in rows]
        ips = {r["ip"] for r in rows}
        span = (min(r["when"] for r in rows), max(r["when"] for r in rows))
        print(f"\n{label}: {len(rows)} connections, {len(ips)} unique address(es)")
        print(f"  {span[0]:%Y-%m-%d %H:%M} → {span[1]:%Y-%m-%d %H:%M}")
        print(f"  total listening time : {fmt_secs(sum(durations))}")
        print(f"  average session       : {fmt_secs(statistics.mean(durations))}")
        print(f"  median session         : {fmt_secs(statistics.median(durations))}")
        print(f"  longest session        : {fmt_secs(max(durations))}")

    print(f"Source: {log}")
    summarize("Real listeners (non-local)", real)
    summarize("Local/loopback (probably you testing)", local)

    if not real:
        print("\nEverything so far is local testing — no external listener has "
              "connected yet. That's expected until the station is reachable "
              "somewhere other than localhost.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
