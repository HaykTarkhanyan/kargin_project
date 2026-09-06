"""Pure-logic tests for scripts/sync_firestore.py — no network, no emulator."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import pytest
from sync_firestore import check_delete_guard, content_hash, plan_sync


def test_content_hash_is_stable_and_key_order_independent():
    a = {"id": "x", "title": "t", "actors": ["a", "b"]}
    b = {"actors": ["a", "b"], "title": "t", "id": "x"}
    assert content_hash(a) == content_hash(b)
    assert content_hash(a) != content_hash({**a, "title": "changed"})


def test_content_hash_survives_armenian_text():
    assert len(content_hash({"text": "Կարգին"})) == 64


def test_plan_sync_diffs_by_hash():
    desired = {"a": "h1", "b": "h2", "c": "h3"}
    existing = {"a": "h1", "b": "OLD", "d": "h4"}
    to_write, to_delete = plan_sync(desired, existing)
    assert to_write == ["b", "c"]  # changed + new, sorted
    assert to_delete == ["d"]  # gone from desired


def test_plan_sync_second_run_is_empty():
    desired = {"a": "h1"}
    assert plan_sync(desired, dict(desired)) == ([], [])


def test_delete_guard_blocks_mass_delete():
    with pytest.raises(RuntimeError, match="mass delete"):
        check_delete_guard(existing_count=700, delete_count=100, allow=False)


def test_delete_guard_allows_small_or_forced():
    check_delete_guard(existing_count=700, delete_count=10, allow=False)  # < 5%
    check_delete_guard(existing_count=700, delete_count=100, allow=True)  # forced
    check_delete_guard(existing_count=0, delete_count=0, allow=False)  # empty mirror
