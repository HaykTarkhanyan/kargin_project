"""
Find where a piece of audio occurs in a set of recordings, with its time offset.

The engine behind the archive extension (plan Phase 0,
docs/superpowers/plans/2026-11-03-extend-archive.md; DECISIONS #21): which archive
sketch is this fan upload, and where inside a compilation does each sketch play.
A thin layer over audfprint2 (landmark fingerprints), using the settings the
2026-11-03 probe validated.

  build  --index NAME --inputs DIR...    new index of every audio file in DIRs
  add    --index NAME --inputs DIR...    add the files the index doesn't hold yet
  match  --index NAME --queries PATH... --out FILE.jsonl
                                         every hit for every query, one JSON line each

Indexes live in data/audio_index/<NAME>.pklz (gitignored; the 702 rebuild in ~9 min).

A hit says: ref (video id), ref_path, aligned (matched hashes), density (aligned per
second of query), offset_sec (ref time = query time + offset_sec), q_start/q_end (the
matched span of the query). density >= MATCH_DENSITY is a match: on the probe the
weakest true match scored 3.24/s and the strongest spurious one (shared intro stings,
shared songs, reversed speech, noise) 1.14/s. Offsets were exact to 0.02 s. The engine
does NOT survive speed changes (0/40 on sped-up clips), but no real fan upload seems to
be speed-shifted: 0 of 109 unmatched clips matched after a +-3/5% correction, and 0 of
324 after +-1.5% (DECISIONS #21), so this is accepted.

Usage (needs the match group):
  uv run --group match python scripts/audio_index.py build --index archive --inputs data/audio
  uv run --group match python scripts/audio_index.py match --index archive \
      --queries data/candidates/audio --out data/candidates/matches_raw.jsonl
Runtime: ingest ~220x real time (702 files, 34 h of audio: 556 s); match ~2 s per 90 s clip,
~45-65 s per 30-min compilation, ~85% of it analysing the query (measured 2026-11-04). With
--hash-cache a second index reuses that analysis and costs only the lookup.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_DIR = ROOT / "data" / "audio_index"
AUDIO_EXT = {".webm", ".m4a", ".opus", ".mp3", ".wav", ".ogg", ".mp4"}
VIDEO_ID = re.compile(r"([A-Za-z0-9_-]{11})\.[^.]+$")

MATCH_DENSITY = 2.0      # matched hashes per query second; see the module docstring
# audfprint2 settings the probe used (its defaults, except maxtime). 512-point FFT at
# 11025 Hz with a 256 hop = 23.2 ms frames.
SAMPLE_RATE = 11025
DENSITY = 20.0
HASHBITS = 20
BUCKET_DEPTH = 100
MAXTIME_BITS = 16        # 65,536 frames = ~1,520 s; the default 14 bits wraps at ~380 s
MAX_HITS = 10            # floor; see max_hits_for(): long queries hold many recordings
HITS_PER_MINUTE = 6      # a 77-min compilation saturated at 40 hits (review 2026-11-03)
# Every hit with at least this many matched hashes is kept, beyond the cap. No consumer
# accepts a hit with fewer than 30 (map_compilations: 20 s at 1.5/s; a short piece needs 40;
# a copy link 2.0/s over half a 90 s clip), so nothing usable is ever cut.
KEEP_HASHES = 20
ANALYZER = {"density": DENSITY, "pks_per_frame": 5, "fanout": 3, "freq_sd": 30.0, "shifts": 0,
            "samplerate": SAMPLE_RATE}
FRAME_SEC = 256 / SAMPLE_RATE

log = logging.getLogger("audio_index")


def setup_logging() -> None:
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(),
                  logging.FileHandler(ROOT / "logs" / "audio_index.log", encoding="utf-8")],
    )


def video_id_of(path: str | Path) -> str:
    m = VIDEO_ID.search(Path(path).name)
    if not m:
        raise ValueError(f"no 11-character video id at the end of {Path(path).name!r}")
    return m.group(1)


def audio_files(paths: list[Path], from_list: bool = False) -> list[Path]:
    """Audio files under each path (a file, or a folder searched one level deep), sorted.

    from_list: each path is a text file of audio paths, one per line (relative paths are
    relative to the repo root). Avoids Windows' command-line length limit for ~1,000 files.
    """
    if from_list:
        listed = [Path(line.strip()) for lp in paths for line in lp.read_text(encoding="utf-8").splitlines()
                  if line.strip()]
        paths = [x if x.is_absolute() else ROOT / x for x in listed]
    out: list[Path] = []
    for p in paths:
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out += sorted(f for f in p.iterdir() if f.suffix.lower() in AUDIO_EXT)
        else:
            raise FileNotFoundError(p)
    return out


def rel(path: Path) -> str:
    """Repo-relative posix path when inside the repo, so indexes are portable."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def hit_record(name: str, aligned: int, align_frames: float, raw: int, t_min: float, t_max: float,
               query_dur: float) -> dict:
    """One audfprint2 result row as a plain dict, with density and offsets in seconds."""
    return {
        "ref": video_id_of(name),
        "ref_path": name,
        "aligned": int(aligned),
        "raw": int(raw),
        "density": round(int(aligned) / max(query_dur, 1.0), 3),
        "offset_sec": round(float(align_frames) * FRAME_SEC, 2),
        "q_start": round(float(t_min) * FRAME_SEC, 2),
        "q_end": round(float(t_max) * FRAME_SEC, 2),
    }


