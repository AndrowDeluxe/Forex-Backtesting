# Weekly Checkup - Education - KW47/2026

**Abgedeckte Woche: Mo 2026-11-16 bis So 2026-11-22.** Quellen: `git log` der Woche, `knowledge/CHANGELOG.md`,
neue/geänderte PARA-Notizen, Memory-Einträge vom 16.–21.11.

## 1. Was stand die Woche an / Hauptfokus

Die Woche hatte drei Schwerpunkte. Sie endete mit einer Richtungsentscheidung.

- **Live-Abgleich und ORB NASDAQ (Mi 18.11.).** Der Soll/Ist-Bericht war seit September für ORB blind. Das ist
  repariert, und die Fehlerklasse steht jetzt in `CLAUDE.md`. Gleichzeitig kam die Analyse, warum NASDAQ-ORB live
  so anders handelt als im Backtest. Die Regel füllt fast nur in der ersten Minute. Daraus folgte eine Live-Änderung:
  Market-Einstieg statt `breakout_passed`. Den Kandidaten „Kerzen-SL“ hat der Tresor verworfen.
- **Dachprojekt / Rohstoffe und Gold-Makro (Mi 18.11.).** Rohstoff-Screener 1.2 ist im Forward-Betrieb. Der
  Edelmetall-Backtest auf 4–26 Wochen fand **keinen Edge** (0 von 285 Varianten). Die Gold-Richtungs-Komposition
  schlägt „immer long“ nicht.
- **Signal-Hub Stufe 1 (Do 19.11.) = neue Hauptrichtung.** Nach den widerlegten mechanischen Edges (Daily-C2,
  H4 in vier Runden) findet die Maschine Setups, du bestätigst per Telegram-Knopf. Jede Entscheidung wird
  paper-simuliert. Der erste echte Alarm (Gold Long 20.11.) hast du mit „Ja“ bestätigt.
- **Nebenher:** Gesamtportfolio-Backtest 2016–2026 je Konto (Mo), Risk-Management-Bausteine durchgerechnet (Fr),
  Prosper-Kurs Lektion 4/5, News-Quellen-Ledger, TradingAgents-Forward (ab 23.11.), Cockpit online hinter
  Cloudflare Access, Lebensjournal Stufen B–D1 (eigenes Repo).
- **Live:** ORB-SP500 seit Mo auf allen Bridges pausiert. Die Bots hatten eine ruhige Woche, die Handtrades
  nicht (Performance-Report).

## 2. Aktive Zeiten

Ohne Auto-Commits gab es 26 eigene Commits an 5 Tagen. Der Schwerpunkt lag klar auf **Mittwochabend**: 13 Commits
zwischen 21 und 24 Uhr (Soll/Ist-Reparatur, ORB, Rohstoffe, Edelmetalle). Dazu kommen Mo spätabends (22 Uhr),
Di mittags (12 Uhr), Do nachmittags (Signal-Hub 15 Uhr) und die Nacht auf Sa (01 Uhr, News-Quellen, TradingAgents).
Die Handtrades lagen tagsüber (Di 13–17 Uhr MEZ) und am Do kurz vor Mitternacht (EK Gold/Silber 23:53 Serverzeit).
Das Muster bleibt wie zuletzt: Arbeit in langen Abendblöcken, oft bis nach Mitternacht.

## 3. Meine Main Erkenntnisse

### 3.1 Eine Lücke, die jede Woche gleich aussieht, war ein kaputtes Messgerät

**Befund.** `soll_ist.py` hat von September bis 18.11. **jeden** ORB-Trade als „nie gesehen“ geführt. Das galt
auch für den gehandelten +17,9-R-Tag am 05.11. Dahinter verschwanden die echten Verpasser: 09.11. (+6 R, Order
„Invalid price“) und 13.11. (Ausbruch vor der Platzierung).

