"""Education-Track: Kelly-Formel & Risk Management.

Ausgelagert als eigener Track (2026-08-11), analog zu education_book_chan.py.
Erklaert die Kelly-Formel von Grund auf und wie sie sich sinnvoll in ein
praktisches Risk-Management-Regime einbauen laesst -- inkl. einem eigenen
Test der Formel auf den echten Trades des OU-Modells (S&P 500, gesperrte
finale Config aus fertige_strategien.py), sowohl in-sample (2018-2024) als
auch auf dem echten 2025-heute-Holdout. Zahlen kommen aus
scripts/research_kelly_ou_model.py -> ou_paper_backtest/results/sp500/kelly_test.json.
"""

import json
from pathlib import Path

import pandas as pd

import streamlit as st

st.set_page_config(page_title="Education -- Kelly-Formel", page_icon=":material/calculate:", layout="wide")

REPO_DIR = Path(__file__).resolve().parents[1]
KELLY_JSON = REPO_DIR / "ou_paper_backtest" / "results" / "sp500" / "kelly_test.json"

st.page_link("app_pages/education.py", label="Zurueck zu Education", icon=":material/arrow_back:")
st.space("small")

st.markdown("## :material/calculate: Kelly-Formel & Risk Management")
st.caption(
    "Die Kelly-Formel bestimmt den mathematisch optimalen Kapitalanteil pro Trade, "
    "um die langfristige (geometrische) Wachstumsrate des Kapitals zu maximieren. "
    "Dieser Track erklaert Herleitung und Grenzen und testet die Formel anschliessend "
    "an echten Trades des OU-Modells."
)

st.space("small")

with st.expander(":material/functions: 1. Die Formel", icon=":material/functions:", expanded=True):
    st.markdown(
        r"""
**Binaere Wette / Einzeltrade mit festem Gewinn-/Verlust-Vielfachen:**

$$f^{*} = \frac{b \cdot p - q}{b} = p - \frac{q}{b}$$

- $f^{*}$ -- optimaler Anteil des Kapitals, der pro Trade **riskiert** wird
- $p$ -- Gewinnwahrscheinlichkeit (Win-Rate)
- $q = 1-p$ -- Verlustwahrscheinlichkeit
- $b$ -- Payoff-Ratio (durchschnittlicher Gewinn in R geteilt durch durchschnittlichen Verlust in R)

**Beispiel:** Win-Rate 45 %, Payoff-Ratio 2 (durchschnittlicher Gewinn 2R, durchschnittlicher Verlust 1R):

$$f^{*} = 0.45 - \frac{0.55}{2} = 0.175 \rightarrow 17.5\,\% \text{ des Kapitals riskiert pro Trade}$$

**Allgemeinere Form** (kontinuierliche Renditen statt fixer Win/Loss-Werte, z. B. fuer
eine ganze Strategie mit einer Renditeverteilung):

$$f^{*} = \frac{\mu}{\sigma^{2}}$$

wobei $\mu$ der erwartete Return und $\sigma^{2}$ dessen Varianz ist. Eine kontraintuitive
Konsequenz daraus: die geometrische (verzinste) Rendite ist ungefaehr gleich der
arithmetischen Rendite minus der halben Varianz -- Risiko senkt also grundsaetzlich die
langfristige Wachstumsrate, selbst bei positivem Erwartungswert. Ein reiner Random Walk
mit je 50 % Wahrscheinlichkeit auf +1 %/-1 % verliert auf lange Sicht Geld (ca. -0,005 %
pro Periode), obwohl der arithmetische Erwartungswert null ist.
        """
    )

with st.expander(":material/warning: 2. Warum reines Kelly in der Praxis gefaehrlich ist", icon=":material/warning:"):
    st.markdown(
        """
1. **Parameterschaetzfehler.** Kelly braucht exakte $p$ und $b$. In Backtests sind das
   Schaetzungen aus begrenzten Stichproben -- Overfitting und Zukunftsunsicherheit fuehren
   fast immer zu einer Ueberschaetzung der eigenen Kante. Ein zu hoch geschaetztes $p$
   oder $b$ fuehrt zu massivem Overbetting.
2. **Extreme Volatilitaet.** Volles Kelly fuehrt zu enormen Drawdowns (auch bei
   positivem Erwartungswert sind 50-90 % Drawdowns moeglich) -- psychologisch und
   praktisch (Margin Calls) kaum durchhaltbar.
3. **Nicht-stationaere Maerkte.** Kelly setzt konstante $p$/$b$ ueber die Zeit voraus --
   bei Handelsstrategien wechseln Marktregime, die Kante ist nie wirklich konstant.
4. **Korrelierte Wetten.** Kelly setzt Unabhaengigkeit der Wetten voraus. Ein Portfolio
   mit mehreren gleichzeitig offenen, aehnlich gerichteten Positionen verletzt diese
   Annahme -- das OU-Modell selbst ist ein gutes Beispiel dafuer (siehe Abschnitt 4).
        """
    )

