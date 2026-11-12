# Indikator-Steckbriefe

Seit 12.11.2026 (Nutzerauftrag 10.11., vor dem nächsten Edge). Je Indikator: was er misst, Einstellungen,
wie der Nutzer ihn liest, in welchem Edge er vorkommt, Stand im Code, offene Fragen. Danach Nachbau
(gegen TradingView-Werte geprüft) und Edge-Test je Indikator unter der [[overfitting-sperre]]
(allein auf Daily, 9 Märkte, und als Filter auf C2/Typ R).
Quelle: Elite-2-Kurs, OneNote „Statistiken und Indikatoren“ (`fusion_lab/raw/onenote/…/Elite 2/
Statistiken und Indikatoren/`), plus Nutzer-Screenshots 02.11. in [[htf-daily-trade-edge-card]].
Status: ✅ bestätigt · 📝 Entwurf, wartet auf Nutzer · ⬜ offen.

| # | Indikator | Steckbrief | Code | Test |
|---|---|---|---|---|
| 1 | RSI | 📝 | `htf_daily_trade/rules.py` `rsi()` (Wilder) | ⬜ |
| 2 | RSI Multi Length [LuxAlgo] | 📝 | nur Näherung (Mittel RSI 10–20), **nicht** LuxAlgo | ⬜ |
| 3 | Stoch RSI | ⬜ | – | ⬜ |
| 4 | MACD | ⬜ | `rules.py` (12/26/9, Cross) | ⬜ |
| 5 | Bollinger Bands | ⬜ | – | ⬜ |
| 6 | Nadaraya-Watson | ⬜ | – (Repaint-Gefahr) | ⬜ |
| 7 | MA Cross 12/20 | ⬜ | `rules.py`, Filter T1 | T1 in Filter-Matrix |
| 8 | Fractals | ⬜ | `rules.py` (Bill Williams 2/2) | Auslöser Typ R |
| 9 | Pivots | ⬜ | – | ⬜ |
| 10 | Volumen | ⬜ | – | ⬜ |
| 11 | SVP/VRVP | ⬜ | Volumen-POC 20 T (Filter X11) | X11 in Filter-Matrix |
| 12 | Money Flow Profile | ⬜ | – | ⬜ |
| 13 | COT | ⬜ | M7 COT-Fluss, X4 COT-Index | M7/X4 in Filter-Matrix |

## 1 RSI 📝

- **Misst:** „Fairness des Preises“ im gewählten Timeframe. 30–70 = Fair Value, über 70 / unter 30 =
  überproportional bullish/bearish (über-/unterkauft).
- **Einstellungen (Kurs):** Standard, Länge 14, Quelle Close, dazu MA des RSI (SMA 14).
  **Ausnahme Daily: Länge 20** („für mögliche IPDA-Umkehrpunkte“). Unter Daily 14.
- **Lesart:**
  - RSI steigt → Chart steigt (Bestätigung der Richtung).
  - **Überkauft/überverkauft ist kein valides Hoch/Tief.** Im HTF reagiert der Markt aber oft bei > 70 / < 30.
  - Nach einem IPDA-Shift gilt bullishe Stimmung, bis der RSI über 70 geht. Bei der ersten Reaktion über 70
    darf man erstmals Trades gegen den Trend suchen.
  - **Divergenz** (Preis neues Hoch, RSI tieferes Hoch) als Bestätigung.
  - **Erst wenn die MA des RSI den RSI kreuzt, nach Sells suchen.** Das filtert Rauschen davor und verkleinert
    die Zone (Beispiel EURUSD M1 21.04.2025: „relevanter Cross“ nach dem Hoch, nicht der davor).
- **Edge:** HTF-Daily-Trade, Confi „RSI überkauft/überverkauft und RSI-Cross“, Typ R (RSI-Extrem vor dem Fractal).
- **Offen:** Daily-Länge 20 oder 14? Gilt der MA-Cross nur für LTF-Einstiege oder auch auf Daily?

## 2 RSI Multi Length [LuxAlgo] 📝

- **Misst:** Stärke über mehrere RSI-Längen (10–20) gleichzeitig. Kurs: „Stärke/Schwäche gewinnt an
  Aussagekraft, wenn sie in mehreren Timeframes messbar ist“ → höhere Chance auf einen Umkehrpunkt.
- **Einstellungen (Kurs):** Max. Länge 20, Min. Länge 10, Overbought 70, Oversold 30, Quelle Close.
  **Nutzer 02.11.: orientiert sich an 25 / 75.**
- **Anzeige:** Linie = Durchschnitts-RSI. Grüne/rote Flächen = Anteil der Längen über Overbought bzw. unter
  Oversold (0–100 %). Die Schwellenlinien im Chart sind **beweglich** (z. B. 74,7 / 29,1), nicht fix 70/30.
- **Lesart:** Signal, wenn der normale RSI über 70 (unter 30) ist **und** gleichzeitig ein grüner (roter)
  Ausbruch im Multi Length erscheint. Danach weitere Confis: Divergenz, IPDA-Zeit, NW/BB-Ausbruch, RSI-MA-Cross.
  Kurs-Beispiel EURUSD H4 April 2025: zwei grüne Spikes + RSI-Divergenz → Hoch.
- **Edge:** HTF-Daily-Trade, Typ R: „RSI Multi Length ≤ 30 in den 20 Handelstagen bis zum Fractal“.
- **Code-Lücke:** `rules.py` mittelt RSI 10–20. Das ist nicht die LuxAlgo-Formel (andere Mittelung,
  bewegliche Schwellen, Anteils-Flächen). Nachbau aus dem offenen Pine-Quelltext, dann an einigen
  Daily-Kerzen gegen deine TradingView-Werte prüfen. Die Typ-R-Ergebnisse können sich dadurch verschieben.
- **Offen:** Meinst du mit 25/75 die Einstellung im Indikator (Overbought 75 / Oversold 25) oder liest du
  die Linie gegen 25/75? Zählt als Signal die Fläche (Spike) oder die Linie?

## 3–13 offen

Quellen gefunden: Stoch RSI (2 Seiten), MACD, NW + Bollinger (+ „Edge-Erweiterung Settlements und
Nadaraya/Bollis“), „MA 8 und 14“ (Elite 1). Für Pivots, Money Flow Profile und SVP/VRVP noch keine
Kursseite gefunden. Volumen und COT: [[smh-volumen-delta-und-cot-calls]], [[smh-dennis-cot-volumen-calls]].