def max_hits_for(dur_sec: float, floor: int = MAX_HITS) -> int:
    """Hits to keep for a query this long. Hits come back ranked by matched hashes, so a
    fixed cap silently drops the weaker real recordings in a long compilation."""
    return max(floor, int(dur_sec / 60 * HITS_PER_MINUTE))


def keep_n(aligned_desc, cap: int) -> int:
    """How many of the strongest-first hits to keep: the cap, or every hit with at least
    KEEP_HASHES matched hashes, whichever is more.

    audfprint computes every hit and its cap is only a slice of that list, so the cap
    never saved work, only dropped hits. A fixed cap cut real ones: a 12-min highlight
    reel held 71+ archive pieces, and a fan clip with 25+ re-uploads filled 25 slots with
    copies of 477-688 hashes (2026-11-03).
    """
    return max(min(cap, len(aligned_desc)), sum(1 for a in aligned_desc if a >= KEEP_HASHES))


def _analyzer(is_match: bool):
    from audfprint2 import cli
    return cli.setup_analyzer(is_match=is_match, continue_on_error=False, ffmpeg_path=None, **ANALYZER)


def _query_hashes(an, f: Path, cache: Path | None):
    """The query's landmark hashes, analysed once per file when `cache` is a folder.

    Analysis is most of a match and doesn't depend on the index: profiled 2026-11-04, a
    511 s pool video took 23.6 s to match, 20.6 s of it analysing the audio. Without a
    cache, mapping the pool against two indexes analysed every video twice.
    """
    import numpy as np

    if cache is None:
        return an.wavfile2hashes(str(f))
    st = f.stat()
    key = json.dumps({"size": st.st_size, "mtime_ns": st.st_mtime_ns, **ANALYZER}, sort_keys=True)
    c = cache / f"{video_id_of(f)}.npz"
    if c.exists():
        with np.load(c) as z:
            if str(z["key"]) == key:
                return z["hashes"]
        log.info(f"{f.name}: cached hashes are stale (the file or the analyzer settings changed); re-analysing")
    q = an.wavfile2hashes(str(f))
    cache.mkdir(parents=True, exist_ok=True)
    tmp = c.with_suffix(".tmp")
    with open(tmp, "wb") as fh:
        np.savez_compressed(fh, hashes=q, key=np.array(key))
    tmp.replace(c)                     # never leave a half-written cache file behind
    return q


def ingest(index: str, inputs: list[Path], new: bool, from_list: bool = False) -> None:
    from audfprint2.core import hash_table

    path = INDEX_DIR / f"{index}.pklz"
    if new:
        if path.exists():
            raise FileExistsError(f"{path} exists; use `add`, or move it aside to rebuild")
        ht = hash_table.HashTable(hashbits=HASHBITS, depth=BUCKET_DEPTH, maxtime=1 << MAXTIME_BITS)
        ht.params["samplerate"] = SAMPLE_RATE
    else:
        ht = hash_table.HashTable(str(path))
    have = {video_id_of(n) for n in ht.names if n}
    files = [f for f in audio_files(inputs, from_list) if video_id_of(f) not in have]
    log.info(f"{'new' if new else 'add to'} index {index}: {len(have)} already in, {len(files)} to ingest")
    an = _analyzer(is_match=False)
    capacity = (1 << MAXTIME_BITS) * FRAME_SEC
    t0 = time.time()
    for i, f in enumerate(files, 1):
        # Read the file by its absolute path but label it repo-relative: audfprint's own
        # ingest() uses one string for both, which only worked when run from the repo root.
        hashes = an.wavfile2hashes(str(f))
        ht.store(rel(f), [(int(tm), int(hs)) for tm, hs in hashes.tolist()])
        dur = an.soundfiledur
        if dur > capacity:
            raise ValueError(f"{f.name} is {dur:.0f} s, longer than the index's {capacity:.0f} s time range; "
                             f"its offsets would wrap. Raise MAXTIME_BITS and rebuild.")
        if i % 50 == 0 or i == len(files):
            el = time.time() - t0
            log.info(f"[{i}/{len(files)}] ({el:.0f}s elapsed, ~{el / i * (len(files) - i):.0f}s left)")
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    ht.save(str(path))
    log.info(f"saved {path} ({len(ht.names)} recordings) in {time.time() - t0:.0f}s")


