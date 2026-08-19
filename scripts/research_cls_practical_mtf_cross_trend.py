"""EUR/USD: Mentor-Idee 2026-08-19 - der bestehende, live genutzte
Cross-Filter (strategy.cls_advanced.compute_cross_confirmation) prueft nur
den 06:00-09:00-MOVE der 5 anderen Majors (GBPUSD, USDJPY, USDCHF, AUDUSD,
USDCAD - dieselben 5, die der Mentor als "5 Crosspairs" meint). Der Mentor
prueft stattdessen deren TREND, und zwar zweifach: einmal auf H1, einmal auf
M15 - beide muessen zustimmen. Bisher nicht getestet.

Trend-Definition: dieselbe SMA-basierte trend_bias()-Logik, die die eigene
EUR/USD-Tagestrend-Bedingung schon nutzt (Schlusskurs vs. eigenem gleitenden
Durchschnitt, jeweils PRIOR bar - kein Lookahead), hier auf H1- bzw.
M15-Balken statt Tagesbalken angewendet. sma_window ist eine bewusst
offengelegte Annahme (im Code kein Vorbild dafuer) - deshalb hier ueber
mehrere Werte gesweept statt einen einzelnen zu erraten.

Pro Zeitrahmen: USD-Staerke-Mehrheitsvotum ueber alle 5 Crosses (>=3/5,
_USD_IS_QUOTE-Vorzeichenkonvention wie compute_cross_confirmation), gelesen
als letzter Balken VOR/AM Haltetest-Checkpoint (09:00, aktueller Default) -
kein Lookahead. Bestaetigt = H1-Mehrheit UND M15-Mehrheit stimmen mit der
von EUR/USDs eigenem Break implizierten USD-Richtung ueberein.

Getestet als Ersatz fuer den bestehenden Cross-Gate (cross_confirm_override,
filter_mode="and", use_cross_filter=True unveraendert) gegen die aktuelle
Live-Baseline, IS/OOS."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import strategy.cls_advanced as cls_advanced
from cls_practical.data import fetch_eurusd_entry_tf_berlin, fetch_major_m15_berlin, fetch_rate_instrument_m5_berlin
from cls_practical.engine import simulate_cls_practical, trend_bias
from combined_strategy.data import fetch_timeframe
from strategy.cls_advanced import compute_daily_features, to_berlin

START, END = "2018-12-01", "2026-08-11"
SPLIT = "2022-06-01"
FIVE_CROSSES = [p for p in cls_advanced.PAIRS if p != "EURUSD"]
CHECKPOINT_HOUR = 9.0


def fetch_h1_berlin(key: str) -> pd.DataFrame:
    df = fetch_timeframe(key, "H1", START, END)
    df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    df.index = df.index.tz_convert("Europe/Berlin")
    return df


def as_of_checkpoint(bias: pd.Series, bar_index: pd.DatetimeIndex, checkpoint_hour: float) -> pd.Series:
    """Last bar's trend_bias value at/before checkpoint_hour, per Berlin
    calendar day - the reading actually knowable by the checkpoint."""
    berlin = to_berlin(bar_index)
    hour = berlin.hour + berlin.minute / 60.0
    date = pd.Series(berlin.date, index=bar_index)
    df = pd.DataFrame({"date": date.to_numpy(), "hour": hour, "bias": bias.to_numpy()})
    df = df[df["hour"] <= checkpoint_hour]
    return df.groupby("date")["bias"].last()


def usd_strength_majority(pair_bias_by_tf: dict[str, pd.Series]) -> pd.Series:
    """+1/-1 majority vote (USD-strength direction) across the 5 crosses,
    each already reduced to a date-indexed daily reading. NaN if fewer than
    3 of 5 pairs have a reading that day (can't form a majority)."""
    adj = {}
    for pair, daily_bias in pair_bias_by_tf.items():
        adj[pair] = -daily_bias if cls_advanced._USD_IS_QUOTE[pair] else daily_bias
    df = pd.DataFrame(adj)
    vote_sum = df.sum(axis=1, skipna=True)
    n_avail = df.notna().sum(axis=1)
    majority = np.sign(vote_sum)
    majority[n_avail < 3] = np.nan
    return majority


def stats(trades: pd.DataFrame, label: str) -> dict:
    n = len(trades)
    if n == 0:
        print(f"    {label}: keine Trades")
        return {"label": label, "n": 0}
    r = trades["pnl_usd"] / trades["risk_amount_usd"]
    win_rate = (trades["pnl_usd"] > 0).mean()
    gross_profit = trades.loc[trades["pnl_usd"] > 0, "pnl_usd"].sum()
    gross_loss = -trades.loc[trades["pnl_usd"] < 0, "pnl_usd"].sum()
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    is_mask = trades["entry_time"].dt.tz_localize(None) < SPLIT
    is_r, oos_r = r[is_mask], r[~is_mask]
    row = {
        "label": label, "n": n, "win_rate": win_rate * 100, "avg_r": r.mean(), "profit_factor": pf,
        "total_pnl": trades["pnl_usd"].sum(), "n_is": int(is_mask.sum()),
        "avg_r_is": is_r.mean() if len(is_r) else float("nan"),
        "n_oos": int((~is_mask).sum()), "avg_r_oos": oos_r.mean() if len(oos_r) else float("nan"),
    }
    print(f"    {label:28s}: n={row['n']:>3d} WR={row['win_rate']:5.1f}% avg_R={row['avg_r']:+.3f} PF={row['profit_factor']:.2f} "
          f"PnL=${row['total_pnl']:+,.0f} | IS(n={row['n_is']:>3d}) avg_R={row['avg_r_is']:+.3f} | "
          f"OOS(n={row['n_oos']:>3d}) avg_R={row['avg_r_oos']:+.3f}")
    return row


def main():
    print("Lade Daten (EUR/USD M5 + 5 Crosses H1+M15 + Rates)...")
    eurusd_m5 = fetch_eurusd_entry_tf_berlin("M5", START, END)
    other_majors_m15 = {p: fetch_major_m15_berlin(p, START, END) for p in FIVE_CROSSES}
    crosses_h1 = {p: fetch_h1_berlin(p) for p in FIVE_CROSSES}
    bund_m5 = fetch_rate_instrument_m5_berlin("BUND", START, END)
    ustbond_m5 = fetch_rate_instrument_m5_berlin("USTBOND", START, END)

    daily = compute_daily_features(eurusd_m5, test_hour=CHECKPOINT_HOUR)
    direction = daily["direction"]
    eurusd_implied_usd_dir = -direction  # EURUSD is _USD_IS_QUOTE=True

    print("\n" + "=" * 100 + "\nBASELINE (aktueller Live-Cross-Filter, unveraendert)\n" + "=" * 100)
    baseline = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5)
    rows = [stats(baseline, "Baseline (compute_cross_confirmation)")]

    print("\n" + "=" * 100 + "\nH1+M15 TREND-MEHRHEITSVOTUM DER 5 CROSSES (sma_window-Sweep)\n" + "=" * 100)
    for sma_h1 in (20, 50):
        h1_bias = {p: as_of_checkpoint(trend_bias(crosses_h1[p]["close"], sma_window=sma_h1), crosses_h1[p].index, CHECKPOINT_HOUR)
                   for p in FIVE_CROSSES}
        h1_majority = usd_strength_majority(h1_bias)
        for sma_m15 in (20, 50):
            m15_bias = {p: as_of_checkpoint(trend_bias(other_majors_m15[p]["close"], sma_window=sma_m15), other_majors_m15[p].index, CHECKPOINT_HOUR)
                       for p in FIVE_CROSSES}
            m15_majority = usd_strength_majority(m15_bias)

            idx = direction.index
            h1_al = h1_majority.reindex(idx)
            m15_al = m15_majority.reindex(idx)
            confirmed = (h1_al == eurusd_implied_usd_dir) & (m15_al == eurusd_implied_usd_dir) & eurusd_implied_usd_dir.notna()
            confirmed = confirmed.fillna(False)
            coverage = (h1_al.notna() & m15_al.notna()).mean() * 100

            label = f"H1({sma_h1})+M15({sma_m15}) ({confirmed.mean()*100:.0f}% best., {coverage:.0f}% Abdeckung)"
            trades = simulate_cls_practical(eurusd_m5, other_majors_m15, bund_m5, ustbond_m5, cross_confirm_override=confirmed)
            row = stats(trades, label)
            row.update({"sma_h1": sma_h1, "sma_m15": sma_m15})
            rows.append(row)

    df = pd.DataFrame(rows)
    out_path = Path(__file__).resolve().parents[1] / "cls_practical" / "results" / "eurusd_mtf_cross_trend_sweep.csv"
    df.to_csv(out_path, index=False)
    print(f"\nGespeichert: {out_path}")


if __name__ == "__main__":
    main()
