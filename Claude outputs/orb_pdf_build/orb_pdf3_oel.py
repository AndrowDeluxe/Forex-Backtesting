"""ORB-Kriterien-PDF v3: v2 (unveraendert) + 3 Seiten Gegenprobe Oel (11.10.2026).

Daten: scripts/research_orb_oel_vergleich.py -> ny_open_orb/results/oel_vergleich_*.csv
"""
import os
import re
from pathlib import Path

HERE = Path(__file__).parent
OUT3 = r"C:\Users\andre\Forex-Backtesting\Claude outputs\orb_profitabilitaets_kriterien_oel_20261011.pdf"

src = (HERE / "orb_pdf2.py").read_text(encoding="utf-8")
src = src[: src.index("\nif PNG:")]          # nur Definitionen + Daten, kein Build
os.chdir(HERE)
g = {"__file__": str(HERE / "orb_pdf2.py"), "__name__": "orb_pdf2"}
exec(compile(src, "orb_pdf2.py", "exec"), g)

plt, pd, np, PdfPages = g["plt"], g["pd"], g["np"], g["PdfPages"]
page0, table, header, RES = g["page"], g["table"], g["header"], g["RES"]
G, A, R, INK, MUTED, LINE = g["G"], g["A"], g["R"], g["INK"], g["MUTED"], g["LINE"]
C_SP, C_NQ = g["C_SP"], g["C_NQ"]
C_OIL = "#3d3d3d"
W, H = g["W"], g["H"]
FancyBboxPatch = g["FancyBboxPatch"]
KICK = "NY-OPEN ORB · GEGENPROBE ÖL · STAND 11.10.2026"

perf = pd.read_csv(RES / "oel_vergleich_perf.csv")
mech = pd.read_csv(RES / "oel_vergleich_mechanik.csv")
eia = pd.read_csv(RES / "oel_vergleich_eia.csv")
corr = pd.read_csv(RES / "oel_vergleich_korrelation.csv").set_index("periode")


def page(t, s):
    return page0(t, s, KICK)


def de(v, d=2, sign=True):
    if pd.isna(v):
        return "–"
    s = f"{v:+.{d}f}" if sign else f"{v:.{d}f}"
    return s.replace("-", "−").replace(".", ",")


def pf_kind(pf):
    return G if pf > 1.3 else (A if pf >= 1.0 else R)


def box(ax, x, y, w, h, title, lines, kind=("#edf2fb", INK)):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.08", fc=kind[0], ec="#c3d3ee"))
    ax.text(x + 0.22, y + h - 0.3, title, fontsize=11, weight="bold", color=INK, va="center")
    ax.text(x + 0.22, y + h - 0.55, "\n".join(lines), fontsize=8.1, color=INK, va="top", linespacing=1.55)


LEGS = [("SP500", "index", "S&P 500"), ("NASDAQ", "index", "Nasdaq 100"),
        ("OIL", "index", "Öl · 09:30–16:00"), ("OIL", "oel", "Öl · 09:00–14:30")]


def p(inst, uhr, konfig, per):
    return perf[(perf.instrument == inst) & (perf.uhr == uhr) & (perf.konfig == konfig) & (perf.periode == per)].iloc[0]


def mrow(inst, uhr, zr):
    return mech[(mech.instrument == inst) & (mech.uhr == uhr) & (mech.zeitraum == zr)].iloc[0]


def page_result(pdf):
    fig, ax = page("Gegenprobe Öl: Trägt derselbe ORB auf WTI?",
                   "Dieselben Regeln, nichts neu optimiert, auf WTI-Öl (Dukascopy-CFD, M1, 07/2016–09/2026) angewendet, einmal zur Index-Uhrzeit\n"
                   "und einmal zur Öl-Uhrzeit (NYMEX-Pit-Open 09:00, Settlement 14:30). 4 Konfigurationen × 2 Uhren = 8 Versuche, alle gezählt.")
    cols = [("Konfiguration", 1.95), ("Markt", 1.6), ("IS 2016–22\nPF · Ø R", 1.95), ("OOS 2023–09/25\nPF · Ø R", 1.95),
            ("Tresor 10/25–09/26\nPF · Ø R", 1.95), ("Ø R brutto\n(IS)", 1.15)]
    x0, y = 0.55, H - 2.2
    header(ax, cols, x0, y, h=0.55)
    names = {"SP500-Gewinner": "Nur neutrale Tage,\nlong + short (= SP500)", "ungefiltert": "Ohne Trendfilter,\nlong + short",
             "mit Trend": "Nur in Trendrichtung,\nlong + short"}
    rows = []
    for k, label in names.items():
        for j, (inst, uhr, mk) in enumerate(LEGS):
            row = [label if j == 0 else "", mk]
            for per in ("IS", "OOS", "Tresor"):
                q = p(inst, uhr, k, per)
                row.append((f"{de(q.pf, 2, False)}  ·  {de(q.avg)} R", pf_kind(q.pf), f"{int(q.n)} Trades · t {de(q.t, 1)}"))
            qi = p(inst, uhr, k, "IS")
            row.append(de(qi.avg + qi.cost_r))
            rows.append(row)
    rh = 0.36
    yb = table(ax, cols, rows, x0, y, rh, first_bold=True)
    for i in range(1, 3):  # Trennlinien zwischen den Konfigurationsblöcken
        yy = y - i * 4 * rh
        ax.plot([x0, x0 + sum(w for _, w in cols)], [yy, yy], color="#8a93a3", lw=1.2)
    ax.text(x0, yb - 0.25,
            "Stop 1,0 × M15-ATR, Ziel 8 R, spätestens Sitzungsende. Kosten Öl: 4,0 bps Spread (Annahme, ~3 Cent bei 70–80 $) + dieselbe Slippage wie bei den Indizes,\n"
            "das sind ~0,15 R je Trade (Indizes 0,08–0,19 R). April 2020 (WTI nahe null) ist ausgelassen. PF-Farbe: grün > 1,3 · gelb 1,0–1,3 · rot < 1,0.",
            fontsize=7.4, color=MUTED, va="top", linespacing=1.5)
    box(ax, 0.55, 0.22, W - 1.1, 0.92, "Ergebnis: Öl hat keinen ORB-Edge, weder zur Index- noch zur Öl-Uhrzeit",
        ["Bester Wert in IS: PF 1,03, t 0,3. Brutto liegt Öl bei +0,04 bis +0,18 R je Trade; das fressen die Kosten (~0,15 R) ganz auf.",
         "Auch bei halben Kosten bliebe bestenfalls ~+0,1 R mit t ~1. Zum Vergleich: die Indizes hatten in IS auf neutralen Tagen +0,42 bis +0,46 R brutto."])
    pdf.savefig(fig); plt.close(fig)


