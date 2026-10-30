# Live-Beine je Wachstums-Inflations-Regime (28.10.2026)

**Frage (Nutzer):** Zeigen unsere Edges auf der [[regimekarte-wachstum-inflation]]
Besonderheiten, also starke und schwache Phasen in bestimmten Regimen?
**Status:** abgeschlossen, diagnostisch. Rahmen und „keine Regel“ vom Nutzer bestätigt (30.10.). Nichts gewählt, 0 optimierte Punkte.
Unter der [[overfitting-sperre]] ist das keine Variante.

## Aufbau
- **Trades:** dieselben wie beim [[residual-edge-check]]. Quelle ist
  `live_trades_ttp_2019_2026.csv` mit gemessenen TTP-Kosten, gold_silver kommt aus der
  Tickmill-Liste `ampel`.
- **Regime:** das Label am Entry-Tag. Ein Print gilt ab der Folgesitzung, also ohne Vorgriff.
- **Linsen:** Tempo (4 Zellen: g/π beschleunigt oder verlangsamt) und gemeinsame Sicht
  (7 Zellen seit 2019; die drei g↓-Zellen stammen fast nur aus 2020/21).
- **Nur IS** (Vier-Fragen-Check, Fragen 2–3). Grenzen wie beim Residual-Check:
  - ORB, Gold ASB, gold_silver und OU bis 2022
  - CLS bis 05/2022
  - trend_pullback bis 06/2024
  - CTNL komplett, weil es kein sauberes OOS hat
- **Zufallstest:** Die Regime-Reihe wird 2000-mal zirkulär gegen die Trades verschoben.
  Die Blockstruktur der Regime bleibt dabei erhalten. p ist der Anteil der Läufe, in denen
  die Regime-Mittel mindestens so stark streuen wie in echt.
- Code: `scripts/research_edges_by_regime.py` → `knowledge/_data/edges_by_regime.json`.

## Ergebnis: kein Bein hängt nachweisbar vom Regime ab

| Bein | n (IS) | p Tempo | p gemeinsam | stärkste Zelle (n ≥ 15) | schwächste Zelle (n ≥ 15) |
|---|---:|---:|---:|---|---|
| orb_sp500 | 186 | 0,62 | 0,46 | g↓·slow × π↑·accel +1,12 R | **g↑·slow × π↑·accel −0,15 R** |
| orb_nasdaq | 824 | 0,89 | 0,45 | g↑·accel × π↑·slow +0,71 | g↓·accel × π↑·slow −0,58 (t −1,9, Winter 2020/21) |
| orb_us30 | 195 | 0,90 | 0,12 | g↑·slow × π↑·slow +0,49 | **g↑·slow × π↑·accel −0,11** |
| gold_asb | 96 | 0,88 | 0,89 | g↑·slow × π↑·slow +0,39 | g↑·slow × π↑·accel +0,21 |
| gold_silver | 54 | 0,81 | 0,08* | alle g↑-Zellen positiv, Zellen n ≤ 13 | — |
| ou_modell | 301 | 0,86 | 0,47 | g↓·accel × π↑·accel +0,10 | g↑·accel × π↑·accel −0,07 |
| cls_practical | 57 | 0,28 | 0,23 | g↑·slow × π↑·accel +0,50 | (alle anderen Zellen n ≤ 10) |
| trend_pullback | 169 | 0,60 | 0,40 | **g↑·slow × π↑·accel +0,74 (t 2,2)** | g↑·accel × π↑·slow −0,01 |
| ctnl_reversal | 166 | 0,67 | 0,74 | g↑·slow × π↑·slow +1,80 (t 2,9) | g↑·accel × π↑·accel +0,54 |

\* bei gold_silver kommt das p nur durch Zellen mit 1–4 Trades zustande, darum ohne Aussage.

