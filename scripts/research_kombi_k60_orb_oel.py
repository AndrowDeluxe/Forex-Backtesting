"""Kombination: Noise-Area-K60 (NASDAQ) + Oel-gefilterte ORB (SP500 + NASDAQ) auf einem TTP-Konto.

Nutzerfrage 2026-10-16: "Wie wuerde eine Kombination dieser Strategie mit der Oel-validierten
ORB-Strategie aussehen?" Beschreibend, keine neue Auswahl -- alle Bausteine sind eingefroren:
  K60     research_noise_area_k60_ttp.py: 1 % Risiko, SL 1 sigma, Exit 15:55, TTP-Kosten 1,32 bps
  ORB O1  research_orb_oel_filter.py Option 1 (IS-validiert): Basis-ORB, nur wenn Oel 09:00-09:45
          gegen die Ausbruchsrichtung lief (Lock orb_oel_filter_is_20261012)
  ORB O2  Option 2 (an 2026 angepasst, explorativ): K20-Regime -> Trend-Tage + Oel gegen
          (Lock orb_oel_filter_fit2026_20261012)
ORB-R sind netto (Kosten bereits abgezogen). Jeder Trade riskiert 1 % der Equity zu Tagesbeginn.
Intraday-Tief: K60 ueber MAE (gedeckelt am SL); ORB-Verlierer mit ihrem Verlust, ORB-Gewinner
ohne Zwischentief (Naeherung, unterschaetzt das Tief leicht). TTP: Tageslimit 3 %, 7 % trailing, Ziel 10 %.
Perioden wie ueberall: IS 2016-07..2022 | OOS 2023..09/2025 | Tresor 10/2025..09/2026 (je ab 100k).

  python scripts/research_kombi_k60_orb_oel.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))

from research_noise_area_k60_sltp import PERIODS, entries  # noqa: E402
from research_noise_area_k60_ttp import EXITS, trades  # noqa: E402
from research_orb_oel_filter import BASE, INSTRUMENTS, RES, apply, load  # noqa: E402

OUT = ROOT / "noise_area_momentum" / "results"
RISK, START, DAILY_LIM, TOTAL_DD, TARGET = 0.01, 100_000.0, 0.03, 0.07, 0.10
TRESOR_END = "2026-09-30"


def orb_days(data: dict, sel: dict) -> pd.DataFrame:
    """Tagesweise ORB-P&L (Anteil Equity) und Intraday-Tief, beide Indizes summiert."""
    parts = []
    for inst in INSTRUMENTS:
        r, _ = apply(data[inst], sel[inst])
        idx = r.index.tz_localize(None) if r.index.tz is not None else r.index
        parts.append(pd.DataFrame({"pnl": r.to_numpy() * RISK, "low": np.minimum(r.to_numpy(), 0) * RISK,
                                   "n": 1}, index=idx.normalize()))
    return pd.concat(parts).groupby(level=0).sum()


def k60_days() -> pd.DataFrame:
    t, g = entries()
    tr = trades(t, g, EXITS["15:55"])
    return pd.DataFrame({"pnl": tr["lev"] * tr["ret"], "low": tr["lev"] * tr["mae"], "n": 1}, index=tr.index), g["dates"]


def account(daily: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame:
    d = daily.reindex(days).fillna(0.0)
    eq, peak, rows = START, START, []
    for day, x in d.iterrows():
        prev = eq
        low = prev * (1 + x.low)
        eq = prev * (1 + x.pnl)
        rows.append({"date": day, "equity": eq, "low": low, "peak_prev": peak,
                     "tag": low < prev * (1 - DAILY_LIM), "dd": min(low, eq) < peak * (1 - TOTAL_DD), "n": x.n})
        peak = max(peak, eq)
    return pd.DataFrame(rows).set_index("date")


def report(acc: pd.DataFrame) -> dict:
    eq = acc.equity
    r = eq.pct_change().fillna(eq.iloc[0] / START - 1)
    act = r[acc.n > 0]
    hit = acc.index[eq >= START * (1 + TARGET)]
    mon = eq.resample("ME").last()
    mon = mon / mon.shift(1).fillna(START) - 1
    return {"Trades": int(acc.n.sum()), "Endstand": round(eq.iloc[-1]), "Rendite %": (eq.iloc[-1] / START - 1) * 100,
            "CAGR %": ((eq.iloc[-1] / START) ** (252 / len(acc)) - 1) * 100,
            "MaxDD Schluss %": ((eq / eq.cummax()) - 1).min() * 100,
            "MaxDD intraday %": (acc.low / acc.peak_prev - 1).min() * 100,
            "Sharpe": r.mean() / r.std(ddof=1) * np.sqrt(252),
            "PF (Tage)": act[act > 0].sum() / -act[act < 0].sum(),
            "schlechtester Tag %": r.min() * 100, "Monate positiv": f"{(mon > 0).sum()}/{len(mon)}",
            "Tageslimit-Brueche (Tage)": int(acc.tag.sum()),
            "erster 7%-Bruch": acc.index[acc.dd][0].strftime("%Y-%m-%d") if acc.dd.any() else "nie",
            "Ziel +10 %": hit[0].strftime("%Y-%m-%d") if len(hit) else "nein"}


def pass_rate(daily: pd.DataFrame, days: pd.DatetimeIndex, horizon: int = 252) -> dict:
    out = []
    for i in range(0, len(days) - horizon, 5):          # nur Starts mit voller Laufzeit
        acc = account(daily, days[i:i + horizon])
        hit = np.where(acc.equity >= START * (1 + TARGET))[0]
        br = np.where(acc.tag | acc.dd)[0]
        th, tb = (hit[0] if len(hit) else 1e9), (br[0] if len(br) else 1e9)
        out.append(("ok", th) if th < tb else ("bruch", tb) if tb < 1e9 else ("offen", 0))
    n = len(out)
    ok = [x[1] for x in out if x[0] == "ok"]
    return {"Starts": n, "bestanden %": len(ok) / n * 100 if n else np.nan,
            "gebrochen %": sum(x[0] == "bruch" for x in out) / n * 100 if n else np.nan,
            "Median Tage bis Ziel": float(np.median(ok)) if ok else np.nan}


def main() -> None:
    k60, all_days = k60_days()
    data = load(TRESOR_END)
    sel1 = json.loads((RES / "oel_filter_is_selection.json").read_text(encoding="utf-8"))["winners"]
    sel2 = json.loads((RES / "oel_filter_fit2026_selection.json").read_text(encoding="utf-8"))["winners"]
    orb1, orb2 = orb_days(data, sel1), orb_days(data, sel2)
    orb0 = orb_days(data, {i: BASE for i in INSTRUMENTS})
    combos = {"K60 allein": k60, "ORB-Basis (ohne Oel)": orb0, "ORB Oel O1 (IS-validiert)": orb1,
              "ORB Oel O2 (2026-Fit)": orb2,
              "K60 + ORB O1": pd.concat([k60, orb1]).groupby(level=0).sum(),
              "K60 + ORB O2": pd.concat([k60, orb2]).groupby(level=0).sum()}
    rows = {}
    for name, d in combos.items():
        for per, a, b in PERIODS:
            days = all_days[(all_days >= a) & (all_days <= b)]
            rows[(name, per)] = report(account(d, days))
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 40)
    rep = pd.DataFrame(rows)
    print(rep.to_string())
    rep.to_csv(OUT / "kombi_k60_orb_oel.csv")
    for o_name, o in (("O1", orb1), ("O2", orb2)):
        j = pd.concat([k60["pnl"].rename("k60"), o["pnl"].rename("orb")], axis=1, sort=True).reindex(all_days).fillna(0)
        both = j[(j.k60 != 0) & (j.orb != 0)]
        print(f"\nKorrelation Tages-P&L K60 vs ORB {o_name}: alle Tage {j.k60.corr(j.orb):+.2f}, "
              f"Tage mit beiden ({len(both)}) {both.k60.corr(both.orb):+.2f}")
    print("\nChallenge-Simulation (Start alle 5 Tage, volle 252 Tage Laufzeit, 2016-07..2026-09):")
    pr = {name: pass_rate(d, all_days) for name, d in combos.items()}
    print(pd.DataFrame(pr).round(1).to_string())
    # nur Starts ab 2023 (juengeres Regime)
    rec = all_days[all_days >= "2023-01-01"]
    pr2 = {name: pass_rate(d, rec) for name, d in combos.items()}
    print("\n... nur Starts ab 2023 (letzter Start 09/2025):\n", pd.DataFrame(pr2).round(1).to_string())
    rows2 = []
    for o_name, o in (("O1", orb1), ("O2", orb2)):
        for r_orb in (0.25, 0.5):
            for r_k in (0.5, 1.0):
                d = pd.concat([k60 * [r_k, r_k, 1], o * [r_orb, r_orb, 1]]).groupby(level=0).sum()
                row = {"ORB": o_name, "ORB-Risiko %": r_orb, "K60-Risiko %": r_k}
                for per, a, b in PERIODS:
                    rp = report(account(d, all_days[(all_days >= a) & (all_days <= b)]))
                    row[f"{per} Endstand"] = rp["Endstand"]
                    row[f"{per} MaxDD %"] = round(rp["MaxDD intraday %"], 1)
                pa, pb2 = pass_rate(d, all_days), pass_rate(d, rec)
                row.update({"bestanden % (alle)": round(pa["bestanden %"], 1),
                            "gebrochen % (alle)": round(pa["gebrochen %"], 1),
                            "bestanden % (ab 2023)": round(pb2["bestanden %"], 1),
                            "gebrochen % (ab 2023)": round(pb2["gebrochen %"], 1),
                            "Median Tage (alle)": pa["Median Tage bis Ziel"]})
                rows2.append(row)
    ra = pd.DataFrame(rows2)
    ra.to_csv(OUT / "kombi_k60_orb_oel_risiko.csv", index=False)
    print("Risiko-Aufteilung (je Periode ab 100k; Bestehensquote: Start alle 5 Tage, 1 Jahr):")
    print(ra.to_string(index=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
