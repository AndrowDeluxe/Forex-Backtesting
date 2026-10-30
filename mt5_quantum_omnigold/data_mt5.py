"""Einlesen der MT5-Strategietester-Ausgaben des Quantum OmniGold EA.

- `read_report(html)`: Orders + Deals des HTML-Berichts -> eine Zeile je
  Trade (Einstieg, SL/TP beim Einstieg, Ausstieg, Exit-Art, Gewinn).
  Exit-Art: "sl"/"tp" aus dem Deal-Kommentar, sonst "ea" (vom EA selbst
  geschlossen, fast immer zur vollen Minute).
- `read_log(log)`: EA-/Trade-Ausgaben des Tester-Logs als Ereignistabelle,
  je Testlauf (`run`). Das Log ist UTF-16 und kann mehrere Laeufe enthalten.

Alle Zeiten sind Brokerzeit (tz-naiv), wie im Tester.
"""

import re
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd

REPORT_DIR = Path(r"C:\Users\andre\OneDrive\Dokumente\Unternehmen\Trading Investments\Institutial Mandate\Bots\Quantum Omni Gold")
LOG_DIR = Path(r"C:\Users\andre\AppData\Roaming\MetaQuotes\Tester\E48CB66983626931D26313F2B2AC6744\Agent-127.0.0.1-3000\logs")


def _read_text(path: Path) -> str:
    raw = Path(path).read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    return raw.decode("utf-8", "ignore")


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(r"[\s\xa0]", "", regex=True), errors="coerce")


def _section(table: pd.DataFrame, name: str, next_name: str | None) -> pd.DataFrame:
    first = table[0].astype(str).str.strip()
    start = table.index[first == name][0]
    stop = table.index[first == next_name][0] if next_name else len(table)
    part = table.loc[start + 1:stop - 1].reset_index(drop=True)
    part.columns = part.iloc[0]
    part = part.iloc[1:]
    return part[part.iloc[:, 0].astype(str).str.match(r"\d{4}\.")]


def read_report(path: Path) -> pd.DataFrame:
    table = pd.read_html(StringIO(_read_text(path)))[1]
    orders = _section(table, "Orders", "Trades")
    deals = _section(table, "Trades", None)

    orders = orders.iloc[:, [0, 7, 8, 12]]
    orders.columns = ["t", "sl", "tp", "cmt"]
    orders = orders[orders.cmt.astype(str).str.startswith("Quantum")]
    orders["t"] = pd.to_datetime(orders.t, format="%Y.%m.%d %H:%M:%S")
    orders[["sl", "tp"]] = orders[["sl", "tp"]].apply(_num)

    deals = deals[deals.Symbol == "XAUUSD"].copy()
    for c in ["Volumen", "Preis", "Swap", "Gewinn", "Kontostand"]:
        deals[c] = _num(deals[c])
    deals["Zeit"] = pd.to_datetime(deals.Zeit, format="%Y.%m.%d %H:%M:%S")
    ins = deals[deals.Richtung == "in"].reset_index(drop=True)
    outs = deals[deals.Richtung == "out"].reset_index(drop=True)
    if len(ins) != len(outs):
        raise ValueError(f"{len(ins)} Einstiege, aber {len(outs)} Ausstiege")

    t = pd.DataFrame({
        "t_in": ins.Zeit, "side": ins.Typ, "lot": ins.Volumen, "p_in": ins.Preis,
        "t_out": outs.Zeit, "p_out": outs.Preis,
        "pnl": outs.Gewinn + outs.Swap, "balance": outs.Kontostand,
        "cmt": outs.Kommentar.fillna("").astype(str),
    })
    t = t.merge(orders[["t", "sl", "tp"]], left_on="t_in", right_on="t", how="left").drop(columns="t")
    sign = np.where(t.side == "buy", 1, -1)
    t["sl_dist"] = (t.p_in - t.sl) * sign
    t["tp_dist"] = (t.tp - t.p_in) * sign
    t["exit"] = np.select([t.cmt.str.startswith("sl"), t.cmt.str.startswith("tp")], ["sl", "tp"], "ea")
    return t


_TS = r"(\d{4}\.\d\d\.\d\d \d\d:\d\d:\d\d)"
_PATTERNS = [
    ("atr", re.compile(_TS + r"\s+ATR current: ([\d.]+)"), lambda m: dict(value=float(m[2]))),
    ("line", re.compile(_TS + r"\s+recalculate (res|support) price: ([\d.]+)"),
     lambda m: dict(kind=m[2], value=float(m[3]))),
    ("open", re.compile(_TS + r"\s+market (buy|sell) ([\d.]+) XAUUSD sl: ([\d.]+) tp: ([\d.]+) \(([\d.]+) / ([\d.]+)"),
     lambda m: dict(kind=m[2], lot=float(m[3]), sl=float(m[4]), tp=float(m[5]), bid=float(m[6]), ask=float(m[7]))),
    ("close", re.compile(_TS + r"\s+market (buy|sell) ([\d.]+) XAUUSD, close #\d+ \(([\d.]+) / ([\d.]+)"),
     lambda m: dict(kind=m[2], lot=float(m[3]), bid=float(m[4]), ask=float(m[5]))),
    ("modify", re.compile(_TS + r"\s+position modified \[#\d+ (buy|sell) ([\d.]+) XAUUSD ([\d.]+) sl: ([\d.]+) tp: ([\d.]+)"),
     lambda m: dict(kind=m[2], lot=float(m[3]), value=float(m[4]), sl=float(m[5]), tp=float(m[6]))),
    ("stop", re.compile(_TS + r"\s+(stop loss|take profit) triggered"), lambda m: dict(kind=m[2][:4].strip())),
    ("info", re.compile(_TS + r"\s+>>>\s*(.*)"), lambda m: dict(kind=m[2][:80])),
]


def read_log(path: Path) -> pd.DataFrame:
    rows, run = [], -1
    for line in _read_text(path).splitlines():
        if "testing of Experts\\Quantum OmniGold" in line:
            run += 1
            continue
        if run < 0 or ("Trade\t" not in line and "Quantum OmniGold EA" not in line):
            continue
        for ev, rx, fields in _PATTERNS:
            m = rx.search(line)
            if m and (ev not in ("open", "close") or "Trade\t" in line):
                rows.append(dict(run=run, t=m[1], ev=ev, **fields(m)))
                break
    e = pd.DataFrame(rows)
    e["t"] = pd.to_datetime(e.t, format="%Y.%m.%d %H:%M:%S")
    return e


REPORTS = {  # Lauf 1: 01/2022-07/2023, Lauf 2: 07/2023-10/2026 (neu ab 100k)
    1: "ReportTester-5057577303.html",
    2: "ReportTester-5057577303_1.html",
}
TRADES = Path(__file__).parent / "results" / "mt5_trades.parquet"


def read_all_reports() -> pd.DataFrame:
    return pd.concat([read_report(REPORT_DIR / f).assign(run=r) for r, f in REPORTS.items()], ignore_index=True)


if __name__ == "__main__":
    tr = read_all_reports()
    tr.to_parquet(TRADES)
    for r, g in tr.groupby("run"):
        print(f"Lauf {r}:", len(g), "Trades, Endstand", g.balance.iloc[-1], g.exit.value_counts().to_dict())
    ev = read_log(LOG_DIR / "20261019.log")
    print(ev.groupby("run").agg(von=("t", "min"), bis=("t", "max"), n=("ev", "size"),
                                opens=("ev", lambda s: (s == "open").sum())))
