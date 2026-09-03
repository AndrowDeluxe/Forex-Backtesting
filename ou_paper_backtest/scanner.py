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

Since 2026-08-11, each market's OU-selected universe is additionally filtered down
to tickers actually tradable on TTP (the broker behind Konto 1/2 in
OU-Modell-MT5-Bridge) -- see _load_ttp_tradable_tickers()/
scripts/build_ttp_tradable_universe.py. Fixes a real data leak: the scanner used to
emit signals for OU-selected tickers the live bot could never execute (resolve_symbol()
in executor.py silently drops them) -- e.g. only 58 of 147 OU-selected S&P tickers, and
0 of 40 DAX tickers, are actually tradable on TTP.

Run: `python scanner.py` from the ou_paper_backtest/ directory. Commit the resulting
results/scanner_signals.csv afterward for the dashboard to pick up.
"""

import datetime as dt

import pandas as pd
import yfinance as yf

import config

try:
    # Nur auflösbar, wenn dieses Modul als Skript aus ou_paper_backtest/ heraus
    # laeuft (sys.path[0] = dieses Verzeichnis) -- NICHT wenn challenge_portfolio/
    # paper_bot.py::_import_ou_paper_backtest() es per importlib.util.spec_from_
    # file_location laedt (dort ist ou_paper_backtest/ nicht auf sys.path). Dieser
    # zweite Pfad treibt die LIVE Funded-Portfolio-Bridge (OU-Modell-Bein) -- ein
    # harter Import hier wuerde dessen Verbindung kaputt machen. Fallback: No-Op,
    # exakt dasselbe "Telegram optional" -Verhalten wie ein fehlendes telegram_config.py.
    from telegram_notify import send_telegram_message
except ImportError:
    def send_telegram_message(text: str, parse_mode: str | None = None) -> None:
        pass

# Nutzerwunsch 2026-09-02: nur bei den 3 "Tagesscans" (nicht allen 8 stuendlichen
# Task-Scheduler-Laeufen) eine Telegram-Nachricht schicken -- die tatsaechlichen
# Trigger-Zeiten des Tasks "OU-Modell-ScannerHourly" sind 14:30/15:35.../21:35,
# vom Nutzer als "15:30/18:30/21:30" grob benannt. Toleranzfenster (+/- 10 Min),
# da ein Lauf durch Datenladen/vorherige haengende Prozesse leicht verspaetet
# starten kann.
TELEGRAM_RUN_TIMES = [(15, 35), (18, 35), (21, 35)]
TELEGRAM_TOLERANCE_MINUTES = 10


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


def _load_ttp_tradable_tickers(market_key: str) -> set[str] | None:
    """Ticker, die auf TTP (Konto 1/2, siehe OU-Modell-MT5-Bridge) tatsaechlich als
    Symbol existieren -- gebaut von scripts/build_ttp_tradable_universe.py (read-only
    gegen das TTP-Demo-Terminal, Symbol-Namen 1:1 wie resolve_symbol() sie live prueft).
    Datenleck-Fix (2026-08-11): der Scanner selektierte bisher NUR ueber die
    OU-Kriterien, ohne zu pruefen, ob der Live-Bot ein Signal je ausfuehren koennte --
    von 147 OU-selektierten S&P-Tickern waren nur 58 tatsaechlich handelbar. Gibt None
    zurueck, wenn die Datei fehlt (z.B. frisch geklontes Repo vor dem ersten Lauf von
    build_ttp_tradable_universe.py) -- der Aufrufer faellt dann auf das ungefilterte
    Verhalten zurueck, statt hart zu failen."""
    path = config.RESULTS_DIR / f"{market_key}_ttp_tradable.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    return set(df[df["ttp_tradable"]]["Symbol"])


def scan_market(market_key: str) -> pd.DataFrame:
    label = config.UNIVERSES[market_key]["label"]
    benchmark_ticker = config.UNIVERSES[market_key]["benchmark"]
    ou_table = pd.read_csv(config.RESULTS_DIR / market_key / "ou_parameters_in_sample.csv", index_col=0)
    sel = ou_table[
        (ou_table["theta"] > config.THETA_MIN) & (ou_table["p_value"] < config.PVALUE_MAX)
        & (ou_table["half_life"].between(config.HALFLIFE_MIN, config.HALFLIFE_MAX))
    ]
    tickers = sel.index.tolist()

    tradable = _load_ttp_tradable_tickers(market_key)
    if tradable is None:
        print(f"[{market_key}] WARNUNG: keine {market_key}_ttp_tradable.csv gefunden -- "
              f"scanne UNGEFILTERT (siehe scripts/build_ttp_tradable_universe.py).")
    else:
        n_before = len(tickers)
        tickers = [t for t in tickers if t in tradable]
        print(f"[{market_key}] TTP-Handelbarkeitsfilter: {n_before} -> {len(tickers)} Ticker.")
        if not tickers:
            print(f"[{market_key}] {label}: 0 auf TTP handelbare OU-selektierte Ticker -- "
                  f"kein Scan (z.B. DAX: 0/40 Ticker auf TTP handelbar).")
            return pd.DataFrame()

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
            # Fixed 1:1.5 TP -- challenge-optimization finding (2026-08-07, S&P-only,
            # 2025+ OOS, at the tighter risk_pct=0.25%/max_total_risk_pct=5%/be=0.35R
            # sizing now live on Konto 2): beats the earlier "no TP" locked-config result
            # on speed to a funded-challenge profit target AND Sharpe/Calmar, without
            # giving up safety margin on the 3%-max-daily-loss rule. ONLY validated on
            # S&P -- deliberately NOT applied to nasdaq100/dax (which stay on the
            # original no-TP behavior) since internal_scanner.py has no per-market
            # filter and would otherwise pass an untested TP through to whichever
            # account reads this CSV the moment a Nasdaq/DAX signal ever appears.
            # See app_pages/risk_management.py for the full derivation.
            tp_price = (close_t + 1.5 * stop_distance) if market_key == "sp500" else None
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
                "tp": round(tp_price, 2) if tp_price is not None else "kein TP (finale Config)",
                "tp_price": round(tp_price, 2) if tp_price is not None else 0.0,
                "risk_pct_price": round(risk_pct_price, 2),
                "position_size_pct": round(position_pct, 2),
                "regime_ok": regime_ok,
                "tradeable": regime_ok,
            })

    # concentrated sizing: equal-weight among TODAY's candidates in this market,
    # capped at 1/8 -- matches portfolio.simulate_concentrated_book. Needs the full
    # candidate count first, so computed as a second pass over the collected rows.
    if rows:
        concentrated_frac = min(1.0 / len(rows), 0.125) * 100
        for row in rows:
            row["position_size_concentrated_pct"] = round(concentrated_frac, 2)

    print(f"[{market_key}] {len(rows)} raw signal(s) as of {last_date.date()}, regime_ok={regime_ok}")
    return pd.DataFrame(rows)


def _is_telegram_run_time(now: dt.datetime) -> bool:
    now_minutes = now.hour * 60 + now.minute
    return any(
        abs(now_minutes - (h * 60 + m)) <= TELEGRAM_TOLERANCE_MINUTES
        for h, m in TELEGRAM_RUN_TIMES
    )


def _format_telegram_message(combined: pd.DataFrame, now: dt.datetime) -> str:
    lines = [f"OU-Modell Scan {now.strftime('%H:%M')} Uhr"]
    if combined.empty:
        lines.append("Keine Signale.")
        return "\n".join(lines)
    for market, sub in combined.groupby("market"):
        lines.append(f"\n{market}:")
        for _, row in sub.iterrows():
            status = "handelbar" if row["tradeable"] else "Regime-Filter zu"
            lines.append(
                f"  {row['ticker']}: Entry {row['entry']}, SL {row['sl']}, "
                f"TP {row['tp']} ({status})"
            )
    return "\n".join(lines)


def main():
    all_signals = []
    for market_key in ["sp500", "nasdaq100", "dax"]:
        all_signals.append(scan_market(market_key))
    combined = pd.concat(all_signals, ignore_index=True) if all_signals else pd.DataFrame()

    # Wall-clock run timestamp, separate from scan_date (the underlying trading
    # day, which only advances once/day). Written unconditionally -- even with
    # 0 signals -- as its own small file so app_pages/ou_scanner.py can show
    # "last actually ran at HH:MM" and let the user tell an hourly re-run with
    # unchanged data apart from a task that silently stopped firing.
    scanned_at = dt.datetime.now().isoformat(timespec="seconds")
    if not combined.empty:
        combined["scanned_at"] = scanned_at
    out_path = config.RESULTS_DIR / "scanner_signals.csv"
    combined.to_csv(out_path, index=False)

    meta_path = config.RESULTS_DIR / "scanner_last_run.json"
    meta_path.write_text(
        f'{{"scanned_at": "{scanned_at}", "signal_count": {len(combined)}}}', encoding="utf-8"
    )

    print(f"\nSaved {len(combined)} total signal(s) to {out_path} (scanned_at={scanned_at})")
    if not combined.empty:
        print(combined.to_string(index=False))

    now = dt.datetime.now()
    if _is_telegram_run_time(now):
        send_telegram_message(_format_telegram_message(combined, now))


if __name__ == "__main__":
    main()
