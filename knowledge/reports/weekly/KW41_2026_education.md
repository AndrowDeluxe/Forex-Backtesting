# Weekly Checkup - Education - KW41/2026

**Abgedeckte Woche: Mo 2026-10-05 bis So 2026-10-11.**

**Vorab festgehalten am Di 06.10. auf Nutzerwunsch.** Abschnitt 3, 4 und 4b
sind schon geschrieben. Der geplante Sonntagslauf ergaenzt die Abschnitte 1
und 2 sowie alles, was ab dem 07.10. dazukommt, und baut auf dieser Datei
auf.

## 3. Meine Main Erkenntnisse

### 3.1 Der Tresor hat eine ORB-Strategie entlarvt, die nach IS und OOS wie ein Treffer aussah

**Befund:** Die ORB-Strategie (SP500 + NASDAQ) wurde neu und ausschliesslich
auf IS 2016-2022 optimiert, mit 7 Punkten je Index. Danach wurde sie
eingefroren.

| | PF | Σ R |
|---|---|---|
| IS | 1,49 | |
| OOS 2023-09/2025 | 1,34 | +120 |
| Tresor 10/2025-09/2026 | 0,52 | −87 |

Auf einem 100k-Konto mit 1 % Risiko je Trade wurden im Tresor
**100.000 $ → 40.495 $** (MaxDD −62 %).

**Mechanismus / Warum:** Eine Strategie kann in zwei Zeitraeumen hintereinander
funktionieren und trotzdem auf einem Muster beruhen, das nur in einem
bestimmten Marktregime gilt. IS und OOS lagen beide im selben Regime (siehe
3.2). Erst der Tresor fiel in ein anderes.

**Wie es aufgefallen ist:** Durch die neue Overfitting-Sperre (3.3). Der
Tresor (die letzten 12 Monate) war technisch versiegelt und wurde erst nach
dem Einfrieren einmal geoeffnet. Ein Datenfehler wurde ausgeschlossen:
- Die Trades sind normal ueber die Monate verteilt.
- Jeder Verlust ist bei −1 R gedeckelt.
- Es gibt keine doppelten Tage.

**Lehre:** OOS bestanden heisst nicht handelbar. Erst ein einmal geoeffneter
Tresor zeigt, ob ein Edge regimeuebergreifend traegt. Auch die
Deflated-Sharpe-Pruefung war hier schon rot (Vertiefung unten).
[[orb-is-only-tresor-durchgefallen]]

### 3.2 Bruchpunkt gefunden: Nicht der ORB ist gekippt, sondern der Trendfilter

**Befund:** Gemessen wurde das Ø R je Trade an Tagen, an denen der EMA-Ribbon
(4H/1D/1W) neutral ist, gegen Tage mit klarem Trend.

| | Vorsprung „neutral“ |
|---|---|
| 2017-2025 | in 16 von 18 Index-Jahren positiv (bis +0,7 R; Ausnahmen NASDAQ 2019 −0,04, 2022 −0,01) |
| 2022 (Zinsschock) | SP500 +0,38 |
| Tresor | erstmals bei beiden Indizes negativ: SP500 −0,65, NASDAQ −0,41 |

Der ORB ohne Filter lag schon immer bei etwa 0 R. Der Bruch beginnt im
Quartal 2025Q4 bzw. 2026Q1.

**Mechanismus / Warum:**
- **Hypothese, nicht belegt:** Das Dealer-Gamma-Regime hat sich gedreht.
- **Positives Gamma:** Market Maker hedgen gegen die Bewegung, daraus
  entstehen Intraday-Umkehrungen. Ausbrueche an Trendtagen werden gefadet.
- **Negatives Gamma:** Sie hedgen mit der Bewegung, daraus entsteht Momentum.
- **Literatur:** Dim/Eraker/Vilkov; Adams et al. (10/2025); SpotGamma
  („neues Volatilitaetsregime“, 03/2026).
- **Umfeld 2026:**
  - 0DTE auf Rekord (~63 % des SPX-Optionsvolumens)
  - Iran-Krieg, Oel > 100 $
  - Q1 −9 % vom Hoch, Q2 das beste Quartal seit 2020
  - Fed-Erhoehung 09/2026

**Wie es aufgefallen ist:**
- **Quartalsweise Zerlegung:** Der Bruch ist abrupt, kein langsames Ausbluten.
- **Zehn Varianten je Index:** Nur der Ribbon-Filter dreht das Vorzeichen.
- **Gegenprobe Jahr fuer Jahr:** 2022 hielt trotz Makrostress, Makro allein
  erklaert es also nicht.
- **Die Eroeffnungsmechanik ist unveraendert** (Follow-through ~50 %,
  Range-Breite, Ausbrueche in beide Richtungen).
- **Querbefund Live-Version:** NASDAQ live hat keinen Ribbon und blieb
  positiv. SP500 live nutzt „neutral“ und lag bei ~0.

