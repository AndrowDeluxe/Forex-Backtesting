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
