"""OU-Modell: frisst die reale Ausfuehrung den Edge? (Research, 2026-09-16)

Frage des Nutzers: das OU-Bein wirkt live nicht profitabel -- ist das normal,
und fressen Kosten/Versatz den Edge?

Vorgehen: das Modell (ou_paper_backtest/portfolio.py::simulate_bracket_portfolio,
exakt die Funded-Konfiguration aus challenge_portfolio/paper_bot.py) erzeugt die
Trade-LISTE -- welche Aktie an welchem Signaltag. Diese Liste bleibt fix. Jeder
Trade wird danach auf echten Tageskerzen (OHLC) in mehreren Ausfuehrungs-
Varianten neu durchgespielt. Damit ist jede Differenz zwischen den Varianten
reine Ausfuehrung, keine andere Signalauswahl.

Das Modell rechnet reibungsfrei und nur auf Schlusskursen:
  - Einstieg zum Schlusskurs des Signaltags (live: erst am Folgetag),
  - SL/Breakeven/TP nur geprueft, wenn ein SCHLUSSKURS die Marke kreuzt
    (live: Broker-Stop reagiert auf jedes Intraday-Tief),
  - kein Spread, kein Swap.

Varianten (kumulativ):
  A  Modell          Schlusskurs-Einstieg, Schlusskurs-Exits, keine Kosten
  B  +Folgetag       Einstieg zur Eroeffnung des Folgetags; SL/TP-Preise bleiben
                     die absoluten Signal-Level (wie live); Deviation-Gate 3,5 %
                     und "Open schon unter SL" -> Trade faellt aus (wie live)
  C  +Intraday-SL    der Initial-SL wird auf dem Tagestief geprueft, Gap unter
                     den SL fuellt zur Eroeffnung  (= Funded-Bridge: nur der
                     Initial-SL liegt beim Broker, BE/TP laufen ueber den Re-Scan)
  D  +Intraday-BE/TP zusaetzlich BE-Stop und TP broker-seitig auf Hoch/Tief
                     (= OU-Modell-Solo-Bot / EK-Bridge)
  C$ / D$            C bzw. D plus LIVE GEMESSENE Kosten (MT5-Ticks/Deals der drei
                     OU-Konten, 2026-07-23..09-16): Einstieg halber Spread + Fill-
                     vs-Mid 13 bps (Eroeffnungsphase), Exit 5 bps, Swap 1,78 bps
                     je Kalendertag auf den Nominalwert.

R wird wie live gegen die TATSAECHLICHE Stopdistanz (Fill -> SL) gemessen, da die
Bridges genau darauf sizen (konstantes $-Risiko).

Bekannte Grenzen: Universum = heutige Index-Mitglieder (Survivorship-Bias,
betrifft alle Varianten gleich); yfinance auto_adjust (Dividenden in den Kursen
statt als Buchung); Einstieg zur Eroeffnung statt ~5 Min. danach.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import challenge_portfolio.paper_bot as pb  # noqa: E402

START, END = "2018-01-01", "2026-09-16"
DL_START = "2016-06-01"
DEV_GATE = 0.035  # = MAX_OU_MODELL_ENTRY_DEVIATION_PCT der Bridges
COST_ENTRY_BPS, COST_EXIT_BPS, SWAP_BPS_DAY = 13.0, 5.0, 1.78
OUT = REPO / "ou_paper_backtest" / "results" / "execution_costs_20260916.json"


def load_universe():
    ou_config, ou_portfolio, tradable_fn = pb._import_ou_paper_backtest()
    uni = {}
    for mk in pb.OU_MODELL_MARKETS:
        tab = pd.read_csv(ou_config.RESULTS_DIR / mk / "ou_parameters_in_sample.csv", index_col=0)
        sel = tab[(tab["theta"] > ou_config.THETA_MIN) & (tab["p_value"] < ou_config.PVALUE_MAX)
                  & tab["half_life"].between(ou_config.HALFLIFE_MIN, ou_config.HALFLIFE_MAX)]
        tick = sel.index.tolist()
        tr = tradable_fn(mk)
        if tr is not None:
            tick = [t for t in tick if t in tr]
        uni[mk] = tick
    return ou_config, ou_portfolio, uni


CACHE_DIR = REPO / "ou_paper_backtest" / "data_cache" / "ou_research_ohlc"


def download(tickers, refresh=False):
    """Tages-OHLC je Ticker, mit Plattencache.

    Der Cache ist am 2026-09-23 dazugekommen und loest zwei GEMESSENE Probleme:
    (a) yfinance liefert bei vielen Abrufen in kurzer Folge einzelne Symbole gar
        nicht mehr -- in einem Lauf blieben 58 von 66 leer. Ein Ergebnis, das
        danach auf einer Teilmenge des Universums rechnet, sieht aus wie ein
        normales Ergebnis. Jetzt wird gemeldet, was fehlt.
    (b) `auto_adjust` bereinigt rueckwirkend um Dividenden, wodurch derselbe
        Lauf an zwei Tagen um ~0,002R auseinanderlaeuft (dokumentiert in
        knowledge/projects/ou-modell-kostenvalidierung.md). Mit Cache rechnet
        jede Verifikation auf exakt denselben Kursen.

    `refresh=True` holt neu und ueberschreibt den Cache."""
    tickers = sorted(set(tickers))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ohlc, missing = {}, []
    for t in tickers:
        p = CACHE_DIR / f"{t}.parquet"
        if p.exists() and not refresh:
            ohlc[t] = pd.read_parquet(p)
        else:
            missing.append(t)

    if missing:
        raw = yf.download(missing, start=DL_START, end="2026-09-17", auto_adjust=True,
                          progress=False, group_by="ticker", threads=True)
        for t in missing:
            try:
                d = (raw[t] if len(missing) > 1 else raw)[["Open", "High", "Low", "Close"]].dropna()
            except KeyError:
                continue
            if len(d) > 300:
                d.to_parquet(CACHE_DIR / f"{t}.parquet")
                ohlc[t] = d

    fehlend = [t for t in tickers if t not in ohlc]
    if fehlend:
        print(f"WARNUNG: {len(fehlend)} von {len(tickers)} Tickern ohne Kurse "
              f"(weder Cache noch Abruf): {', '.join(fehlend[:8])}"
              f"{' ...' if len(fehlend) > 8 else ''}", flush=True)
    return ohlc


def model_trades(ou_config, ou_portfolio, mk, tickers, ohlc):
    panel = pd.DataFrame({t: ohlc[t]["Close"] for t in tickers if t in ohlc}).sort_index()
    bench = yf.download(ou_config.UNIVERSES[mk]["benchmark"], start=DL_START, end="2026-09-17",
                        auto_adjust=True, progress=False)["Close"]
    if isinstance(bench, pd.DataFrame):
        bench = bench.iloc[:, 0]
    regime = (bench > bench.ewm(span=200).mean()).reindex(panel.index).ffill().fillna(False)
    rr = 1.5 if mk == "sp500" else None
    _, trades = ou_portfolio.simulate_bracket_portfolio(
        panel, list(panel.columns), START, END, stop_sigma=pb.OU_MODELL_STOP_SIGMA, rr_ratio=rr,
        be_trigger_r=pb.OU_MODELL_BE_TRIGGER_R, allowed_directions=(1,), regime_filter=regime,
        risk_pct=pb.OU_MODELL_RISK_PCT, max_total_risk_pct=pb.OU_MODELL_MAX_TOTAL_RISK_PCT)
    std20 = panel.rolling(ou_config.BB_LOOKBACK).std()
    rows = []
    for t in trades:
        sd = std20.loc[t["entry_date"], t["ticker"]] * pb.OU_MODELL_STOP_SIGMA
        rows.append({"market": mk, "ticker": t["ticker"], "d0": t["entry_date"], "c0": t["entry_price"],
                     "stop_dist": sd, "rr": rr, "engine_R": (t["exit_price"] - t["entry_price"]) / sd,
                     "engine_reason": t["reason"]})
    return rows


def replay(tr, bars, variant, max_hold, be_r):
    """Einen Trade in einer Ausfuehrungsvariante durchspielen. Rueckgabe dict oder None (faellt aus)."""
    c0, sd = tr["c0"], tr["stop_dist"]
    sl0 = c0 - sd
    be_level = c0 + be_r * sd
    tp = c0 + tr["rr"] * sd if tr["rr"] else None
    after = bars[bars.index > tr["d0"]]
    if after.empty:
        return None
    next_day = variant != "A"
    intraday_sl = variant in ("C", "D", "C$", "D$")
    intraday_be_tp = variant in ("D", "D$")
    costs = variant.endswith("$")

    if next_day:
        o1 = after["Open"].iloc[0]
        if abs(o1 - c0) / c0 > DEV_GATE or o1 <= sl0:
            return None  # Deviation-Gate bzw. Signal schon tot -- live ebenfalls kein Entry
        entry, path, entry_day_idx = o1, after, 0
    else:
        entry, path, entry_day_idx = c0, after, -1
    if costs:
        entry *= 1 + COST_ENTRY_BPS / 1e4
    risk = entry - sl0
    if risk <= 0:
        return None

    # Broker-seitiger BE/TP (Variante D) haengt live am FILL-Preis der Position
    # (Solo-Bot/EK setzen ihn relativ zum Einstieg); Re-Scan-Logik (A/B/C) am
    # Signalpreis c0, weil das Modell selbst so rechnet.
    raw_entry = entry / (1 + COST_ENTRY_BPS / 1e4) if costs else entry
    if intraday_be_tp:
        be_level = raw_entry + be_r * (raw_entry - sl0)
        tp = raw_entry + tr["rr"] * (raw_entry - sl0) if tr["rr"] else None
        be_price = raw_entry
    else:
        be_price = c0
    stop = sl0
    be_moved = False
    exit_px, reason, days = None, None, 0
    for i, (dt, b) in enumerate(path.iterrows()):
        days = i + 1 if not next_day else i + 1
        # --- Intraday-Stops (Broker) -----------------------------------------
        if intraday_sl:
            active_stop = stop if intraday_be_tp else sl0
            if b["Low"] <= active_stop:
                exit_px = min(b["Open"], active_stop)
                reason = "BE" if (intraday_be_tp and be_moved) else "SL"
                break
        if intraday_be_tp and tp is not None and b["High"] >= tp:
            exit_px, reason = max(b["Open"], tp), "TP"
            break
        if intraday_be_tp and not be_moved and b["High"] >= be_level:
            be_moved, stop = True, be_price  # greift ab dem naechsten Bar (Reihenfolge im Bar unbekannt)
        # --- Schlusskurs-Logik (Modell / Re-Scan) ------------------------------
        close = b["Close"]
        if not intraday_be_tp and not be_moved and close >= be_level:
            be_moved = True
        if not intraday_be_tp and be_moved and close <= be_price:
            exit_px, reason = close, "BE"
            break
        if not intraday_sl and close <= sl0:
            exit_px, reason = close, "SL"
            break
        if not intraday_be_tp and tp is not None and close >= tp:
            exit_px, reason = close, "TP"
            break
        if days >= max_hold:
            exit_px, reason = close, "MaxHold"
            break
    if exit_px is None:
        return None  # noch offen am Datenende
    if costs:
        exit_px *= 1 - COST_EXIT_BPS / 1e4
        cal_days = max((path.index[min(days - 1, len(path) - 1)] - path.index[0]).days, 1)
        swap = entry * SWAP_BPS_DAY / 1e4 * cal_days
    else:
        swap = 0.0
    R = (exit_px - entry - swap) / risk
    return {"R": R, "reason": reason, "days": days}


def stats(r):
    r = np.asarray(r)
    if len(r) == 0:
        return {}
    w, l = r[r > 0].sum(), -r[r < 0].sum()
    return {"n": int(len(r)), "avg_R": round(float(r.mean()), 4), "sum_R": round(float(r.sum()), 1),
            "hit": round(float((r > 0).mean()), 3), "PF": round(float(w / l), 3) if l else None}


def main():
    ou_config, ou_portfolio, uni = load_universe()
    all_t = [t for v in uni.values() for t in v]
    print("Ticker:", {k: len(v) for k, v in uni.items()}, flush=True)
    ohlc = download(all_t)
    print("OHLC geladen:", len(ohlc), flush=True)
    trades = []
    for mk, tick in uni.items():
        trades += model_trades(ou_config, ou_portfolio, mk, [t for t in tick if t in ohlc], ohlc)
    print("Modell-Trades:", len(trades), flush=True)

    variants = ["A", "B", "C", "D", "C$", "D$"]
    res = {v: [] for v in variants}
    for tr in trades:
        bars = ohlc[tr["ticker"]]
        for v in variants:
            out = replay(tr, bars, v, ou_config.MAX_HOLDING_DAYS, pb.OU_MODELL_BE_TRIGGER_R)
            if out is not None:
                res[v].append({**out, "d0": tr["d0"], "ticker": tr["ticker"], "market": tr["market"]})

    summary = {"config": {"start": START, "end": END, "stop_sigma": pb.OU_MODELL_STOP_SIGMA,
                          "be_trigger_r": pb.OU_MODELL_BE_TRIGGER_R, "tp_sp500": 1.5,
                          "cost_entry_bps": COST_ENTRY_BPS, "cost_exit_bps": COST_EXIT_BPS,
                          "swap_bps_day": SWAP_BPS_DAY, "dev_gate": DEV_GATE,
                          "tickers": {k: len(v) for k, v in uni.items()}},
               "engine_check": stats([t["engine_R"] for t in trades]), "variants": {}}
    for v in variants:
        d = pd.DataFrame(res[v])
        d["year"] = pd.to_datetime(d["d0"]).dt.year
        by_year = {int(y): stats(g["R"]) for y, g in d.groupby("year")}
        reasons = d["reason"].value_counts(normalize=True).round(3).to_dict()
        # rollierende 65-Trade-Fenster (Groesse der Live-Stichprobe Aug-Sep)
        roll = d.sort_values("d0")["R"].rolling(65).sum().dropna()
        summary["variants"][v] = {"all": stats(d["R"]), "by_year": by_year, "exit_mix": reasons,
                                  "roll65_sumR_pct": {p: round(float(roll.quantile(p / 100)), 1) for p in (5, 10, 25, 50, 75, 90)},
                                  "roll65_share_le_minus17_6": round(float((roll <= -17.6).mean()), 4),
                                  "roll88_share_le_0": round(float((d.sort_values('d0')['R'].rolling(88).sum().dropna() <= 0).mean()), 4)}
        d.to_csv(OUT.with_name(f"execution_costs_20260916_trades_{v.replace('$', 'cost')}.csv"), index=False)
    OUT.write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