**Korrektur (06.10. abends, echte Gamma-Daten von SqueezeMetrics):** 2026
hatte nur an 4 % der Tage negatives SPX-Gamma, 2022 an 42 %, und 2022 hielt
der Filter. Die Gamma-Erklaerung ist damit unwahrscheinlich, die Ursache bleibt
offen. Eine Hypothese mit den echten Daten gegenzupruefen, statt sie mit der
Literatur nur plausibel zu machen, war hier entscheidend.

**Lehre:** Haengt ein Edge fast ganz an einem einzigen Regime-Filter, ist er
so stabil wie das Regime. Filter-Vorzeichen live weiter beobachten, statt sie
als Naturkonstante zu behandeln. [[orb-ribbon-filter-kippt-2026]]

### 3.3 Prozessluecke: Wir haben jahrelang „auf OOS“ optimiert, ohne es zu merken

**Befund:** Die Live-ORB-Konfiguration (15 auf den Daten gewaehlte
Entscheidungen, mehrere hundert Varianten) wurde ab Stage 2 direkt auf
OOS-Zahlen ausgewaehlt. Beispiele:
- Stage 3: „alle Zahlen OOS“
- Stage 4a: „OOS-only-Scan“
- Exit-Gitter: „IS und OOS positiv“

**Mechanismus / Warum:** Der Standardprozess nannte den OOS-Split nur in
Phase 6 als Pruefung. Fuer Phase 4/5 gab es keine Regel. Ein Skript, das IS
und OOS nebeneinander ausgibt, verfuehrt zur Auswahl auf OOS, und jeder Blick
macht OOS ein Stueck weit zu IS.

**Wie es aufgefallen ist:** Durch die Nutzerfrage „Haben wir mehr als 9
Parameter optimiert?“. Beim Zaehlen fiel auf, dass praktisch jede Stufe ihre
Wahl mit OOS-Zahlen begruendet hatte.

**Lehre / neue Regel (Overfitting-Sperre, Standardprozess seit 05.10.):**
1. Split IS / OOS / Tresor vor dem ersten Test registrieren.
2. Nur auf IS optimieren.
3. Jede Variante zaehlen (Trial-Register).
4. Einfrieren.
5. OOS und Tresor je genau einmal oeffnen.

Technisch ist das umgesetzt in `research_lock.py`. Dazu gilt als Hinweis ein
Richtwert von max. 9 optimierten Punkten je Index.
[[orb-auswahl-auf-oos-prozessluecke]] · [[overfitting-sperre]]

### 3.4 Kosten: Unser ORB-Edge ist groesser als der aus der Literatur, aber genau dieser Teil war gefittet

**Befund:** Eine unabhaengige Replikation (MQL5, 09/2026, 5 Index-CFDs, M1)
findet das Paper-ORB **brutto +0,05 bis +0,13 R, netto null**. Unsere Kosten
liegen gleichauf:

| Rundturn | Wir | Replikation |
|---|---|---|
| SP500 | 0,69 Pkt | 0,80 Pkt |
| NASDAQ | 1,93 Pkt | 2,50 Pkt |

Der Unterschied lag im Brutto-Edge, und den lieferten Filter und Exit-Regeln.

**Mechanismus / Warum:** Was gegenueber der Literatur „extra“ ist, wurde auf
unseren Daten gewaehlt. Genau dort sitzt das Overfitting-Risiko.

**Wie es aufgefallen ist:** Durch die Web-Recherche zu den Kriterien der
Mentor-Folie („Kosten eingerechnet“) und die Kosten-Gegenprobe mit 2×/3×
Kosten.

**Lehre:** Liegt der eigene Edge ein Vielfaches ueber dem, was unabhaengige
Replikationen finden, ist das zuerst ein Warnsignal und erst dann ein Erfolg.

### 3.5 Ein Regimewechsel laesst sich nicht aus der Bruchphase lernen

**Befund:** Die ORB-Strategie wurde neu auf genau dem Halbjahr des Bruchs
optimiert (IS 10/2025-03/2026, 9 Punkte, 46.656 Varianten je Index).

| | SP500 (3. Ausbruch) | NASDAQ (Ausbruch nach Fehlausbruch) |
|---|---|---|
| IS | PF 1,66 | PF 2,20 |
| OOS 04-06/2026 | −31 R | ±0 |
| Tresor | −8 R | −13 R |

Auf dem 100k-Konto waren das −27,6 % im OOS. Der 2./3. Ausbruch war ueber
2016-2026 in keinem Regime besser als der erste.

**Mechanismus / Warum:**
- **Zu wenig Daten fuer zu viele Freiheitsgrade:** ~60-120 Trades gegen
  zehntausende Varianten. Die Suche findet sicher ein Muster, aber fast
  sicher ein zufaelliges.
- **Der Bruch selbst ist kein stabiles Regime:** Das Umkehr-Muster (Fade,
  Fehlausbruch), das im Bruch-Halbjahr ins Plus drehte, hielt in Q2/Q3 2026
  nicht.

**Wie es aufgefallen ist:**
- **Schon im IS:** t-Werte von nur 2,3 bzw. 1,5 und eine Deflated Sharpe
  von ~0.