with st.expander(":material/tune: 3. Praktischer Einbau ins Risk Management", icon=":material/tune:"):
    st.markdown(
        """
**Fractional Kelly (Standard-Praxis).** Nur einen Bruchteil des berechneten $f^{*}$
nutzen -- ueblich sind **Half-Kelly (50 %)** oder **Quarter-Kelly (25 %)**. Half-Kelly
senkt die Wachstumsrate nur um ca. 25 %, reduziert Varianz/Drawdown-Tiefe aber drastisch.
Bei unsicheren, backtest-basierten Schaetzungen ist Quarter-Kelly meist der realistischere
Startpunkt.

**Konservative Parameterschaetzung.** Konfidenzintervalle statt Punktschaetzungen nutzen
(z. B. unteres Quantil der Win-Rate aus Walk-Forward/Cross-Validation), und mit
Out-of-Sample- statt In-Sample-Metriken rechnen -- sonst systematische Ueberschaetzung
von $f^{*}$.

**Harte Obergrenze.** Ein Maximum pro Trade festlegen (z. B. 2-5 % des Kapitals),
unabhaengig davon, was Kelly ausspuckt -- als Schutz gegen Modellfehler.

**Aggregation ueber Strategien/Positionen.** Bei mehreren parallel laufenden Strategien
Kelly nicht isoliert pro Strategie berechnen, sondern die Korrelation der Equity-Kurven
beruecksichtigen -- sonst summiert sich das effektive Risiko unbemerkt auf. Genau das ist
beim OU-Modell bereits unabhaengig als staerkerer Hebel identifiziert worden: siehe
'Risk Management' (`max_total_risk_pct`).

**Dynamisches Nachjustieren.** $f^{*}$ rollierend neu schaetzen (gleitendes Fenster oder
Bayesianisches Update), mit Traegheit/Glaettung, um nicht auf kurzfristige Ausreisser zu
ueberreagieren.

**Kombination mit klassischem Risk Management.** Kelly ersetzt keinen Stop-Loss oder
Max-Drawdown-Limits -- es bestimmt nur die Positionsgroesse gegeben ein Risiko pro Trade:

```
Positionsgroesse = Kapital x f_kelly_fractional x Risiko-Cap-Faktor
Stop-Loss-Distanz -> daraus Lot-/Share-Size ableiten
```
        """
    )

st.space("small")
st.divider()

st.markdown("### :material/science: 4. Test am OU-Modell (S&P 500, gesperrte finale Config)")
st.caption(
    "Kelly $f^{*}$ direkt aus den echten Trades der gesperrten finalen Config berechnet "
    "(long-only, OU-selektiertes Universum, 3.0-Sigma-SL, kein TP, 0.25R-Breakeven, "
    "markt-weiter EMA200-Regimefilter, `risk_pct=1%` -- siehe 'OU-Modell (finale "
    "Konfiguration)'). R-Vielfaches pro Trade approximiert als "
    "`pnl_dollars / (risk_pct * equity_at_entry)`, Methodik und Code: "
    "`scripts/research_kelly_ou_model.py`."
)

if not KELLY_JSON.exists():
    st.warning(
        "Noch keine Ergebnisdatei gefunden -- `python scripts/research_kelly_ou_model.py` "
        "einmal laufen lassen (dauert ein paar Minuten wegen frischem Datendownload fuer "
        "den Holdout-Teil).",
        icon=":material/hourglass_empty:",
    )
