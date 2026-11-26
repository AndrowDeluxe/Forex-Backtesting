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
| 1 | RSI | ✅ | `indikatoren.py`, TV-geprüft | 26.11. getestet |
| 2 | RSI Multi Length [LuxAlgo] | ✅ | `indikatoren.py`, TV-geprüft | 26.11. getestet |
| 3 | Stoch RSI | ✅ | `indikatoren.py`, TV-geprüft | 26.11. getestet |
| 4 | MACD | ✅ | `indikatoren.py`, TV-geprüft | 26.11. getestet |
| 5 | Bollinger Bands | ✅ | `indikatoren.py`, TV-geprüft | 26.11. getestet |
| 6 | Nadaraya-Watson | ✅ | `indikatoren.py`, TV-geprüft | 26.11. getestet |
| 7 | MA Cross 12/20 (D), 8/14 (H4) | ✅ | `rules.py`, Filter T1 | T1 in Filter-Matrix |
| 8 | Fractals | ✅ | `rules.py` (Bill Williams 2/2) | Auslöser Typ R |
| 9 | Pivots | ✅ | – | ⬜ |
| 10 | Volumen | ✅ | – | ⬜ |
| 11 | SVP/VRVP | ✅ | Volumen-POC 20 T (Filter X11) | X11 in Filter-Matrix |
| 12 | Money Flow Profile | ✅ | – | ⬜ |
| 13 | COT | ⏸ Dennis-Education | M7 COT-Fluss, X4 COT-Index | M7/X4 in Filter-Matrix |

## Nutzer-Antworten 26.11. (Kurzfassung)

RSI und Multi Length sind die Kernpaarung: Im Daily und H4 „funktioniert es sehr, sehr gut“. In Gold gibt es
fast immer eine kurzfristige Richtungsänderung, wenn der RSI seine MA kreuzt bzw. der Multi Length eine starke
Kauf-/Verkaufszone zeigt. „Mit diesen zwei Indikatoren allein konnte man im Daily schon gute, kleine Setups
catchen.“ Stoch RSI, MACD und BB kommen als weitere Confis dazu, Einstieg jeweils über den Cross. Alle
Indikatoren lassen sich in Kombination auch im LTF nutzen. Einstellungen per TradingView-Screenshot belegt.

**Indikatoren im Daily-Chart des Nutzers (Gold, 26.11.):** sichtbar RSI (+MA), RSI Multi Length [LuxAlgo],
ATR, COT-NocTrading (Non-Commercials / Commercials / Retail), Volumen, Daily Range, Jon Fibs Lon & NY Open,
Midnight Open. Ausgeblendet: SVP, VRVP, MA Cross, Fractals, BB, Sessions, LuxAlgo Money Flow Profile, Pivots,
QuantForceX QX Intelligence Dashboard.

## 1 RSI ✅

- **Misst:** „Fairness des Preises“ im gewählten Timeframe. 30–70 = Fair Value, über 70 / unter 30 =
  überproportional bullish/bearish (über-/unterkauft).
- **Einstellungen (Nutzer 26.11.):** **Länge 14** auch im Daily (nicht die Kurs-Variante 20), Quelle Close,
  MA des RSI (SMA 14). Haupt-Timeframes **Daily und H4**.
- **Lesart:**
  - RSI steigt → Chart steigt (Bestätigung der Richtung).
  - **Überkauft/überverkauft ist kein valides Hoch/Tief.** Im HTF reagiert der Markt aber oft bei > 70 / < 30.
  - Nach einem IPDA-Shift gilt bullishe Stimmung, bis der RSI über 70 geht. Bei der ersten Reaktion über 70
    darf man erstmals Trades gegen den Trend suchen.
  - **Divergenz** (Preis neues Hoch, RSI tieferes Hoch) als Bestätigung.
  - **Cross RSI/MA = Auslöser** (Nutzer 26.11., gilt auch auf Daily/H4): Gold dreht danach fast immer
    kurzfristig. Kurs: erst nach dem Cross nach Sells suchen, filtert das Rauschen davor.
- **Edge:** HTF-Daily-Trade, Confi „RSI überkauft/überverkauft und RSI-Cross“, Typ R (RSI-Extrem vor dem Fractal).
- **Testhypothese:** Daily/H4, RSI(14) kreuzt seine SMA(14) nach einem Extrem (> 70 / < 30) → kurzfristige
  Gegenbewegung. Allein und zusammen mit Multi Length.

