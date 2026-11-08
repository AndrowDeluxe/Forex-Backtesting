# Area: Makro-Agent – Report prüfen, gewichten, Trades ableiten

Arbeitsweise, nach der der Makro-Agent (Dachprojekt [[quant-diskretionaer-fusion]], Strang 3) später
seinen eigenen Makro-Report erstellt, den der Nutzer prüft. Vorlage ist die Prüfung der zwei
SMT-Reports vom 08.11.2026 (Nutzer, 08.11.: „Genau so soll der Makro Agent später arbeiten und mir
einen Makro Report anfertigen, den ich dann prüfe“). Regeln und Wirkketten selbst stehen in
[[makro-wirkketten-und-regeln]]; diese Notiz legt den **Ablauf und das Ausgabeformat** fest.

## Ablauf (sechs Schritte)

1. **Quelle holen und lesen.** Neue Reports aus Telegram „SMH Daily Update“ ziehen
   (`python -m fusion_lab.ingest.telegram --chat -1002552394198 --skip-video`), PDF-Text extrahieren,
   ganz lesen. Begleitnachrichten von Dennis im Kanal mitlesen (oft widersprechen sie dem PDF).
2. **Faktencheck.** Jede Zahl, die sich prüfen lässt, gegen eigene Daten prüfen: Kurse und
   Wochenveränderungen gegen den Data Lake (`data_lake_store/validated/`), Renditen gegen
   US02Y/DE02Y bzw. FRED, Modellwerte nachrechnen (G8-Score = Mittel der z-Werte je Zeitraum).
   Termine/Konsens/Ereignisse per Websuche. Ergebnis in drei Körbe: ✓ bestätigt · ≈ leichte
   Abweichung · ? nicht prüfbar (Zinsmarkt aus Bezahl-Terminal, Positionierung, Bank-Calls).
3. **Widersprüche suchen.** Innerhalb eines Reports, zwischen den Reports, zwischen Report und
   Kanal-Nachrichten, zwischen Begründung und Daten (Beispiel 08.11.: „Gold fällt bei steigenden
   Renditen“ – tatsächlich Gold +5 %, Renditen tiefer). Ziel und Stop gegen Zonen prüfen, die der
   Report selbst nennt (SNB-Zone vs. EUR/CHF-Ziel).
4. **Gewichten.** Gegen die eigene Evidenz, nicht gegen den Ton des Reports:
   - Richtung bei Markteinstieg ≈ 0 R ([[smh-makro-reports-backtest]]); nur Rücksetzer-Limit
     (0,5 ATR D1) positiv; Edelmetalle tragen, FX-Kreuze negativ.
   - Eigene Filter abfragen (aktuell: [[filter-gold-zinskurve]] → Regime und erlaubte Gold-Richtung).
   - Scorecard des Reports selbst (Trefferquote, Summe R) mitnennen.
   - Szenario-Wahrscheinlichkeiten grob schätzen (ohne Modell, als Schätzung kennzeichnen), Konsens
     und Nowcast als Anker.
5. **Trades ableiten.** Tabelle mit Rang, Trade, Wertung (mit Begründung aus Schritt 4), Umsetzung
   (Limit statt Markt, Stop, Ziel, Größe, Ungültigkeit, Sperrzeiten um Termine). Explizit auch, was
   man **auslässt** oder abwertet und warum.
