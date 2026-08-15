#!/usr/bin/env bash
# Turn a raw phone/mic recording into a broadcast-ready voice drop.
#
#   ./scripts/clean_voice.sh sources/voice-take-01.m4a morning/greeting
#   ./scripts/clean_voice.sh sources/rec.m4a latenight/goodnight
#
# Second argument is where it lands under drops/today/, without the extension.
# Output is 44.1kHz stereo WAV to match the station.
#
# Add --raw to keep an untouched copy in sources/ for A/B. Drop your original
# recordings in sources/ too — the project should hold everything it needs.

set -euo pipefail
cd "$(dirname "$0")/.."

IN="${1:?usage: clean_voice.sh <input> <band/name> [--raw]}"
DEST="${2:?usage: clean_voice.sh <input> <band/name> [--raw]}"
OUT="drops/today/${DEST}.wav"
mkdir -p "$(dirname "$OUT")"

# Voice rides *under* nothing and *over* music — consistency matters far more
# than loudness. -16 LUFS sits a little above the music bed once smooth_add
# ducks it, without the drop feeling shouted.
TARGET_I=-16
TARGET_TP=-1.5
TARGET_LRA=7

# The chain, in order and why:
#   silenceremove  drop dead air at the head, keep 0.15s so crossfades have
#                  something to grab; same at the tail via areverse.
#                  RMS detection, not peak — a single click or breath in
#                  otherwise-silent room tone reads as signal to a peak
#                  detector and blocks the trim entirely.
#   highpass 85    kill rumble, handling noise, desk thump — nothing musical
#                  lives below 85Hz in a voice
#   afftdn         lift the room tone off the noise floor. Set high enough to
#                  survive what the compressor does next — makeup gain raises
#                  the pauses along with the speech, so under-denoising here
#                  ends with a louder but *noisier* file than you started with
#   equalizer 300  -2dB cut where "boxy" lives in most untreated rooms
#   equalizer 3.4k +3dB presence, so consonants survive under the music
#   deesser        tame the sibilance the presence lift just exaggerated
#   acompressor    even out a 9:1 crest factor into something consistent
#   agate          downward expansion, not a hard gate — pushes the pauses
#                  back down after the compressor lifted them. This does most
#                  of the SNR work: measured on a real take, denoising past
#                  nr=30 changed nothing while the gate moved SNR from 22dB to
#                  31dB. Threshold stops at -31dB deliberately; higher chews
#                  quiet consonants and breath tails
#   alimiter       catch peaks without letting them clip
#
# adeclip goes in front of all of it, and only for takes that actually
# clipped — recorded too hot, not just a peak that happens to touch 0dB.
# astats' "Flat factor" is the tell: it counts runs of consecutive
# identical samples, which is what a clipped waveform's flat-topped peaks
# look like and a merely loud one doesn't have. Running adeclip on a take
# that never clipped does nothing useful and risks smearing transients for
# no reason, so it's conditional rather than always-on.
FLAT=$(ffmpeg -hide_banner -nostats -i "$IN" -af astats=metadata=1 -f null /dev/null 2>&1 \
  | grep -m1 "Flat factor" | sed 's/.*: *//')
DECLIP=""
if [ -n "$FLAT" ] && awk "BEGIN{exit !($FLAT > 0)}"; then
  echo "  clipping detected (flat factor ${FLAT}) — de-clipping before the rest of the chain"
  DECLIP="adeclip,"
fi

CHAIN="${DECLIP}silenceremove=start_periods=1:start_duration=0.1:start_silence=0.15:start_threshold=-36dB:detection=rms,\
areverse,\
silenceremove=start_periods=1:start_duration=0.1:start_silence=0.25:start_threshold=-36dB:detection=rms,\
areverse,\
highpass=f=85,\
afftdn=nr=30:nf=-42,\
equalizer=f=300:t=q:w=1.2:g=-2,\
equalizer=f=3400:t=q:w=1.5:g=3,\
deesser=i=0.35,\
acompressor=threshold=-20dB:ratio=3:attack=8:release=180:makeup=2,\
agate=threshold=0.028:ratio=4:attack=15:release=300:knee=4,\
alimiter=level_in=1:level_out=1:limit=0.94"

echo "Cleaning $(basename "$IN")"

# Two-pass loudness. One pass guesses and drifts; two passes actually land on
# the target, which is what keeps thirty separate recordings sounding like one
# person on one microphone.
echo "  pass 1: measuring"
MEASURED=$(ffmpeg -hide_banner -nostats -i "$IN" \
  -af "${CHAIN},loudnorm=I=${TARGET_I}:TP=${TARGET_TP}:LRA=${TARGET_LRA}:print_format=json" \
  -f null /dev/null 2>&1 | sed -n '/^{/,/^}/p')

get() { echo "$MEASURED" | grep "\"$1\"" | sed 's/.*: *"\([^"]*\)".*/\1/'; }
I=$(get input_i); TP=$(get input_tp); LRA=$(get input_lra)
THRESH=$(get input_thresh); OFFSET=$(get target_offset)

if [ -z "$I" ]; then
  echo "  measurement failed, falling back to single pass"
  LNORM="loudnorm=I=${TARGET_I}:TP=${TARGET_TP}:LRA=${TARGET_LRA}"
else
  echo "  measured $I LUFS, peak $TP dBTP"
  LNORM="loudnorm=I=${TARGET_I}:TP=${TARGET_TP}:LRA=${TARGET_LRA}\
:measured_I=${I}:measured_TP=${TP}:measured_LRA=${LRA}\
:measured_thresh=${THRESH}:offset=${OFFSET}:linear=true"
fi

echo "  pass 2: rendering"
ffmpeg -hide_banner -loglevel error -y -i "$IN" \
  -af "${CHAIN},${LNORM},aresample=44100,aformat=channel_layouts=stereo" \
  -c:a pcm_s16le "$OUT"

# The A/B copy goes to sources/, never into drops/ — anything sitting in a band
# folder is on the air, and shipping the unprocessed take alongside the cleaned
# one means the station plays both.
if [ "${3:-}" = "--raw" ]; then
  mkdir -p sources
  RAW="sources/$(basename "${DEST}")-raw.wav"
  ffmpeg -hide_banner -loglevel error -y -i "$IN" \
    -af "aresample=44100,aformat=channel_layouts=stereo" \
    -c:a pcm_s16le "$RAW"
  echo "  untouched copy for A/B: $RAW"
fi

echo ""
echo "  → $OUT"
ffmpeg -hide_banner -nostats -i "$OUT" -af ebur128=framelog=quiet -f null /dev/null 2>&1 \
  | grep -E "^\s+I:" | sed 's/^/    /'
ffmpeg -hide_banner -nostats -i "$OUT" -af astats=metadata=1 -f null /dev/null 2>&1 \
  | grep -m1 -E "Noise floor dB" | sed 's/^/    /'
