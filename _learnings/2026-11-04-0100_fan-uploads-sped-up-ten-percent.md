# Fan channels speed sketches up ~10% (tempo only), which hides them from the matcher

**Symptom.** The landmark matcher survives only ±3% of tempo change and ±0.5% of tape speed
(DECISIONS #21, measured). An earlier ±1.5/3/5% check found "no speed-shifted fan copies",
so leftover `new` clips were taken at face value.

**Evidence (2026-11-04, `speed_sweep.py` in the session scratchpad, results in
`data/audio_index/probe_2026-11-03/speed_sweep.json`).** 100 leftover `new` canonicals
re-queried at a 1%-step tape-speed grid and six tempo factors: 12 match an archive sketch.
- 10 need tempo x0.90 (the upload plays ~11% fast, pitch unchanged), 1 tempo x0.95,
  1 tape speed x0.98.
- 6 of the 12 come from Kargin Club, 3 from Kargin Tube.
- Three uploads say "Kargin Haghordum sketch 424 / 415 / 402" in the title, and each
  speed-corrected match is exactly that sketch.

**Why the first check missed it.** It used a ±1.5/3/5% grid. A clip that needs tempo x0.90
is more than 3% away from every factor in that grid (the nearest, 0.95, is 5.5% off),
so with ±3% tolerance none of them could bring it back. It also used the single-stretch
score of that time, which the method review later replaced.

**Consequences.** Without a speed pass, roughly 1 in 8 `new` clusters in the triage queue
are sketches the archive already has. The sweep took ~58 s per clip for 28 variants; the
hits sit at tempo 0.90-0.95 and tape speed ~0.98, so a narrower grid is the cheap way
to cover the whole queue.
