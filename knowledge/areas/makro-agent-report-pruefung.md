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
   Termine/Konsens/Ereignisse per Websuche. ATR für Kreuze nur aus echten Kreuzkursen, nie aus
   den Hochs/Tiefs der Dollar-Paare multipliziert (EUR/CHF so ~2,5× zu hoch, 08.11.). Ergebnis in drei Körbe: ✓ bestätigt · ≈ leichte
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

## Leitlinie: Gegenwährung wählen (Rohstoff- vs. Hafenvergleich)

> **Backtest 15.11.2026 (Punkt 2 eingeschränkt, Lock `gegenwaehrung_angst`, 6 Versuche,
> `scripts/research_gegenwaehrung_angst.py`):** Wochen 2004–05/2026, Zinswoche = US-2J ≥ +10 bp,
> Angst = VIX steigt in der Woche. Spread S = Dollar-Gewinn gegen CHF/JPY minus gegen AUD/NZD/CAD.
> - Zinswoche **ohne** Angst: S IS +1,14 % (83 % der Wochen > 0, n 41), OOS +0,31 % (63 %, n 38).
>   Der Hafen ist dann die bessere Gegenwährung. ✓
> - Zinswoche **mit** Angst: S IS +0,68 % (n 10), OOS 0,00 % (n 31). Rohstoffwährungen schlagen den
>   Hafen auch dann **nicht**. ✗ für den alten Punkt 2. Unterschied ohne/mit nicht signifikant (p 0,2).
> - Über alle Wochen erklärt die Angst derselben Woche die Wahl stark (t 9,4 IS / 5,2 OOS), aber die
>   Angst der **Vorwoche** sagt nichts über die Folgewoche (OOS p 0,20–0,90). Kein Sonntags-Signal.
> - Varianten VIX > 20 (Niveau) und S&P fällt: OOS nichts.
>
> **Neue Lesart:** Steigt der Dollar wegen der Zinsen, ist im Schnitt der zinslose Hafen (CHF, JPY bis
> zum Eingriff) das schwächste Glied. Die Rohstoffwährung ist nur dann besser, wenn in der Woche Angst
> **aufkommt**, und das muss der Agent als Ereignis-Risiko vorhersagen (z. B. Nvidia-Zahlen), nicht aus der
> Vorwoche ablesen. Punkt 2 unten gilt deshalb nur mit einem konkreten Angst-Auslöser in der Woche. Vom Nutzer bestätigt
> 15.11.; als Filter-Baustein abgelegt: [[filter-gegenwaehrung]].

Nutzer 08.11.: „Die Begründungen und die Logik dahinter gefällt mir sehr.“ Eine Währungs-These
(z. B. „Dollar stark“) ist noch kein Trade. Der Agent wählt die **Gegenwährung, bei der alle Kräfte
in dieselbe Richtung zeigen**, und begründet die Wahl ausdrücklich.

1. **Kräfte getrennt prüfen:** (a) Zinspfad-Differenz (wer erhöht mehr bis Herbst 2027),
   (b) Risikostimmung (Angst → Rohstoffwährungen AUD/NZD/CAD fallen, Häfen CHF/JPY steigen),
   (c) eigener Rohstoff der Gegenwährung, (d) Datenüberraschungen, (e) Positionierung.
   Ein Trade ist sauber, wenn (a)–(d) gleich zeigen und (e) nicht extrem auf unserer Seite ist.
2. **Dollar-Stärke aus Zinsen + Angst nur gegen Rohstoffwährungen**, nie gegen CHF/JPY – dort
   kämpft die Angst gegen den Trade. Beleg 08.11.: Wochenbewegung USD +2,4 % gegen AUD, +1,6 % NZD,
   +1,1 % CAD, aber −0,5 % gegen CHF.
3. **Je Rohstoffwährung den eigenen Schalter nennen:** CAD ↔ Brent (über 105 stärkt den CAD,
   Hormus), AUD ↔ Tech-/China-Risiko und Metalle, NZD ↔ Innenpolitik/Milch. Kippt der Rohstoff,
   kippt der Trade, auch wenn die Dollar-These hält.
   *Befund 15.11. (Gleichlauf, kein Signal):* Die Tech-Seite des AUD läuft seit 2025 über Asien
   (AUD~KOSPI +0,54), kaum noch über den Nasdaq (+0,21). Kupfer +0,34. [[danske-ai-investment-tracker]]
