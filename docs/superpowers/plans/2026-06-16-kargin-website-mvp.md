# Kargin Archive Website — MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a beautiful, static, GitHub-Pages-hosted website that lets anyone search/browse the 702 curated Kargin sketches (Armenian) and jump to the YouTube moment.

**Architecture:** A Python build script joins the two CSVs into one canonicalized `sketches.json`. A Next.js (App Router) app static-exports pages that load that JSON and run all search/filter/sort **client-side** (normalized substring scan — true mid-word match, zero backend). Watch pages are pre-rendered per sketch. Deployed to GitHub Pages via Actions.

**Tech Stack:** Python 3.11 + pandas + pytest (data build); Next.js (App Router, `output: 'export'`) + TypeScript + Tailwind CSS + Vitest + React Testing Library (frontend); GitHub Actions (deploy).

**Design spec:** `docs/superpowers/specs/2026-06-16-kargin-website-ui-design.md` (rev 4). Visual direction = "Kargin Classic" (warm paper, hard ink borders + offset shadows, flag-color accents, Anton + Noto Sans Armenian).

---

## File structure (created/modified by this plan)

```
scripts/build_site_data.py        # CSV → web/public/data/sketches.json (+ coverage report)
scripts/kargin_build/             # importable, testable build helpers
  __init__.py
  parse.py                        # extract_video_id, parse_seq, split_lines
  canon.py                        # canonicalize_actors / _location / _languages
  assemble.py                     # row → sketch dict; build_all()
tests/build/                      # pytest for the above (pure functions)
  test_parse.py  test_canon.py  test_assemble.py
web/                              # Next.js app (created by create-next-app)
  app/layout.tsx                  # shell: fonts, header, theme
  app/page.tsx                    # Home / Search
  app/sketch/[id]/page.tsx        # Watch view (generateStaticParams over 702 ids)
  app/random/page.tsx  app/about/page.tsx
  components/                     # Header, Hero, SearchBar, StatStrip, FilterRail,
                                  #   ActiveFilters, ResultsHeader, SketchCard, SketchGrid,
                                  #   WatchView, EmptyState, Footer
  lib/types.ts  lib/data.ts  lib/search.ts  lib/facets.ts  lib/format.ts
  lib/__tests__/                  # vitest: search, facets, format
  public/data/sketches.json       # build artifact (committed)
  next.config.ts  app/globals.css  vitest.config.ts   # Tailwind v4 = CSS-first, NO tailwind.config.ts
.github/workflows/deploy.yml      # build python data + next export → Pages
pyproject.toml                    # add pytest dev dep
```

**Pre-req (do once, not a task):** work on a feature branch off `dev`:
```bash
git checkout dev && git checkout -b feat/website-mvp
```

---

## Task 1: Python build helpers — `extract_video_id`, `parse_seq`, `split_lines`

**Files:**
- Create: `scripts/kargin_build/__init__.py` (empty)
- Create: `scripts/kargin_build/parse.py`
- Create: `tests/build/test_parse.py`
- Modify: `pyproject.toml` (add pytest dev dependency)

- [ ] **Step 1: Add pytest and create test dirs**

Run:
```bash
uv add --dev pytest
mkdir -p scripts/kargin_build tests/build
touch scripts/kargin_build/__init__.py tests/__init__.py tests/build/__init__.py
```

> **Import-scheme note:** tests import `scripts.kargin_build.*` while the entrypoint imports `kargin_build.*` (under `PYTHONPATH=scripts`). Both resolve under pytest's default `prepend` import mode — do **not** switch pytest to `importmode=importlib`, which would break the test imports.

- [ ] **Step 2: Write the failing tests**

Create `tests/build/test_parse.py`:
```python
from scripts.kargin_build.parse import extract_video_id, parse_seq, split_lines


def test_extract_video_id_watch_url():
    assert extract_video_id("https://www.youtube.com/watch?v=ofvCL_U2Er0&list=x") == "ofvCL_U2Er0"

def test_extract_video_id_short_url():
    assert extract_video_id("https://youtu.be/hp0U2719O0A?t=10") == "hp0U2719O0A"

def test_extract_video_id_none_on_garbage():
    assert extract_video_id("not a url") is None
    assert extract_video_id(None) is None

def test_parse_seq_from_title():
    assert parse_seq("Kargin Haghordum sketch 579 (Hayko Mko)") == 579

def test_parse_seq_missing_returns_none():
    assert parse_seq("Kargin Haghordum - Dombel (Hayko Mko)") is None

def test_split_lines_semicolon_and_armenian_fullstop():
    assert split_lines("բարև; ոնց ես։ լավ") == ["բարև", "ոնց ես", "լավ"]

def test_split_lines_does_not_split_on_hyphen():
    assert split_lines("1-2 հատ") == ["1-2 հատ"]

def test_split_lines_empty():
    assert split_lines("") == []
    assert split_lines(None) == []
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/build/test_parse.py -v`
Expected: FAIL (ModuleNotFoundError / ImportError — `parse` not found).

- [ ] **Step 4: Implement `parse.py`**

Create `scripts/kargin_build/parse.py`:
```python
"""Pure parsing helpers for the site-data build. No I/O."""
import re

_VIDEO_ID = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})")
_SEQ = re.compile(r"(?:sketch|սքեթչ)\s+(\d+)", re.IGNORECASE)
# Real separators in the curated `text`: ';' (~60%) and '։' (Armenian full stop, ~30%).
# Deliberately NOT bare '-' (would mangle "1-2").
_LINE_SPLIT = re.compile(r"[;։]")


def extract_video_id(url):
    if not isinstance(url, str):
        return None
    m = _VIDEO_ID.search(url)
    return m.group(1) if m else None


def parse_seq(title):
    if not isinstance(title, str):
        return None
    m = _SEQ.search(title)
    return int(m.group(1)) if m else None


def split_lines(text):
    if not isinstance(text, str):
        return []
    return [seg.strip() for seg in _LINE_SPLIT.split(text) if seg.strip()]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/build/test_parse.py -v`
Expected: PASS (7 passed).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock scripts/kargin_build tests
git commit -m "feat(build): parsing helpers for video_id, seq, dialogue lines"
```

---

## Task 2: Python build helpers — facet canonicalization

**Files:**
- Create: `scripts/kargin_build/canon.py`
- Create: `tests/build/test_canon.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/build/test_canon.py`:
```python
from scripts.kargin_build.canon import (
    canonicalize_actors, canonicalize_location, canonicalize_languages,
)

ALLOW = {"Հայկո", "Մկո", "Հասմիկ", "Լևոն", "Անդո", "Քրիստինե", "Աշոտ", "Արմինե"}
TYPOS = {"Հակյո": "Հայկո", "ՄԿո": "Մկո"}


