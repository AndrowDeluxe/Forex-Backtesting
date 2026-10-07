"""ORB-Kriterien-PDF v2: IS-only-Strategie (Overfitting-Sperre), alle Kriterien, Equity 10 Jahre."""
import json
import os
import re
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
HERE = Path(__file__).parent
RES = Path(r"C:\Users\andre\Forex-Backtesting\ny_open_orb\results")
OUT = r"C:\Users\andre\Forex-Backtesting\Claude outputs\orb_profitabilitaets_kriterien_20261005.pdf"
PNG = os.environ.get("PNG")
INK, MUTED, LINE, HEAD = "#1b2330", "#5b6574", "#d5dae1", "#1e2a3d"
G, A, R = ("#e3f3e6", "#1f7a3a"), ("#fdf1dc", "#9a6200"), ("#f9e1df", "#a8322a")
C_SP, C_NQ, C_US = "#2a78d6", "#eb6834", "#1baf7a"
COL = {"SP500": C_SP, "NASDAQ": C_NQ, "US30": C_US}
W, H = 11.69, 8.27
IS_END, OOS_END = pd.Timestamp("2022-12-31 23:59"), pd.Timestamp("2025-09-30 23:59")
RISK_PCT = 1.0   # wie im 100k-Konto: 1 % Risiko je Trade

# ------------------------------------------------------------------ Daten
sel = json.loads((RES / "is_only_7p_selection.json").read_text(encoding="utf-8"))
WIN = sel["winners"]
tr = pd.read_csv(RES / "is_only_7p_trades_tresor.csv")
tr["time"] = pd.to_datetime(tr["time"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
rep = pd.read_csv(RES / "is_only_7p_report_tresor.csv")
ACC = pd.read_csv(RES / "is_only_7p_account_summary.csv")
LEGS = [i for i in ("SP500", "NASDAQ", "US30") if WIN.get(i)]


def series(inst, variant="IS-only"):
    d = tr[(tr.instrument == inst) & (tr.variant == variant)].sort_values("time")
    return pd.Series(d.r.to_numpy(), index=d.time), pd.Series(d.cost_r.to_numpy(), index=d.time)


def portfolio(variant="IS-only", legs=None):
    legs = legs or (LEGS if variant == "IS-only" else ["SP500", "NASDAQ"])
    rs, cs = zip(*(series(i, variant) for i in legs))
    return pd.concat(rs).sort_index(), pd.concat(cs).sort_index()


S = {i: series(i) for i in LEGS}
S["Portfolio"] = portfolio()
LIVE = {i: series(i, "frueher") for i in ("SP500", "NASDAQ")}
LIVE["Portfolio"] = portfolio("frueher")
COLS = LEGS + ["Portfolio"]


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


def m(r, c=None):
    if len(r) < 2:
        return {"n": len(r)}
    loss = -r[r < 0].sum()
    eq = r.cumsum().to_numpy()
    half = len(r) // 2
    yrs = max((r.index.max() - r.index.min()).days / 365.25, 1 / 12)
    out = {"n": len(r), "py": len(r) / yrs, "avg": r.mean(), "t": r.mean() / r.std(ddof=1) * np.sqrt(len(r)),
           "pf": r[r > 0].sum() / loss if loss > 0 else np.inf, "sum": r.sum(),
           "dd": (eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]).min(),
           "h1": r.iloc[:half].sum(), "h2": r.iloc[half:].sum(), "win": (r > 0).mean()}
    if c is not None and len(c):
        out["cost"] = c.mean()
        out["x2"] = (r - c).mean()
    return out


def f(v, d=1, sign=True):
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return "–"
    s = f"{v:+.{d}f}" if sign else f"{v:.{d}f}"
    return s.replace(".", ",").replace("-", "−")


def acct_dd(r, risk=0.01):
    """MaxDD in % auf einem Konto mit 1 % vom Kontostand je Trade (Tages-Sizing wie im Skript)."""
    if r.empty:
        return np.nan
    day = r.groupby(r.index.normalize()).apply(list)
    eq, path = 1.0, [1.0]
    for rs in day:
        eq += sum(x * risk * eq for x in rs)
        path.append(eq)
    path = np.array(path)
    return (path / np.maximum.accumulate(path) - 1).min() * 100


def kind_pf(v):
    return G if v > 1.3 else (A if v >= 1.0 else R)


# ------------------------------------------------------------------ Layout
def page(title, sub, kicker="NY-OPEN ORB · IS-ONLY-STRATEGIE · STAND 06.10.2026"):
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
            weight="bold" if bold or kind else "normal")
    if sub:
        ax.text(x + 0.14, y + h / 2 - 0.13, sub, fontsize=7.1, color=color if kind else MUTED, va="center")


def header(ax, cols, x0, y, h=0.45):
    x = x0
    for name, w in cols:
        ax.add_patch(Rectangle((x, y), w, h, fc=HEAD, ec="none"))
        ax.text(x + 0.12, y + h / 2, name, fontsize=8.8, color="white", va="center", weight="bold", linespacing=1.15)
        x += w


