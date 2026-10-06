import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Rectangle

plt.rcParams["font.family"] = "DejaVu Sans"
OUT = r"C:\Users\andre\Forex-Backtesting\Claude outputs\orb_profitabilitaets_kriterien_20261005.pdf"
INK, MUTED, LINE, HEAD = "#1b2330", "#5b6574", "#d5dae1", "#1e2a3d"
G, A, R = ("#e3f3e6", "#1f7a3a"), ("#fdf1dc", "#9a6200"), ("#f9e1df", "#a8322a")
W, H = 11.69, 8.27


def page(title, sub):
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    ax.text(0.55, H - 0.55, "NY-OPEN ORB · STAND 05.10.2026", fontsize=9, color="#2b6cb0", weight="bold", family="DejaVu Sans Mono")
    ax.text(0.55, H - 1.0, title, fontsize=21, color=INK, weight="bold")
    ax.text(0.55, H - 1.3, sub, fontsize=9.5, color=MUTED, va="top", linespacing=1.4)
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
        ax.text(x + 0.14, y + h / 2 - 0.13, sub, fontsize=7.2, color=color if kind else MUTED, va="center")


import os
class _P:
    def __init__(s): s.n=0
    def savefig(s, f): f.savefig(OUT.replace(".pdf", f"_p{s.n}.png") if os.environ.get("PNG") else None, dpi=80) if os.environ.get("PNG") else None; s.n+=1
