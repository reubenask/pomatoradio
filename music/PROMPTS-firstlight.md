# Generation prompts — First Light

**Show:** `firstlight/` · Monday–Friday, 06:00–10:00 · 4 hours a day
**Target:** ~30 tracks (about 69 for a morning with zero repeats)

From `schedule.json`: *soft, slow, nothing demanding. Music for opening the
laptop and deciding what the day is.*

---

## Settings, before any prompt

- **Instrumental — always on.** Vocals fight your voice drops, and lyrics you've
  heard forty times stop being background. This is the single most important
  setting.
- **Length:** 3–4 minutes. Shorter means more crossfades per hour; longer gets
  repetitive in a four-hour show.
- **Don't name living artists.** "In the style of [artist]" is discouraged by
  both platforms, sometimes blocked, and legally murkier than describing the
  sound yourself. Every prompt below describes instruments and feel instead.
- **Generate more than you need and delete freely.** Expect to keep about half.

---

## The base prompt

Use this as-is for your first few, then work through the variations.

> Slow instrumental ambient lo-fi at 68 BPM. Felt piano with the hammers
> audible, warm analogue pads underneath, soft upright bass. Brushed drums kept
> very low in the mix, or none at all. Unhurried and spacious, hopeful but not
> bright — early morning, nobody in a rush. Tape saturation, gentle vinyl
> crackle, wide natural reverb. No vocals, no build-ups, no drops, no sudden
> dynamics. Consistent volume throughout.

**Why it's shaped this way.** The last two sentences do the heavy lifting: a
station needs tracks with a flat dynamic profile, because anything that
suddenly swells will duck your voice drop or startle someone at seven in the
morning. Most AI music defaults to a build — you have to ask it not to.

---

## Twelve variations

Same show, different textures, so four hours doesn't sound like one idea. Run
each two or three times.

**1. Felt piano** — Slow instrumental at 65 BPM, solo felt piano with soft pads
far back in the mix. Sparse, lots of space between phrases. Warm, intimate,
early morning. No percussion, no vocals, no build-ups.

**2. Rhodes** — Gentle instrumental at 72 BPM led by a warm Rhodes electric
piano, soft brushed drums, muted upright bass. Jazzy but very relaxed, no
soloing. Tape warmth, no vocals, steady volume throughout.

**3. Guitar** — Slow instrumental at 70 BPM, fingerpicked nylon guitar with
light reverb, soft synth pad underneath. Warm and unhurried, folk-adjacent but
ambient. No percussion, no vocals, no dynamic swells.

**4. Ambient, no drums** — Beatless ambient at very slow tempo. Long warm synth
pads, distant piano notes, faint field recording of morning air. Extremely calm,
almost still. No percussion, no vocals, no structure changes.

**5. Vibraphone** — Soft instrumental at 66 BPM. Vibraphone melody, warm double
bass, brushed snare barely present. Mellow, spacious, nostalgic. Tape hiss, no
vocals, consistent dynamics.

**6. Strings** — Slow instrumental at 60 BPM. Muted string ensemble, soft
sustained cello, distant piano. Neo-classical and gentle, warm rather than sad.
No percussion, no vocals, no crescendos.

**7. Lo-fi hip hop** — Lo-fi instrumental hip hop at 74 BPM. Dusty drums low in
the mix, warm sampled piano chords, soft sub bass. Relaxed head-nod feel,
nothing aggressive. Vinyl crackle, no vocals, steady throughout.

**8. Harp and pad** — Slow instrumental at 62 BPM. Plucked harp motif over warm
analogue pads, occasional soft bass note. Delicate, airy, first light. No
drums, no vocals, no build.

**9. Marimba** — Gentle instrumental at 76 BPM. Soft marimba pattern, warm bass,
brushed percussion very low. Gently rhythmic without being energetic. Wooden and
warm, no vocals, flat dynamics.

**10. Tape organ** — Slow instrumental at 64 BPM. Warm tape organ chords, soft
electric piano, subtle bass. Hazy, saturated, slightly worn. No percussion, no
vocals, no dynamic changes.

**11. Flute and pad** — Slow ambient instrumental at 68 BPM. Breathy flute
melody, warm pads, soft double bass. Calm and pastoral, morning air. Light
reverb, no drums, no vocals.

**12. Clock-and-drift** — Beatless slow instrumental. Warm drone, occasional
soft piano note, faint ticking texture in the background. Meditative and
patient, almost no movement. No percussion, no vocals, no structure.

---

## After generating

Download as WAV or the highest-quality MP3 available, then name each file:

```
Pomato Radio - First Light 01.wav
```

`Artist - Title` is the convention the station reads — the player shows what's
playing from the tags, and falls back to this filename pattern if tags are
missing. Then:

```bash
# drop them into the show folder
open music/firstlight
```

Liquidsoap picks up new files without a restart.

---

## Two things to check by ear

**Loudness consistency.** AI generators vary track to track. Once you have a
batch, tell me and I'll level-match the folder — the same two-pass treatment the
voice drops get, so nothing jumps when a track changes at 6am.

**Endings.** Some generated tracks stop abruptly rather than resolving. The
station crossfades over 5 seconds, which hides most of it, but a hard stop is
still audible. Delete those rather than keeping them for the sake of the count.
