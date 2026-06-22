"""Build web/public/data/sketches.json from the curation + metadata CSVs."""
import json
import logging
import os
from collections import Counter
from pathlib import Path

from kargin_build.assemble import build_all, ACTOR_ALLOWLIST
from kargin_build.stats import build_stats

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "public" / "data" / "sketches.json"


def _atomic_write(path: Path, text: str) -> None:
    """Write to a temp file then os.replace, so a crash mid-write can't corrupt the output."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


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
    _atomic_write(OUT, json.dumps(sketches, ensure_ascii=False, indent=None))
    log.info("wrote %s (%.1f KB)", OUT, OUT.stat().st_size / 1024)

    stats = build_stats(sketches)
    stats_out = OUT.parent / "stats.json"
    _atomic_write(stats_out, json.dumps(stats, ensure_ascii=False))
    log.info("wrote %s (%.1f KB)", stats_out, stats_out.stat().st_size / 1024)


if __name__ == "__main__":
    main()
