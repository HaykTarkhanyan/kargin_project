"""Turn a joined CSV row into the site's sketch dict, and build the full list."""
import pandas as pd
from .parse import extract_video_id, parse_seq
from .canon import canonicalize_actors, canonicalize_location, canonicalize_languages
from .songs import load_songs
from .transcripts import load_transcripts, novelty
from .visual import load_visual

# Seed from the known cast; refined empirically from top non-allowlist tokens (Task 4).
ACTOR_ALLOWLIST = {
    "Հայկո", "Մկո", "Հասմիկ", "Լևոն", "Անդո", "Քրիստինե", "Աշոտ", "Արմինե",
    "Ռաֆո", "Արմեն", "Սմբո", "Մարի", "Հայո", "Սիմոնյան", "Հովո", "Սամվել", "Սամ",
    "Գեղամ", "Վաղո", "Պետրոսյան", "Վարդան", "Սաքո", "Մամիկոն", "Գագո",
    "Վաչո", "Ստյոպ", "Գուգո",
}
ACTOR_TYPOS = {"Հակյո": "Հայկո", "ՄԿո": "Մկո"}

# A transcript rides along only when at least this fraction of its sentences say
# something curation does not already contain.
#
# This replaced a length-ratio test, which measured the wrong thing. Curation and
# a transcript routinely run the SAME LENGTH while covering different parts of a
# sketch -- the curator writes the punchlines, the recogniser catches a monologue.
# The length rule dropped 26 of 31 pilot videos whose transcripts carried a median
# 27% new dialogue.
MIN_TRANSCRIPT_NOVELTY = 0.25


def _s(v):
    return "" if pd.isna(v) else str(v).strip()


def _fmt_date(raw):
    d = _s(raw).split(".")[0]                      # "20130410.0" -> "20130410"
    return f"{d[0:4]}-{d[4:6]}-{d[6:8]}" if len(d) == 8 else ""


def row_to_sketch(row, allowlist, typos, songs=None, transcripts=None, visual=None):
    vid = extract_video_id(_s(row.get("links")))
    actors, roles_extra = canonicalize_actors(_s(row.get("main_actors")), allowlist, typos)
    roles = _s(row.get("roles_names"))
    text = _s(row.get("text"))
    out = {
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
    # Omitted when empty rather than shipped as [] on all 702 rows: song
    # recognition covers only part of the archive, and an always-empty field is
    # exactly what the 2026-06-22 payload cleanup removed.
    found = (songs or {}).get(vid)
    if found:
        out["songs"] = found

    # Same rule as songs: omitted entirely when absent rather than shipped empty
    # on all 702 rows. Kept under its own key, never merged into `text` -- one is
    # a person's transcription, the other a machine's, and the page says which.
    #
    # Shipped only when it ADDS something, judged by how much of it curation does
    # not already say -- not by how long it is.
    tr = (transcripts or {}).get(vid)
    if tr:
        n = novelty(text, tr["text"])
        if n >= MIN_TRANSCRIPT_NOVELTY:
            out["transcript"] = {**tr, "novelty": round(n, 2)}

    # Machine-read scene metadata from the contact sheets. Ships whole (unlike
    # transcripts there is no novelty gate): even where curation is rich, the
    # visual layer holds facts text never carries — props, animals, drag, the
    # fine-grained setting.
    vis = (visual or {}).get(vid)
    if vis:
        out["visual"] = vis
    return out


_METADATA_COLS = ["video_id", "duration_sec", "view_count", "upload_date"]


def build_all(kargin_csv, metadata_csv, allowlist=ACTOR_ALLOWLIST, typos=ACTOR_TYPOS,
              songs_csv=None, transcripts_dir=None, visual_dir=None):
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
    songs = load_songs(songs_csv) if songs_csv else {}
    transcripts = load_transcripts(transcripts_dir) if transcripts_dir else {}
    visual = load_visual(visual_dir) if visual_dir else {}
    return [row_to_sketch(r, allowlist, typos, songs, transcripts, visual) for _, r in df.iterrows()]
