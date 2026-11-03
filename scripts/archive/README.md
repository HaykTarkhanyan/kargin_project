# archive/

One-off scripts kept as an institutional record: finished investigations and
throwaway diagnostics. Not expected to still run unchanged, and never imported by
live code.

| Script | What it did / when you would re-run it |
|---|---|
| `p0_groundtruth.py` | Phase 0.1 of the archive-extension plan: built 128 query clips with known right answers (the 23 duplicate and 4 contains pairs from `data/duplicates.csv`, 60 s cut from the middle of 20 sketches with seed 509, the same behind a 20 s noise intro, sped up 4% with and without pitch, reversed speech and noise as negatives). Re-run to rebuild the clips if a new engine needs probing: `python p0_groundtruth.py <repo> <out dir>`. Moved here 2026-11-03; the answers are in `data/audio_index/probe_2026-11-03/groundtruth.csv`. |
| `p0_probe_audfprint.py` | Phase 0.2: matched those clips against an audfprint2 index of the 702 archive files and saved every hit (`probe_results.json`). Needs a venv with `audfprint2==0.1.2`. Moved here 2026-11-03 after the probe decided Q13 (DECISIONS #21). |
| `p0_rescore.py` | Re-scored the probe by matched hashes per query second; produced `probe_summary.json` (threshold 2.0/s, 67/67 unmodified positives, worst offset error 0.02 s, 0/40 sped-up). Moved here 2026-11-03. |