def test_actors_comma_separated():
    actors, roles = canonicalize_actors("Հայկո, Մկո", ALLOW, TYPOS)
    assert actors == ["Հայկո", "Մկո"] and roles == []

def test_actors_space_joined_no_comma():
    actors, _ = canonicalize_actors("Հայկո Մկո", ALLOW, TYPOS)
    assert actors == ["Հայկո", "Մկո"]

def test_actors_typo_mapped():
    actors, _ = canonicalize_actors("Հակյո, ՄԿո", ALLOW, TYPOS)
    assert actors == ["Հայկո", "Մկո"]

def test_actors_role_word_goes_to_roles_not_actors():
    actors, roles = canonicalize_actors("Հայկո, ոստիկան", ALLOW, TYPOS)
    assert actors == ["Հայկո"] and roles == ["ոստիկան"]

def test_actors_two_word_role_with_comma_not_split():
    # comma present, so we do NOT space-split — "փոքր երեխա" stays one token
    actors, roles = canonicalize_actors("Հայկո, փոքր երեխա", ALLOW, TYPOS)
    assert actors == ["Հայկո"] and roles == ["փոքր երեխա"]

def test_actors_empty():
    assert canonicalize_actors("", ALLOW, TYPOS) == ([], [])
    assert canonicalize_actors(None, ALLOW, TYPOS) == ([], [])

def test_location_known_passes_through():
    assert canonicalize_location("Տուն") == "Տուն"

def test_location_noise_bucketed_to_other():
    assert canonicalize_location("Այլ(գրեք ավելացնենք)") == "Այլ"
    assert canonicalize_location("") == "Այլ"

def test_languages_split_and_normalized():
    assert canonicalize_languages("հայերեն+ռուսերեն") == ["հայերեն", "ռուսերեն"]
    assert canonicalize_languages("այլ") == ["այլ"]
    assert canonicalize_languages("") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/build/test_canon.py -v`
Expected: FAIL (ImportError — `canon` not found).

- [ ] **Step 3: Implement `canon.py`**

Create `scripts/kargin_build/canon.py`:
```python
"""Facet canonicalization. Raw columns are dirty; these make clean facets."""

# Canonical location set; everything else (incl. blanks/noise) buckets to "Այլ".
_KNOWN_LOCATIONS = {
    "Տուն", "Դուրս", "Խանութ", "Հիվանդանոց", "Գրասենյակ", "Փողոց", "Մեքենա",
}


def canonicalize_actors(raw, allowlist, typos):
    """Return (actors, roles). Comma-split first; space-split only when no comma."""
    if not isinstance(raw, str) or not raw.strip():
        return [], []
    if "," in raw:
        tokens = [t.strip() for t in raw.split(",")]
    else:
        tokens = [t.strip() for t in raw.split()]
    actors, roles = [], []
    for tok in tokens:
        if not tok:
            continue
        tok = typos.get(tok, tok)
        if tok in allowlist:
            if tok not in actors:
                actors.append(tok)
        else:
            roles.append(tok)
    return actors, roles


def canonicalize_location(raw):
    if isinstance(raw, str):
        v = raw.strip()
        if v in _KNOWN_LOCATIONS:
            return v
    return "Այլ"


def canonicalize_languages(raw):
    if not isinstance(raw, str) or not raw.strip():
        return []
    parts = raw.replace("+", ",").split(",")
    out = []
    for p in (x.strip() for x in parts):
        if p and p not in out:
            out.append(p)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/build/test_canon.py -v`
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/kargin_build/canon.py tests/build/test_canon.py
git commit -m "feat(build): actor/location/language canonicalization"
```

---

## Task 3: Python — assemble one sketch dict + `build_all()`

**Files:**
- Create: `scripts/kargin_build/assemble.py`
- Create: `tests/build/test_assemble.py`

- [ ] **Step 1: Write the failing test**

Create `tests/build/test_assemble.py`:
```python
import pandas as pd
from scripts.kargin_build.assemble import row_to_sketch, ACTOR_ALLOWLIST, ACTOR_TYPOS


def _row(**kw):
    base = dict(titles="Kargin Haghordum sketch 663 (Hayko Mko)",
                links="https://youtu.be/ofvCL_U2Er0", text="բարև; ոնց ես",
                text_common="արա էսի ուզբեկ ա", main_actors="Հայկո, Մկո",
                roles_names="", location="Տուն", lighting="", languages="հայերեն",
                duration_sec=242, view_count=1358199, upload_date="20130410.0")
    base.update(kw)
    return pd.Series(base)


def test_row_to_sketch_core_fields():
    s = row_to_sketch(_row(), ACTOR_ALLOWLIST, ACTOR_TYPOS)
    assert s["id"] == "ofvCL_U2Er0"
    assert s["videoId"] == "ofvCL_U2Er0"
    assert s["title"] == "Kargin Haghordum sketch 663 (Hayko Mko)"   # REAL title, not fabricated
    assert s["seq"] == 663
    assert s["lines"] == ["բարև", "ոնց ես"]
    assert s["actors"] == ["Հայկո", "Մկո"]
    assert s["location"] == "Տուն"
    assert s["durationSec"] == 242
    assert s["viewCount"] == 1358199
    assert s["uploadDate"] == "2013-04-10"
    assert s["thumbnail"].endswith("/ofvCL_U2Er0/mqdefault.jpg")
    assert s["segments"] == []

def test_row_to_sketch_empty_text_yields_no_lines():
    s = row_to_sketch(_row(text=""), ACTOR_ALLOWLIST, ACTOR_TYPOS)
    assert s["lines"] == [] and s["text"] == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/build/test_assemble.py -v`
Expected: FAIL (ImportError — `assemble` not found).

- [ ] **Step 3: Implement `assemble.py`**

