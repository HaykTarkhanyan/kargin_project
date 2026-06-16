"""Build web/public/data/sketches.json from the curation + metadata CSVs."""
import json
import logging
import os
from collections import Counter
from pathlib import Path

from kargin_build.assemble import build_all, ACTOR_ALLOWLIST

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "public" / "data" / "sketches.json"


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
    OUT.write_text(json.dumps(sketches, ensure_ascii=False, indent=None), encoding="utf-8")
    log.info("wrote %s (%.1f KB)", OUT, OUT.stat().st_size / 1024)


if __name__ == "__main__":
    main()
