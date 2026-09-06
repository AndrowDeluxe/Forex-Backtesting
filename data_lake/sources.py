"""Registry: jede (source, key, timeframe)-Kombination, die die 6
Funded-Portfolio-Bridge-Beine brauchen, mit der bereits bestehenden,
validierten Fetch-Funktion, die sie zieht (data_lake baut NIE eine eigene
Fetch-Logik -- siehe resilient-painting-raven.md-Plan). Jeder Eintrag wird
GENAU EINMAL gespeichert, auch wenn mehrere Beine dieselben Rohdaten in
UNTERSCHIEDLICHER Form brauchen (z.B. GOLD H1 roh/UTC fuer trend_pullback
vs. klein/NY-tz fuer ctnl_edge) -- die Formumwandlung passiert erst in
reader.py beim Lesen, nie doppelt gespeichert.

`lookback_days` wird NUR beim allerersten Ingest-Lauf fuer einen Key benutzt
(noch keine gespeicherten Balken vorhanden) -- jeder folgende Lauf holt nur
die Luecke seit dem zuletzt gespeicherten Balken (siehe ingest.py), nie das
komplette Fenster erneut. Das ist der eigentliche Hebel gegen den
dukascopy_python-Paginierungs-Bug (siehe ny_open_orb/data.py-Docstring):
kleine, haeufige Anfragen statt grosser, seltener."""

from dataclasses import dataclass
from typing import Callable

import pandas as pd


@dataclass(frozen=True)
class LakeSource:
    source: str        # Namespace in data_lake_store/validated/<source>/ -- trennt Dukascopy/TradingView/eigene Bloecke
    key: str            # Instrument/Ticker-Label fuer den Dateinamen
    timeframe: str
    fetch: Callable[[str, str, bool], pd.DataFrame]  # (start, end, force_refresh) -> DataFrame, IMMER die echte Original-Funktion
    lane: str            # "fast" (15-Min-Ingestion), "fast5" (5-Min-Ingestion -- NUR die M5/M15-
                          # Timing-kritischen Keys fuer ctnl_continuation/orb, siehe DASHBOARD.md
                          # 2026-09-02/2026-09-04-Entscheidung und Funded-Portfolio-Bridge/
                          # run_once_fast.py) oder "slow" (stuendlich, siehe ou_modell)
    lookback_days: int    # nur fuer den allerersten Seed-Lauf ohne vorhandene Lake-Daten


def _dukascopy(key: str, timeframe: str):
    from combined_strategy.data import fetch_timeframe
    return lambda start, end, force_refresh: fetch_timeframe(key, timeframe, start, end, force_refresh=force_refresh)


def _orb(instrument: str, timeframe: str):
    from ny_open_orb.data import fetch_m5, fetch_m15
    fn = fetch_m5 if timeframe == "M5" else fetch_m15
    return lambda start, end, force_refresh: fn(instrument, start, end, force_refresh=force_refresh)


def _rate_instrument(key: str):
    from cls_practical.data import fetch_rate_instrument_m5_berlin
    return lambda start, end, force_refresh: fetch_rate_instrument_m5_berlin(key, start, end, force_refresh=force_refresh)


def _tvc_yield(key: str):
    from cls_practical.data import fetch_2y_yield_daily
    # fetch_2y_yield_daily kennt keine start/end-Spanne (tvDatafeed liefert nur "letzte n_bars") --
    # start/end werden hier bewusst ignoriert, n_bars deckt die volle noetige Historie ab (siehe
    # cls_practical/data.py-Docstring: 3650 ~= 10 Jahre).
    return lambda start, end, force_refresh: fetch_2y_yield_daily(key, force_refresh=force_refresh)


