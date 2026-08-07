"""Strategie Bestandteile -- Risk Management.

Reine Wissens-/Referenzseite (wie orb_writeup.py): generalisiert den Denkansatz
"wie senkt man Max Drawdown, ohne die Kante der Strategie kaputtzumachen" -- aus
zwei konkreten Experimenten am OU-Modell (2026-08-07): sweep_risk_caps.py
(in-sample 2018-2024) und oos_holdout_riskcap.py (echter 2025+-Holdout). Die
zentrale Lehre ist nicht "welcher Wert ist der beste", sondern dass die
In-Sample-Antwort und die Out-of-Sample-Antwort sich WIDERSPRACHEN -- ein
eigenstaendiger Beleg fuer die Overfitting-Disziplin, die dieses ganze Projekt
durchzieht, diesmal auf einen Sizing-/Risk-Parameter statt auf Entry-Regeln
angewendet."""

import pandas as pd

import streamlit as st

st.set_page_config(page_title="Risk Management -- Strategiebestandteile", page_icon=":material/shield:", layout="wide")

st.markdown("## :material/shield: Risk Management -- Strategiebestandteile")
st.caption(
    "Generalisierter Denkansatz zur Drawdown-Reduktion, hergeleitet aus zwei "
    "Experimenten am OU-Modell (S&amp;P 500, siehe 'OU-Modell Paper-Backtest'): "
    "sweep_risk_caps.py (in-sample) und oos_holdout_riskcap.py (echter "
    "2025-heute-Holdout)."
)

st.markdown("### Die Kernidee: zwei verschiedene Risiko-Hebel, ein grosser Unterschied")
col_a, col_b = st.columns(2)
with col_a:
    st.info(
        "**Risiko pro Trade** (`risk_pct`)\n\nWie viel % des Kontos wird gegen den "
        "Stop-Abstand EINES einzelnen Trades riskiert. Steuert die Groesse einer "
        "einzelnen Position.",
        icon=":material/pin_drop:",
    )
with col_b:
    st.success(
        "**Aggregiertes Risiko** (`max_total_risk_pct`)\n\nDeckel auf die SUMME "
        "des Risikos ueber ALLE gleichzeitig offenen Positionen. Steuert, wie "
        "viele korrelierte Wetten gleichzeitig laufen duerfen.",
        icon=":material/layers:",
    )
st.markdown(
    "Der eigene Test zeigt deutlich: **der zweite Hebel bestimmt den Max Drawdown, "
    "nicht der erste.** Im in-sample-Sweep (2018-2024, S&amp;P) veraenderte `risk_pct` "
    "zwischen 0.5% und 1.5% den Max Drawdown kaum und ohne klares Muster (-31.9% bis "
    "-40.6%, nicht monoton). `max_total_risk_pct` dagegen zeigte einen klaren, fast "
    "monotonen Zusammenhang: 15% Deckel -> -37.6% MDD, 5% Deckel -> -19.6% MDD. Der "
    "Grund: der Drawdown in diesem Modell entsteht ueberwiegend dadurch, dass in "
    "schlechten Marktphasen VIELE aehnlich betroffene Positionen gleichzeitig offen "
    "sind (korreliert, gleiche Marktrichtung) -- nicht dadurch, dass eine einzelne "
    "Position zu gross ist."
)

st.markdown("### Der Stolperstein: In-Sample sah 12,5% wie ein Gratis-Gewinn aus")
st.warning(
    "**In-Sample (2018-2024):** Senkung von 15% auf 12,5% verbesserte Sharpe (0.86 -> "
    "0.91) UND Calmar (0.58 -> 0.60) UND senkte den Max Drawdown (-37.6% -> -33.2%) "
    "gleichzeitig -- sah nach einem echten Gratis-Gewinn ohne Trade-off aus.\n\n"
    "**Auf dem echten 2025-heute-Holdout (nie in einem Sweep verwendet):** genau "
    "das Gegenteil. 12,5% schneidet SCHLECHTER ab als der 15%-Status-quo (Sharpe "
    "0.98 vs. 1.56, Calmar 1.40 vs. 2.24) -- der vermeintliche Gratis-Gewinn war "
    "ueberwiegend Ueberanpassung an das 2018-2024-Fenster, kein echter Effekt.",
    icon=":material/warning:",
)
st.markdown(
    "Das ist derselbe Fund wie beim parallel getesteten Trailing-Stop (siehe "
    "'OU-Modell Paper-Backtest'): ein Parameter, der in-sample optimiert wurde, "
    "**muss** durch einen echten Out-of-Sample-Test, sonst weiss man nicht, ob "
    "man eine echte Verbesserung oder nur Rauschen gefunden hat. Das gilt genauso "
    "fuer Risk-/Sizing-Parameter wie fuer Entry-Regeln -- ein haeufiger blinder "
    "Fleck, weil Risk-Parameter sich \"sicher\" anfuehlen."
)