**Mechanismus.** Der Abgleich suchte Soll und Ist über die **Einstiegsminute**. Seit dem Bridge-Umbau am 17.09.
tragen die ORB-Pending-Keys aber nur noch ein **Datum**. Der Vergleich konnte also nie treffen. Das Werkzeug meldete
keinen Fehler, nur eine konstante Zeile „nie gesehen“.

**Wie es aufgefallen ist.** Nicht durch das Werkzeug selbst. Auslöser war die Handprüfung der Tage 13./16./17.11.
Dabei zeigte sich, dass ein als „nie gesehen“ geführter Tag im Bridge-Log klar „platziert“ stand. Gegenprobe an
KW45/46 nach der Reparatur: 05.11. jetzt „platziert“, 09.11. „Platzierung gescheitert“, 13.11. „keine ORB-Order“.
Diese Woche schlug die neue Warnung `⚠️ ZUORDNUNG` gleich an. Diesmal war es ein Fehlalarm, weil live die
Gegenseite füllte (Performance 5, Vorbehalt 4). Auch das ist eine Lehre: Eine neue Warnung braucht einige Wochen,
bis man ihre Fehlalarme kennt.

**Lehre.** Eine konstante Lücke zuerst als Messfehler behandeln, nicht als Bridge-Fehler. Wer State-Keys oder den
Order-Pfad ändert, prüft im selben Zug den Abgleich. Das steht jetzt in `CLAUDE.md` („Live-Abgleich absichern“).
[[live-abgleich-fehlerklassen]] · siehe Memory: `konstante_luecke_ist_messfehler`

### 3.2 NASDAQ-ORB lebt von einer Minute, die die Bridge kaum sieht

**Befund.** Von 702 Backtest-Trades der Live-Regel (0,6 ATR + Storno) füllen **655 in der ersten Minute** nach
09:45 NY. Rechnet man „erste Minute blind“, bleibt nichts übrig (IS 0,02 R, OOS −0,11 R). Im Tresor kommt der
gesamte Gewinn (+61 R) aus dieser Minute.

**Mechanismus.** Nach der ersten Minute streicht das Storno fast immer beide Seiten, weil beide SLs in der Range
liegen. Die Bridge platziert erst um ~09:45:03. Bricht der Kurs schon in diesen Sekunden aus, meldete sie bisher
`breakout_passed` und ließ den Tag aus. Genau diese Tage trugen den Backtest.

**Wie es aufgefallen ist.** Über die verpassten Gewinner in KW46 (+14,9 R in einer Woche). Dann der M1-Backtest
mit Füll-Minute je Trade. Fast getäuscht hätte uns der Kandidat „SL an der 15:30-Kerze + Market“. Er gewann alle
drei Anlass-Tage, aber die waren am Chart ausgesucht. Im Tresor: 102 Trades, Ø −0,16 R. Live-Abgleich
05.10.–17.11.: Die Bridge traf 5 von 9 Erste-Minute-Ausbrüchen, netto verpasst ≈ +3,2 R. Das ist weniger schlimm
als die Untergrenze.

**Lehre.** Vor jeder Live-Regel fragen: In welcher Minute füllt der Backtest, und liegt die Order dann schon? Das
ist jetzt Pflicht in `CLAUDE.md`. Und: Tage, an denen eine Idee entsteht, gehören nie in ihren Test.
[[orb-nasdaq-kerzen-sl-market]] · siehe Memory: `orb_nasdaq_storno_nur_erste_minute`

### 3.3 Edelmetalle auf Wochen: belegt ist nur das Long-Beta

**Befund.** Getestet wurden Gold, Silber und Platin auf 4–26 Wochen mit vorab registrierten Regeln (336 Versuche).
Ergebnis: **0 von 285** Merkmal-Varianten bestehen. Der nachgebaute Rohstoff-Screener schlägt bei keinem Metall
„immer long“. Die Short-Seite ist im OOS überall negativ.