with (PdfPages(OUT) if not os.environ.get("PNG") else __import__("contextlib").nullcontext(_P())) as pdf:
    # ---------- Seite 1: Scorecard ----------
    fig, ax = page("Ist die beste ORB-Variante „profitabel“?",
                   "Live-Konfiguration seit 04.10.: SP500 long-only, Stop 0,6 ATR, Ziel 6R, Storno bei Bruch nach unten\n"
                   "NASDAQ long+short, Stop 0,6 ATR, kein Ziel (Exit 16:00), Storno am geplanten SL\n"
                   "US30 pausiert "
                   "(nur zum Vergleich).  M1-Daten, tick-korrigiert, 2019-01 bis 2026-09.")
    cols = [("Kriterium", 1.95), ("Mindestens", 1.45), ("SP500", 1.85), ("NASDAQ", 1.85),
            ("Portfolio SP+NQ", 1.85), ("US30 (pausiert)", 1.65)]
    TW = sum(w for _, w in cols)
    x0, y, rh = 0.55, H - 2.6, 0.64
    x = x0
    for name, w in cols:
        ax.add_patch(Rectangle((x, y), w, 0.45, fc=HEAD, ec="none"))
        ax.text(x + 0.14, y + 0.225, name, fontsize=9, color="white", va="center", weight="bold")
        x += w
    rows = [
        ("Kosten eingerechnet", "Gebühren + 1 Tick",
         [("Erfüllt", G, "Tickmill 0 Komm. · TTP/IQ offen")] * 3 + [("Erfüllt", G, "wie links")]),
        ("Anzahl Trades", "100 im Test",
         [("302", G, "Test vor Holdout"), ("374", G, "Test vor Holdout"),
          ("676", G, "Test vor Holdout"), ("337", G, "Test vor Holdout")]),
        ("Profit Factor", "über 1,3",
         [("1,65", G, "gesamt inkl. Holdout 1,54"), ("1,53", G, "gesamt inkl. Holdout 1,52"),
          ("1,58", G, "gesamt inkl. Holdout 1,53"), ("1,50", A, "gesamt 1,33 · ab 2023: 0,94")]),
        ("Beide Hälften", "jeweils im Plus",
         [("+109 R / +51 R", G, "PF 1,92 / 1,39"), ("+100 R / +74 R", G, "PF 1,62 / 1,44"),
          ("+211 R / +124 R", G, "PF 1,75 / 1,41"), ("+108 R / +34 R", G, "PF 1,81 / 1,23")]),
        ("Holdout (12 Monate)", "im Plus",
         [("+4,7 R", A, "PF 1,09 · 60 Trades · knapp"), ("+30,2 R", G, "PF 1,48 · 68 Trades"),
          ("+35,0 R", G, "PF 1,30 · 128 Trades"), ("−30,7 R", R, "PF 0,44 · 55 Trades")]),
        ("Mechanismus", "erklärbar",
         [("Plausibel", A, "Felder 1, 2, 4 gestützt, S. 2–3")] * 3 + [("Plausibel", A, "wie links")]),
    ]
    y -= rh
    for i, (k, m, vals) in enumerate(rows):
        if i % 2 == 0:
            ax.add_patch(Rectangle((x0, y), TW, rh, fc="#f5f7fa", ec="none"))
        ax.plot([x0, x0 + TW], [y, y], color=LINE, lw=0.8)
        x = x0
        cell(ax, x, y, cols[0][1], rh, k, bold=True); x += cols[0][1]
        cell(ax, x, y, cols[1][1], rh, m, color=MUTED); x += cols[1][1]
        for (t, kind, sub), (_, w) in zip(vals, cols[2:]):
            cell(ax, x, y, w, rh, t, kind, sub=sub)
            x += w
        y -= rh
    y += rh - 0.25
    ax.add_patch(FancyBboxPatch((x0, y - 1.15), TW, 1.15, boxstyle="round,pad=0,rounding_size=0.08",
                                fc="#eef3fb", ec="#c4d4ec"))
    ax.text(x0 + 0.2, y - 0.22, "Fazit", fontsize=10.5, weight="bold", color=INK, va="center")
    ax.text(x0 + 0.2, y - 0.4,
            "NASDAQ und das Portfolio erfüllen alle messbaren Kriterien. SP500 besteht alles außer einem überzeugenden Holdout\n"
            "(PF 1,09, 2026 bisher −4,3 R). US30 scheitert am Holdout, die Pause ist damit bestätigt. Bei allen Varianten ist die\n"
            "zweite Hälfte deutlich schwächer als die erste. Die 12 Holdout-Monate waren bei der Parameterwahl schon sichtbar (siehe Seite 4).",
            fontsize=8.8, color=INK, va="top", linespacing=1.5)
    ax.text(x0, 0.22, "Grün = erfüllt · Gelb = teilweise/knapp · Rot = nicht erfüllt.   "
            "R = Vielfaches des Risikos je Trade (1 R = Abstand Einstieg–Stop).", fontsize=7.5, color=MUTED)
    pdf.savefig(fig); plt.close(fig)

    # ---------- Seite 2: Mechanismus-Felder ----------
    fig, ax = page("Wer verliert an unserem ORB?",
                   "Die fünf Mechanismus-Felder, auf den ORB angewendet. Nicht nach einer profitablen Strategie suchen, sondern nach einem\n"
                   "dokumentierten Effekt mit Grund. Belegstand: eigene Daten + Literatur (Details auf Seite 3).")
    mcols = [("Feld", 1.75), ("Wer zahlt?", 1.55), ("Bezug zum ORB", 3.05), ("Belegstand", 2.35), ("Suchbegriffe", 1.9)]
    MW = sum(w for _, w in mcols)
    x0, y, rh = 0.55, H - 2.35, 0.86
    x = x0
    for name, w in mcols:
        ax.add_patch(Rectangle((x, y), w, 0.42, fc=HEAD, ec="none"))
        ax.text(x + 0.12, y + 0.21, name, fontsize=9, color="white", va="center", weight="bold"); x += w
    mrows = [
        ("Strukturelle Flows\nund Zwänge", "Wer handeln muss",
         "Ungleichgewicht aus der Eröffnungsauktion\n(Market-on-Open-Orders, Fondsflüsse,\nÜbernacht-Orders), das nach 09:30 abfließt.",
         ("Indiz + Literatur", G, "eigen: 58–65 % in erster M5-Kerze\nextern: Gamma-Hedging (Baltussen)"),
         "opening auction imbalance,\nfund flows"),
        ("Verhaltensfehler", "Wer zu spät oder\nfalsch reagiert",
         "Intraday-Momentum: Der frühe Ausbruch setzt\nsich fort, weil der Markt den Eröffnungsimpuls\nunterschätzt (Unterreaktion).",
         ("Indiz, aber Warnung", A, "extern: Gao 2018 belegt Effekt;\nseit 0DTE (2022) nicht mehr messbar"),
         "intraday momentum,\nunderreaction"),
        ("Risikoprämien", "Wer Risiko abgibt",
         "Long-only bei SP500 könnte bloßes Beta sein,\nalso eine Aktienprämie fürs Halten.",
         ("Widerlegt", R, "Cash-Session ohne Drift\n(t = 0,89, Bondarenko/Muravyev)"),
         "intraday equity premium"),
        ("Mikrostruktur und\nLiquidität", "Wer sofort\nhandeln will",
         "Stop-Orders sammeln sich über dem Range-Hoch\nund unter dem Range-Tief. Der Ausbruch löst sie\naus, die Kaskade treibt den Kurs weiter.",
         ("Literatur, nur FX", A, "Osler: Stops clustern an Marken,\nlösen Kaskaden aus (FX, nicht Index)"),
         "stop clustering, order\nflow, price clustering"),
        ("Information", "Wer Infos langsamer\nverarbeitet",
         "Nachrichten über Nacht werden in der ersten\nHandelsstunde eingepreist, und der Ausbruch\nzeigt die Richtung.",
         ("Schwach", A, "Infoweg Europa→NY ist tot\n(Kinoshita); Gap-Bezug offen"),
         "announcement effect,\novernight news"),
    ]
    y -= rh
    for i, (f, who, orb, (bt, kind, bsub), sb) in enumerate(mrows):
        if i % 2 == 0:
            ax.add_patch(Rectangle((x0, y), MW, rh, fc="#f5f7fa", ec="none"))
        ax.plot([x0, x0 + MW], [y, y], color=LINE, lw=0.8)
        x = x0
        for txt, (_, w), st in [(f, mcols[0], "b"), (who, mcols[1], "m"), (orb, mcols[2], "n")]:
            ax.text(x + 0.12, y + rh / 2, txt, fontsize=8.3 if st == "n" else 8.8, va="center", linespacing=1.3,
                    color=MUTED if st == "m" else INK, weight="bold" if st == "b" else "normal"); x += w
        w = mcols[3][1]
        bg, fg = kind
        ax.add_patch(FancyBboxPatch((x + 0.06, y + 0.07), w - 0.12, rh - 0.14, boxstyle="round,pad=0,rounding_size=0.06", fc=bg, ec="none"))
        ax.text(x + 0.14, y + rh - 0.22, bt, fontsize=8.8, color=fg, weight="bold", va="center")
        ax.text(x + 0.14, y + 0.3, bsub, fontsize=7.2, color=fg, va="center", linespacing=1.3); x += w
        ax.text(x + 0.12, y + rh / 2, sb, fontsize=7.8, va="center", color=MUTED, family="DejaVu Sans Mono", linespacing=1.3)
        y -= rh
    y += rh - 0.3
    ax.add_patch(FancyBboxPatch((x0, y - 1.25), MW, 1.25, boxstyle="round,pad=0,rounding_size=0.08", fc="#eef3fb", ec="#c4d4ec"))
    ax.text(x0 + 0.2, y - 0.22, "Einordnung", fontsize=10.5, weight="bold", color=INK, va="center")
    ax.text(x0 + 0.2, y - 0.4,
            "Stärkster Kandidat ist Feld 1: Options-Market-Maker mit Short-Gamma müssen in Kursrichtung hedgen (Baltussen et al., JFE 2021).\n"
            "Das ist ein Zwangs-Flow, kein Zufall. Feld 2 ist in der Literatur gut belegt, gilt seit dem 0DTE-Boom aber als abgeschwächt.\n"
            "Mit unseren Daten testbar: Ist der Edge an Tagen mit großem Gap bzw. hohem Volumen der ersten 15 Minuten größer? Gao und\n"
            "Zarattini fanden genau das (Aktien: +0,38 R bei extremem Volumen gegen −0,02 R bei normalem). Wenn ja, ist das Kriterium grün.",
            fontsize=8.6, color=INK, va="top", linespacing=1.5)
    pdf.savefig(fig); plt.close(fig)

    # ---------- Seite 3: Externe Belege ----------
    fig, ax = page("Was die Literatur dazu sagt",
                   "Web-Recherche 05.10.2026: Studien und Replikationen, die unsere Kriterien und Felder ergänzen oder infrage stellen")
    ecols = [("Quelle", 2.0), ("Befund", 5.15), ("Bedeutung für unseren ORB", 3.45)]
    EW = sum(w for _, w in ecols)
    x0, y, rh = 0.55, H - 1.95, 0.6
    x = x0
    for name, w in ecols:
        ax.add_patch(Rectangle((x, y), w, 0.4, fc=HEAD, ec="none"))
        ax.text(x + 0.12, y + 0.2, name, fontsize=9, color="white", va="center", weight="bold"); x += w
    erows = [
        ("Gao, Han, Li, Zhou\nJFE 2018 · SPY 1993–2013", "Erste halbe Stunde sagt die letzte halbe Stunde voraus (R² 1,6 %).\nStärker an volatilen Tagen, Tagen mit hohem Volumen und News-Tagen.", "Feld 2 belegt. Liefert die Test-Idee:\nEdge nach Gap/Volumen aufteilen.", G),
        ("Baltussen, Da, Lammers,\nMartens · JFE 2021", "Intraday-Momentum in über 60 Futures (1974–2020). Ursache: Gamma-Hedging\nvon Options-Market-Makern und gehebelten ETFs, das in Kursrichtung handelt.", "Feld 1: Wer zahlt, ist ein Zwangs-Flow.\nStärkster Mechanismus-Kandidat.", G),
        ("FirmTape-Messung\n1.085 SPX-Tage 2022–26", "Klassisches Intraday-Momentum ist seit der 0DTE-Ära flach (t = +0,6, jedes\nJahr ~0). Nur an Short-Gamma-Tagen (15 %) noch da: t = +3,1. Blog, kein Paper.", "Warnung: passt zur schwächeren\n2. Hälfte. Gamma-Filter wäre ein Test.", A),
        ("Zarattini, Barbon, Aziz\nSSRN 2024 · US-Aktien", "Ungefiltertes 5-Min-ORB über 7.000 Aktien: nur 3,2 % p. a. Mit „Stocks in Play“\n(abnormales Eröffnungsvolumen): Ø +0,38 R gegen −0,02 R bei normalem Volumen.", "Ungleichgewicht zur Eröffnung trägt den\nEdge. Stützt Feld 1 und den Volumen-Test.", G),
        ("Zarattini, Aziz\nSSRN 2023 · QQQ", "5-Min-ORB auf QQQ 2016–23: 24 % Treffer, +0,13 R je Trade, 33 % p. a. mit Hebel.\nSlippage nicht modelliert.", "Gleiche Gewinnstruktur wie bei uns\n(wenige große Gewinner).", A),
        ("MQL5-Replikation\n09/2026 · 5 Index-CFDs", "Paper auf NQ/SPX/Dow/DAX/FTSE nachgebaut, M1, 2015–2026: brutto +0,05 bis +0,13 R,\nnetto bei keinem Markt von null unterscheidbar. „Der Edge ist so groß wie der Spread.“", "Größtes Risiko für Kriterium 1. Unser\nBrutto-Edge liegt aber 4–5× höher (unten).", R),
        ("Osler · NY Fed 2003/05\nFX-Orderbücher", "Stop-Buy-Orders clustern knapp über runden Marken, Stop-Sells knapp darunter.\nTrends laufen dort messbar schneller (Preiskaskaden).", "Feld 4 plausibel, aber nur für FX belegt,\nnicht für Index-Range-Grenzen.", A),
    ]
    y -= rh
    for i, (q, b, m, kind) in enumerate(erows):
        if i % 2 == 0:
            ax.add_patch(Rectangle((x0, y), EW, rh, fc="#f5f7fa", ec="none"))
        ax.plot([x0, x0 + EW], [y, y], color=LINE, lw=0.8)
        ax.add_patch(Rectangle((x0, y + 0.08), 0.05, rh - 0.16, fc=kind[1], ec="none"))
        ax.text(x0 + 0.14, y + rh / 2, q, fontsize=7.7, weight="bold", color=INK, va="center", linespacing=1.3)
        ax.text(x0 + ecols[0][1] + 0.12, y + rh / 2, b, fontsize=7.1, color=INK, va="center", linespacing=1.35)
        ax.text(x0 + ecols[0][1] + ecols[1][1] + 0.12, y + rh / 2, m, fontsize=7.5, color=kind[1], va="center",
                linespacing=1.35, weight="bold")
        y -= rh
    y += rh - 0.4
    ax.text(x0, y, "Kosten-Gegenprobe: unsere Annahmen gegen die Replikation", fontsize=10.5, weight="bold", color=INK)
    kc = [("", 1.3), ("Unsere Kosten\nRundturn", 1.55), ("Replikation\nRundturn", 1.45), ("Kosten\nin R", 1.1),
          ("Ø R netto\n(live, M1)", 1.35), ("Ø R bei\nKosten ×2", 1.3), ("Ø R bei\nKosten ×3", 1.3)]
    y -= 0.5
    x = x0
    for name, w in kc:
        ax.text(x + 0.1, y + 0.15, name, fontsize=7.6, color=MUTED, va="center", weight="bold", linespacing=1.2); x += w
    krows = [("SP500", "0,69 Pkt", "0,80 Pkt", "0,19 R", "+0,455", "+0,27", "+0,09"),
             ("NASDAQ", "1,93 Pkt", "2,50 Pkt", "0,14 R", "+0,463", "+0,32", "+0,19")]
    for r_ in krows:
        y -= 0.3
        ax.plot([x0, x0 + sum(w for _, w in kc)], [y + 0.3, y + 0.3], color=LINE, lw=0.6)
        x = x0
        for j, ((_, w), v) in enumerate(zip(kc, r_)):
            ax.text(x + 0.1, y + 0.14, v, fontsize=8.4, color=INK, va="center", weight="bold" if j in (0, 4) else "normal"); x += w
    ax.text(x0, y - 0.15, "Unsere Kosten liegen nahe an der Replikation. Der Unterschied ist der Brutto-Edge (~0,6 R statt ~0,13 R) aus 15-Min-Range, Filtern und\n"
            "Storno-Regeln. Genau diese Teile wurden auf denselben Daten gewählt, deshalb ist der Live-Betrieb ab 05.10. der eigentliche Test.\n"
            "Tickmill nimmt auf Index-CFDs keine Kommission (Spread ist die einzige Gebühr).",
            fontsize=7.8, color=MUTED, va="top", linespacing=1.45)
    pdf.savefig(fig); plt.close(fig)

    # ---------- Seite 4: Details ----------
    fig, ax = page("Wie die Zahlen entstanden sind",
                   "Was gemessen wurde, wie geteilt wurde und was die Zahlen nicht aussagen")
    blocks = [
        ("Datengrundlage", [
            "M1-Kerzen 2019-01 bis 2026-09. Füll-Minuten, in denen Stop und Einstieg zusammenfallen, sind mit Dukascopy-Ticks aufgelöst.",
            "Frühere M5-Zahlen lagen 25–45 % zu hoch, weil M5 den Stop in der Füll-Kerze nicht prüft. Deshalb sind diese Werte niedriger.",
            "Trade-Reihen: scripts/research_orb_m1_candidates_montecarlo.py (leg_series), dieselbe Logik wie live seit 04.10.2026."]),
        ("Kosten", [
            "Gemessene Broker-Spreads (SP500 0,84 · US30 0,48 · NASDAQ 0,54 bps) + Slippage 0,45 bps beim Einstieg, 0,30 bps beim Ausstieg.",
            "Rundturn SP500 ≈ 0,69 Pkt (≈ 0,19 R), NASDAQ ≈ 1,93 Pkt (≈ 0,14 R). Slippage allein liegt über 1 Tick. Kommission nicht modelliert.",
            "Tickmill (EK): Index-CFDs ohne Kommission, also erfüllt. TTP/IQ: Kommission nicht geprüft. Bei doppelten Kosten bleibt alles positiv."]),
        ("Aufteilung", [
            "Test = alles vor dem Holdout (2019-01 bis 2025-09). Die Hälften teilen den Test nach Trade-Anzahl (z. B. SP500 je 151 Trades).",
            "Holdout = die letzten 12 Monate (2025-10 bis 2026-09).",
            "Profit Factor = Summe der Gewinne in R / Summe der Verluste in R, jeder Trade mit gleichem Risiko."]),
        ("Grenzen – bitte mitlesen", [
            "Kein blinder Holdout: Stop 0,6 ATR, das 6R-Ziel (21.09.) und das NASDAQ-Storno (04.10.) wurden mit Daten bis 09/2026 gewählt.",
            "    Wirklich unberührte Daten gibt es erst ab dem 05.10.2026, also ab dem Live-Betrieb.",
            "Trefferquote nur 16–23 %: Das Ergebnis lebt von wenigen großen Gewinnern. Lange Verlustserien sind normal.",
            "Mechanismus: Die Literatur stützt Feld 1, 2 und 4 (Seite 3), für unseren ORB ist aber keines kausal getestet.",
            "Live kommt die Abfrage-Latenz dazu: Blitz-Trades beim NASDAQ-Storno kosten im Backtest rund −21 R von +205 R."]),
    ]
    y = H - 2.0
    for head, lines in blocks:
        ax.text(0.55, y, head, fontsize=11, weight="bold", color=INK)
        y -= 0.32
        for ln in lines:
            ax.text(0.75, y, ln if ln.startswith("    ") else "• " + ln, fontsize=8.6, color=INK)
            y -= 0.27
        y -= 0.18
    ax.text(0.55, 0.35, "Quellen: knowledge/projects/orb-order-storno-und-haltedauer.md · "
            "ny_open_orb/results/fill_minute_ticks.csv · Web-Quellen siehe Seite 3 · erstellt 05.10.2026", fontsize=7.5, color=MUTED)
    pdf.savefig(fig); plt.close(fig)
print("ok")
