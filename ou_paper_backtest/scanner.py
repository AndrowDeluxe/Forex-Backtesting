"""Local scanner script (run manually, NOT from Streamlit Cloud -- same pattern as
scripts/collect_ou_modell_daily_log.py for the live bot's dashboard): refreshes
price data up to today for the OU-selected universe of all three markets (S&P 500,
Nasdaq-100, DAX), evaluates the final locked strategy's entry rule as of the latest
available trading day, and writes one committed CSV that app_pages/fertige_strategien.py
(the "Live-Signale (Scanner)" tab) reads -- the Streamlit page itself never calls
yfinance.

Entry rule matches portfolio.simulate_bracket_portfolio exactly: close < lower
Bollinger band (n=20, k=2) on the OU-selected universe, only when the market-wide
EMA200 regime filter permits it. This is a point-in-time signal snapshot, not a
running position tracker -- it does not know about (and cannot show) positions a
user might already be holding from a prior scan.

Run: `python scanner.py` from the ou_paper_backtest/ directory. Commit the resulting
results/scanner_signals.csv afterward for the dashboard to pick up.
"""

import datetime as dt

import pandas as pd
import yfinance as yf

import config


def _refresh_universe_prices(tickers: list[str], benchmark_ticker: str) -> tuple[pd.DataFrame, pd.Series]:
    """Downloads FRESH data up to today for just the (small) OU-selected ticker set
    + its benchmark -- deliberately not the full historical panel used elsewhere in
    this package, since a scanner only needs enough trailing history for a 20-day
    Bollinger window + a 200-day EMA regime filter, not the full 2009-2024 span."""
    lookback_start = (dt.date.today() - dt.timedelta(days=400)).isoformat()
    today = dt.date.today().isoformat()

    prices = {}
    for t in tickers:
        df = yf.download(t, start=lookback_start, end=today, auto_adjust=True, progress=False)
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        if not close.empty:
            prices[t] = close

    panel = pd.DataFrame(prices)
    bench_df = yf.download(benchmark_ticker, start=lookback_start, end=today, auto_adjust=True, progress=False)
    benchmark = bench_df["Close"]
    if isinstance(benchmark, pd.DataFrame):
        benchmark = benchmark.iloc[:, 0]
    return panel, benchmark


def scan_market(market_key: str) -> pd.DataFrame:
    label = config.UNIVERSES[market_key]["label"]
    benchmark_ticker = config.UNIVERSES[market_key]["benchmark"]
    ou_table = pd.read_csv(config.RESULTS_DIR / market_key / "ou_parameters_in_sample.csv", index_col=0)
    sel = ou_table[
        (ou_table["theta"] > config.THETA_MIN) & (ou_table["p_value"] < config.PVALUE_MAX)
        & (ou_table["half_life"].between(config.HALFLIFE_MIN, config.HALFLIFE_MAX))
    ]
    tickers = sel.index.tolist()
    print(f"[{market_key}] {label}: scanning {len(tickers)} OU-selected tickers...")

    panel, benchmark = _refresh_universe_prices(tickers, benchmark_ticker)
    if panel.empty or benchmark.empty:
        print(f"[{market_key}] no data returned, skipping")
        return pd.DataFrame()

    last_date = panel.index.max()
    regime_ok = bool((benchmark > benchmark.ewm(span=200).mean()).reindex(panel.index).ffill().loc[last_date])

    rows = []
    for t in tickers:
        price = panel[t].dropna()
        if len(price) < config.BB_LOOKBACK + 1 or price.index.max() != last_date:
            continue
        ma = price.rolling(config.BB_LOOKBACK).mean()
        std = price.rolling(config.BB_LOOKBACK).std()
        lower = (ma - config.BB_K * std).loc[last_date]
        close_t = price.loc[last_date]
        std_t = std.loc[last_date]
        if pd.isna(lower) or pd.isna(std_t) or std_t == 0:
            continue
        if close_t < lower:
            stop_distance = 3.0 * std_t  # stop_sigma from the final locked config
            sl_price = close_t - stop_distance
            risk_pct_price = stop_distance / close_t * 100  # SL distance as % of entry (Kurs->Stop)
            # position size: same rule as portfolio.simulate_bracket_portfolio -- risk
            # RISK_PCT_PER_TRADE of equity against the stop distance, capped at
            # MAX_POSITION_PCT notional. Assumes this is the only open position (the
            # scanner is a point-in-time snapshot, it doesn't track concurrently open
            # positions, so the 15%-total-risk portfolio cap isn't applied here).
            position_pct = min(config.RISK_PCT_PER_TRADE / (stop_distance / close_t), config.MAX_POSITION_PCT) * 100
            rows.append({
                "market": label, "ticker": t, "scan_date": last_date.date().isoformat(),
                "close": round(close_t, 2), "lower_band": round(lower, 2),
                "entry": round(close_t, 2), "sl": round(sl_price, 2),
                "tp": "kein TP (finale Config)",
                "risk_pct_price": round(risk_pct_price, 2),
                "position_size_pct": round(position_pct, 2),
                "regime_ok": regime_ok,
                "tradeable": regime_ok,
            })
    print(f"[{market_key}] {len(rows)} raw signal(s) as of {last_date.date()}, regime_ok={regime_ok}")
    return pd.DataFrame(rows)


def main():
    all_signals = []
    for market_key in ["sp500", "nasdaq100", "dax"]:
        all_signals.append(scan_market(market_key))
    combined = pd.concat(all_signals, ignore_index=True) if all_signals else pd.DataFrame()
    out_path = config.RESULTS_DIR / "scanner_signals.csv"
    combined.to_csv(out_path, index=False)
    print(f"\nSaved {len(combined)} total signal(s) to {out_path}")
    if not combined.empty:
        print(combined.to_string(index=False))


if __name__ == "__main__":
    main()