4. **Währung mit eigenem Problem nicht als Vehikel:** Der Euro hat Frankreich; ein Euro-Short ist
   eine eigene These (dann gegen CHF), keine Dollar-These.
5. **Bündeln statt zählen:** Trades mit demselben Treiber sind ein Risiko. Dollar-Longs zusammen
   deckeln (Vorschlag 1,5 Einheiten); Rangfolge: erfüllt Punkt 2 vor verletzt Punkt 4. Immer
   nennen, welches eine Ereignis alle gleichzeitig trifft (08.11.: Kern-CPI ≤ 0,0 %).
6. **Mentor-Trades durch denselben Filter:** Auch Dennis' Chart-Trades bekommen Dafür / Dagegen /
   Bündelung / Timing / Wertung – unabhängig davon, wer sie vorschlägt.

## Ausgabeformat (Report an den Nutzer)

1. Stimmen die Zahlen? (✓ / ≈ / ? mit Werten Report vs. eigene Daten)
2. Widersprüche (nummeriert, je ein Satz + Beleg)
3. Gewichtung (Stärke, Schwäche mit eigenen Zahlen, Szenario-Schätzung)
4. Trades nächste Woche (Tabelle, Rang 1 zuerst, inkl. „auslassen“)
5. Je Einzeltrade (auch Mentor-Trades): Kennzahlen (Einstieg/Stop/Ziel, Pips, R) · **Dafür** ·
   **Dagegen** · **Bündelung** · **Timing** (Termine, Sperrzeiten) · **Wertung** (Rang, Größe)
6. Alarmliste (falls Chart/Limits)
7. Quellen

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

### Nachprüfung (ausgefüllt im Weekly KW46, So 15.11.)

Kurse: Data Lake Dukascopy M15/M5 (AUDUSD, EURUSD, USDCAD, Gold, USDJPY), EUR/CHF und DXY über
yfinance (nicht im Lake). Füllung = erste Berührung des Limits ab So 08.11. 22:00 UTC; bei Stop und Ziel
in derselben Kerze zählt der Stop. Offene Trades zum Schluss Fr 13.11. bewertet.

| Punkt | Erwartet | Eingetreten | Urteil |
|---|---|---|---|
| CPI Kern Di 10.11. | 0,1–0,2 % | **0,3 %** (ungerundet 0,296 %, aus dem Kernindex 338,896 → 339,9); Gesamt 0,4 % (0,350 %) | ✗ heiß; BASE-Schätzung (55–60 %) lag falsch |
| DXY-Pfad Dennis (Zone 101,55–101,82, dann > 102,6) | ja | Di-Tief 101,49 (knapp unter der Zone, kein D1-Schluss < 101,50), ab Mi > 102,6, Fr Hoch 103,44 / Schluss 103,41 | ✓ voll eingetreten, Ziel ~103 erreicht |
| AUD/USD Limit 0,6905 gefüllt / Ergebnis R | gefüllt, Ziel 0,6670 | gefüllt Mo 09:45 UTC; Wochenhoch danach 0,69307 (Stop 0,6990 nie nah); Fr-Schluss 0,67693 | ✓ **offen +1,60 R** (halbe Größe), Ziel 99 Pips entfernt |
| Gold 4.030 erreicht, Schluss < 4.000? | Alarm, Long nur bei DXY < 102,6 | 4.030 Di erreicht (Tief 4.013); D1-Schluss Mi 3.978,5 → Long ungültig; Fr 3.883 (Woche −4,6 %) | Alarm ✓, Invalidierung ✓ (hätte geschützt); Long-Neigung ✗ |
| EUR/CHF 0,910 erreicht | Gewinne sichern | nein: Tief 0,9134 (Mo), danach bis 0,9267 (Fr) | Short lief gegen; „abwerten“ ✓ |
| EUR/USD (Dennis) Limit 1,1192 gefüllt / Ergebnis R | Rang 2, halbe Größe | gefüllt Mo 09:55 UTC, Stop 1,12439 Di 08:00 UTC (Hoch 1,12513) → **−1 R**; danach Fall bis 1,1020 | ✗ −1 R; die Prüfungs-Warnung „Stop unter dem Hoch 04./05.11., kann abgefischt werden“ ✓ |
| USD/CAD (Dennis) Limit 1,4009 gefüllt / Ergebnis R | Füllung unsicher | nicht gefüllt (Tief 1,40769 Mo), Fr 1,4266 | 0 R; Richtung ✓, „Füllung unsicher“ ✓ |