Create `scripts/kargin_build/assemble.py`:
```python
"""Turn a joined CSV row into the site's sketch dict, and build the full list."""
import pandas as pd
from .parse import extract_video_id, parse_seq, split_lines
from .canon import canonicalize_actors, canonicalize_location, canonicalize_languages

# Seed from the known cast; refine by inspecting top tokens during the real build (Task 4).
ACTOR_ALLOWLIST = {
    "Հայկո", "Մկո", "Հասմիկ", "Լևոն", "Անդո", "Քրիստինե", "Աշոտ", "Արմինե",
}
ACTOR_TYPOS = {"Հակյո": "Հայկո", "ՄԿո": "Մկո"}


def _s(v):
    return "" if pd.isna(v) else str(v).strip()


def _fmt_date(raw):
    d = _s(raw).split(".")[0]                      # "20130410.0" -> "20130410"
    return f"{d[0:4]}-{d[4:6]}-{d[6:8]}" if len(d) == 8 else ""


def row_to_sketch(row, allowlist, typos):
    vid = extract_video_id(_s(row.get("links")))
    actors, roles_extra = canonicalize_actors(_s(row.get("main_actors")), allowlist, typos)
    roles = _s(row.get("roles_names"))
    text = _s(row.get("text"))
    return {
        "id": vid,
        "videoId": vid,
        "seq": parse_seq(_s(row.get("titles"))),
        "title": _s(row.get("titles")),
        "url": f"https://youtu.be/{vid}" if vid else "",
        "thumbnail": f"https://img.youtube.com/vi/{vid}/mqdefault.jpg" if vid else "",
        "text": text,
        "lines": split_lines(text),
        "textCommon": _s(row.get("text_common")),
        "actors": actors,
        "actorsRaw": _s(row.get("main_actors")),
        "rolesNames": ", ".join([r for r in [roles, *roles_extra] if r]),
        "location": canonicalize_location(_s(row.get("location"))),
        "languages": canonicalize_languages(_s(row.get("languages"))),
        "lighting": _s(row.get("lighting")),
        "durationSec": int(row["duration_sec"]) if not pd.isna(row.get("duration_sec")) else None,
        "viewCount": int(row["view_count"]) if not pd.isna(row.get("view_count")) else None,
        "uploadDate": _fmt_date(row.get("upload_date")),
        "segments": [],
    }


def build_all(kargin_csv, metadata_csv, allowlist=ACTOR_ALLOWLIST, typos=ACTOR_TYPOS):
    k = pd.read_csv(kargin_csv)
    m = pd.read_csv(metadata_csv)[["video_id", "duration_sec", "view_count", "upload_date"]]
    k["video_id"] = k["links"].map(lambda u: extract_video_id(u) if isinstance(u, str) else None)
    if k["video_id"].isna().any():
        raise ValueError(f"{k['video_id'].isna().sum()} rows have no parseable video_id")  # loud fail
    df = k.merge(m, on="video_id", how="left")
    return [row_to_sketch(r, allowlist, typos) for _, r in df.iterrows()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/build/test_assemble.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add scripts/kargin_build/assemble.py tests/build/test_assemble.py
git commit -m "feat(build): assemble sketch dicts from joined CSV rows"
```

---

## Task 4: Python — `build_site_data.py` entrypoint + coverage report (run on real data)

**Files:**
- Create: `scripts/build_site_data.py`

- [ ] **Step 1: Implement the entrypoint**

Create `scripts/build_site_data.py`:
```python
"""Build web/public/data/sketches.json from the curation + metadata CSVs."""
import json
import logging
import os
from collections import Counter
from pathlib import Path

from kargin_build.assemble import build_all, ACTOR_ALLOWLIST

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "public" / "data" / "sketches.json"


def _setup_logging():
    Path(ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(ROOT / "logs" / "build_site_data.log", encoding="utf-8")],
    )


def main():
    _setup_logging()
    log = logging.getLogger(__name__)
    sketches = build_all(ROOT / "kargin_eng.csv", ROOT / "data" / "youtube_metadata.csv")

    n = len(sketches)
    with_text = sum(1 for s in sketches if s["text"])
    with_actors = sum(1 for s in sketches if s["actors"])
    log.info("built %d sketches | %d with dialogue | %d with actors", n, with_text, with_actors)
    # Surface unmapped actor tokens so the allowlist can be tightened (REQUIRED per spec 7.1).
    leftover = Counter(tok for s in sketches for tok in s["rolesNames"].split(", ") if tok and tok not in ACTOR_ALLOWLIST)
    log.info("top non-allowlist tokens in roles: %s", leftover.most_common(15))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(sketches, ensure_ascii=False, indent=None), encoding="utf-8")
    log.info("wrote %s (%.1f KB)", OUT, OUT.stat().st_size / 1024)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it on the real data**

Run: `PYTHONIOENCODING=utf-8 PYTHONPATH=scripts uv run python scripts/build_site_data.py`
Expected: log shows `built 702 sketches | 602 with dialogue | ~606 with actors`, a `top non-allowlist tokens` line, and `wrote .../sketches.json`.

- [ ] **Step 3: Refine the actor allowlist from the report**

Inspect the `top non-allowlist tokens` log line. Any real recurring actor names mistakenly dropped into roles → add them to `ACTOR_ALLOWLIST` in `scripts/kargin_build/assemble.py`. Re-run Step 2. Repeat until the leftover list is only genuine role-words (e.g. `ոստիկան`), not names.

- [ ] **Step 4: Sanity-check the JSON**

Run: `uv run python -c "import json;d=json.load(open('web/public/data/sketches.json',encoding='utf-8'));print(len(d), d[0]['title'], d[0]['id'])"`
Expected: `702 <a real title> <an 11-char id>`.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_site_data.py scripts/kargin_build/assemble.py web/public/data/sketches.json
git commit -m "feat(build): build_site_data entrypoint + coverage report; generate sketches.json"
```

---

## Task 5: Scaffold the Next.js app (static export)

**Files:**
- Create: `web/` (via create-next-app), `web/next.config.ts`

- [ ] **Step 1: Scaffold**

Run (from repo root):
```bash
npx create-next-app@latest web --typescript --tailwind --app --eslint --no-src-dir --import-alias "@/*" --use-npm
```
(If `web/` already has `public/data/sketches.json`, create-next-app may warn about a non-empty dir — choose to continue; it does not delete `public/`. If it refuses, scaffold in a temp dir and move `public/data` back.)

- [ ] **Step 1b: Verify Tailwind v4 was installed (the `@theme` syntax in Task 6 depends on it)**

Run: `cd web && node -p "(require('./package.json').devDependencies.tailwindcss||require('./package.json').dependencies.tailwindcss)"`
Expected: a `^4.x` version. If it prints v3, STOP — the CSS-first `@theme` tokens in Task 6 won't work on v3.

- [ ] **Step 2: Configure static export**

Replace `web/next.config.ts` with:
```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },     // no Image Optimization server on static hosts
  // basePath/assetPrefix: set ONLY for a project page (user.github.io/<repo>) — decided in deploy task
  trailingSlash: true,                // friendlier static routing on GitHub Pages
};

export default nextConfig;
```

- [ ] **Step 3: Verify dev server + build/export work**

Run:
```bash
cd web && npm run build
```
Expected: build succeeds and prints `Exporting (…)`; an `out/` directory is produced. (Default create-next-app page is fine for now.)

- [ ] **Step 4: Commit**

```bash
git add web
git commit -m "chore(web): scaffold Next.js app with static export config"
```

---

## Task 6: Design tokens, fonts, global styles (Kargin Classic)

**Files:**
- Modify: `web/app/globals.css`, `web/app/layout.tsx` (Tailwind v4 has no config file — all theming is in `globals.css`)

- [ ] **Step 1: Add fonts + CSS tokens**

