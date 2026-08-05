"""Fetch & cache daily adjusted close prices via yfinance (mirrors paper section 3)."""

import time

import pandas as pd
import yfinance as yf

import config


def _cache_path(ticker: str) -> "config.Path":
    safe = ticker.replace("^", "IDX_")
    return config.DATA_CACHE / f"{safe}.parquet"


def _download_one(ticker: str) -> pd.Series | None:
    try:
        df = yf.download(
            ticker,
            start=config.DOWNLOAD_START,
            end=config.DOWNLOAD_END,
            auto_adjust=True,
            progress=False,
        )
    except Exception as exc:
        print(f"  {ticker}: download error {exc!r}")
        return None
    if df is None or df.empty or "Close" not in df:
        return None
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close.name = ticker
    return close.dropna()


def get_prices(ticker: str, force: bool = False) -> pd.Series | None:
    path = _cache_path(ticker)
    if path.exists() and not force:
        s = pd.read_parquet(path).iloc[:, 0]
        s.name = ticker
        return s
    s = _download_one(ticker)
    if s is None or s.empty:
        return None
    s.to_frame().to_parquet(path)
    return s


def build_price_panel(tickers: list[str], min_start: str, verbose: bool = True) -> pd.DataFrame:
    """Download/cache each ticker, keep only those with uninterrupted history
    starting on/before `min_start` (mirrors the paper's survivorship-continuity filter)."""
    series = {}
    dropped = []
    min_start_ts = pd.Timestamp(min_start)
    for i, t in enumerate(tickers):
        s = get_prices(t)
        if s is None or s.empty or s.index.min() > min_start_ts:
            dropped.append(t)
            if verbose:
                print(f"  [{i+1}/{len(tickers)}] {t}: excluded (insufficient history)")
            continue
        series[t] = s
        if verbose:
            print(f"  [{i+1}/{len(tickers)}] {t}: ok ({s.index.min().date()} - {s.index.max().date()})")
        time.sleep(0.05)
    panel = pd.DataFrame(series)
    panel = panel.sort_index()
    if verbose:
        print(f"Kept {panel.shape[1]}/{len(tickers)} tickers; dropped: {dropped}")
    return panel


if __name__ == "__main__":
    import universe

    tickers = universe.sample_universe()
    panel = build_price_panel(tickers, min_start=config.IN_SAMPLE_START)
    panel.to_parquet(config.DATA_CACHE / "_panel.parquet")
    print(panel.shape)
