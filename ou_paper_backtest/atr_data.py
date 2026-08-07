"""Fetches & caches High/Low/Close (not just Close, unlike data.py) for the small
OU-selected ticker subset, needed only for the ATR-based trailing-stop variant in
portfolio.simulate_trailing_bracket_portfolio -- the rest of this package works off
Close-only price panels since the paper's own rules never need intrabar range."""

from pathlib import Path

import pandas as pd
import yfinance as yf

import config

OHLC_CACHE = config.DATA_CACHE / "ohlc"


def _cache_path(ticker: str) -> Path:
    safe = ticker.replace("^", "IDX_")
    return OHLC_CACHE / f"{safe}.parquet"


def _download_ohlc(ticker: str) -> pd.DataFrame | None:
    try:
        df = yf.download(
            ticker, start=config.DOWNLOAD_START, end=config.DOWNLOAD_END,
            auto_adjust=True, progress=False,
        )
    except Exception as exc:
        print(f"  {ticker}: download error {exc!r}")
        return None
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    if not {"High", "Low", "Close"}.issubset(df.columns):
        return None
    return df[["High", "Low", "Close"]].dropna()


def get_ohlc(ticker: str, force: bool = False) -> pd.DataFrame | None:
    OHLC_CACHE.mkdir(parents=True, exist_ok=True)
    path = _cache_path(ticker)
    if path.exists() and not force:
        return pd.read_parquet(path)
    df = _download_ohlc(ticker)
    if df is None or df.empty:
        return None
    df.to_parquet(path)
    return df


def true_range(ohlc: pd.DataFrame) -> pd.Series:
    prev_close = ohlc["Close"].shift(1)
    return pd.concat([
        ohlc["High"] - ohlc["Low"],
        (ohlc["High"] - prev_close).abs(),
        (ohlc["Low"] - prev_close).abs(),
    ], axis=1).max(axis=1)


def atr(ohlc: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder's ATR (EWM with alpha=1/period, the original/standard smoothing)."""
    tr = true_range(ohlc)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def build_atr_panel(tickers: list[str], period: int = 14, verbose: bool = True) -> pd.DataFrame:
    series = {}
    for i, t in enumerate(tickers):
        ohlc = get_ohlc(t)
        if ohlc is None or ohlc.empty:
            if verbose:
                print(f"  [{i+1}/{len(tickers)}] {t}: no OHLC data, skipped")
            continue
        series[t] = atr(ohlc, period=period)
        if verbose:
            print(f"  [{i+1}/{len(tickers)}] {t}: ok")
    panel = pd.DataFrame(series).sort_index()
    if verbose:
        print(f"ATR panel: {panel.shape[1]}/{len(tickers)} tickers, period={period}")
    return panel


if __name__ == "__main__":
    import sys

    universe_key = sys.argv[1] if len(sys.argv) > 1 else "sp500"
    ou_table = pd.read_csv(config.RESULTS_DIR / universe_key / "ou_parameters_in_sample.csv", index_col=0)
    sel = ou_table[
        (ou_table["theta"] > config.THETA_MIN) & (ou_table["p_value"] < config.PVALUE_MAX)
        & (ou_table["half_life"].between(config.HALFLIFE_MIN, config.HALFLIFE_MAX))
    ]
    tickers = sel.index.tolist()
    panel = build_atr_panel(tickers)
    out_path = config.DATA_CACHE / f"_atr_panel_{universe_key}.parquet"
    panel.to_parquet(out_path)
    print(f"Saved {out_path} {panel.shape}")
