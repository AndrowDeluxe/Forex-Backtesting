"""Baut Eingaben fuer den residual-edge-analyzer-Skill (je Live-Bein CSV + Config).

Strategie-Reihe: R x 1 % Risiko, nach Exit-Datum auf Handelstage des Basiswerts summiert.
Baselines und Fenster sind vorab festgelegt (Plan 28.10.2026), nicht nach Ergebnis gewaehlt.
Nur Lesezugriffe auf Quelldaten; Ausgabe nach portfolio_construction/results/residual_edge/.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "portfolio_construction" / "results" / "residual_edge"
ANALYZER = Path.home() / ".claude/skills/residual-edge-analyzer/scripts/analyze_residual_edge.py"
RISK = 0.01

LEGS = {
    # leg: (baseline, start, end, scope, quelle)
    "orb_sp500": ("SPX", "2023-01-01", "2026-09-30", "out_of_sample", "ttp"),
    "orb_nasdaq": ("NDX", "2023-01-01", "2026-09-30", "out_of_sample", "ttp"),
    "orb_us30": ("DJI", "2023-01-01", "2026-09-30", "out_of_sample", "ttp"),
    "gold_asb": ("Gold", "2023-01-01", "2026-09-30", "out_of_sample", "ttp"),
    "cls_practical": ("EURUSD", "2022-06-01", "2026-09-30", "out_of_sample", "ttp"),
    "gold_silver": ("Gold", "2023-01-01", "2026-09-30", "out_of_sample", "ampel"),
    "trend_pullback": ("Gold", "2024-07-01", "2026-08-14", "out_of_sample", "ttp"),
    "ou_modell": ("SPX", "2023-01-01", "2026-09-09", "out_of_sample", "ttp"),
    "ctnl_reversal": ("Gold", "2024-08-01", "2026-09-30", "in_sample", "ttp"),
}
GOLD_LEGS = {k for k, v in LEGS.items() if v[0] == "Gold"}


def load_prices() -> pd.DataFrame:
    d = ROOT / "data_cache" / "macro_regime"
    px = pd.read_parquet(d / "yf_prices.parquet").join(pd.read_parquet(d / "yf_prices_extra.parquet"), how="outer")
    eur = pd.read_parquet(ROOT / "data_cache/combined/EURUSD_D1_2003-01-01_2026-10-10.parquet")["Close"]
    eur.index = eur.index.tz_localize(None).normalize()
    px.index = pd.to_datetime(px.index).normalize()
    return px.join(eur.rename("EURUSD"), how="outer")


def load_trades() -> pd.DataFrame:
    res = ROOT / "portfolio_construction" / "results"
    ttp = pd.read_csv(res / "live_trades_ttp_2019_2026.csv").assign(quelle="ttp")
    amp = pd.read_csv(res / "live_trades_tickmill_ampel.csv").assign(quelle="ampel")
    t = pd.concat([ttp, amp], ignore_index=True)
    t["exit_date"] = pd.to_datetime(t["exit_time"]).dt.normalize()
    return t


def baseline_frame(px: pd.DataFrame, col: str, with_silver: bool) -> pd.DataFrame:
    cols = [col, "Silver"] if with_silver else [col]
    p = px[cols].dropna()
    f = pd.DataFrame(index=p.index)
    f["base_return"] = p[col].pct_change()
    trend = np.sign(p[col] / p[col].shift(252) - 1).shift(1)
    f["trend_return"] = trend * f["base_return"]
    if with_silver:
        f["silver_return"] = p["Silver"].pct_change()
    return f.dropna()


def build_leg(leg, spec, px, trades, regimes):
    base, start, end, scope, quelle = spec
    f = baseline_frame(px, base, leg in GOLD_LEGS).loc[start:end]
    t = trades[(trades.leg == leg) & (trades.quelle == quelle)]
    t = t[(t.exit_date >= start) & (t.exit_date <= end)]
    # Exit am Wochenende/Feiertag -> naechster Handelstag des Basiswerts
    pos = f.index.searchsorted(t.exit_date.values)
    pos = np.clip(pos, 0, len(f) - 1)
    daily = pd.Series(t["r"].values * RISK, index=f.index[pos]).groupby(level=0).sum()
    f.insert(0, "strategy_return", daily.reindex(f.index).fillna(0.0))
    f["regime"] = regimes.reindex(f.index, method="ffill").fillna("unbekannt")
    f.index.name = "date"
    df = f.reset_index()
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    csv = OUT / f"{leg}_returns.csv"
    df.to_csv(csv, index=False)

    sens = []
    # Konstantes Trendvorzeichen im Fenster -> Trendfaktor == Basiswert (rangdefizient), entfaellt
    trend_const = bool(np.isclose(f["trend_return"], f["base_return"]).all()
                       or np.isclose(f["trend_return"], -f["base_return"]).all())
    if not trend_const:
        sens.append({"name": "base_plus_trend", "baseline_columns": ["base_return", "trend_return"]})
    if leg in GOLD_LEGS:
        sens.append({"name": "gold_plus_silver", "baseline_columns": ["base_return", "silver_return"]})
    cfg = {
        "schema_version": "1.0",
        "date_column": "date",
        "strategy_column": "strategy_return",
        "return_unit": "decimal",
        "frequency": "daily",
        "primary_model": {"name": f"hold_{base}", "baseline_columns": ["base_return"]},
        "sensitivity_models": sens,
        "regime_columns": ["regime"],
        "rolling_window": 63,
        "minimum_observations": 60,
        "minimum_regime_observations": 20,
        "minimum_rolling_windows": 12,
        "hac_lags": "auto",
        "include_series": False,
        "data_declarations": {
            "baseline_selection": "predeclared",
            "strategy_return_basis": "net",
            "baseline_return_basis": "gross",
            "analysis_scope": scope,
            "universe_data": "not_applicable",
        },
    }
    cfg_path = OUT / f"{leg}_config.json"
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return csv, cfg_path, len(t), float(t["r"].sum()), trend_const


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    px, trades = load_prices(), load_trades()
    lab = pd.read_parquet(ROOT / "fusion_lab/data/macro_regime/labels.parquet")["joint"]
    lab.index = pd.to_datetime(lab.index).normalize()
    rows = []
    for leg, spec in LEGS.items():
        csv, cfg, n, sum_r, trend_const = build_leg(leg, spec, px, trades, lab)
        stem = OUT / leg
        subprocess.run(
            [sys.executable, str(ANALYZER), "--input", str(csv), "--config", str(cfg),
             "--output-json", f"{stem}_report.json", "--output-markdown", f"{stem}_report.md"],
            check=True, cwd=OUT, capture_output=True, text=True,
        )
        rows.append({"leg": leg, "trades": n, "sum_r": round(sum_r, 1), "trend_entfaellt": trend_const})
    pd.DataFrame(rows).to_csv(OUT / "inputs_summary.csv", index=False)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