**Lesart:** 18 Tests, keiner mit p < 0,05. Ein Treffer unter 0,10 ist bei 18 Tests reiner
Zufall. Die Unterschiede zwischen den Regimen liegen also im Rauschen. Das passt zu
dem Richtungstest vom 28.10. (IS Sharpe 1,60 → Tresor −0,30, siehe [[regimekarte-wachstum-inflation]]): Die Karte taugt als Kontext, nicht als Schalter.

## Besonderheiten (Hypothesen, nicht bestätigt)
1. **Das aktuelle Regime g↑·slow × π↑·accel (seit 14.09.) teilt das Portfolio.** In diesem
   Regime war ORB im IS am schwächsten: S&P −0,15 R, US30 −0,11 R, NASDAQ +0,25 R (die
   schwächste g↑-Zelle). Die Gold-Trend-Beine waren dort am stärksten: trend_pullback
   +0,74 R und gold_silver +1,56 R, letzteres bei nur 10 Trades. Der Mechanismus wäre
   plausibel: Gold trendet, wenn die Inflation anzieht. Die drei ORB-Werte sind aber keine
   unabhängigen Belege, denn es sind dieselben Handelstage.
2. **trend_pullback hängt am ehesten an der Inflation.** Bei steigender Inflation lag es
   bei +0,31 bzw. +0,63 R, bei fallender bei −0,06 bzw. +0,10 R. Das ist das einzige
   Muster mit einem Mechanismus dahinter, p liegt aber bei 0,60.
3. **CTNL ist in allen großen Zellen positiv.** Am schwächsten ist es bei beschleunigtem
   Wachstum und beschleunigter Inflation (+0,54 R). Ein Regime-Problem hat CTNL nicht,
   der Hebel bleibt der Trend-Regime-Filter, siehe [[ctnl-kostenvalidierung]].
4. **CLS widerspricht sich zwischen IS und OOS.** Die IS-Zelle g↑·accel × π↑·slow ist mit
   +1,28 R die beste (n 10). Im OOS war genau diese Zelle die schlechteste (Sharpe −1,65,
   siehe [[residual-edge-check]]). Das zeigt, dass die Zellen bei so wenigen Trades rauschen.
5. **Die Corona-Phase (g↓, 2020/21) ist kein eigenes Regime, sondern ein einziger Block.**
   ORB NASDAQ hatte dort −0,58 R (Nov. 2020–Jan. 2021). Daraus lässt sich nichts lernen,
   siehe [[orb-neues-regime-2026]].
6. **Die Karte wechselt häufig:** seit 2019 rund 50-mal, also alle 1–3 Monate, weil der CPI
   monatlich kommt. Eine Regel „Bein X nur in Regime Y“ würde ständig an- und abschalten.

## Vier-Fragen-Check
1. **Warum verdient es Geld?** Die Beine verdienen ihr Geld unabhängig von
   Wachstum × Inflation. Ihre Edges sind intraday- oder mikrostrukturgetrieben.
2. **Wo verliert es am meisten?** ORB im Regime g↑·slow × π↑·accel, gemessen im IS.
3. **Was ist dort anders?** Offen. Steigende Inflation bei nachlassendem Wachstum kann
   Zins-Unsicherheit am Open bedeuten, also mehr Fehlausbrüche. Gemessen ist das nicht.
4. **Welche eine Regel könnte helfen?** ORB in diesem Regime mit halbem Risiko. Das wäre eine
   gezählte Variante und bräuchte ein Forward-Fenster. Da ORB auch ohne Regime den Tresor
   nicht bestanden hat ([[orb-neues-regime-2026]]), lohnt sie sich kaum.
   **Empfehlung: keine Regel einführen.**

## Folgen für den Makro-Agenten
- Die Regimekarte bleibt Kontext (Rolle R). Sie ist kein Ein-/Aus-Schalter für die Beine.
- Lohnen könnte eine Anzeige im Wochenbericht: „Aktuelles Regime, IS-Stärke je Bein“. Das ist
  rein informativ, ohne Regel.
- Am 29.10. kommt der GDP-Advance-Print. Er kann das Regime wechseln.
