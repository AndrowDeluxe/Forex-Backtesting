"""Unit-Tests fuer research_lock (Overfitting-Sperre)."""
import pandas as pd
import pytest

from research_lock import Lock, LockError, config_hash, deflated_sharpe


@pytest.fixture
def lock(tmp_path):
    lk = Lock("test_strat", lock_dir=tmp_path)
    lk.register_split("2016-07-28", "2022-12-31", "2025-09-30", "2026-09-30")
    return lk


def _series():
    idx = pd.date_range("2016-08-01", "2026-09-30", freq="D", tz="America/New_York")
    return pd.Series(1.0, index=idx)


def test_split_cannot_be_moved(lock):
    lock.register_split("2016-07-28", "2022-12-31", "2025-09-30", "2026-09-30")  # identisch: ok
    with pytest.raises(LockError):
        lock.register_split("2016-07-28", "2023-12-31", "2025-09-30", "2026-09-30")


def test_split_must_be_ascending(tmp_path):
    with pytest.raises(LockError):
        Lock("x", lock_dir=tmp_path).register_split("2020-01-01", "2019-01-01", "2021-01-01")


def test_is_only_cuts_at_is_end(lock):
    s = lock.is_only(_series())
    assert s.index.max().date() == pd.Timestamp("2022-12-31").date()
    assert s.index.min().date() == pd.Timestamp("2016-08-01").date()


def test_no_unseal_without_freeze(lock):
    with pytest.raises(LockError):
        lock.unseal("oos", "abc")


def test_unseal_needs_matching_hash(lock):
    lock.freeze({"stop": 0.6})
    with pytest.raises(LockError):
        lock.unseal("oos", config_hash({"stop": 0.8}))


def test_freeze_is_immutable(lock):
    lock.freeze({"stop": 0.6})
    assert lock.freeze({"stop": 0.6}) == config_hash({"stop": 0.6})
    with pytest.raises(LockError):
        lock.freeze({"stop": 0.8})


def test_no_trials_after_freeze(lock):
    lock.log_trials(10)
    lock.freeze({"stop": 0.6})
    with pytest.raises(LockError):
        lock.log_trials(1)
    assert lock.trials == 10


def test_stages_open_once_and_in_order(lock):
    h = lock.freeze({"stop": 0.6})
    with pytest.raises(LockError):
        lock.unseal("tresor", h)                     # Tresor erst nach OOS
    assert lock.unseal("oos", h) == ("2023-01-01", "2025-09-30")
    with pytest.raises(LockError):
        lock.unseal("oos", h)                        # zweites Mal gesperrt
    assert lock.unseal("tresor", h) == ("2025-10-01", "2026-09-30")
    with pytest.raises(LockError):
        lock.unseal("tresor", h)


def test_stage_slice_requires_unsealed(lock):
    with pytest.raises(LockError):
        lock.stage_slice(_series(), "oos")
    h = lock.freeze({"stop": 0.6})
    lock.unseal("oos", h)
    s = lock.stage_slice(_series(), "oos")
    assert s.index.min().date() == pd.Timestamp("2023-01-01").date()
    assert s.index.max().date() == pd.Timestamp("2025-09-30").date()


def test_deflated_sharpe_drops_with_trials():
    one = deflated_sharpe(0.1, 500, 1)
    many = deflated_sharpe(0.1, 500, 10_000)
    assert one > 0.95 and many < one


def test_forward_stays_sealed_until_rule_met(lock):
    h = lock.freeze({"stop": 0.6})
    lock.register_forward("2026-10-05", "2027-03-31", 100)
    with pytest.raises(LockError):
        lock.unseal("forward", h, n_forward_trades=10, today="2026-12-01")   # vor OOS + zu frueh
    lock.unseal("oos", h)
    with pytest.raises(LockError):
        lock.unseal("forward", h, n_forward_trades=99, today="2027-03-30")
    assert lock.unseal("forward", h, n_forward_trades=100, today="2026-12-01") == ("2026-10-05", None)
    with pytest.raises(LockError):
        lock.unseal("forward", h, n_forward_trades=500, today="2027-06-01")   # nur einmal


def test_forward_rule_is_immutable(lock):
    lock.register_forward("2026-10-05", "2027-03-31", 100)
    with pytest.raises(LockError):
        lock.register_forward("2026-10-05", "2027-01-31", 50)


def test_blind_stage_before_is(lock):
    with pytest.raises(LockError):
        lock.register_blind("2010-01-01", "2016-12-31")          # ragt ins IS
    lock.register_blind("2010-01-01", "2015-12-31")
    with pytest.raises(LockError):
        lock.register_blind("2011-01-01", "2015-12-31")          # unveraenderlich
    with pytest.raises(LockError):
        lock.unseal("blind", "abc")                              # erst freeze
    h = lock.freeze({"stop": 0.6})
    idx = pd.date_range("2010-01-01", "2026-09-30", freq="D", tz="America/New_York")
    with pytest.raises(LockError):
        lock.stage_slice(pd.Series(1.0, index=idx), "blind")
    assert lock.unseal("blind", h) == ("2010-01-01", "2015-12-31")   # ohne OOS moeglich
    s = lock.stage_slice(pd.Series(1.0, index=idx), "blind")
    assert s.index.max().date() == pd.Timestamp("2015-12-31").date()
    assert lock.is_only(pd.Series(1.0, index=idx)).index.min().date() == pd.Timestamp("2016-07-28").date()
    with pytest.raises(LockError):
        lock.unseal("blind", h)                                  # nur einmal


def test_blind_not_after_freeze(lock):
    lock.freeze({"stop": 0.6})
    with pytest.raises(LockError):
        lock.register_blind("2010-01-01", "2015-12-31")
