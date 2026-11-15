# Forward-Regel Aktien- + Krypto-Screener (festgelegt 15.11.2026, Version 1.0)

Vorab festgelegt, bevor ein einziges Ergebnis ausgewertet ist. Nach dem Forward-Start nicht mehr ändern;
jede Änderung an Gewichten, Schwellen oder Zonenregeln = neue `VERSION` in `config.py` und eigene Auswertung.

## Ablauf

1. **Probebetrieb** ab 15.11.2026: Das Ledger schreibt mit `status = probe`. Zählt nicht.
2. Der Nutzer sieht die ersten Berichte durch. Danach wird `FORWARD_START` in `config.py` gesetzt (Datum).
   Ab da `status = forward`.
3. **Auswertung frühestens**, wenn eine der beiden Bedingungen erfüllt ist (je Screener getrennt):
   - 3 Monate nach `FORWARD_START`
   - 50 gefüllte Szenarien

## Was gemessen wird

- **Szenarien** (A Limit in der Zone, B Stop über dem Widerstand): Füllung innerhalb von 10 Handelstagen,
  danach Stopp/Ziel innerhalb der Kerze, Stopp vor Ziel, Zeitausstieg nach 20 Kerzen. Ergebnis in R nach
  Kosten (Aktien 5 bps, Krypto 10 bps Round-Trip).
  - alle berechneten Szenarien
  - nur die vom LLM gewählten (`gewaehlt = True`)
- **Gruppen** je Tag: KAUFEN (Score ≥ 65), VERKAUFEN (≤ 35), TOP10. Gleichgewichtete Rendite nach 5/20/60
  Kerzen gegen das gleichgewichtete Universum und gegen die Benchmark (SPY bzw. BTC).
- **Referenz:** NVDA-Handanalyse vom 15.11.2026 (Stand 13.11.), Szenarien A 149–158 / Stopp 145 / Ziel 180
  und B über 172 / Stopp 158 / Ziel 180. Gleiche Auswertung, eigener Status `referenz`.

## Erfolg (alle drei müssen gelten)

1. Ø R der gefüllten Szenarien > 0 nach Kosten.
2. KAUFEN-Gruppe schlägt im 20-Kerzen-Horizont im Schnitt **sowohl** das Universum **als auch** die Benchmark.
3. VERKAUFEN-Gruppe liegt im 20-Kerzen-Horizont im Schnitt unter dem Universum.

Kriterium 2 ist die Kontrolle gegen reines Markt-Beta (Memory „t > 2, aber nur Long-Beta“): Eine Long-
Empfehlung, die nur den Markt mitnimmt, besteht nicht.

## Bekannte Grenzen

- Fundamentaldaten von Yahoo sind der heutige Stand, nicht historisch. Deshalb gibt es keinen Backtest des
  Scores, nur diesen Forward-Test.
- Die LLM-Einordnung ist nur vorwärts prüfbar (Memory „LLM-Agent nur vorwärts testbar“).
- Neue Szenarien für denselben Titel werden erst angelegt, wenn das vorige abgeschlossen ist.
