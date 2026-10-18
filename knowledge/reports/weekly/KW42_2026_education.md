# Weekly Checkup - Education - KW42/2026

**Abgedeckte Woche: Mo 2026-10-12 bis So 2026-10-18.** Erzeugt am So
18.10. abends durch den geplanten `Forex-Weekly-Report`-Task (puenktlich).

## 1. Was stand die Woche an / Hauptfokus

Wieder eine reine Research-Woche: **keine Aenderung an Code oder Config der
drei Live-Bridges** (geprueft ueber Datei-Zeitstempel und Git). Fuenf Faeden:

- **Noise-Area-Momentum (Zarattini) weitergedacht (Mo-Fr):** Tresor-Diagnose,
  Regime-2026-Raster (18.432 Versuche), Oel als Filter und als Gegenprobe,
  daraus der Forward-Kandidat "NASDAQ K2 + Oel-Index-Korrelation 60 T. < 0"
  (K60) und am Fr eine Challenge-Gewichtung K60 + kleines ORB-NASDAQ fuer TTP
  und IQ. Alles Forward bis 31.03.2027, **kein Livegang**.
- **ORB:** Oel als ORB-Filter (Mo), NASDAQ mit/ohne Storno am SL ueber 10
  Jahre (Fr). Ergebnis: Die live laufende Storno-Regel ist ein 2026-Fit (3.2).
  Dein Entscheid vom 16.10.: ORB bleibt erstmal, wie es ist.
- **Fruehwarnung/Kill-Switch und Tresor-Check aller Live-Beine (Mi):** Paket
  `edge_monitor/`, seit Fr als Schritt 5b mit Warnstufen im Weekly Report.
- **Gruppenarbeit SMH Elite 3:** Gold ASB nur auf IS neu optimiert (Do),
  Mentor-PDF dazu (So); Key-Level-Edge-Card + Stufe-1-Backtest (Fr);
  Mikrostruktur Runde 2 mit 22 gescreenten Papers und 4 Backtests (So).
- **Dachprojekt:** Makro-Faktor-Katalog aus OneNote (49 Faktoren, Mo),
  Telegram "SMH Daily Update" nachimportiert (Fr), neuer Task
  `G8-Notion-Sync` (Mo).

Commits der Woche: `7c09e9a6`, `764ed010`, `942ea803`, `a5ef963b`,
`4e7857ce`, `d9c0e4ce`, `be8c6e14` und der Sammel-Commit `9ebdc80a` (So,
Research-Stand 11.-18.10.). Damit ist der in KW41 bemaengelte ungesicherte
Research-Stand **weitgehend committet**; nur die Runde-2-Dateien vom So
(Locks `smh_k4`-`k7`, `smh_microstructure/*.py`, Screening-Notiz) liegen noch
ungetrackt im Working Tree.

## 2. Aktive Zeiten

Nach Commit-Zeiten, CHANGELOG-Daten und dem Energie-Protokoll des Rechners:

- **Mo und Mi spaetabends** (22-24 Uhr: Oel-Filter, Edge-Monitor),
- **Do/Fr nach Mitternacht** (bis ca. 00:30: Gold ASB, NASDAQ-Storno),
- **Fr Vormittag bis Mittag** (Warnstufen, K60-Gewichtung, Key Levels),
- **So Vormittag** (Sammel-Commit 11:26, Mentor-PDF, Mikrostruktur Runde 2).

Also wieder vor allem Abende, Naechte und das Wochenende. Auffaellig wie in
KW40/41: Die langen Standby-Phasen der Bridges (Mo 09:55-17:09, Do
14:49-15:53) liegen tagsueber an Werktagen. Ob das zugeklappter Deckel oder
Akku ist, bleibt unbelegt (Performance-Teil, Abschnitt 6).

## 3. Meine Main Erkenntnisse

### 3.1 Einen Edge-Kipp sieht man nicht kommen; man kann nur den Schaden begrenzen