**Mechanismus.** Realzins, 2J-Rendite und Zinskurve wirken nur 2018–26 (OOS-t bis +2,3), 2004–17 nicht. Das ist
ein Regime, keine Regel. In einem Markt mit starker Aufwärtsdrift sieht jedes Long-Signal gut aus. Ein Score muss
deshalb die Drift schlagen, nicht null.

**Wie es aufgefallen ist.** Die Registrierung vor dem Test (`56a49a99`) verlangte IS-t ≥ 2 in beiden IS-Hälften und
auf ≥ 2 Metallen. Diese Hürde hat die scheinbar guten Kandidaten aussortiert. Zwei Gegenproben bestätigten das Bild.
Die Gold-Komposition (5 Makro-Bausteine) liegt im OOS unter „immer long“ (+6,3 bp/Tag). Der Gold-Zinskurven-Filter
stand drei Wochen lang auf „nur long“, während Gold um ca. 13 % fiel. Der Treiber war der Dollar, den der Filter
nicht sieht.

**Lehre.** Für Edelmetalle keine Short-Signale aus Score oder Makro ableiten. Jede neue Makro-Idee gegen „immer
long“ und gegen beide Zeiträume (vor/nach 2018) prüfen. Mehr Bausteine machen einen Filter wählerischer, nicht
treffsicherer. [[edelmetalle-htf-makro]] · [[filter-gold-komposition]] · siehe Memory: `edelmetalle_htf_kein_edge`,
`gold_komposition_schlaegt_drift_nicht`, `gold_zinskurven_filter_twist_und_cache`

### 3.4 Serienbremsen klingen vernünftig und schaden fast überall

**Befund.** 69 Varianten auf allen Live-Beinen, H4 und Daily-C2: Pause nach N Verlusten, Risikohalbierung,
Tageslimit. Fast überall neutral bis schädlich. Einziger Kandidat ist ORB S&P mit Pause nach 3 Verlusten (OOS-Sharpe
1,07 → 1,32), bei 69 Versuchen möglicherweise Zufall. Das TTP-Tageslimit (3 %) greift nie, der schlechteste Tag
liegt bei −0,95 %.

**Mechanismus.** Eine Bremse hilft nur, wenn Verluste gehäuft kommen und die Trades danach schlechter sind. Bei
unseren Beinen ist der Ø R nach 1–3 Verlusten **gleich oder höher** als der Durchschnitt (Rücklauf nach Stopps).
Die Bremse schneidet also genau die Erholung ab. Die Halbierung ist nur ein pauschal kleineres Risiko in teurer Form.

**Wie es aufgefallen ist.** Anlass war Prosper-Lektion 4, die Cooldown und Tageslimit als Standard empfiehlt.
Statt die Regeln zu übernehmen, kam zuerst die Diagnose (Ø R nach N Verlusten), dann der Test. Bei CTNL war eine
frühere „Halbierung hilft“-Zahl schon einmal ein Vorgriff gewesen.

**Lehre.** Bei Vorschlägen wie „nach Verlusten pausieren“ zuerst die Diagnose zeigen, dann bauen. Die Bausteine sind
jetzt fester Prüfschritt in Phase 5 jedes neuen Edges, aber kein Automatismus. [[risk-management-bausteine]] ·
siehe Memory: `serienbremsen_schaden_fast_allen_beinen`

### 3.5 Das Portfolio trägt, der Engpass ist das Risiko je Konto

**Befund.** Live-Beine mit echten Kosten, 2016–10/2026. Sharpe EK 1,52, FK 1,44, TTP 1,50, IQ 1,78. Aber die
Wahrscheinlichkeit, binnen 12 Monaten die Kontogrenze zu reißen, liegt bei **IQ 15 %**. EK hätte einen Max DD von
−59 % (45-%-Grenze 2018 gerissen).

