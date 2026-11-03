"""The archive's file-number prefix (the NNN_ in data/audio/NNN_<title>_<id>.webm).

Every per-sketch file is named after the sketch's `id` in kargin_eng.csv. The
downloaders used to recompute that number as the row position among the PUBLIC rows
of data/youtube_metadata.csv, so one archive video turning unlisted would have
shifted every later download onto the wrong number (DECISIONS #19, Q19). Reading the
`id` column instead makes the number a property of the row, not of its neighbours.

New rows get their `id` when they are added (plan step B1), before anything is
downloaded for them, so a video with no row here is an error, not a default.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

KARGIN_CSV = Path(__file__).resolve().parents[1] / "kargin_eng.csv"


def load_seq_of(kargin_csv: Path, video_ids: Iterable[str]) -> dict[str, int]:
    """video_id -> its `id` as an int, for each requested video. Fails loudly on any gap."""
    k = pd.read_csv(kargin_csv, dtype={"id": str, "video_id": str})
    dup = k.loc[k["id"].duplicated(keep=False), "id"].unique().tolist()
    if dup:
        raise ValueError(f"duplicate id values in {kargin_csv.name}: {dup[:10]}")
    dup_vid = k.loc[k["video_id"].duplicated(keep=False), "video_id"].unique().tolist()
    if dup_vid:
        raise ValueError(f"video_id appears on more than one row of {kargin_csv.name}: {dup_vid[:10]}")
    bad = k.loc[~k["id"].fillna("").str.fullmatch(r"\d+"), "id"].tolist()
    if bad:
        raise ValueError(f"id is not a number in {kargin_csv.name}: {bad[:10]}")
    seq = dict(zip(k["video_id"], k["id"].astype(int)))
    wanted = list(video_ids)
    missing = [v for v in wanted if v not in seq]
    if missing:
        raise ValueError(f"{len(missing)} video(s) have no row in {kargin_csv.name}, so no file "
                         f"number; add the rows to {kargin_csv.name} with an id first (plan step B1): {missing[:10]}")
    return {v: seq[v] for v in wanted}