**Befund:** Fuenf Leistungssignale (gleitender Mittelwert, CUSUM, SPRT,
Bayes, Drawdown) wurden an **7 bekannten Edge-Bruechen** (ORB IS-only,
Zarattini, EU-Open) und an **10 Live-Beinen** getestet. Keines warnt
verlaesslich **vor** dem letzten Equity-Hoch. Bester Schadensbegrenzer ist ein
Drawdown-Schalter mit strengem Fehlalarm-Budget (1 Fehlalarm in 5 Jahren): Er
verbessert **7 von 7** Bruechen, kostet gesunde Live-Beine aber im Median
**-3,4 R** und greift erst **ca. 6 Monate** nach dem Hoch.

**Mechanismus / Warum:** Ein Kipp sieht in den ersten Wochen genauso aus wie
eine normale Pechstraehne. Strategien mit niedriger Trefferquote und fetten
Gewinnern (ORB) haben lange Verlustserien auch dann, wenn der Edge lebt.
Sequenzielle Tests wie CUSUM oder SPRT schlagen deshalb dort dauernd an
(orb_nasdaq: -157 R durch Fehlabschaltungen). Ein Drawdown-Schalter reagiert
dagegen nur auf das, was wirklich weh tut: die Tiefe des Lochs.

**Wie es aufgefallen ist:** Die Schwellen wurden nur auf den Fenstern **vor**
dem Bruch kalibriert, per Bootstrap mit festem Fehlalarm-Budget, und alles
war vorab im Lock `edge_monitor_20261014` registriert (13 Regeln, 17 Faelle).
So konnte kein Signal "im Nachhinein" gut aussehen. Nebenbei fiel auf, dass
die Broker-Liste vom 04.10. orb_nasdaq **ohne** Storno rechnet (ca. 206 statt
77 Trades im Jahr); ihre NASDAQ-Zahlen gelten also nicht fuer die
Live-Konfiguration.

**Lehre / Regel:** Bei Live-Beinen nicht nach dem Fruehwarnsignal suchen,
sondern den Preis eines Schalters festlegen: wie viel Ertrag man im
Normalfall opfert, um im Bruchfall frueher auszusteigen. Die Ampel im Weekly
Report ist eine Anzeige, kein Eingriff.
siehe Memory: `edge_kipp_nicht_vorhersagbar` · [[edge-fruehwarnung-kill-switch]]

### 3.2 Die NASDAQ-Storno-Regel, die live laeuft, ist ein 2026-Fit

**Befund:** Ueber 10 Jahre M1 (2016-2026) bringt ORB NASDAQ **ohne** Storno am
SL **Σ +584 R (t 3,2)**, **mit** Storno nur **+198 R (t 1,8)**, bei aehnlichem
MaxDD. Nur im Tresor ist Storno besser (+55 gegen +21 R). Die Tage, die die
Regel wegnimmt, brachten im IS +0,43 R je Trade, 2026 dagegen -0,29 R.

**Mechanismus / Warum:** Die Entscheidung vom 04.10. stand auf dem Fenster
2019-2026 (Storno verliert gerade 2016-18) und auf einem "OOS" ab 2023, das
2026 schon enthielt. Damit wurde ein Muster des Zieljahrs zur "robusten"
Regel. Ihr Hauptargument (unklare Fill-Minuten) war ausserdem am selben Tag
durch Tickdaten erledigt.

**Wie es aufgefallen ist:** Durch deine Frage, woher die Wahl eigentlich kam.
Der saubere Vergleich mit getrennten IS/OOS/Tresor-Fenstern zeigte die
Herkunft. Live wirkt die Regel diese Woche sichtbar: Am Di 13.10. und Fr 16.10.
wurden auf allen Konten **beide** NASDAQ-Seiten storniert, es gab keinen
einzigen ORB-NASDAQ-Trade. Ob das gespart oder gekostet hat, sagt erst der
Soll/Ist-Teil.

