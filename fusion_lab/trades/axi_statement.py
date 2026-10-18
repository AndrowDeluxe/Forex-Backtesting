"""Liest Axi-MT4-Statements (PDF oder .htm) in Tickets, Balance-Buchungen und
Positionen -- Strang 0 des Dachprojekts (Trade-Inventur 2025).

Eigenheiten der Axi-Statements, die hier abgefangen werden:
- Betraege mit Leerzeichen als Tausendertrenner ("1 243.13"), im PDF teils
  umgebrochen ("-1\\n000.00").
- Seitenkopf/-fuss ("7/21/26, 11:03 PM Statement: ..." / "file:///...") kann
  mitten in einem Datensatz stehen.
- Die SL-Spalte ist der Stop beim SCHLIESSEN (nach BE-Nachziehen), nicht das
  Anfangsrisiko.
- "Data Truncation DDMMYYYY <betrag>" ist der zusammengefasste Saldo der
  abgeschnittenen Historie bis DDMMYYYY -- als Startsaldo zu diesem Datum
  behandeln, nicht zum Buchungsdatum (das liegt teils Monate spaeter).
- Der "Balance"-Wert im Summary ist der Kontostand bei Erstellung (2026), das
  Statement deckt aber nur 2025 ab -- deshalb wird er NICHT gegengeprueft.

Teilschliessungen: MT4 spaltet eine Position in Tickets mit identischer
Eroeffnungszeit und -kurs ("to #/from #"). `positions()` fasst sie zusammen.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

MONEY = r"-?\d{1,3}(?:\s\d{3})*\.\d{2}"
_TS = r"\d{4}\.\d{2}\.\d{2}\s\d{2}:\d{2}:\d{2}"
_NUM = r"\d+(?:\.\d+)?"

_PAGE_NOISE = re.compile(
    r"^\s*(?:\d{1,2}/\d{1,2}/\d{2},\s.*Statement:.*|file:///.*|"
    r"AxiCorp Financial Services Pty Ltd|"
    r"Ticket\s+Open Time\s+Type.*)\s*$",
    re.M,
)
_RECORD_START = re.compile(rf"(?m)^(?=\d{{8}}\s+{_TS}\s+(?:buy|sell|balance)\b)")
_TRADE = re.compile(
    rf"^(?P<ticket>\d{{8}})\s+(?P<open_time>{_TS})\s+(?P<side>buy|sell)\s+"
    rf"(?P<lots>{_NUM})\s+(?P<symbol>\S+)\s+(?P<open_price>{_NUM})\s+"
    rf"(?P<sl>{_NUM})\s+(?P<tp>{_NUM})\s+(?P<close_time>{_TS})\s+"
    rf"(?P<close_price>{_NUM})\s+(?P<commission>{MONEY})\s+(?P<taxes>{MONEY})\s+"
    rf"(?P<swap>{MONEY})\s+(?P<profit>{MONEY})(?P<rest>.*)$",
    re.S,
)
_BALANCE = re.compile(
    rf"^(?P<ticket>\d{{8}})\s+(?P<time>{_TS})\s+balance\s+(?P<comment>.*?)"
    rf"(?<!\S)(?P<amount>{MONEY})\s*$",
    re.S,
)
_TOTALS_TAIL = re.compile(rf"(?:\s+(?<!\S){MONEY}){{4}}\s*$")


def money(s: str) -> float:
    return float(re.sub(r"\s", "", s))


def _ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(re.sub(r"\s+", " ", s).replace(".", "-", 2))


@dataclass
class Statement:
    account: str
    trades: pd.DataFrame
    balances: pd.DataFrame
    totals: dict = field(default_factory=dict)

    def verify(self) -> None:
        """Bricht ab, wenn die geparsten Summen nicht exakt den Fusszeilen
        des Statements entsprechen (Plan: Gegenprobe Pflicht)."""
        t, b = self.trades, self.balances
        checks = {
            "commission": (t["commission"].sum(), self.totals.get("commission")),
            "swap": (t["swap"].sum(), self.totals.get("swap")),
            "profit": (t["profit"].sum(), self.totals.get("profit")),
            "closed_pl": (t[["commission", "taxes", "swap", "profit"]].sum().sum(),
                          self.totals.get("closed_pl")),
            "deposit_withdrawal": (b["amount"].sum(), self.totals.get("deposit_withdrawal")),
        }
        bad = {k: v for k, v in checks.items() if v[1] is None or abs(v[0] - v[1]) > 0.005}
        if bad:
            detail = ", ".join(f"{k}: geparst {v[0]:.2f} vs Statement {v[1]}" for k, v in bad.items())
            raise ValueError(f"Konto {self.account}: Gegenprobe fehlgeschlagen ({detail})")


def _clean(text: str) -> str:
    return _PAGE_NOISE.sub("", text.replace("\r", ""))


def parse_text(text: str) -> Statement:
    text = _clean(text)
    acc = re.search(r"Account:\s*(\d+)", text)
    account = acc.group(1) if acc else "?"

    start = text.index("Closed Transactions:")
    end = text.index("Closed P/L:", start)
    section = text[start:end]
    tail = _TOTALS_TAIL.search(section)
    if not tail:
        raise ValueError(f"Konto {account}: Summenzeile der Closed Transactions nicht gefunden")
    tot = re.findall(rf"(?<!\S){MONEY}", tail.group(0))
    section = section[: tail.start()]

    trades, balances = [], []
    for rec in _RECORD_START.split(section)[1:]:
        rec = rec.strip()
        if m := _TRADE.match(rec):
            d = m.groupdict()
            rest = d.pop("rest")
            trades.append({
                "account": account,
                "ticket": int(d["ticket"]),
                "open_time": _ts(d["open_time"]),
                "close_time": _ts(d["close_time"]),
                "side": d["side"],
                "lots": float(d["lots"]),
                "symbol": d["symbol"].lower(),
                "open_price": float(d["open_price"]),
                "sl": float(d["sl"]),
                "tp": float(d["tp"]),
                "close_price": float(d["close_price"]),
                "commission": money(d["commission"]),
                "taxes": money(d["taxes"]),
                "swap": money(d["swap"]),
                "profit": money(d["profit"]),
                "exit_tag": (re.search(r"\[(sl|tp)\]", rest) or [None, None])[1],
                "to_ticket": int(x.group(1)) if (x := re.search(r"to #(\d+)", rest)) else None,
                "from_ticket": int(x.group(1)) if (x := re.search(r"from #(\d+)", rest)) else None,
            })
        elif m := _BALANCE.match(rec):
            comment = re.sub(r"\s+", " ", m["comment"]).strip()
            booked = _ts(m["time"])
            effective = booked
            if tr := re.match(r"Data Truncation (\d{2})(\d{2})(\d{4})", comment):
                effective = pd.Timestamp(f"{tr[3]}-{tr[2]}-{tr[1]} 23:59:59")
            balances.append({
                "account": account, "ticket": int(m["ticket"]), "time": booked,
                "effective_time": effective, "comment": comment, "amount": money(m["amount"]),
            })
        else:
            raise ValueError(f"Konto {account}: Datensatz nicht lesbar: {rec[:120]!r}")

    def _after(label: str) -> float | None:
        x = re.search(rf"{re.escape(label)}\s*({MONEY})", text)
        return money(x.group(1)) if x else None

    totals = {
        "commission": money(tot[0]), "taxes": money(tot[1]),
        "swap": money(tot[2]), "profit": money(tot[3]),
        "closed_pl": _after("Closed P/L:"),
        "deposit_withdrawal": _after("Deposit/Withdrawal:"),
        "floating_pl": _after("Floating P/L:"),
    }
    bal_cols = ["account", "ticket", "time", "effective_time", "comment", "amount"]
    return Statement(account, pd.DataFrame(trades), pd.DataFrame(balances, columns=bal_cols), totals)


def _htm_to_text(raw: str) -> str:
    """Eine Tabellenzeile = eine Textzeile, damit derselbe Parser greift."""
    raw = re.sub(r"(?is)<(script|style).*?</\1>", "", raw)
    rows = re.split(r"(?i)</tr\s*>", raw)
    lines = []
    for row in rows:
        cells = [html.unescape(re.sub(r"<[^>]+>", " ", c)) for c in re.split(r"(?i)</t[dh]\s*>", row)]
        line = " ".join(" ".join(c.split()) for c in cells if c.strip())
        if line:
            lines.append(line)
    return "\n".join(lines)


def read_statement(path: Path) -> Statement:
    path = Path(path)
    if path.suffix.lower() in (".htm", ".html"):
        text = _htm_to_text(path.read_text(encoding="utf-8", errors="replace"))
    elif path.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        text = "\n".join(p.extract_text() or "" for p in PdfReader(str(path)).pages)
    else:
        raise ValueError(f"Unbekanntes Format: {path}")
    st = parse_text(text)
    st.verify()
    return st


def positions(trades: pd.DataFrame) -> pd.DataFrame:
    """Teilschliessungen zu Positionen: gleiche Eroeffnungszeit, Symbol,
    Richtung und Eroeffnungskurs je Konto = eine Position."""
    if trades.empty:
        return trades
    t = trades.copy()
    t["net"] = t[["commission", "taxes", "swap", "profit"]].sum(axis=1)
    key = ["account", "open_time", "symbol", "side", "open_price"]
    g = t.sort_values("close_time").groupby(key, sort=False)
    pos = g.agg(
        first_ticket=("ticket", "min"),
        n_tickets=("ticket", "size"),
        lots_total=("lots", "sum"),
        close_time=("close_time", "max"),
        gross=("profit", "sum"),
        costs=("commission", "sum"),
        swap=("swap", "sum"),
        net=("net", "sum"),
        last_exit_tag=("exit_tag", "last"),
    ).reset_index()
    pos["hold_hours"] = (pos["close_time"] - pos["open_time"]).dt.total_seconds() / 3600
    return pos.sort_values(["account", "open_time"]).reset_index(drop=True)


def equity_at(st: Statement) -> pd.Series:
    """Kontostand vor jeder Position (Eroeffnungszeitpunkt): Startsaldo +
    Buchungen + bis dahin geschlossene Ergebnisse. Ignoriert Floating."""
    pos = positions(st.trades)
    t = st.trades.assign(net=st.trades[["commission", "taxes", "swap", "profit"]].sum(axis=1))
    out = []
    for ot in pos["open_time"]:
        bal = st.balances.loc[st.balances["effective_time"] <= ot, "amount"].sum()
        closed = t.loc[t["close_time"] <= ot, "net"].sum()
        out.append(bal + closed)
    return pd.Series(out, index=pos.index, name="equity_at_open")
