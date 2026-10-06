"""Equity-Seite (10 Jahre, IS/OOS) - wird von orb_pdf.py importiert."""
from pathlib import Path

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

HERE = Path(__file__).parent
OOS_START = pd.Timestamp("2023-01-01")
C_SP, C_NQ, C_US, C_PF = "#2a78d6", "#eb6834", "#1baf7a", "#0b0b0b"
INK, MUTED, LINE = "#1b2330", "#5b6574", "#d5dae1"


def load():
    t = pd.read_csv(HERE / "orb_10y_trades.csv", parse_dates=["time"])
    s = {leg: g.set_index("time")["r"].sort_index() for leg, g in t.groupby("leg")}
    s["Portfolio"] = pd.concat([s["SP500"], s["NASDAQ"]]).sort_index()
    return s


def pf(x):
    g, l = x[x > 0].sum(), -x[x < 0].sum()
    return g / l if l else np.inf


def maxdd(x):
    eq = x.cumsum()
    return (eq - np.maximum.accumulate(np.concatenate([[0.0], eq.values]))[1:]).min()


def stats(x):
    return dict(n=len(x), pf=pf(x), sum=x.sum(), avg=x.mean(), dd=maxdd(x),
                yrs=f"{(x.groupby(x.index.year).sum() > 0).sum()}/{x.index.year.nunique()}")


def fmt(v, d=1, sign=True):
    s = f"{v:+.{d}f}" if sign else f"{v:.{d}f}"
    return s.replace(".", ",").replace("-", "−")


def draw(fig, page_fn_ax):
    ax0 = page_fn_ax
    s = load()
    start = min(v.index.min() for v in s.values())
    end = max(v.index.max() for v in s.values())

    def shade(ax, ymin, ymax):
        ax.axvspan(OOS_START, end + pd.Timedelta(days=20), color="#eef3fb", zorder=0, lw=0)
        ax.axvline(OOS_START, color=MUTED, lw=0.8, ls=(0, (3, 3)), zorder=1)

    def style(ax):
        for sp in ("top", "right", "left"):
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color(LINE)
        ax.grid(axis="y", color="#e9ecf0", lw=0.6)
        ax.tick_params(colors=MUTED, labelsize=7.5, length=0)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.set_xlim(start - pd.Timedelta(days=20), end + pd.Timedelta(days=20))
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:+.0f} R".replace("-", "−") if v else "0")

    # Panel 1: Portfolio
    a1 = fig.add_axes([0.06, 0.53, 0.6, 0.29])
    eq = s["Portfolio"].cumsum()
    shade(a1, 0, 1)
    a1.step(eq.index, eq.values, where="post", color=C_SP, lw=1.8, zorder=3)
    a1.axhline(0, color=LINE, lw=0.8)
    style(a1)
    is_end = eq[eq.index < OOS_START].iloc[-1]
    a1.text(start, eq.max() * 0.98, "In-Sample (IS)", fontsize=8.5, color=MUTED, weight="bold", va="top")
    a1.text(OOS_START + pd.Timedelta(days=40), eq.max() * 0.98, "Out-of-Sample (OOS)", fontsize=8.5,
            color="#2b6cb0", weight="bold", va="top")
    a1.annotate(fmt(eq.iloc[-1], 0) + " R", (eq.index[-1], eq.iloc[-1]), xytext=(4, 0), textcoords="offset points",
                fontsize=8.5, weight="bold", color=INK, va="center")
    a1.annotate(fmt(is_end, 0) + " R", (OOS_START, is_end), xytext=(-4, 8), textcoords="offset points",
                fontsize=8, color=MUTED, ha="right")
    a1.set_title("Portfolio SP500 + NASDAQ (live-Konfiguration), kumuliert in R", fontsize=9.5, color=INK,
                 loc="left", weight="bold", pad=6)

    # Panel 2: Beine
    a2 = fig.add_axes([0.06, 0.12, 0.6, 0.31])
    shade(a2, 0, 1)
    for leg, c, ls in (("SP500", C_SP, "-"), ("NASDAQ", C_NQ, "-"), ("US30", C_US, (0, (4, 2)))):
        e = s[leg].cumsum()
        a2.step(e.index, e.values, where="post", color=c, lw=1.5, ls=ls, zorder=3)
        label = leg + (" (pausiert)" if leg == "US30" else "")
        a2.annotate(f"{label}  {fmt(e.iloc[-1], 0)} R", (e.index[-1], e.iloc[-1]), xytext=(4, 0),
                    textcoords="offset points", fontsize=8, color=INK, va="center")
    a2.axhline(0, color=LINE, lw=0.8)
    style(a2)
    a2.set_title("Einzelne Beine, kumuliert in R", fontsize=9.5, color=INK, loc="left", weight="bold", pad=6)
    from matplotlib.lines import Line2D
    a2.legend(handles=[Line2D([], [], color=C_SP, lw=1.5, label="SP500"),
                       Line2D([], [], color=C_NQ, lw=1.5, label="NASDAQ"),
                       Line2D([], [], color=C_US, lw=1.5, ls=(0, (4, 2)), label="US30 (pausiert)")],
              loc="upper left", fontsize=7.5, frameon=False, ncol=3)

    # Tabelle rechts: IS vs OOS
    x0, y = 8.25, 6.55
    ax0.text(x0, y, "IS gegen OOS", fontsize=10.5, weight="bold", color=INK)
    y -= 0.25
    ax0.text(x0, y, f"IS {start:%m/%Y}–12/2022 · OOS 01/2023–{end:%m/%Y}", fontsize=7.3, color=MUTED)
    y -= 0.35
    cols = [("", 0.95), ("Trades", 0.5), ("PF", 0.45), ("Σ R", 0.6), ("Ø R", 0.55), ("MaxDD", 0.5)]
    xx = x0
    for c, w in cols:
        ax0.text(xx, y, c, fontsize=7.3, color=MUTED, weight="bold"); xx += w
    for leg in ("Portfolio", "SP500", "NASDAQ", "US30"):
        x = s[leg]
        for part, sub in (("IS", x[x.index < OOS_START]), ("OOS", x[x.index >= OOS_START])):
            y -= 0.27
            st = stats(sub)
            vals = [f"{leg if part == 'IS' else ''} {part}".strip() if part == "IS" else "   OOS",
                    str(st["n"]), fmt(st["pf"], 2, False), fmt(st["sum"], 0), fmt(st["avg"], 2), fmt(st["dd"], 0)]
            xx = x0
            for j, ((c, w), v) in enumerate(zip(cols, vals)):
                col = INK
                if j == 2:
                    col = "#1f7a3a" if st["pf"] >= 1.3 else ("#9a6200" if st["pf"] >= 1 else "#a8322a")
                ax0.text(xx, y, v, fontsize=7.6, color=col, weight="bold" if j in (0, 2) else "normal"); xx += w
        y -= 0.1
        ax0.plot([x0, x0 + sum(w for _, w in cols)], [y + 0.02, y + 0.02], color=LINE, lw=0.6)
    y -= 0.3
    ax0.text(x0, y, "PF-Farbe: grün ≥ 1,3 · gelb 1,0–1,3 · rot < 1,0\n"
             "Je Trade 1 R Risiko, ohne Zinseszins.\n"
             "Ab 2019 tick-korrigiert, davor nur M1\n(Effekt ca. −0,01 bis −0,04 R je Trade).\n"
             "Die Parameter wurden auf Daten bis\n09/2026 gewählt, auch OOS war sichtbar.",
             fontsize=7.3, color=MUTED, va="top", linespacing=1.45)
    return s
