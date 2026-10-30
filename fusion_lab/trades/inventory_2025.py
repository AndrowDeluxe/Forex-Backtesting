"""Trade-Inventur 2025: Wer hat den Gewinn getragen? (Strang 0, Dachprojekt)

    python -m fusion_lab.trades.inventory_2025

Liest alle Axi-Statements aus fusion_lab/raw/trades/axi/, fasst Teil-
schliessungen zu Positionen zusammen und zerlegt den Netto-Gewinn nach Konto,
Instrument, Richtung, Session, Haltedauer und Monat. Ergebnis in $ und in %
vom Kontostand bei Eroeffnung (kein R: die Statements zeigen nur den letzten SL).
Konto 6059497 (EK-Kopierkonto) zaehlt in den Summen, nicht in den Aufschluesselungen.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from fusion_lab._secrets import RAW_DIR
from fusion_lab.trades.axi_statement import equity_at, positions, read_statement

AXI_DIR = RAW_DIR / "trades" / "axi"
OUT = Path(__file__).resolve().parent.parent / "data" / "trades_2025.parquet"
COPY_ACCOUNTS = {"6059497"}

# Richtung gegen den USD = profitiert von schwachem Dollar
USD_BASE = ("usdjpy", "usdcad", "usdchf")


def _session(ts: pd.Timestamp) -> str:
    """Grobe Session nach Eroeffnungszeit (Serverzeit Axi = UTC+2/+3)."""
    h = ts.hour
    if h < 9:
        return "Asia"
    if h < 15:
        return "London"
    if h < 22:
        return "NY"
    return "Spaet"


def _usd_view(symbol: str, side: str) -> str:
    s = symbol.split(".")[0]
    if "usd" not in s:
        return "ohne USD"
    short_usd = (side == "sell") if s.startswith(USD_BASE) else (side == "buy")
    return "gegen USD" if short_usd else "fuer USD"


def build() -> pd.DataFrame:
    frames = []
    for p in sorted(AXI_DIR.glob("*.pdf")) + sorted(AXI_DIR.glob("*.htm")):
        st = read_statement(p)
        pos = positions(st.trades)
        pos["equity_at_open"] = equity_at(st).values
        frames.append(pos)
    pos = pd.concat(frames, ignore_index=True)
    pos = pos[pos["close_time"].dt.year == 2025].copy()
    pos["instrument"] = pos["symbol"].str.split(".").str[0]
    pos["pct"] = 100 * pos["net"] / pos["equity_at_open"].where(pos["equity_at_open"] > 0)
    pos["session"] = pos["open_time"].map(_session)
    pos["hold"] = pd.cut(pos["hold_hours"], [-1, 4, 24, 1e9], labels=["<4h", "4-24h", ">1 Tag"])
    pos["usd"] = [_usd_view(s, d) for s, d in zip(pos["symbol"], pos["side"])]
    pos["half"] = (pos["open_time"].dt.month > 6).map({False: "H1", True: "H2"})
    pos["month"] = pos["open_time"].dt.to_period("M").astype(str)
    pos["copy_account"] = pos["account"].isin(COPY_ACCOUNTS)
    return pos


def breakdown(pos: pd.DataFrame, by) -> pd.DataFrame:
    total = pos["net"].sum()
    g = pos.groupby(by, observed=True)
    out = g.agg(n=("net", "size"), net=("net", "sum"), avg_pct=("pct", "mean"))
    out["hit"] = g["net"].apply(lambda x: (x > 0).mean())
    wins = g["net"].apply(lambda x: x[x > 0].sum())
    losses = g["net"].apply(lambda x: -x[x < 0].sum())
    out["pf"] = wins / losses.where(losses > 0)
    out["share"] = out["net"] / total
    out["net_ohne_top3"] = g["net"].apply(lambda x: x.sum() - x.nlargest(3).clip(lower=0).sum())
    return out.sort_values("net", ascending=False).round(2)


def main() -> None:
    pos = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pos.to_parquet(OUT)
    pd.set_option("display.width", 160)
    print(f"Positionen 2025: {len(pos)}  Netto: {pos['net'].sum():,.2f} $\n")
    print(breakdown(pos, "account"), "\n")
    core = pos[~pos["copy_account"]]
    print(f"Ohne Kopierkonto {sorted(COPY_ACCOUNTS)}: {len(core)} Positionen, {core['net'].sum():,.2f} $\n")
    for by in ["instrument", "side", "session", "hold", "usd", ["half", "usd"], "month",
               ["account", "hold"]]:
        print(breakdown(core, by), "\n")


if __name__ == "__main__":
    main()
