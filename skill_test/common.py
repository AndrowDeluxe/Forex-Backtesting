"""Gemeinsame Daten fuer den Skill-Test ORB + CTNL (Plan 28.10.2026).

Trades: TTP-Simulation der Live-Konfiguration. Nur IS laut research_lock-Sperren
orb_skill_filter_20261028 / ctnl_skill_filter_20261028 -- OOS ist dort gesperrt.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research_lock import Lock  # noqa: E402

SKILLS = Path.home() / ".claude" / "skills"
RESULTS = ROOT / "skill_test" / "results"
RISK_PCT = 1.0

STRATEGIES = {
    "orb": {"lock": "orb_skill_filter_20261028", "legs": ["orb_sp500", "orb_nasdaq", "orb_us30"]},
    "ctnl": {"lock": "ctnl_skill_filter_20261028", "legs": ["ctnl_reversal"]},
}


def lock(strategy: str) -> Lock:
    return Lock(STRATEGIES[strategy]["lock"])


def all_trades() -> pd.DataFrame:
    t = pd.read_csv(ROOT / "portfolio_construction/results/live_trades_ttp_2019_2026.csv")
    t["entry_time"] = pd.to_datetime(t["entry_time"])
    t["exit_time"] = pd.to_datetime(t["exit_time"])
    t["entry_date"] = t["entry_time"].dt.normalize()
    return t


def is_trades(strategy: str) -> pd.DataFrame:
    t = all_trades()
    t = t[t.leg.isin(STRATEGIES[strategy]["legs"])].set_index("entry_time", drop=False).sort_index()
    return lock(strategy).is_only(t).reset_index(drop=True)


def stats(r: pd.Series) -> dict:
    """Kennzahlen einer R-Reihe (chronologisch), Risiko RISK_PCT je Trade, einfach summiert."""
    r = pd.Series(r, dtype=float)
    if r.empty:
        return {"n": 0}
    eq = (r * RISK_PCT).cumsum()
    dd = (eq - eq.cummax()).min()
    wins, losses = r[r > 0], r[r < 0]
    pf = wins.sum() / -losses.sum() if len(losses) else np.inf
    return {
        "n": int(len(r)),
        "sum_r": round(float(r.sum()), 2),
        "avg_r": round(float(r.mean()), 4),
        "win_rate": round(100 * len(wins) / len(r), 1),
        "pf": round(float(pf), 3),
        "sharpe_trade": round(float(r.mean() / r.std(ddof=1)), 4) if len(r) > 1 else np.nan,
        "max_dd_pct": round(float(-dd), 2),
        "avg_win_pct": round(float(wins.mean() * RISK_PCT), 3) if len(wins) else 0.0,
        "avg_loss_pct": round(float(-losses.mean() * RISK_PCT), 3) if len(losses) else 0.0,
    }
