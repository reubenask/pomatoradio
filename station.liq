#!/usr/bin/env liquidsoap
#
# The station. Genre rotates by weekday, voice drops land every couple of hours
# and duck the music underneath instead of cutting it, and you can take over the
# mic live at any time.
#
#   liquidsoap station.liq
#
# Requires Liquidsoap 2.2 or newer.

settings.log.level := 3
settings.log.stdout := true

root = path.dirname(argv(0))
music_dir = "#{root}/music"

# Passwords come from the environment so they never sit in a public repo. The
# defaults are deliberately obvious placeholders — fine on a laptop where only
# you can reach port 8000, not fine on a machine facing the internet.
#
#   export POMATO_SOURCE_PASSWORD='...'   # liquidsoap → icecast
#   export POMATO_LIVE_PASSWORD='...'     # your mic → liquidsoap
#
# start.sh reads the same two variables when it generates icecast.xml, so the
# two halves cannot drift apart.
source_password = environment.get(default = "change-me", "POMATO_SOURCE_PASSWORD")
live_password = environment.get(default = "change-me-too", "POMATO_LIVE_PASSWORD")

# ---------------------------------------------------------------- the library

# Folders collect junk — .DS_Store, stray .txt, artwork. Skip anything that
# isn't playable rather than letting the decoder fail on it every rotation.
def is_audio(r) =
  uri = string.case(lower = true, request.uri(r))
  string.match(pattern = "\\.(wav|mp3|m4a|flac|ogg|opus|aiff)$", uri)
end

# One folder per genre. reload_mode="watch" means adding a track to a folder
# shows up on air without restarting anything.
def genre(name) =
  playlist(
    id = name,
    mode = "randomize",
    reload_mode = "watch",
    check_next = is_audio,
    "#{music_dir}/#{name}"
  )
end

# ------------------------------------------------------------------- the shows
#
# The day is seven named shows. Music and talking share the same folder names,
# so "Slow Drive" means music/slowdrive/ and drops/today/slowdrive/ — one
# vocabulary for both.
#
#   06-10  firstlight      soft, slow, nothing demanding
#   10-12  slowroll        warmer, jazzier, awake
#   12-14  midday          brighter, easy
#   14-17  longafternoon   focus music, minimal, low drama
#   17-20  slowdrive       rush hour — steady, calm, get-home-safe
#   20-23  nightgarage     deeper, groove, house and garage
#   23-06  smallhours      sparse, ambient, quiet
#
# Music selection used to rotate by weekday. It rotates by show instead: what
# suits a drive home has nothing to do with whether it's Tuesday.
def weekday_shows(~track_sensitive = true, mk) =
  night = mk("smallhours")
  switch(
    track_sensitive = track_sensitive,
    [
      ({ 23h-24h }, night),
      ({ 0h-6h }, night),
      ({ 6h-10h }, mk("firstlight")),
      ({ 10h-12h }, mk("slowroll")),
      ({ 12h-14h }, mk("midday")),
      ({ 14h-17h }, mk("longafternoon")),
      ({ 17h-20h }, mk("slowdrive")),
      ({ 20h-23h }, mk("nightgarage"))
    ]
  )
end

# The weekend isn't a mood, it's a genre schedule — each day belongs to a sound.
# 5w is Friday, 6w Saturday, 7w Sunday, 1w Monday.
#
#   Fri 17:00 - Sat 06:00   afrofriday     afrobeats, all night
#   Sat 06:00 - 12:00       saturdaysoul   r&b and soul, easy start
#   Sat 12:00 - 18:00       hiphop         hip hop through the afternoon
#   Sat 18:00 - 22:00       trap           harder, the night building
#   Sat 22:00 - Sun 06:00   househours     house, peak of the weekend
#   Sun 06:00 - 14:00       sundayfolk     folk and acoustic, gentle
#   Sun 14:00 - 22:00       country        country and americana
#   Sun 22:00 - Mon 06:00   sundaynight    r&b, closing the weekend out
#
# The nights deliberately run past midnight into the next date: Friday night
# *is* Saturday 1am, and Sunday night is Monday 1am — same reason
# sundaynight needs both a 7w and a 1w case below, same shape as afrofriday.
# The schedule agrees with how people live, not with the calendar.
def by_show(~track_sensitive = true, mk) =
  afro = mk("afrofriday")
  house = mk("househours")
  sundaynight = mk("sundaynight")
  switch(
    track_sensitive = track_sensitive,
    [
      ({ 5w and 17h-24h }, afro),
      ({ 6w and 0h-6h }, afro),
      ({ 6w and 6h-12h }, mk("saturdaysoul")),
      ({ 6w and 12h-18h }, mk("hiphop")),
      ({ 6w and 18h-22h }, mk("trap")),
      ({ 6w and 22h-24h }, house),
      ({ 7w and 0h-6h }, house),
      ({ 7w and 6h-14h }, mk("sundayfolk")),
      ({ 7w and 14h-22h }, mk("country")),
      ({ 7w and 22h-24h }, sundaynight),
      ({ 1w and 0h-6h }, sundaynight),
      ({ true }, weekday_shows(track_sensitive = track_sensitive, mk))
    ]
  )