## 2 RSI Multi Length [LuxAlgo] ✅

- **Misst:** Stärke über mehrere RSI-Längen (10–20) gleichzeitig. Kurs: „Stärke/Schwäche gewinnt an
  Aussagekraft, wenn sie in mehreren Timeframes messbar ist“ → höhere Chance auf einen Umkehrpunkt.
- **Einstellungen (Nutzer 26.11.):** Max. Länge 20, Min. Länge 10, **Overbought 70, Oversold 30**, Quelle Close.
  (Die frühere Angabe 25/75 ist damit überholt.)
- **Anzeige:** Linie = Durchschnitts-RSI. Grüne/rote Flächen = Anteil der Längen über Overbought bzw. unter
  Oversold (0–100 %). Die Schwellenlinien im Chart sind **beweglich** (26.11. Gold Daily: 71,70 / 26,47).
- **Lesart (Nutzer 26.11.):** Signal ist die **Fläche**, nicht die Linie. **Je größer die ausgebrochene
  Fläche, desto valider das Setup.** Zusammen mit dem RSI-Cross (§1) die Kernpaarung im Daily.
  Kurs-Beispiel EURUSD H4 April 2025: zwei grüne Spikes + RSI-Divergenz → Hoch.
- **Edge:** HTF-Daily-Trade, Typ R: „RSI Multi Length ≤ 30 in den 20 Handelstagen bis zum Fractal“.
- **Code-Lücke:** `rules.py` mittelt RSI 10–20 und prüft die Linie. Der Nutzer liest aber die Fläche. Nachbau
  aus dem offenen Pine-Quelltext (Anteils-Fläche + bewegliche Schwellen), dann an einigen Daily-Kerzen gegen
  TradingView prüfen. Typ R danach mit der Fläche statt der Linie neu rechnen.
- **Testhypothese:** Flächengröße (Anteil der Längen jenseits 70/30, Höhe und Dauer) als Stärke-Maß:
  größere Fläche → bessere Gegenbewegung?

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

## 3 Stoch RSI ✅

- **Misst:** Stochastik-Formel auf den RSI angewandt (0–100), also wo der RSI in seiner eigenen
  Spanne der letzten n Kerzen steht. Reagiert viel schneller als der RSI.
- **Einstellungen Daily (Nutzer-Screenshot 26.11.):** **K 3, D 3, RSI-Länge 14, Stochastik-Länge 14, Close**,
  Zeitrahmen Chart, auf Kerzenschluss warten. Im Kurs-LTF auch Stochastik-Länge 8 („3 3 14 8“).
- **Lesart (Nutzer 26.11.):** Einstieg in Verbindung mit den anderen Indikatoren **über den Cross K/D**.
  Kurs (LTF, EURUSD 11.04.2025): Phase flach am Boden/oben, danach der Cross als Timing im Settlement-Fenster.
- **Edge:** HTF-Daily-Trade nennt „Stoch-RSI-Ausschlag“ als Confi.
- **Testhypothese:** K/D-Cross (aus dem Extrembereich) als Einstiegs-Timing nach RSI-/Multi-Length-Signal.

## 4 MACD ✅

- **Misst:** Differenz zweier EMAs (Trend) + Signallinie; Histogramm = Abstand MACD/Signal.
- **Einstellungen Daily (Nutzer-Screenshot 26.11.):** **8 / 20 / 14**, Close, Oszillator und Signal je EMA,
  auf Kerzenschluss warten. Standard sonst 12/26/9.
  **⚠️ Code-Abweichung:** `rules.py` rechnet auf Daily mit 12/26/9 → Typ R mit 8/20/14 neu rechnen.
- **Lesart (Nutzer 26.11.):** Einstieg = **Cross der zwei Linien** (MACD/Signal).
  Kurs dazu: über/unter der 0-Linie bullish/bearish; wachsender Abstand = Trendstärke; Divergenz für echte
  lower lows/lower highs und Gewinnbereiche; Daily für TP-Bestimmung in IPDA.
- **Nutzer 02.11.:** MACD-Cross nach RSI-Extrem = „sehr valides Setup“ → höhere Risikostufe.

## 5 Bollinger Bands ✅

- **Misst:** SMA ± k Standardabweichungen = Schwankungsbreite um den „Fair Value“ (Mittellinie).
- **Einstellungen (Nutzer-Screenshot 26.11.):** **20, SMA, Close, 2 Abweichungen, Offset 0**, auf
  Kerzenschluss warten. Auch im **Daily** (Kurs sagte „sehr selten Daily“; der Nutzer nutzt es dort).
  Kurs-Intraday-Variante BB 34 SMA hl2 2,5 (Settlements EURUSD 10 min).
