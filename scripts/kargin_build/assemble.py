"""Turn a joined CSV row into the site's sketch dict, and build the full list."""
import pandas as pd
from .parse import extract_video_id, parse_seq
from .canon import canonicalize_actors, canonicalize_location, canonicalize_languages

# Seed from the known cast; refined empirically from top non-allowlist tokens (Task 4).
ACTOR_ALLOWLIST = {
    "Հայկո", "Մկո", "Հասմիկ", "Լևոն", "Անդո", "Քրիստինե", "Աշոտ", "Արմինե",
    "Ռաֆո", "Արմեն", "Սմբո", "Մարի", "Հայո", "Սիմոնյան", "Հովո", "Սամվել", "Սամ",
    "Գեղամ", "Վաղո", "Պետրոսյան", "Վարդան", "Սաքո", "Մամիկոն", "Գագո",
    "Վաչո", "Ստյոպ", "Գուգո",
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
        "textCommon": _s(row.get("text_common")),
        "actors": actors,
        "actorsRaw": _s(row.get("main_actors")),
        "rolesNames": ", ".join([r for r in [roles, *roles_extra] if r]),
        "location": canonicalize_location(_s(row.get("location"))),
        "languages": canonicalize_languages(_s(row.get("languages"))),
        "lighting": _s(row.get("lighting")),
        "durationSec": int(row["duration_sec"]) if not pd.isna(row["duration_sec"]) else None,
        "viewCount": int(row["view_count"]) if not pd.isna(row["view_count"]) else None,
        "uploadDate": _fmt_date(row.get("upload_date")),
    }


_METADATA_COLS = ["video_id", "duration_sec", "view_count", "upload_date"]


def build_all(kargin_csv, metadata_csv, allowlist=ACTOR_ALLOWLIST, typos=ACTOR_TYPOS):
    k = pd.read_csv(kargin_csv)
    m = pd.read_csv(metadata_csv)
    missing = [c for c in _METADATA_COLS if c not in m.columns]
    if missing:
        raise ValueError(f"metadata CSV missing required columns: {missing}")  # loud fail
    m = m[_METADATA_COLS]
    if m["video_id"].duplicated().any():
        dups = m.loc[m["video_id"].duplicated(), "video_id"].tolist()
        raise ValueError(f"metadata CSV has duplicate video_ids: {dups[:10]}")  # a left-merge would fan out rows
    k["video_id"] = k["links"].map(lambda u: extract_video_id(u) if isinstance(u, str) else None)
    if k["video_id"].isna().any():
        raise ValueError(f"{k['video_id'].isna().sum()} rows have no parseable video_id")  # loud fail
    df = k.merge(m, on="video_id", how="left")
    if len(df) != len(k):
        raise ValueError(f"row count changed in merge: {len(k)} -> {len(df)} (duplicate video_ids?)")
    return [row_to_sketch(r, allowlist, typos) for _, r in df.iterrows()]