def page_mech(pdf):
    fig, ax = page("Welchen Mechanismus verfolgt Öl gegenüber S&P und Nasdaq?",
                   "Beschreibende Messungen, keine Auswahl. Je Markt dieselben Kennzahlen; Öl hier zur Index-Uhrzeit (09:30–16:00),\n"
                   "in Klammern zur Öl-Uhrzeit (09:00–14:30), wo sie abweicht.")
    cols = [("Messung", 3.0), ("S&P 500", 1.9), ("Nasdaq 100", 1.9), ("Öl (WTI)", 2.3), ("Was es heißt", 1.5)]
    cols[-1] = ("Lesart", W - 1.1 - sum(w for _, w in cols[:-1]))
    x0, y = 0.55, H - 2.25
    header(ax, cols, x0, y)

    def three(fn, d=2, sign=True, oil_alt=True):
        a = [de(fn("SP500", "index"), d, sign), de(fn("NASDAQ", "index"), d, sign)]
        o = de(fn("OIL", "index"), d, sign)
        if oil_alt:
            o += f"  ({de(fn('OIL', 'oel'), d, sign)})"
        return a + [o]

    rs = lambda zr, col: (lambda i, u: mrow(i, u, zr)[col])  # noqa: E731
    pct = lambda zr, col: (lambda i, u: 100 * mrow(i, u, zr)[col])  # noqa: E731
    rows = [
        ["Eröffnungsschock: 1. 15-Min-Kerze\nin ATR (Median, IS)", *three(rs("Periode IS", "range_atr"), 1, False), "Öl kaum Schock"],
        ["Folgequote: 1. Ausbruch schließt\njenseits des Levels (IS, %)", *three(pct("Periode IS", "folgequote"), 0, False), "überall Münzwurf"],
        ["Intraday-Momentum (Gao), t-Wert IS\n(erste 30 Min. → letzte 30 Min.)", *three(rs("Periode IS", "im_t"), 1), "nirgends Momentum"],
        ["Trendfilter-Spread IS / OOS\n(Ø R neutral − Ø R mit Trend)",
         *[f"{de(mrow(i, u, 'Periode IS').ribbon_spread)} / {de(mrow(i, u, 'Periode OOS').ribbon_spread)}"
           for i, u in (("SP500", "index"), ("NASDAQ", "index"))],
         f"{de(mrow('OIL', 'index', 'Periode IS').ribbon_spread)} / {de(mrow('OIL', 'index', 'Periode OOS').ribbon_spread)}", "bei Öl schwach"],
        ["Trendfilter-Spread im Tresor", *three(rs("Periode Tresor", "ribbon_spread")), "kippt nur Index"],
        ["Tag-zu-Tag (heute auf gestern),\nt-Wert IS → Tresor",
         *[f"{de(mrow(i, u, 'Periode IS').trend_t, 1)} → {de(mrow(i, u, 'Periode Tresor').trend_t, 1)}"
           for i, u in (("SP500", "index"), ("NASDAQ", "index"))],
         f"{de(mrow('OIL', 'index', 'Periode IS').trend_t, 1)} → {de(mrow('OIL', 'index', 'Periode Tresor').trend_t, 1)}", "dreht überall"],
        ["Korrelation Sitzung Öl ↔ S&P\nIS → Tresor", "–", "–",
         f"{de(corr.loc['IS', 'korr_sitzung_oil_sp500'])} → {de(corr.loc['Tresor', 'korr_sitzung_oil_sp500'])}", "Vorzeichen kippt"],
    ]
    yb = table(ax, cols, rows, x0, y, 0.5)
    w_ = eia.set_index(["tag", "periode"])
    ax.text(x0, yb - 0.22,
            f"Öl-eigener Kandidat EIA-Lagerdaten (Mi 10:30): ORB am Mittwoch IS {de(w_.loc[('Mittwoch (EIA)', 'IS'), 'avg'])} · OOS "
            f"{de(w_.loc[('Mittwoch (EIA)', 'OOS'), 'avg'])} · Tresor {de(w_.loc[('Mittwoch (EIA)', 'Tresor'), 'avg'])} R je Trade: kein stabiler Effekt.\n"
            "Rauschen grob: Trendfilter-Spread ±0,2 R im Tresor (~100 Trades je Topf); t-Werte über 2 gelten als belastbar.",
            fontsize=7.4, color=MUTED, va="top", linespacing=1.5)
    box(ax, 0.55, 0.3, W - 1.1, 1.55, "Einordnung: Was Öl über unseren ORB verrät",
        ["1. Öl hat keinen Eröffnungsschock (1,5 statt 2,4–3,0 ATR) und keinen ORB-Edge. Bei den Indizes treten beide zusammen auf. Das stützt",
         "    Feld 1 (Auktion/Zwangsflüsse zur Eröffnung) als Index-Mechanismus, indirekt, nicht kausal.",
         "2. Der Kipp des Trendfilters 2026 ist index-spezifisch: Bei Öl war der Filter nie stark und dreht im Tresor nicht deutlich.",
         "3. Marktübergreifend ist aber der Wechsel von Umkehr zu Fortsetzung über Tage: bis 09/2025 bei allen drei eher Umkehr, im Tresor",
         "    bei allen drei Fortsetzung, obwohl Öl und S&P dort gegenläufig laufen. Einzeln nicht signifikant, aber dreimal gleiche Richtung."])
    pdf.savefig(fig); plt.close(fig)


