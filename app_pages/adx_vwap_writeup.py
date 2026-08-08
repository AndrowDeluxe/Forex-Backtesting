"""Strategie Bestandteile -- ADX-VWAP: die einzelnen Bausteine getrennt
dargestellt, plus die ehrlichen empirischen Befunde aus mehreren
Recherche-Runden (`scripts/research_adx_params.py` u.a.).

Reine Wissens-/Referenzseite, kein Backtest -- der interaktive Backtest lebt
unveraendert unter "Backtests" -> `app_pages/adx_vwap.py`. Gleiches Muster
wie `orb_writeup.py` fuer ORB: Konzept + Befunde hier, Zahlen/Chart dort.

Quelle (2026-08-09 identifiziert, siehe app_pages/fx_papers_202608.py Tab 5):
mit sehr hoher Wahrscheinlichkeit Amaanullah Bhatti (Hafzan Osmanoglu),
"Momentum Exhaustion and Fair Value Reversion: An ADX-Conditioned VWAP
Strategy in FX Markets", Symbiosis International University, SSRN Working
Paper 6454659 (22. Maerz 2026) -- Formeln (VWAP Eq. 1-3, Vortages-Extreme
Sec. 4.3, Wilder-ADX Eq. 4-10, Regimefilter Eq. 11-13), Abschnittsnummern in
Code-Kommentaren (strategy/backtest.py: "Sec 5.3"/"Sec 6.1") und sogar der
Docstring-Kopf von strategy/indicators.py stimmen exakt mit der Struktur
dieses Papers ueberein. Das Paper selbst enthaelt keine eigenen Backtest-
Zahlen ("left to future work") -- alle empirischen Befunde in diesem Repo
sind eigene, originaere Arbeit, keine Reproduktion behaupteter Paper-Werte.
Implementiert in `strategy/indicators.py` und `strategy/signals.py`.
"""

import streamlit as st

st.set_page_config(
    page_title="ADX-VWAP -- Strategiebestandteile", page_icon=":material/candlestick_chart:", layout="wide"
)

st.markdown("## :material/candlestick_chart: ADX-VWAP -- Strategiebestandteile")
st.caption(
    "Die Handelsthese hinter dem Composite-Signal S_t (Eq. 14) des ADX-VWAP-Backtests. "
    "Vier einzelne, grundsaetzlich unabhaengig wiederverwendbare Bausteine, hier getrennt "
    "von den Backtest-Zahlen dargestellt -- die laufen unveraendert unter **Backtests -> "
    "ADX-VWAP FX-Strategie**."
)
st.info(
    "**Quelle wahrscheinlich identifiziert (2026-08-09):** Bhatti/Osmanoglu (2026), "
    "\"Momentum Exhaustion and Fair Value Reversion: An ADX-Conditioned VWAP Strategy in "
    "FX Markets\" (SSRN 6454659) -- Formeln, Abschnittsnummern und ein Code-Docstring in "
    "diesem Repo stimmen exakt überein. Details/Beleg: **Neue Papers -> FX-Papers (Aug. "
    "2026) -> Tab 5**. Das Paper selbst liefert keine eigenen Backtest-Zahlen -- alle Zahlen "
    "auf dieser Seite und im Backtest-Dashboard bleiben eigene, originäre Arbeit.",
    icon=":material/manage_search:",
)

st.markdown(
    "Kernidee: nach einer starken Trendbewegung, die bereits Anzeichen von Erschoepfung "
    "zeigt (ADX faellt wieder), an einem markanten technischen Level (Vortages-Extrem) "
    "gegen eine statistisch signifikante Ueberdehnung vom fairen Wert (VWAP) zu handeln. "
    "Vier Bausteine kombiniert per logischem UND zu einem Signal $S_t \\in \\{-1,0,+1\\}$."
)

st.markdown("### Baustein 1: Session-VWAP & Deviation -- \"fairer Wert\"")
st.markdown(
    "Volumen-gewichteter Durchschnittspreis, kumuliert seit Session-Beginn, als Proxy fuer "
    "den \"fairen\" Intraday-Preis. Die Abweichung $D_t = (close_t - VWAP_t)/VWAP_t$ misst, "
    "wie weit der Kurs gerade vom fairen Wert weggelaufen ist -- je groesser $|D_t|$, desto "
    "staerker die unterstellte Ueberdehnung."
)
st.code(
    "from strategy.indicators import compute_vwap_and_deviation\n"
    "df = compute_vwap_and_deviation(df, reset_hour=22)  # -> df['vwap'], df['deviation']",
    language="python",
)
st.caption(
    "Implementierung: `strategy/indicators.py::compute_vwap_and_deviation`. Session-Reset "
    "per `reset_hour`, kein Blick ueber Session-Grenzen hinweg (per Test abgesichert)."
)

