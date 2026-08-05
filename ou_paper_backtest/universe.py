"""Build reproducible ticker universes for the OU-Modell replica: a sampled S&P 500
subset (paper's original universe) and the full Nasdaq-100 (individual tech/growth
names, the user's second requested universe)."""

import random

import pandas as pd

import config


def _yfinance_symbol(raw: str) -> str:
    """Wikipedia uses dots (BRK.B); yfinance wants dashes (BRK-B)."""
    return raw.strip().replace(".", "-")


def load_sp500_symbols() -> list[str]:
    df = pd.read_csv(config.SP500_WIKI_CSV)
    return [_yfinance_symbol(s) for s in df["Symbol"].tolist()]


def load_nasdaq100_symbols() -> list[str]:
    df = pd.read_csv(config.NASDAQ100_WIKI_CSV)
    return [_yfinance_symbol(s) for s in df["Ticker"].tolist()]


def sample_universe(n: int = config.N_SAMPLE_TICKERS, seed: int = config.RANDOM_SEED) -> list[str]:
    """Reproducible random subset of the S&P 500 (paper used 424/503; we sample fewer
    for tractability)."""
    symbols = load_sp500_symbols()
    rng = random.Random(seed)
    rng.shuffle(symbols)
    return sorted(symbols[:n])


def nasdaq100_universe() -> list[str]:
    """Full current Nasdaq-100 constituent list (already a curated, liquid ~100-name
    universe, so no further sampling)."""
    return sorted(set(load_nasdaq100_symbols()))


if __name__ == "__main__":
    tickers = sample_universe()
    print(len(tickers), "S&P sample tickers")
    print(tickers)
    nas = nasdaq100_universe()
    print(len(nas), "Nasdaq-100 tickers")
    print(nas)
