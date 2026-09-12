# non_essential/

Maintained dev/QA tooling that is not needed to operate the project.

| Script | What it does / when to re-run |
|---|---|
| `build_text_annotation_pilot_report.py` | Builds the side-by-side HTML report (`data/text_annotations_pilot/report.html`) comparing flash3 vs flash38 pilot annotations, plus spend totals from the ledger. Re-run after adding pilot rows. Added 2026-09-07 for the text-annotation model pilot. |
| `parse_google_forms.py` | Turns the raw Google Forms captures in `data/google_forms/<n>/` (Playwright dumps of `FB_PUBLIC_LOAD_DATA_` + page HTML) into `form.json`, `form.md`, `page_text.txt` and downloads the question/option images at full size. Re-run after re-capturing a form. See `data/google_forms/README.md`. Added 2026-09-11. |
| `report_usage.py` | Pulls the Firestore `events` collection (site + Telegram bot usage) into `data/usage/` — raw dump, JSON summary, HTML report. Re-run any time you want to know what people searched for. `--from-dump <path>` re-aggregates without re-reading Firestore. Needs `--group firebase` and the SA key at `internal/firebase-sa-kargin-archive.json`. Added 2026-09-11. |