**Dafür/Dagegen im Rückblick:** Getragen hat die Leitlinie „Stärke aus Zinsen nur gegen
Rohstoffwährungen“ (AUD −1,35 %, CAD −1,0 %, Euro −1,0 % gegen USD) und Dennis' DXY-Pfad. *Korrigiert 15.11.:
hier stand zuerst „AUD −2,3 %“; −2,3 % war der Franken (Lake: USD/CHF 0,8199 → 0,8386). Damit war der
beste Dollar-Trade der Woche ausgerechnet der gegen einen Hafen, siehe Beispiel 3.* Falsch lag die
CPI-Schätzung und die eigene Gold-Neigung („Gold nur long“): Der Report-Satz „Gold fällt bei steigenden
Renditen“, den die Prüfung als Widerspruch Nr. 3 abgewertet hatte, traf diese Woche zu. Die
Invalidierung „Schluss < 4.000“ hätte den Schaden begrenzt.

---

## Beispiel 2: CPI-Preview Di 10.11.2026 (Sonderreport msg 7000 + Kanal 08./09.11.)

Quellen: SMT-Sonderreport „Die Zahl, die zwei Ziffern hat“ (Datenstand Mo 15:30), Dennis' Setups
So 22:20 (EU, GU, XAU, AU, DXY, UCAD, NU), Kanal Mo (Cluster-Warnung, GU gefüllt, USDCHF).
Charts 7006–7010 sind von einem anderen Autor (timothyespagnole8), nicht von Dennis. Msg 7003 =
Agrar-/El-Niño-Deep-Dive, ohne CPI-Bezug. Kurse: Yahoo 1h, Stand Di 00:00.

**Stand vor der Zahl:** DXY 101,68 (Zone 101,55–101,82 schon erreicht, die C-Welle kam vor dem CPI).
EUR/USD 1,1226: Dennis' Short 1,1192 gefüllt, 18 Pips vor dem Stop 1,1244. GBP/USD 1,3441: Short
1,3420 gefüllt, Stop 1,3482. AUD/USD 0,6924 (Report-Short 0,6862, Stop 0,6990). NZD/USD: Hoch 0,56386
> Stop 0,56365 → vermutlich ausgestoppt. USD/CAD-Limits (1,4060/1,4009) nicht gefüllt, Tief 1,4073.
Gold 4.147, also an der Report-Schwelle 4.150, Dennis' Limit 4.040 nicht gefüllt. Brent 92,3, Tief 90,6,
nahe am Kipppunkt „unter 90“.

**Widersprüche:** (1) Der Report sagt „kein Trade vor der Zahl“ und „EUR/USD nur bei heiß + Schluss
< 1,1100“, Dennis' Chart-Short 1,1192 ist aber schon offen. (2) Fed-Pricing 77 % ≥ 75 % = bezahlt, das
Risiko ist laut Report asymmetrisch gegen den Dollar. Trotzdem sind 4–5 Dollar-Long-Beine offen (EU, GU,
AU, NU, UCHF), genau das Cluster, vor dem Dennis Mo selbst warnt. (3) Das Gold-Chart-Limit 4.040 füllt nur
bei heißer Zahl, und genau dann erwartet der Report Gold < 4.000. (4) „Dollar fest“ (Teil 1) ist durch
den Montag überholt (DXY −0,6 %).

**Szenario-Schätzung (ohne Modell):** weich (Kern < 0,20) ~30 %, im Rahmen (0,20–0,24) ~50 %,
heiß (≥ 0,25) ~20 %.

| # | Trade | Bedingung | Umsetzung |
|---|---|---|---|
| 1 | Gold long | weich + D1-Schluss > 4.150 | Rücksetzer-Limit (~0,5 ATR D1), Stop unter 4.060, Zinskurven-Filter long |
| 2 | USD/JPY short | weich + Schluss < 157,40 | halbe Größe, Stop über dem Tageshoch nach 14:30 |
| 3 | AUD/USD short | heiß oder im Rahmen | Bestand halten, kein Nachkaufen; neu nur nach Spike in 0,6950–0,6970 |
| 4 | EUR/USD short | heiß + Schluss < 1,1100 | Report-Variante; den Chart-Short vor 14:15 halbieren/schließen |
| – | NZD, USD/CAD, GBP/USD, EUR/CHF | – | auslassen (ausgestoppt / nicht gefüllt / Cluster / Kreuz) |

### Nachprüfung CPI (ausgefüllt im Weekly KW46, So 15.11.)

