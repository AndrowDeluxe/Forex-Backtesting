---
name: ipda-zyklus-eurusd
description: "Abgeschlossen, negativ: IPDA-Kalenderzyklus (Tag 8/14/20), EMA8/14-Cross-Periodizitaet und die daraus abgeleitete Pivot-Timing-Handelsregel auf EUR/USD Daily halten Permutationstests, OOS, Kosten-Sensitivitaet und Cross-Pair-Generalisierung (6 FX-Majors) nicht stand -- kein Edge gefunden."
metadata:
  node_type: memory
  type: project
  modified: 2026-08-25
---

# IPDA-Zyklus EUR/USD Daily

**Quelle**: "IPDA Playbook -- Das Uhrwerk des Geldes" (Dennis Schwer Consulting
PDF), vom User am 2026-08-24 im Chat geteilt. Grossteils unfalsifizierbare
"Insider-Erzaehlung" (Wal-Metaphern, fiktive Desk-Dialoge), aber mit ein paar
konkret testbaren Behauptungen. Siehe [[backtest-standard-process]] fuer den
8-Phasen-Rahmen, in dem dieses Projekt laeuft.

## Kandidaten (Phase 3, per AskUserQuestion mit dem User abgestimmt)

Vier unabhaengig testbare Hypothesen aus dem Dokument extrahiert:
1. **Tag 8/14/20 Zyklus-Reversal** (Kernthese, User-Prioritaet) -- getestet, siehe unten.
2. 8/14-EMA-Cross als Trend-Timing -- noch offen, vom User als Validierungs-Layer
   fuer die Kernthese gedacht ("danach anschauen, wie man die Zyklen oder Trades
   dadurch weiter validieren koennte"), macht aber ohne (1) als eigenstaendige
   Frage weniger Sinn -- ist dann nur noch ein generisches Dual-EMA-Crossover-
   System ohne IPDA-Bezug.
3. Monats-/Quartalsende USD-Staerke (Window Dressing/Basel III) -- noch offen.
4. 20-Tage-Hoch/Tief Liquidity-Sweep + Reversal -- noch offen.

## Kernthese: Tag 8/14 Zyklus-Reversal

**Capture** -- User-Vorgabe zum Zyklus-Anker (2026-08-24): "im Optimalfall am
01. des jeweiligen Kalendermonats, aber auf +/-10 Tage realisierbar" --
deshalb ankerlos getestet (User-Entscheidung nach AskUserQuestion), nicht auf
einen festen Tag fixiert. User kuendigte einen TradingView-Auszug als
zusaetzliches Belegmaterial an (noch nicht erhalten).

**Distill** -- `scripts/research_ipda_cycle_daily_eurusd.py`: ZigZag-Pivots
(ATR(14)-skalierte Schwelle) auf EUR/USD Daily (Dukascopy, 2003-2026, IS =
aeltere 70% = 2003-05 bis 2019-06, 5238 Handelstage). Fuer jede Kombination
aus Zyklus-Anker (Monatsanfang +/-10 Handelstage, 21 Offsets) und Zykluslaenge
(18-22 Handelstage) wird gemessen, wie stark sich Pivots im Toleranzfenster
(+/-1 Tag) um den auf die Zykluslaenge skalierten Tag 8 bzw. Tag 14 haeufen
(Anreicherung relativ zur Gleichverteilungs-Erwartung). Permutationstest
(zirkulaerer Shift der Pivot-Serie, n=2000, analog zur "rotation"-Methode in
`asian_range_breakout/randomization.py`) mit Max-Statistik-Korrektur ueber
alle 105 getesteten Kombinationen je Zieltag.

Robustheits-Sweep ueber 5 ZigZag-Schwellenwerte (ATR-Multiplikator 1.0-3.0,
medianer Pivot-Abstand dadurch 6-26 Handelstage):

| ATR-Mult. | Median-Abstand | p (Tag 8, korrigiert) | p (Tag 14, korrigiert) |
|---|---|---|---|
| 1.0 | 6 Tage | 0.682 | 0.710 |
| 1.5 | 10 Tage | 0.127 | 0.069 |
| 2.0 | 13 Tage | 0.537 | 0.548 |
| 2.5 | 20 Tage (~Zyklus-Hypothese) | 0.748 | 0.984 |
| 3.0 | 26 Tage | 0.977 | 0.980 |

Kein p-Wert unterschreitet 0.05. Gerade bei ATR-Mult. 2.5, wo der mediane
Pivot-Abstand die 20-Tage-Zyklus-Hypothese fast exakt trifft, ist der Befund
am eindeutigsten reines Rauschen (p=0.748/0.984). Der beste Treffer (ATR 1.5,
Tag 14, p=0.069) haelt dem Parameter-Sweep nicht stand -- klassisches Muster
fuer einen Zufallstreffer statt echtem Signal (ein echter Effekt bliebe ueber
einen plausiblen ZigZag-Schwellenwertbereich einigermassen signifikant). Die
"besten" Anker-Offsets lagen ausserdem fast immer am Rand des getesteten
+/-10-Tage-Fensters (-10, -7, -6), nicht nahe Monatsanfang -- passt nicht zur
Dokument-Intuition, sondern zum erwarteten Verhalten eines Suchraum-Randmaximums
unter reinem Rauschen.

**Express** -- **Kernthese widerlegt** (Phase-3-Screening, EUR/USD Daily, IS
2003-2019): keine statistisch robuste Haeufung von Trendwechseln um Tag 8/14
eines ~20-Handelstage-Zyklus, unabhaengig vom getesteten Anker (Monatsanfang
+/-10 Tage) und unabhaengig von der Pivot-Definition (ZigZag-Schwelle 1.0-3.0x
ATR). Kein Phase-4-Vollausbau (Backend-Package, Entry/Exit, vollstaendiger
Backtest) auf dieser Basis -- waere Rauschen in ein plausibel aussehendes
Setup zurueckgerechnet, genau das Muster aus [[backtest-standard-process]],
das die Checkliste verhindern soll.

Noch NICHT final, weil: (a) die anderen 3 Kandidaten (EMA-Cross, Monats-/
Quartalsende, Liquidity-Sweep) sind eigenstaendige Hypothesen und noch nicht
getestet -- der Fehlschlag der Kernthese schliesst sie nicht automatisch aus;
(b) der angekuendigte TradingView-Auszug des Users koennte eine andere
Definition von "Wendepunkt/Shift-Candle" nahelegen als die hier verwendeten
ZigZag-Pivots; (c) nur EIN Toleranzfenster (+/-1 Tag) getestet, kein Sweep
davon.

## Nachtrag 2026-08-25: TradingView-Chart des Users + praezisierte These

**Capture** -- User teilte zwei TradingView-Screenshots eines eigenen "IPDA"-
Indikators (EUR/USD Daily, OANDA) mit Boxen variabler Laenge (7t-23t) zwischen
Preis-Extrempunkten, plus einem festen "IPDA Nullpunkt" (01. Apr '26) und der
Beobachtung "das sind die Zyklen, die sehr oft mit einem High oder Low enden"
sowie "2025 lief das ganze sehr sauber ueber die einzelnen Quartale". Auf
Nachfrage bestaetigt: die Boxen werden RUECKWAERTS zwischen bereits erkannten
Pivots gezogen (nicht vorwaerts von einem festen Anker projiziert) -- macht
"Zyklus endet in Hoch/Tief" tautologisch (Boxgrenzen SIND per Konstruktion
die Pivots), liefert also keine neue Evidenz ueber den obigen Befund hinaus.

User praezisierte danach die eigentliche These: "Es geht um 20-Tage-Zyklen
+/-2 Tage zum lokalen High oder Low" -- eine andere, NICHT-zirkulaere
Formulierung: haeufen sich die ABSTAENDE zwischen aufeinanderfolgenden
ZigZag-Pivots selbst bei ~20+/-2 Handelstagen, unabhaengig von jedem
Kalender-Anker?

**Distill** -- Fuer jeden der 5 bereits getesteten ATR-Schwellenwerte (Median-
Abstand 7.7-33.5 Tage): (1) Anteil der Pivot-Abstaende im Fenster [18,22]t
gegen eine Zufalls-Platzierungs-Null (n_pivots Punkte gleichverteilt zufaellig
unter n_days platziert, n=2000); (2) Variationskoeffizient (CV=Std/Mittel)
der echten Abstaende gegen denselben Zufalls-Null, als Test auf generelle
Regelmaessigkeit (nicht spezifisch bei 20).

| ATR-Mult. | Oe-Abstand | CV | Anteil in [18,22]t | p(Haeufung bei 18-22) | p(regelmaessiger als Zufall) |
|---|---|---|---|---|---|
| 1.0 | 7.7t | 0.794 | 4.6% | 0.602 | 0.0000 |
| 1.5 | 12.6t | 0.785 | 8.2% | 0.561 | 0.0000 |
| 2.0 | 18.0t | 0.793 | 9.3% | 0.564 | 0.0000 |
| 2.5 | 25.3t | 0.802 | 10.2% | 0.327 | 0.0005 |
| 3.0 | 33.5t | 0.750 | 10.3% | 0.242 | 0.0000 |

**Express** -- Zwei getrennte Befunde, die auseinanderfallen:
1. **Keine spezielle Haeufung genau bei 18-22 Tagen** (p=0.24-0.60 durchweg
   nicht signifikant) -- die "20" ist nicht privilegiert.
2. **Aber echte, robuste Regelmaessigkeit**: bei JEDEM der 5 Schwellenwerte
   sind die Pivot-Abstaende hochsignifikant regelmaessiger (niedrigerer CV)
   als eine zufaellige Punktplatzierung derselben Anzahl (p<0.001 durchweg,
   robust ueber den ganzen Parameterbereich -- anders als der Tag-8/14-Befund
   oben, der beim Parameter-Sweep zusammenbrach). Die "natuerliche"
   Zyklusdauer skaliert aber mit der Pivot-Sensitivitaet (7.7 bis 33.5 Tage)
   statt fix bei 20 zu liegen -- ATR x2.0 kommt der 20-Tage-Vorgabe des Users
   mit 18.0t am naechsten, ist aber kein privilegierter Wert gegenueber den
   anderen Schwellen.

**Einordnung**: Die urspruengliche IPDA-These (Kalender-verankerter 20-Tage-
Zyklus mit Wendepunkten an FESTEN Tagen 8/14) bleibt widerlegt. Aber die
verwandte, schwaechere These "Wendepunkte kommen in ungewoehnlich regelmaessigen
Abstaenden, nicht zufaellig verteilt" ist ein neuer, robuster, nicht-
zirkulaerer Befund -- moeglicher Ansatzpunkt fuer ein Edge, das auf
Zeit-seit-letztem-Pivot statt auf einem Kalenderanker basiert.

## Nachtrag 2026-08-25 (Teil 2): EMA8/14-Cross-Periodizitaet + Phase-4-Handelsregel

**Capture** -- Dokument nochmal gezielt nach praeziseren Regeln durchsucht
(User-Anfrage). Fund: das Dokument definiert den "Shift Candle"-Wendepunkt
eigentlich ueber den 8er-/14er-EMA-Cross, nicht ueber einen generischen
Preis-Pivot ("Der Cross ist die sichtbare Folge des Signals"; explizites
Scoring-System mit IPDA-Zeitfenster/Preis-POI/Volumen/MA-Cross als additive
Kriterien). Passt zum "MA Cross"-Layer im User-Indikator-Screenshot.

**Distill** -- Zwei unabhaengige Tests:

1. **EMA8/14-Cross-Periodizitaet** (`scripts/research_ipda_ema_cross_...`,
   inline getestet): Abstand zwischen aufeinanderfolgenden EMA8/EMA14-Cross-
   Ereignissen im IS. CV=0.984 (praktisch Zufallsniveau, Referenz-Null=0.967),
   p(regelmaessiger als Zufall)=0.644 -- NICHT signifikant, anders als die
   ZigZag-Pivots. Ursache vermutlich Whipsaw: 21% aller Cross-Abstaende sind
   <5 Tage (Rauschen in Seitwaertsphasen), waehrend ZigZag-Pivots per
   Definition kleine Bewegungen herausfiltern. Schwaecht die EMA-Cross-als-
   Bestaetigung-These des Dokuments zusaetzlich.

2. **Timing-Handelsregel auf ZigZag-Pivot-Bestaetigung** (der einzige bisher
   robuste Befund) -- `scripts/research_ipda_pivot_timing_eurusd.py`: Fade-
   Entry gegen die Bewegung seit dem letzten BESTAETIGTEN Pivot (ATR x2.0),
   sobald 18-22 Handelstage seit der Bestaetigung vergangen sind (User-
   Vorgabe 20+/-2). Kritisch: Entry nutzt `confirm_idx` (Bestaetigungs-Bar),
   nie die tatsaechliche Extrem-Position -- sonst Look-ahead-Bias, da ein
   Pivot erst erkennbar ist, nachdem der Preis sich bereits wieder entfernt
   hat. SL jenseits des laufenden Extrems seit dem Pivot (+ATR-Puffer), TP
   als R-Vielfaches, 9-Zellen-Grid (SL-Puffer x TP-R) im IS, bester
   IS-Kandidat (SL=0.5xATR, TP=3.0R, n=106) einmal in OOS bestaetigt --
   PLUS Vergleichs-Baseline ohne Zeitfenster-Filter (sofortiger Entry bei
   jeder Pivot-Bestaetigung) zur Isolierung des Timing-Werts.

**Express** -- Gemischtes, aber am Ende NICHT ausreichendes Ergebnis:
- IS (getimt, bester Kandidat): n=106, TotalR=+20.04, Ø R=+0.189, PF=1.32.
- OOS (dieselbe Konfiguration, kein Retuning): n=47, TotalR=+3.23, Ø R=+0.069,
  PF=1.11 -- schwaecher als IS (erwartbarer Rueckgang), aber immerhin positiv.
- OOS-Vergleich OHNE Timing-Filter (identische SL/TP): n=116, TotalR=-28.00,
  Ø R=-0.241, PF=0.70 -- klar negativ. Das Timing-Fenster traegt also
  offenbar etwas zur Trade-Auswahl bei, nicht nur "nach jedem Pivot faden".
- **Kosten-Sensitivitaet** (OOS): mittlere Stop-Distanz 101 Pips. Bei 5 Pips
  Spread+Slippage/Trade sinkt TotalR auf +0.12R (praktisch Breakeven), bei
  8 Pips negativ (-1.74R) -- der Edge ist hauchduenn gegenueber realistischen
  Handelskosten.
- **Block-Bootstrap-Signifikanztest** (block_size=5 Trades, n=2000, auf der
  Trade-R-Sequenz, analog zur Block-Bootstrap-Methodik in
  `ou_paper_backtest/monte_carlo.py`, hier auf Trade- statt Tages-Ebene
  angewendet, siehe Script-Docstring fuer die Begruendung dieser Abweichung):
  90%-CI fuer OOS mean R = **[-0.30, +0.46]**, umspannt komfortabel die Null.
  **p(mean R <= 0) = 0.395** -- statistisch nicht von Zufall unterscheidbar.
  Selbst der IS-Bestwert (profitiert von "bester aus 9 Kombinationen")
  erreicht nur p=0.089, verfehlt die 0.05-Schwelle.

**Gesamtfazit (vorlaeufig, Stand vor dem Generalisierungstest unten)**: Kein
Teilkandidat haelt allen Pruefungen stand. Kalender-Zyklus widerlegt (robust),
EMA-Cross-Periodizitaet widerlegt (robust), Pivot-Abstands-Regelmaessigkeit
bestaetigt (sehr robust, p<0.001 ueber 5 Parameter) aber nicht in eine
statistisch signifikante, kostenrobuste Handelsregel uebersetzbar (n zu klein,
p=0.395 OOS, Kosten-Breakeven bei nur ~5 Pips).

## Nachtrag 2026-08-25 (Teil 3): Generalisierungstest ueber 5 weitere FX-Majors

User-Entscheidung nach dem duennen OOS-Ergebnis oben: "mehr statistische Power
holen (andere Paare/Timeframes/laengere Historie)" statt das Thema
zurueckzustellen. Wichtig fuer die Methodik: um NICHT einfach ein neues
Mehrfachvergleichs-Problem zu erzeugen (jedes Paar einzeln testen und das
guenstigste herauspicken), wurde die EXAKT GLEICHE, auf EUR/USD-IS fixierte
Regel (ATR x2.0 Pivot-Schwelle, Fenster 18-22 Tage, SL=0.5xATR, TP=3.0R) OHNE
jede Neukalibrierung auf 5 weiteren FX-Majors (GBP/USD, USD/JPY, USD/CHF,
AUD/USD, USD/CAD, volle Historie 2003-2026 -- fuer diese Paare komplett
unberuehrt von jeglichem Tuning) angewendet und mit dem EUR/USD-OOS-Ergebnis
gepoolt.

**Distill** -- Pro Paar (fixe Regel, keine Anpassung):

| Paar | Zeitraum | n | TotalR | mean R | WinRate | PF |
|---|---|---|---|---|---|---|
| EUR/USD | OOS 2019-2026 | 47 | +3.23 | +0.069 | 38.3% | 1.11 |
| GBP/USD | voll 2003-2026 | 142 | -3.15 | -0.022 | 28.9% | 0.97 |
| USD/JPY | voll 2003-2026 | 138 | -6.44 | -0.047 | 31.2% | 0.93 |
| USD/CHF | voll 2003-2026 | 148 | +12.40 | +0.084 | 34.5% | 1.13 |
| AUD/USD | voll 2003-2026 | 147 | -1.69 | -0.012 | 36.1% | 0.98 |
| USD/CAD | voll 2003-2026 | 146 | +6.59 | +0.045 | 34.2% | 1.07 |
| **Gepoolt (6 Paare)** | -- | **768** | **+10.94** | **+0.0143** | 33.3% | **1.02** |

Block-Bootstrap (block_size=5, n=2000) auf der gepoolten Sequenz: 90%-CI fuer
mean R = **[-0.076, +0.101]**, p(mean R<=0) = **0.4145**.

**Express** -- Eindeutig negativ, und methodisch aussagekraeftiger als der
EUR/USD-Einzelbefund: 3 von 6 Paaren positiv, 3 negativ -- kein konsistentes
Vorzeichen, wie es ein echter Effekt zeigen wuerde. PF gepoolt = 1.02
(praktisch Breakeven, VOR Kosten). Entscheidend: das 90%-CI wurde mit der
16-fach groesseren Stichprobe (768 vs. 47 Trades) enger, aber blieb um die
Null zentriert (p praktisch unveraendert, 0.4145 vs. 0.395) -- das ist das
Muster, das einen echten (nur unterversorgten) Effekt von einem reinen
Zufallsbefund unterscheidet: mehr Daten haetten einen echten Effekt
praeziser SICHTBAR gemacht, nicht ihn weiter zur Null hin verduennt. Der
fruehere EUR/USD-OOS-Treffer (PF=1.11) war rueckblickend hoechstwahrscheinlich
ein guenstiger Zufallsausschlag der kleinen Stichprobe. Caveat zur
Interpretation: FX-Majors sind untereinander korreliert (gemeinsamer
USD-Faktor), die 6 Paar-Ergebnisse sind also nicht vollstaendig unabhaengige
Beobachtungen -- die effektive Staerke der Verengung ist etwas schwaecher als
die nominale 6x-Stichprobenvergroesserung suggeriert, aendert aber nichts am
klaren Gesamtbild.

## Gesamtfazit (final, 2026-08-25)

Alle vier aus dem Dokument extrahierten Teilthesen (Kalender-Zyklus,
EMA8/14-Cross-Periodizitaet, Pivot-Timing-Handelsregel, deren Generalisierung
ueber 6 FX-Majors) wurden gepruefft und halten der vollstaendigen Pruefung
(Permutationstests, Parameter-Robustheit, Out-of-Sample, Kosten-Sensitivitaet,
Block-Bootstrap-Signifikanz, Cross-Pair-Generalisierung) nicht stand.
Einziger ueberlebender Strukturbefund (Pivot-Abstaende sind regelmaessiger
als Zufall, p<0.001) bleibt strukturell interessant, liess sich aber trotz
sauberer Operationalisierung nicht in Geld uebersetzen.

## Nachtrag 2026-08-25 (Teil 4): Kandidat C -- Monats-/Quartalsende-USD-Staerke

**Capture** -- `scripts/research_ipda_quarter_end_usd_strength_eurusd.py`,
auf User-Anfrage ausgefuehrt. These aus dem Dokument ("Window Dressing",
Basel-III-Bilanzoptimierung, Repo-Markt-Verknappung): EUR/USD faellt (USD
staerker) in den letzten 3-5 Handelstagen vor Monats-/Quartalsende.

**Distill** -- Kumulative Rendite ueber die letzten K={3,4,5} Handelstage vor
jedem Monats- bzw. Quartalsende, Permutationstest (zirkulaerer Shift, n=2000)
gegen ein zufaelliges K-Tage-Fenster.

| Test | n | Ø-Rendite | p (2-seitig) | p (1-seitig, EUR/USD faellt) |
|---|---|---|---|---|
| Monatsende, alle 12, K=3/4/5 (IS) | 194 | +0 bis +4 Pips | 0.62-1.00 | 0.51-0.71 |
| Quartalsende, K=3/4/5 (IS) | 65 | +10 bis +15 Pips | 0.26-0.52 | 0.74-0.87 |
| Quartalsende, K=5 (OOS) | 29 | +7.9 Pips | 0.58 | 0.69 |

Zum Vergleich die urspruengliche User-Beobachtung (2025, K=5, die den Anstoss
fuer diesen Kandidaten gab): 2025-03-31 +26.4, 2025-06-30 **+148.9**,
2025-09-30 -6.7, 2025-12-31 -32.1 Pips -- kein einheitliches Muster, sondern
von einem einzelnen Ausreisser (Q2, vermutlich ein unabhaengiges Makro-Event)
dominiert.

**Express** -- Klar negativ, und zusaetzlich in die dem Dokument
entgegengesetzte Richtung: nirgends signifikant (alle p>0.25), und wo ueberhaupt
eine Tendenz erkennbar ist, steigt EUR/USD tendenziell zum Quartalsende
(USD SCHWAECHER, nicht staerker wie behauptet). Die Einzelfall-Beobachtung,
die den Kandidaten ausgeloest hat, haelt der Nachrechnung nicht stand --
bestaetigt die Small-Sample-Warnung von Anfang des Nachtrags.

## Nachtrag 2026-08-25 (Teil 5): Kandidat D -- 20-Tage-Hoch/Tief-Liquidity-Sweep

**Capture** -- `scripts/research_ipda_liquidity_sweep_eurusd.py`. These
(Dokument-Abschnitt "Liquidity Pools"/"Stop-Loss-Hunting"): Kurs durchbricht
ein rollierendes 20-Tage-Hoch/Tief NUR INTRABAR (Wick), schliesst aber
zurueck innerhalb der alten Range ("Sweep"/Fake-Out) -- danach Reversal.
Gegenprobe: sauberer Breakout (durchbricht UND schliesst dort) sollte laut
Dokument-Logik eher fortsetzen (Momentum) statt umkehren.

**Distill** -- 4 Ereignistypen (sweep_high/sweep_low/breakout_high/
breakout_low) x 4 Vorwaerts-Horizonte (1/3/5/10 Tage) x IS/OOS = 32 Tests,
Permutationstest (zirkulaerer Shift, n=2000) je Zelle.

**Express** -- Klar negativ, mit einem lehrbuchhaften Multiple-Testing-
Beispiel: von 32 Zellen ist genau 1 nominell signifikant (OOS sweep_low,
H=5d, p=0.029, +19.9 Pips -- passend zur erwarteten Richtung). Bei 32 Tests
und alpha=0.05 sind im Erwartungswert ~1.6 solche Treffer allein durch
Zufall zu erwarten -- 1 Treffer ist also kein Ausreisser nach oben. Entscheidend:
DIESELBE Zelle in IS (deutlich groessere Stichprobe, mehr Power) zeigt
praktisch nichts (mean=-0.5 Pips, p=0.95) -- kein Vorzeichen des Effekts in
den grossen, aelteren Daten, nur ein Ausschlag in der kleineren OOS-Stichprobe.
Ein echter Effekt haette sich zuerst/deutlicher in IS zeigen sollen, nicht
umgekehrt. Zusaetzlich zeigt der eigentlich entscheidende Kontrast (Sweep
sollte umkehren, sauberer Breakout sollte fortsetzen) sich nicht: sweep_high
und breakout_high verhalten sich in IS fast identisch (beide leicht negativ,
H5/H10 um -9 bis -10 Pips, keins signifikant) statt sich zu unterscheiden --
eher generisches, nicht-signifikantes Rauschen als ein sweep-spezifischer
Effekt.

## Gesamtfazit (final, 2026-08-25)

**Status: abgeschlossen, negativ -- kein weiterer Aufwand auf dieser Basis
geplant.** Alle vier aus dem Dokument extrahierten Kandidaten getestet
(Kalender-Zyklus, EMA-Cross-Periodizitaet, Pivot-Timing-Handelsregel inkl.
Cross-Pair-Generalisierung ueber 6 FX-Majors, Monats-/Quartalsende-USD-
Staerke, 20-Tage-Liquidity-Sweep) -- keiner haelt einer sauberen Pruefung
(Permutationstests, Parameter-Robustheit, Out-of-Sample, Kosten-Sensitivitaet,
Block-Bootstrap-Signifikanz, Cross-Pair-Generalisierung, Multiple-Testing-
Einordnung) stand. Ein Kandidat (Quartalsende) zeigte sogar das dem Dokument
entgegengesetzte Vorzeichen. Einziger ueberlebender Strukturbefund ueber die
gesamte Untersuchung (Pivot-Abstaende sind regelmaessiger als Zufall, p<0.001,
Teil 2 oben) bleibt strukturell interessant, liess sich aber nicht in eine
profitable, statistisch abgesicherte Handelsregel uebersetzen. Vier
lauffaehige Scripts unter `scripts/research_ipda_*.py` fuer den Fall, dass
spaeter neues Beweismaterial (z.B. eine praezisere Definition aus dem
Original-Indikator des Users) eine erneute Pruefung rechtfertigt.