**Lehre / Regel:** Jede Entscheidung von vor dem 05.10. (Overfitting-Sperre)
ist verdaechtig, bis sie ueber 2016-2026 mit getrennten Fenstern nachgerechnet
ist. Dein Entscheid (16.10.): Storno bleibt vorerst; das ist bewusst, und
der Preis steht jetzt in Zahlen da.
siehe Memory: `nasdaq_storno_ist_2026_fit` · [[orb-order-storno-und-haltedauer]]

### 3.3 Gold ASB verduennt sich, statt zu brechen, und hatte diese Woche seinen ersten echten Fill

**Befund:** Nur auf IS optimiert (20.736 Versuche, M5, TTP-Kosten) liegt Gold
ASB bei **Ø +0,33 R (IS) → +0,18 R (OOS) → +0,04 R (Tresor**, PF 1,19, 18
Trades). Alle 11 Jahre sind positiv, die Deflated Sharpe ist 0,24. Live
loeste am **Do 15.10. die erste Stop-Order** seit der Umstellung aus (Short
4.136); der Zeit-Exit um 11:00 NY schloss bei ca. 4.157, auf TTP **-333 USD
(-0,56 R)**.

**Mechanismus / Warum:** Anders als beim ORB kippt hier kein Filter ins
Gegenteil. Der Effekt wird Jahr fuer Jahr kleiner, vermutlich weil
Asia-Range-Breakouts in Gold bekannter und enger geworden sind (Hypothese).
Der Zeit-Exit wirkt dabei wie geplant: Der Kurs lief gegen die Position, der
Stop (4.174) wurde aber nicht erreicht, also ging nur ein halbes R verloren.

**Wie es aufgefallen ist:** Der Tresor-Check aller Live-Beine (14.10.) zeigte
bereits +0,33 → +0,18; die IS-only-Runde bestaetigte die Treppe. Fast
taeuschend war die Zahl "alle 11 Jahre positiv": Sie klingt robust, sagt aber
nichts ueber die Groesse, und die Groesse ist im Tresor fast null.

**Lehre / Regel:** "Ueberlebt den Tresor" und "statistisch belegt" sind zwei
verschiedene Aussagen. Ein Edge mit sinkender Treppe gehoert unter
Beobachtung (Ampel), nicht nachjustiert auf altem OOS.
siehe Memory: `gold_asb_verduennt_statt_bruch` · [[gold-asb-is-only-neuanalyse]]

### 3.4 Mikrostruktur-Praemien gehoeren dem Maker: 7 von 7 Kandidaten an den Kosten gescheitert

**Befund:** Ueber zwei Runden der Teamaufgabe (07.10. und 18.10.) ist **kein
einziger** Mikrostruktur-Kandidat netto positiv. Die vier neuen Tresore
(netto je Trade): Dollar-W Europa **-1,20 bps**, Tokio **-2,35**,
Halbstunden-Periodizitaet **-3,34**, Overnight Drift **-0,73**. Das Dollar-W
nach dem Tokio-Fix ist trotzdem echt: brutto im IS **+1,6 bps, t 4,8**.

**Mechanismus / Warum:** Jeder dokumentierte Effekt liegt brutto bei 0-3 bps,
also genau in der Groesse unserer Rundturn-Kosten (FX 1,1-1,3 bps,
Index-CFDs 2,3-2,6 bps). Diese Effekte entstehen, weil jemand Liquiditaet
braucht und dafuer zahlt; verdienen kann sie nur, wer die Liquiditaet stellt
(Limit-Order). Wer per Market-Order einsteigt, zahlt die Praemie, die er
ernten will (Vertiefung 4b).

**Wie es aufgefallen ist:** Die verschobenen Kontrollfenster (±4/+8 Stunden)
lagen beim Tokio-Effekt bei +0,35 bis -0,9 bps; der Effekt ist also an den
Fix gebunden und kein Datenartefakt. Dass er trotzdem nicht erntbar ist,
steht in den Papers selbst: Krohn et al. positiv erst bei halbem Spread,
Boyarchenko nach Spread Sharpe -0,5. Eine Datenfalle (Ausstiege zur
Rollover-Zeit) wurde vor dem ersten gezaehlten Lauf behoben.