- **Lesart (Nutzer 26.11.):** (a) **Berührung** des oberen/unteren Bands in Kombination mit den anderen
  Indikatoren; (b) vor allem **Durchbruch mit Kerzenschluss** über/unter dem Band; (c) im **Weekly/Monthly
  ist auch die Mittellinie** eine relevante Zone (Berührung).
  Kurs: Ziel Fib-Extension 1,272/1,618 bzw. Gegenband, Bänder validieren OBs/Breaker.
- **Edge:** Settlements/Time-and-Price (Intraday), HTF-Daily-Trade Confi „Ausbruch in BBs oder NW“.
- **Testhypothese:** Daily-Schluss außerhalb des Bands (± RSI/Multi-Length-Extrem) → Gegenbewegung.

## 6 Nadaraya-Watson Envelope [LuxAlgo] ✅

- **Misst:** geglättete Kurve (Kernregression) mit Hülle; Pfeile, wenn der Preis die Hülle kreuzt.
- **Einstellungen (Kurs):** **8 / 3 / Close** (Bandbreite 8, Multiplikator 3).
- **Repaint:** Die Kursbilder zeigen „Repainting Mode Enabled“. **Nutzer 26.11.: live ist Repainting aus.**
  Nachbau und Backtest daher nur in der nicht-repaintenden Variante (Endpunkt-Schätzung), wie live.
- **Lesart:** wie BB: Berührung/Ausbruch der Hülle + Pfeil als Bestätigung, OB-Validierung („sehr starker
  OB-Magnet“), Exit über Zeit, Fib-Extension oder Ausbruch → finaler Scalp-TP (Handschrift, siehe oben).
  Fazit des Kurses: weniger Setups, aber valider.

## 7–13 (Nutzer-Antworten 26.11. abends)

Belegt aus Edge Card 02.11. [[htf-daily-trade-edge-card]], Code und den Nutzer-Antworten vom 26.11. mit sechs
Chart-Beispielen (Gold D1 Pivots, EURUSD H4/H8/D1 Volumen, SVP, VRVP, Money Flow).

### 7 MA Cross ✅
- **Einstellungen:** Daily **SMA 12/20** (TradingView „MA Cross“, Kerzenschluss abwarten) — primär genutzt.
  **Weekly 20/50** als Zusatz zum Hochskalieren des Risikos (02.11.). **H4 8/14** als möglicher Einstiegs-Bestätiger
  (Nutzer 26.11., Idee, bisher nicht genutzt). „MA 8 und 14“ im Kurs (Elite 1) meint die 8-/14-Tageskerze im IPDA.
- **Lesart:** Signal-Bestätiger, kein eigener Signalgeber (Typ R: Confi, keine Pflicht).
- **Code:** Filter T1 (12/20), T2 Weekly SMA 20/50. **Test:** H4 8/14-Cross als Einstiegs-Bestätiger nach Daily-Signal.

### 8 Fractals ✅
- **Einstellungen:** Bill Williams 2/2 (5 Kerzen), Skript mit ZigZag, Time-Fractals auf 240 (02.11.).
- **Lesart:** Confirmation, **kein einzelner Signalgeber**. Im Daily für Struktur und Stop (Stop am Fractal-Extrem),
  im H4 selten.
- **Code:** `rules.py`, Typ-R-Auslöser. **Test:** Stop am Daily-Fractal statt Signalkerze im Fib-Limit-Kandidaten.

### 9 Pivots ✅
- **Einstellungen:** je Timeframe umgestellt, meist **monatliche oder Quartals-Pivots** (Bild: Gold D1, P/R1–R4/S1–S4).
- **Lesart:** **Reaktionszonen.** Höherer Zeitraum = stärkere Confi (Quartal > Monat > Woche > Tag), höhere Stufe =
  wahrscheinlichere Reaktion (R3 > R1, S3 > S1). Auch Ziel (Edge Card).
- **Code:** – . **Test:** Reaktion an Monats-/Quartals-Pivots je Stufe (Abprall-Quote, R3/S3 vs. R1/S1), als Ziel/Filter.