else:
    data = json.loads(KELLY_JSON.read_text(encoding="utf-8"))

    def render_leg(key: str, label: str, tone) -> None:
        d = data[key]
        st.markdown(f"#### {label}")
        st.caption(d["period"])
        cols = st.columns(5)
        cols[0].metric("Trades", d["n_trades"])
        cols[1].metric("Win-Rate", f"{d['win_rate']*100:.1f} %")
        cols[2].metric("Payoff-Ratio b", f"{d['payoff_ratio_b']:.2f}")
        cols[3].metric("Kelly f*", f"{d['kelly_f']*100:.1f} %")
        cols[4].metric("Half-Kelly", f"{d['half_kelly_f']*100:.1f} %")
        tone(
            f"Tatsaechlich verwendetes `risk_pct` in der gesperrten Config: "
            f"**{d['used_risk_pct']*100:.1f} %**. Quarter-Kelly waere hier "
            f"**{d['quarter_kelly_f']*100:.2f} %**.",
        )

    render_leg("in_sample", "In-Sample (2018-2024)", st.info)
    st.space("small")
    render_leg("holdout", "Echter Out-of-Sample-Holdout (2025-heute)", st.warning)

    st.space("small")
    ins = data["in_sample"]
    hold = data["holdout"]
    st.markdown("#### Einordnung")
    st.markdown(
        f"""
- **Ueberraschung: Kelly bricht auf dem Holdout NICHT ein.** In-Sample (2018-2024, 1834
  Trades) sagt Kelly {ins['kelly_f']*100:.1f} % pro Trade, auf dem echten
  2025-heute-Holdout (523 Trades) sogar leicht MEHR: {hold['kelly_f']*100:.1f} %. Win-Rate
  (~47-48 %) und Payoff-Ratio (1,49 vs. 1,59) sind auf beiden Fenstern fast identisch --
  anders als beim `max_total_risk_pct`-Fund auf der 'Risk Management'-Seite, wo sich der
  In-Sample-Befund auf dem Holdout umdrehte, ist die reine Trade-Kante hier (Win-Rate x
  Payoff-Ratio) also stabil. Ein positives Robustheitssignal fuer das Setup selbst --
  aber, wie der letzte Punkt zeigt, kein Freibrief fuer die Positionsgroesse.
- **Der eigentliche Befund ist die Luecke, nicht der Trend:** Kelly haelt 12-15 % Risiko
  pro Trade fuer optimal, tatsaechlich genutzt wird **{ins['used_risk_pct']*100:.0f} %**
  -- also nur rund ein Siebtel von Full-Kelly, deutlich unter selbst Quarter-Kelly
  (~{ins['quarter_kelly_f']*100:.1f}-{hold['quarter_kelly_f']*100:.1f} %).
- **Warum das trotzdem richtig ist, nicht zu konservativ:** die klassische Kelly-Formel
  unterstellt EINE Wette nach der anderen (Abschnitt 2, Punkt 4). Das OU-Modell haelt aber
  oft viele Positionen gleichzeitig -- und laut 'Risk Management' ist dort nicht
  `risk_pct`, sondern der AGGREGIERTE Deckel (`max_total_risk_pct=15%`) die eigentliche
  Drawdown-Determinante. Wuerde man jeden Trade mit ~13-15 % Kelly-Groesse sizen, waeren
  bereits ein bis zwei gleichzeitig offene Positionen am gesamten Aggregat-Deckel -- bei
  oft deutlich mehr korrelierten, gleichzeitig offenen Signalen waere das ein garantierter
  Verstoss gegen genau den Hebel, der laut eigenem Test den Max Drawdown dominiert. Die
  grosse Kelly-Luecke ist hier also kein Zeichen von Uebervorsicht, sondern die direkte
  Konsequenz aus der Portfolio-Konzentration: der aggregierte Deckel frisst den
  Kelly-Spielraum pro Einzeltrade fast vollstaendig auf, lange bevor Full-Kelly erreicht
  waere.
- **Praktische Einordnung:** `risk_pct=1%` liegt damit weit auf der sicheren Seite von
  Kelly, was angesichts der Portfolio-Konzentration richtig ist -- Kelly pro Einzeltrade
  ist hier eine obere Leitplanke fuer die Kante, kein vollstaendiges Sizing-Modell. Wer
  den aggregierten Deckel eng haelt (siehe die 2,5-5 %-Profile auf 'Risk Management'),
  bewegt sich ohnehin weit innerhalb des Kelly-Korridors; das eigentliche Risiko liegt
  nicht im zu niedrigen `risk_pct`, sondern in einem zu weiten `max_total_risk_pct`.
        """
    )

st.space("small")
st.divider()