**Mechanismus.** Die Beine sind kaum korreliert (|ρ| < 0,15). Die Kombination ist also gut. Die Grenzen sind aber
eng (IQ 6 %), oder das Risiko je Trade ist hoch (EK 3,5 %). Dann entscheidet nicht der Edge, sondern die Pfad-Tiefe
der schlechten Phasen.

**Wie es aufgefallen ist.** Erste vollständige Rechnung je Konto statt je Bein. Datenfallen auf dem Weg: USTBOND
erst ab 12/2018, Platin-Daten kaputt, ASB-Dateien enden 01.10. Diese Woche passt live dazu: IQ hat nur noch ca.
3.500 USD Abstand zur Grenze. Auf EK liegt das größte Risiko gerade nicht bei den Bots, sondern bei den Handtrades
(ca. 16 % offen).

**Lehre.** Gewichtungs- und Risikoänderungen gegen diese Basis messen, nicht gegen Einzelbein-Sharpes.
[[gesamtportfolio-backtest-2016]] · siehe Memory: `gesamtportfolio_backtest_2016`

## 4. Neues Wissen diese Woche (Papers/Ideen)

- **Edelmetalle HTF + Makro** ([[edelmetalle-htf-makro]]). (a) These aus Screener und Makro-Ketten: Score- und
  Makro-Bausteine sagen die Richtung von Gold/Silber/Platin auf Wochen voraus. (b) Getestet auf Yahoo-Futures
  2004–05/2026, Lock `metals_htf_v1`. (c) 0 von 285 Varianten bestehen, Screener < „immer long“. (d) **Verworfen**
  als Signal. Rohstoff-Screener zeigt VERKAUFEN bei Edelmetallen nur noch als Warnung (1.2).
- **NASDAQ-ORB Kerzen-SL + Market / Vorbörsen-Range** ([[orb-nasdaq-kerzen-sl-market]],
  [[nasdaq-orb-vorboersen-range]]). (a) SL an der 15:30-Kerze statt 0,6 ATR, Market statt Stop-Order. (b) M1-Backtest,
  48 Versuche. (c) IS/OOS +0,08/+0,09 R, Tresor Ø −0,16 R. (d) **Verworfen**; live nur der Market-Rückfall (IS +88,
  OOS +7, Tresor +36 R gegenüber Auslassen). Die Vorbörsen-Range (OOS +0,28 R) ist geparkt, die Kosten sind offen.
- **Gold-Richtungs-Komposition** ([[filter-gold-komposition]]). (a) Fünf Makro-Stimmen sagen die Gold-Richtung
  „sehr wahrscheinlich“ voraus. (b) IS 2010–19, OOS bis 05/2026, 17 + 53 Versuche. (c) Kein OOS-Vorteil gegen die
  Drift; als Veto auf CTNL sperrt sie Gewinner. (d) **Verworfen**, MACRO-Veto allein bleibt live.
- **Risk-Management-Bausteine** ([[risk-management-bausteine]]). (a) Prosper-Kurs: Cooldown/Tageslimit gehören in
  jedes System. (b) 69 Varianten auf allen Beinen. (c) Siehe 3.4. (d) **Prüfschritt in Phase 5**, keine Bot-Änderung.
- **Gesamtportfolio-Backtest 2016** ([[gesamtportfolio-backtest-2016]]). Siehe 3.5. **Basis für künftige
  Gewichtungen.**
- **Signal-Hub** ([[signal-hub]]). (a) These: Deine Auswahl ist der Edge, nicht die Regel. (b) Noch kein Test,
  Forward-Messung über Journal + Paper-Simulation. (c) –. (d) **Live seit 19.11.** (Stufe 1, keine Orders).
  Erinnerung Handbacktest Sa 28.11.