### 10 Volumen ✅
- **Lesart:** **Divergenz als Richtungswechsel-Hinweis.** Bsp. EURUSD H4 (Bild 2): Aufwärts mit höherem Tief, aber
  deutlich weniger Kaufvolumen → Käufer werden weniger, Abverkauf geht weiter. Umgekehrt (Bild 3): mehr
  Verkaufsvolumen, aber kein neues signifikantes Tief → Verkäufer geben die Kontrolle ab.
- **Daten:** FX/Metalle = Tick-Volumen. **Test:** Preis-/Volumen-Divergenz an Swings (H4/D1) → Umkehr-Quote vs. Zufall.

### 11 SVP / VRVP ✅
- **SVP (Session Volume Profile), Daily/H4 — Trendfolge:** POC jeder Periode konstant unter dem vorherigen → Abwärts-
  trend intakt, weiter Sells. POC steigt gegenüber Vortag/Vorperiode → mögliches Retracement oder Richtungswechsel
  (Bild 4). Long spiegelbildlich.
- **VRVP (Visible Range):** immer über eine **HTF-Range** legen (Monats-/Quartals-Hoch bis -Tief oder nach einem langen
  Trend Hoch → Tief, Bild 5). **POC = Anziehungspunkt** für das Retracement bzw. Grenze, ab der Trendfortsetzung
  möglich ist; Hochvolumen-Knoten als Ziele (EURUSD D1: 1,12 / 1,138; H8 Range: 1,105 / 1,122).
- Multi-Timeframe von Monthly bis H1. **Code:** X11 POC 20 T (anders gerechnet). **Test:** SVP-POC-Folge als Trendfilter;
  Retracement bis VRVP-POC (Trefferquote, Laufweite).

### 12 Money Flow Profile [LuxAlgo] ✅
- **Lesart:** Ergänzung zum VRVP — Zonen, in denen **beide übereinstimmen**, sind besonders interessant (Bild 6).
- **Test:** erst mit 11 (Übereinstimmung VRVP-Knoten × Money-Flow-Zone).

### 13 COT ⏸
- Wenig eigene Erfahrung; Nutzer orientiert sich an der **neuen Education von Dennis aus den Elite-Calls**
  ([[smh-dennis-cot-volumen-calls]]). Steckbrief folgt daraus. Code bleibt: M7 COT-Fluss, X4 COT-Index.

## Nachbau + Edge-Test 1–6 (26.11.)

**Nachbau** `htf_daily_trade/indikatoren.py`, geprüft mit `tv_abgleich.py` gegen TradingView-Exporte (FXCM,
XAUUSD + EURUSD, D1 + H4, `htf_daily_trade/tv_referenz/`): RSI, RSI-MA, Multi Length (Mittel, Kanäle, Flächen),
ATR, NW-Hülle stimmen nach der Aufwärmphase auf Rundungsfehler genau. Das BB im Chart-Export hat Basis SMA 34 auf
hl2 (anderes BB als 20/close/2 aus dem Steckbrief). Stoch RSI + MACD waren nicht im Export (Standardformel).

**Eigener Edge** (`indikator_edge.py` Teil A, Lock `indikator_kombi_daily`, 54 Varianten, 9 Märkte, Daily,
Einstieg Folgetag-Open, Stop 5-Tage-Extrem − 0,2 ATR, netto ohne Swap):
- RSI-MA-Cross allein: ≈ 0 R (IS −0,02, OOS ±0).
- **Cross + ML-Fläche ≥ 50 % in den letzten 3 Tagen, 10 Tage halten: IS +0,13 R (n 176), OOS +0,17 R (n 135),
  OOS 8/9 Märkte positiv, t je ~1,3.** Die Fläche macht den Unterschied (Nutzer-Lesart bestätigt in der
  Richtung), aber nicht signifikant → Kandidat, kein Edge. Tresor zu.
- Beste IS-Varianten (mit NW-Bestätigung, n 36–46) fallen im OOS auf ~0.

**Als Filter** (Teil B, Stand bis Vortag des Fülltags bzw. letzte geschlossene H4-Kerze):
- Daily C2: Momentum in Trade-Richtung hilft leicht und stabil: RSI-Cross mit IS +0,45 / OOS +0,27 R (Basis
  +0,22 / +0,16), MACD 8/20/14 mit +0,33 / +0,20.
- Daily Typ R: ML-Fläche ≥ 50 % mit IS +0,75 / OOS +0,14 R (Basis +0,29 / −0,08, OOS n 50).
- H4 (h4_ny15 Top-3 je Klasse): IS-Verbesserungen (ML-Fläche, MACD, RSI) kippen im OOS — kein stabiler Filter.

