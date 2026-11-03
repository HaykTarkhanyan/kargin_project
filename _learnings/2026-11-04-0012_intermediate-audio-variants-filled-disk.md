# A probe that writes every variant before matching any filled the disk

**Symptom.** The first speed-tolerance probe (2026-11-03) wrote 2,168 speed-shifted WAVs
(12 GB) into the scratchpad before matching them, and took the C: drive down to 5.5 GB free.

**Cause.** "Generate all inputs, then process" is the natural loop shape, but uncompressed
WAV is big (these averaged 5.5 MB each), and a grid of factors x clips multiplies fast.

**Fix.** Deleted that one scratchpad folder by its literal path (16+ GB free again). Every
later probe (speed_tolerance.py, speed_sweep.py) writes ONE temporary file, matches it,
deletes it, then moves on; the sweep spends ~2.7 s per variant on writing and matching it,
and disk use stays flat.

**Consequences.** Before a loop writes intermediates, multiply count x size. Above a few
hundred MB, stream them one at a time.