- **TradingAgents (Tauric Research)** ([[tradingagents-tauric]]). (a) LLM-Agenten-Team trifft Kaufentscheidungen.
  (b) Forward ab 23.11. auf NVDA/JPM/XOM/UNH/WMT gegen Buy/Zufall/Momentum. (c) Hürde ab 15.02.2027: schlägt alle
  Kontrollen und t > 2. (d) **In Arbeit (Forward)**. Fallstrick: Ein Datum vor heute gilt als historisch, dann
  fehlen Fundamentaldaten.
- **News-/Sentiment-Quellen** ([[news-sentiment-quellen]]). Quellen-Ledger mit Kontrolle gegen die Marktrichtung,
  täglich 22:30. **In Arbeit (Forward)**. Keys für Finnhub/Alpha Vantage/Reddit fehlen.
- **Prosper-Education** ([[prosper-education-uebernahme]]). Plan: erst die ganze Education durchgehen, dann
  vergleichen und übernehmen. Lektion 4 umgesetzt. **In Arbeit.**

**Ideen-Inbox, neu seit KW46:**
- (16.11.) Persönliches Dashboard + Trading-Journal ins Cockpit: einsortiert (Lebensjournal, eigenes Repo).
- (18.11.) Screener-Pipeline auch für Forex (Modus `devisen`): noch nicht einsortiert.
- (18.11.) NASDAQ-ORB Market-Rückfall: ersten echten Fall beobachten. Offen, in KW47 kein Fall.
- (21.11.) Prosper-Dashboard als Vorlage für Makro-Agent/Trading-System: in den Prosper-Plan eingeordnet.

## 4b. Vertiefung: Der bedingte Erwartungswert nach einer Verlustserie

**Was es ist.** Eine Serienbremse („nach 3 Verlusten pausieren“) ist eine Wette auf eine Aussage: Die Trades
**nach** einer Verlustserie sind schlechter als der Durchschnitt. Das lässt sich direkt messen, bevor man eine
Bremse baut. Man nimmt alle Trades, die auf genau N Verluste in Folge folgen, und vergleicht ihren Ø R mit dem
Ø R aller Trades. Das ist der bedingte Erwartungswert E[R | N Verluste davor]. Nur wenn er klar darunter liegt,
kann eine Pause helfen. Liegt er gleich hoch, kostet die Pause nur Trades. Liegt er höher, schneidet sie die
besten Trades ab.

**Beispiel mit unseren Zahlen.** ORB S&P im OOS: Ø R aller Trades 0,44. Mit der Regel „nach 3 Verlusten die
nächsten 3 Signale auslassen“ steigt der Ø R der verbleibenden Trades auf 0,71. Etwa ein Drittel der Trades fällt
weg, ΣR steigt trotzdem leicht (67,8 → 72,2 R), der Max DD sinkt (−17,8 → −13,6 R). Bei CLS, CTNL, Gold ASB, Trend
Pullback, OU und C2 ist es umgekehrt. Dort liegt der Ø R nach 1–3 Verlusten auf oder über dem Durchschnitt, also
schadet jede Pause.

**Warum das für uns wichtig ist.** Zwei Fallen. Erstens die Zahl der Versuche: Bei 69 getesteten Varianten findet
man fast immer eine, die zufällig gut aussieht. Deshalb läuft ORB-S&P-P3 nicht live. Zweitens der Vorgriff: Bei CTNL
sah eine Halbierung einmal gut aus, weil die Regel schon wusste, wie der aktuelle Trade endet. Die Serie darf nur
aus **geschlossenen** Trades vor dem Einstieg bestehen. Diese Woche passte es auch live. Die NASDAQ-ORB-Bridge hat
nach dem Stopp am Montag an drei Tagen nicht gehandelt, aber nur weil das Storno griff, nicht wegen einer Bremse.

## 4c. Makro-Wochenprüfung