| Punkt | Erwartet | Eingetreten | Urteil |
|---|---|---|---|
| Kern ungerundet | 0,20–0,24 (Basis) | 0,296 % | ✗ heiß (Schätzung „heiß“ ~20 %) |
| DXY-Schluss Di | 101,5–103 | 102,23 | ✓ |
| Dollar-Cluster (EU/GU/AU) bei weicher Zahl ausgestoppt? | ja | Zahl heiß → Bedingung nicht eingetreten. EU (Dennis) war schon **vor** der Zahl ausgestoppt (Di 08:00 UTC); AU lief ins Plus. GU nicht geprüft | n/a |
| Gold-Schluss > 4.150 / Long gefüllt / R | nur bei weich | Di-Schluss 4.038,7 → keine Auslösung | ✓ richtig nicht gehandelt |
| USD/JPY-Schluss < 157,40 | nur bei weich | Di-Schluss 158,71 → keine Auslösung (Fr 159,69) | ✓ richtig nicht gehandelt |
| Limit Gold long 4.045 (SL 3.970, TP 4.150/4.220) gefüllt / R | | gefüllt Di 13:30 UTC (Minute der CPI-Zahl), Stop Mi/Do um Mitternacht UTC → **−1 R** | ✗ |
| Limit AUD/USD short 0,6968 (SL 0,7030, TP 0,6900/0,6835) gefüllt / R | | nicht gefüllt (Hoch ab Di 0,6927) | 0 R |

Unklar: Die beiden Limit-Zeilen sind in Beispiel 2 weder als Agent- noch als Dennis-Trade
markiert. In der Bilanz unten stehen sie als eigene Spalte „Kanal-Limits“.

---

## Beispiel 3: KW 47/2026 (Reports vom 15.11.2026)

Quellen: Macro-Report 15.11. (msg 7071, 8 S.) + Sonderreport „G8 komplett“ (msg 7072, 16 S.),
Kurse = Schluss Fr 13.11. Kanal: Dennis' USD/CAD-Live-Long Fr (msg 7069), Pro-Call So 21:00
(Bilder 7074–7077 nur Zoom-Logos, Chart-Trades noch nicht im Kanal).

### Faktencheck

- ✓ Kurse vs. Dukascopy/Yahoo: EUR/USD 1,1023 (1,1022, Woche −1,04 %), AUD/USD 0,6776 (0,6769,
  −1,35 %, tiefster Stand seit 22.01.), GBP/USD 1,3214 (1,3209), USD/CAD 1,4266 (1,4266), USD/CHF
  0,8394 (0,8386, +2,27 %), USD/JPY 159,80 (159,69), Gold 3.886 (3.883, −4,6 %), DXY 103,41 (höchster
  Schluss seit 02.04.2025), Brent 95,84 / WTI 88,56 (je −2,5 %), S&P 7.562, Nasdaq Comp. 25.136, VIX 19,3.
  Kreuze passen zusammen (EUR/CHF 0,925, GBP/CHF 1,109, EUR/GBP 0,8342). EUR/USD-Schluss Mi 1,1090
  (Report-Einstieg 1,1092). Scorecard-Arithmetik stimmt (−0,25 R in voller Größe).
- ≈ US-2J „4,88 %“ ist der Donnerstags-Schluss, Fr 4,85 (TradingView) / 4,86 (FRED Do). 5-Tage-Sprung
  +38 bp = gleichauf mit Okt. 2024 (+38,5 bp), also „größter seit Nov. 2022“ nur knapp. USD/JPY über 160
  laut Dukascopy schon Do 16:30 UTC (Hoch 160,19), vorher zuletzt 02.09. ✓. Zinsabstand US–DE 2J 1,74 Pp.,
  Jahreshoch war 1,76 am 02.10. → „so weit wie nie in diesem Jahr“ knapp falsch.
  Gold „tiefster Stand seit Oktober 2025“ gilt für das Do-Tief 3.852, nicht für den Schluss
  (30.10.2026 schloss tiefer, 3.875).
- ? Zinsmarkt-Pricing, Bank-Calls, CFTC (Stichtag 03.11.), Privatanleger, NZD-Wochenwert.

### Widersprüche

1. **US-Einzelhandel Di:** Macro-Report „erwartet +0,3 %“, BASE „um +0,3 %“, ALT „unter +0,3 %“.
   Sonderreport „erwartet 0,0 bis +0,2 %“. Stimmt der Sonderreport, ist das ALT-Szenario der Konsens.
