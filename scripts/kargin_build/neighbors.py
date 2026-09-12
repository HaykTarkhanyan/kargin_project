"""Fold data/embeddings/top_neighbors.json into the site payload.

Semantic neighbours from gemini-embedding-2 over each sketch's detailed English
summary (see DECISIONS.md #12). Replaces actor-overlap as the primary source for
the site's "ՆՄԱՆԱՏԻՊ" list: actor overlap says who is in it, this says what it is
about.

Only pairs at or above MIN_SCORE ship. That cutoff is not cosmetic -- measured
over all 246,051 pairs, matches are excellent above 0.80, mixed in 0.70-0.75 and
noise below 0.70 ("The Boss and the Seductive Secretary" pairs with "Nazi
Interrogation" at 0.669). Only 292 of 702 sketches have any neighbour this good,
so most rows carry a short list or none, and the caller fills the remainder.
"""
import json

# Cosine floor for a neighbour worth showing. Raising it shows fewer, better
# matches; the full matrix is in data/embeddings/, so re-deriving costs no API call.
MIN_SCORE = 0.75


def load_neighbors(path, min_score=MIN_SCORE, limit=6):
    """{video_id: [{"id": video_id, "score": float}, ...]}. {} when absent.

    Omitted per sketch when nothing clears the floor, same rule as songs and
    visual: an always-empty field on 702 rows is payload for nothing.
    """
    if not path.exists():
        return {}

    doc = json.loads(path.read_text(encoding="utf-8"))
    if "neighbors" not in doc:
        raise ValueError(f"{path.name}: no 'neighbors' key")  # loud fail

    out = {}
    for vid, pairs in doc["neighbors"].items():
        kept = [{"id": nid, "score": round(float(score), 3)}
                for nid, score in pairs if float(score) >= min_score][:limit]
        if kept:
            out[vid] = kept
    return out
