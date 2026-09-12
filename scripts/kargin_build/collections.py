"""Turn the `collections` column plus data/collections.csv into the site payload.

Membership lives in kargin_eng.csv as `;`-separated slugs; the Armenian name,
description and order live in data/collections.csv. See
docs/superpowers/specs/2026-09-12-collections-design.md.

Everything here fails loudly. A collection is a hand-curated promise that a page
exists and has sketches on it, so a typo must stop the build rather than ship an
empty page or drop a member quietly.
"""
from __future__ import annotations

import re

SLUG_RE = re.compile(r"^[a-z0-9_]+$")


def parse_slugs(value: str | None) -> list[str]:
    """"cards; tv" -> ["cards", "tv"]. Trims, drops blanks, keeps first order."""
    out: list[str] = []
    for part in (value or "").split(";"):
        slug = part.strip()
        if slug and slug not in out:
            out.append(slug)
    return out


def _definitions(definitions) -> list[dict]:
    defs, seen = [], set()
    for d in definitions:
        slug = (d.get("slug") or "").strip()
        if not SLUG_RE.match(slug):
            raise ValueError(f"collections.csv: bad slug {slug!r}, expected [a-z0-9_]+")
        if slug in seen:
            raise ValueError(f"collections.csv: duplicate slug {slug!r}")
        seen.add(slug)

        name = (d.get("name_hy") or "").strip()
        description = (d.get("description_hy") or "").strip()
        if not name:
            raise ValueError(f"collections.csv: {slug} has no name_hy")
        if not description:
            raise ValueError(f"collections.csv: {slug} has no description_hy")

        raw_sort = (d.get("sort") or "").strip()
        try:
            sort = int(raw_sort)
        except ValueError:
            raise ValueError(f"collections.csv: {slug} has a non-integer sort {raw_sort!r}") from None

        defs.append({"slug": slug, "name": name, "description": description, "sort": sort})
    if not defs:
        raise ValueError("collections.csv defines no collections")
    return defs


def build_collections(rows, definitions) -> list[dict]:
    """[{slug, name, description, sketchIds}], ordered by the sort column.

    `rows` are kargin_eng.csv records, `definitions` are data/collections.csv
    records. Member order is the CSV order; the site sorts by view count, so the
    payload stays independent of youtube_metadata.csv.
    """
    defs = _definitions(definitions)
    members: dict[str, list[str]] = {d["slug"]: [] for d in defs}

    for row in rows:
        slugs = parse_slugs(row.get("collections"))
        if not slugs:
            continue

        video_id = (row.get("video_id") or "").strip()
        if not video_id:
            raise ValueError(f"row id {row.get('id')!r} is in {slugs} but has no video_id")

        duplicate_of = (row.get("duplicate_of") or "").strip()
        if duplicate_of:
            raise ValueError(
                f"{video_id} is in {slugs} but is a duplicate of {duplicate_of}; "
                "put the original in the collection instead")

        for slug in slugs:
            if slug not in members:
                raise ValueError(
                    f"{video_id} is in {slug!r}, which data/collections.csv does not define")
            members[slug].append(video_id)

    for d in defs:
        if not members[d["slug"]]:
            raise ValueError(
                f"collection {d['slug']!r} has no members; tag some sketches or remove it")

    return [{"slug": d["slug"], "name": d["name"], "description": d["description"],
             "sketchIds": members[d["slug"]]}
            for d in sorted(defs, key=lambda d: (d["sort"], d["slug"]))]