end

# Track-sensitive, so a show change never chops a song in half — the new show
# starts on the next track.
by_hour = by_show(genre)

# music/any/ is the catch-all: anything that suits the station at any hour.
# With a small library, put everything there and the shows fill in over time.
# Silence is the one failure a radio station can't survive, so blank() last.
music = fallback(track_sensitive = false, [by_hour, genre("any"), blank()])

# normalize() rides a moving gain to hit a target level. That's right for a
# library pulled from mixed sources at wildly different levels — and wrong for
# tracks you mastered yourself, where it second-guesses the master, drops the
# level (measured: -13.1 LUFS in, -15.3 out) and can pump on loud sections.
#
# Off while the library is your own masters. Uncomment when you add third-party
# music and tracks start jumping in volume between songs.
# music = normalize(music)

music = crossfade(fade_in = 2., fade_out = 3., duration = 5., music)

# ------------------------------------------------------------------ the voice

# Drops live in four time-band folders so a three-in-the-morning line never
# airs at noon. Drop your own recordings straight into these — the station
# doesn't care whether a wav came from your microphone or from TTS.
# The band folders hold .txt scripts next to their .wav audio — same is_audio
# guard as the genre folders above.
def band(name) =
  playlist(
    id = "drops-#{name}",
    mode = "randomize",
    reload_mode = "watch",
    check_next = is_audio,
    "#{root}/drops/today/#{name}"
  )
end

# Same seven shows, same clock — the host's folder for the show that's on air.
band_now = by_show(track_sensitive = false, band)

# anytime/ is in the rotation, not a fallback behind it. Written as
# fallback([band_now, anytime]) the evergreen drops only ever air when the
# current band folder is empty — so the moment you record a single night drop,
# all twelve anytime drops go permanently silent. random() picks between the
# two and skips whichever is unavailable, so empty folders still cost nothing.
drops = random(weights = [1, 1], [band_now, band("anytime")])

# Minimum gap between drops. 30 minutes while the library is 4 generic
# anytime clips — often enough that listeners hear a human, not so often it
# repeats within a sitting. Once the full 56-drop set is recorded, widen this
# back toward 7200. (two hours), since a real per-show script set shouldn't
# need to lean on frequency to feel present.
drops = delay(1800., drops)

# The live mic. Point a broadcaster (BUTT, Mixxx) at:
#   host localhost / port 8005 / mount live / POMATO_LIVE_PASSWORD
live = input.harbor("live", port = 8005, password = live_password)

# Both the generated drops and your live mic ride *over* the music, ducking it
# down rather than replacing it — the sound of a DJ talking across an intro.
#
# p is the amplitude the music keeps while a voice is on top. The default 0.2
# is -14dB, which measured deep enough that the bed nearly disappears and it
# reads as "voice with music behind it". 0.35 is about -9dB, inside the 8-12dB
# a radio station actually ducks by, so the record stays present under you.
# Lower it toward 0.2 if the music ever fights your voice for intelligibility.
radio = smooth_add(p = 0.35, normal = music, special = drops)
radio = smooth_add(p = 0.35, normal = radio, special = live)

# --------------------------------------------------------------- now playing

# Written on every track change. The YouTube overlay reads this file; harmless
# to leave running even if you never stream video.
# Plenty of free-to-broadcast music arrives untagged — and ffmpeg's Ogg muxer
# drops metadata under -c copy, so even files we tag ourselves can come through
# bare. Rather than showing "untitled", fall back to the filename, which the
# library already follows: "Artist - Title.mp3".
def from_filename(m) =
  base = path.remove_extension(path.basename(m["filename"]))
  parts = string.split(separator = " - ", base)
  if list.length(parts) >= 2 then
    (list.nth(default = "", parts, 0),
     string.concat(separator = " - ", list.tl(parts)))
  else
    ("", base)
  end
end

def write_now_playing(m) =
  artist = m["artist"]
  title = m["title"]

  # Tags win; the filename is the safety net.
  let (artist, title) =
    if artist == "" or title == "" then
      let (fa, ft) = from_filename(m)
      (if artist == "" then fa else artist end,
       if title == "" then ft else title end)
    else
      (artist, title)
    end

  if artist != "" and title != "" then
    file.write(data = "#{artist} — #{title}", "#{root}/nowplaying.txt")
  elsif title != "" then
    file.write(data = title, "#{root}/nowplaying.txt")
  end
end

radio.on_metadata(synchronous = false, write_now_playing)

# ------------------------------------------------------------------- output

# MP3 via ffmpeg rather than %mp3 — the Homebrew build ships without the native
# LAME encoder, so %mp3 compiles fine and then dies at startup with "unsupported
# format". This route works everywhere ffmpeg does.
output.icecast(
  %ffmpeg(
    format = "mp3",
    %audio(codec = "libmp3lame", b = "128k", samplerate = 44100, channels = 2)
  ),
  format = "audio/mpeg",
  host = "localhost",
  port = 8000,
  password = source_password,
  mount = "radio.mp3",
  name = "Pomato Radio 130.3",
  radio
)