**Die Vorgehensweise kurz** ([[makro-agent-report-pruefung]]): (1) Report ganz lesen, auch die Kanal-Nachrichten.
(2) Jede prüfbare Zahl gegen eigene Daten. (3) Widersprüche suchen. (4) Gegen die eigene Evidenz gewichten
(Richtung allein ≈ 0 R, Rücksetzer-Limit positiv). (5) Trade-Tabelle inkl. „auslassen“. (6) Mentor-Chart
einarbeiten, Alarmliste. **Gegenwährung wählen:** Stärke aus Zinsen + Angst nur gegen Rohstoffwährungen
(AUD/NZD/CAD), nie gegen CHF/JPY. Jede Rohstoffwährung hat ihren eigenen Rohstoff-Schalter (CAD: Brent über 105).
Trades mit demselben Treiber zählen als ein Risiko.

**Nachprüfung KW47** (Beispiele 3 = Reports 15.11. und 4 = Mittwochsreport 18.11., Lake-Kurse; in die Notiz
zurückgeschrieben):

| Trade / Punkt | Sicht | Ergebnis |
|---|---|---|
| AUD/USD Short 0,6905 | Agent | **Ziel 0,6670 Do 19.11. ~02:00 UTC → +2,64 R** (halbe Größe), Stop nie berührt |
| GBP/CHF Long (nur nach UK-CPI > 3,8) | Agent | nicht aktiv (CPI 3,6), Fr ~1,098 → **Auslassen richtig** |
| EUR/GBP Short (< 0,8320) | Agent | nicht ausgelöst, Fr 0,8386 → **Watch richtig** |
| Gold (gesperrt, auch long) | Agent | −8,9 % in der Woche → **Sperre richtig** |
| EUR/USD Short (Report-Trade) | Agent ausgelassen (Regel 2) | Report-Ziel 1,1000 Mo erreicht → **Auslassen kostete ≈ +1,2 R** |
| GBP/CHF Long 1,10673 | Dennis | gefüllt, SL ca. Do → **−1,0 R** |
| US100 Long 27.003 | Dennis | gefüllt Mi, Fr 25.181 → **offen −0,73 R** |
| EUR/USD 1,1104–1,1132 / Gold 4.015,7 | Dennis | nicht gefüllt, Richtung ✓ |
| USD/JPY Short 159,84 | Nutzer | offen +0,61 R; **EK-Stop auf 159,716 nachgezogen** (Risiko weg), FK weiter 162,00 |

**Was hielt:** Das Auslassen (4 von 5 Fällen richtig). Die Gold-Sperre gegen den eigenen Filter („nur long“). Die
Grundregel „bei Angst halten die Häfen“: JPY +0,7 %, CHF −0,1 %, AUD −2,2 % gegen USD. Die Frage „CHF/JPY schwächer
in einer Zinswoche ohne Angst?“ war nicht anwendbar, denn es kam eine Angstwoche ohne Zinsanstieg.
**Was nicht hielt:** Das Szenario. BASE „Dollar hält“ (50 %) wurde vom TAIL „KI-Schock“ (20 %) abgelöst, NAS100
−9,6 %. Der Gold-Zinskurven-Filter blieb die dritte Woche gegen den Markt. Regel 2 kostete beim EUR/USD-Short einen
Gewinner.

**Laufende Bilanz:** Agent 1 Trade, 1 Treffer, **+2,64 R** (geschlossen) · Dennis 2 geschlossen, 0 Treffer,
**−2,0 R** (+ US100 offen −0,73) · Kanal-Limits 1 / 0 / −1,0 R. Dennis-Limits: **2 von 7 gefüllt**, beide im Minus.
In 4 der 5 ungefüllten Fälle wurde das Ziel trotzdem erreicht. Nach zwei Wochen ist das noch kein Urteil.
**Nutzer real:** EUR/USD **Long** (3×) und Gold Long (2×), alle gestoppt (−510 USD / −71 EUR). Beide lagen gegen
die Agent-Sicht. Offen: EK Gold + Silber Long (ca. 16 % Kontorisiko).

**Für KW48 gibt es noch kein Beispiel** in der Notiz (keine Report-Prüfung vom 22.11.).

