#!/usr/bin/env bash
# Bring up the whole station: Icecast, Liquidsoap, and the player page.
#
#   ./start.sh
#
# Ctrl-C stops all three. Logs land in logs/.

set -uo pipefail
cd "$(dirname "$0")"

WEB_PORT="${WEB_PORT:-8080}"

# Icecast's config is generated on every run rather than read from
# $(brew --prefix)/etc/icecast.xml. That system file ships with the password
# "hackme", station.liq sends its own, and the mismatch fails authentication
# with no stream and no obvious cause. Generating it here means the two cannot
# drift: the password below is read out of station.liq itself.
ICECAST_XML="logs/icecast.xml"

mkdir -p logs
pids=()

cleanup() {
  echo ""
  echo "Stopping…"
  for pid in "${pids[@]:-}"; do
    [ -n "$pid" ] && kill "$pid" 2>/dev/null
  done
  wait 2>/dev/null
  echo "Off air."
}
trap cleanup EXIT INT TERM

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing '$1'. Install with: brew install liquidsoap icecast ffmpeg"
    exit 1
  }
}
need liquidsoap
need icecast

# --- sanity: is there anything to actually play? -----------------------------
tracks=$(find music -type f \( -iname "*.mp3" -o -iname "*.wav" -o -iname "*.flac" \
  -o -iname "*.m4a" -o -iname "*.ogg" \) 2>/dev/null | wc -l | tr -d ' ')
if [ "$tracks" -eq 0 ]; then
  echo "No music found in music/. Drop some audio files in there first."
  exit 1
fi
drops=$(find drops/today -type f \( -iname "*.wav" -o -iname "*.mp3" -o -iname "*.m4a" \) \
  2>/dev/null | wc -l | tr -d ' ')

echo "Pomato Radio 130.3"
echo "  $tracks tracks, $drops voice drops"
echo ""

# --- icecast ----------------------------------------------------------------
# Single source of truth for the password: whatever station.liq sends.
PASSWORD=$(grep -m1 '^  password' station.liq | sed 's/.*"\(.*\)".*/\1/')
[ -n "$PASSWORD" ] || { echo "Couldn't read the source password out of station.liq."; exit 1; }

SHARE="$(brew --prefix 2>/dev/null)/share/icecast"
[ -d "$SHARE/web" ] || SHARE="/usr/local/share/icecast"

cat > "$ICECAST_XML" <<XML
<icecast>
  <limits><clients>100</clients><sources>4</sources></limits>
  <authentication>
    <source-password>$PASSWORD</source-password>
    <relay-password>$PASSWORD</relay-password>
    <admin-user>admin</admin-user>
    <admin-password>$PASSWORD</admin-password>
  </authentication>
  <hostname>localhost</hostname>
  <listen-socket><port>8000</port></listen-socket>
  <paths>
    <logdir>$(pwd)/logs</logdir>
    <webroot>$SHARE/web</webroot>
    <adminroot>$SHARE/admin</adminroot>
  </paths>
  <logging>
    <accesslog>icecast-access.log</accesslog>
    <errorlog>icecast-error.log</errorlog>
    <loglevel>2</loglevel>
  </logging>
</icecast>
XML

# Reuse an already-running instance rather than fighting it for port 8000 — but
# only if it accepts our password, otherwise we'd connect to a stranger's
# server and silently fail to publish.
if curl -fs --max-time 2 "http://localhost:8000/status-json.xsl" >/dev/null 2>&1; then
  if curl -fs --max-time 2 -u "admin:$PASSWORD" \
       "http://localhost:8000/admin/stats" >/dev/null 2>&1; then
    echo "  icecast     already running"
  else
    echo "  icecast     something else owns :8000 and won't take our password."
    echo "              Stop it (pkill icecast) and run this again."
    exit 1
  fi
else
  icecast -c "$ICECAST_XML" > logs/icecast.log 2>&1 &
  pids+=($!)
  sleep 2
  if ! curl -fs --max-time 2 http://localhost:8000/status-json.xsl >/dev/null 2>&1; then
    echo "  icecast     FAILED to start — see logs/icecast.log"
    tail -5 logs/icecast.log
    exit 1
  fi
  echo "  icecast     :8000"
fi

# --- liquidsoap -------------------------------------------------------------
pkill -f "liquidsoap station.liq" 2>/dev/null && sleep 1
liquidsoap station.liq > logs/station.log 2>&1 &
pids+=($!)

# Wait for the mount to actually appear before claiming we're on air.
for i in $(seq 1 20); do
  if curl -fs --max-time 2 http://localhost:8000/status-json.xsl 2>/dev/null \
     | grep -q "radio.mp3"; then
    break
  fi
  sleep 1
done
if curl -fs --max-time 2 http://localhost:8000/status-json.xsl 2>/dev/null | grep -q "radio.mp3"; then
  echo "  liquidsoap  on air"
else
  echo "  liquidsoap  FAILED — see logs/station.log"
  tail -5 logs/station.log
fi

# --- player page ------------------------------------------------------------
python3 scripts/serve_web.py --port "$WEB_PORT" > logs/web.log 2>&1 &
pids+=($!)
sleep 1
echo "  player      http://localhost:$WEB_PORT"
echo ""
echo "Listen in a browser, or point VLC at http://localhost:8000/radio.mp3"
echo "Ctrl-C to stop."

wait