st.markdown("### Der robuste Fund: ein enger Deckel reduziert Drawdown drastisch -- zum Preis von Rendite")
st.success(
    "**2,5% Deckel (zufaellig identisch mit dem bereits laufenden Live-Bot-Wert "
    "auf Konto 2, unabhaengig davon gewaehlt):** auf dem 2025-heute-Holdout "
    "Sharpe 2.05, Calmar 3.54, Max Drawdown nur **-3.3%** (gegenueber -17.7% beim "
    "15%-Status-quo). Kein Zufallstreffer eines einzelnen Sweep-Punkts, sondern "
    "ein grosser, eindeutiger Unterschied auf ungesehenen Daten.\n\n"
    "**Der Preis:** deutlich weniger absolute Rendite (+19% statt +70%) und viel "
    "weniger Trades (78 statt 519) -- der enge Deckel laesst schlicht viele "
    "Signale mangels Kapazitaet liegen. Kein Gratis-Gewinn wie der 12,5%-Fund "
    "vorgab zu sein, sondern ein ehrlicher Trade-off: viel weniger Tail-Risiko "
    "gegen viel weniger Wachstum.",
    icon=":material/check_circle:",
)

st.markdown("### Generalisierter Denkansatz (uebertragbar auf andere Strategien im Projekt)")
st.markdown(
    """
1. **Erst fragen, WOHER der Drawdown kommt**, bevor an Stellschrauben gedreht wird.
   Kommt er von zu grossen Einzelpositionen (-> `risk_pct` senken) oder von zu vielen
   gleichzeitig offenen, korrelierten Positionen (-> aggregierten Deckel senken)? Bei
   diesem Modell war es eindeutig Letzteres -- bei einer Einzelinstrument-Strategie
   (z.B. `triple_ma_strategy`, `checklist_strategy`) faellt diese Unterscheidung weg,
   da nur eine Position gleichzeitig offen ist.
2. **Ein aggregierter Risiko-Deckel ist der zuverlaessigere Hebel** fuer Multi-Position-
   Portfolios als die Groesse der Einzelposition -- deckt sich mit dem, was der Live-Bot
   (`OU-Modell-MT5-Bridge`, `calc_open_risk()`) bereits unabhaengig als Sicherheitsnetz
   fuer alle drei Konten einsetzt.
3. **Jeder Risk-/Sizing-Parameter, der in-sample optimiert wurde, ist genauso
   overfitting-gefaehrdet wie eine Entry-Regel** -- der 12,5%-Fund waere ohne den
   Out-of-Sample-Check als "verbesserte Config" durchgegangen. Nie eine Sizing-
   Aenderung ausrollen, die nur auf dem In-Sample-Fenster geprueft wurde.
4. **Ein Deckel ist ein Risikoappetit-Dial, kein Sharpe-Optimierungsknopf** -- eng
   (2,5%) heisst massiv weniger Tail-Risiko bei deutlich weniger Wachstum, weit (15%)
   heisst mehr Wachstum bei mehr Drawdown-Exposition. Es gibt keinen Wert, der beides
   maximiert; die Wahl haengt vom eigenen Risikoappetit ab (z.B. Funded-Challenge-
   Vorgaben vs. eigenes Kapital mit langem Horizont), nicht von einem einzelnen
   Backtest-Optimum.
"""
)

st.info(
    "**Fuer dieses Projekt:** die gesperrte finale Config (`max_total_risk_pct=15%`) "
    "bleibt vorerst unveraendert -- der 12,5%-Fund ist widerlegt. Ein enger Deckel "
    "(~2,5%, wie bereits auf Konto 2 im Live-Bot) ist aber eine geprueft robuste "
    "Option fuer alle, die den Drawdown bewusst gegen Wachstum eintauschen wollen.",
    icon=":material/hourglass_empty:",
)

# ------------------------------------------------------------------ Zusatz-Erkenntnisse
st.divider()
st.markdown("### Zusatz-Erkenntnisse: Funded-Challenge-Profile (2026-08-07)")
st.caption(
    "Sechs konkrete risk_pct/max_total_risk_pct-Kombinationen, alle auf demselben "
    "echten 2025-heute-Holdout, 100k Startkapital, gegen eine reale Funded-Challenge-"
    "Regel geprueft: **max. 3% Verlust an einem einzelnen Kalendertag**, Ziel **+10% "
    "Gesamtrendite**. Locked Entry/Exit (3.0-Sigma-SL, kein TP, 0.25R-Breakeven, "
    "EMA200-Regimefilter) durchgehend unveraendert -- nur Sizing variiert."
)

