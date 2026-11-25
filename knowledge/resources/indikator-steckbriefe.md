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
| 3 | Stoch RSI | 📝 | – | ⬜ |
| 4 | MACD | 📝 | `rules.py` (12/26/9, Kurs Daily 8/20/14!) | ⬜ |
| 5 | Bollinger Bands | 📝 | – | ⬜ |
| 6 | Nadaraya-Watson | 📝 | – (Kurs nutzt Repaint-Modus) | ⬜ |
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

**Ergänzung (Seite „Multi RSI“, 25.11.):** Einsatz vor allem H4 (EURUSD April 2025): Hoch mit
NW-Pfeil + BB-Ausbruch + grünem Multi-Length-Spike + RSI über 70. Kurs-Zitate: „Auch Target Levels mit dem
Multi RSI validieren“, „RSI-Divergenz nutzen, um Trades zu generieren“, „Ipda-Shift, wenn wir auf 70er RSI
sind, keine Trendwende vorher“. Kontertrades: schnell Partials ziehen, eigene Confis/Actionplan für mit
und gegen den Trend. Grundsatz: „Indikatoren validieren unsere Basissetups“, kein eigenes Einstiegssignal.

## Lücke im OneNote-Export (25.11.)

Handschrift (Ink) fehlt im Export: Die NW-Seite hat in OneNote handschriftliche Notizen (Nutzer-Screenshot
25.11.: „Exit: Time; Fib-Extension, Ausbruch → finaler Scalp-TP!“, „Sehr starker OB-Magnet! → Validierung
der OBs mgl.!“, „OB-Validierung!“, „Wir bekommen weniger Setups, aber sie sind so viel valider!“, „Kein
Platz mehr für Emotionen → wir gehen mit statistischer Sicherheit“). Lokal ist nur der Titel angekommen.
Gilt vermutlich für weitere Seiten (Seite „Zusammenfassung Mon. 1“ ist lokal ganz leer) → Handschrift-
Seiten bei Bedarf per Screenshot nachreichen.

## 3 Stoch RSI 📝

- **Misst:** Stochastik-Formel auf den RSI angewandt (0–100), also wo der RSI in seiner eigenen
  Spanne der letzten n Kerzen steht. Reagiert viel schneller als der RSI.
- **Einstellungen (Kurs):** K 3, D 3, RSI-Länge 14, Stochastik-Länge 14, Quelle Close (Standard). In späteren
  Kursbildern auch **Stochastik-Länge 8** („3 3 14 8“).
- **Lesart (nur aus Kursbildern, kein Text auf der Seite):** Einsatz im **LTF** (5 s bis 30 min, EURUSD
  11.04.2025). Markiert werden (a) Phasen, in denen der Stoch RSI flach am Boden (0) bzw. oben (100) klebt,
  und (b) der folgende Kreuzungspunkt K/D, als Timing im Settlement-Fenster, zusammen mit Multi-Length-
  Spike und RSI.
- **Edge:** HTF-Daily-Trade nennt „Stoch-RSI-Ausschlag“ als Confi; im Chart des Nutzers als Panel.
- **Offen:** Daily-Einstellung? Gilt ein Ausschlag (0/100) oder der K/D-Cross als Confi?

## 4 MACD 📝

- **Misst:** Differenz zweier EMAs (Trend) + Signallinie; Histogramm = Abstand MACD/Signal.
- **Einstellungen (Kurs):** Standard 12/26/9, **Daily IPDA-Einstellung 8 / 20 / 14** („MACD 8 20 close“
  im Kurschart EURUSD 1T). **Code-Abweichung:** `rules.py` rechnet auch auf Daily mit 12/26/9.
- **Lesart (Kurstext):**
  - Über der 0-Linie bullish, darunter bearish (Text sagt zweimal „über“, gemeint ist über/unter).
  - Trendindikator; Volumen bestätigt Fortsetzung. Wird der Abstand MACD–Signal größer, steigt die Trendstärke.
  - **Divergenz** (Preis höheres Hoch, MACD tieferes Hoch bzw. umgekehrt): echte lower lows / lower highs
    erkennen, Gewinnbereiche „callen“, Divergenz-Erweiterung im Trend.
  - Mit klassischem SMH (Zonen, OBs) „super crazy Entries“, auch im LTF (Gold 10 min Beispiel).
  - Daily: TP-Bestimmung in IPDA, IPDA-Shift „so vorhersehbar“ (EURUSD Mai 2025).
- **Nutzer 02.11.:** MACD-Cross nach RSI-Extrem = „sehr valides Setup“ → höhere Risikostufe.
- **Offen:** Daily wirklich 8/20/14 (dann Typ R neu rechnen)? Signal = Cross, Divergenz oder 0-Linie?

## 5 Bollinger Bands 📝

- **Misst:** SMA ± k Standardabweichungen = Schwankungsbreite um den „Fair Value“ (Mittellinie).
- **Einstellungen (Kurs):** zwei Varianten: **BB 20 SMA Close 2** (Standard) und **BB 34 SMA hl2 2,5**
  (Intraday, Settlement-Beispiele EURUSD 10 min).
- **Lesart:** „BBs und Nadaraya als zusätzliche Confirmation mit Noise-Filter im HTF (M30, H1, H4, sehr
  selten Daily)“. Einstieg, wenn Preis im Settlement-Fenster (rote Linien / graue Box 08:00–09:00) das
  untere Band berührt und dreht; Ziel Fib-Extension 1,272/1,618 bzw. oberes Band („Profit-Findung in den
  Bollis – Thema Fair Value“). Bänder validieren OBs/Breaker („welcher OB ist wirklich valide“).
  Ausbruch über/unter das Band = Confi für Hoch/Tief (zusammen mit RSI/Multi Length).
- **Edge:** Settlements/Time-and-Price (Intraday), HTF-Daily-Trade Confi „Ausbruch in BBs oder NW“.
- **Offen:** Welche Variante nutzt du heute, für welchen Timeframe?

## 6 Nadaraya-Watson Envelope [LuxAlgo] 📝

- **Misst:** geglättete Kurve (Kernregression) mit Hülle; Pfeile, wenn der Preis die Hülle kreuzt.
- **Einstellungen (Kurs):** **8 / 3 / Close** (Bandbreite 8, Multiplikator 3).
- **⚠️ Repaint:** In den Kursbildern steht „Repainting Mode Enabled“. In diesem Modus wird die Kurve
  rückwirkend neu gezeichnet: Hoch/Tief sehen im Nachhinein perfekt getroffen aus, live nicht. Für Backtest
  nur die nicht-repaintende Variante (Endpunkt-Schätzung) zulässig, und live solltest du dieselbe sehen.
- **Lesart:** wie BB: Berührung/Ausbruch der Hülle + Pfeil im Settlement-Fenster als Bestätigung,
  OB-Validierung („sehr starker OB-Magnet“), Exit über Zeit, Fib-Extension oder Ausbruch → finaler Scalp-TP
  (Handschrift, siehe oben). Fazit des Kurses: weniger Setups, aber valider.
- **Offen:** Hast du live „Repainting Mode“ an? Wenn ja, sind deine Treffer im Chart rückblickend geschönt.

## 7–13 offen

Quellen: „MA 8 und 14“ (Elite 1), Fractals/MA Cross aus [[htf-daily-trade-edge-card]]. Pivots, Money Flow
Profile, SVP/VRVP: noch keine Kursseite gefunden (Pivots tauchen in Nutzer-Charts auf, Gold H4 Okt. 2023).
Volumen und COT: [[smh-volumen-delta-und-cot-calls]], [[smh-dennis-cot-volumen-calls]].
