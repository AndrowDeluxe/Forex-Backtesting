"""Einlesen der MT5-Strategietester-Berichte des Quantum Valkyrie EA.

Valkyrie arbeitet mit Buy-/Sell-Stop-Orders (gesetzt zur M15-Grenze), haelt
mehrere Positionen gleichzeitig (Hedging-Konto) und schliesst fast nur ueber den
nachgezogenen SL. Der Deals-Teil des Berichts nennt keine Positions-ID; die
Zuordnung Ausstieg -> Einstieg laeuft deshalb ueber den Gewinn:
Einstiegskurs = Ausstiegskurs - Gewinn / (Volumen * 100 * Richtung), dann die
offene Position gleicher Richtung/Volumen mit diesem Kurs.

- `read_orders(html)`: eine Zeile je Pending-Order (gesetzt, Level, SL, TP,
  Status, Erledigt-Zeit).
- `read_positions(html)`: eine Zeile je Position (Einstieg aus Order, Ausstieg,
  Gewinn, Lot) inkl. der ausloesenden Order.

Alle Zeiten Brokerzeit (EET mit EU-Sommerzeit), tz-naiv.
"""

from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

from mt5_quantum_omnigold.data_mt5 import _num, _read_text, _section

BOTS = Path(r"C:\Users\andre\OneDrive\Dokumente\Unternehmen\Trading Investments\Institutial Mandate\Bots")
REPORTS = {  # Name -> (Datei, Tick-Modell, Zeitraum laut Lauf)
    "ohlc_2020_2023": (BOTS / "Report.html", "ohlc"),
    "ticks_2020_2023": (BOTS / "Quantum Valkyrie" / "ReportTester-5057577303_1.html", "ticks"),
    "ohlc_2023_2026": (BOTS / "Quantum Valkyrie" / "ReportTester-5057577303_2.html", "ohlc"),
}
RESULTS = Path(__file__).parent / "results"
_TS = "%Y.%m.%d %H:%M:%S"


def _tables(path: Path) -> pd.DataFrame:
    return pd.read_html(StringIO(_read_text(path)))[1]


def read_orders(path: Path) -> pd.DataFrame:
    o = _section(_tables(path), "Orders", "Trades").copy()
    o.columns = ["t_set", "order", "sym", "typ", "vol", "vol2", "price", "sl", "tp", "t_done", "t_done2", "status", "cmt"]
    o = o[o.typ.astype(str).str.contains("stop")].copy()
    for c in ["price", "sl", "tp"]:
        o[c] = _num(o[c])
    o["lot"] = _num(o.vol.astype(str).str.split("/").str[0])
    o["order"] = o.order.astype(int)
    o["t_set"] = pd.to_datetime(o.t_set, format=_TS)
    o["t_done"] = pd.to_datetime(o.t_done, format=_TS)
    o["s"] = np.where(o.typ.str.startswith("buy"), 1, -1)
    o["sl_dist"] = (o.price - o.sl) * o.s
    o["tp_dist"] = (o.tp - o.price) * o.s
    return o[["t_set", "order", "typ", "s", "lot", "price", "sl", "tp", "sl_dist", "tp_dist", "t_done", "status"]].reset_index(drop=True)


def read_positions(path: Path) -> pd.DataFrame:
    d = _section(_tables(path), "Trades", None).copy()
    for c in ["Volumen", "Preis", "Gewinn", "Swap", "Kontostand"]:
        d[c] = _num(d[c])
    d["Zeit"] = pd.to_datetime(d.Zeit, format=_TS)
    d["Auftrag"] = pd.to_numeric(d.Auftrag, errors="coerce")
    d = d[d.Symbol == "XAUUSD"]
    opened, rows = [], []
    for x in d.itertuples():
        if x.Richtung == "in":
            opened.append(dict(order=int(x.Auftrag), s=1 if x.Typ == "buy" else -1, lot=x.Volumen, p_in=x.Preis, t_in=x.Zeit))
            continue
        s = -1 if x.Typ == "buy" else 1          # Ausstieg "sell" schliesst eine Long-Position
        p_in = x.Preis - x.Gewinn / (x.Volumen * 100 * s)
        cand = [k for k, p in enumerate(opened) if p["s"] == s and abs(p["lot"] - x.Volumen) < 1e-9]
        if not cand:
            raise ValueError(f"Keine offene Position fuer Ausstieg {x.Zeit}")
        k = min(cand, key=lambda k: abs(opened[k]["p_in"] - p_in))
        p = opened.pop(k)
        rows.append(dict(**p, t_out=x.Zeit, p_out=x.Preis, pnl=x.Gewinn + (x.Swap if pd.notna(x.Swap) else 0),
                         balance=x.Kontostand, exit=str(x.Kommentar)[:2], match_err=abs(p["p_in"] - p_in)))
    pos = pd.DataFrame(rows)
    pos["usd"] = (pos.p_out - pos.p_in) * pos.s     # lot-neutral, $ je Unze
    return pos.sort_values("t_in").reset_index(drop=True)


def load_all(refresh: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Alle Berichte: Orders und Positionen mit Spalte `run`."""
    fo, fp = RESULTS / "orders.parquet", RESULTS / "positions.parquet"
    if fo.exists() and fp.exists() and not refresh:
        return pd.read_parquet(fo), pd.read_parquet(fp)
    RESULTS.mkdir(parents=True, exist_ok=True)
    os_, ps = [], []
    for run, (path, model) in REPORTS.items():
        os_.append(read_orders(path).assign(run=run, model=model))
        ps.append(read_positions(path).assign(run=run, model=model))
    o, p = pd.concat(os_, ignore_index=True), pd.concat(ps, ignore_index=True)
    o.to_parquet(fo)
    p.to_parquet(fp)
    return o, p


if __name__ == "__main__":
    o, p = load_all(refresh=True)
    for run, g in p.groupby("run"):
        oo = o[o.run == run]
        print(f"{run}: {len(oo)} Orders {oo.status.value_counts().to_dict()}, {len(g)} Positionen, "
              f"{g.t_in.min():%Y-%m-%d} -> {g.t_out.max():%Y-%m-%d}, max Zuordnungsfehler {g.match_err.max():.3f}, "
              f"Endstand {g.sort_values('t_out').balance.iloc[-1]:,.2f}")