profile_rows = [
    {"Profil": "Konservativ (S&P solo)", "Risiko/Trade": "0,25%", "Aggregiert": "2,5%",
     "Sharpe": 1.21, "Calmar": 1.74, "Max Drawdown": "-3,5%", "Return": "+9,8%",
     "Schlechtester Tag": "-0,97%", "3%-Regel": "eingehalten", "10%-Ziel nach": "579 Tage"},
    {"Profil": "Mittelweg (S&P solo)", "Risiko/Trade": "0,5%", "Aggregiert": "4%",
     "Sharpe": 1.03, "Calmar": 1.37, "Max Drawdown": "-6,5%", "Return": "+14,4%",
     "Schlechtester Tag": "-1,87%", "3%-Regel": "eingehalten", "10%-Ziel nach": "526 Tage"},
    {"Profil": "Live-Bot Konto 2 (S&P solo)", "Risiko/Trade": "0,5%", "Aggregiert": "2,5%",
     "Sharpe": 0.96, "Calmar": 0.95, "Max Drawdown": "-6,2%", "Return": "+9,6%",
     "Schlechtester Tag": "-1,86%", "3%-Regel": "eingehalten", "10%-Ziel nach": "nie erreicht"},
    {"Profil": "60/40 S&P+DAX", "Risiko/Trade": "0,5%", "Aggregiert": "5%",
     "Sharpe": 0.91, "Calmar": 1.31, "Max Drawdown": "-4,7%", "Return": "+10,4%",
     "Schlechtester Tag": "-1,41%", "3%-Regel": "eingehalten", "10%-Ziel nach": "547 Tage"},
    {"Profil": "50/50 S&P+DAX", "Risiko/Trade": "0,5%", "Aggregiert": "5%",
     "Sharpe": 0.82, "Calmar": 1.12, "Max Drawdown": "-4,5%", "Return": "+8,4%",
     "Schlechtester Tag": "-1,73%", "3%-Regel": "eingehalten", "10%-Ziel nach": "nie erreicht"},
    {"Profil": "Aggressiv (S&P solo)", "Risiko/Trade": "1%", "Aggregiert": "10%",
     "Sharpe": 1.03, "Calmar": 1.55, "Max Drawdown": "-12,3%", "Return": "+31,8%",
     "Schlechtester Tag": "-3,74%", "3%-Regel": "VERLETZT (05.06.2025)", "10%-Ziel nach": "330 Tage (zaehlt nicht)"},
]
profile_df = pd.DataFrame(profile_rows)
st.dataframe(
    profile_df, hide_index=True, width="stretch",
    column_config={
        "Sharpe": st.column_config.NumberColumn(format="%.2f"),
        "Calmar": st.column_config.NumberColumn(format="%.2f"),
    },
)

st.warning(
    "**Ueberraschung:** die aktuelle Live-Bot-Sizing auf Konto 2 (0,5%/2,5%) ist "
    "NICHT die beste gepruefte Kombination -- sie schneidet schlechter ab als das "
    "urspruengliche 0,25%/2,5%-Profil (Sharpe 0.96 vs. 1.21, Max Drawdown -6,2% vs. "
    "-3,5%) und erreicht das 10%-Ziel im Testfenster gar nicht. Grund: bei "
    "gleichem 2,5%-Deckel fuehrt hoeheres Risiko/Trade zu WENIGER, dafuer groesseren "
    "Positionen (180 statt 365 Trades) -- weniger Streuung ueber Einzelwerte, "
    "schlechteres risikoadjustiertes Ergebnis trotz identischem Aggregat-Deckel. "
    "**S&P-DAX-Diversifikation half in keiner Gewichtung** -- DAX hat in diesem "
    "Projekt durchgehend eine schwaechere eigene Kante als S&P, eine Beimischung "
    "verduennt daher eher, als zu diversifizieren.",
    icon=":material/priority_high:",
)
st.markdown(
    "**Lehre Nr. 5 fuer den generalisierten Denkansatz oben:** bei gleichem "
    "aggregierten Deckel ist ein NIEDRIGERES Risiko/Trade meist besser, nicht "
    "neutral -- es erlaubt mehr gleichzeitige, kleinere Positionen und damit mehr "
    "Streuung ueber Einzelwerte innerhalb desselben Risikobudgets. Die Kombination "
    "aus Deckel-Hoehe UND Risiko/Trade muss gemeinsam geprueft werden, nicht "
    "unabhaengig voneinander."
)