**Lehre / Regel:** Vor jedem Mikrostruktur-Test die Brutto-Effektgroesse
des Papers gegen unsere Kosten halten (`smh_microstructure/costs.py`). Unter
etwa 3x Kosten nur testen, wenn eine Maker-Ausfuehrung realistisch ist.
siehe Memory: `mikrostruktur_praemie_gehoert_dem_maker` ·
[[smh-elite-mikrostruktur]] · [[mikrostruktur-paper-screening]]

### 3.5 Key Levels: Je sichtbarer das Level, desto staerker der Sog

**Befund:** Der Magnet-Befund aus KW41 (runde Zahlen) gilt breit. Auf 10
FX-Paaren (nur IS 01/2016-03/2023) drehen Kurse bei M1-Beruehrung **seltener**
um als an Schein-Leveln: Vorwoche 43,3 % gegen 48,5 % (z -4,5), Session
47,4 % gegen 49,5 % (z -7,6), runde Zahl z -7,8, halbe Zahl z -5,1. Das
Vorzeichen ist in **38 von 40** Paar-Level-Kombinationen negativ. Pivots und
Engulfing-Opens verhalten sich wie Schein-Level.

**Mechanismus / Warum:** Hinter sichtbaren Leveln sammeln sich Stops und
Ausbruchs-Orders. Wird das Level erreicht, loesen sie aus und ziehen den
Kurs hindurch. In News- und Hochvola-Phasen ist der Sog noch staerker, was
zur Stop-Erklaerung passt.

**Wie es aufgefallen ist:** Durch die Edge Card, die mit dir Feld fuer Feld
erarbeitet wurde, und durch die Kontrollgruppe (Schein-Level) in jedem
Vergleich. Ohne sie haette "Umkehrquote unter 50 %" auch "M1 laeuft halt
weiter" heissen koennen. Unterwegs fiel ein Zeiteinheiten-Fehler unter
pandas 3 auf (ms/us/ns), der auch in K1 steckte, dort aber wirkungslos war.

