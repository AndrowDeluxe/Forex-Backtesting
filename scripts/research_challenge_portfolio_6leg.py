"""Challenge-Portfolio-Update (2026-08-27): prueft, ob NY-Open ORB als 6. Bein
zum bestehenden 5-Bein-FK-Portfolio (Gold ASB, CLS Practical, OU-Modell,
Trend Pullback, CTNL Edge -- siehe portfolio_construction/results/
ctnl_fk_extension.json, dort "5 Beine, CTNL konservativ" als empfohlener
Kandidat) die Bruchwahrscheinlichkeit/Geschwindigkeit auf den beiden Ziel-
Regelwerken TTP und IQ Markets ("I Capital" im Nutzer-Wortlaut, identische
Zahlen) verbessert oder verschlechtert. ORB war bisher bewusst ausgeschlossen
("keine Evidenz, dass TTP/IQ Markets die Instrumente anbieten") -- auf
Nutzerwunsch jetzt trotzdem aufgenommen.

Kombinationsmethodik 1:1 aus app_pages/portfolio_construction.py::
combine_rebalanced() uebernommen (taeglich rebalancierte gewichtete Returns,
konstante Gewichte, gemeinsames Fenster). OU-Modell nutzt hier bewusst den
Referenz-Risiko-Ersatz (volles Universum, 1% Risiko, ou_modell.csv) statt der
echten TTP-58-Ticker-Teilmenge (ou_modell_fk_r150.csv endet 2024-12-31, zu
kurz fuer ein gemeinsames Fenster mit CTNL Edge ab 2024-08) -- derselbe,
bereits in ctnl_fk_extension.json dokumentierte Kompromiss.

ORB-Bein bewusst NICHT aus legs/orb_strategy_r100.csv geladen (Stand 2026-08-19,
aus der ALTEN, mittlerweile verworfenen orb_strategy/-Variante -- siehe
knowledge/projects/ny-open-orb-sp500.md: "alte orb_strategy/ discarded").
Stattdessen frisch aus den drei per-Instrument-Trade-Listen gebaut, die die
FK-Instant-Funding-Integration am 2026-08-27 aus dem AKTUELLEN ny_open_orb/-
Modul erzeugt hat (legs/trades_ny_orb_{sp500,us30,nasdaq}.csv, Config 1:1 aus
app_pages/ny_open_orb_portfolio.py: SP500/US30 long-only+EMA-neutral, NASDAQ
long+short ohne Mittwoch, ATR-Stop 0.6x, Target 4R) -- exakt dieselbe
1/3-Instrumente-Gleichgewichtung + 1,0% kombiniertes Risiko/Trade wie in
fk_instant_funding/paper_bot.py::_scan_orb()/ORB_COMBINED_RISK_PCT.

p_breach/p_target/median_days-Scoring ist neu geschrieben (kein wieder-
verwendbares Vorbild im Repo gefunden), folgt aber exakt der Definition, die
in fk_risk_optimized.json/ctnl_fk_extension.json bereits verwendet wird:
pro Block-Bootstrap-Pfad (block_size=20, n_sims=3000) chronologisch first-
touch klassifizieren -- Regelbruch (Tageslimit ODER Gesamt-Drawdown) vs.
Zielerreichung vs. keins von beiden bis Pfadende."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_DIR = Path(__file__).resolve().parents[1]
OU_DIR = REPO_DIR / "ou_paper_backtest"
sys.path.insert(0, str(OU_DIR))

from monte_carlo import block_bootstrap_paths  # noqa: E402

LEGS_DIR = REPO_DIR / "portfolio_construction" / "results" / "legs"
RESULTS_DIR = REPO_DIR / "portfolio_construction" / "results"

TRADING_DAYS_PER_YEAR = 252
INITIAL_EQUITY = 100_000.0

RULES = {
    "ttp": {"daily_loss_cap": 0.03, "total_dd_cap": 0.07, "target_gain": 0.10},
    "iqmarkets": {"daily_loss_cap": None, "total_dd_cap": 0.06, "target_gain": 0.08},
}

LEG_FILES = {
    "gold_asb": "gold_asb_r200",
    "cls_practical": "cls_practical_r150",
    "ou_modell": "ou_modell",  # Referenz-Risiko-Ersatz, siehe Docstring
    "trend_pullback": "trend_pullback_r050",
    "ctnl_edge": "ctnl_edge_fk",
}
LEG_LABELS = {
    "gold_asb": "Gold ASB", "cls_practical": "CLS Practical",
    "ou_modell": "OU-Modell (Referenz-Risiko-Ersatz)", "trend_pullback": "Trend Pullback",
    "ctnl_edge": "CTNL Edge (Gold SMC)", "orb_portfolio": "NY-Open ORB Portfolio (SP500+US30+NASDAQ)",
}
LEGS_5 = ("gold_asb", "cls_practical", "ou_modell", "trend_pullback", "ctnl_edge")
LEGS_6 = LEGS_5 + ("orb_portfolio",)

ORB_INSTRUMENTS = ["sp500", "us30", "nasdaq"]
ORB_COMBINED_RISK_PCT = 0.01  # matches fk_instant_funding/paper_bot.py::ORB_COMBINED_RISK_PCT


def _utc_naive(s: pd.Series) -> pd.Series:
    s = pd.to_datetime(s, utc=True)
    return s.dt.tz_localize(None)


def build_orb_equity(combined_risk_pct: float = ORB_COMBINED_RISK_PCT) -> pd.Series:
    """Frisch aus den drei aktuellen per-Instrument-Trade-Listen gebaut (siehe
    Docstring oben) statt aus der veralteten legs/orb_strategy_r100.csv --
    gleichgewichtet 1/3 je Instrument, sequenziell nach exit_time kompoundiert,
    identische Konvention wie fk_instant_funding/paper_bot.py::compute_shared_equity."""
    per_instrument_risk = combined_risk_pct / len(ORB_INSTRUMENTS)
    frames = []
    for inst in ORB_INSTRUMENTS:
        df = pd.read_csv(LEGS_DIR / f"trades_ny_orb_{inst}.csv")
        df["exit_time"] = _utc_naive(df["exit_time"])
        df = df.dropna(subset=["r_multiple", "exit_time"])
        frames.append(df[["exit_time", "r_multiple"]])
    trades = pd.concat(frames, ignore_index=True).sort_values("exit_time").reset_index(drop=True)

    equity = INITIAL_EQUITY
    rows = []
    for _, t in trades.iterrows():
        pnl = per_instrument_risk * equity * t["r_multiple"]
        equity += pnl
        rows.append({"date": t["exit_time"].normalize(), "equity": equity})
    curve = pd.DataFrame(rows).groupby("date")["equity"].last()
    return curve


def load_leg(key: str) -> pd.Series:
    if key == "orb_portfolio":
        return build_orb_equity()
    df = pd.read_csv(LEGS_DIR / f"{LEG_FILES[key]}.csv", parse_dates=["date"]).drop_duplicates("date").set_index("date").sort_index()
    return df["equity"].astype(float)


def combine_rebalanced(leg_keys: tuple[str, ...]) -> tuple[pd.Series, pd.DataFrame]:
    """Matches app_pages/portfolio_construction.py::combine_rebalanced() exactly
    (equal weight here, 1/n_legs each) -- daily-rebalanced weighted returns over
    the common window, ffilled across calendar days (same convention every prior
    portfolio JSON in this repo already used, kept for comparability)."""
    sers = {k: load_leg(k) for k in leg_keys}
    common_start = max(s.index.min() for s in sers.values())
    common_end = min(s.index.max() for s in sers.values())
    idx = pd.date_range(common_start, common_end, freq="D")
    rets = pd.DataFrame({k: sers[k].reindex(idx).ffill().pct_change() for k in leg_keys}).dropna()
    w = np.full(len(leg_keys), 1.0 / len(leg_keys))
    port_daily = rets.values @ w
    equity = pd.Series(INITIAL_EQUITY * (1 + port_daily).cumprod(), index=rets.index)
    return equity, rets


def historical_metrics(equity: pd.Series) -> dict:
    daily_ret = equity.pct_change().dropna()
    years = len(daily_ret) / TRADING_DAYS_PER_YEAR
    total_return = equity.iloc[-1] / equity.iloc[0] - 1.0
    cagr = (1 + total_return) ** (1 / years) - 1.0 if years > 0 else np.nan
    ann_vol = daily_ret.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    sharpe = (cagr / ann_vol) if ann_vol else np.nan
    running_max = equity.cummax()
    max_dd = (equity / running_max - 1.0).min()
    calmar = (cagr / abs(max_dd)) if max_dd else np.nan
    return {
        "final_equity": float(equity.iloc[-1]), "cagr_pct": float(cagr * 100),
        "sharpe": float(sharpe), "max_dd_pct": float(max_dd * 100), "calmar": float(calmar),
    }


def classify_paths(daily_returns: pd.Series, rules: dict, block_size: int = 20, n_sims: int = 3000, seed: int = 42) -> dict:
    paths = block_bootstrap_paths(daily_returns, block_size=block_size, n_sims=n_sims, seed=seed)
    n_days = paths.shape[1]
    equity = INITIAL_EQUITY * np.cumprod(1.0 + paths, axis=1)
    equity_with_start = np.hstack([np.full((n_sims, 1), INITIAL_EQUITY), equity])
    running_max = np.maximum.accumulate(equity_with_start, axis=1)
    drawdown = equity_with_start / running_max - 1.0

    target_equity = INITIAL_EQUITY * (1 + rules["target_gain"])
    target_arr = equity_with_start[:, 1:] >= target_equity
    dd_breach_arr = drawdown[:, 1:] <= -rules["total_dd_cap"]
    if rules["daily_loss_cap"] is not None:
        daily_breach_arr = paths <= -rules["daily_loss_cap"]
        breach_arr = daily_breach_arr | dd_breach_arr
    else:
        breach_arr = dd_breach_arr

    target_happened = target_arr.any(axis=1)
    breach_happened = breach_arr.any(axis=1)
    first_target_idx = np.where(target_happened, target_arr.argmax(axis=1), n_days)
    first_breach_idx = np.where(breach_happened, breach_arr.argmax(axis=1), n_days)

    outcome_target = target_happened & (~breach_happened | (first_target_idx < first_breach_idx))
    outcome_breach = breach_happened & (~target_happened | (first_breach_idx <= first_target_idx))
    outcome_neither = ~outcome_target & ~outcome_breach

    days_to_target = first_target_idx[outcome_target] + 1
    return {
        "p_target": float(outcome_target.mean()), "p_breach": float(outcome_breach.mean()),
        "p_neither": float(outcome_neither.mean()),
        "median_days_to_target": float(np.median(days_to_target)) if len(days_to_target) else None,
        "n_sims": n_sims, "block_size": block_size, "path_length_days": n_days,
    }


def run_combo(leg_keys: tuple[str, ...]) -> dict:
    equity, rets = combine_rebalanced(leg_keys)
    daily_ret = equity.pct_change().dropna()
    hist = historical_metrics(equity)
    mc = {rule_key: classify_paths(daily_ret, rules) for rule_key, rules in RULES.items()}
    weekly = equity.resample("W-FRI").last().dropna()
    return {
        "legs": list(leg_keys), "common_window": {"start": str(equity.index.min().date()), "end": str(equity.index.max().date())},
        "historical_metrics": hist, "monte_carlo": mc,
        "weekly_curve": [[str(d.date()), float(v)] for d, v in weekly.items()],
    }, rets


def main():
    print("Lade 5-Bein-Baseline (ohne ORB) ...")
    result_5leg, rets_5 = run_combo(LEGS_5)
    print(f"  Fenster {result_5leg['common_window']}, CAGR {result_5leg['historical_metrics']['cagr_pct']:.1f}%, "
          f"MaxDD {result_5leg['historical_metrics']['max_dd_pct']:.1f}%")
    for rk, m in result_5leg["monte_carlo"].items():
        print(f"  [{rk}] p_target={m['p_target']*100:.1f}% p_breach={m['p_breach']*100:.1f}% "
              f"p_neither={m['p_neither']*100:.1f}% median_days={m['median_days_to_target']}")

    print("\nLade 6-Bein-Kombi (mit ORB) ...")
    result_6leg, rets_6 = run_combo(LEGS_6)
    print(f"  Fenster {result_6leg['common_window']}, CAGR {result_6leg['historical_metrics']['cagr_pct']:.1f}%, "
          f"MaxDD {result_6leg['historical_metrics']['max_dd_pct']:.1f}%")
    for rk, m in result_6leg["monte_carlo"].items():
        print(f"  [{rk}] p_target={m['p_target']*100:.1f}% p_breach={m['p_breach']*100:.1f}% "
              f"p_neither={m['p_neither']*100:.1f}% median_days={m['median_days_to_target']}")

    orb_corr = {k: float(rets_6["orb_portfolio"].corr(rets_6[k])) for k in LEGS_5}
    print("\nKorrelation ORB vs. bestehende 5 Beine (gemeinsames 6-Bein-Fenster):")
    for k, v in orb_corr.items():
        print(f"  {LEG_LABELS[k]}: {v:+.3f}")

    out = {
        "leg_labels": LEG_LABELS,
        "baseline_5leg": result_5leg,
        "with_orb_6leg": result_6leg,
        "orb_vs_existing_correlation": orb_corr,
    }
    out_path = RESULTS_DIR / "challenge_portfolio_6leg.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved {out_path}")


if __name__ == "__main__":
    main()
