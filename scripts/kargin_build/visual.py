"""Fold data/visual_annotations/*.json into the site payload.

One JSON per video, produced by vision models reading the contact sheets in
data/contact_sheets/ (blind: no CSV or transcript access). See
.claude/skills/annotate-sheets/SKILL.md for the schema and how they are made.

Only the site-relevant subset ships: the searchable strings (synopsis, fine
location, characters, props, animals, vehicles) plus drag/physicality flags and
the representative frame timestamp. Machine bookkeeping (people_count,
scene_structure, needs_audio, indoor/outdoor) stays in the repo files.

The synopses are English while the site is Armenian. They ship anyway: for the
~90 sketches whose transcripts are garbage and whose curation is empty, the
synopsis is the only description of the sketch that exists at all.
"""
import json


def load_visual(dir_path):
    """{video_id: compact visual dict}. {} when the directory is absent.

    Empty arrays and false flags are omitted per field, same philosophy as
    songs/transcripts: an always-empty field on 702 rows is payload for nothing.
    """
    if not dir_path.exists():
        return {}

    out = {}
    for p in sorted(dir_path.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        vid = d.get("video_id")
        if not vid:
            raise ValueError(f"{p.name}: missing video_id")  # loud fail
        if vid in out:
            raise ValueError(f"duplicate visual annotation for {vid} ({p.name})")
        v = {
            "locationFine": d["location_fine"],
            "synopsis": d["visual_synopsis"],
            "physicality": d["physicality"],
            "bestFrameTs": d["best_frame_ts"],
            "confidence": d["confidence"],
        }
        for src, dst in (("character_types", "characterTypes"), ("key_props", "keyProps"),
                         ("animals", "animals"), ("vehicles", "vehicles")):
            if d[src]:
                v[dst] = d[src]
        if d["drag"]:
            v["drag"] = True
        out[vid] = v
    return out
