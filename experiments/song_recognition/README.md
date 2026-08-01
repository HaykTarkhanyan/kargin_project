# Song recognition experiment (imported)

Copied verbatim on 2026-08-01 from `~/OneDrive/Desktop/00_notes/misc/kargin_experiment/`
(original dated 2026-07-26). **Not wired into the pipeline** — staged here for
reference and as the basis for a real archive-wide run.

The source folder also held a 5.6 MB `Kargin Haghordum sketch 142 ... [AXFZ8ymj--w].mp3`.
Not copied: that video is already in the archive as `data/audio/*_AXFZ8ymj--w.*`,
so the mp3 is a redundant second copy of audio we have.

## Why this matters

It is the only approach that actually answers "what music is in these sketches".
YouTube will not tell us: the Data API has no copyright-claim field for videos
you don't own, Content ID claims are partner-only, and yt-dlp returns 78 fields
with nothing music-related. Identifying the music ourselves from the audio we
already hold sidesteps all of that.

## What it produced

`song_recognition_results.json`, 5 clips of 12 s from sketch 142 (`AXFZ8ymj--w`),
ShazamIO only — 4 of 5 matched:

| clip | match | label |
|---|---|---|
| 0 s, 8 s | Andrei Petrov — *The play* (from "Autumn Marathon", 1979) | Bel Air Music |
| 204 s, 216 s | Emmanuel Santarromana — *Opéra* (Métropolitain, 1999) | Pschent |
| 223 s | no match | |

Both are real third-party recordings the channel does not own. That video carries
`licensed_content = False` in `data/youtube_metadata.csv`, consistent with the
pattern that all 35 region-blocked videos are also `licensed_content = False`.

ShazamIO needs no API key (it is an unofficial, reverse-engineered client, so it
can break whenever Shazam changes its private service). AudD and ACRCloud both
require credentials and were skipped in this run.

## KNOWN BUG in `recognize_songs.py` — read before reusing

`recognize_acrcloud` is broken, and the file is kept unmodified so the defect is
visible rather than silently inherited:

- The function body stops after building `string_to_sign` (~line 166). The next
  line is `def recognize_shazamio(...)`, so **`recognize_acrcloud` falls off the
  end and returns `None`** — no signature, no request.
- The rest of the ACRCloud implementation (`signature = base64.b64encode(...)`
  through `return post_multipart(...)`, ~lines 186-201) ended up *inside*
  `recognize_shazamio`, after a `try/except` that always returns or raises. It is
  unreachable, and if it ever ran it would `NameError` on `access_secret`,
  `string_to_sign`, `host`, `access_key`, `timestamp` and `data_type`, none of
  which exist in that scope.

Looks like a bad paste. Only the ShazamIO path was ever exercised, which is why
it went unnoticed. Fix the function boundaries before enabling `--provider
acrcloud`, `both`, or `all`.

## To run it as-is

```bash
uv run --with shazamio python experiments/song_recognition/recognize_songs.py \
  --provider shazamio \
  --starts 0,30,60 \
  "data/audio/<file>.webm"
```

## If we take this further

Scale it to all 702: sample a few clips per sketch, cache by `video_id`, make it
resume-safe, and rate-limit politely (ShazamIO is unofficial). Output a
`data/song_matches.csv` keyed on `video_id` with track/artist/label/timestamp.
That would give per-sketch music attribution for the whole archive — a real
"songs in Kargin" dataset, and the input the deferred song-extraction idea in
`PLAN.md` was waiting on.