Replace `web/app/globals.css` with:
```css
@import "tailwindcss";

:root{
  --paper:#FBF3E2; --paper2:#F4E9D0; --card:#FFFDF7; --ink:#1A1410; --muted:#8A7C64;
  --red:#D90012; --blue:#0033A0; --orange:#F2A800;
}
@theme inline {
  --color-paper: var(--paper); --color-paper2: var(--paper2); --color-card: var(--card);
  --color-ink: var(--ink); --color-muted: var(--muted);
  --color-kred: var(--red); --color-kblue: var(--blue); --color-korange: var(--orange);
  --font-display: var(--font-anton), var(--font-arm), sans-serif;
  --font-body: var(--font-arm), var(--font-inter), sans-serif;
}
html,body{ background:var(--paper); color:var(--ink); font-family:var(--font-body); }
*:focus-visible{ outline:3px solid var(--blue); outline-offset:2px; }

/* the load-bearing motif */
.k-shadow{ box-shadow:6px 6px 0 var(--ink); }
.k-shadow-red{ box-shadow:6px 6px 0 var(--red); }
.k-border{ border:2px solid var(--ink); }
```

- [ ] **Step 2: Wire fonts in the layout**

Replace `web/app/layout.tsx` with:
```tsx
import type { Metadata } from "next";
import { Anton, Inter, Noto_Sans_Armenian } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";

const anton = Anton({ weight: "400", subsets: ["latin"], variable: "--font-anton" });
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const arm = Noto_Sans_Armenian({ subsets: ["armenian"], weight: ["400", "600", "700", "800"], variable: "--font-arm" });

export const metadata: Metadata = {
  title: "Կարգին Արխիվ — Kargin Archive",
  description: "Որոնիր 702 Կարգին սքեթչ՝ տող առ տող։",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="hy" className={`${anton.variable} ${inter.variable} ${arm.variable}`}>
      <body><Header />{children}</body>
    </html>
  );
}
```

- [ ] **Step 3: Stub Header so layout compiles**

Create `web/components/Header.tsx`:
```tsx
import Link from "next/link";

const NAV = [
  ["/", "Որոնել"], ["/random", "Պատահական"], ["/about", "Մասին"],
] as const;

export default function Header() {
  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b-2 border-ink bg-paper px-8 py-4">
      <Link href="/" className="flex items-baseline gap-2 text-xl font-extrabold tracking-wide">
        ԿԱՐԳԻՆ<span className="rounded bg-kred px-2 py-0.5 text-[9px] font-extrabold tracking-[0.26em] text-white">ARCHIVE</span>
      </Link>
      <nav className="flex gap-6 text-sm font-semibold">
        {NAV.map(([href, label]) => (
          <Link key={href} href={href} className="opacity-70 hover:opacity-100">{label}</Link>
        ))}
      </nav>
    </header>
  );
}
```

- [ ] **Step 4: Verify it builds**

Run: `cd web && npm run build`
Expected: build succeeds (fonts fetched, no type errors).

- [ ] **Step 5: Commit**

```bash
git add web/app web/components/Header.tsx
git commit -m "feat(web): Kargin Classic design tokens, fonts, header shell"
```

---

## Task 7: Types + data loader + Vitest setup

**Files:**
- Create: `web/lib/types.ts`, `web/lib/data.ts`, `web/vitest.config.ts`
- Modify: `web/package.json` (test script + dev deps)

- [ ] **Step 1: Install test tooling**

Run:
```bash
cd web && npm i -D vitest @vitejs/plugin-react @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 2: Vitest config + test script**

Create `web/vitest.config.ts`:
```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", globals: true },
  resolve: { alias: { "@": new URL("./", import.meta.url).pathname } },
});
```
In `web/package.json` add to `"scripts"`: `"test": "vitest run"`.

- [ ] **Step 3: Define the Sketch type + loader**

Create `web/lib/types.ts`:
```ts
export interface Segment { startSec: number; endSec: number; text: string }
export interface Sketch {
  id: string; videoId: string; seq: number | null; title: string;
  url: string; thumbnail: string;
  text: string; lines: string[]; textCommon: string;
  actors: string[]; actorsRaw: string; rolesNames: string;
  location: string; languages: string[]; lighting: string;
  durationSec: number | null; viewCount: number | null; uploadDate: string;
  segments: Segment[];
}
```
Create `web/lib/data.ts`:
```ts
import type { Sketch } from "./types";
import sketches from "@/public/data/sketches.json";

export const ALL: Sketch[] = sketches as Sketch[];
export const byId = (id: string): Sketch | undefined => ALL.find((s) => s.id === id);
```
Ensure `web/tsconfig.json` has `"resolveJsonModule": true` (create-next-app sets it; verify).

> **Accepted tradeoff:** a static `import` inlines all 702 rows into the JS bundle (vs the spec's "fetch once"). Fine at this size for MVP; switch to a runtime `fetch('/data/sketches.json')` later if bundle size matters.

- [ ] **Step 4: Verify import compiles**

Run: `cd web && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add web/lib web/vitest.config.ts web/package.json web/package-lock.json
git commit -m "feat(web): Sketch types, data loader, vitest setup"
```

---

## Task 8: Search + format utils (TDD)

**Files:**
- Create: `web/lib/format.ts`, `web/lib/search.ts`, `web/lib/__tests__/search.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `web/lib/__tests__/search.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { normalize, searchSketches } from "@/lib/search";
import { formatViews, formatDuration } from "@/lib/format";
import type { Sketch } from "@/lib/types";

const mk = (p: Partial<Sketch>): Sketch => ({
  id: "x", videoId: "x", seq: null, title: "", url: "", thumbnail: "",
  text: "", lines: [], textCommon: "", actors: [], actorsRaw: "", rolesNames: "",
  location: "Այլ", languages: [], lighting: "", durationSec: 120, viewCount: 0,
  uploadDate: "", segments: [], ...p,
});

describe("normalize", () => {
  it("lowercases and collapses whitespace", () => {
    expect(normalize("  ՏոՌմՈՒզ   հլը ")).toBe("տոռմուզ հլը");
  });
});

describe("searchSketches", () => {
  const data = [
    mk({ id: "a", title: "sketch 285", text: "Հոպ ընգեր ջան, տոռմուզ հըլը", location: "Տուն" }),
    mk({ id: "b", title: "sketch 108", textCommon: "լվացքի փոշի", location: "Խանութ" }),
  ];
  it("matches mid-word substring inside dialogue", () => {
    const r = searchSketches("տոռմուզ", data, {});
    expect(r.map((s) => s.id)).toEqual(["a"]);
  });
  it("returns all when query empty", () => {
    expect(searchSketches("", data, {}).length).toBe(2);
  });
  it("filters by location and composes with query", () => {
    expect(searchSketches("", data, { location: ["Խանութ"] }).map((s) => s.id)).toEqual(["b"]);
  });
  it("random sort returns the same set of results (no drops/dupes)", () => {
    expect(searchSketches("", data, {}, "random").map((s) => s.id).sort()).toEqual(["a", "b"]);
  });
});

describe("format", () => {
  it("formats views", () => { expect(formatViews(1358199)).toBe("1.4M"); expect(formatViews(813444)).toBe("813K"); });
  it("formats duration", () => { expect(formatDuration(242)).toBe("4:02"); });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd web && npx vitest run lib/__tests__/search.test.ts`
