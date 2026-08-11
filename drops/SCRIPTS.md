# Recording scripts

Thirty-five drops — five for each of the seven dayparts.

Every daypart gets the same five **kinds**, because that's what a real shift
sounds like: you open the hour, you keep people with you through it, you go to
a break, you come back, and you hand over to the next hour.

| kind | when it airs | what it does |
|---|---|---|
| **greeting** | top of the daypart | welcomes people in, names the station |
| **stay tuned** | middle of the set | reminds them someone's there |
| **break** | going into an ad | "back after this" |
| **back** | returning from one | picks the thread up |
| **handover** | end of the daypart | points at what's next |

Record all five for every daypart and the station never repeats itself in a
single sitting.

**How to record:** phone voice memos are fine — these sit under music, so room
tone matters more than gear. Warm and unhurried, like you're talking to one
person who just tuned in. Record the whole set in one session so the voice
matches. Half a second of silence at each end.

```bash
./scripts/clean_voice.sh sources/rec.m4a firstlight/greeting
```

The folder decides when it airs; the filename is yours.

**Monday to Friday daytime**

| folder | on air |
|---|---|
| `firstlight/` | 06:00 – 10:00 |
| `slowroll/` | 10:00 – 12:00 |
| `midday/` | 12:00 – 14:00 |
| `longafternoon/` | 14:00 – 17:00 |
| `slowdrive/` | 17:00 – 20:00 |
| `nightgarage/` | 20:00 – 23:00 |
| `smallhours/` | 23:00 – 06:00 |

**Friday 17:00 through Sunday 22:00** — the weekend runs by genre. Scripts in
the weekend section below.

| folder | on air |
|---|---|
| `afrofriday/` | Fri 17:00 – Sat 06:00 |
| `saturdaysoul/` | Sat 06:00 – 12:00 |
| `hiphop/` | Sat 12:00 – 18:00 |
| `trap/` | Sat 18:00 – 22:00 |
| `househours/` | Sat 22:00 – Sun 06:00 |
| `sundayfolk/` | Sun 06:00 – 14:00 |
| `country/` | Sun 14:00 – 22:00 |

`anytime/` airs at any hour on either schedule.

> **Before you record the break lines:** an ad break needs something to break
> *to*. If you say "back after this" and the music simply continues, it sounds
> broken. Either record a few house spots first — a station promo, a shout-out,
> anything that fills ten seconds — or skip the **break** and **back** drops
> and record two extra *stay tuned* lines per daypart instead.

---

## `firstlight/` — 06:00–10:00

**1. greeting** — Good morning, and welcome to Pomato Radio, one-thirty-point-three.
Wherever you're starting from today, I'm glad you're here with me. Let's ease
into it together.

**2. stay tuned** — You're listening to Pomato Radio. Stay with me — there's good
music coming your way all morning.

**3. break** — We're going to take a short break. Don't go anywhere, I'll be
right back with more.

**4. back** — And we're back. Thanks for staying with me. Let's pick up right
where we left off.

**5. handover** — That's the morning almost done, and you made it. Stay tuned —
brunch is next.

---

## `slowroll/` — 10:00–12:00

**6. greeting** — Good morning, and welcome to brunch here on Pomato Radio,
one-thirty-point-three. Whether you're eating or just pretending to, you're in
good company.

**7. stay tuned** — Hope you're enjoying the music. Keep it right here — I've got
plenty more lined up for you.

**8. break** — We'll pause for a short break. Stay close, I'll be right here when
we get back.

**9. back** — Welcome back to Pomato Radio. Glad you stuck around.

**10. handover** — Brunch is winding down. Stay with me through lunch — there's
more music on the way.

---

## `midday/` — 12:00–14:00

**11. greeting** — Good afternoon, listeners, and welcome to lunch on Pomato
Radio, one-thirty-point-three. Take a proper break today. You've earned it.

**12. stay tuned** — Hope you're having a wonderful day so far. Stay tuned, there's
plenty more to come.

**13. break** — Time for a short break. We'll be right back, so don't go far.

**14. back** — And we're back — thank you for your company. Let's get back to the
music.

**15. handover** — That's lunch. Stay with me into the afternoon, and I'll keep
you going.

---

## `longafternoon/` — 14:00–17:00

**16. greeting** — Good afternoon, and welcome back to Pomato Radio,
one-thirty-point-three. I know this hour can be a slow one — let's get through
it together.

**17. stay tuned** — You're with me on Pomato Radio. Stay tuned, the best of the
afternoon is still ahead.

**18. break** — We'll take a short break for a word from our sponsors. Don't go
anywhere.

**19. back** — Welcome back to the afternoon on Pomato Radio. Good to have you.

**20. handover** — The afternoon's nearly done and you made it through. Stay
tuned, supper is next.