**Lehre / Regel:** Key Levels als Ziel behandeln, nicht als Einstieg gegen
den Kurs. Netto traegt bisher nur eine von 226 Zellen knapp ("Vorwoche, M1,
G = 20, Durchlauf", t 0,9); Stufe 2 und OOS/Tresor stehen aus.
siehe Memory: `runde_zahlen_magnet_statt_wand` · [[keylevel-edge-card-final]]
· [[keylevel-edge-card]]

### 3.6 Live: Ein Standby von einer Stunde reicht, um den ORB-Tag zu verlieren

**Befund:** Am Do 15.10. war der Rechner von 14:49 bis 15:53 im Standby.
Die ORB-Range endet um 15:45 Berlin. Der erste Lauf danach (15:54) fand auf
SP500 und NASDAQ beide Ausbruchsseiten schon durchlaufen vor und
platzierte **nichts** (`breakout_passed ... vor Platzierung`). Am Mo 12.10.
schlief der Rechner sogar **7 Stunden** (09:55-17:09).

**Mechanismus / Warum:** ORB haengt an einem einzigen Zeitpunkt pro Tag (dem
Platzierungs-Pass kurz vor Range-Ende). Andere Beine holen ein verpasstes
Fenster beim naechsten Lauf nach, ORB kann das nicht. Nach dem Aufwachen war
ausserdem der Data Lake stundenlang veraltet (EK: Lake-Fallback bis 17:06),
die Laeufe wurden langsam, und auf EK kam der Gold-ASB-Zeit-Exit 13 Minuten
zu spaet (diesmal zufaellig zum besseren Kurs).

**Wie es aufgefallen ist:** Die Logzeile `[ORB-PRAEZISE] Range-Ende in
110s` fehlte am Do, an den anderen Tagen war sie da. Das Energie-Protokoll
(`Kernel-Power 506/507`) zeigte dann die Luecke auf die Minute.

**Lehre / Regel:** Fuer zeitpunktgebundene Beine ist Verfuegbarkeit Teil der
Strategie. Ein ORB-Ergebnis ohne Blick auf Standby-Luecken ist nicht lesbar.
siehe Memory: `standby_watchdog_schlaeft_mit`

## 4. Neues Wissen diese Woche (Papers/Ideen)

- **Zarattini/Aziz/Barbon "Beat the Market", Folgerunden:** (a) Das Paper
  behauptet ein robustes Intraday-Momentum am Rand einer Noise Area (SPY,
  hohes Sharpe). (b) Wir haben den Tresor-Bruch zerlegt (Gewinner schrumpfen
  um ein Drittel, Verlierer bleiben), ein Regime-2026-Raster gerechnet und Oel
  als Filter getestet. (c) Die IS-Gewinner auf 10/25-03/26 fallen im OOS
  durch (SP500 -5,9, NASDAQ -8,4 bps je Trade); einzig "NASDAQ K2 +
  Oel-Index-Korr. 60 T. < 0" ist in allen drei Fenstern positiv (vorbelastet,
  Tresor +10,4 % auf 100k). Fuer TTP: K60 1 % + ORB-NASDAQ 0,25 %,
  MC-Median +8,2 %/Jahr bei P(Bruch) 5 %. (d) **Forward bis 31.03.2027**, kein
  Livegang. [[zarattini-noise-area-momentum]] · siehe Memory:
  `challenge_k60_orb_gewichtung`
- **Oel als ORB-Filter (Fortsetzung der Mentor-Gegenprobe):** (a) These: Die
  Oel-Index-Beziehung erklaert, wann der ORB traegt. (b) Nur-IS-Raster und
  ein explizit an 2026 angepasstes Raster (1.524 Versuche). (c) IS-Gewinner
  "Oel gegen die Ausbruchsrichtung" verliert im Tresor (SP500 -0,68, NASDAQ
  -0,18 R je Trade); der 2026-Fit macht 2026 +39/+46 R, aber Deflated Sharpe
  ≈ 0. (d) **Beide im Forward bis 31.03.2027**, ausdruecklich kein Beleg: Ein
  Regime, das nur im Zieljahr existiert, laesst sich trivial "profitabel"
  filtern. [[orb-gegenprobe-oel]] · [[oel-als-marktregime]]
- **Mikrostruktur Runde 2 (Krohn/Mueller/Whelan JF 2024; Breedon/Ranaldo;
  Ito/Yamada Gotobi; Heston/Korajczyk/Sadka JF 2010; Boyarchenko/Larsen/Whelan
  NY Fed):** (a) Dollar-W um die Fixings, Halbstunden-Fortsetzung, Overnight
  Drift nach Abverkauf. (b) 22 Papers gescreent, 4 Kandidaten auf M1
  (FX-Majors, SP500/NASDAQ) mit gleichem Split wie Runde 1, 34 Versuche. (c)
  Alle Tresore negativ (bester K7 -0,73 bps netto); K6 kehrt sich auf
  CFDs sogar um (brutto t -2,7). (d) **Verworfen**, keine PDF (deine Vorgabe:
  nur bei positivem Tresor). [[mikrostruktur-paper-screening]]
- **Key-Level-Edge-Card (eigene Strategie, kein Paper):** (a) These aus deinem
  Trading: sichtbare Level (Vorwoche, Session, runde Zahlen, Pivots,
  Engulfing-Open) halten. (b) Stufe 1 auf 10 FX-Paaren, M1, nur IS. (c) Das
  Gegenteil: Magnet, z bis -7,8 (3.5). (d) **In Arbeit**, Stufe 2 auf der
  einen Zelle, die netto knapp traegt. [[keylevel-edge-card-final]]