def match(index: str, queries: list[Path], out: Path, max_hits: int = MAX_HITS,
          from_list: bool = False, time_quantile: float = 0.05, hash_cache: Path | None = None) -> None:
    """max_hits is a floor: each query keeps keep_n(), i.e. max_hits_for(its duration) hits
    or every hit with >= KEEP_HASHES, whichever is more. time_quantile sets q_start/q_end to
    that quantile of the matched hash times (0.05 trims ~5% off each end; compilations use
    0.0 so adjacent sketches don't leave false 30 s gaps between them). hash_cache: a folder
    that keeps each query's analysis for the next index (see _query_hashes)."""
    from audfprint2 import cli
    from audfprint2.core import hash_table

    ht = hash_table.HashTable(str(INDEX_DIR / f"{index}.pklz"))
    an = _analyzer(is_match=True)
    ma = cli.setup_matcher(match_win=2, search_depth=100, min_count=3, max_matches=max_hits,
                           exact_count=False, find_time_range=True, time_quantile=time_quantile,
                           sortbytime=False, illustrate=False, illustrate_hpf=False)
    done = set()
    if out.exists():
        done = {json.loads(line)["query"] for line in out.read_text(encoding="utf-8").splitlines() if line}
    files = [f for f in audio_files(queries, from_list) if rel(f) not in done]
    log.info(f"match against {index} ({len(ht.names)} recordings): {len(done)} done, {len(files)} to go")
    out.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with open(out, "a", encoding="utf-8") as fh:
        for i, f in enumerate(files, 1):
            # What Matcher.match_file does, split so the analysis can be cached: hashes, the
            # duration as the last hash time, every hit strongest first, then our own slice.
            q = _query_hashes(an, f, hash_cache)
            dur = an.n_hop * q[-1][0] / an.target_sr if len(q) else 0.0
            nhash = len(q)
            allr = ma.match_hashes(ht, q)
            cap = max_hits_for(dur, max_hits)
            n = keep_n([int(a) for a in allr[:, 1]], cap) if len(allr) else 0
            if n > cap:
                log.info(f"{f.name}: kept {n} hits with >= {KEEP_HASHES} hashes, above the cap of {cap} "
                         f"(best {int(allr[0, 1])})")
            rslts = allr[:n]
            hits = [hit_record(str(ht.names[hid]), n_al, align, n_raw, tmin, tmax, float(dur))
                    for (hid, n_al, align, n_raw, _rank, tmin, tmax) in rslts]
            fh.write(json.dumps({"query": rel(f), "video_id": video_id_of(f), "query_dur": round(float(dur), 2),
                                 "query_hashes": int(nhash), "hits": hits}) + "\n")
            fh.flush()
            if i % 25 == 0 or i == len(files):
                el = time.time() - t0
                log.info(f"[{i}/{len(files)}] ({el:.0f}s elapsed, ~{el / i * (len(files) - i):.0f}s left)")
    log.info(f"wrote {out} in {time.time() - t0:.0f}s")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "add"):
        p = sub.add_parser(name)
        p.add_argument("--index", required=True)
        p.add_argument("--inputs", nargs="+", type=Path, required=True)
        p.add_argument("--from-list", action="store_true", help="--inputs are text files listing audio paths")
    p = sub.add_parser("match")
    p.add_argument("--index", required=True)
    p.add_argument("--queries", nargs="+", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--from-list", action="store_true", help="--queries are text files listing audio paths")
    p.add_argument("--time-quantile", type=float, default=0.05,
                   help="quantile of matched hash times reported as q_start/q_end (0 = full extent)")
    p.add_argument("--max-hits", type=int, default=MAX_HITS,
                   help="floor of hits kept per query (every hit with >= KEEP_HASHES is kept anyway)")
    p.add_argument("--hash-cache", type=Path, default=None,
                   help="folder that keeps each query's analysis, so matching it against another index is fast")
    args = ap.parse_args()
    setup_logging()
    if args.cmd in ("build", "add"):
        ingest(args.index, args.inputs, new=args.cmd == "build", from_list=args.from_list)
    else:
        match(args.index, args.queries, args.out, args.max_hits, from_list=args.from_list,
              time_quantile=args.time_quantile, hash_cache=args.hash_cache)
    return 0


if __name__ == "__main__":
    sys.exit(main())