st.markdown("### :material/warning: 5. Test: was, wenn man den Deckel abschaltet?")
st.caption(
    "Direkter Test der Behauptung oben: `risk_pct` auf Full-/Half-/Quarter-Kelly (aus "
    "dem In-Sample-Wert, kein Blick auf den Holdout) gesetzt, `max_total_risk_pct` "
    "praktisch abgeschaltet (1000 %) -- gegen die gesperrte Baseline (1 %/15 %-Deckel). "
    "Code: `scripts/research_kelly_uncapped_ou_model.py`."
)

UNCAPPED_JSON = REPO_DIR / "ou_paper_backtest" / "results" / "sp500" / "kelly_uncapped_test.json"

if not UNCAPPED_JSON.exists():
    st.warning(
        "Noch keine Ergebnisdatei gefunden -- `python scripts/research_kelly_uncapped_ou_model.py` "
        "einmal laufen lassen.",
        icon=":material/hourglass_empty:",
    )
else:
    udata = json.loads(UNCAPPED_JSON.read_text(encoding="utf-8"))
    VARIANT_LABELS = {
        "baseline_1pct_15cap": "Baseline (1 % / 15 %-Deckel, gesperrt)",
        "full_kelly_15cap": "Full-Kelly (12,7 %), Deckel bleibt bei 15 %",
        "full_kelly_no_cap": "Full-Kelly (12,7 %), Deckel abgeschaltet",
        "half_kelly_no_cap": "Half-Kelly (6,3 %), Deckel abgeschaltet",
        "quarter_kelly_no_cap": "Quarter-Kelly (3,2 %), Deckel abgeschaltet",
    }

    def render_uncapped_table(leg_key: str, label: str) -> None:
        rows = []
        for vkey, vlabel in VARIANT_LABELS.items():
            r = udata[leg_key][vkey]
            rows.append({
                "Variante": vlabel,
                "Sharpe": r["sharpe"],
                "Calmar": r["calmar"],
                "Max Drawdown": f"{r['max_drawdown_pct']:.1f} %",
                "Return": f"{r['total_return_pct']:.0f} %",
                "Max. gleichzeitige Positionen": r["max_concurrent_positions"],
                "Minimale Equity": f"${r['min_equity']:,.0f}",
            })
        st.markdown(f"#### {label}")
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    render_uncapped_table("in_sample", "In-Sample (2018-2024)")
    st.space("small")
    render_uncapped_table("holdout", f"Echter Out-of-Sample-Holdout ({udata['holdout_period']})")

    st.space("small")
    st.error(
        "**Ohne Deckel bricht das Portfolio zusammen** -- unabhaengig von der "
        "Kelly-Fraktion. In-Sample geht die Equity bei Full-/Half-/Quarter-Kelly ohne "
        "Deckel sogar rechnerisch NEGATIV (bis zu -$65.541), weil bis zu 82-121 "
        "gleichzeitig offene, korrelierte Positionen gleichzeitig gegen die Marktrichtung "
        "laufen koennen -- die Simulation kennt keinen Margin Call, ein echtes Konto waere "
        "laengst zwangsliquidiert.",
        icon=":material/dangerous:",
    )
    st.markdown(
        """
- **Kelly + Deckel behalten killt die Diversifikation:** Bei 12,7 % Risiko/Trade passt
  unter einem 15 %-Deckel nur noch **eine** Position gleichzeitig -- die Strategie wird
  faktisch zur Einzelaktien-Wette statt eines breiten Portfolios, und genau die Streuung
  ueber viele OU-selektierte Titel war Teil der urspruenglichen Kante (Sharpe faellt
  in-sample von 0.86 auf -0.17).
- **Kontraintuitiv: ohne Deckel wird es mit NIEDRIGEREM Risiko/Trade noch schlimmer.**
  Quarter-Kelly schneidet schlechter ab als Full-Kelly (in-sample MDD -127 % vs. -109 %,
  Endkapital noch negativer) -- kleinere Einzelpositionen lassen das Konto laenger
  "ueberleben", wodurch sich VOR dem Crash noch mehr korrelierte Positionen gleichzeitig
  aufbauen (bis zu 121 statt 82). Ohne Deckel ist die ANZAHL gleichzeitig offener Wetten
  das eigentliche Risiko, nicht ihre Einzelgroesse -- der aggregierte Deckel ist also kein
  optionales Extra zu Kelly, sondern die Voraussetzung dafuer, dass Kelly-Groessen hier
  ueberhaupt sicher anwendbar sind.
        """
    )
