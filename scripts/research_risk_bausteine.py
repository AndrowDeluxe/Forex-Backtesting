"""Risk-Management-Bausteine auf allen Edges (Nutzerauftrag 2026-11-20).

Anlass: Prosper-Kurs Lektion 4, Notiz knowledge/areas/risk-management-bausteine.md.
Prueft je Bein (Live-Beine, H4-Spike des Signal-Hubs, eingefrorener Daily-C2):
  D  Diagnose: Oe R nach 1/2/3 geschlossenen Verlusten in Folge vs. alle Trades
  P  Pause nach N Verlusten in Folge: die naechsten K=3 Signale auslassen
  H  Risiko halbieren, solange >= N Verluste in Folge (zurueck nach Gewinn)
  T  Tageslimit je Bein: nach realisiert <= -L R am Tag keine neuen Einstiege
  TP Tageslimit auf dem TTP-Konto (Live-Risiken je Bein), nur realisierte Verluste
Serien zaehlen NUR Trades mit exit_time <= entry_time (Daily: exit < entry), und nur
tatsaechlich genommene Trades. Vergleichsmass gegen "pauschal kleineres Risiko":
Rendite/DD = Summe R / |Max DD in R| (skaleninvariant).
Split: IS 2016-2022, OOS 2023-01-01..2026-05-19, Tresor ab 2026-05-20 bleibt draussen.

Aufruf: python scripts/research_risk_bausteine.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO)]
from research_lock import Lock  # noqa: E402

LIVE = REPO / "portfolio_construction" / "results" / "live_2016"
OUT = REPO / "portfolio_construction" / "results" / "risk_bausteine"
IS_END, OOS_END = pd.Timestamp("2023-01-01"), pd.Timestamp("2026-05-20")
TTP_RISK = {"gold_asb": 0.0060, "cls_practical": 0.0015, "trend_pullback": 0.0010, "ctnl_reversal": 0.0010,
            "ou_modell": 0.0005, "orb_sp500": 0.00075, "orb_nasdaq": 0.0010}


# ------------------------------------------------------------------ Daten
def load_sets() -> dict[str, pd.DataFrame]:
    sets = {}
    ttp = pd.read_parquet(LIVE / "ttp_trades.parquet")
    for leg, g in ttp.groupby("leg"):
        sets[leg] = g[["entry_time", "exit_time", "r"]].assign(daily=False)
    ek = pd.read_parquet(LIVE / "ek_trades.parquet")
    for leg in ("gold_silver", "btc_ema_cross"):
        sets[leg] = ek.loc[ek["leg"] == leg, ["entry_time", "exit_time", "r"]].assign(daily=False)

    from htf_daily_trade.h4_v4 import apply_busy, masks
    h = pd.read_parquet(REPO / "htf_daily_trade" / "h4_v4_signale.parquet")
    mk = masks(h)
    h = apply_busy(h[mk["Q"] & mk["A"]], "R3_BE1")
    h = h[np.isfinite(h["r_R3_BE1"])]
    sets["h4_spike"] = pd.DataFrame({"entry_time": h["einstieg"].dt.tz_localize(None),
                                     "exit_time": h["t_R3_BE1"].dt.tz_localize(None),
                                     "r": h["r_R3_BE1"], "daily": False})

    c = pd.read_csv(REPO / "htf_daily_trade" / "c2_kandidat_trades.csv", parse_dates=["einstieg", "ausstieg"])
    sets["daily_c2"] = pd.DataFrame({"entry_time": c["einstieg"], "exit_time": c["ausstieg"], "r": c["r_TTP"],
                                     "daily": True})
    out = {}
    for k, d in sets.items():
        d = d.dropna(subset=["r"]).sort_values("entry_time").reset_index(drop=True)
        out[k] = d[d["entry_time"] < OOS_END].reset_index(drop=True)
    return out


# ------------------------------------------------------------------ Simulation
def _closed(taken: list, t_entry, daily: bool, after=None) -> list:
    """Genommene Trades, die zum Einstieg schon geschlossen sind, nach exit_time sortiert."""
    c = [x for x in taken if (x[0] < t_entry if daily else x[0] <= t_entry) and (after is None or x[0] > after)]
    return sorted(c, key=lambda x: x[0])


def _streak(closed: list) -> int:
    n = 0
    for _, r in reversed(closed):
        if r < 0:
            n += 1
        else:
            break
    return n


def run(d: pd.DataFrame, rule: str | None = None, n: int = 2, k: int = 3, lim: float = 1.0) -> pd.Series:
    """Rueckgabe: R je Trade nach Regel (NaN = ausgelassen)."""
    daily = bool(d["daily"].iat[0])
    res = np.full(len(d), np.nan)
    taken: list = []
    skip_left, reset_at = 0, None
    for i, row in enumerate(d.itertuples()):
        et, xt, r = row.entry_time, row.exit_time, row.r
        size = 1.0
        if rule == "P":
            if skip_left > 0:
                skip_left -= 1
                if skip_left == 0:
                    reset_at = et  # Serie nach der Pause neu zaehlen
                continue
            if _streak(_closed(taken, et, daily, reset_at)) >= n:
                skip_left = k - 1
                if skip_left == 0:
                    reset_at = et
                continue
        elif rule == "H":
            if _streak(_closed(taken, et, daily)) >= n:
                size = 0.5
        elif rule == "T":
            day = et.normalize()
            real = sum(x[1] for x in taken if day <= x[0] <= et)
            if real <= -lim:
                continue
        res[i] = r * size
        taken.append((xt, r * size))
    return pd.Series(res, index=d.index)


def metrics(r: pd.Series, et: pd.Series) -> dict:
    r = r.dropna()
    if r.empty:
        return {"n": 0}
    eq = r.cumsum()
    dd = float((eq - eq.cummax().clip(lower=0)).min())
    yrs = max((et.loc[r.index].max() - et.loc[r.index].min()).days / 365.25, 0.5)
    sd = r.std()
    return {"n": len(r), "sumR": round(r.sum(), 1), "avgR": round(r.mean(), 3), "maxDD_R": round(dd, 1),
            "ret_dd": round(r.sum() / abs(dd), 2) if dd < 0 else np.nan,
            "sharpe": round(r.mean() / sd * np.sqrt(len(r) / yrs), 2) if sd > 0 else np.nan}


def diagnose(d: pd.DataFrame) -> list[dict]:
    daily = bool(d["daily"].iat[0])
    taken = list(zip(d["exit_time"], d["r"]))
    st = np.array([_streak(_closed(taken, et, daily)) for et in d["entry_time"]])
    out = []
    for per, m in (("IS", d["entry_time"] < IS_END), ("OOS", d["entry_time"] >= IS_END)):
        row = {"periode": per, "alle_n": int(m.sum()), "alle_R": round(d.loc[m, "r"].mean(), 3)}
        for s in (1, 2, 3):
            mm = m & (st >= s)
            row[f"nach{s}V_n"] = int(mm.sum())
            row[f"nach{s}V_R"] = round(d.loc[mm, "r"].mean(), 3) if mm.any() else np.nan
        out.append(row)
    return out


VARIANTS = [("Basis", None, {}), ("P2", "P", {"n": 2}), ("P3", "P", {"n": 3}), ("H2", "H", {"n": 2}),
            ("H3", "H", {"n": 3}), ("T1R", "T", {"lim": 1.0}), ("T2R", "T", {"lim": 2.0})]


def ttp_daily_limit(sets: dict, lim_pct: float | None) -> pd.Series:
    """TTP-Konto: PnL in % = R x Live-Risiko; neue Einstiege gesperrt, sobald realisiert <= -lim am Tag."""
    rows = [d.assign(leg=leg) for leg, d in sets.items() if leg in TTP_RISK]
    t = pd.concat(rows).sort_values("entry_time").reset_index(drop=True)
    t["pct"] = t["r"] * t["leg"].map(TTP_RISK) * 100
    res, taken = np.full(len(t), np.nan), []
    for i, row in enumerate(t.itertuples()):
        if lim_pct is not None:
            day = row.entry_time.normalize()
            if sum(p for x, p in taken if day <= x <= row.entry_time) <= -lim_pct:
                continue
        res[i] = row.pct
        taken.append((row.exit_time, row.pct))
    t["res"] = res
    return t


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    lock = Lock("risk_bausteine_20261120")
    try:
        lock.register_split("2016-01-01", "2022-12-31", "2026-05-19", "2026-11-20")
    except Exception as e:  # schon registriert
        print("Lock:", e)
    sets = load_sets()

    diag, var = [], []
    for leg, d in sets.items():
        for row in diagnose(d):
            diag.append({"bein": leg, **row})
        for name, rule, kw in VARIANTS:
            r = run(d, rule, **kw)
            for per, m in (("IS", d["entry_time"] < IS_END), ("OOS", d["entry_time"] >= IS_END)):
                var.append({"bein": leg, "variante": name, "periode": per, **metrics(r[m], d["entry_time"])})
    lock.log_trials(len(sets) * (len(VARIANTS) - 1) + 3, "P2/P3/H2/H3/T1R/T2R je Bein + TTP-Tageslimit 1/2/3 %")

    diag, var = pd.DataFrame(diag), pd.DataFrame(var)
    diag.to_csv(OUT / "diagnose.csv", index=False)
    var.to_csv(OUT / "varianten.csv", index=False)
    pd.set_option("display.width", 220)
    print("\n=== Diagnose: Oe R nach Verlustserie ===\n", diag.to_string(index=False))
    piv = var.pivot_table(index=["bein", "periode"], columns="variante", values="ret_dd")[[v[0] for v in VARIANTS]]
    print("\n=== Rendite/DD (hoeher = besser als pauschal weniger Risiko) ===\n", piv.to_string())
    piv2 = var.pivot_table(index=["bein", "periode"], columns="variante", values="sumR")[[v[0] for v in VARIANTS]]
    print("\n=== Summe R ===\n", piv2.to_string())

    rows = []
    for lim in (None, 1.0, 2.0, 3.0):
        t = ttp_daily_limit(sets, lim)
        for per, m in (("IS", t["entry_time"] < IS_END), ("OOS", t["entry_time"] >= IS_END)):
            s = t.loc[m, "res"].dropna()
            daily_pnl = t.loc[m].dropna(subset=["res"]).groupby(t["exit_time"].dt.normalize())["res"].sum()
            eq = s.cumsum()
            dd = float((eq - eq.cummax().clip(lower=0)).min())
            rows.append({"limit_%": lim or "aus", "periode": per, "trades": len(s), "summe_%": round(s.sum(), 1),
                         "maxDD_%": round(dd, 2), "ret_dd": round(s.sum() / abs(dd), 2),
                         "schlechtester_Tag_%": round(daily_pnl.min(), 2),
                         "Tage<=-3%": int((daily_pnl <= -3).sum()), "gesperrt": int(m.sum() - len(s))})
    tp = pd.DataFrame(rows)
    tp.to_csv(OUT / "ttp_tageslimit.csv", index=False)
    print("\n=== TTP-Konto Tageslimit (realisiert) ===\n", tp.to_string(index=False))


if __name__ == "__main__":
    main()