def page_years(pdf):
    fig, ax = page("Je Jahr: Trendfilter und Tag-zu-Tag-Verhalten",
                   "Links: Vorteil „nur neutrale Tage“ gegenüber „nur in Trendrichtung“ (Ø R je Trade). Rechts: t-Wert der Regression\n"
                   "Sitzungsrendite heute auf gestern (über null = Fortsetzung über Tage, unter null = Umkehr). Öl zur Index-Uhrzeit.")
    years = [str(y) for y in range(2017, 2026)] + ["2026 bis 09"]
    xs = np.arange(len(years))
    lab = [y.replace(" bis 09", "*") for y in years]
    for k, (col, title, ylab) in enumerate((("ribbon_spread", "Trendfilter-Spread", "Ø R neutral − mit Trend"),
                                            ("trend_t", "Tag-zu-Tag-Trend", "t-Wert"))):
        a = fig.add_axes([0.07 + k * 0.48, 0.2, 0.41, 0.52])
        for inst, c, name in (("SP500", C_SP, "S&P 500"), ("NASDAQ", C_NQ, "Nasdaq 100"), ("OIL", C_OIL, "Öl (WTI)")):
            v = [mrow(inst, "index", y)[col] for y in years]
            a.plot(xs, v, marker="o", ms=4, lw=2 if inst != "OIL" else 2.4, color=c, label=name,
                   ls="-" if inst != "OIL" else "--")
        a.axhline(0, color="#8a93a3", lw=0.9)
        if col == "trend_t":
            for lvl in (2, -2):
                a.axhline(lvl, color=LINE, lw=0.9, ls=":")
        a.axvspan(len(years) - 1.5, len(years) - 0.5, color="#fdf1dc", zorder=0)
        a.set_xticks(xs); a.set_xticklabels(lab, fontsize=8)
        a.tick_params(axis="y", labelsize=8)
        a.set_title(title, fontsize=11, weight="bold", loc="left", color=INK)
        a.set_ylabel(ylab, fontsize=8.5, color=MUTED)
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
        if k == 0:
            a.legend(fontsize=8, frameon=False, loc="lower left")
    ax.text(0.55, 0.75,
            "* 2026 = Jan.–Sep. (Tresor-Jahr, gelb). Kalenderjahre; 2025 enthält schon drei Tresor-Monate. Öl 2026 ohne den 30.09. (Datenende 29.09.).\n"
            "Lesart: Der Trendfilter-Vorteil der Indizes war 2017–2025 fast immer positiv und fällt 2026 tief ins Minus; Öl schwankt um einen kleinen Wert.\n"
            "Das Tag-zu-Tag-Verhalten steigt 2026 bei allen drei Märkten gleichzeitig über null, 2025 lag es bei den Indizes stark darunter.",
            fontsize=7.6, color=MUTED, va="top", linespacing=1.55)
    pdf.savefig(fig); plt.close(fig)


with PdfPages(OUT3) as pdf:
    g["build"](pdf)
    page_result(pdf)
    page_mech(pdf)
    page_years(pdf)
print("ok", OUT3)