def table(ax, cols, rows, x0, y, rh, first_bold=True):
    """rows: list of lists; Zellen sind str oder (text, kind, sub)."""
    TW = sum(w for _, w in cols)
    for i, row in enumerate(rows):
        y -= rh
        if i % 2 == 0:
            ax.add_patch(Rectangle((x0, y), TW, rh, fc="#f5f7fa", ec="none"))
        ax.plot([x0, x0 + TW], [y, y], color=LINE, lw=0.8)
        x = x0
        for j, (val, (_, w)) in enumerate(zip(row, cols)):
            if isinstance(val, tuple):
                cell(ax, x, y, w, rh, val[0], val[1], sub=val[2] if len(val) > 2 else None)
            else:
                cell(ax, x, y, w, rh, val, bold=(j == 0 and first_bold), color=INK if j == 0 else INK)
            x += w
    return y


def cfg_text(c):
    if not c:
        return "nicht handelbar laut IS"
    d = {"long": "nur long", "short": "nur short", "beide": "long + short"}[c["dirs"]]
    return d


class _Png:
    def __init__(self): self.n = 0
    def savefig(self, fig):
        fig.savefig(OUT.replace(".pdf", f"_p{self.n}.png"), dpi=80); self.n += 1


def build(pdf):
    # ============ Seite 0: Die Strategie in Klartext ============
    fig, ax = page("Die Strategie: NY-Open Opening-Range-Breakout",
                   "Ein Intraday-Ausbruch nach der Eröffnung der US-Börse, gehandelt auf S&P 500 und Nasdaq 100 (Index-CFDs).\n"
                   "Alle Regeln wurden nur auf Daten von 2016 bis 2022 gewählt und danach eingefroren.", kicker="GRUPPENARBEIT · NY-OPEN ORB")
    WD = {None: "kein Tag ausgeschlossen", "Monday": "montags kein Handel", "Tuesday": "dienstags kein Handel",
          "Wednesday": "mittwochs kein Handel", "Thursday": "donnerstags kein Handel", "Friday": "freitags kein Handel"}
    steps = [
        ("1  Range", "Die erste 15-Minuten-Kerze nach der Eröffnung um 09:30 New York bildet die Opening Range (Hoch und Tief)."),
        ("2  Filter", "Gehandelt wird nur an Tagen ohne klaren übergeordneten Trend. Der Trend wird gemessen mit einem EMA-Band aus\n"
                      "4-Stunden-, Tages- und Wochen-EMAs am Vortag. Zeigt es klar nach oben oder unten, bleibt der Tag aus."),
        ("3  Einstieg", "Eine Kauf-Stop-Order liegt am Range-Hoch, beim S&P 500 zusätzlich eine Verkauf-Stop-Order am Range-Tief.\n"
                        "Die zuerst ausgelöste Seite gilt (eine Position je Tag). Beim Nasdaq 100 nur die Kauf-Seite."),
        ("4  Stop", "Der Stop liegt 1,0 × ATR (15 Minuten) unter dem Einstieg. Dieser Abstand ist 1 R, das Risiko je Trade."),
        ("5  Ausstieg", "Ziel bei 8 R. Wird es nicht erreicht, schließt der Trade spätestens um 16:00 New York. Keine Position über Nacht."),
    ]
    y = H - 2.05
    for head, txt in steps:
        ax.add_patch(FancyBboxPatch((0.55, y - 0.52), 1.55, 0.5, boxstyle="round,pad=0,rounding_size=0.06", fc="#eef3fb", ec="none"))
        ax.text(0.7, y - 0.27, head, fontsize=10, weight="bold", color="#2b6cb0", va="center")
        ax.text(2.3, y - 0.27, txt, fontsize=9, color=INK, va="center", linespacing=1.4)
        y -= 0.68
    ax.text(0.55, y - 0.15, "Unterschiede je Index", fontsize=11, weight="bold", color=INK)
    cols = [("", 2.2), ("S&P 500", 4.2), ("Nasdaq 100", 4.2)]
    yy = y - 0.4
    header(ax, cols, 0.55, yy - 0.4, 0.4)
    DIRS_T = {"long": "nur Long (Kauf am Range-Hoch)", "short": "nur Short", "beide": "Long und Short (erster Ausbruch zählt)"}
    diff_rows = [
        ["Richtung", DIRS_T[WIN["SP500"]["dirs"]], DIRS_T[WIN["NASDAQ"]["dirs"]]],
        ["Teilgewinn", "50 % bei 3 R, Rest läuft bis 8 R / 16:00" if WIN["SP500"]["partial"] else "keiner",
         "50 % bei 3 R, Rest läuft bis 8 R / 16:00" if WIN["NASDAQ"]["partial"] else "keiner, alles läuft bis 8 R / 16:00"],
        ["Order-Storno", {"opposite": "Kauf-Order fällt weg, wenn zuerst das Range-Tief bricht", "none": "keins, Order gilt bis 16:00",
                          "sl": "Order fällt weg, wenn zuerst der Stop-Kurs erreicht wird"}[WIN["SP500"]["rule"]],
         {"opposite": "Kauf-Order fällt weg, wenn zuerst das Range-Tief bricht", "none": "keins, Order gilt bis 16:00",
          "sl": "Order fällt weg, wenn zuerst der Stop-Kurs erreicht wird"}[WIN["NASDAQ"]["rule"]]],
    ]
    table(ax, cols, diff_rows, 0.55, yy - 0.4, 0.42)
    ax.text(0.55, 0.45, "Warum das funktionieren könnte, steht auf Seite 8 (Mechanismus), warum genau diese Regeln, auf Seite 3 (Einstellungen)\n"
            "und Seite 7 (Overfitting). Alle Zahlen in R: 1 R = Risiko je Trade, also der Abstand vom Einstieg zum Stop.",
            fontsize=8, color=MUTED, linespacing=1.5)
    pdf.savefig(fig); plt.close(fig)

    # ============ Seite 1: Scorecard (Folien-Kriterien) ============
    fig, ax = page("Ist die nur auf IS optimierte ORB-Strategie profitabel?",
                   "Overfitting-Sperre: optimiert nur auf IS 07/2016–12/2022, eingefroren, dann einmal OOS 01/2023–09/2025 und einmal\n"
                   "Tresor 10/2025–09/2026 geöffnet. „Test“ = alles bis 30.09.2025 (wie Folie „Holdout“). M1, Kosten eingerechnet.")
    cols = [("Kriterium", 1.95), ("Mindestens", 1.5)] + [(c if c != "Portfolio" else "Portfolio", (10.6 - 3.45) / len(COLS)) for c in COLS]
    x0, y = 0.55, H - 2.25
    header(ax, cols, x0, y)
    rows = []
    r_cost, r_n, r_pf, r_h, r_ho, r_me = (["Kosten eingerechnet", "Gebühren + 1 Tick"], ["Anzahl Trades", "100 im Test"],
                                          ["Profit Factor", "über 1,3"], ["Beide Hälften", "jeweils im Plus"],
                                          ["Holdout (12 Monate)", "im Plus"], ["Mechanismus", "erklärbar"])
    for c in COLS:
        r, k = S[c]
        mt, mo, mh = m(part(r, "Test"), part(k, "Test")), m(part(r, "OOS")), m(part(r, "Tresor"))
        r_cost.append(("Erfüllt" if mt["x2"] > 0 else "Knapp", G if mt["x2"] > 0 else A,
                       f"Kosten {f(mt['cost'], 2, False)} R · ×2: Ø {f(mt['x2'], 2)}"))
        r_n.append((str(mt["n"]), G if mt["n"] >= 100 else R, f"{mt['py']:.0f} pro Jahr".replace(".", ",")))
        r_pf.append((f(mt["pf"], 2, False), kind_pf(mt["pf"]), f"nur OOS: {f(mo.get('pf', np.nan), 2, False)}"))
        ok = mt["h1"] > 0 and mt["h2"] > 0
        r_h.append((f"{f(mt['h1'], 0)} / {f(mt['h2'], 0)} R", G if ok else R, "nach Trade-Anzahl geteilt"))
        if mh.get("n", 0) >= 2:
            r_ho.append((f"{f(mh['sum'], 1)} R", G if mh["pf"] > 1.3 else (A if mh["sum"] > 0 else R),
                         f"PF {f(mh['pf'], 2, False)} · {mh['n']} Trades"))
        else:
            r_ho.append(("–", A, "zu wenig Trades"))
        r_me.append(("Plausibel", A, "Felder 1, 2, 4 gestützt (S. 8–9)"))
    rows = [r_cost, r_n, r_pf, r_h, r_ho, r_me]
    y = table(ax, cols, rows, x0, y, 0.66)
    ax.text(x0, y - 0.35, "Grün = erfüllt · Gelb = teilweise/knapp · Rot = nicht erfüllt.  R = Vielfaches des Risikos je Trade.  "
            "Kosten = gemessener Spread + Slippage, ohne Kommission (beim genutzten Broker 0).", fontsize=7.5, color=MUTED)
    ho = m(part(S["Portfolio"][0], "Tresor"))
    ax.add_patch(FancyBboxPatch((x0, y - 1.95), 10.6, 1.25, boxstyle="round,pad=0,rounding_size=0.08", fc="#f9e1df", ec="#e6b3ae"))
    ax.text(x0 + 0.2, y - 0.93, "Fazit: Im Tresor durchgefallen", fontsize=10.5, weight="bold", color=R[1], va="center")
    ax.text(x0 + 0.2, y - 1.12,
            "Bis 09/2025 erfüllt die Strategie alle messbaren Kriterien: genug Trades, PF über 1,3, beide Hälften im Plus, Kosten gedeckt.\n"
            f"Im Tresor verliert sie aber deutlich ({f(ho['sum'], 0)} R, PF {f(ho['pf'], 2, False)}). Nach der Holdout-Regel zählt das Ergebnis, egal wie:\n"
            "Diese Version ist nicht handelbar. Auch der t-Wert nach Korrektur für die vielen getesteten Varianten (Deflated Sharpe) besteht nicht.",
            fontsize=8.6, color=INK, va="top", linespacing=1.5)
    pdf.savefig(fig); plt.close(fig)

    # ============ Seite 2: Uebernommene Einstellungen ============
    fig, ax = page("Welche Einstellungen die Strategie nutzt",
                   "Nur die übernommenen Werte der nur auf IS 2016–2022 gewählten Konfiguration, keine verworfenen Alternativen.\n"
                   "Alles wurde vor dem Öffnen von OOS und Tresor eingefroren.")
    LIVECFG = {
        "SP500": dict(dirs="long", ribbon="neutral", weekday=None, rule="opposite", stop=0.6, target=6.0, partial=None, range_bars=1),
        "NASDAQ": dict(dirs="beide", ribbon="kein", weekday="Wednesday", rule="sl", stop=0.6, target=None, partial=None, range_bars=1),
        "US30": None}
    WD = {None: "keiner", "Monday": "ohne Montag", "Tuesday": "ohne Dienstag", "Wednesday": "ohne Mittwoch",
          "Thursday": "ohne Donnerstag", "Friday": "ohne Freitag"}
    params = [
        ("Einstieg", lambda c: "Stop-Order am Range-Hoch/-Tief"),
        ("Opening Range", lambda c: f"{15 * c['range_bars']} Min. ab 09:30 NY"),
        ("Richtung", lambda c: {"long": "nur long", "short": "nur short", "beide": "long + short"}[c["dirs"]]),
        ("Trendfilter (EMA-Ribbon)", lambda c: {"kein": "keiner", "neutral": "nur neutrale Tage", "mit_trend": "nur mit Trend"}[c["ribbon"]]),
        ("Wochentag", lambda c: WD[c["weekday"]]),
        ("Order-Storno", lambda c: {"none": "keins", "opposite": "bei Bruch der Gegenseite", "sl": "am geplanten SL"}[c["rule"]]),
        ("Stop", lambda c: f"{f(c['stop'], 1, False)} × M15-ATR"),
        ("Ziel", lambda c: "keins (Exit 16:00)" if c["target"] is None else f"{f(c['target'], 0, False)} R"),
        ("Teilziel", lambda c: "keins" if c["partial"] is None else f"{f(c['partial'], 0, False)} R (50 %)"),
        ("Ausstieg spätestens", lambda c: "16:00 NY"),
    ]
    insts = ["SP500", "NASDAQ"]
    cols = [("Einstellung", 2.8)] + [(i, 3.9) for i in insts]
    x0, y = 0.55, H - 2.3
    header(ax, cols, x0, y, 0.5)
    y_rows = y
    rh = 0.44
    for k, (name, fn) in enumerate(params):
        y_rows -= rh
        if k % 2 == 0:
            ax.add_patch(Rectangle((x0, y_rows), sum(w for _, w in cols), rh, fc="#f5f7fa", ec="none"))
        ax.plot([x0, x0 + sum(w for _, w in cols)], [y_rows, y_rows], color=LINE, lw=0.8)
        ax.text(x0 + 0.12, y_rows + rh / 2, name, fontsize=8.4, weight="bold", color=INK, va="center")
        x = x0 + 2.8
        for i in insts:
            ax.text(x + 0.12, y_rows + rh / 2, fn(WIN[i]) if WIN.get(i) else "—", fontsize=8.2, color=INK, va="center")
            x += 3.9
    ax.text(x0, y_rows - 0.35, "Optimiert wurden 7 Punkte je Index (Range, Richtung, Trendfilter, Storno, Stop, Ziel, Teilziel); Richtwert max. 9.",
            fontsize=7.8, color=MUTED)
    ax.text(x0, y_rows - 0.6, f"Versuche je Instrument (Trial-Register): " +
            " · ".join(f"{i} {sel['n_trials'][i]:,}".replace(",", ".") for i in insts) +
            ".  Fest vorgegeben (nicht optimiert): Einstiegsart, Ausstieg 16:00, kein Breakeven.", fontsize=7.8, color=MUTED)
    pdf.savefig(fig); plt.close(fig)

    # ============ Seite 3: OOS + Tresor ============
    fig, ax = page("Was OOS und Tresor zeigen",
                   "Kennzahlen je Zeitraum. Die IS-only-Konfiguration wurde vor dem Öffnen eingefroren; OOS und Tresor ließen sich\n"
                   "technisch nur je einmal öffnen. Das Ergebnis zählt, egal wie.")
    cols = [("", 2.3), ("Zeitraum", 1.0), ("Trades", 0.8), ("PF", 0.8), ("Ø R", 0.85), ("Σ R", 0.9), ("MaxDD R", 0.95),
            ("t-Wert", 0.85), ("Treffer", 0.85), ("Ø R bei\nKosten ×2", 1.3)]
    x0, y = 0.55, H - 2.25
    header(ax, cols, x0, y, 0.5)
    rows = []
    for label, src, keys in (("IS-only", S, COLS),):
        for c in keys:
            r, k = src[c]
            for p in ("IS", "OOS", "Tresor"):
                mm = m(part(r, p), part(k, p))
                if mm.get("n", 0) < 2:
                    continue
                name = f"{c} · {label}" if p == "IS" else ""
                rows.append([name, p, str(mm["n"]), (f(mm["pf"], 2, False), kind_pf(mm["pf"])), f(mm["avg"], 2), f(mm["sum"], 0),
                             f(mm["dd"], 0), f(mm["t"], 1), f"{mm['win'] * 100:.0f} %", f(mm["x2"], 2)])
    rh = min(0.42, 5.4 / max(len(rows), 1))
    TW = sum(w for _, w in cols)
    yy = y
    for i, row in enumerate(rows):
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
    dsr = rep[rep.part == "DSR"].set_index("instrument")["avg"].to_dict()
    dsr1 = rep[rep.part == "DSR_runde1"].set_index("instrument")["avg"].to_dict()
    ax.text(x0, yy - 0.35, "Deflated Sharpe (IS, Ziel > 0,95) gegen 3.780 Varianten dieser Runde: " +
            " · ".join(f"{i} {f(dsr.get(i, np.nan), 2, False)}" for i in LEGS) +
            "  |  gegen alle 22.680 aus Runde 1: " + " · ".join(f"{i} {f(dsr1.get(i, np.nan), 2, False)}" for i in LEGS) +
            "\nPF-Farbe: grün > 1,3 · gelb 1,0–1,3 · rot < 1,0.", fontsize=7.8, color=MUTED, va="top", linespacing=1.5)
    pdf.savefig(fig); plt.close(fig)

    # ============ Seite 4: Equity 10 Jahre ============
    fig, ax = page("Equity-Kurve: 10 Jahre, IS / OOS / Tresor",
                   "Kumuliert in R (1 R Risiko je Trade, ohne Zinseszins). Nur auf IS 2016–2022 optimierte Strategie,\n"
                   "danach eingefroren: OOS 2023–09/2025 und Tresor 10/2025–09/2026 je einmal geöffnet.")
    r_all = S["Portfolio"][0]
    start, end = r_all.index.min(), r_all.index.max()

    def style(a):
        for sp in ("top", "right", "left"):
            a.spines[sp].set_visible(False)
        a.spines["bottom"].set_color(LINE)
        a.grid(axis="y", color="#e9ecf0", lw=0.6)
        a.tick_params(colors=MUTED, labelsize=7.5, length=0)
        a.xaxis.set_major_locator(mdates.YearLocator())
        a.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        a.set_xlim(start - pd.Timedelta(days=20), end + pd.Timedelta(days=150))
        a.yaxis.set_major_formatter(lambda v, _: (f"{v:+.0f} R".replace("-", "−")) if v else "0")
        a.axvspan(IS_END, OOS_END, color="#eef3fb", zorder=0, lw=0)
        a.axvspan(OOS_END, end + pd.Timedelta(days=150), color="#fdf1dc", zorder=0, lw=0)
        a.axhline(0, color=LINE, lw=0.8)

    a1 = fig.add_axes([0.06, 0.47, 0.8, 0.29])
    style(a1)
    eq = r_all.cumsum()
    a1.step(eq.index, eq.values, where="post", color=C_SP, lw=1.9, zorder=3)
    top = eq.max()
    for x_, lab, c in ((start, "IS – optimiert", MUTED), (IS_END + pd.Timedelta(days=30), "OOS – einmal getestet", "#2b6cb0"),
                       (OOS_END + pd.Timedelta(days=20), "Tresor", A[1])):
        a1.text(x_, top * 1.02, lab, fontsize=8, color=c, weight="bold", va="bottom")
    a1.annotate(f"IS-only {f(eq.iloc[-1], 0)} R", (eq.index[-1], eq.iloc[-1]), xytext=(4, 0), textcoords="offset points",
                fontsize=8, weight="bold", color=INK, va="center")
    a1.set_title("Portfolio (" + " + ".join(LEGS) + ")", fontsize=9.5, color=INK, loc="left", weight="bold", pad=16)

    a2 = fig.add_axes([0.06, 0.07, 0.8, 0.3])
    style(a2)
    handles = []
    for i in LEGS:
        e = S[i][0].cumsum()
        a2.step(e.index, e.values, where="post", color=COL[i], lw=1.5, zorder=3)
        handles.append(Line2D([], [], color=COL[i], lw=1.5, label=f"{i}  {f(e.iloc[-1], 0)} R"))
    a2.legend(handles=handles, loc="upper left", fontsize=7.5, frameon=False, ncol=3)
    a2.set_title("Einzelne Beine (IS-only)", fontsize=9.5, color=INK, loc="left", weight="bold", pad=6)
    pdf.savefig(fig); plt.close(fig)

    # ============ Seite 6: Tresor auf dem 100k-Konto ============
    fig, ax = page("Der Tresor auf einem 100.000-$-Konto",
                   "10/2025–09/2026, einmal geöffnet. Risiko je Trade 1 % vom aktuellen Kontostand (mit Zinseszins); laufen S&P 500 und\n"
                   "Nasdaq 100 am selben Tag, trägt jeder Trade 1 %. Kosten (Spread + Slippage) sind eingerechnet.")
    acc_t = pd.read_csv(RES / "is_only_7p_account_tresor.csv", parse_dates=["date"]).set_index("date")
    a3 = fig.add_axes([0.06, 0.2, 0.55, 0.56])
    eqs = pd.concat([pd.Series([100_000.0], index=[acc_t.index.min() - pd.Timedelta(days=1)]), acc_t["equity"]])
    a3.step(eqs.index, eqs.values, where="post", color=C_SP, lw=1.9, zorder=3)
    a3.axhline(100_000, color=LINE, lw=0.9)
    for sp in ("top", "right", "left"):
        a3.spines[sp].set_visible(False)
    a3.spines["bottom"].set_color(LINE)
    a3.grid(axis="y", color="#e9ecf0", lw=0.6)
    a3.tick_params(colors=MUTED, labelsize=7.5, length=0)
    a3.xaxis.set_major_formatter(mdates.DateFormatter("%m/%y"))
    a3.yaxis.set_major_formatter(lambda v, _: f"{v / 1000:.0f}k $")
    a3.annotate(f"{eqs.iloc[-1] / 1000:.1f}k $".replace(".", ","), (eqs.index[-1], eqs.iloc[-1]), xytext=(4, 0),
                textcoords="offset points", fontsize=9, weight="bold", color=INK, va="center")
    a3.set_title("Kontostand (Tagesende)", fontsize=9.5, color=INK, loc="left", weight="bold", pad=6)
    # Kennzahlen rechts
    x0, y = 7.6, H - 2.25
    ax.text(x0, y, "Kennzahlen", fontsize=10.5, weight="bold", color=INK)
    names = {"Tresor": "Tresor", "OOS": "OOS (Vergleich)", "Gesamt": "10 Jahre (Vergleich)"}
    for _, row in ACC.iterrows():
        key = row.zeitraum.split()[0]
        y -= 0.36
        ax.text(x0, y, f"{names.get(key, key)} · {row.zeitraum.split(' ', 1)[1]}", fontsize=8.6, weight="bold",
                color=A[1] if key == "Tresor" else INK)
        for lab, val in (("Endstand", f"{row.end:,.0f} $".replace(",", ".")), ("Rendite", f"{f(row.ret * 100, 1)} %"),
                         ("Rendite p. a.", f"{f(row.cagr * 100, 1)} %"), ("Max Drawdown", f"{f(row.maxdd * 100, 1)} %"),
                         ("Trades", f"{int(row.trades)}")):
            y -= 0.22
            ax.text(x0 + 0.15, y, lab, fontsize=8, color=MUTED)
            ax.text(x0 + 2.2, y, val, fontsize=8, color=INK, weight="bold" if lab in ("Rendite", "Max Drawdown") else "normal")
        y -= 0.12
    ax.text(0.55, 0.45, "Startkapital je Zeitraum 100.000 $. Gleichzeitige Trades werden mit dem Kontostand vom Vortag gesized und am selben Abend\n"
            "gebucht (alle Trades schließen bis 16:00). Keine Kommission (beim genutzten Broker 0).", fontsize=7.8, color=MUTED, linespacing=1.5)
    pdf.savefig(fig); plt.close(fig)

    # ============ Seite 5: Overfitting ============
    fig, ax = page("Warum OOS angefasst wurde – und was jetzt gilt",
                   "Die ursprüngliche Version entstand über Wochen in vielen Stufen. Dabei wurde ab Stage 2 direkt auf OOS-Zahlen ausgewählt.")
    blocks = [
        ("Was passiert ist", [
            "Stage 3 wertete „alle Zahlen OOS“ aus, Stage 4a war ein „OOS-only-Scan“, die Exit-Gitter verlangten „IS und OOS positiv“,",
            "    und das NASDAQ-Storno (04.10.) wurde mit Blick auf OOS gewählt. Jeder dieser Blicke macht OOS ein Stück weit zu IS.",
            "Am Ende standen 15 auf den Daten gewählte Entscheidungen und mehrere hundert getestete Varianten, aber kein unberührter Zeitraum."]),
        ("Warum es passiert ist", [
            "Eine Prozesslücke: Der Standardprozess nannte den OOS-Split nur in Phase 6 als Prüfung („anderer Zeitraum als beim Fitting“).",
            "Für Phase 4/5 gab es keine Regel, nur auf IS zu optimieren, und kein Skript hinderte daran, OOS-Zahlen mit auszugeben."]),
        ("Was dieser Test leistet", [
            "Die Strategie wurde nur auf IS 2016–2022 neu ausgewählt, nach einer vorher festgelegten Regel: ≥ 100 Trades, PF > 1,3, beide",
            "    Hälften positiv, dann höchster t-Wert, geglättet über die Stop-/Ziel-Nachbarn (Plateau statt Spitze).",
            "Runde 1 (8 Punkte inkl. Wochentag, 22.680 Varianten je Index) fand Gewinner mit Wochentag-Ausschluss, die die Deflated-",
            "    Sharpe-Prüfung nicht bestanden. Daraufhin Runde 2: höchstens 9 optimierte Punkte je Index (Richtwert), genutzt 7, ohne Wochentag.",
            "    Runde 1 wurde vor jeder OOS-/Tresor-Berechnung verworfen; nur Runde 2 wurde eingefroren und geöffnet.",
            "Dann eingefroren und OOS sowie Tresor je genau einmal geöffnet (technisch gesperrt: ein zweites Öffnen bricht ab).",
            "Ergebnis: OOS hielt (PF 1,34), der Tresor nicht (PF 0,52). Genau dafür gibt es den Tresor: Ohne ihn hätte die Strategie",
            "    nach IS + OOS wie ein Treffer ausgesehen.",
            "Grenze: Die Gitter-Grenzen entstanden mit Wissen bis 09/2026. Der Test prüft den Prozess, nicht ein jungfräuliches Datenset.",
            "    Wirklich unberührt sind erst Forward-Daten ab dem 05.10.2026."]),
        ("Die Overfitting-Sperre (Standardprozess seit 05.10.2026)", [
            "1. Split IS / OOS / Tresor vor dem ersten Test registrieren, danach unveränderlich.",
            "2. In Phase 4/5 nur auf IS optimieren, keine OOS-Zahlen ausgeben.",
            "3. Jede Variante zählt (Trial-Register), der Gewinner braucht Deflated Sharpe > 0,95.",
            "4. Einfrieren, dann OOS einmal öffnen. Kein Nachjustieren auf OOS.",
            "5. Tresor einmal öffnen, das Ergebnis zählt, egal wie. 6. Nach dem Livegang nur Forward-Daten als Test.",
            "Die Sperre ist als Code umgesetzt: Split, Einfrieren und Öffnen werden protokolliert, Verstöße brechen ab."]),
    ]
    y = H - 1.75
    for head, lines in blocks:
        ax.text(0.55, y, head, fontsize=10.5, weight="bold", color=INK); y -= 0.28
        for ln in lines:
            ax.text(0.75, y, ln if ln.startswith(("    ", "1.", "2.", "3.", "4.", "5.")) else "• " + ln, fontsize=8.4, color=INK)
            y -= 0.235
        y -= 0.12
    pdf.savefig(fig); plt.close(fig)

    # ============ Seiten 6+7: Mechanismus + Literatur (aus v1) ============
    src = (HERE / "orb_pdf.py").read_text(encoding="utf-8")
    seg = src[src.index("    # ---------- Seite 2: Mechanismus-Felder"):src.index("    # ---------- Seite 4: Details")]
    seg = seg.replace("(Details auf Seite 3)", "(Details auf Seite 9)")
    seg = seg.replace("Größtes Risiko für Kriterium 1. Unser\\nBrutto-Edge liegt aber 4–5× höher (unten).",
                      "Größtes Risiko für Kriterium 1. Passt\\nzum Tresor-Ergebnis (Seite 4–6).")
    seg = seg.replace('"Ø R netto\\n(live, M1)"', '"Ø R netto\\n(IS-only, M1)"')
    kr = []
    for i, pts in (("SP500", ("0,69 Pkt", "0,80 Pkt")), ("NASDAQ", ("1,93 Pkt", "2,50 Pkt"))):
        r_, c_ = S[i]
        kr.append((i, pts[0], pts[1], f"{f(c_.mean(), 2, False)} R", f(r_.mean(), 3), f((r_ - c_).mean(), 2), f((r_ - 2 * c_).mean(), 2)))
    seg = re.sub(r"krows = \[.*?\]\n", "krows = " + repr(kr) + "\n", seg, flags=re.S)
    seg = seg.replace("Der Unterschied ist der Brutto-Edge (~0,6 R statt ~0,13 R) aus 15-Min-Range, Filtern und\\n",
                      "Der Unterschied ist der Brutto-Edge aus 15-Min-Range, Trendfilter und Stop-Order-Einstieg; er wurde\\n")
    seg = seg.replace("Storno-Regeln. Genau diese Teile wurden auf denselben Daten gewählt, deshalb ist der Live-Betrieb ab 05.10. der eigentliche Test.\\n",
                      "hier nur auf IS gewählt und dann einmal auf OOS und Tresor geprüft (Seite 4).\\n")
    seg = seg.replace("Tickmill nimmt auf Index-CFDs keine Kommission (Spread ist die einzige Gebühr).",
                      "Der genutzte Broker nimmt auf Index-CFDs keine Kommission (Spread ist die einzige Gebühr).")
    import textwrap
    exec(textwrap.dedent(seg), {**globals(), "pdf": pdf, "page": lambda t, s: page(t, s, "NY-OPEN ORB · STAND 06.10.2026")})

    # ============ Seite 8: Methode ============
    fig, ax = page("Wie die Zahlen entstanden sind", "Daten, Kosten, Aufteilung und Grenzen")
    blocks = [
        ("Daten", [
            "M1-Ausführung, M15-Range und -ATR, Dukascopy-CFD-Daten 07/2016–09/2026. Ohne Tick-Korrektur, für alle Kandidaten gleich",
            "    (Tick-Effekt laut 04.10.: −0,01 bis −0,04 R je Trade).",
            "Eigener Simulator, Trade für Trade gegen die Backtest-Engine abgeglichen (Abweichung 0)."]),
        ("Kosten", [
            "Gemessene Broker-Spreads (S&P 500 0,84 · Nasdaq 100 0,54 bps) + Slippage 0,45 bps Einstieg, 0,30 bps Ausstieg.",
            "Der genutzte Broker nimmt auf Index-CFDs keine Kommission. Bei Brokern mit Kommission wäre sie zusätzlich abzuziehen."]),
        ("Aufteilung", [
            "IS 28.07.2016–31.12.2022 (optimieren) · OOS 01.01.2023–30.09.2025 (einmal testen) · Tresor 01.10.2025–30.09.2026 (einmal).",
            "„Test“ auf Seite 2 = IS + OOS. Hälften nach Trade-Anzahl. PF = Gewinne in R / Verluste in R."]),
        ("Grenzen", [
            "Trefferquote meist unter 30 %: wenige große Gewinner tragen das Ergebnis, lange Verlustserien sind normal.",
            "Mechanismus nur durch Literatur gestützt, für unseren ORB nicht kausal getestet.",
            "Live kommen Ausführungs-Verzögerung und Abweichungen des Brokers dazu."]),
    ]
    y = H - 1.95
    for head, lines in blocks:
        ax.text(0.55, y, head, fontsize=11, weight="bold", color=INK); y -= 0.32
        for ln in lines:
            ax.text(0.75, y, ln if ln.startswith("    ") else "• " + ln, fontsize=8.5, color=INK); y -= 0.27
        y -= 0.18
    pdf.savefig(fig); plt.close(fig)

    # ============ Seite 9: Fuenf Zahlen ============
    fig, ax = page("Fünf Zahlen, die jedes Team zeigt",
                   f"Ausgefüllt für die IS-only-Strategie, Portfolio {' + '.join(LEGS)}. MaxDD zusätzlich in % bei {f(RISK_PCT, 1, False)} % Risiko je Trade.",
                   kicker="WAS WIR PRÜFEN · KENNZAHLEN")
    r, k = S["Portfolio"]
    P = {p: m(part(r, p), part(k, p)) for p in ("IS", "OOS", "Tresor")}
    for p in P:
        P[p]["acc_dd"] = acct_dd(part(r, p))

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
    spec = [("Profit Factor", "Summe Gewinne ÷ Summe Verluste", "über 1,3 nach Kosten", "pf",
             lambda mm: (f(mm["pf"], 2, False), None)),
            ("Ø Trade", "Netto ÷ Anzahl Trades", "deutlich über den Kosten", "avg",
             lambda mm: (f"{f(mm['avg'], 2)} R", (f"Kosten {f(mm['cost'], 2, False)} R = {mm['avg'] / mm['cost']:.1f}×".replace(".", ","))
                         if mm["avg"] > 0 else f"Kosten {f(mm['cost'], 2, False)} R")),
            ("Max Drawdown", "Größter Rückgang vom Kontohoch", "du hältst ihn aus", "dd",
             lambda mm: (f"{f(mm['dd'], 0)} R", f"Konto (1 %): {f(mm['acc_dd'], 1)} %")),
            ("Trades pro Jahr", "Anzahl ÷ Jahre", "genug zum Lernen", "py",
             lambda mm: (f"{mm['py']:.0f}", f"{mm['n']} Trades gesamt")),
            ("t-Wert", "Ø Trade ÷ Streuung × √Anzahl", "über 2", "t",
             lambda mm: (f(mm["t"], 2, False), None))]
    rows = []
    for name, how, good, key, fn in spec:
        row = [name, how, good]
        for p in ("IS", "OOS", "Tresor"):
            txt, sub = fn(P[p])
            row.append((txt, judge(key, P[p]), sub) if sub else (txt, judge(key, P[p])))
        rows.append(row)
    yb = y
    for i, row in enumerate(rows):
        yb -= 0.72
        if i % 2 == 0:
            ax.add_patch(Rectangle((x0, yb), sum(w for _, w in cols), 0.72, fc="#f5f7fa", ec="none"))
        ax.plot([x0, x0 + sum(w for _, w in cols)], [yb, yb], color=LINE, lw=0.8)
        x = x0
        for j, (val, (_, w)) in enumerate(zip(row, cols)):
            if isinstance(val, tuple):
                cell(ax, x, yb, w, 0.72, val[0], val[1], sub=val[2] if len(val) > 2 else None)
            else:
                ax.text(x + 0.12, yb + 0.36, val, fontsize=8.8, va="center", color=INK if j != 1 else MUTED,
                        weight="bold" if j == 0 else "normal")
            x += w
    tval = P["Tresor"]["t"]
    ax.text(x0, yb - 0.4, "Der t-Wert sagt: Wie sicher ist es, dass der Gewinn kein Zufall ist? Über 2 heißt grob: weniger als 5 % Wahrscheinlichkeit für Zufall.\n"
            "Im Tresor halten weder Ø Trade noch PF: Der negative t-Wert zeigt, dass der Verlust dort ebenfalls kaum Zufall ist.\n"
            "Grenzen der Farben: Ø Trade grün ab 2× Kosten · MaxDD grün bis 10 %, gelb bis 20 % Konto · Trades/Jahr grün ab 50. Konto: 1 % vom Kontostand je Trade.",
            fontsize=7.8, color=MUTED, va="top", linespacing=1.5)
    pdf.savefig(fig); plt.close(fig)


if PNG:
    build(_Png())
else:
    with PdfPages(OUT) as pdf:
        build(pdf)
print("ok")