---

## `slowdrive/` — 17:00–20:00

**21. greeting** — Good evening, listeners, and welcome to Pomato Radio,
one-thirty-point-three. The day's behind you now — let's take it easy.

**22. stay tuned** — Hope you're enjoying the music this evening. Keep it right
here with me.

**23. break** — Just a short break, and then we'll be straight back with more.

**24. back** — And we're back. Thank you for staying tuned.

**25. handover** — That's supper done. Stay with me — the evening is just getting
started.

---

## `nightgarage/` — 20:00–23:00

**26. greeting** — Good evening, and welcome back to Pomato Radio,
one-thirty-point-three. Settle in — this is the good part of the day.

**27. stay tuned** — Hope you're having a wonderful evening. Stay tuned, there's
more music on the way.

**28. break** — We're going to take a short break. Stay close, I'll be right back.

**29. back** — Welcome back. Glad you're still here with me.

**30. handover** — The evening's winding down now. Stay tuned — I'll be here with
you through the night.

---

## `smallhours/` — 23:00–06:00

**31. greeting** — Good evening, night owls, and welcome to the late show on
Pomato Radio, one-thirty-point-three. Wherever you are tonight, thank you for
keeping me company.

**32. stay tuned** — Still with me? Good. Stay tuned — I'll keep the music going
as long as you're listening.

**33. break** — We'll take one short break. I'll be right here when we get back.

**34. back** — Welcome back to the small hours on Pomato Radio.

**35. handover** — That's about it from me tonight. Thank you for listening,
sleep well, and I'll see you in the morning. Goodnight.

---

# Weekend

Friday evening through Sunday. Each show is a genre now, so **name it** — that's
what makes it feel like a station with a schedule rather than a playlist. More
lift in the voice than the weekday shows; you're pleased *for* people rather
than keeping them company.

Three per show instead of five: skip the break and back lines until you have
something to advertise.

## `afrofriday/` — Fri 17:00 – Sat 06:00

**36. greeting** — Good evening, and welcome to Afro Friday on Pomato Radio,
one-thirty-point-three. The week is done. Afrobeats from here until sunrise.

**37. stay tuned** — You're with Afro Friday. Stay right there — we're going all
night.

**38. handover** — Afro Friday is winding down, but the weekend is only getting
started. Stay with me.

## `saturdaysoul/` — Sat 06:00 – 12:00

**39. greeting** — Good morning, and welcome to Saturday Soul on Pomato Radio,
one-thirty-point-three. R&B to ease you into the weekend.

**40. stay tuned** — Hope you're taking it slow this morning. Stay tuned, there's
more soul on the way.

**41. handover** — That's Saturday Soul. Hip hop is next — stay with me.

## `hiphop/` — Sat 12:00 – 18:00

**42. greeting** — Good afternoon, and welcome to the hip hop hours on Pomato
Radio, one-thirty-point-three.

**43. stay tuned** — Hope you're having a good Saturday. Keep it locked right here.

**44. handover** — That's the afternoon done. It gets harder from here — stay
tuned.

## `trap/` — Sat 18:00 – 22:00

**45. greeting** — Good evening. You're locked into Pomato Radio,
one-thirty-point-three, and the night starts right now.

**46. stay tuned** — Hope you're getting ready for something good. Stay tuned.

**47. handover** — That's the warm-up. House music from here until sunrise —
don't go anywhere.

## `househours/` — Sat 22:00 – Sun 06:00

**48. greeting** — Good evening, and welcome to House Hours on Pomato Radio,
one-thirty-point-three. This is the peak of the weekend. Enjoy yourselves.

**49. stay tuned** — Hope you're having a wonderful night. We're going straight
through till morning.

**50. handover** — That's the night just about done. Thank you for spending it
with me. Sleep well.

## `sundayfolk/` — Sun 06:00 – 14:00

**51. greeting** — Good morning, and welcome to Sunday on Pomato Radio,
one-thirty-point-three. Folk and acoustic, and absolutely no hurry.

**52. stay tuned** — Hope you're having a gentle morning. Stay right where you are.

**53. handover** — Enjoy the rest of your Sunday. Country is coming up — stay with
me.

## `country/` — Sun 14:00 – 22:00

**54. greeting** — Good afternoon, and welcome to the country hour on Pomato
Radio, one-thirty-point-three. Windows open, feet up.

**55. stay tuned** — Hope you're having a wonderful Sunday. Keep it right here
with me.

**56. handover** — That's Sunday about done. Thank you for spending it with me —
I'll see you in the morning.

---

## After you record

```bash
find ~/Desktop/radio/drops/today -name "*.wav" | sort
```

Anything in a band folder is on the air — there's no staging area, so keep
rough takes in `compare/`.