- **Gold ASB IS-only (Gruppenarbeit):** (a) Unsere eigene Live-Strategie,
  diesmal sauber nach der Overfitting-Sperre. (b) 8 Stellschrauben, 20.736
  Versuche. (c) Tresor +0,04 R je Trade, DSR 0,24 (3.3). (d) **Live
  unveraendert**, Mentor-PDF steht. [[gold-asb-is-only-neuanalyse]]
- **Tresor-Check aller Live-Beine:** (a) Frage: Welche Live-Beine tragen in
  den letzten 12 Monaten noch? (b) Tresor 10/2025-09/2026 je Bein. (c)
  Negativ: orb_us30 (-16 R, pausiert) und btc_ema_cross (nur 6 Trades);
  orb_sp500 fast null; der Rest positiv. (d) Laeuft jetzt woechentlich als
  Ampel weiter. [[live-strategien-tresor-check]]
- **Makro-Faktor-Katalog aus OneNote:** 49 Faktoren, 13 Regime-Schemata, 37
  Regeln, 12 Testkandidaten, **nichts davon getestet**; Input fuer den
  Makro-Agenten. [[makro-faktoren-katalog]]

**Ideen-Inbox neu (12.-18.10.):**
- (16.10.) Automatischer Drawdown-Schalter je Live-Bein - offen, braucht
  eigenen Plan + Freigabe (echtes Geld).
- (18.10.) Dollar-W nach dem Tokio-Fix nur als Maker handelbar? - offen,
  "eher verwerfen".

## 4b. Vertiefung: Maker und Taker - warum der Spread die Praemie ist

**Was es ist:** An jedem Markt stehen zwei Rollen gegenueber. Der **Maker**
stellt Liquiditaet: Er legt eine Limit-Order ins Buch und wartet, bis
jemand sie nimmt. Der **Taker** nimmt Liquiditaet: Er handelt sofort per
Market- oder Stop-Order und zahlt dafuer den Spread (plus Kommission). Der
Spread ist der Preis fuer Sofortigkeit. Viele Mikrostruktur-Effekte (Kurs
weicht am Fixing ab und kommt zurueck, Druck nach Abverkauf) sind genau
diese Bezahlung: Jemand muss jetzt handeln, und der, der ihm die Gegenseite
stellt, verdient eine kleine Praemie.

