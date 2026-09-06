"""Mirror web/public/data/sketches.json into the Firestore `sketches` collection.

Diffs by a contentHash field so an unchanged corpus produces zero writes.
Deletes docs that left the JSON, but refuses to delete >5% of the mirror
unless --allow-mass-delete is passed (a truncated-but-valid JSON must not
silently wipe it). Fails loudly on any error. Runs in CI after a successful
deploy; also runnable locally with GOOGLE_APPLICATION_CREDENTIALS set, or
against the emulator with FIRESTORE_EMULATOR_HOST.
"""
import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

SKETCHES_JSON = Path("web/public/data/sketches.json")
DELETE_GUARD_FRACTION = 0.05
BATCH_LIMIT = 400  # Firestore caps batches at 500 ops; stay clear of it

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("logs/sync_firestore.log", encoding="utf-8")],
)
log = logging.getLogger("sync_firestore")


def content_hash(sketch: dict) -> str:
    canonical = json.dumps(sketch, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def plan_sync(desired: dict[str, str], existing: dict[str, str]) -> tuple[list[str], list[str]]:
    """desired/existing map sketch id -> contentHash. Returns (to_write, to_delete), sorted."""
    to_write = sorted(i for i, h in desired.items() if existing.get(i) != h)
    to_delete = sorted(set(existing) - set(desired))
    return to_write, to_delete


def check_delete_guard(existing_count: int, delete_count: int, allow: bool) -> None:
    if allow or delete_count == 0:
        return
    if delete_count > existing_count * DELETE_GUARD_FRACTION:
        raise RuntimeError(
            f"mass delete blocked: {delete_count} of {existing_count} mirror docs would be "
            f"deleted (> {DELETE_GUARD_FRACTION:.0%}). Re-run with --allow-mass-delete if intended."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.environ.get("FIREBASE_PROJECT_ID"), help="GCP project id")
    parser.add_argument("--dry-run", action="store_true", help="plan only, write nothing")
    parser.add_argument("--allow-mass-delete", action="store_true")
    args = parser.parse_args()
    if not args.project:
        parser.error("--project or FIREBASE_PROJECT_ID required")

    sketches = json.loads(SKETCHES_JSON.read_text(encoding="utf-8"))
    if not isinstance(sketches, list) or not sketches:
        raise RuntimeError(f"{SKETCHES_JSON} is empty or not a list — refusing to sync")
    by_id = {s["id"]: s for s in sketches}
    if len(by_id) != len(sketches):
        raise RuntimeError("duplicate sketch ids in sketches.json")
    desired = {i: content_hash(s) for i, s in by_id.items()}

    from google.cloud import firestore  # deferred: pure-logic tests need no credentials

    db = firestore.Client(project=args.project)
    col = db.collection("sketches")
    # to_dict().get, not snap.get(): snap.get raises KeyError on docs missing the field
    existing = {snap.id: (snap.to_dict().get("contentHash") or "") for snap in col.select(["contentHash"]).stream()}

    to_write, to_delete = plan_sync(desired, existing)
    check_delete_guard(len(existing), len(to_delete), args.allow_mass_delete)
    log.info(f"mirror: {len(existing)} existing, {len(desired)} desired -> "
             f"{len(to_write)} writes, {len(to_delete)} deletes{' (dry-run)' if args.dry_run else ''}")
    if args.dry_run:
        return

    ops = 0
    batch = db.batch()
    for sid in to_write:
        batch.set(col.document(sid), {**by_id[sid], "contentHash": desired[sid]})
        ops += 1
        if ops % BATCH_LIMIT == 0:
            batch.commit()
            batch = db.batch()
    for sid in to_delete:
        batch.delete(col.document(sid))
        ops += 1
        if ops % BATCH_LIMIT == 0:
            batch.commit()
            batch = db.batch()
    if ops % BATCH_LIMIT:
        batch.commit()
    log.info(f"done: {len(to_write)} written, {len(to_delete)} deleted")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("sync failed")
        sys.exit(1)
