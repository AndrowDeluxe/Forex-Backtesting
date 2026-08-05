"""Position signals for the two variants the paper backtests (Sec. 4):

1. **Single TEMA/TSMA** (Sec. 4.1): long while Close is above the n-period
   TEMA/TSMA, flat once Close closes back below it. The paper's own chart
   captions call this a "12 month" indicator (Fig. 8/9), which we read as
   n=`SINGLE_WINDOW_DEFAULT`=252 trading days - the paper never states an
   exact bar count, so this is an explicit, documented reading rather than
   a hidden guess.

2. **Three Triple crossover / TTEMA-TTSMA** (Sec. 4.2): short (20d),
   medium (30d) and long (50d) TEMA or TSMA are "crossed over". The paper
   describes the inputs but never spells out the exact entry/exit
   condition. We implement the standard triple-MA reading: long while the
   three are bullishly stacked (short > medium > long), flat otherwise.
   This is the one place in this module where the paper's text is
   genuinely ambiguous and a choice had to be made - flagged here and in
   the dashboard, not silently assumed.
"""

import pandas as pd

from triple_ma_strategy.indicators import triple_ma

SINGLE_WINDOW_DEFAULT = 252
TRIPLE_SHORT_DEFAULT = 20
TRIPLE_MEDIUM_DEFAULT = 30
TRIPLE_LONG_DEFAULT = 50


def generate_single_signal(close: pd.Series, window: int = SINGLE_WINDOW_DEFAULT, ma_type: str = "tema") -> pd.Series:
    """1 = long (Close > MA), 0 = flat. NaN warmup bars are flat."""
    ma = triple_ma(close, window, ma_type)
    position = (close > ma).astype(float)
    position[ma.isna()] = 0.0
    position.name = "position"
    return position


def generate_triple_crossover_signal(
    close: pd.Series, short: int = TRIPLE_SHORT_DEFAULT, medium: int = TRIPLE_MEDIUM_DEFAULT,
    long: int = TRIPLE_LONG_DEFAULT, ma_type: str = "tema",
) -> pd.Series:
    """1 = long (short > medium > long, bullishly stacked), 0 = flat."""
    short_ma = triple_ma(close, short, ma_type)
    medium_ma = triple_ma(close, medium, ma_type)
    long_ma = triple_ma(close, long, ma_type)
    stacked_bull = (short_ma > medium_ma) & (medium_ma > long_ma)
    position = stacked_bull.astype(float)
    position[long_ma.isna()] = 0.0
    position.name = "position"
    return position