**Beispiel mit unseren Zahlen:** Das Dollar-W nach dem Tokio-Fix bringt im IS
brutto **+1,6 bps** je Trade, hochsignifikant (t 4,8). Unser Rundturn auf
FX kostet **1,1-1,3 bps**. Als Taker bleiben also hoechstens 0,3-0,5 bps,
und schon im OOS ist der Bruttoeffekt auf +0,24 bps geschrumpft: netto
-1,6 bps. Ein Maker, der denselben Effekt mit Limit-Orders erntet, zahlt den
Spread nicht, sondern bekommt ihn. Fuer ihn waere derselbe Effekt positiv;
das Paper von Krohn et al. sagt das selbst ("positiv erst bei halbem
Spread").

**Warum es fuer unsere Bots zaehlt:** Alle unsere Bridges handeln als Taker
(Market- oder Stop-Orders). Ein Edge ist fuer uns nur erntbar, wenn er
deutlich groesser ist als ein Rundturn. Faustregel aus dieser Woche: unter
etwa **3x Kosten** gar nicht erst testen, ausser eine Limit-Order-Ausfuehrung
ist realistisch. Das gleiche Prinzip steckt hinter dem CLS-Befund (Entry-Lag
und Kosten fressen kleine Edges, siehe Memory:
`cls_practical_cost_model_and_entry_lag`).

## 5. Verbesserungen

- **Edge-Fruehwarnung mit Warnstufen** (14./16.10.): Paket `edge_monitor/`
  (6 Tests gruen), vorab registriertes Lock, Ampel ROT/GELB/gruen jetzt
  woechentlich im Report. Reine Anzeige, kein Eingriff.
- **Tresor-Check aller Live-Beine** als wiederholbares Skript
  (`scripts/research_live_tresor_check.py`).
- **Overfitting-Sperre wirkt als Routine:** Diese Woche liefen ORB-Oel,
  Noise-Area (5 Locks), Gold ASB, Key Levels, Mikrostruktur K4-K7 und die
  K60-Gewichtung durch Lock, Trial-Zaehlung und einmaliges Oeffnen.
- **Research-Stand gesichert:** Sammel-Commit `9ebdc80a` am So holt den in
  KW41 gemeldeten ungesicherten Stand (07.-18.10.) in Git.
- **Neuer Daten-Task `G8-Notion-Sync`** (taeglich 07:00, kein Order-Bezug).
- **Live, ohne Codeaenderung:** Gold ASB hat seinen ersten Stop-Order-Fill
  mit Zeit-Exit sauber durchlaufen (alle 4 Konten, gleiche Minute), und die
  NASDAQ-Storno-Regel greift wie konfiguriert.

## 6. Verschlechterungen / offene Probleme

- **Standby waehrend der Handelszeit, schlimmer als in KW41:** Mo 7 Stunden,
  Do eine Stunde genau ueber dem ORB-Fenster. Der Watchdog schlaeft weiter
  mit.
- **CTNL-Altpositionen weiter ohne Zeit-Exit:** TTP 3 Shorts (18.09., 2x
  30.09.), IQ 1973249 und FK 1973231 (02.10.) sind auch nach dieser Woche
  offen. TTP nahm deshalb wieder **keinen** neuen CTNL-Trade. Unveraendert im
  Dashboard, nichts angefasst.
- **TTP-OU: Titel "fehlen im Scan"** - neben DD/EOG (bekannt) jetzt auch
  STT, und zwar zwei Stunden nach dem eigenen Entry am 16.10.
- **Datenpfad nach dem Aufwachen:** `str`/`float`-Fehler und
  `dukascopy_python`-Haenger gehaeuft am Mo und Do (jeweils nach Standby), dazu
  IPC-Timeouts auf allen drei Funded/FK-Terminals.
- **Inhaltlich:** Drei Live-Entscheidungen stehen jetzt auf nachweislich
  schwachem Grund (ORB SP500 ROT in der Ampel, NASDAQ-Storno als 2026-Fit,
  Gold ASB verduennt). Alle bewusst so belassen (Entscheide 06./16.10.), der
  Forward muss es zeigen.

## 7. Optimierungsmoeglichkeiten

1. **Standby abstellen oder ORB davon entkoppeln:** Energieplan/Deckel
   klaeren; falls das nicht geht, ORB-Platzierung als Pending-Order schon vor
   Range-Ende vorbereiten ist keine Loesung (Range unbekannt), also bleibt nur
   Verfuegbarkeit. Zweitbeste Option: Watchdog auf ein Geraet, das nicht
   mitschlaeft.
2. **CTNL-Exit-Abgleich gegen Broker-Positionen** und die fuenf Altpositionen
   entscheiden (echtes Geld; Dashboard-Punkt seit 12.10.).
3. **Runde-2-Dateien committen** (`knowledge/_research_lock/smh_k4`-`k7`,
   `smh_microstructure/*.py`, `mikrostruktur-paper-screening.md`): Die Locks
   sind der Nachweis fuer das einmalige Oeffnen.
4. **Offene Frage aus dem Dashboard ist beantwortbar:** "Kann IQ NASDAQ
   handeln?" - Ja, die Funded-Bridge platzierte diese Woche auf IQ ORB-Orders
   auf `NAS100.gbe` (13.10. und 16.10.). Bitte so bestaetigen.
5. **Drawdown-Schalter je Bein** (Ideen-Inbox 16.10.): wenn, dann mit eigenem
   Plan; die Ampel liefert die Schwellen schon.
