# Matching time in audfprint2 is almost all query analysis, done at 4 time shifts

**Symptom.** Mapping the 256-video fan pool (8,125 min of audio) against two indexes was
on course for ~9 h: ~65 s per ~30-min video per index. Indexing runs at ~220x real time,
so matching at ~30x looked wrong.

**Cause (profiled 2026-11-04, cProfile on one 511 s pool video).** `match_file` took
23.6 s: 20.6 s in `Analyzer.wavfile2hashes` (spectrogram and the per-frame peak-picking
loops) and 3.0 s in `match_hashes` (the index lookup). The analysis runs 4 times per
query, because `setup_analyzer(shifts=0)` means 4 sub-frame shifts when matching and 1 when
indexing (audfprint2/cli.py lines 396-399). The analysis doesn't depend on the index, so
matching one video against two indexes did the expensive part twice.

**Fix.** `audio_index.match(..., hash_cache=DIR)` (CLI `--hash-cache`) stores each query's
hashes as `<video_id>.npz`, keyed on file size, mtime and the analyzer settings, and the
next index reuses them. `map_compilations.py` uses `data/compilations/hashes/`. A
re-matched pool row came out identical to the old one (same 3,709 hashes, same 12 hits).

**Not done, on purpose.** `shifts=1` for queries would cut the analysis ~4x, but the
Phase 0 probe validated the engine with 4 shifts. It needs a fresh ground-truth run
before anyone relies on it. Running two mappers in parallel: not on this laptop. The
mapper holds ~2.4 GB and only ~1.5 GB of 15.6 GB RAM was free.
