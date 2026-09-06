# Deferred TODO

Topics parked so they don't get lost. Move an item out when work starts.

## Contact sheets: one frame-grid image per sketch (parked 2026-09-03)

Wanted for two uses: (1) see a whole sketch at a glance, (2) let Claude reason
about a video visually without paying for per-frame images.

Input: the 360p corpus in `data/video/` (640x360, downloading as of this note).
Tooling: plain ffmpeg — `fps=<rate>,scale=<tile_w>:-1,tile=<cols>x<rows>` plus
`drawtext` with `%{pts\:hms}` to burn the timestamp into each tile (without
timestamps Claude cannot anchor what it sees to a moment in the video).

Design envelope, from the live vision docs (platform.claude.com, read
2026-09-03 — the old tokens=w*h/750 formula is obsolete):
- Cost is ceil(w/28) * ceil(h/28) tokens (28 px patches). Token cost depends on
  TOTAL SHEET AREA only — packing more, smaller tiles into the same sheet is
  free; what it trades away is per-frame legibility.
- Claude 4.7+ (incl. Fable, Opus 5) take up to 2576 px long edge / 4784 tokens
  without downscaling. Older/Haiku tier: 1568 px / 1568 tokens.
- >20 images in one request triggers a stricter 2000 px per-image cap — one
  sheet per sketch keeps requests small anyway.

Concrete options at 2560 px wide (all ~1 sheet per sketch):
- 8x5 grid of 320x180 tiles = 2560x900 -> 3,036 tokens, 40 frames.
- 6x4 grid of 426x240 tiles = 2556x960 -> 3,220 tokens, 24 frames (more legible).
- Same 40-frame sheet as 30 separate full-res 640x360 frames would be ~9,000
  tokens (299 each) — the grid is ~3x cheaper.
- Consumption will be Claude Code on the subscription (Read tool on the image
  file), NOT the paid API — so no per-call dollar cost. The token math still
  matters identically though: sheets burn context window and usage limits at
  ~3k tokens each vs ~9k+ for loose frames.

Sampling: DECIDED (owner, 2026-09-03) — fixed ~40 frames per video
(interval = duration/40), one sheet per sketch. The long tail gets coarse
(max 19:37 -> 1 frame/29 s) and the owner explicitly does not care about that
outlier. Scene-detect sampling was considered and dropped — sketches are
mostly single-scene dialogues with few cuts.

Storage: ~250-400 MB of JPEGs for 702 sheets, gitignored next to data/video/.
Compute: sequential ffmpeg, tens of minutes on this laptop. No GPU needed.

## Firebase migration + bot follow-ups (parked 2026-09-07)

Small items surfaced by the two review passes and the bot build, none blocking:

- **`web/lib/log.ts` try-block hardening** — `JSON.stringify(filters)` and
  `crypto.randomUUID()` run outside the try in `flush()`; a circular `filters`
  or an ancient browser would throw past the "never break the app" contract
  (harmless context, one-brace fix). Same shape exists in `bot/src/log.ts`.
- **CI polish**: cache `~/.cache/firebase/emulators` (saves ~10-20 s/run
  re-downloading the Firestore emulator jar); bump `actions/setup-java` v4→v5
  (deprecation warning in runs).
- **Telemetry nits (bot)**: clearing filters via «✕ Հանել զտիչները» (`v:`) isn't
  logged while a panel's ✓ clear (`V:`) is; inline queries deliberately unlogged
  per-keystroke — only chosen results, and only if `/setinlinefeedback` is
  enabled (never confirmed).
- **Backfill `logs/bot_events.jsonl` into Firestore `events`** once the project
  exists — records carry client `ts` (ISO string) but rules demand
  `ts == request.time`, so a backfill needs the admin SDK (bypasses rules), not
  the REST path; keep the original time in a separate field if it matters.
- **`events` TTL policy** (Firestore) once on Blaze — unbounded growth
  otherwise, bounded in practice by the 20k writes/day rules ceiling.
- **App Check** — the documented response if junk writes ever appear.
- **BigQuery export extension** — the SQL-analytics story for `events` (needs
  Blaze); until then events are effectively write-only at scale.
- **Bot: find-my-name** — the declension-aware site feature, deferred from bot
  v1 by user choice; the shared lib (`web/lib/findName.ts`) makes it cheap.
- **Facet-index drift**: old bot messages' filter buttons index boot-time
  frequency-ordered lists; a corpus rebuild can reorder them (mislabeled filter
  until the next tap re-renders). Fix only if it ever confuses anyone —
  e.g. hash-pin the lists or encode values for short facets.