Expected: FAIL (modules not found).

- [ ] **Step 3: Implement `format.ts` and `search.ts`**

Create `web/lib/format.ts`:
```ts
export function formatViews(n: number | null): string {
  if (!n) return "0";
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${Math.round(n / 1e3)}K`;
  return String(n);
}
export function formatDuration(sec: number | null): string {
  if (!sec) return "0:00";
  const m = Math.floor(sec / 60), s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}
```
Create `web/lib/search.ts`:
```ts
import type { Sketch } from "./types";

export interface Filters {
  location?: string[]; actors?: string[]; language?: string[]; duration?: "<2" | "2-4" | "4+";
}
export type SortKey = "views" | "newest" | "random";

export function normalize(s: string): string {
  return s.toLowerCase().normalize("NFC").replace(/\s+/g, " ").trim();
}

// Field weights: catchphrase + title rank highest, then dialogue, then people/place.
const FIELDS: Array<[keyof Sketch, number]> = [
  ["textCommon", 5], ["title", 4], ["text", 3], ["actorsRaw", 2], ["rolesNames", 1], ["location", 1],
];

function durationOk(sec: number | null, bucket?: Filters["duration"]): boolean {
  if (!bucket || sec == null) return !bucket;
  if (bucket === "<2") return sec < 120;
  if (bucket === "2-4") return sec >= 120 && sec <= 240;
  return sec > 240;
}

function passesFilters(s: Sketch, f: Filters): boolean {
  if (f.location?.length && !f.location.includes(s.location)) return false;
  if (f.actors?.length && !f.actors.some((a) => s.actors.includes(a))) return false;
  if (f.language?.length && !f.language.some((l) => s.languages.includes(l))) return false;
  if (f.duration && !durationOk(s.durationSec, f.duration)) return false;
  return true;
}