6. **Mentor-/Chartbild einarbeiten und Alarme.** Kommt ein Chartbild (z. B. Dennis' DXY-Pfad),
   Limits daran anpassen (welche Welle füllt das Limit, mit uns oder gegen uns) und eine
   Alarmliste für TradingView liefern (Symbol · Bedingung · Wert · Bedeutung · Auslöse-Art).
   Tagesschluss-Schwellen als „Bei Bar-Schluss“ auf D1.

## Ausgabeformat (Report an den Nutzer)

1. Stimmen die Zahlen? (✓ / ≈ / ? mit Werten Report vs. eigene Daten)
2. Widersprüche (nummeriert, je ein Satz + Beleg)
3. Gewichtung (Stärke, Schwäche mit eigenen Zahlen, Szenario-Schätzung)
4. Trades nächste Woche (Tabelle, Rang 1 zuerst, inkl. „auslassen“)
5. Alarmliste (falls Chart/Limits)
6. Quellen

Kurz halten, Fazit in einem Satz unter der Tabelle. Keine Anlageberatung; Trades sind Hypothesen.

## Grenzen

- Der Agent setzt keine Orders und keine Alarme selbst, solange kein Browser-Werkzeug verbunden ist.
- Bewertet wird nur vorwärts ([[overfitting-sperre]], Memory „LLM-Agent nur vorwärts testbar“):
  jede Wochenprüfung unten mit Ergebnis nachtragen, damit die Vorlage messbar wird.

---

## Beispiel 1: KW 46/2026 (Reports vom 08.11.2026)

Quellen: Macro-Report 08.11. (msg 6976, 8 S.) + Sonderreport „Der Dollar und seine Zukunft“
(msg 6977, 10 S.), Kurse = Schluss Fr 06.11.

### Faktencheck

- ✓ Kurse vs. Dukascopy: AUD/USD 0,6862 (0,6862), EUR/USD 1,1140 (1,1138), USD/JPY 158,48 (158,44),
  Gold 4.075 (4.069, Woche +5,0 %), S&P 7.377 (7.382), US-2J 4,51 % (4,51 %); Dollar-Wochenänderung
  gegen alle sieben auf 0,1 Pp. genau.
- ✓ NFP +165.000 vs. ~65.000 erwartet; RBA 4,85 % (aber am 03.11. *erhöht*, gespalten);
  Brent ~98–100 $, Woche −13…−15 %, Katar-Vermittlung; G8-Score reproduzierbar.
- ≈ CPI-Erwartung im Report „Gesamt +0,4 %“, Konsens +0,3 % / Kern +0,2 %, Cleveland-Nowcast
  0,24 / 0,21.
- ? BoE 4,00 % einstimmig, Zinsmarkt-Pricing, Positionierung, Bank-Calls.

### Widersprüche

1. EUR/CHF-Ziel 0,8975 unter der selbst genannten SNB-Zone (0,91).
2. EUR/USD Short auf der Watchlist vs. Sonderreport-Regel 2 „Kein Euro-Short auf die Dollar-These“.
3. „Gold Long verworfen: fällt bei steigenden Renditen“ – Woche Gold +5 %, 2J −5…−8 bp; Dennis am
   04.11. im Kanal: Gold-Longs für die nächsten Wochen.
4. AUD-Short vs. Muster 1 im selben Report (nach Midterms laufen Rohstoffwährungen am besten).

### Gewichtung

Fakten sauber, Logik nachrechenbar, Schalter klar. Eigene Scorecard ≈ −0,1 R, 9/15 Richtungen –
passt zu unserem Befund (Richtung ≈ 0 R). Gold-Zinskurven-Filter: Reflation → nur long.
Schätzung CPI Di: BASE (Kern 0,1–0,2) ~55–60 %, Dollar-Bulle (≥ 0,3) ~25 %, Kern ≤ 0,0 ~15 %.

### Trades KW 46

| # | Trade | Wertung | Umsetzung |
|---|---|---|---|
| 1 | AUD/USD Short | Bester Kandidat: Zinsen + Tech-Angst + unter SMA50 (0,7018) | Limit ~0,6885, nach Dennis' DXY-Bild **0,6905**; Stop 0,6990, Ziel 0,6670, halb; NZ-Lücke Mo abwarten; raus bei Kern ≤ 0,0 % oder 2 Tagen Chip-Erholung |
| 2 | Gold nur long, nur Rücksetzer | Gegen den Report; Filter long, Gold einziger Edge-Bereich | Nur Alarm 4.030 (füllt sonst in der DXY-Rally gegen uns); ungültig Schluss < 4.000 |
| 3 | EUR/CHF Short | Abwerten: Kreuz, SNB, HF fast am CHF-Short-Extrem | Gewinne bei 0,905–0,910 sichern, nicht neu einsteigen |
| 4 | EUR/USD Short | Auslassen: Euro-Shorts voll, widerspricht Regel 2 | – |
| 5 | USD/JPY Short | Erst nach Fed 09.12. | – |
| – | Di 14:15–15:30 | Keine neuen Positionen (CPI) | Danach: geht die 2J mit dem Dollar? |

Fazit: AUD-Short per Limit statt Markt, Gold nicht shorten, EUR/CHF und EUR/USD schwächer als im
Report.

### Mentor-Bild (Live-Call 08.11.) und Alarme

Dennis' DXY (1h): A-B-C-Korrektur in die Zone 101,55–101,82 (um CPI), dann Anstieg durch
102,45–102,60 bis ~103,0. Deckt sich mit Report-BASE (101,5–103).

| Symbol | Bedingung | Wert | Bedeutung |
|---|---|---|---|
| TVC:DXY | kreuzt abwärts | 101,82 | C-Welle in der Zone → AUD-Short-Fenster |
| TVC:DXY | Schluss unter (D1) | 101,50 | Zone + These gebrochen |
| TVC:DXY | kreuzt aufwärts | 102,60 | Anstieg bestätigt |
| TVC:DXY | kreuzt aufwärts | 102,95 | Ziel, Dollar-Gewinne sichern |
| AUDUSD | kreuzt aufwärts | 0,6905 | Short-Limit |
| AUDUSD | kreuzt aufwärts | 0,6990 | Stop |
| XAUUSD | kreuzt abwärts | 4.030 | nur Alarm, Long prüfen wenn DXY < 102,6 |
| XAUUSD | Schluss unter (D1) | 4.000 | Gold-Long ungültig |
| EURCHF | kreuzt abwärts | 0,9100 | Gewinne sichern |

### Nachtrag: Dennis' EUR/USD Short (Live-Call 08.11., 4h-Chart)

Short-Limit 1,11923 · Stop 1,12439 · Ziel 1,10003 → 52 Pips Risiko, 192 Pips Ziel, ≈ 3,7 R.
Erwartet A-B-C aufwärts in die Zone 1,1192–1,1218, dann Abverkauf.

- **Dafür:** Passt zu seinem DXY-Bild (DXY 101,8 ≈ EUR/USD ~1,119). Es ist ein Rücksetzer-Limit,
  der einzige Einstieg mit positivem Backtest. Privatanleger 85 % long (Gegenseite). Banken 1 : 3 short.
- **Dagegen:** Sonderreport-Regel 2 („Kein Euro-Short auf die Dollar-These“). Watchlist-Trigger des
  Macro-Reports (Schluss < 1,1100) nicht erfüllt. Profis am Euro-Short-Jahrestief → Eindeckungsgefahr.
  Ziel 1,1000 liegt unter fast allen Bankzielen (Danske 1,10, Nordea/KBC 1,1111). Der Stop liegt
  unter dem Hoch vom 04./05.11. (~1,126) und kann bei einem Retest abgefischt werden. DXY-Schluss
  < 101,5 (These kippt) entspricht etwa EUR/USD 1,123 – Stop und These-Kipp fallen zusammen,
  das ist sauber.
- **Bündelung:** Mit AUD/USD Short = zweimal Dollar long ins CPI. Mit EUR/CHF Short = zweimal Euro
  short → nach Report-Regel zusammen höchstens eine volle Größe.
- **Timing:** Die C-Welle in die Zone fällt vermutlich auf CPI Di; Füllung 14:15–15:30 verstößt
  gegen die Report-Sperre → Limit für dieses Fenster herausnehmen oder bewusst als Ausnahme werten.
- **Wertung:** Spielbar als Rang 2 (vor Gold), halbe Größe. EUR/CHF-Short dafür schließen oder bei
  0,910 sichern. Teilgewinn bei 1,1100 (Report-Trigger, Bankziele), Rest auf 1,1000.

| Symbol | Bedingung | Wert | Bedeutung |
|---|---|---|---|
| EURUSD | kreuzt aufwärts | 1,1192 | Short-Limit (Zone) |
| EURUSD | kreuzt aufwärts | 1,1244 | Stop |
| EURUSD | kreuzt abwärts | 1,1100 | Teilgewinn |
| EURUSD | kreuzt abwärts | 1,1000 | Ziel |

### Nachtrag: Dennis' USD/CAD Long (Live-Call 08.11., 8h-Chart)

Long-Limit 1,4009 · Stop 1,3951 · Ziel 1,4300 (Oktober-Hochs) → 58 Pips Risiko, 291 Pips Ziel,
≈ 5 R. Einstieg = Retest der Ausbruchszone 1,4010–1,4070 (altes Spannen-Hoch), Kurs Fr 1,4128.

- **Dafür:** Regel 1 des Sonderreports (Dollar-Stärke nur gegen Rohstoffwährungen). CAD mit den
  schwächsten Datenüberraschungen der G8, Arbeitslosigkeit 6,7 %, BoC-Dezember von 56 % auf 37 %
  gefallen. Fügt sich in Dennis' DXY-Pfad (C-Welle bringt den Retest, danach DXY Richtung 103).
  Rücksetzer-Limit statt Markt.
- **Dagegen:** Laut Report kein aktives Setup (CAD „neutral“, Rang 4). Hedgefonds schon stark short
  CAD (F-Gate-Konflikt). Ölrisiko: Brent über 105 (Hormus-Eskalation) stärkt den CAD – das ist der
  Report-Schalter. Das Limit liegt 119 Pips unter Schluss (~1,5–2 Tages-ATR); eine DXY-Delle auf 101,8
  bringt USD/CAD rechnerisch nur auf ~1,406 → Füllung unsicher.
- **Bündelung:** Mit AUD/USD Short und EUR/USD Short = **dreimal Dollar long ins CPI**. Kern ≤ 0,0 %
  trifft alle drei gleichzeitig. Dollar-Risiko insgesamt deckeln (Vorschlag: zusammen höchstens
  1,5 Einheiten).
- **Wertung:** Bestes Chance-Risiko-Verhältnis der Woche, aber ohne Report-Gates. Halbe Größe; wenn
  nur zwei Dollar-Longs, dann AUD/USD und USD/CAD (beide Rohstoffwährungen, Regel 1) vor EUR/USD
  (widerspricht Regel 2).

| Symbol | Bedingung | Wert | Bedeutung |
|---|---|---|---|
| USDCAD | kreuzt abwärts | 1,4070 | Zone erreicht |
| USDCAD | kreuzt abwärts | 1,4009 | Long-Limit |
| USDCAD | kreuzt abwärts | 1,3951 | Stop |
| USDCAD | kreuzt aufwärts | 1,4300 | Ziel |
| UKOIL | kreuzt aufwärts | 105 | Report-Schalter: CAD-Stärke, Long prüfen |

### Nachprüfung (nach Fr 13.11. ausfüllen)

| Punkt | Erwartet | Eingetreten | Urteil |
|---|---|---|---|
| CPI Kern Di 10.11. | 0,1–0,2 % | | |
| DXY-Pfad Dennis (Zone 101,55–101,82, dann > 102,6) | ja | | |
| AUD/USD Limit 0,6905 gefüllt / Ergebnis R | | | |
| Gold 4.030 erreicht, Schluss < 4.000? | | | |
| EUR/CHF 0,910 erreicht | | | |
| EUR/USD (Dennis) Limit 1,1192 gefüllt / Ergebnis R | | | |
| USD/CAD (Dennis) Limit 1,4009 gefüllt / Ergebnis R | | | |
