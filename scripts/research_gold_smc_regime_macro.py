"""Regime-Untersuchung Runde 2 (chat 2026-08-20): weitere Makrofaktoren -
VIX, DXY (Dollar-Index-Proxy), Oel (WTI) - ueber FRED, gleiches Muster wie
bond_yield_indicator/fred.py (CSV-Endpoint, kein API-Key). "Krieg" und
"Trump-Regime" haben keine sauber quantifizierbare taegliche Datenquelle
im Repo - dazu unten eine narrative Einordnung statt eines erfundenen
Proxys. Gold-ETF-Inflows (World Gold Council) sind ebenfalls nicht ueber
FRED verfuegbar - hier explizit als Datenluecke vermerkt, nicht stillschweigend
ausgelassen.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from gold_smc_htf_ltf.continuation import run_pipeline as run_continuation
from gold_smc_htf_ltf.data import fetch_gold_d1, fetch_gold_h1, fetch_gold_h4, fetch_gold_m5, fetch_gold_m15
from gold_smc_htf_ltf.reversal_cascade import run_pipeline as run_reversal
from strategy.backtest import BacktestConfig, simulate_trades
from strategy.metrics import summarize

pd.set_option("display.width", 160)

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
FULL_START, FULL_END = "2016-01-01", "2026-08-01"
SPREAD_BPS = 8.0

CONT_PIPELINE_KWARGS = dict(trend_indicator="ema_adx_combo", htf_valid_bars=24, entry_variant="direct", min_target_distance_atr=0.5)
CONT_BACKTEST_CFG = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=0.5, use_vwap_target=True, breakeven_trigger_r=None, max_hold_bars=24 * 12)
REV_PIPELINE_KWARGS = dict(h4_confirm_bars=30, h1_valid_bars=24, min_target_distance_atr=1.0, require_ema_reject=True, m15_entry_mode="repeat_sweep")
REV_BACKTEST_CFG = BacktestConfig(spread_bps=SPREAD_BPS, stop_atr_mult=3.0, use_vwap_target=False, take_profit_r=5.0, breakeven_trigger_r=None, max_hold_bars=96 * 4)

SUB_PERIODS = [
    ("2016-01-01", "2018-08-01"), ("2018-08-01", "2020-08-01"),
    ("2020-08-01", "2022-08-01"), ("2022-08-01", "2024-08-01"),
    ("2024-08-01", "2026-08-01"),
]


def fetch_fred(series: str) -> pd.Series:
    df = pd.read_csv(FRED_CSV_URL.format(series=series))
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"]).set_index("date").sort_index()
    return df["value"]


def fmt(s: dict) -> str:
    if s["n_trades"] == 0:
        return "n=0"
    return f"n={s['n_trades']:>4}  WR={s['win_rate']:.1%}  PF={s['profit_factor']:.3f}  Sharpe={s['sharpe']:>6.2f}  CAGR={s['cagr']:+.1%}"


def main():
    print("Fetching VIX (VIXCLS), Dollar-Index-Proxy (DTWEXBGS), WTI-Oel (DCOILWTICO) via FRED ...")
    vix = fetch_fred("VIXCLS")
    dxy = fetch_fred("DTWEXBGS")
    oil = fetch_fred("DCOILWTICO")
    print(f"VIX {vix.index.min().date()}..{vix.index.max().date()} n={len(vix)}")
    print(f"DXY-Proxy {dxy.index.min().date()}..{dxy.index.max().date()} n={len(dxy)}")
    print(f"Oil {oil.index.min().date()}..{oil.index.max().date()} n={len(oil)}")

    print(f"\nFetching GOLD D1 {FULL_START} -> {FULL_END} ...")
    d1 = fetch_gold_d1(FULL_START, FULL_END)
    d1 = d1.copy()
    d1.index = d1.index.tz_localize(None).normalize()
    gold_daily_ret = d1["close"].pct_change()

    macro = pd.DataFrame({"vix": vix, "dxy": dxy, "oil": oil})
    macro["dxy_roc_60"] = macro["dxy"].pct_change(60) * 100  # 60-Handelstage-Momentum
    macro["oil_roc_60"] = macro["oil"].pct_change(60) * 100
    macro = macro.reindex(d1.index).ffill()

    print("\n" + "=" * 100)
    print("MAKRO-KENNZAHLEN PRO SUB-PERIODE")
    print("=" * 100)
    for sp_start, sp_end in SUB_PERIODS:
        sp = macro.loc[sp_start:sp_end]
        print(f"  {sp_start}->{sp_end}:  median VIX={sp['vix'].median():>6.1f}   "
              f"median DXY={sp['dxy'].median():>7.1f}  DXY-60T-RoC median={sp['dxy_roc_60'].median():>+6.2f}%   "
              f"median Oil=${sp['oil'].median():>6.1f}  Oil-60T-RoC median={sp['oil_roc_60'].median():>+7.2f}%")

    # Korrelation Gold-Tagesrendite vs DXY-Tagesrendite (klassische inverse Beziehung? staerker/schwaecher je Periode?)
    dxy_ret = macro["dxy"].pct_change()
    print("\n" + "=" * 100)
    print("KORRELATION Gold-Tagesrendite <-> DXY-Tagesrendite, PRO SUB-PERIODE (staerker negativ = klassischer)")
    print("=" * 100)
    for sp_start, sp_end in SUB_PERIODS:
        g = gold_daily_ret.loc[sp_start:sp_end]
        dx = dxy_ret.loc[sp_start:sp_end]
        corr = g.corr(dx)
        print(f"  {sp_start}->{sp_end}: corr={corr:+.3f}")

    # ---- Filter-Test mit dem vielversprechendsten Kandidaten: DXY 60-Tage-RoC < 0 (struktureller Dollar-Abwertungstrend) ----
    print("\n" + "=" * 100)
    print("FILTER-TEST: nur traden, wenn DXY 60-Tage-Momentum < 0% (struktureller Dollar-Abwertungstrend)")
    print("=" * 100)
    h4 = fetch_gold_h4(FULL_START, FULL_END)
    h1 = fetch_gold_h1(FULL_START, FULL_END)
    m15 = fetch_gold_m15(FULL_START, FULL_END)
    m5 = fetch_gold_m5(FULL_START, FULL_END)

    cont_sig = run_continuation(h4, h1, m5, trend_df=m15, **CONT_PIPELINE_KWARGS)
    rev_sig = run_reversal(h4, h1, m15, **REV_PIPELINE_KWARGS)

    dxy_roc_daily = macro["dxy_roc_60"].copy()
    dxy_roc_daily.index = dxy_roc_daily.index.tz_localize(None)

    def attach_and_filter(sig: pd.DataFrame) -> pd.DataFrame:
        sig = sig.copy()
        day_key = sig.index.tz_localize(None).normalize()
        roc = dxy_roc_daily.reindex(day_key, method="ffill")
        mask = (roc.to_numpy() < 0)
        sig.loc[~mask, "signal"] = 0
        return sig

    cont_sig_f = attach_and_filter(cont_sig)
    rev_sig_f = attach_and_filter(rev_sig)

    for sp_start, sp_end in SUB_PERIODS:
        sp_start_ts, sp_end_ts = pd.Timestamp(sp_start, tz="America/New_York"), pd.Timestamp(sp_end, tz="America/New_York")
        cont_sp = cont_sig_f[(cont_sig_f.index >= sp_start_ts) & (cont_sig_f.index < sp_end_ts)]
        rev_sp = rev_sig_f[(rev_sig_f.index >= sp_start_ts) & (rev_sig_f.index < sp_end_ts)]
        cont_t = simulate_trades(cont_sp, CONT_BACKTEST_CFG)
        rev_t = simulate_trades(rev_sp, REV_BACKTEST_CFG)
        print(f"  {sp_start}->{sp_end}:  Cont {fmt(summarize(cont_t, cont_sp.index))}   |   Rev {fmt(summarize(rev_t, rev_sp.index))}")


if __name__ == "__main__":
    main()