export function searchSketches(query: string, data: Sketch[], filters: Filters, sort: SortKey = "views"): Sketch[] {
  const q = normalize(query);
  const scored: Array<{ s: Sketch; score: number }> = [];
  for (const s of data) {
    if (!passesFilters(s, filters)) continue;
    let score = 0;
    if (q) {
      for (const [field, w] of FIELDS) {
        const v = s[field];
        if (typeof v === "string" && normalize(v).includes(q)) score += w;
      }
      if (score === 0) continue; // query given but no field matched → drop
    }
    scored.push({ s, score });
  }
  if (sort === "random") {
    const arr = scored.map((x) => x.s);
    for (let i = arr.length - 1; i > 0; i--) {           // Fisher-Yates — actually shuffle
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }
  scored.sort((a, b) => {
    if (q && b.score !== a.score) return b.score - a.score;
    if (sort === "newest") return (b.s.uploadDate).localeCompare(a.s.uploadDate);
    return (b.s.viewCount ?? 0) - (a.s.viewCount ?? 0);
  });
  return scored.map((x) => x.s);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd web && npx vitest run lib/__tests__/search.test.ts`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add web/lib/format.ts web/lib/search.ts web/lib/__tests__/search.test.ts
git commit -m "feat(web): substring search, filters, sort, formatters (TDD)"
```

---

## Task 9: Facet counts (TDD)

**Files:**
- Create: `web/lib/facets.ts`, `web/lib/__tests__/facets.test.ts`

- [ ] **Step 1: Write the failing test**

Create `web/lib/__tests__/facets.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { facetCounts } from "@/lib/facets";
import type { Sketch } from "@/lib/types";

const mk = (p: Partial<Sketch>): Sketch => ({ id:"x",videoId:"x",seq:null,title:"",url:"",thumbnail:"",
  text:"",lines:[],textCommon:"",actors:[],actorsRaw:"",rolesNames:"",location:"Այլ",languages:[],
  lighting:"",durationSec:120,viewCount:0,uploadDate:"",segments:[],...p });

describe("facetCounts", () => {
  it("counts locations and actors over the dataset", () => {
    const data = [
      mk({ location: "Տուն", actors: ["Հայկո", "Մկո"] }),
      mk({ location: "Տուն", actors: ["Հայկո"] }),
      mk({ location: "Խանութ", actors: [] }),
    ];
    const f = facetCounts(data);
    expect(f.location["Տուն"]).toBe(2);
    expect(f.location["Խանութ"]).toBe(1);
    expect(f.actors["Հայկո"]).toBe(2);
    expect(f.actors["Մկո"]).toBe(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run lib/__tests__/facets.test.ts`
Expected: FAIL.

- [ ] **Step 3: Implement `facets.ts`**

Create `web/lib/facets.ts`:
```ts
import type { Sketch } from "./types";

export interface Facets { location: Record<string, number>; actors: Record<string, number>; language: Record<string, number>; }

function tally(map: Record<string, number>, key: string) { if (key) map[key] = (map[key] ?? 0) + 1; }

export function facetCounts(data: Sketch[]): Facets {
  const f: Facets = { location: {}, actors: {}, language: {} };
  for (const s of data) {
    tally(f.location, s.location);
    s.actors.forEach((a) => tally(f.actors, a));
    s.languages.forEach((l) => tally(f.language, l));
  }
  return f;
}

export const sortedEntries = (m: Record<string, number>) =>
  Object.entries(m).sort((a, b) => b[1] - a[1]);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run lib/__tests__/facets.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/lib/facets.ts web/lib/__tests__/facets.test.ts
git commit -m "feat(web): facet count helpers (TDD)"
```

---

## Task 10: `SketchCard` + `SketchGrid` (render test)

**Files:**
- Create: `web/components/SketchCard.tsx`, `web/components/SketchGrid.tsx`, `web/components/__tests__/SketchCard.test.tsx`

- [ ] **Step 1: Write a render test**

Create `web/components/__tests__/SketchCard.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SketchCard from "@/components/SketchCard";
import type { Sketch } from "@/lib/types";

const s = { id:"ofvCL_U2Er0",videoId:"ofvCL_U2Er0",seq:663,title:"sketch 663",url:"",
  thumbnail:"https://img.youtube.com/vi/ofvCL_U2Er0/mqdefault.jpg",text:"",lines:[],
  textCommon:"արա էսի ուզբեկ ա",actors:["Հայկո","Մկո"],actorsRaw:"",rolesNames:"",
  location:"Տուն",languages:[],lighting:"",durationSec:242,viewCount:1358199,uploadDate:"",segments:[] } as Sketch;

describe("SketchCard", () => {
  it("renders title, location, duration, views, links to /sketch/:id", () => {
    render(<SketchCard sketch={s} />);
    expect(screen.getByText("sketch 663")).toBeTruthy();
    expect(screen.getByText("Տուն")).toBeTruthy();
    expect(screen.getByText("4:02")).toBeTruthy();
    expect(screen.getByRole("link").getAttribute("href")).toContain("/sketch/ofvCL_U2Er0");
  });
});
```
Add `import "@testing-library/jest-dom"` at the top of `web/vitest.setup.ts` (create it) and reference it in `vitest.config.ts` via `test.setupFiles: ["./vitest.setup.ts"]`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && npx vitest run components/__tests__/SketchCard.test.tsx`
Expected: FAIL (component missing).

- [ ] **Step 3: Implement the components**

Create `web/components/SketchCard.tsx`:
```tsx
import Link from "next/link";
import type { Sketch } from "@/lib/types";
import { formatViews, formatDuration } from "@/lib/format";

export default function SketchCard({ sketch: s, snippet }: { sketch: Sketch; snippet?: string }) {
  const quote = snippet ?? s.textCommon ?? "";
  return (
    <Link href={`/sketch/${s.id}`} className="group block overflow-hidden rounded-xl k-border k-shadow transition hover:-translate-x-[3px] hover:-translate-y-[3px] hover:k-shadow-red bg-card">
      <div className="relative aspect-video border-b-2 border-ink bg-cover bg-center" style={{ backgroundImage: `url(${s.thumbnail})` }}>
        <span className="absolute left-2 top-2 rounded-full bg-kblue px-2.5 py-1 text-[11px] font-bold text-white">{s.location}</span>
        <span className="absolute bottom-2 right-2 rounded bg-ink px-2 py-0.5 text-[11px] font-bold text-paper">{formatDuration(s.durationSec)}</span>
      </div>
      <div className="p-4">
        <div className="mb-2 font-bold leading-snug">{s.title}</div>
        {quote && <div className="mb-3 border-l-[3px] border-korange pl-3 text-sm opacity-75">«{quote}»</div>}
        <div className="flex items-center gap-2 text-xs font-semibold text-muted">
          <span>{s.actors.join(" ")}</span><span className="opacity-50">·</span>
          <span className="text-ink">{formatViews(s.viewCount)} դիտում</span>
        </div>
      </div>
    </Link>
  );
}
```
Create `web/components/SketchGrid.tsx`:
```tsx
import type { Sketch } from "@/lib/types";
import SketchCard from "./SketchCard";

export default function SketchGrid({ items }: { items: Sketch[] }) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
      {items.map((s) => <SketchCard key={s.id} sketch={s} />)}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web && npx vitest run components/__tests__/SketchCard.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/components web/vitest.config.ts web/vitest.setup.ts
git commit -m "feat(web): SketchCard + SketchGrid with render test"
```

---

## Task 11: Home / Search page (client island: search + filters + sort + states)

**Files:**
- Create: `web/components/Hero.tsx`, `web/components/FilterRail.tsx`, `web/components/SearchExperience.tsx`
- Modify: `web/app/page.tsx`

- [ ] **Step 1: Hero (presentational)**

Create `web/components/Hero.tsx`:
```tsx
import { formatViews } from "@/lib/format";

export default function Hero({ total, withDialogue, totalViews, totalHours, onSearch, query }:
  { total: number; withDialogue: number; totalViews: number; totalHours: number; onSearch: (q: string) => void; query: string }) {
  return (
    <section className="border-b-2 border-ink px-8 py-14">
      <h1 className="font-display text-6xl leading-none" style={{ maxWidth: "18ch" }}>
        Գտի՛ր <span className="text-kred">ցանկացած</span> պահը
      </h1>
      <p className="mt-4 max-w-[58ch] text-base opacity-70">
        {total} սքեթչ՝ տող առ տող։ Որոնիր երկխոսությունը, անցիր ուղիղ YouTube-ի այդ վայրկյանին։
      </p>
      <div className="mt-7 flex max-w-[720px] k-border k-shadow rounded-lg bg-white">
        <span className="flex items-center pl-5 pr-1 text-xl font-bold text-kred">⌕</span>
        <input value={query} onChange={(e) => onSearch(e.target.value)} autoFocus
          placeholder="որոնիր երկխոսություն, դերասան, վայր…"
          className="flex-1 bg-transparent px-2 py-4 text-[17px] outline-none" />
      </div>
      <div className="mt-5 flex gap-10">
        <Stat n={String(total)} l="սքեթչ" c="text-kred" />
        <Stat n={`${totalHours}ժ`} l="արխիվ" c="text-kblue" />
        <Stat n={formatViews(totalViews)} l="դիտում" c="text-korange" />
      </div>
      <p className="mt-3 text-xs text-muted">{withDialogue} սքեթչ ունի համադրված տեքստ</p>
    </section>
  );
}
function Stat({ n, l, c }: { n: string; l: string; c: string }) {
  return <div><div className={`font-display text-3xl ${c}`}>{n}</div><div className="mt-1 text-[10px] font-bold uppercase tracking-widest text-muted">{l}</div></div>;
}
```

- [ ] **Step 2: FilterRail (presentational, driven by facet counts)**

Create `web/components/FilterRail.tsx`:
```tsx
"use client";
import type { Facets } from "@/lib/facets";
import { sortedEntries } from "@/lib/facets";
import type { Filters } from "@/lib/search";

export default function FilterRail({ facets, filters, setFilters }:
  { facets: Facets; filters: Filters; setFilters: (f: Filters) => void }) {
  const toggle = (k: "location" | "actors" | "language", v: string) => {
    const cur = filters[k] ?? [];
    const next = cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v];
    setFilters({ ...filters, [k]: next });
  };
  return (
    <aside className="border-r-2 border-ink bg-paper2 px-6 py-6">
      <Group title="Վայր" entries={sortedEntries(facets.location).slice(0, 6)} sel={filters.location ?? []} on={(v) => toggle("location", v)} />
      <Group title="Դերասան" entries={sortedEntries(facets.actors).slice(0, 6)} sel={filters.actors ?? []} on={(v) => toggle("actors", v)} />
      <Group title="Լեզու" entries={sortedEntries(facets.language).slice(0, 4)} sel={filters.language ?? []} on={(v) => toggle("language", v)} />
    </aside>
  );
}
function Group({ title, entries, sel, on }:
  { title: string; entries: [string, number][]; sel: string[]; on: (v: string) => void }) {
  return (
    <div className="mb-6">
      <h4 className="mb-3 text-[11px] font-extrabold uppercase tracking-widest">{title}</h4>
      {entries.map(([name, count]) => (
        <button key={name} onClick={() => on(name)} className="flex w-full items-center gap-2.5 py-2 text-left text-sm">
          <span className={`h-4 w-4 shrink-0 rounded border-2 border-ink ${sel.includes(name) ? "bg-kblue" : ""}`} />
          {name}<span className="ml-auto text-[11px] font-semibold text-muted">{count}</span>
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: SearchExperience (client island wiring it together)**

Create `web/components/SearchExperience.tsx`:
```tsx
"use client";
import { useMemo, useState } from "react";
import { ALL } from "@/lib/data";
import { searchSketches, type Filters, type SortKey } from "@/lib/search";
import { facetCounts } from "@/lib/facets";
import Hero from "./Hero";
import FilterRail from "./FilterRail";
import SketchGrid from "./SketchGrid";

export default function SearchExperience() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<Filters>({});
  const [sort, setSort] = useState<SortKey>("views");
  const facets = useMemo(() => facetCounts(ALL), []);
  const results = useMemo(() => searchSketches(query, ALL, filters, sort), [query, filters, sort]);
  const withDialogue = useMemo(() => ALL.filter((s) => s.text).length, []);
  const totalViews = useMemo(() => ALL.reduce((a, s) => a + (s.viewCount ?? 0), 0), []);
  const totalHours = useMemo(() => Math.round(ALL.reduce((a, s) => a + (s.durationSec ?? 0), 0) / 3600), []);

  return (
    <>
      <Hero total={ALL.length} withDialogue={withDialogue} totalViews={totalViews} totalHours={totalHours} onSearch={setQuery} query={query} />
      <div className="grid grid-cols-1 md:grid-cols-[248px_1fr]">
        <FilterRail facets={facets} filters={filters} setFilters={setFilters} />
        <main className="px-8 py-6">
          <div className="mb-6 flex items-center justify-between">
            <div className="font-display text-2xl"><span className="text-kred">{results.length}</span> ԱՐԴՅՈՒՆՔ</div>
            <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)} className="k-border rounded-lg bg-white px-3 py-2 text-sm font-bold">
              <option value="views">Ըստ դիտումների</option>
              <option value="newest">Ամենանորը</option>
              <option value="random">Պատահական</option>
            </select>
          </div>
          {results.length === 0
            ? <div className="k-border rounded-lg bg-card p-10 text-center text-muted">Արդյունք չկա։ Փորձիր այլ բառ կամ մաքրիր զտիչները։</div>
            : <SketchGrid items={results} />}
        </main>
      </div>
    </>
  );
}
```

- [ ] **Step 4: Use it as the home page**

Replace `web/app/page.tsx`:
```tsx
import SearchExperience from "@/components/SearchExperience";
export default function Home() { return <SearchExperience />; }
```

- [ ] **Step 5: Verify build + manual smoke**

Run: `cd web && npm run build && npm run dev`
Then open `http://localhost:3000`, type `տոռմուզ`, confirm results filter, toggle a location filter, switch sort. Expected: instant updates, no console errors.

- [ ] **Step 6: Commit**

```bash
git add web/components web/app/page.tsx
git commit -m "feat(web): home search experience — hero, filters, sort, empty state"
```

---

## Task 12: Watch page `/sketch/[id]` (static params + player + dialogue + empty state)

**Files:**
- Create: `web/components/WatchView.tsx`, `web/app/sketch/[id]/page.tsx`

- [ ] **Step 1: WatchView component**

Create `web/components/WatchView.tsx`:
```tsx
import type { Sketch } from "@/lib/types";
import { formatViews, formatDuration } from "@/lib/format";

export default function WatchView({ s }: { s: Sketch }) {
  return (
    <div className="mx-auto grid max-w-5xl grid-cols-1 gap-0 p-6 md:grid-cols-[1.35fr_1fr]">
      <div className="md:border-r-2 md:border-ink md:pr-6">
        <div className="aspect-video overflow-hidden rounded-lg k-border k-shadow">
          <iframe className="h-full w-full" src={`https://www.youtube.com/embed/${s.videoId}`}
            title={s.title} allowFullScreen
            allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture" />
        </div>
        <div className="mt-4 flex flex-wrap gap-2.5">
          <a className="k-border rounded-lg bg-korange px-4 py-2.5 text-sm font-bold" href={s.url} target="_blank" rel="noreferrer">▶ Դիտել YouTube-ում</a>
        </div>
        <dl className="mt-5 grid grid-cols-2 gap-4 border-t-2 border-ink pt-5 text-sm">
          <Meta k="Վայր" v={<span className="rounded-full bg-kblue px-2.5 py-0.5 font-bold text-white">{s.location}</span>} />
          <Meta k="Տևողություն" v={formatDuration(s.durationSec)} />
          <Meta k="Դիտումներ" v={formatViews(s.viewCount)} />
          <Meta k="Վերբեռնված" v={s.uploadDate || "—"} />
          <div className="col-span-2"><Meta k="Դերասաններ" v={s.actors.join(", ") || "—"} /></div>
        </dl>
      </div>
      <div className="bg-paper2 md:pl-0">
        <div className="border-b border-ink/20 px-5 py-4"><h3 className="font-display text-base tracking-wide">ԵՐԿԽՈՍՈՒԹՅՈՒՆ</h3></div>
        <div className="px-5 py-4">
          {s.lines.length === 0
            ? <p className="text-sm text-muted">Դեռ չկա ձեռքով համադրված տեքստ։{s.textCommon ? ` «${s.textCommon}»` : ""}</p>
            : s.lines.map((ln, i) => (
                <div key={i} className="flex gap-3 border-b border-dashed border-ink/15 py-2.5">
                  <span className="shrink-0 cursor-not-allowed rounded border border-ink/25 bg-white px-1.5 text-[11px] font-bold text-muted" title="Ժամանակը՝ շուտով">⏱</span>
                  <span className="text-sm leading-relaxed">{ln}</span>
                </div>
              ))}
        </div>
      </div>
    </div>
  );
}
function Meta({ k, v }: { k: string; v: React.ReactNode }) {
  return <div><dt className="mb-1 text-[10px] font-bold uppercase tracking-widest text-muted">{k}</dt><dd className="font-semibold">{v}</dd></div>;
}
```

- [ ] **Step 2: The static page with `generateStaticParams`**

Create `web/app/sketch/[id]/page.tsx`:
```tsx
import { notFound } from "next/navigation";
import { ALL, byId } from "@/lib/data";
import WatchView from "@/components/WatchView";

export function generateStaticParams() {
  return ALL.map((s) => ({ id: s.id }));
}

export default async function SketchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const s = byId(id);
  if (!s) notFound();
  return <WatchView s={s} />;
}
```

- [ ] **Step 3: Build to verify all 702 pages export**

Run: `cd web && npm run build`
Expected: build log shows `/sketch/[id]` generating ~702 static pages; `out/sketch/<id>/index.html` exists.

- [ ] **Step 4: Manual smoke**

Run: `npm run dev`, open `http://localhost:3000/sketch/ofvCL_U2Er0`. Expected: player loads, metadata + dialogue render; open a sketch whose `text` is empty (find one from the build log) and confirm the empty-state shows, not a blank panel.

- [ ] **Step 5: Commit**

```bash
git add web/components/WatchView.tsx web/app/sketch
git commit -m "feat(web): static watch page per sketch with empty-state dialogue"
```

---

## Task 13: Random + About pages

**Files:**
- Create: `web/app/random/page.tsx`, `web/app/about/page.tsx`

- [ ] **Step 1: Random (client redirect to a random sketch)**

Create `web/app/random/page.tsx`:
```tsx
"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ALL } from "@/lib/data";

export default function RandomPage() {
  const router = useRouter();
  useEffect(() => {
    const s = ALL[Math.floor(Math.random() * ALL.length)];
    router.replace(`/sketch/${s.id}`);
  }, [router]);
  return <p className="p-10 text-center text-muted">Բացում ենք պատահական սքեթչ…</p>;
}
```

- [ ] **Step 2: About (static)**

Create `web/app/about/page.tsx`:
```tsx
export default function About() {
  return (
    <main className="mx-auto max-w-2xl px-8 py-14">
      <h1 className="font-display text-5xl">Կարգին Արխիվ</h1>
      <p className="mt-5 leading-relaxed opacity-80">
        KarginTV-ի 702 սքեթչ (2012–2013), ձեռքով համադրված տեքստերով։ Որոնիր երկխոսությունը,
        դերասանին կամ վայրը, ու անցիր ուղիղ YouTube։
      </p>
      <p className="mt-4 leading-relaxed opacity-80">
        Տվյալները՝ ձեռքով կուրացված + YouTube Data API։ ~602 սքեթչ ունի համադրված տեքստ. մնացածի
        ամբողջական որոնումը կգա ձայնի տրանսկրիպցիայից հետո։
      </p>
    </main>
  );
}
```

- [ ] **Step 3: Build + smoke**

Run: `cd web && npm run build && npm run dev`. Open `/random` (redirects to a sketch) and `/about`. Expected: both work; `/random` lands on a real sketch each refresh.

- [ ] **Step 4: Commit**

```bash
git add web/app/random web/app/about
git commit -m "feat(web): random redirect page + about page"
```

---

## Task 14: Run full test + lint gate

**Files:** none (verification task)

- [ ] **Step 1: Python tests**

Run: `uv run pytest tests/build -v`
Expected: all pass.

- [ ] **Step 2: Frontend tests + typecheck + build**

Run: `cd web && npm test && npx tsc --noEmit && npm run build`
Expected: vitest all pass, no type errors, static export succeeds (`out/` with `index.html`, `sketch/<id>/index.html`, `about/`, `random/`).

- [ ] **Step 3: Commit (if any incidental fixes)**

```bash
git add -A && git commit -m "test: green build + test gate for website MVP" || echo "nothing to commit"
```

---

## Task 15: GitHub Pages deploy workflow

**Files:**
- Create: `.github/workflows/deploy.yml`

- [ ] **Step 1: Decide URL shape (resolves spec §14.1)**

Pick one and set `basePath` accordingly in `web/next.config.ts`:
- Custom domain or `you.github.io` user page → no `basePath`.
- Project page `you.github.io/kargin_project` → add `basePath: "/kargin_project"`, `assetPrefix: "/kargin_project/"`.

- [ ] **Step 2: Workflow**

Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy to GitHub Pages
on:
  push: { branches: [main] }
  workflow_dispatch:
permissions: { contents: read, pages: write, id-token: write }
concurrency: { group: pages, cancel-in-progress: true }
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv sync
      - run: PYTHONPATH=scripts uv run python scripts/build_site_data.py
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm, cache-dependency-path: web/package-lock.json }
      - run: npm ci
        working-directory: web
      - run: npm run build
        working-directory: web
      - uses: actions/upload-pages-artifact@v3
        with: { path: web/out }
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: { name: github-pages, url: "${{ steps.deployment.outputs.page_url }}" }
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

> **Known CI risk:** `next/font/google` fetches Anton/Inter/Noto from Google **at build time**; a transient fetch failure can flake `next build` in Actions. If a deploy flakes, re-run it; if it recurs, self-host via `next/font/local`.

- [ ] **Step 3: Add `.nojekyll` so `_next/` assets serve**

Run: `touch web/public/.nojekyll`

- [ ] **Step 4: Commit + push; enable Pages**

```bash
git add .github/workflows/deploy.yml web/public/.nojekyll web/next.config.ts
git commit -m "ci: GitHub Pages deploy workflow (python build + next export)"
```
Then in GitHub repo Settings → Pages → Source = "GitHub Actions". Merge `feat/website-mvp` → `main` (or push) to trigger. Expected: Action succeeds, site live at the Pages URL.

---

## Self-review (done while writing)

- **Spec coverage:** Home/Search (T11), Watch view (T12), Random + About (T13), build pipeline + canonicalization (T1–T4), substring search/filters/sort (T8), facet counts (T9), Kargin Classic tokens (T6), GitHub Pages static deploy (T5, T15), data model incl. real titles + empty-states + segments seam (T3, T12). Deferred items (logging, Stats, Find-my-name, semantic, timestamps) intentionally absent — matches spec §2.
- **Placeholder scan:** every code step contains real code; commands have expected output. No TBDs.
- **Type consistency:** `Sketch` (T7) used identically in search (T8), facets (T9), components (T10–T13); `Filters`/`SortKey` defined in `search.ts` and consumed in `SearchExperience`/`FilterRail`. `searchSketches(query, data, filters, sort)` signature consistent across test and callers.
- **Known follow-ups (not blockers):** actor allowlist is refined empirically in T4 Step 3; intercepting-route overlay modal is deferred (plain pages ship, per spec §13.4).
- **Independent review applied (2026-06-16):** real Fisher-Yates shuffle for random sort + test (C1); removed all `tailwind.config.ts` references + added a Tailwind-v4 assert (C2); `setup-uv@v6` (M1); noted `next/font` CI-flake risk (M2) and the JSON-bundle-vs-fetch tradeoff (M3); Hero archive-hours + views now computed from data, not hardcoded (m1). Verified-good: Python pipeline on real data, formatters, Next 15 `params` + `generateStaticParams`.
```