- **Am Checkpoint offen gesagt;** OOS wurde trotzdem bewusst geoeffnet.
- **Ergebnis:** Die eingefrorene Auswahl fiel durch.

**Lehre:** Nach einem Regimebruch keinen schnell nachoptimierten Ersatz-Edge
handeln. Stattdessen Risiko senken oder pausieren und Forward-Daten sammeln.
Ein IS unter einem Jahr mit vielen Stellschrauben ist ein Warnsignal.
[[regimewechsel-nicht-aus-bruchphase-lernbar]] · [[orb-neues-regime-2026]]

## 4. Neues Wissen diese Woche (Papers/Ideen)

- **Gao, Han, Li, Zhou (JFE 2018):**
  - **Aussage:** Die erste halbe Stunde sagt die letzte halbe Stunde voraus
    (SPY 1993-2013, R² 1,6 %), staerker an Volumen- und News-Tagen.
  - **Bei uns:** Die Korrelation erste gegen letzte 30 Min. lag 2016-2022 bei
    SP500 +0,09, 2023-24 bei ~0, im Tresor bei +0,11. Das ist kein stabiler
    Effekt.
  - **Status:** Hintergrund, geparkt.
- **Baltussen, Da, Lammers, Martens (JFE 2021):**
  - **Aussage:** Intraday-Momentum ueber 60 Futures, verursacht durch
    Gamma-Hedging.
  - **Bei uns:** staerkster Mechanismus-Kandidat fuer den ORB.
  - **Status:** nicht testbar ohne GEX-Historie, Ideen-Inbox.
- **Dim, Eraker, Vilkov (SSRN 2024/25):**
  - **Aussage:** Positives Market-Maker-Gamma staerkt Reversals, negatives
    Momentum.
  - **Bei uns:** Das passt zum Ribbon-Kipp (3.2).
  - **Status:** Hypothese.
- **Adams, Dim, Eraker, Fontaine, Ornthanalai, Vilkov (SSRN 10/2025):**
  - **Aussage:** 0DTE daempft die Index-Volatilitaet (−60 bis −90 bp
    annualisiert), mit staerkeren Order-Flow-Reversals und schwaecherem
    Momentum.
  - **Bei uns:** Hintergrund zum alten Regime.
- **Ladia (SSRN 07/2026):**
  - **Aussage:** Opening-Range-REVERSAL in Dow-Futures 2023-03/2026: Short
    an der Eroeffnung trifft zu 59,8 %, vorher 45 %. Das passt zeitlich zum
    0DTE-Wachstum (keine Kausalitaet belegt).
  - **Status:** Kandidat fuer die neue ORB-Runde.
- **Fetna (SSRN 09/2026):**
  - **Aussage:** Vorregistriert, 225 ORB-Zellen, 9 Futures, 2010-2026: keine
    einzige traegt nach Kosten. Die 5-Min-Range ist die schlechteste.
  - **Status:** Warnung, gelesen.
- **Zarattini, Barbon, Aziz (SSRN 2024):**
  - **Aussage:** ORB nur auf „Stocks in Play“ (abnormales
    Eroeffnungsvolumen): +0,38 R gegen −0,02 R.
  - **Status:** Kandidat fuer einen Volumen-Filter (Ideen-Inbox).
- **Markt 2025/26 (SpotGamma, Cboe, Quartalsberichte):**
  - 0DTE ~63 % des SPX-Optionsvolumens, Rekord 3,3 Mio. Kontrakte pro Tag
    (06/2026)
  - Half-Penny-Ticks seit 11/2025 (nur Aktien/ETFs)
  - Nasdaq-23h-Handel ab 12/2026 geplant
- **Ideen-Inbox neu:** ORB-Mechanismus-Test (Gap/Volumen), ORB-Gamma-Regime-Filter.

## 4b. Vertiefung: Deflated Sharpe Ratio

**Was es ist:** Testet man viele Varianten und nimmt die beste, sieht diese
auch dann gut aus, wenn keine einen echten Edge hat. Das liegt allein an
der Auswahl. Die Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014) rechnet
aus, welcher Sharpe beim Besten von N Versuchen schon durch Zufall zu
erwarten ist. Sie gibt die Wahrscheinlichkeit an, dass der gefundene Sharpe
darueber liegt. Ueblich ist eine Schwelle von 0,95.

**Beispiel mit unseren Zahlen:** Der IS-Gewinner fuer NASDAQ hatte t = 3,5.
Das sieht stark aus.
- Gegen 3.780 getestete Varianten ergibt die Deflated Sharpe 0,01.
- Selbst bei nur 15 unabhaengigen Versuchen waeren es 0,81, also unter 0,95.

Der Tresor hat das dann bestaetigt (PF 0,57).

**Warum es fuer unsere Bots zaehlt:** Jede Gitter-Suche erhoeht N. Ein t-Wert
von 3 ist nach 20.000 Versuchen nichts Besonderes. Deshalb fuehrt die
Overfitting-Sperre jetzt ein Trial-Register und verlangt die Deflated Sharpe
fuer jeden Gewinner.