2. **Euro-Short gegen die eigene Regel:** Sonderreport 08.11., Regel 2 „Kein Euro-Short auf die
   Dollar-These“. Jetzt ist EUR/USD Short Trade 2 im Buch, als Dollar-Trade gezählt.
3. **„Dritter Dollar-Trade verworfen“ (USD/CAD), Dennis kauft USD/CAD aber Fr live** (1,4239, Stop 1,4225,
   msg 7069 „2 % running, BE ziehen“). Im Kanal sind es damit drei Dollar-Longs.
4. **BoE-Entscheid:** 08.11. „4,00 % einstimmig“, jetzt „+0,25 mit 8:1, Mann wollte 0,50“.
5. **EUR/USD-Stop über der These:** Die These kippt bei Schluss > 1,1100, der Stop liegt bei 1,1130.
   Sauber, wenn man den Schluss-Ausstieg ernst nimmt; sonst trägt man 30 Pips über das Kippen hinaus.
6. **Unsere eigene Leitlinie** („Dollar-Stärke nur gegen Rohstoffwährungen, nie gegen Häfen“): Diese
   Woche verlor der Franken am meisten (−2,3 %), mehr als AUD (−1,35 %). Der Report erklärt es selbst:
   Zinsen ohne Angst (VIX 25,6 → 19,3, S&P +2,5 %). Die Leitlinie gilt nur für „Zinsen **plus** Angst“;
   bei „Zinsen ohne Angst“ ist der zinslose Hafen das schwächste Glied. Vor jedem Dollar-Trade also
   zuerst prüfen, ob Angst überhaupt da ist.

### Gewichtung

Fakten sauber, Logik nachrechenbar. Stärke: Buch ist diszipliniert (Deckel eine Dollar-Größe, Stops
nachgezogen, nichts dazu). Schwäche: Die Einzelhandels-Erwartung ist uneinheitlich, und Kanal und Report
widersprechen sich beim dritten Dollar-Trade. Report-Scorecard −0,25 R seit 23.09. passt zu unserem
Befund (Richtung ≈ 0 R).
Gold-Zinskurven-Filter: bestätigt Goldilocks → long erlaubt; roh am 12.11. schon „Twist“ (2J 20 T. +4 bp,
10J −9 bp). Steigt die 10J noch ~10 bp, wird es Bear-Flattener = Inflation → Gold nur short. Makro-Veto
(Realzins und USD steigen, [[gold-confirmation-score]]) spricht gegen Gold-Long. Deckt sich mit
der Report-Sperre.
Schätzung (ohne Modell): BASE „Dollar hält“ ~50 %, ALT „Luft raus“ ~30 % (2J am Widerstand 4,95,
Positionierung voll, Crédit Agricole „überkauft“), TAIL „KI-Schock“ ~20 % (Nvidia ohne CEO, Halbleiter
Fr −3,4 %; Kippschalter Nasdaq Comp. unter 24.262 = Tief 05.11.).

### Trades KW 47

| # | Trade | Wertung | Umsetzung |
|---|---|---|---|
| 1 | AUD/USD Short (Bestand, Agent-Einstieg 0,6905) | Halten. Stärkster Banken-Konsens, RBA-Ende im Preis | Stop auf 0,6862 (= Report-Einstieg) sichert +0,5 R; Ziel 0,6670; nichts dazu. Risiken: Löhne Mi 01:30, Jobs Do 01:30, Shenzhen-Deal |
| 2 | GBP/CHF Long | Nur nach UK-CPI Mi > 3,8 % **und** D1-Schluss Mi > 1,1100. Ohne Dollar, gleicht den AUD-Short im TAIL aus (Franken steigt bei KI-Schock) | Danach Rücksetzer-Limit ~0,5 ATR (≈ 30 Pips) unter Schluss, halbe Größe, Stop unter 1,0950 (Wochentief). Kreuz → im Backtest schwach, darum klein |
| 3 | EUR/GBP Short | Abwerten: Euro-Short als eigene These, bündelt mit EUR/USD | Nur eines der zwei Pfund-Setups, GBP/CHF zuerst |
| 4 | EUR/USD Short | Auslassen für Neueinstieg: verletzt Regel 2 vom 08.11., zweiter Dollar-Trade | – |
| 5 | USD/CAD Long | Auslassen: dritter Dollar-Trade; CAD-CPI Mo 14:30, heiß = CAD fester | Dennis' Live-Trade gehört nicht ins Agent-Buch |
| 6 | USD/JPY, Gold | Gesperrt (Eingriffszone 160–164; Gold ohne Boden, Filter kippt) | Nur Alarme |
| 7 | AUD/NZD Short | Nach Wahlergebnis NZ 27.11. | – |
| – | Sperrzeiten | Mo 17:45–19:00, Di 14:15–15:30, Di 22:00–Mi 01:00, Mi 07:45–08:30 | + für AUD: Mi/Do 01:15–02:00 |

