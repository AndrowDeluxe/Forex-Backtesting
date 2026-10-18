"""Gold-ASB-Kriterien-PDF: IS-only-Strategie (Overfitting-Sperre, Lock gold_asb_is_reopt_20261015),
dieselben Kriterien und dasselbe Layout wie orb_pdf2.py. Nutzerauftrag 18.10.2026.

Eingaben: asian_range_breakout/results/is_reopt_* + trades_cost.csv (Kostenzerlegung derselben
eingefrorenen Konfiguration mit bps=0, kein neuer Versuch; Pfad als 1. Argument)."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Rectangle

plt.rcParams["font.family"] = "DejaVu Sans"
RES = Path(r"C:\Users\andre\Forex-Backtesting\asian_range_breakout\results")
OUT = r"C:\Users\andre\Forex-Backtesting\Claude outputs\gold_asb_profitabilitaets_kriterien_20261018.pdf"
COSTS = Path(sys.argv[1])
INK, MUTED, LINE, HEAD = "#1b2330", "#5b6574", "#d5dae1", "#1e2a3d"
G, A, R = ("#e3f3e6", "#1f7a3a"), ("#fdf1dc", "#9a6200"), ("#f9e1df", "#a8322a")
C_ALL, C_L, C_S, C_LIVE = "#2a78d6", "#1baf7a", "#eb6834", "#8a94a3"
W, H = 11.69, 8.27
IS_END, OOS_END = pd.Timestamp("2022-12-31 23:59"), pd.Timestamp("2025-09-30 23:59")
PERIODS = {"IS": ("2016-11-02", "2022-12-31"), "OOS": ("2023-01-01", "2025-09-30"), "Tresor": ("2025-10-01", "2026-09-30"),
           "Gesamt": ("2016-11-02", "2026-09-30")}
KICK = "GOLD ASB · IS-ONLY-STRATEGIE · STAND 18.10.2026"

# ------------------------------------------------------------------ Daten
sel = json.loads((RES / "is_reopt_selection.json").read_text(encoding="utf-8"))
WIN = sel["winner"]
rep = pd.read_csv(RES / "is_reopt_report.csv")
DSR = float(rep[(rep.variant == "IS-only") & (rep.part == "DSR")]["avg"].iloc[0])
tc = pd.read_csv(COSTS)
tc["time"] = pd.to_datetime(tc["time"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
tc = tc.sort_values("time")
live = pd.read_csv(RES / "is_reopt_trades.csv")
live = live[live.variant == "Live"].copy()
live["time"] = pd.to_datetime(live["time"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
live = live.sort_values("time")


def ser(d):
    return pd.Series(d.r.to_numpy(), index=d.time), pd.Series(d.cost_r.to_numpy(), index=d.time)


S = {"Long": ser(tc[tc.dir == 1]), "Short": ser(tc[tc.dir == -1]), "Gesamt": ser(tc)}
COLS = ["Long", "Short", "Gesamt"]
LIVE_R = pd.Series(live.r.to_numpy(), index=live.time)
assert len(S["Gesamt"][0]) == 325 and abs(S["Gesamt"][0].sum() - 88.23) < 0.01


def part(s, p):
    if p == "IS":
        return s[s.index <= IS_END]
    if p == "OOS":
        return s[(s.index > IS_END) & (s.index <= OOS_END)]
    if p == "Tresor":
        return s[s.index > OOS_END]
    if p == "Test":
        return s[s.index <= OOS_END]
    return s


def years(p):
    a, b = PERIODS["IS"][0] if p == "Test" else PERIODS[p][0], PERIODS["OOS"][1] if p == "Test" else PERIODS[p][1]
    return (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25


def m(r, c=None, p=None):
    if len(r) < 2:
        return {"n": len(r)}
    loss = -r[r < 0].sum()
    eq = r.cumsum().to_numpy()
    half = len(r) // 2
    out = {"n": len(r), "py": len(r) / years(p) if p else np.nan, "avg": r.mean(),
           "t": r.mean() / r.std(ddof=1) * np.sqrt(len(r)),
           "pf": r[r > 0].sum() / loss if loss > 0 else np.inf, "sum": r.sum(),
           "dd": (eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min(),
           "h1": r.iloc[:half].sum(), "h2": r.iloc[half:].sum(), "win": (r > 0).mean()}
    if c is not None and len(c):
        out["cost"] = c.mean()
        out["x2"] = (r - c).mean()
        out["x3"] = (r - 2 * c).mean()
    return out


def f(v, d=1, sign=True):
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return "–"
    s = f"{v:+.{d}f}" if sign else f"{v:.{d}f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s.replace("-", "−")


def account(r, risk=0.01, start=100_000.0):
    """1 % vom aktuellen Kontostand je Trade (Zinseszins). Gold ASB: höchstens ein Trade je Tag."""
    eq = start * np.cumprod(1 + risk * r.to_numpy())
    s = pd.Series(eq, index=r.index)
    path = np.concatenate([[start], eq])
    dd = (path / np.maximum.accumulate(path) - 1).min()
    return s, dd


def kind_pf(v):
    return G if v > 1.3 else (A if v >= 1.0 else R)


# ------------------------------------------------------------------ Layout (wie orb_pdf2.py)
def page(title, sub, kicker=KICK):
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    ax.text(0.55, H - 0.55, kicker, fontsize=9, color="#2b6cb0", weight="bold", family="DejaVu Sans Mono")
    ax.text(0.55, H - 1.0, title, fontsize=21, color=INK, weight="bold")
    ax.text(0.55, H - 1.3, sub, fontsize=9.3, color=MUTED, va="top", linespacing=1.4)
    return fig, ax


def cell(ax, x, y, w, h, txt, kind=None, bold=False, size=9, color=INK, sub=None):
    if kind:
        bg, fg = kind
        ax.add_patch(FancyBboxPatch((x + 0.06, y + 0.07), w - 0.12, h - 0.14,
                                    boxstyle="round,pad=0,rounding_size=0.06", fc=bg, ec="none"))
        color = fg
    ax.text(x + 0.14, y + h / 2 + (0.1 if sub else 0), txt, fontsize=size, color=color, va="center",
            weight="bold" if bold or kind else "normal", linespacing=1.35)
    if sub:
        ax.text(x + 0.14, y + h / 2 - 0.13, sub, fontsize=7.1, color=color if kind else MUTED, va="center")


def header(ax, cols, x0, y, h=0.45):
    x = x0
    for name, w in cols:
        ax.add_patch(Rectangle((x, y), w, h, fc=HEAD, ec="none"))
        ax.text(x + 0.12, y + h / 2, name, fontsize=8.8, color="white", va="center", weight="bold", linespacing=1.15)
        x += w


def table(ax, cols, rows, x0, y, rh, size=9, muted_cols=()):
    TW = sum(w for _, w in cols)
    for i, row in enumerate(rows):
        y -= rh
        if i % 2 == 0:
            ax.add_patch(Rectangle((x0, y), TW, rh, fc="#f5f7fa", ec="none"))
        ax.plot([x0, x0 + TW], [y, y], color=LINE, lw=0.8)
        x = x0
        for j, (val, (_, w)) in enumerate(zip(row, cols)):
            if isinstance(val, tuple):
                cell(ax, x, y, w, rh, val[0], val[1], sub=val[2] if len(val) > 2 else None, size=size)
            else:
                cell(ax, x, y, w, rh, val, bold=(j == 0), size=size, color=MUTED if j in muted_cols else INK)
            x += w
    return y


def box(ax, x0, ytop, h, title, body, tone="blue", size=8.4):
    fc, ec, tc_ = {"blue": ("#eef3fb", "#c4d4ec", INK), "amber": ("#fdf1dc", "#ecd3a4", A[1]),
                   "red": ("#f9e1df", "#e6b3ae", R[1])}[tone]
    ax.add_patch(FancyBboxPatch((x0, ytop - h), 10.6, h, boxstyle="round,pad=0,rounding_size=0.08", fc=fc, ec=ec))
    ax.text(x0 + 0.2, ytop - 0.27, title, fontsize=10.5, weight="bold", color=tc_, va="center")
    ax.text(x0 + 0.2, ytop - 0.5, body, fontsize=size, color=INK, va="top", linespacing=1.5)


def style_time(a, start, end):
    for sp in ("top", "right", "left"):
        a.spines[sp].set_visible(False)
    a.spines["bottom"].set_color(LINE)
    a.grid(axis="y", color="#e9ecf0", lw=0.6)
    a.tick_params(colors=MUTED, labelsize=7.5, length=0)


def build(pdf):
    # ============ Seite 1: Strategie in Klartext ============
    fig, ax = page("Die Strategie: Gold Asian-Session-Breakout",
                   "Ein Ausbruch aus der ruhigen Asien-Range in Gold (XAUUSD, CFD), gehandelt in die London- und frühe US-Session.\n"
                   "Alle Regeln wurden nur auf Daten von 11/2016 bis 2022 gewählt und danach eingefroren.",
                   kicker="GRUPPENARBEIT · GOLD ASB")
    steps = [
        ("1  Range", "Hoch und Tief von 21:00 bis 01:00 New York (Asien-Session) bilden die Range."),
        ("2  Filter", "Gehandelt wird nur, wenn (a) der Trend-Stärke-Index ADX (15 Min.) um 01:00 bei mindestens 15 liegt, (b) Silber in den\n"
                      "letzten 5 Tagen in Handelsrichtung lief und (c) der Gold-Markt am Vortag ruhig/liquide war (geschätzter Spread\n"
                      "höchstens so hoch wie der Median aller Tage davor). Kein Trendfilter auf Gold selbst."),
        ("3  Einstieg", "Um 01:00 liegen eine Kauf-Stop-Order am Range-Hoch und eine Verkauf-Stop-Order am Range-Tief (OCO).\n"
                        "Die zuerst ausgelöste Seite gilt (ein Trade je Tag). Ist bis 02:30 New York nichts ausgelöst, fallen beide weg."),
        ("4  Stop", "Der Stop liegt 2,0 × Range-Breite vom Einstieg entfernt. Dieser Abstand ist 1 R, das Risiko je Trade."),
        ("5  Ausstieg", "Kein Kursziel, kein Breakeven. Der Trade schließt um 11:00 New York (nach dem Londoner Nachmittags-Fix)."),
    ]
    y = H - 2.05
    for head, txt in steps:
        hh = 0.5 + 0.17 * txt.count("\n")
        ax.add_patch(FancyBboxPatch((0.55, y - hh - 0.02), 1.55, hh, boxstyle="round,pad=0,rounding_size=0.06", fc="#eef3fb", ec="none"))
        ax.text(0.7, y - hh / 2 - 0.02, head, fontsize=10, weight="bold", color="#2b6cb0", va="center")
        ax.text(2.3, y - hh / 2 - 0.02, txt, fontsize=9, color=INK, va="center", linespacing=1.4)
        y -= hh + 0.18
    ax.text(0.55, y - 0.15, "Zeitachse eines Handelstags (New York)", fontsize=11, weight="bold", color=INK)
    cols = [("21:00–01:00", 2.1), ("01:00", 1.7), ("bis 02:30", 1.7), ("03:00 / 05:30", 1.9), ("10:00", 1.5), ("11:00", 1.7)]
    yy = y - 0.4
    header(ax, cols, 0.55, yy - 0.4, 0.4)
    table(ax, cols, [["Asien-Range bildet\nsich (Tokio, Shanghai)", "Orders liegen\n(OCO)", "Order muss\nausgelöst sein",
                      "London öffnet /\nLBMA-Vormittags-Fix", "LBMA-Nachmittags-\nFix, US-Cash läuft", "Ausstieg"]],
          0.55, yy - 0.4, 0.62, size=8.2)
    ax.text(0.55, 0.45, "Warum das funktionieren könnte, steht auf Seite 7 (Mechanismus), welche Regeln genau gelten, auf Seite 3 (Einstellungen).\n"
            "Alle Zahlen in R: 1 R = Risiko je Trade, also der Abstand vom Einstieg zum Stop.", fontsize=8, color=MUTED, linespacing=1.5)
    pdf.savefig(fig); plt.close(fig)

    # ============ Seite 2: Scorecard ============
    fig, ax = page("Ist die nur auf IS optimierte Gold-ASB-Strategie profitabel?",
                   "Overfitting-Sperre: optimiert nur auf IS 11/2016–12/2022, eingefroren, dann einmal OOS 01/2023–09/2025 und einmal\n"
                   "Tresor 10/2025–09/2026 geöffnet. „Test“ = alles bis 30.09.2025. M5, Kosten des teuersten Brokers (TTP) eingerechnet.")
    cols = [("Kriterium", 1.95), ("Mindestens", 1.5)] + [(c, (10.6 - 3.45) / 3) for c in COLS]
    x0, y = 0.55, H - 2.25
    header(ax, cols, x0, y)
    r_cost, r_n, r_pf, r_h, r_ho, r_me = (["Kosten eingerechnet", "Gebühren + 1 Tick"], ["Anzahl Trades", "100 im Test"],
                                          ["Profit Factor", "über 1,3"], ["Beide Hälften", "jeweils im Plus"],
                                          ["Holdout (12 Monate)", "im Plus"], ["Mechanismus", "erklärbar"])
    for c in COLS:
        r, k = S[c]
        mt, mo, mh = m(part(r, "Test"), part(k, "Test"), "Test"), m(part(r, "OOS")), m(part(r, "Tresor"))
        r_cost.append(("Erfüllt" if mt["x2"] > 0 else "Knapp", G if mt["x2"] > 0 else A,
                       f"Kosten {f(mt['cost'], 2, False)} R · ×2: Ø {f(mt['x2'], 2)}"))
        r_n.append((str(mt["n"]), G if mt["n"] >= 100 else R, f"{mt['py']:.0f} pro Jahr"))
        r_pf.append((f(mt["pf"], 2, False), kind_pf(mt["pf"]), f"nur OOS: {f(mo.get('pf', np.nan), 2, False)}"))
        ok = mt["h1"] > 0 and mt["h2"] > 0
        r_h.append((f"{f(mt['h1'], 0)} / {f(mt['h2'], 0)} R", G if ok else R, "nach Trade-Anzahl geteilt"))
        kind = G if (mh["pf"] > 1.3 and mh["n"] >= 30) else (A if mh["sum"] > 0 else R)
        r_ho.append((f"{f(mh['sum'], 1)} R", kind, f"PF {f(mh['pf'], 2, False)} · nur {mh['n']} Trades"))
        r_me.append(("Plausibel", A, "Felder 1, 4 gestützt (S. 7–8)"))
    y = table(ax, cols, [r_cost, r_n, r_pf, r_h, r_ho, r_me], x0, y, 0.66)
    ax.text(x0, y - 0.35, "Grün = erfüllt · Gelb = teilweise/knapp · Rot = nicht erfüllt.  R = Vielfaches des Risikos je Trade.  "
            "Holdout grün erst ab PF > 1,3 und mindestens 30 Trades.", fontsize=7.5, color=MUTED)
    ho, oo, ii = (m(part(S["Gesamt"][0], p)) for p in ("Tresor", "OOS", "IS"))
    box(ax, x0, y - 0.7, 1.35, "Fazit: Im Tresor knapp im Plus, aber der Edge läuft aus",
        "Bis 09/2025 erfüllt die Strategie alle messbaren Kriterien: genug Trades, PF über 1,3, beide Hälften im Plus, Kosten klar gedeckt.\n"
        f"Im Tresor bleibt sie im Plus ({f(ho['sum'], 1)} R, PF {f(ho['pf'], 2, False)}), aber nur mit {ho['n']} Trades. Ø R je Trade fällt stufenweise: "
        f"IS {f(ii['avg'], 2)} → OOS {f(oo['avg'], 2)} → Tresor {f(ho['avg'], 2)}.\n"
        f"Nicht durchgefallen wie ORB, aber auch nicht bestätigt. Deflated Sharpe {f(DSR, 2, False)} (Ziel > 0,95): gegen 20.736 Versuche nicht von Glück zu trennen.",
        tone="amber")
    pdf.savefig(fig); plt.close(fig)

    # ============ Seite 3: Einstellungen ============
    fig, ax = page("Welche Einstellungen die Strategie nutzt",
                   "Die nur auf IS 2016–2022 gewählte Konfiguration, daneben zum Vergleich die heute live laufende.\n"
                   "Die Live-Konfiguration wurde am 01.10. auf ALLEN Daten gewählt (inkl. OOS und Tresor) und ist deshalb kein Beleg.")
    rows = [
        ["Asien-Range", "21:00–01:00 NY", "21:00–01:00 NY", "fest"],
        ["Einstieg", "OCO-Stop-Orders an Hoch/Tief ab 01:00", "OCO-Stop-Orders an Hoch/Tief ab 01:00", "fest"],
        ["Order-Storno", f"{WIN['cancel']} NY", "03:00 NY", "optimiert"],
        ["Stop", f"{f(WIN['stop'], 1, False)} × Range", "1,5 × Range", "optimiert"],
        ["Ausstieg", f"{WIN['exit']} NY, kein Ziel", "11:00 NY, kein Ziel", "optimiert"],
        ["Richtung", {"beide": "long + short", "long": "nur long", "short": "nur short"}[WIN["dirs"]], "long + short", "optimiert"],
        ["ADX (M15) mindestens", "aus" if WIN["adx"] is None else f(WIN["adx"], 0, False), "15", "optimiert"],
        ["Trendfilter Gold (SMA)", "keiner" if WIN["sma"] is None else f"SMA {WIN['sma']}", "SMA 200 (nur mit Trend)", "optimiert"],
        ["Silber-Bestätigung", f"{WIN['silver']} Tage in Handelsrichtung", "5 Tage in Handelsrichtung", "optimiert"],
        ["Liquiditätsfilter", "Vortags-Spread ≤ Median (Quantil 0,5)", "Vortags-Spread ≤ 2/3-Quantil", "optimiert"],
    ]
    cols = [("Einstellung", 2.6), ("IS-only (eingefroren)", 3.4), ("Live-Konfiguration (Vergleich)", 3.4), ("", 1.2)]
    x0, y = 0.55, H - 2.3
    header(ax, cols, x0, y, 0.5)
    yb = table(ax, cols, rows, x0, y, 0.42, size=8.3, muted_cols=(2, 3))
    ax.text(x0, yb - 0.35, "Optimiert wurden 8 Stellschrauben (Stop, Storno, Ausstieg, ADX, Trend-SMA, Silber, Liquidität, Richtung); Richtwert max. 9.",
            fontsize=7.8, color=MUTED)
    ax.text(x0, yb - 0.6, f"Versuche (Trial-Register): {sel['n_trials']:,} Varianten".replace(",", ".") +
            f", davon {sel['n_eligible']:,}".replace(",", ".").replace(". davon", ", davon") + " mit ≥ 100 IS-Trades, PF > 1,3 und beiden Hälften im Plus.", fontsize=7.8, color=MUTED)
    ax.text(x0, yb - 0.85, "Auswahl: höchster t-Wert, geglättet über die Stop- und Storno-Nachbarn (Plateau statt Spitze). Die Top 12 lagen alle bei t 4,2–4,4.",
            fontsize=7.8, color=MUTED)
    pdf.savefig(fig); plt.close(fig)

    # ============ Seite 4: OOS + Tresor ============
    fig, ax = page("Was OOS und Tresor zeigen",
                   "Kennzahlen je Zeitraum. Die IS-only-Konfiguration wurde vor dem Öffnen eingefroren; OOS und Tresor ließen sich\n"
                   "technisch nur je einmal öffnen. Das Ergebnis zählt, egal wie.")
    cols = [("", 2.3), ("Zeitraum", 1.0), ("Trades", 0.8), ("PF", 0.8), ("Ø R", 0.85), ("Σ R", 0.9), ("MaxDD R", 0.95),
            ("t-Wert", 0.85), ("Treffer", 0.85), ("Ø R bei\nKosten ×2", 1.3)]
    x0, y = 0.55, H - 2.25
    header(ax, cols, x0, y, 0.5)
    rows = []
    for c in ("Gesamt", "Long", "Short"):
        r, k = S[c]
        for p in ("IS", "OOS", "Tresor"):
            mm = m(part(r, p), part(k, p))
            rows.append([f"{'Long + Short' if c == 'Gesamt' else c} · IS-only" if p == "IS" else "", p, str(mm["n"]),
                         (f(mm["pf"], 2, False), kind_pf(mm["pf"])), f(mm["avg"], 2), f(mm["sum"], 1), f(mm["dd"], 1),
                         f(mm["t"], 1), f"{mm['win'] * 100:.0f} %", f(mm["x2"], 2)])
    rh = 0.34
    TW = sum(w for _, w in cols)
    yy = y
    for row in rows:
        yy -= rh
        if row[0]:
            ax.plot([x0, x0 + TW], [yy + rh, yy + rh], color="#9aa3af", lw=0.9)
        x = x0
        for j, (val, (_, w)) in enumerate(zip(row, cols)):
            if isinstance(val, tuple):
                ax.text(x + 0.12, yy + rh / 2, val[0], fontsize=7.6, color=val[1][1], va="center", weight="bold")
            else:
                ax.text(x + 0.12, yy + rh / 2, val, fontsize=7.6, va="center",
                        color=("#2b6cb0" if row[1] in ("OOS", "Tresor") and j == 1 else INK),
                        weight="bold" if j == 0 or (j == 1 and val != "IS") else "normal")
            x += w
    ax.text(x0, yy - 0.35, f"Deflated Sharpe (IS, Ziel > 0,95) gegen {sel['n_trials']:,}".replace(",", ".").replace("IS. Ziel > 0.95", "IS, Ziel > 0,95") +
            f" Varianten: {f(DSR, 2, False)}" +
            "  (ORB zum Vergleich: ~0).\nPF-Farbe: grün > 1,3 · gelb 1,0–1,3 · rot < 1,0.", fontsize=7.8, color=MUTED, va="top", linespacing=1.5)
    lv = {p: m(part(LIVE_R, p)) for p in ("OOS", "Tresor")}
    box(ax, x0, yy - 0.95, 1.5, "Warum wird der Tresor dünn? Was die Zahlen zeigen",
        f"• Weniger Trades: {ho['n']} statt sonst ~35 pro Jahr. Der Liquiditätsfilter (Median-Spread) sortiert im volatilen Gold-Jahr 2025/26 mehr Tage aus.\n"
        "• Der Edge bricht nicht, er verdünnt sich: alle 11 Kalenderjahre positiv, 2026 nur noch knapp (+1,2 R in 12 Trades).\n"
        f"• Die Short-Seite im Tresor ({m(part(S['Short'][0], 'Tresor'))['n']} Trades, {f(part(S['Short'][0], 'Tresor').sum(), 1)} R) ist bei dieser Anzahl Rauschen.\n"
        f"• Die Live-Konfiguration sieht im Tresor besser aus ({f(lv['Tresor']['avg'], 2)} R je Trade, {lv['Tresor']['n']} Trades), wurde aber auf diesen Daten gewählt: kein Beleg.",
        size=7.8)
    pdf.savefig(fig); plt.close(fig)

    # ============ Seite 5: Equity ============
    fig, ax = page("Equity-Kurve: 10 Jahre, IS / OOS / Tresor",
                   "Kumuliert in R (1 R Risiko je Trade, ohne Zinseszins). Nur auf IS 2016–2022 optimierte Strategie,\n"
                   "danach eingefroren: OOS 2023–09/2025 und Tresor 10/2025–09/2026 je einmal geöffnet.")
    r_all = S["Gesamt"][0]
    start, end = r_all.index.min(), r_all.index.max()

    def style(a):
        style_time(a, start, end)
        a.xaxis.set_major_locator(mdates.YearLocator())
        a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        a.set_xlim(start - pd.Timedelta(days=20), end + pd.Timedelta(days=170))
        a.yaxis.set_major_formatter(lambda v, _: (f"{v:+.0f} R".replace("-", "−")) if v else "0")
        a.axvspan(IS_END, OOS_END, color="#eef3fb", zorder=0, lw=0)
        a.axvspan(OOS_END, end + pd.Timedelta(days=170), color="#fdf1dc", zorder=0, lw=0)
        a.axhline(0, color=LINE, lw=0.8)

    a1 = fig.add_axes([0.06, 0.47, 0.8, 0.29])
    style(a1)
    eq = r_all.cumsum()
    a1.step(eq.index, eq.values, where="post", color=C_ALL, lw=1.9, zorder=3)
    top = eq.max()
    for x_, lab, c in ((start, "IS – optimiert", MUTED), (IS_END + pd.Timedelta(days=30), "OOS – einmal getestet", "#2b6cb0"),
                       (OOS_END + pd.Timedelta(days=20), "Tresor", A[1])):
        a1.text(x_, top * 1.03, lab, fontsize=8, color=c, weight="bold", va="bottom")
    a1.annotate(f"IS-only {f(eq.iloc[-1], 0)} R", (eq.index[-1], eq.iloc[-1]), xytext=(4, 0), textcoords="offset points",
                fontsize=8, weight="bold", color=INK, va="center")
    a1.set_title("Gold ASB, long + short", fontsize=9.5, color=INK, loc="left", weight="bold", pad=16)

    a2 = fig.add_axes([0.06, 0.07, 0.8, 0.3])
    style(a2)
    handles = []
    for name, c in (("Long", C_L), ("Short", C_S)):
        e = S[name][0].cumsum()
        a2.step(e.index, e.values, where="post", color=c, lw=1.5, zorder=3)
        handles.append(Line2D([], [], color=c, lw=1.5, label=f"{name}  {f(e.iloc[-1], 0)} R"))
    a2.legend(handles=handles, loc="upper left", fontsize=7.5, frameon=False, ncol=2)
    a2.set_title("Getrennt nach Richtung", fontsize=9.5, color=INK, loc="left", weight="bold", pad=6)
    pdf.savefig(fig); plt.close(fig)

    # ============ Seite 6: 100k-Konto ============
    fig, ax = page("Der Tresor auf einem 100.000-$-Konto",
                   "10/2025–09/2026, einmal geöffnet. Risiko je Trade 1 % vom aktuellen Kontostand (mit Zinseszins).\n"
                   "Höchstens ein Trade je Tag. Kosten (TTP-Spread + Slippage, 2,08 bps je Round-Trip) sind eingerechnet.")
    acc_t, _ = account(part(r_all, "Tresor"))
    a3 = fig.add_axes([0.06, 0.2, 0.55, 0.56])
    t0 = pd.Timestamp(PERIODS["Tresor"][0])
    eqs = pd.concat([pd.Series([100_000.0], index=[t0]), acc_t, pd.Series([acc_t.iloc[-1]], index=[pd.Timestamp(PERIODS["Tresor"][1])])])
    a3.step(eqs.index, eqs.values, where="post", color=C_ALL, lw=1.9, zorder=3)
    a3.axhline(100_000, color=LINE, lw=0.9)
    style_time(a3, None, None)
    a3.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
    a3.yaxis.set_major_formatter(lambda v, _: f"{v / 1000:.1f}k $".replace(".", ","))
    a3.annotate(f"{eqs.iloc[-1] / 1000:.1f}k $".replace(".", ","), (eqs.index[-1], eqs.iloc[-1]), xytext=(4, 0),
                textcoords="offset points", fontsize=9, weight="bold", color=INK, va="center")
    a3.set_title("Kontostand nach jedem Trade", fontsize=9.5, color=INK, loc="left", weight="bold", pad=6)
    x0, y = 7.6, H - 2.25
    ax.text(x0, y, "Kennzahlen", fontsize=10.5, weight="bold", color=INK)
    for key, lab in (("Tresor", "Tresor · 10/2025-09/2026"), ("OOS", "OOS (Vergleich) · 01/2023-09/2025"),
                     ("Gesamt", "10 Jahre (Vergleich) · 2016-2026")):
        rr = r_all if key == "Gesamt" else part(r_all, key)
        s, dd = account(rr)
        ret = s.iloc[-1] / 100_000 - 1
        cagr = (1 + ret) ** (1 / years(key)) - 1
        y -= 0.36
        ax.text(x0, y, lab, fontsize=8.6, weight="bold", color=A[1] if key == "Tresor" else INK)
        for k_, v_ in (("Endstand", f"{s.iloc[-1]:,.0f} $".replace(",", ".")), ("Rendite", f"{f(ret * 100, 1)} %"),
                       ("Rendite p. a.", f"{f(cagr * 100, 1)} %"), ("Max Drawdown", f"{f(dd * 100, 1)} %"), ("Trades", f"{len(rr)}")):
            y -= 0.22
            ax.text(x0 + 0.15, y, k_, fontsize=8, color=MUTED)
            ax.text(x0 + 2.2, y, v_, fontsize=8, color=INK, weight="bold" if k_ in ("Rendite", "Max Drawdown") else "normal")
        y -= 0.12
    ax.text(0.55, 0.45, "Startkapital je Zeitraum 100.000 $. Zum Vergleich ORB im selben Tresor: 100.000 $ → 40.495 $ (−59,5 %).\n"
            "Wenige Trades je Jahr: Die Rendite p. a. bleibt bei 1 % Risiko klein, auch wenn der Edge hält.", fontsize=7.8, color=MUTED, linespacing=1.5)
    pdf.savefig(fig); plt.close(fig)

    # ============ Seite 7: Mechanismus ============
    fig, ax = page("Wer verliert an unserem Gold ASB?",
                   "Die fünf Mechanismus-Felder, auf Gold ASB angewendet. Nicht nach einer profitablen Strategie suchen, sondern nach einem\n"
                   "dokumentierten Effekt mit Grund. Belegstand: eigene Daten + Literatur (Details auf Seite 8).",
                   kicker="GOLD ASB · STAND 18.10.2026")
    ml, sh = m(part(S["Long"][0], "IS")), m(part(S["Short"][0], "IS"))
    rows = [
        ["Strukturelle Flows\nund Zwänge", "Wer handeln muss",
         "Zwischen 01:00 und 11:00 NY liegen London-\nEröffnung und beide LBMA-Fixes. Banken,\nETFs und Hersteller müssen dort handeln.",
         ("Literatur, indirekt", A, "Fix bewegt Volumen und Richtung\n(Caminschi/Heaney 2014)"), "London fix,\norder imbalance"],
        ["Verhaltensfehler", "Wer zu spät oder\nfalsch reagiert",
         "Der erste Ausbruch nach der ruhigen Nacht wird\nunterschätzt, der Kurs läuft bis in die US-\nSession weiter (Unterreaktion).",
         ("Offen", A, "Silber-Bestätigung hilft (Trend\nquer über Metalle), nicht kausal"), "intraday momentum,\nunderreaction"],
        ["Risikoprämien", "Wer Risiko abgibt",
         "Long könnte bloß Golds Aufwärtsdrift sein\n(Gold stieg 2016–2026 stark).",
         ("Widerlegt", R,f"Short auch positiv: IS t {f(sh['t'], 1)},\nØ {f(sh['avg'], 2)} R (Long t {f(ml['t'], 1)})"), "gold drift, time-of-day\nreturns"],
        ["Mikrostruktur und\nLiquidität", "Wer sofort\nhandeln will",
         "Stops sammeln sich über und unter der engen\nAsien-Range. London-Liquidität löst sie aus,\ndie Kaskade treibt den Kurs weiter.",
         ("Indiz + Literatur FX", G, "eigen: Liquiditätsfilter trägt\nextern: Osler (Stops, nur FX)"), "stop clustering,\nliquidity"],
        ["Information", "Wer Infos langsamer\nverarbeitet",
         "Asiatische Nachfrage (China/Indien) setzt die\nRichtung, Europa und USA ziehen nach.",
         ("Schwach", A, "Asien-Stunden tragen den Großteil\nder Gold-Rendite (Wei 2026, kurz)"), "price discovery,\nsession returns"],
    ]
    cols = [("Feld", 1.95), ("Wer zahlt?", 1.6), ("Bezug zu Gold ASB", 3.3), ("Belegstand", 2.45), ("Suchbegriffe", 1.3)]
    x0, y = 0.55, H - 2.25
    header(ax, cols, x0, y, 0.45)
    rh = 0.86
    TW = sum(w for _, w in cols)
    for i, row in enumerate(rows):
        y -= rh
        if i % 2 == 0:
            ax.add_patch(Rectangle((x0, y), TW, rh, fc="#f5f7fa", ec="none"))
        ax.plot([x0, x0 + TW], [y, y], color=LINE, lw=0.8)
        x = x0
        for j, (val, (_, w)) in enumerate(zip(row, cols)):
            if isinstance(val, tuple):
                ax.add_patch(FancyBboxPatch((x + 0.06, y + 0.07), w - 0.12, rh - 0.14, boxstyle="round,pad=0,rounding_size=0.06",
                                            fc=val[1][0], ec="none"))
                ax.text(x + 0.14, y + rh - 0.22, val[0], fontsize=8.6, weight="bold", color=val[1][1], va="center")
                ax.text(x + 0.14, y + 0.3, val[2], fontsize=6.9, color=val[1][1], va="center", linespacing=1.35)
            else:
                ax.text(x + 0.12, y + rh / 2, val, va="center", linespacing=1.35,
                        fontsize={0: 8.4, 1: 8.0, 2: 7.6, 4: 7.0}[j], weight="bold" if j == 0 else "normal",
                        color=MUTED if j in (1, 4) else INK, family="DejaVu Sans Mono" if j == 4 else None)
            x += w
    box(ax, x0, y - 0.25, 1.3, "Einordnung",
        "Stärkste Kandidaten sind Feld 4 (Stop-Kaskade an der engen Asien-Range) und Feld 1 (London-Eröffnung und Fixes als Zwangs-Flow).\n"
        "Beide passen dazu, dass der Edge nur an ruhigen, liquiden Vortagen trägt. Feld 3 fällt weg, weil auch die Short-Seite verdient.\n"
        "Mit unseren Daten testbar: Ist der Edge an Tagen mit enger Range bzw. großem Volumen zur London-Eröffnung größer? Wenn ja, ist das Kriterium grün.",
        size=8.0)
    pdf.savefig(fig); plt.close(fig)

    # ============ Seite 8: Literatur + Kosten ============
    fig, ax = page("Was die Literatur dazu sagt",
                   "Web-Recherche 18.10.2026 auf Ebene der Zusammenfassungen: Studien, die unsere Felder ergänzen oder infrage stellen.",
                   kicker="GOLD ASB · STAND 18.10.2026")
    lit = [
        ("Caminschi, Heaney\nJ. Futures Markets 2014", "Um den Londoner Nachmittags-Fix steigt das Volumen in COMEX-Gold und GLD;\ndie ersten Minuten des Fixings sagen dessen Richtung voraus.",
         "Feld 1: Der Fix ist ein Zwangs-Flow\nim Handelsfenster (10:00 NY).", G),
        ("Crain, Hoelscher, Jones\nACRN 2020 (Übersicht)", "Globex-Gold-Futures führen den Londoner OTC-Spotmarkt bei der Preisfindung.",
         "Unsere Stop-Orders reagieren dort,\nwo der Preis entsteht.", G),
        ("Wei · SSRN 2026\nGold/Silber, ab 07/2024", "Die Asien-Session liefert 77 % der kumulierten Gold-Rendite, Europa +36 %,\ndie USA −13 %. Fortsetzung über die Sessions (Autokorr. +0,13).",
         "Feld 5 gestützt, aber kurzes Sample\nin einer Rally. Kein Beleg.", A),
        ("CBS-Masterarbeit 2019\nGold intraday", "„Hutförmige“ Tagessaisonalität: Gold steigt in den asiatischen Stunden\nund fällt im Rest des Tages; um den Londoner Fix Kursrückgänge.",
         "Warnung: Long nach 01:00 handelt\ngegen diese Saisonalität.", A),
        ("World Gold Council\nMid-Year Outlook 2026", "Ein Großteil der Gold-Bewegung fällt in die asiatischen und US-Handelsstunden;\nasiatische Anleger gewinnen an Gewicht bei der Preisfindung.",
         "Passt zum Zeitfenster bis 11:00 NY.\nKeine Studie, Branchenquelle.", A),
        ("Osler · NY Fed 2003/05\nFX-Orderbücher", "Stop-Buy-Orders clustern knapp über runden Marken, Stop-Sells knapp darunter.\nTrends laufen dort messbar schneller (Preiskaskaden).",
         "Feld 4 plausibel, aber nur für FX\nbelegt, nicht für Gold.", A),
    ]
    cols = [("Quelle", 2.25), ("Befund", 5.4), ("Bedeutung für Gold ASB", 2.95)]
    x0, y = 0.55, H - 1.9
    header(ax, cols, x0, y, 0.42)
    rh = 0.58
    for i, (src, fnd, imp, kind) in enumerate(lit):
        y -= rh
        if i % 2 == 0:
            ax.add_patch(Rectangle((x0, y), 10.6, rh, fc="#f5f7fa", ec="none"))
        ax.plot([x0, x0 + 10.6], [y, y], color=LINE, lw=0.8)
        ax.add_patch(Rectangle((x0, y + 0.06), 0.05, rh - 0.12, fc=kind[1], ec="none"))
        ax.text(x0 + 0.15, y + rh / 2, src, fontsize=7.6, weight="bold", color=INK, va="center", linespacing=1.35)
        ax.text(x0 + 2.37, y + rh / 2, fnd, fontsize=7.1, color=INK, va="center", linespacing=1.35)
        ax.text(x0 + 7.77, y + rh / 2, imp, fontsize=7.3, weight="bold", color=kind[1], va="center", linespacing=1.35)
    ax.text(x0, y - 0.4, "Kosten-Gegenprobe: Wie viel Kosten verträgt der Edge?", fontsize=11, weight="bold", color=INK)
    r, k = S["Gesamt"]
    kcols = [("", 1.5), ("Kosten\nRound-Trip", 1.4), ("Stop\n(Median)", 1.3), ("Kosten\nin R", 1.2), ("Ø R netto", 1.3),
             ("Ø R bei\nKosten ×2", 1.3), ("Ø R bei\nKosten ×3", 1.3)]
    yk = y - 0.62
    xx = x0
    for name, w in kcols:
        ax.text(xx + 0.12, yk, name, fontsize=7.6, color=MUTED, weight="bold", va="center", linespacing=1.2)
        xx += w
    yk -= 0.3
    for p in ("IS", "OOS", "Tresor"):
        mm = m(part(r, p), part(k, p))
        vals = [p, "2,08 bps", f"{(2.08 / part(k, p)).median():.0f} bps", f"{f(mm['cost'], 3, False)} R", f(mm["avg"], 3), f(mm["x2"], 2), f(mm["x3"], 2)]
        yk -= 0.3
        ax.plot([x0, x0 + 9.3], [yk + 0.15, yk + 0.15], color=LINE, lw=0.7)
        xx = x0
        for j, (v, (_, w)) in enumerate(zip(vals, kcols)):
            ax.text(xx + 0.12, yk, v, fontsize=8.2, color=INK, va="center", weight="bold" if j in (0, 4) else "normal")
            xx += w
    ax.text(x0, yk - 0.38, "Kosten = TTP, der teuerste unserer Broker. Weil der Stop die ganze Asien-Range (×2) umfasst, sind die Kosten in R klein: sie decken den Edge\n"
            "auch dreifach. Bei Gold ASB entscheiden Range-Breite und Filter, nicht die Gebühren (anders als beim ORB auf Index-CFDs).",
            fontsize=7.6, color=MUTED, va="top", linespacing=1.5)
    pdf.savefig(fig); plt.close(fig)

    # ============ Seite 9: Methode ============
    fig, ax = page("Wie die Zahlen entstanden sind", "Daten, Kosten, Aufteilung und Grenzen")
    blocks = [
        ("Daten", [
            "M5-Ausführung mit ruhender OCO-Stop-Order ab 01:00 NY, ADX auf M15, Gold- und Silber-Tagesschlüsse; Dukascopy-CFD-Daten 2016–09/2026.",
            "Alle Filter nutzen nur Werte vom Vortag bzw. bis 01:00 (kein Blick in die Zukunft). Wegen der 200-Tage-Vorlaufzeit startet IS am 02.11.2016."]),
        ("Kosten", [
            "TTP 2,08 bps je Round-Trip (Spread + Slippage, gemessen), der teuerste der genutzten Broker. Keine Kommission eingerechnet.",
            "Kosten ×2 / ×3 auf den Seiten 2, 4 und 8: dieselben Trades mit doppelten bzw. dreifachen Kosten."]),
        ("Aufteilung", [
            "IS 02.11.2016–31.12.2022 (optimieren) · OOS 01.01.2023–30.09.2025 (einmal testen) · Tresor 01.10.2025–30.09.2026 (einmal).",
            "„Test“ auf Seite 2 = IS + OOS. Hälften nach Trade-Anzahl. PF = Gewinne in R / Verluste in R.",
            "Vorbehalt: Der Tresor wurde am 14.10. im Tresor-Check der Live-Beine schon einmal angesehen; der Lauf ist eine Rekonstruktion „als ob nur IS“."]),
        ("Grenzen", [
            "Wenige Trades (~35 pro Jahr, im Tresor 18): einzelne Jahre sind statistisch kaum aussagekräftig.",
            "Der Liquiditätsfilter nutzt ein wachsendes Quantil aller Vortage: Ein später nachgerechneter Tag kann anders ausfallen als live.",
            "Mechanismus nur durch Literatur und indirekte eigene Daten gestützt, nicht kausal getestet.",
            "Live kommen Ausführungs-Verzögerung und Abweichungen des Brokers dazu."]),
    ]
    y = H - 1.95
    for head, lines in blocks:
        ax.text(0.55, y, head, fontsize=11, weight="bold", color=INK); y -= 0.32
        for ln in lines:
            ax.text(0.75, y, "• " + ln, fontsize=8.4, color=INK); y -= 0.27
        y -= 0.18
    pdf.savefig(fig); plt.close(fig)

    # ============ Seite 10: Fünf Zahlen ============
    fig, ax = page("Fünf Zahlen, die jedes Team zeigt",
                   "Ausgefüllt für die IS-only-Strategie, long + short. MaxDD zusätzlich in % bei 1,0 % Risiko je Trade.",
                   kicker="WAS WIR PRÜFEN · KENNZAHLEN")
    r, k = S["Gesamt"]
    P = {p: m(part(r, p), part(k, p), p) for p in ("IS", "OOS", "Tresor")}
    for p in P:
        P[p]["acc_dd"] = account(part(r, p))[1] * 100

    def judge(name, mm):
        if name == "pf":
            return kind_pf(mm["pf"])
        if name == "avg":
            ratio = mm["avg"] / mm["cost"] if mm["cost"] > 0 else 0
            return G if ratio >= 2 else (A if ratio >= 1 else R)
        if name == "dd":
            pct = -mm["acc_dd"]
            return G if pct <= 10 else (A if pct <= 20 else R)
        if name == "py":
            return G if mm["py"] >= 50 else A
        return G if mm["t"] > 2 else (A if mm["t"] > 1 else R)

    cols = [("Zahl", 1.6), ("So rechnest du sie", 2.4), ("Gut ist", 1.75), ("IS 2016–2022", 1.6), ("OOS 2023–09/2025", 1.6), ("Tresor 10/25–09/26", 1.65)]
    x0, y = 0.55, H - 2.0
    header(ax, cols, x0, y)
    spec = [("Profit Factor", "Summe Gewinne ÷ Summe Verluste", "über 1,3 nach Kosten", "pf", lambda mm: (f(mm["pf"], 2, False), None)),
            ("Ø Trade", "Netto ÷ Anzahl Trades", "deutlich über den Kosten", "avg",
             lambda mm: (f"{f(mm['avg'], 2)} R", f"Kosten {f(mm['cost'], 3, False)} R = {f(mm['avg'] / mm['cost'], 1, False)}×")),
            ("Max Drawdown", "Größter Rückgang vom Kontohoch", "du hältst ihn aus", "dd",
             lambda mm: (f"{f(mm['dd'], 1)} R", f"Konto (1 %): {f(mm['acc_dd'], 1)} %")),
            ("Trades pro Jahr", "Anzahl ÷ Jahre", "genug zum Lernen", "py", lambda mm: (f"{mm['py']:.0f}", f"{mm['n']} Trades gesamt")),
            ("t-Wert", "Ø Trade ÷ Streuung × √Anzahl", "über 2", "t", lambda mm: (f(mm["t"], 2, False), None))]
    rows = []
    for name, how, good, key, fn in spec:
        row = [name, how, good]
        for p in ("IS", "OOS", "Tresor"):
            txt, sub = fn(P[p])
            row.append((txt, judge(key, P[p]), sub) if sub else (txt, judge(key, P[p])))
        rows.append(row)
    yb = table(ax, cols, rows, x0, y, 0.72, size=8.8, muted_cols=(1,))
    ax.text(x0, yb - 0.4, "Der t-Wert sagt: Wie sicher ist es, dass der Gewinn kein Zufall ist? Über 2 heißt grob: weniger als 5 % Wahrscheinlichkeit für Zufall.\n"
            "Im Tresor bleiben PF und Ø Trade knapp positiv, der t-Wert nahe null zeigt aber: Bei 18 Trades ist das nicht von Zufall zu unterscheiden.\n"
            "Grenzen der Farben: Ø Trade grün ab 2× Kosten · MaxDD grün bis 10 %, gelb bis 20 % Konto · Trades/Jahr grün ab 50. Konto: 1 % vom Kontostand je Trade.",
            fontsize=7.8, color=MUTED, va="top", linespacing=1.5)
    pdf.savefig(fig); plt.close(fig)


with PdfPages(OUT) as pdf:
    build(pdf)
print("ok", OUT)
