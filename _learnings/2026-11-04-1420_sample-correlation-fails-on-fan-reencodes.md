# Sample-level correlation is the wrong referee on fan re-uploads

**Symptom.** In map_compilations' shortcut audit on the fan pool (2026-11-04), 11 of 50
accepted hits "failed" the windowed correlation check, against 0 of 50 on the archive's
own compilations. 10 of the 11 were matches against fan clips, at 6.6-14 hashes/s held
for 60-90 s, mostly with 0% of the 10 s windows agreeing.

**Cause.** Measured on 6 of them with 2 s windows and a +-1.5 s lag search
(scratchpad `drift_probe.py`):
- Same audio with a tiny speed difference plus a lossy re-encode. Correlation is 0.6-0.95
  per 2 s window, and the best lag walks steadily (e.g. -20 ms to 0 ms over 80 s, i.e.
  ~0.03% speed). Inside a 10 s window that drift plus the re-encode drops correlation
  under the 0.6 bar, while landmark hashes don't care.
- Spans that run past the real match. `time_quantile=0.0` reports the full extent of the
  matched hashes, so a few stray ones at an edge stretch the span (`goz59cFpfds`: 2 s
  windows correlate 0.63-0.92 for 24 s, then 0.09 at the span's end).
- Looping music, which is not a sketch. ՀայTV's "actors then and now" slideshows
  (`5hUT109p7YU` and fan clips `mEtWzcFQNjM`, `0pp4KFQUPRU`) share one music track, so
  one clip matches the video at dozens of offsets 20-50 s apart with 1,000-1,900 hashes
  each. At the best offset every 2 s window correlates at 1.00; the audited hit was a
  weaker alignment of the same loop. These slideshows reached the candidates because the
  gate kept ՀայTV (15/17 of its sampled unmarked uploads matched the archive), and they
  sit in the triage as `new` clusters of 1-3.

**Consequences.**
- On fan material the density shortcut was right and the referee was wrong. The audit's
  "11 of 50" is not an error rate of the shortcut.
- Hits that only the windowed check rejected cover at most 140 of the pool's 4,252
  `unknown` minutes (3.3%, 48 videos). So a few unknown gaps there are false, and the
  other ~4,100 min have no hit at all.
- Before mining those gaps (Phase M5), confirm with 2 s windows and a wider lag search,
  or with the time spread of the matched hashes, not with 10 s windows. The 10 s check
  stays fine for the archive's own compilations, whose audio is KarginTV's own.