## Übereinanderlegen + MTF-Einstieg (26.11. mittags)

- **Übereinanderlegen/Risikoskalierung** (`indikator_mtf.py` Teil 1): Zusatz-Bestätigungen am Signaltag (MACD-,
  Stoch-Cross, BB-Berührung, NW außerhalb) zählen. Kandidat Fläche ≥ 50 %: Score 3+ IS +0,46 R, OOS −0,19 R;
  Score 1 IS −0,05, OOS +0,33. Kein stabiler Zusammenhang → keine Skalierung (S1 verschlechtert OOS).
- **MTF** (Teil 2, Lock `indikator_mtf_ltf`): Setup Daily/H4 (Fläche, Kandidat, ≥ 2 von 4 Bausteinen, H4-Zählung),
  Einstieg H1/M15 über BB-Rückkehr, NW-Rückkehr, RSI-Cross. Mit LTF-Stop: Treffer 8–19 %, Ergebnis aus 5 Ausreißern
  (50–90 R), ohne sie negativ. Mit Daily-Stop: LTF-Timing nicht besser als der Daily-Einstieg.
- **Kandidat Fläche ≥ 50 % + RSI-Cross** (`indikator_flaeche.py`, 144 Nachbarn): 93 % IS / 92 % OOS > 0 → Idee
  robust. Basis mit Swap-Näherung IS +0,04 / OOS +0,09 R, ohne Top-5 ≈ 0, 2025 −0,28 / 2026 −0,29 R, MC 21 % Ø < 0,
  DD 95 % −32 % bei 1 %. Cross innerhalb der Fläche (L1) stärker, aber ~4 Trades/Jahr.
  **Lesart:** Die Fläche ist Kontext, kein eigenständiger Edge.

## Fib-Limit nach Daily-Ausbruch (Nutzer-Idee 26.11. nachmittags)

Nutzer: Nach dem Daily-Ausbruch (ML-Fläche extrem + Stoch-/RSI-Cross) im H1 nur die Fib-Range suchen und als
Limit am 0,5-Fib des Signaltags kaufen/verkaufen; SL Vortageshoch/-tief oder ATR-Kombination. Beispiel Gold
29.01.2026 → Einstieg 30.01. ~4 R. Test `htf_daily_trade/indikator_fib_limit.py` (Lock `indikator_fib_limit`,
288 Varianten, Daily-Simulation, in der Füllkerze nur Stop):
- Plateau (IS und OOS gleich gerichtet): Fläche ≥ 80 % > ≥ 50 %; Fib 0,5 > 0,618; Stop + 0,25/0,5 ATR > nackt;
  10-Tage-Ausstieg > 2/3/4 R. Nur der Cross-Typ wechselt (RSI im IS, Stoch/beide im OOS) → „beide“ (GX).
- **A80 GX F0.5 V3 S2 T10:** IS +0,33 R (n 168, t 1,8) / OOS +0,45 R (n 127, t 2,0); mit Swap +0,27 / +0,40;
  ohne Top-3 +0,14 / +0,20; 2025 +0,02, 2026 +1,23 (n 10); Long und Short positiv; 7/9 Märkte (Gold −0,05,
  AUD −0,10); MC 0,4 % Ø < 0, DD 95 % −29 % bei 1 %.
- Gold-Beispiel nachgebaut: Signal 29.01., Füllung 30.01. 5438 (Open unter Limit), Stop 5595 → +4 R am 02.02.
- **Lesart:** Die Fläche liefert die Idee, das Fib-Limit macht daraus einen tragfähigen Einstieg (Markt-Einstieg
  nur +0,13/+0,17 R). Offen: Füllreihenfolge mit H1 prüfen, dann Einfrieren + Tresor.

**H1-Prüfung (26.11. abends, `indikator_fib_h1.py`):** Füllung/Stop Kerze für Kerze auf H1. Mit UTC-Tagen wie im
Backtest: IS +0,33 / OOS +0,42 R (V3, Stop +0,25 ATR) → Füllreihenfolge sauber, Stop am Fülltag in ~22 % der Trades.
**Mit Broker-Tagen (NY 17:00, = TradingView-FXCM-Daily):** IS +0,31 / **OOS +0,12 R (t 0,65), ohne Top-3 −0,06**,
2025 −0,41. Der Edge hängt an der Tagesgrenze → schwächer als gedacht; vor dem Einfrieren Tagesdefinition festlegen.