Fazit: AUD-Short halten und absichern, sonst nichts Neues vor Mittwoch; der einzige neue Kandidat ist
GBP/CHF Long nach der UK-Inflation.

**Nutzer-Bestand:** USD/JPY Short FK 0,3 / EK 0,1 Lot ab 159,84, Stop 162,00 (Stand KW46-Weekly) steht
gegen die Report-Sperre („Short: Zinsen und Trend dagegen“). Spricht dafür: Eingriffszone ab 160.
Entscheidung beim Nutzer.

### Alarme

| Symbol | Bedingung | Wert | Bedeutung |
|---|---|---|---|
| AUDUSD | kreuzt aufwärts | 0,6862 | Stop (nachgezogen) |
| AUDUSD | kreuzt abwärts | 0,6670 | Ziel |
| EURUSD | Schluss über (D1) | 1,1100 | Report-These kippt |
| TVC:US02Y | kreuzt abwärts | 4,70 | ALT greift, Dollar-These kippt |
| TVC:US02Y | kreuzt aufwärts | 4,95 | Widerstand gebrochen, Dollar-Trigger |
| TVC:DXY | kreuzt aufwärts | 104,0 | Report-Trigger nach oben |
| GBPCHF | Schluss über (D1), Mi | 1,1100 | Setup aktiv (nur mit UK-CPI > 3,8 %) |
| USDCHF | kreuzt aufwärts | 0,8400 | ING-Schlüsselmarke |
| USDJPY | kreuzt abwärts | 157,70 | Wochentief: Eingriff oder Drehung |
| NASDAQ:IXIC | kreuzt abwärts | 24.262 | TAIL „KI-Schock“ |
| XAUUSD | kreuzt abwärts | 3.850 | Wochentief gebrochen |

### Nachtrag: Dennis' Charts aus dem Pro-Call (15.11., 21:52–22:01, vom Nutzer geschickt)

Nur EUR/USD, Gold und US100. Werte aus den Bildern abgelesen; was nicht sichtbar ist, steht als „?“.

**EUR/USD Short (4h):** Verkaufszone 1,1104–1,1132, rote Linie ~1,1170 (Stop vermutlich), Zwischenmarken
1,1100 / ~1,1073. Kurs 1,1022. Ziel nicht eingezeichnet (Report: 1,1000 / 1,0950). Risiko von der Mitte
1,1118: ~52 Pips; bis 1,0950 ~168 Pips ≈ 3,2 R.
- **Dafür:** Rücksetzer-Limit in Trendrichtung, die einzige Einstiegsart mit positivem Backtest. Banken
  sehen 1,10 oder tiefer. Die Zone ist das alte Tief von Ende Oktober, jetzt als Widerstand.
- **Dagegen:** Die Zone liegt **über** der Report-Kippmarke (Schluss > 1,1100) und am Report-Stop 1,1130.
  Wo Dennis verkaufen will, ist der Report-Trade ausgestoppt. Hedgefonds am Extrem short → ein Anstieg in die
  Zone wäre genau die Eindeckung (ALT-Szenario, Report-Ziel dann 1,115, knapp unter dem Stop). Regel 2.
- **Bündelung:** Zweiter Dollar-Trade neben AUD/USD. Entweder dieser oder der Report-EUR-Short, nie beide.
- **Timing:** Füllung realistisch nur bei weichem Warsh (Mo 18:00) oder schwachem Einzelhandel (Di 14:30),
  beides Sperrzeiten.
- **Wertung:** Besser als der Report-Euro-Short (der Einstieg liegt höher, der Stop sitzt hinter der
  Kippmarke). Rang 2, halbe Größe, nur ohne Füllung in den Sperrzeiten.

