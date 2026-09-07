from datetime import datetime, timedelta, timezone

import pytest

from data_lake import manifest


@pytest.fixture(autouse=True)
def _isolated_manifest(tmp_path, monkeypatch):
    """Jeder Test bekommt sein eigenes, leeres manifest.json -- nie das echte
    data_lake_store/manifest.json aus einer laufenden Ingestion anfassen."""
    monkeypatch.setattr(manifest, "MANIFEST_PATH", tmp_path / "manifest.json")


def test_cutoff_class_for_groups_timeframes_correctly():
    assert manifest.cutoff_class_for("M5") == "fast"
    assert manifest.cutoff_class_for("M15") == "fast"
    assert manifest.cutoff_class_for("H1") == "fast"
    assert manifest.cutoff_class_for("H4") == "fast"
    assert manifest.cutoff_class_for("D1") == "daily"
    assert manifest.cutoff_class_for("W1") == "daily"
    assert manifest.cutoff_class_for("anything_else") == "slow"


def test_is_fresh_false_when_key_never_ingested():
    assert manifest.is_fresh("dukascopy", "GOLD", "M15") is False


def test_is_fresh_true_right_after_success():
    manifest.record_success("dukascopy", "GOLD", "M15", "2026-09-04T10:00:00", 500)
    assert manifest.is_fresh("dukascopy", "GOLD", "M15") is True


def test_is_fresh_false_once_past_the_fast_cutoff():
    manifest.record_success("dukascopy", "GOLD", "M15", "2026-09-04T10:00:00", 500)
    data = manifest._load()
    stale_time = datetime.now(timezone.utc) - timedelta(minutes=manifest._STALENESS_MINUTES["fast"] + 1)
    data["dukascopy:GOLD_M15"]["last_success_at"] = stale_time.isoformat()
    manifest._save(data)
    assert manifest.is_fresh("dukascopy", "GOLD", "M15") is False


def test_failed_attempt_never_overwrites_a_prior_success():
    manifest.record_success("dukascopy", "GOLD", "M15", "2026-09-04T10:00:00", 500)
    good_success_at = manifest.get_entry("dukascopy", "GOLD", "M15")["last_success_at"]

    manifest.record_failure("dukascopy", "GOLD", "M15", "dukascopy_python-Hang")

    entry = manifest.get_entry("dukascopy", "GOLD", "M15")
    assert entry["last_success_at"] == good_success_at
    assert entry["last_error"] == "dukascopy_python-Hang"
    # Der letzte GUTE Erfolg macht die Daten weiterhin gueltig, solange er selbst noch frisch genug ist --
    # ein einzelner Fehlversuch darf ein Bein nicht sofort lahmlegen, wenn der vorherige Stand noch gilt.
    assert manifest.is_fresh("dukascopy", "GOLD", "M15") is True


def test_record_failure_on_a_never_ingested_key_stays_stale():
    manifest.record_failure("dukascopy", "NEVER_SEEN", "M15", "leerer DataFrame")
    entry = manifest.get_entry("dukascopy", "NEVER_SEEN", "M15")
    assert entry["last_success_at"] is None
    assert manifest.is_fresh("dukascopy", "NEVER_SEEN", "M15") is False
