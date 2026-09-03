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