FAST_SOURCES: list[LakeSource] = [
    # gold_asb + ctnl_edge (GOLD M15 gemeinsam), trend_pullback + gold_asb-Friction (GOLD D1 gemeinsam)
    LakeSource("dukascopy", "GOLD", "M15", _dukascopy("GOLD", "M15"), "fast", 10),
    LakeSource("dukascopy", "GOLD", "D1", _dukascopy("GOLD", "D1"), "fast", 400),
    LakeSource("dukascopy", "SILVER", "M15", _dukascopy("SILVER", "M15"), "fast", 10),
    # trend_pullback
    LakeSource("dukascopy", "GOLD", "H1", _dukascopy("GOLD", "H1"), "fast", 320),
    LakeSource("dukascopy", "SILVER", "H1", _dukascopy("SILVER", "H1"), "fast", 320),
    LakeSource("dukascopy", "PLATINUM", "H1", _dukascopy("PLATINUM", "H1"), "fast", 320),
    LakeSource("dukascopy", "CHFJPY", "H4", _dukascopy("CHFJPY", "H4"), "fast", 320),
    LakeSource("dukascopy", "USDJPY", "H4", _dukascopy("USDJPY", "H4"), "fast", 320),
    # ctnl_edge (GOLD M15 s.o. gemeinsam genutzt). GOLD H4/H1/M15 bleiben bewusst auf "fast" --
    # gold_smc_htf_ltf/continuation.py::compute_h1_context() merged trend_df (M15) nur als
    # H1-getaktete Bias-Serie, keine M5-Entry-Timing-Wirkung. GOLD M5 dagegen ist Continuations
    # tatsaechliche Entry-Timeframe ("M5 sweep-and-reject", run_pipeline()-Docstring) -- deshalb
    # unten auf "fast5" (5-Min-Ingestion, siehe DASHBOARD.md 2026-09-02-Entscheidung).
    LakeSource("dukascopy", "GOLD", "H4", _dukascopy("GOLD", "H4"), "fast", 100),
    LakeSource("dukascopy", "GOLD", "M5", _dukascopy("GOLD", "M5"), "fast5", 100),
    # cls_practical: gehandeltes Paar + 5 Referenz-Majors (nie gehandelt, nur Cross-Check) + Zinsproxy
    LakeSource("dukascopy", "EURUSD", "M5", _dukascopy("EURUSD", "M5"), "fast", 410),
    LakeSource("dukascopy", "GBPUSD", "M15", _dukascopy("GBPUSD", "M15"), "fast", 410),
    LakeSource("dukascopy", "USDJPY", "M15", _dukascopy("USDJPY", "M15"), "fast", 410),
    LakeSource("dukascopy", "USDCHF", "M15", _dukascopy("USDCHF", "M15"), "fast", 410),
    LakeSource("dukascopy", "AUDUSD", "M15", _dukascopy("AUDUSD", "M15"), "fast", 410),
    LakeSource("dukascopy", "USDCAD", "M15", _dukascopy("USDCAD", "M15"), "fast", 410),
    LakeSource("dukascopy", "BUND", "M5", _rate_instrument("BUND"), "fast", 410),
    LakeSource("dukascopy", "USTBOND", "M5", _rate_instrument("USTBOND"), "fast", 410),
    LakeSource("tradingview", "DE02Y", "D1", _tvc_yield("DE02Y"), "fast", 0),
    LakeSource("tradingview", "US02Y", "D1", _tvc_yield("US02Y"), "fast", 0),
    # orb -- M5 UND M15 beide auf "fast5": ny_open_orb/engine.py::build_frame() haengt orb_high/
    # orb_low (und damit JEDE Entry-Erkennung der Session) an der Freshness des M15-Range-Bars
    # direkt nach NY-Open (range_bars=1 -> Range schliesst exakt 15 Min nach Open); auf der alten
    # 15-Min-Kadenz haette das den allerersten Breakout jeder Session um bis zu weitere 15 Minuten
    # verzoegert, obwohl M5 schon frisch waere -- genau das Problem, das dieser Fast-Trigger loesen
    # soll (siehe DASHBOARD.md 2026-09-02-Entscheidung).
    LakeSource("dukascopy", "SP500", "M5", _orb("SP500", "M5"), "fast5", 510),
    LakeSource("dukascopy", "US30", "M5", _orb("US30", "M5"), "fast5", 510),
    LakeSource("dukascopy", "NASDAQ", "M5", _orb("NASDAQ", "M5"), "fast5", 510),
    LakeSource("dukascopy", "SP500", "M15", _orb("SP500", "M15"), "fast5", 510),
    LakeSource("dukascopy", "US30", "M15", _orb("US30", "M15"), "fast5", 510),
    LakeSource("dukascopy", "NASDAQ", "M15", _orb("NASDAQ", "M15"), "fast5", 510),
]


def ou_modell_tickers() -> list[str]:
    """Baut dieselbe dynamische Ticker-Liste, die _scan_ou_modell() live
    berechnen wuerde (theta/p-value/half-life-Filter + TTP-handelbare
    Teilmenge) -- die Lake-Ingestion darf NIE von dem abweichen, was der
    echte Scan tatsaechlich braucht, siehe Plan-Dokument."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import challenge_portfolio.paper_bot as pb

    ou_config, _ou_portfolio, load_ttp_tradable_tickers = pb._import_ou_paper_backtest()
    tickers: set[str] = set()
    for market_key in pb.OU_MODELL_MARKETS:
        import pandas as _pd
        table = _pd.read_csv(ou_config.RESULTS_DIR / market_key / "ou_parameters_in_sample.csv", index_col=0)
        sel = table[
            (table["theta"] > ou_config.THETA_MIN) & (table["p_value"] < ou_config.PVALUE_MAX)
            & (table["half_life"].between(ou_config.HALFLIFE_MIN, ou_config.HALFLIFE_MAX))
        ]
        selected = sel.index.tolist()
        tradable = load_ttp_tradable_tickers(market_key)
        if tradable is not None:
            selected = [t for t in selected if t in tradable]
        tickers.update(selected)
    return sorted(tickers)
