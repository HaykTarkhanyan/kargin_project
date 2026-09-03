---
name: annotate-sheets
description: Batch-annotate contact sheets in data/contact_sheets/ with Sonnet subagents writing structured JSON to data/visual_annotations/. Use when the user asks to annotate sheets, extract visual metadata from videos, or continue the annotation sweep. Also covers reading a single sheet to describe a sketch.
---

# Annotate contact sheets

Contact sheets are 8x5 grids of 40 frames sampled uniformly across one video
(built by `scripts/build_contact_sheets.py`), 2560x900, each tile carrying its
source timestamp bottom-left. One sheet costs ~3.1k vision tokens to read
(28 px patches; cost is set by total sheet area, not tile count).

## Reading one sheet (quick investigation)

Read the jpg directly and describe: where, who, what happens over time citing
tile timestamps, best guess at the joke. Cross-check against `kargin_eng.csv`
(`text`, `text_common` by `video_id`) only when asked - annotation runs stay
blind. Do not identify real actors by name from faces; describe roles only.

## Batch annotation

Unit economics, measured 2026-09-03: **9 sheets per Sonnet agent** is the
sweet spot (~11k subagent tokens/sheet; y=5 cost 17k, y=18+ pays growing
context accumulation). Launch ~4 agents first, then one new agent per
completion notification (waves warm the shared prompt cache instead of racing
it). Never use Haiku - it hallucinated an indoor setting from a chain-link
fence in testing. Escalate `confidence: "low"` sheets to Opus or the main
model afterwards if the user wants.

Pick the sheets to do: files in `data/contact_sheets/*.jpg` that have no
matching `data/visual_annotations/<seq>_<video_id>.json` (seq = first 3 chars
of the sheet filename; video_id = last 11 chars of the stem, may contain or
start with `-` or `_`).

Each agent gets the EXACT prompt below (keep it byte-identical across agents
- only the file list at the end differs; identical prefixes hit the prompt
cache). Fill in the file list, launch via the Agent tool with
`subagent_type: general-purpose`, `model: sonnet`.

### Agent prompt template

```
You annotate contact sheets from the Armenian comedy sketch show Kargin Haghordum. Each sheet is an 8x5 grid of 40 frames sampled uniformly across one video; each tile has its source timestamp burned into the bottom-left corner.

Process the sheet files listed at the END of this prompt, one at a time. For each: Read the image, then Write ONE JSON file to C:\Users\hayk_\OneDrive\Desktop\kargin_project\data\visual_annotations\<seq>_<video_id>.json where <seq> is the first 3 characters of the sheet filename and <video_id> is the last 11 characters of the filename before ".jpg" (ids may contain "-" and "_", and may start with either).

Each JSON file must have EXACTLY this shape (lowercase enum values, empty arrays when none, no extra keys):

{
  "video_id": "...",
  "indoor_outdoor": "indoor" | "outdoor" | "both",
  "day_night": "day" | "night" | "mixed" | "unclear",
  "people_count": "1" | "2" | "3" | "4" | "5+" | "crowd",
  "has_crowd_or_extras": true|false,
  "animals": ["cow", ...],
  "vehicles": ["lada", "marshrutka", ...],
  "location_fine": "short lowercase phrase, e.g. 'village farm yard', 'bar', 'school classroom'",
  "character_types": ["bartender", "gangster", "old woman", ...],
  "drag": true|false,
  "key_props": ["plaster casts", "boombox", ...],
  "physicality": "talking" | "physical" | "fight",
  "scene_structure": {"settings": <int, distinct locations>, "repeating_gag": true|false},
  "visual_synopsis": "1-2 English sentences: what visibly happens, start to end.",
  "best_frame_ts": "MM:SS",
  "confidence": "high" | "medium" | "low",
  "needs_audio": true|false
}

Rules:
- Do NOT read any other project file (no CSVs, no transcripts) — annotations must be blind.
- Do NOT attempt to name or identify the real actors; describe characters only by role/appearance.
- "drag" means a male actor visibly playing a female character.
- Judge only from what is visible; when unsure, lower "confidence" rather than guessing confidently.
- "repeating_gag": true only when you can see the same setup recur (e.g. black cut-frames separating near-identical rounds).
- "needs_audio": true when the story is not readable from visuals alone.

Your final message: one line per file (seq, video_id, location_fine, confidence) confirming the JSONs were written.

Files to process:
<absolute sheet paths, one per line>
```

### After all agents finish

Validate (run this; zero violations expected):

```bash
PYTHONIOENCODING=utf-8 python -c "
import json, pathlib, collections
KEYS={'video_id','indoor_outdoor','day_night','people_count','has_crowd_or_extras','animals','vehicles','location_fine','character_types','drag','key_props','physicality','scene_structure','visual_synopsis','best_frame_ts','confidence','needs_audio'}
bad=[]; conf=collections.Counter()
for p in sorted(pathlib.Path('data/visual_annotations').glob('*.json')):
    d=json.loads(p.read_text(encoding='utf-8'))
    if set(d)!=KEYS: bad.append(p.name)
    conf[d['confidence']]+=1
print('violations:', bad or 'none', '| confidence:', dict(conf))
"
```

Report to the user: files written, confidence spread, measured subagent
tokens (sum the completion notifications), and the list of low-confidence
sheets for optional escalation.

Also flag any agent note about mostly-black sheets (few tiles filled): that
means the source video's video stream is shorter than its audio - a broken
download. Verify with ffprobe (compare video vs audio stream durations),
delete the bad mp4 + sheet + json, and re-run the downloader (see
LEARNINGS.md on VP9-over-HLS truncation).

## Escalation pass (low-confidence sheets)

Re-run lows through Opus with the same schema, framed as a second pass:
overwrite the JSON, do NOT read the old one first, zoom into tiles for
anything ambiguous, and keep "low" as a valid honest outcome. Measured
2026-09-04: resolved 100 of 101 lows; the wins came from reading signage and
props at zoom, not from rethinking.

Two rules learned from Opus agent deaths (LEARNINGS.md 2026-09-04):
- Every agent prompt must say: write each JSON the moment that sheet is done,
  never batch writes. Opus vision agents stall/die mid-run; per-file writes
  make recovery a cheap mtime diff instead of a redo.
- Agents scripting crops must use UNIQUELY NAMED helper files - the shared
  scratchpad lets concurrent agents clobber each other's helpers silently.
- Opus sizing: 7 sheets per agent, max 3 concurrent. (Sonnet tolerates 9-13
  per agent and 6-8 concurrent.)
