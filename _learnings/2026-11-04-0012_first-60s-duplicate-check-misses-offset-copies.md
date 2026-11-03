# The August duplicate check misses a copy that starts later: sketches 107 and 430

**Symptom.** Archive sketches 107 (`xaVdaU-N7Gw`, 188 s) and 430 (`sSIXTq8KlTw`, 168 s) are
the same recording, but `data/duplicates.csv` (detect_duplicates.py, 2026-08-01) did not list
them. The landmark engine found them while mapping compilation `mrIUW3fCUUo`, where both
matched the same stretch.

**Cause.** 107 opens with a ~19 s studio title sequence (ballroom dancers, per its visual
annotation); 430 is the same sketch without it. detect_duplicates.py fingerprints the first
60 s of each file with a small lag search, so a 19.4 s head start put the two out of reach.

**Evidence (2026-11-04).** audfprint2: all of 430 (0.1-167.6 s) matches 107 at offset +19.41 s,
1,560 aligned hashes (9.3/s). Windowed sample-level correlation at that offset: 16 of 16
10-s windows at 0.987-0.996 (August's same-recording range was 0.86-0.99).

**Consequences.** Recorded through the corrections overlay (`duplicate_of` on both rows) and
a row in duplicates.csv (canonical 430, the most viewed). Any other pair where one upload has
an intro or a cold open will hide the same way. A full archive-vs-archive pass with
`audio_index.py match --index archive --queries data/audio` would find the rest (measured
~4.5 s per sketch on this pair, so about an hour for all 702).