st.markdown("### Baustein 2: Vortages-Extrem als Trigger-Level")
st.markdown(
    "Erst wenn der aktuelle Kurs das High/Low der **vorherigen** Session erreicht oder "
    "durchbricht, gilt die Bewegung als \"markant genug\", um ueberhaupt ein Setup zu sein "
    "-- reine VWAP-Abweichung ohne dieses Level wird ignoriert. Verhindert, dass jede "
    "kleine Schwankung um den VWAP herum als Signal zaehlt."
)
st.code(
    "from strategy.indicators import compute_prev_session_extremes\n"
    "df = compute_prev_session_extremes(df)  # -> df['prev_high'], df['prev_low']",
    language="python",
)
st.caption(
    "Implementierung: `strategy/indicators.py::compute_prev_session_extremes`. Attacht "
    "explizit das *vorherige* Extrem an jede Bar der laufenden Session -- kein Lookahead "
    "in die eigene, noch laufende Session."
)

st.markdown("### Baustein 3: ADX-Momentum-Decay -- \"Erschoepfungs\"-Filter")
st.markdown(
    "Wilder's ADX misst Trendstaerke, nicht Richtung. Die These handelt nur, wenn ADX "
    "**erhoeht** ist (ein Trend war/ist da) UND bereits **wieder faellt** (der Trend "
    "verliert Momentum) -- die Kombination soll den Moment kurz vor einer Erschoepfungs-"
    "Umkehr treffen, statt blind gegen einen intakten Trend zu wetten."
)
st.code(
    "from strategy.indicators import compute_adx, compute_regime_filter\n"
    "df = compute_adx(df, n=14)              # -> df['adx'], df['plus_di'], df['minus_di']\n"
    "df = compute_regime_filter(df, adx_window=20)  # -> df['adx_mean'], df['delta_adx']",
    language="python",
)
st.warning(
    "**Offene Fragestellung im Original, empirisch beantwortet:** Eq. 14 nutzt die "
    "schwache Bedingung $\\Delta ADX_t \\le 0$ (\"steigt nicht mehr\"). Die strikte Variante "
    "$\\Delta ADX_t < 0$ (\"faellt tatsaechlich\") klang wie ein sauberer Unterschied -- ist "
    "auf echten Daten aber **irrelevant**: ADX ist ein kontinuierlicher Float, exakte "
    "Null-Deltas kommen praktisch nie vor, beide Varianten liefern bytgleiche Ergebnisse. "
    "Eine Vorab-Annahme, die sich als Nicht-Thema herausstellte -- nicht mehr weiter "
    "verfolgen, falls nochmal danach gefragt wird.",
    icon=":material/science:",
)
st.error(
    "**Eigene Erweiterung, nicht Teil der Originalthese:** ein absoluter ADX-Ceiling "
    "(kein Trade wenn $ADX_t \\ge$ Schwelle, z.B. 25) wurde ergaenzt, weil die "
    "Regime-Zerlegung echter Trades zeigte, dass die schwache Decay-Bedingung allein "
    "immer noch Trades gegen **echte, starke** Trends durchliess -- genau das Risiko, vor "
    "dem die eigene Handelsthese ausdruecklich warnt (\"nicht gegen einen laufenden Trend "
    "wetten\"). Nur als Teil der *Refined*-Konfiguration im Backtest aktiv, nicht in der "
    "*Pure*-Variante.",
    icon=":material/warning:",
)

st.markdown("### Baustein 4: Adaptive Theta-Schwelle")
st.markdown(
    "Statt eines fixen Prozent-Schwellenwerts fuer \"genug\" VWAP-Abweichung skaliert "
    "$\\theta_t$ mit der rollierenden Standardabweichung von $D_t$ selbst -- die Schwelle "
    "passt sich automatisch an das aktuelle Volatilitaetsregime des Paares an, statt in "
    "ruhigen Phasen zu locker und in nervoesen Phasen zu eng (oder umgekehrt) zu sein."
)
st.code(
    "from strategy.indicators import compute_adaptive_theta\n"
    "df['theta'] = compute_adaptive_theta(df, window_bars=500, multiplier=1.0)",
    language="python",
)
st.caption("Implementierung: `strategy/indicators.py::compute_adaptive_theta`. Nur rueckwaerts schauend.")

st.markdown("### Composite-Signal & ehrliche Befunde")
st.markdown(
    "Alle vier Bausteine UND-verknuepft ergeben $S_t$ (`strategy/signals.py::generate_signal`, "
    "Eq. 14). Zwei unabhaengig getestete Konfigurationen, beide live im interaktiven Backtest "
    "einsehbar:"
)

