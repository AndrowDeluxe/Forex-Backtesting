"""Remy-King B4: Wie oft tragen die Live-Beine gleichzeitig dieselbe Waehrung?

    python -m scripts.research_remy_b4_exposure

Nur Messung, kein Eingriff. Quelle: die nur lesend gezogenen MT5-Abzuege
scripts/reports/mt5_2026-W*.json (alle Live-Konten). Positionen = Einstiegs-Deal
(entry 0) bis letzter Ausstiegs-Deal (entry 1) je position_id; ohne Ausstieg offen bis
zum Ende des letzten Abzugs. Exposure je Waehrung in Positionen (+1 = Waehrung long):
long EURUSD = +EUR / -USD, long XAUUSD = +XAU / -USD. Aktien/Indizes zaehlen nicht
(keine Waehrungswette), werden aber mitgezaehlt als "sonstige".
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPORTS = Path("scripts/reports")
CCY = {"EUR", "USD", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD", "XAU", "XAG"}


def legs(symbol: str) -> tuple[str, str] | None:
    s = symbol.upper().replace(".", "").replace("_", "")
    base, quote = s[:3], s[3:6]
    return (base, quote) if base in CCY and quote in CCY else None


def leg_name(comment: str) -> str:
    c = str(comment)
    return c.split()[0].split("-", 1)[-1] if "-" in c.split()[0] else c.split()[0] if c else "?"


def positions() -> pd.DataFrame:
    deals, end = [], None
    for f in sorted(REPORTS.glob("mt5_2026-W*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        end = max(end or d["to"], d["to"])
        for acc, a in d["accounts"].items():
            for x in a.get("deals") or []:
                deals.append({**x, "konto": acc})
    df = pd.DataFrame(deals).drop_duplicates(["konto", "ticket"])
    df["t"] = pd.to_datetime(df["time"], unit="s")
    rows = []
    for (acc, pid), g in df.groupby(["konto", "position_id"]):
        e = g[g["entry"] == 0]
        if e.empty:
            continue                      # vor dem ersten Abzug eroeffnet
        e = e.iloc[0]
        x = g[g["entry"] == 1]
        rows.append({"konto": acc, "symbol": e["symbol"], "side": 1 if e["type"] == 0 else -1,
                     "leg": leg_name(e["comment"]), "open": e["t"],
                     "close": x["t"].max() if len(x) else pd.Timestamp(end) + pd.Timedelta(days=1)})
    return pd.DataFrame(rows)


def main() -> None:
    pos = positions()
    pos["fx"] = pos["symbol"].map(legs)
    print(f"Positionen: {len(pos)} auf {pos['konto'].nunique()} Konten, "
          f"{pos['open'].min():%d.%m.} bis {pos['close'].max():%d.%m.%Y}; davon FX/Metall: {pos['fx'].notna().sum()}")
    grid = pd.date_range(pos["open"].min().floor("h"), pos["close"].max().ceil("h"), freq="h")
    out = []
    for acc in sorted(pos["konto"].unique()) + ["ALLE"]:
        p = pos[pos["fx"].notna() & ((pos["konto"] == acc) | (acc == "ALLE"))]
        expo = pd.DataFrame(0.0, index=grid, columns=sorted(CCY))
        for r in p.itertuples():
            alive = (grid >= r.open) & (grid < r.close)
            base, quote = r.fx
            expo.loc[alive, base] += r.side
            expo.loc[alive, quote] -= r.side
        busy = expo.abs().max(axis=1) > 0
        stacked = expo.abs().max(axis=1) >= 2
        worst = expo.abs().max()
        out.append({"Konto": acc, "Std. mit FX-Position": int(busy.sum()),
                    "Std. >=2 gleich gerichtet": int(stacked.sum()),
                    "Anteil gestapelt": stacked.sum() / max(busy.sum(), 1),
                    "max |netto| je Waehrung": worst.max(), "Waehrung": worst.idxmax(),
                    "max USD": expo["USD"].abs().max()})
        if acc == "ALLE":
            print("\nAlle Konten: Stunden mit |netto| >= 2 je Waehrung:")
            print((expo.abs() >= 2).sum().sort_values(ascending=False).head(6).to_string())
            peak = expo.abs().max(axis=1).idxmax()
            print(f"\nSpitze {peak:%d.%m.%Y %H:00}:", expo.loc[peak][expo.loc[peak] != 0].to_dict())
            alive = p[(p["open"] <= peak) & (p["close"] > peak)]
            print(alive[["konto", "symbol", "side", "leg"]].to_string(index=False))
    pd.set_option("display.width", 200)
    print()
    print(pd.DataFrame(out).round(2).to_string(index=False))
    print("\nBeine mit FX/Metall-Positionen:", pos[pos["fx"].notna()].groupby("leg").size().to_dict())


if __name__ == "__main__":
    main()
