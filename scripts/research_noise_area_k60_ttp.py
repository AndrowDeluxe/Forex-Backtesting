"""K60-Kandidat auf einem TTP-Konto: 1 % Risiko, SL 1 sigma, Ausstieg 15:55 (Nutzerauftrag 2026-10-16).

Regel wie forward_noise_area_k60.py (NASDAQ, Noise Area VM 1 / LB 90, nur 1. Ausbruch 10:00-15:30,
nur bei Korr(Oel, NASDAQ, 60 T.) < 0). Fuer Fremdkapital ergaenzt:
  SL      1 sigma (Tagesvola 14 T. bis Vortag) -> echtes 1R; im SL/TP/Haltedauer-Raster (15.10.)
          die beste Variante MIT Stop (Basis ohne Stop war besser, aber ohne Verlustdeckel)
  Exit    15:55 NY (Close der 15:54-Bar) statt 16:00: Puffer vor Kassaschluss/Close-Auktion,
          Bot-Takt -- praktische Wahl, keine Optimierung; 16:00 wird zum Vergleich mitgerechnet
  Sizing  Risiko = 1 % der AKTUELLEN Equity / SL-Abstand, Notional-Hebel <= 4
  Kosten  TTP USTEC gemessen: Spread 0,56 bps (knowledge/_data/broker_spreads_indices.json)
          + Slippage 0,45/0,30 bps = 1,32 bps je Rundturn; keine Kommission angenommen
TTP-Regeln (wie Funded-Portfolio-Bridge): 100k, Tagesverlust 3 % gg. Vortages-Schlussequity
(intraday inkl. offenem Trade), Gesamt-DD 7 % trailing vom Hoechststand, Ziel +10 %.
Beschreibend, keine neue Auswahl (VORBELASTET wie die Regel). Perioden: IS / OOS / Tresor.

  python scripts/research_noise_area_k60_ttp.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from noise_area_momentum.engine import N_BARS  # noqa: E402
from research_noise_area_k60_sltp import PERIODS, entries  # noqa: E402
from research_orb_cancel_at_sl_and_hold import ENTRY_SLIPPAGE_BPS, EXIT_SLIPPAGE_BPS  # noqa: E402

OUT = ROOT / "noise_area_momentum" / "results"
COST = (0.5618 + ENTRY_SLIPPAGE_BPS + EXIT_SLIPPAGE_BPS) * 1e-4
SL_SIGMA, RISK, MAX_LEV = 1.0, 0.01, 4.0
START, DAILY_LIM, TOTAL_DD, TARGET = 100_000.0, 0.03, 0.07, 0.10
EXITS = {"15:55": N_BARS - 6, "16:00": N_BARS - 1}


def trades(t: pd.DataFrame, g: dict, end_bar: int, sl_sigma: float | None = SL_SIGMA) -> pd.DataFrame:
    """sl_sigma=None: ohne Stop (MAE ungedeckelt); Groesse dann 1 sigma = 1 % Risiko."""
    rows = []
    for date, r in t.iterrows():
        d, e, s, px, sg = int(r.d), int(r.bar), r.side, r.entry, r.sigma
        slp = None if sl_sigma is None else px * (1 - s * sl_sigma * sg)
        hi, lo = g["high"][d, e:end_bar + 1], g["low"][d, e:end_bar + 1]
        exit_px, why, mae = g["close"][d, end_bar], "zeit", 0.0
        for k in range(len(hi)):
            adv = lo[k] if s > 0 else hi[k]
            if slp is not None and ((adv <= slp) if s > 0 else (adv >= slp)):
                exit_px, why, mae = slp, "sl", -sl_sigma * sg
                break
            mae = min(mae, s * (adv / px - 1))
        ret = s * (exit_px / px - 1) - COST
        unit = (sl_sigma or 1.0) * sg
        lev = min(MAX_LEV, RISK / unit)
        rows.append({"date": date, "side": "long" if s > 0 else "short", "einstieg": f"{9 + (30 + e) // 60}:{(30 + e) % 60:02d}",
                     "bar": e, "ret": ret, "r": ret / unit, "lev": lev, "mae": mae - COST / 2, "exit": why})
    return pd.DataFrame(rows).set_index("date")


def account(tr: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame:
    """Tagesgenaues Konto nach TTP-Regeln (ab 100k)."""
    eq, peak, rows = START, START, []
    for day in days:
        prev = eq
        if day in tr.index:
            x = tr.loc[day]
            intraday_low = prev * (1 + min(0.0, x.lev * x.mae))
            eq = prev * (1 + x.lev * x.ret)
        else:
            intraday_low = prev
        daily_breach = intraday_low < prev * (1 - DAILY_LIM)
        dd_breach = min(intraday_low, eq) < peak * (1 - TOTAL_DD)
        peak = max(peak, eq)
        rows.append({"date": day, "equity": eq, "peak": peak, "intraday_low": intraday_low,
                     "tagesbruch": daily_breach, "dd_bruch": dd_breach})
    return pd.DataFrame(rows).set_index("date")


def report(tr: pd.DataFrame, acc: pd.DataFrame) -> dict:
    eq = acc["equity"]
    pnl = eq.diff().fillna(eq.iloc[0] - START)
    tp = pnl[pnl.index.isin(tr.index)]
    w, l = tp[tp > 0], tp[tp < 0]
    dd = eq / eq.cummax() - 1
    dd_intra = acc["intraday_low"] / acc["peak"].shift(1).fillna(START) - 1
    under = (dd < 0).astype(int)
    longest = under.groupby((under == 0).cumsum()).sum().max()
    streak = (tr["ret"] < 0).astype(int)
    max_loss_streak = streak.groupby((streak == 0).cumsum()).sum().max()
    hit = acc.index[eq >= START * (1 + TARGET)]
    mon = (eq.resample("ME").last() / eq.resample("ME").last().shift(1).fillna(START) - 1)
    yrs = len(acc) / 252
    return {"Trades": len(tr), "Endstand": eq.iloc[-1], "Rendite %": (eq.iloc[-1] / START - 1) * 100,
            "CAGR %": ((eq.iloc[-1] / START) ** (1 / yrs) - 1) * 100,
            "MaxDD Schluss %": dd.min() * 100, "MaxDD intraday %": dd_intra.min() * 100,
            "laengste DD-Phase (Handelstage)": int(longest), "Trefferquote %": (tr.ret > 0).mean() * 100,
            "PF": w.sum() / -l.sum(), "Oe R je Trade": tr.r.mean(), "Oe Gewinner R": tr.r[tr.r > 0].mean(),
            "Oe Verlierer R": tr.r[tr.r < 0].mean(), "Oe Trade EUR": tp.mean(),
            "bester Trade EUR": tp.max(), "schlechtester Trade EUR": tp.min(),
            "max. Verluste in Folge": int(max_loss_streak), "SL-Quote %": (tr.exit == "sl").mean() * 100,
            "Long-Anteil %": (tr.side == "long").mean() * 100, "Oe Hebel": tr.lev.mean(),
            "Monate positiv": f"{(mon > 0).sum()} / {len(mon)}",
            "Tageslimit-Brueche": int(acc.tagesbruch.sum()), "7%-DD-Brueche": int(acc.dd_bruch.sum()),
            "Ziel +10 % erreicht am": hit[0].strftime("%Y-%m-%d") if len(hit) else "nein"}


def pass_rate(tr: pd.DataFrame, days: pd.DatetimeIndex, horizon: int = 252) -> dict:
    """Challenge an jedem Handelstag starten: Ziel vor Bruch innerhalb `horizon` Tagen?"""
    res = []
    for i in range(0, len(days) - 20, 5):
        acc = account(tr, days[i:i + horizon])
        eq = acc["equity"]
        hit = np.where(eq >= START * (1 + TARGET))[0]
        br = np.where(acc.tagesbruch | acc.dd_bruch)[0]
        t_hit = hit[0] if len(hit) else 10**9
        t_br = br[0] if len(br) else 10**9
        res.append("bestanden" if t_hit < t_br else ("gebrochen" if t_br < 10**9 else "offen"))
        if t_hit < t_br:
            res[-1] = ("bestanden", t_hit)
    n = len(res)
    passed = [x[1] for x in res if isinstance(x, tuple)]
    return {"Starts": n, "bestanden %": len(passed) / n * 100,
            "gebrochen %": sum(1 for x in res if x == "gebrochen") / n * 100,
            "offen nach 1 Jahr %": sum(1 for x in res if x == "offen") / n * 100,
            "Median Tage bis Ziel": float(np.median(passed)) if passed else np.nan}


def main() -> None:
    t, g = entries()
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    summary, monthly, trade_rows = {}, {}, []
    for ex_name, end_bar in EXITS.items():
        tr_all = trades(t, g, end_bar)
        for per, a, b in PERIODS:
            days = g["dates"][(g["dates"] >= a) & (g["dates"] <= b)]
            tr = tr_all[(tr_all.index >= a) & (tr_all.index <= b)]
            acc = account(tr, days)
            summary[(ex_name, per)] = report(tr, acc)
            if ex_name == "15:55":
                m = acc["equity"].resample("ME").last()
                monthly[per] = (m / m.shift(1).fillna(START) - 1) * 100
                trade_rows.append(tr.assign(periode=per, equity=acc["equity"].reindex(tr.index)))
        if ex_name == "15:55":
            pr = {per: pass_rate(tr_all, g["dates"][(g["dates"] >= a) & (g["dates"] <= b)]) for per, a, b in PERIODS}
    s = pd.DataFrame(summary)
    print("TTP-Konto 100k, 1 % Risiko, SL 1 sigma (jede Periode startet bei 100k):\n")
    print(s.to_string())
    print("\nChallenge-Simulation (Start alle 5 Handelstage, max. 1 Jahr, Ziel +10 % vor Bruch 3 %/Tag oder 7 % trailing):")
    print(pd.DataFrame(pr).round(1).to_string())
    mt = pd.concat(monthly, axis=1).round(2)
    mt.index = mt.index.strftime("%Y-%m")
    print("\nMonatsrenditen % (Exit 15:55):\n", mt.dropna(how="all").to_string())
    s.to_csv(OUT / "k60_ttp_summary.csv")
    mt.to_csv(OUT / "k60_ttp_monate.csv")
    pd.concat(trade_rows).to_csv(OUT / "k60_ttp_trades.csv")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
