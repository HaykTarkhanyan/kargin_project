"""Propose members for each site collection by searching the annotations.

Collections are hand-curated (see docs/superpowers/specs/2026-09-12-collections-
design.md). This script only PROPOSES: it writes data/collections_candidates.csv
with one row per (theme, sketch) and the matching phrase as evidence, so each row
can be judged without opening the video. A human marks `include` as `y`, then
apply_collection_candidates.py turns the ticks into corrections rows.

Two strengths of evidence, because they need different amounts of attention:

  strong  the phrase names the situation ("four men playing cards", "watching
          television"), or the annotation's own topics tag it (medical, or the
          police+transport overlap a traffic stop produces)
  weak    the word merely appears ("a television" among the props of a shop).
          Most weak rows are wrong; they are listed so the search is honest
          about what it found, not because they are likely members.

Re-running preserves whatever `include` marks the file already has.

Usage:
    uv run python scripts/non_essential/seed_collection_candidates.py
    uv run python scripts/non_essential/seed_collection_candidates.py --themes cards,tv
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "seed_collection_candidates.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

THEMES: dict[str, dict] = {
    "cards": {
        "strong": [r"playing cards?", r"card game", r"\bpoker\b", r"deck of cards",
                   r"play(?:s|ing)? (?:a game of )?cards", r"card table", r"\bbelote\b"],
        "weak": [r"\bcards?\b", r"\bbackgammon\b", r"\bnardi\b", r"\bgambl", r"\bcasino\b"],
    },
    "tv": {
        "strong": [r"watch(?:ing|es)?(?: the)?[ -](?:television|tv)\b",
                   r"in front of (?:the |a )?(?:television|tv)\b",
                   r"tv (?:screen|programme|program|show|broadcast)",
                   r"(?:television|tv) (?:is )?(?:on|playing)"],
        "weak": [r"\btelevision\b", r"\btv\b"],
    },
    # Deliberately setting-based, not mention-based. "doctor", "patient" and the
    # annotations' own `medical` topic each match over a hundred sketches, because
    # a doctor gets mentioned in passing everywhere; that is a filter, not a
    # collection. Strong means the scene happens somewhere medical.
    "doctor": {
        "strong": [r"\bhospital\b", r"\bclinic\b", r"\bpolyclinic\b", r"\bdentist\b",
                   r"\bsurgeon\b", r"examination (?:room|table)", r"doctors? office",
                   r"operating (?:room|table)", r"medical cent(?:er|re)", r"\bmaternity\b"],
        "weak": [r"\bdoctor\b", r"\bpatient\b", r"\bnurse\b", r"\bmedic", r"\bpharmac",
                 r"\bambulance\b", r"\binjection\b"],
    },
    "traffic_police": {
        "strong": [r"traffic police", r"traffic cop", r"road police", r"pulled over",
                   r"drivers? licen[cs]e", r"traffic stop", r"traffic officer"],
        "topics_all": ["police", "transport"],
        "weak": [r"\bpolice officer\b", r"\bpoliceman\b", r"\bhighway\b", r"\bcar\b.{0,40}\bpolice\b"],
    },
}


def _context(text: str, m: re.Match, width: int = 34) -> str:
    start = max(0, m.start() - width)
    end = min(len(text), m.end() + width)
    return " ".join(text[start:end].split())


def _joined(v) -> str:
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    if isinstance(v, dict):
        return ", ".join(f"{k}: {_joined(x)}" for k, x in v.items())
    return str(v or "")


def _text_fields(doc: dict) -> list[tuple[str, str]]:
    a = doc.get("annotation") or {}
    return [(k, _joined(a.get(k))) for k in
            ("title_en", "summary_en", "summary_detailed_en", "keywords_en", "catchphrases")]


def _visual_fields(doc: dict) -> list[tuple[str, str]]:
    return [(k, _joined(doc.get(k))) for k in
            ("visual_synopsis", "location_fine", "key_props", "character_types", "scene_structure")]


def _topics(doc: dict) -> list[str]:
    return [str(t).strip().lower() for t in ((doc.get("annotation") or {}).get("topics") or [])]


def _scan(fields: list[tuple[str, str]], patterns: list[str], source: str) -> tuple[str, str] | None:
    for field, text in fields:
        if not text:
            continue
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return f"{source}.{field}", _context(text, m)
    return None


def collect(text_dir: Path, visual_dir: Path, themes: dict) -> dict[tuple[str, str], dict]:
    """{(theme, video_id): {strength, where, evidence}} - strongest evidence wins."""
    found: dict[tuple[str, str], dict] = {}

    def record(theme: str, vid: str, strength: str, where: str, evidence: str) -> None:
        key = (theme, vid)
        existing = found.get(key)
        if existing and (existing["strength"] == "strong" or existing["strength"] == strength):
            return
        found[key] = {"strength": strength, "where": where, "evidence": evidence}

    for path in sorted(text_dir.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        vid = doc.get("video_id") or path.stem
        fields, topics = _text_fields(doc), _topics(doc)
        for theme, cfg in themes.items():
            any_t = cfg.get("topics_any") or []
            all_t = cfg.get("topics_all") or []
            tagged = (any_t and any(t in topics for t in any_t)) or (all_t and all(t in topics for t in all_t))
            if tagged:
                record(theme, vid, "strong", "text.topics", ", ".join(topics))
            hit = _scan(fields, cfg.get("strong", []), "text")
            if hit:
                record(theme, vid, "strong", hit[0], hit[1])
            elif not tagged:
                hit = _scan(fields, cfg.get("weak", []), "text")
                if hit:
                    record(theme, vid, "weak", hit[0], hit[1])

    for path in sorted(visual_dir.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        vid = doc.get("video_id") or path.stem
        fields = _visual_fields(doc)
        for theme, cfg in themes.items():
            hit = _scan(fields, cfg.get("strong", []), "visual")
            if hit:
                record(theme, vid, "strong", hit[0], hit[1])
            else:
                hit = _scan(fields, cfg.get("weak", []), "visual")
                if hit:
                    record(theme, vid, "weak", hit[0], hit[1])
    return found


def main(csv_path: Path, text_dir: Path, visual_dir: Path, out: Path, only: list[str] | None) -> int:
    for d in (text_dir, visual_dir):
        if not d.is_dir():
            logging.error(f"missing annotation directory: {d}")
            return 2
    themes = {k: v for k, v in THEMES.items() if not only or k in only}
    if not themes:
        logging.error(f"no such theme(s): {only}; known: {sorted(THEMES)}")
        return 2

    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    by_vid = {r["video_id"]: r for r in df.to_dict("records") if r.get("video_id")}

    previous: dict[tuple[str, str], str] = {}
    if out.exists():
        old = pd.read_csv(out, dtype=str, keep_default_na=False)
        previous = {(r["theme"], r["video_id"]): r.get("include", "") for r in old.to_dict("records")}
        logging.info(f"keeping {sum(1 for v in previous.values() if v.strip())} existing include mark(s)")

    found = collect(text_dir, visual_dir, themes)
    rows = []
    for (theme, vid), hit in sorted(found.items()):
        row = by_vid.get(vid)
        if row is None:
            logging.warning(f"{vid}: matched {theme} but is not in {csv_path.name}; skipped")
            continue
        rows.append({
            "theme": theme,
            "video_id": vid,
            "kargin_id": row.get("id", ""),
            "title": (row.get("titles") or "").split(";")[0].strip(),
            "duplicate_of": row.get("duplicate_of", ""),
            "strength": hit["strength"],
            "where": hit["where"],
            "evidence": hit["evidence"][:200],
            "include": previous.get((theme, vid), ""),
        })

    rows.sort(key=lambda r: (r["theme"], r["strength"] != "strong", r["video_id"]))
    pd.DataFrame(rows, columns=["theme", "video_id", "kargin_id", "title", "duplicate_of",
                                "strength", "where", "evidence", "include"]).to_csv(
        out, index=False, encoding="utf-8", lineterminator="\r\n")

    for theme in sorted(themes):
        strong = sum(1 for r in rows if r["theme"] == theme and r["strength"] == "strong")
        weak = sum(1 for r in rows if r["theme"] == theme and r["strength"] == "weak")
        logging.info(f"{theme}: {strong} strong, {weak} weak")
    logging.info(f"wrote {len(rows)} candidate row(s) -> {out}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", default=ROOT / "kargin_eng.csv", type=Path)
    p.add_argument("--text-dir", default=ROOT / "data" / "text_annotations", type=Path)
    p.add_argument("--visual-dir", default=ROOT / "data" / "visual_annotations", type=Path)
    p.add_argument("--out", default=ROOT / "data" / "collections_candidates.csv", type=Path)
    p.add_argument("--themes", default="", help="comma-separated subset")
    a = p.parse_args()
    raise SystemExit(main(a.csv, a.text_dir, a.visual_dir, a.out,
                          [t for t in a.themes.split(",") if t] or None))
