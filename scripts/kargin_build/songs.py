"""Fold data/song_matches.csv into per-sketch song lists for the site.

Only `verdict == "confirmed"` rows are used: those are matches a time-shifted
second window agreed with (see scripts/recognize_songs.py). `contradicted` and
`inconclusive` clips are acoustic noise or unverified, and putting them on the
site would assert something we could not reproduce.

One song can be confirmed at several clip offsets; those collapse into a single
entry with every offset kept, so the UI can link to each moment it plays.
"""
import re
from collections import OrderedDict

import pandas as pd

REQUIRED = ["video_id", "start_sec", "matched", "artist", "title", "verdict"]
_PAREN = re.compile(r"\s*[(\[].*$")


def _identity(artist, title):
    """Artist + title without any parenthetical suffix.

    Shazam lists one recording under several entries ("... (Remastered 2024)",
    "... (Official Audio)"); without this they would show as separate songs.
    """
    return (str(artist).strip().casefold(), _PAREN.sub("", str(title)).strip().casefold())


def _clean(v):
    return "" if pd.isna(v) else str(v).strip()


def load_songs(csv_path):
    """{video_id: [{artist, title, album, label, released, url, at: [sec, ...]}]}.

    Returns {} when the file is absent -- song recognition is an optional,
    partially-complete pass, so the site builds fine without it.
    """
    if not csv_path.exists():
        return {}

    df = pd.read_csv(csv_path)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"{csv_path} missing required columns: {missing}")  # loud fail

    df = df[(df["matched"] == True) & (df["verdict"] == "confirmed")]  # noqa: E712 - pandas mask

    by_video = {}
    for vid, group in df.groupby("video_id"):
        songs = OrderedDict()
        for _, r in group.sort_values("start_sec").iterrows():
            key = _identity(r["artist"], r["title"])
            entry = songs.get(key)
            if entry is None:
                entry = {
                    "artist": _clean(r["artist"]),
                    "title": _clean(r["title"]),
                    "album": _clean(r.get("album")),
                    "label": _clean(r.get("label")),
                    # `released` arrives as a float ("1982.0") via pandas
                    "released": _clean(r.get("released")).split(".")[0],
                    "url": _clean(r.get("shazam_url")),
                    "at": [],
                }
                songs[key] = entry
            entry["at"].append(int(r["start_sec"]))

        # Most-heard first: a track confirmed across several clips is the
        # sketch's actual theme, not a one-off sting.
        by_video[str(vid)] = sorted(songs.values(), key=lambda s: (-len(s["at"]), s["at"][0]))

    return by_video