col_pure, col_refined = st.columns(2)
with col_pure:
    st.error(
        "**Pure (Eq. 14 woertlich), M15, echte Daten, 10 Jahre, alle 6 Hauptpaare:** "
        "**negativer Sharpe auf allen 6 Paaren.** Die Handelsthese funktioniert in ihrer "
        "urspruenglichen Form nicht auf echten Marktdaten -- der ehrliche Ausgangsbefund, "
        "an dem sich jede Verfeinerung messen muss.",
        icon=":material/trending_down:",
    )
with col_refined:
    st.warning(
        "**Refined (H1, ADX-Lookback n=10 statt 14, ADX-Ceiling 25, theta x1.5):** "
        "bester von mehreren getesteten Kandidaten, gefunden per **jaehrlichem "
        "Walk-Forward** (2017-2025 als 9 unabhaengige Jahres-Folds x 6 Paare statt einem "
        "einzelnen statischen Split): mittlerer Sharpe +0.24, Median +0.76, 63% der "
        "104 Jahr-Paar-Zellen positiv. **Noch keine bestaetigte Kante** -- duenne "
        "Stichprobe, drittes sequentielles Hinsehen auf denselben Datensatz.",
        icon=":material/trending_up:",
    )

st.info(
    "**Methodischer Nebenbefund, generell anwendbar:** ein einzelner statischer "
    "In-Sample/Out-of-Sample-Split war hier zu fragil, um Robustheit zu beurteilen -- "
    "ein Wechsel zu jaehrlichem Walk-Forward (viele unabhaengige Jahres-Folds statt eines "
    "Splits) lieferte erst eine belastbare Verteilung statt einer einzelnen Zahl. Dasselbe "
    "Muster gilt fuer jede andere Strategie in diesem Projekt mit duennem Trade-Count.",
    icon=":material/query_stats:",
)

st.markdown("### Wiederverwendung anderswo im Projekt -- was schon versucht wurde")
st.markdown(
    "`combined_strategy/` hat versucht, drei dieser Bausteine auf die (trendfolgende) "
    "EMA-S/R-Strategie zu uebertragen: (A) VWAP-Ueberdehnung als Entry-Filter, (B) "
    "Vortages-Extrem-Konfluenz als Entry-Filter, (C) ADX-Erschoepfung als Exit statt Entry. "
    "**Ergebnis: keiner der drei Bausteine verbessert einzeln die Out-of-Sample-Performance "
    "ueberzeugend; alle drei kombiniert erhoeht zwar den Durchschnitt, halbiert aber die "
    "Trade-Zahl und reduziert die Zahl profitabler Instrumente** (7/11 vs. 9/11 Baseline) -- "
    "eher \"weniger, konzentriertere Trades\" als eine echte, uebertragbare Kante."
)
st.markdown(
    "**Umgekehrter Test:** `scripts/research_kalman_filter_adx_vwap.py` hat den Kalman-Filter-"
    "Baustein (aus einem komplett anderen Paper, siehe Strategie Bestandteile -> "
    "Kalman-Filter) auf genau diese Refined-Konfiguration angewendet -- gleiches "
    "Walk-Forward-Setup (9 Jahres-Folds x 6 Paare), nur die VWAP-Deviation kommt einmal "
    "vom rohen und einmal vom Kalman-geglaetteten Kurs, alles andere identisch."
)
st.error(
    "**Ergebnis: keine Verbesserung, tendenziell schlechter mit staerkerer Glaettung.** "
    "Mean-Sharpe raw 0.235 vs. Kalman (noise_fraction 0.3/0.5/0.7): 0.215 / 0.228 / 0.096 -- "
    "Median-Sharpe faellt durchgehend (0.763 -> 0.676 / 0.533 / 0.323), ebenso der Anteil "
    "positiver Jahr-Paar-Zellen (63.2% -> 57.5% / 61.5% / 58.5%). Leichte Glaettung ist "
    "grob neutral, aggressive Glaettung (0.7) verschlechtert klar auf allen Metriken. "
    "**Derselbe Befund wie bei combined_strategy: ein Baustein, der woanders sinnvoll "
    "klingt, verbessert nicht automatisch eine bestehende Strategie -- nachpruefen statt "
    "annehmen.**",
    icon=":material/science:",
)

st.info(
    "**Naechster Schritt:** kein Backtest auf dieser Seite -- die vier Bausteine sind "
    "einzeln in `strategy/indicators.py` importierbar und unabhaengig von diesem "
    "Composite-Signal nutzbar. Wer sie in eine andere Strategie einbauen will: importieren, "
    "eigenen Backtest fahren, **nicht** ungeprueft die hier dokumentierten Sharpe-Werte "
    "uebernehmen -- die gelten nur fuer die exakte hier beschriebene Kombination und "
    "Parameter-Wahl.",
    icon=":material/hourglass_empty:",
)
