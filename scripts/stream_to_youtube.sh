#!/usr/bin/env bash
# Pair the audio stream with a looping visual and push it to YouTube Live.
#
#   export YOUTUBE_STREAM_KEY=xxxx-xxxx-xxxx-xxxx
#   ./scripts/stream_to_youtube.sh
#
# Optional: drop a loop.mp4 next to this repo's root for the background. A few
# seconds is plenty — it loops forever.

set -euo pipefail
cd "$(dirname "$0")/.."

: "${YOUTUBE_STREAM_KEY:?Set YOUTUBE_STREAM_KEY first}"
LOOP="${LOOP_VIDEO:-loop.mp4}"
STREAM="${AUDIO_STREAM:-http://localhost:8000/radio.mp3}"
FONT="${FONT_FILE:-/System/Library/Fonts/Supplemental/Georgia.ttf}"

[ -f "$LOOP" ] || { echo "No $LOOP found. Add a short background video."; exit 1; }
: > nowplaying.txt  # make sure the overlay has something to read

# drawtext with reload=1 re-reads nowplaying.txt every frame, so the credit
# updates the moment Liquidsoap changes tracks.
exec ffmpeg -hide_banner \
  -stream_loop -1 -re -i "$LOOP" \
  -i "$STREAM" \
  -map 0:v -map 1:a \
  -vf "drawtext=fontfile=${FONT}:textfile=nowplaying.txt:reload=1:\
fontcolor=white@0.85:fontsize=34:x=80:y=h-140:box=1:boxcolor=black@0.35:boxborderw=18" \
  -c:v libx264 -preset veryfast -tune stillimage \
  -b:v 3000k -maxrate 3000k -bufsize 6000k \
  -pix_fmt yuv420p -g 60 -r 30 \
  -c:a aac -b:a 128k -ar 44100 \
  -f flv "rtmp://a.rtmp.youtube.com/live2/${YOUTUBE_STREAM_KEY}"