**Gold Short (1h):** Positionswerkzeug mit Einstieg 4.015,7 (Unterkante der roten Zone 4.016–4.068), Stop über
der Zone (genauer Wert ?, mindestens 4.068), Ziel unter 3.810 (?). Fib-Ausdehnung der Erholung 3.942 / 3.967 /
3.995, Widerstand 3.933–3.945. Kurs 3.884, Einstieg also +132 $ (~2 Tages-ATR) entfernt.
- **Dafür:** Report sperrt Gold-Long („kein Boden“), Makro-Veto (Realzins + USD steigen), 4.013–4.030 war
  letzte Woche Unterstützung (Alarm 4.030, Dennis' Long-Zone) und ist jetzt Widerstand. Dennis lag diese Woche
  bei Gold richtig („10 von 10“).
- **Dagegen:** Der Gold-Zinskurven-Filter steht noch bestätigt auf Goldilocks = **nur long**. Ein Anstieg
  auf 4.016 bräuchte das ALT-Szenario (2J < 4,70); dann kippt die Short-These mit. Füllung unsicher.
- **Bündelung:** Gold short = Dollar long über den Zins → dritter Dollar-Treiber neben AUD und EUR.
- **Wertung:** Rang 3. Erst wenn der Filter auf Inflation kippt (roh schon Twist), sonst Viertelgröße.

**US100 Long (D1, Capital.com):** Einstieg 27.003, Stop 24.500, Ziel 32.000 → Risiko 2.503 Punkte (9 %),
Ziel 4.997 ≈ 2 R. Kurs 27.836. Einstieg = Retest der kleinen Box über dem Tief Anfang November (NDX 26.265).
- **Dafür:** BASE des Reports: Aktien steigen trotz Zinsen, VIX 19. Rücksetzer statt Markt.
- **Dagegen:** Das Limit füllt am ehesten nach schwachen Nvidia-Zahlen (Di 22:20), also im TAIL-Szenario
  „KI-Schock“. US-10J 5,15 %, 30J 5,47 % drücken die Bewertung. Ein Index-Long ist vor allem Marktrisiko
  (Memory „t > 2, aber nur Long-Beta“). Stop 9 % weit → sehr kleine Größe.
- **Bündelung:** Risk-on. Gleicht den AUD-Short teilweise aus (bei KI-Schock gewinnt AUD-Short, verliert US100).
- **Timing:** Limit erst **nach** den Nvidia-Zahlen legen (Sperre Di 22:00–Mi 01:00); fällt Nasdaq Comp. unter
  24.262, gilt TAIL und der Trade ist ungültig.
- **Wertung:** Kein Makro-Agent-Trade (kein FX), optional, kleine Größe, nicht vor Mittwoch.

| Symbol | Bedingung | Wert | Bedeutung |
|---|---|---|---|
| EURUSD | kreuzt aufwärts | 1,1104 | Dennis-Zone erreicht (Report-Kippmarke schon überschritten) |
| EURUSD | kreuzt aufwärts | 1,1170 | Dennis-Stop |
| XAUUSD | kreuzt aufwärts | 3.933 | Widerstand, erste Fib-Ausdehnung |
| XAUUSD | kreuzt aufwärts | 4.015 | Short-Limit Dennis |
| NAS100 | kreuzt abwärts | 27.003 | Long-Limit (nur nach Nvidia) |
| NAS100 | kreuzt abwärts | 24.500 | Stop |

**USD/JPY Short (4h, Dennis; Nutzer schon drin):** Dennis' Einstieg ~160,0 (Zone 159,8–160,15), Stop ~162,4
(Unterkante der zweiten Zone ab 162,4), Ziel unter 156,2 (genauer Wert ?) → ~240 Pips Risiko, ≥ 380 Pips Ziel
≈ 1,6 R. Freitags-Hoch 160,2 als Linie. Nutzer: FK 0,3 / EK 0,1 Lot ab 159,84, Stop 162,00.
- **Dafür:** Eingriffszone 160–164, Tokio warnt; im TAIL-Szenario (KI-Schock) steigt der Yen. Vermögensverwalter
  nahe dem Halbjahres-Hoch long Yen. ING: Yen bestes Chance-Risiko 2027.
- **Dagegen:** Report sperrt USD/JPY in beide Richtungen („Short: Zinsen und Trend dagegen“). Fed-Dezember
  96–100 % im Preis, Zinsabstand > 2,5 Pp. Backtest von heute: In Zinswochen ohne Angst verliert der Yen eher
  mehr. Privatanleger 65 % short → stützt USD/JPY hoch. Japan-BIP Mo 00:50 schwach = Zweifel an der BoJ.
  Der letzte Eingriff kam erst bei 164; der Nutzer-Stop 162,00 liegt **unter** Dennis' Stop und mitten in der
  Zone, die ein Anlauf auf den Eingriff durchläuft.
- **Bündelung:** Dollar **short**, also Gegengewicht zu AUD/USD Short (und EUR/USD, Gold short). Im TAIL gewinnen
  AUD-Short und USD/JPY-Short gemeinsam; in BASE trägt der AUD-Short, USD/JPY kostet.
- **Größe (geschätzt):** EK 0,1 Lot × 216 Pips ≈ 117 EUR ≈ 4–5 % des EK-Kontos (~2.500 EUR nach KW46);
  FK 0,3 Lot ≈ 405 USD ≈ 0,4 %. Auf EK also das Mehrfache eines üblichen 1-%-Risikos.
- **Wertung:** Ein Trade auf Eingriff oder KI-Schock (zusammen grob 20–25 %), nicht auf das Hauptszenario.
  Als Absicherung des Dollar-Buchs vertretbar, auf EK zu groß. Entscheidung beim Nutzer.

| Symbol | Bedingung | Wert | Bedeutung |
|---|---|---|---|
| USDJPY | kreuzt aufwärts | 160,20 | Freitags-Hoch gebrochen |
| USDJPY | kreuzt aufwärts | 161,50 | halbe Strecke zum Nutzer-Stop |
| USDJPY | kreuzt abwärts | 158,50 | erster Gewinn, Stop auf Einstieg prüfen |

### Nachprüfung (auszufüllen im Weekly KW47, So 22.11.)

| Punkt | Erwartet | Eingetreten | Urteil |
|---|---|---|---|
| Szenario | BASE ~50 / ALT ~30 / TAIL ~20 | | |
| US-Einzelhandel Di (Konsens laut Report +0,3 bzw. 0,0–0,2) | | | |
| AUD/USD Short: Stop 0,6862 / Ziel 0,6670 / Schluss Fr, R | halten | | |
| GBP/CHF: UK-CPI > 3,8 % + Schluss Mi > 1,1100? gefüllt? R | nur bedingt | | |
| EUR/USD (Report-Trade): 1,1000 Teilgewinn / Stop 1,1130 / R | ausgelassen | | |
| USD/CAD (Dennis live 1,4239): R | ausgelassen | | |
| Gold-Filter kippt auf Inflation? | wahrscheinlich | | |
| USD/JPY Eingriff? | Sperre | | |
| Dennis EUR/USD 1,1104–1,1132 gefüllt / Stop 1,1170 / R | Rang 2, halb | | |
| Dennis Gold Short 4.015,7 gefüllt / R | Rang 3, erst bei Filter-Kipp | | |
| Dennis US100 Long 27.003 gefüllt / Stop 24.500 / R | optional, nach Nvidia | | |
| USD/JPY Short (Dennis ~160 / Nutzer 159,84, Stop 162,00) / R | Hedge, auf EK zu groß | | |
| Gegenwährung: Woche mit Zinsanstieg ohne Angst → CHF/JPY schwächer als AUD/NZD/CAD? | ja | | |

---

## Laufende Bilanz (nur vorwärts, nie rückwirkend nachjustieren)

| Woche | Agent-Sicht: Trades / Treffer / Σ R | Dennis-Sicht: Trades / Treffer / Σ R | Kanal-Limits (Zuordnung offen) | Nutzer real (Handtrades auf FK/EK) |
|---|---|---|---|---|
| KW46 | 1 / 1 / **+1,60 R** (AUD/USD, offen, halbe Größe) | 2 Ideen, 1 gefüllt (EUR/USD; USD/CAD nicht) → 1 / 0 / **−1,0 R** | 1 / 0 / −1,0 R (Gold 4.045) | EUR/USD Short +631 USD; 3× Gold Long −145 USD / −124 EUR; USD/JPY Short offen |
| **Summe** | **1 / 100 % / +1,60 R** | **1 / 0 % / −1,0 R** | **1 / 0 % / −1,0 R** | – |

Nutzer-Spalte aus dem MT5-Abzug (`reason` 1 = Mobile, Magic 0): EUR/USD Short FK 0,56 Lot bei
1,12268 (Di, nach Dennis' Stop wieder eingestiegen), Teil 1,11388 und Ziel 1,10937. Gold Long FK
bei 4.029,7 (= Alarm 4.030) und 4.008, EK bei 4.006, alle ausgestoppt. USD/JPY Short FK 0,3 Lot und
EK 0,1 Lot bei 159,84 (Mi 23:23 Serverzeit), Stop 162,00, noch offen. Die Agent-Prüfung sagte zu
USD/JPY „erst nach Fed 09.12.“.