## 5. Verbesserungen

- **Soll/Ist ORB-Zuordnung repariert** (`a2c42324`): Bein + Datum + Richtung, Grund aus dem State, Liste „ORB je
  Tag“, Warnung `⚠️ ZUORDNUNG`. Neuer CLAUDE.md-Abschnitt „Live-Abgleich absichern“.
- **NASDAQ-ORB Market-Rückfall** auf allen drei Bridges (Backups je Bridge). Live noch ohne Fall.
- **ORB-SP500 pausiert** (16.11.), nur noch Forward-Test.
- **Signal-Hub Stufe 1** mit Journal, Paper-Simulation und Risiko-Sperre. Bugfix Zeitformat (21.11.).
- **`fetch_fred` lädt nach 20 h neu** (vorher veralteter Cache im Gold-Filter).
- **Neue Forward-Messungen:** Rohstoff-Screener 1.2, TradingAgents, News-Quellen-Ledger.
- **Cockpit online** hinter Cloudflare Access (Upload per Pages-API, ARM64-Umweg).
- **Weekly-Abzug ohne Ausfall:** Diesmal liefen alle Terminals, Salden auf den Cent.
- **Edge-Ampel zum ersten Mal seit fünf Wochen frisch** (Liste bis 17.11.). Ein Werkzeug-Fix war nicht nötig,
  der Dukascopy-Abruf hing diesmal einfach nicht. Die Ursache der früheren Hänger bleibt offen.

## 6. Verschlechterungen / offene Probleme

- **EK: offene Hand-Longs Gold + Silber mit ca. 16 % Kontorisiko**, EK in drei Wochen ca. −13 %.
  Handtrades auf EK/FK kosteten die Woche −510 USD / −71 EUR. Die Dashboard-Frage aus KW46 ist weiter offen.
- **STT auf TTP weiter offen** (seit 16.10.), obwohl am 10.11. „schließen“ entschieden wurde.
- **Soll/Ist-Werkzeug:** pausierte Beine (US30, SP500) im Soll, Storno-Tage als Stopp, FK-Kopfzeile mit
  Handtrades, Zuordnungswarnung bei gefüllter Gegenseite, EK-NASDAQ-Soll weicht stark ab.
- **Edge-Ampel sieht Gold ASB nur bis 30.09.** (ASB-Datendateien enden 01.10.). Grün heißt dort also „Stand
  September“.
- **Gold-Zinskurven-Filter** die dritte Woche gegen den Markt (Twist setzt die Bestätigung zurück).
- **Dachprojekt weiter ohne mechanischen Live-Kandidaten.** Die Hoffnung liegt jetzt auf dem Forward im Signal-Hub.
- **IQ:** nur noch ca. 3.500 USD bis zur 6-%-Grenze, im Backtest 15 % Bruchrisiko in 12 Monaten.

## 7. Optimierungsmöglichkeiten

1. **Regel für Handtrades auf Bot-Konten** festlegen (max. Risiko je Trade/Treiber, oder eigenes Konto). Auf EK
   ist das jetzt die größte Risikoquelle. Der Signal-Hub mit Risiko-Sperre ist der natürliche Ort dafür.
2. **Soll/Ist:** pausierte Beine aus dem Soll nehmen, Storno-Tage wie die Bridge werten, FK-Kopfzeile nur Bot,
   „Gegenseite gefüllt“ nicht als fehlende Zuordnung zählen.
3. **STT schließen** oder die Entscheidung vom 10.11. bewusst zurücknehmen.
4. **IQ-Risiko** gegen die Basis aus dem Gesamtportfolio-Backtest prüfen (z. B. Gold ASB 0,67 % senken).
5. **Gold-Zinskurven-Filter:** „Twist setzt zurück“ als gezählte IS-Variante testen. Nicht aus den drei Wochen
   heraus auswählen.
