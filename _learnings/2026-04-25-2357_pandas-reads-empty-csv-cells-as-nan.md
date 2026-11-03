# Pandas reads empty CSV cells as `NaN`, not `""`

*From LEARNINGS.md, section "From the metadata-fetch (2026-04-25)".*

**Pandas reads empty CSV cells as `NaN`, not `""`.** Caught this in `load_resume()`: `r.get("fetch_error") or ""` evaluated to `NaN`, then `str(NaN)` is `"nan"` (truthy), so the resume logic considered every prior row failed and refetched everything. Always check `pd.isna(value)` explicitly when distinguishing "no error" from "error string". Or use `pd.read_csv(..., keep_default_na=False)` if you want all empties as `""`, but that complicates numeric columns.
