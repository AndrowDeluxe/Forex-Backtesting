# Weekly Checkup - Education - KW39/2026

> **Zwischeneintrag von Hand, 2026-09-23 (Mittwoch).** Auf Nutzerwunsch
> vorgezogen, weil die Paper-Auswertung nicht bis Sonntag warten soll.
> Der geplante `Forex-Weekly-Report`-Lauf am Sonntagabend erzeugt diese
> Datei neu und ersetzt damit diesen Eintrag -- der Inhalt geht dabei
> **nicht** verloren: die Quellen, aus denen der Report Abschnitt 3 und 4
> baut, sind beide gesetzt (Memory-Eintrag `us_cash_session_hat_keine_risikopraemie`
> und die committeten PARA-Notizen in `1fc8645`). Abschnitte 1, 2, 5-7
> bleiben hier leer, weil die Woche noch laeuft.

## 3. Meine Main Erkenntnisse

**In unserem ORB-Handelsfenster gibt es gar keine Risikopraemie zu ernten --
und das ist eine gute Nachricht.** Bondarenko/Muravyev (SSRN 3596245,
E-mini-S&P-Futures 2004-2018) zeigen, dass die US-Cash-Session 09:30-16:15 ET
im Mittel nur +3,44 % p.a. bei **t=0,89** liefert (Sharpe 0,23, MaxDD 44,6 %).
Die gesamte durchschnittliche Aktienmarktrendite entsteht stattdessen in vier
Nachtstunden, 23:30-03:30 ET.

Warum das wichtig ist: Der Standardeinwand gegen eine long-only-Aktienstrategie
lautet "du erntest doch nur die Marktrendite". Fuer unseren
[[ny-open-orb-sp500]] **stimmt dieser Einwand nachweislich nicht** -- in dem
Fenster, in dem wir long-only sind, ist schlicht keine Drift vorhanden. Der
Stage-4b-Befund (long-only Sharpe 0,56 -> 0,81) wird dadurch nicht
relativiert, sondern gestaerkt: der Vorteil muss konditional sein, weil
unkonditional nichts da ist.

**Der ORB hat nach fast zwei Monaten Arbeit immer noch keinen dokumentierten
Mechanismus.** Das ist mir erst bei dieser Sichtung aufgefallen. Der
EMA-neutral-Filter ist das mit Abstand staerkste bestaetigte Signal des
Projekts (Sharpe 0,56 -> 1,05) und steht auf reiner Backtest-Evidenz --
[[edge-card-workflow]] Regel 4 sagt dazu ausdruecklich: "Ein Backtest ist KEIN
Mechanismus." Kinoshita liefert nun einen Kandidaten (US-Indizes sagen ihren
eigenen Opening-Gap zu 52,8-56,0 % aus dem Vortagsmomentum vorher; der Filter
koennte genau die Tage waehlen, an denen dieser Prior am schwaechsten ist).
**Das ist eine Hypothese, kein Befund** -- aber eine mit vorhandenen Daten
falsifizierbare.

**Ein "dieser Filter ist offensichtlich sinnvoll"-Reflex wurde teuer
widerlegt -- bei jemand anderem.** Kinoshitas Leg Europa -> New York sah
zunaechst nach 72 % Directional Accuracy aus. Erst die Kontrolle auf das
Eigenmomentum des Zielmarkts liess ihn auf **+0,07 Punkte** zusammenfallen;
die reine Vorzeichenregel erreicht dort **48,89 %, also unter Zufall**.
Ursache war eine Scheinkorrelation (europaeische Handelszeit ueberlappt mit
der Zeit NACH dem NY-Open). Lehre fuer uns: **wer einen Cross-Market-Filter
misst, muss gegen Eigenmomentum kontrollieren**, sonst misst er sich selbst.

**Parallele Sessions ueberschreiben weiterhin `knowledge/`.** Zwei am 22.09.
geschriebene Eintraege (DASHBOARD-Rueckfrage, ORB-Abschnitt) waren am 23.09.
spurlos verschwunden, ueberschrieben durch Commit `1fc8645` einer anderen
Session. Wiederhergestellt. Das ist bereits der dokumentierte Fall aus
Memory `parallele_sessions_ueberschreiben_knowledge` -- er ist also **nicht
behoben**, und die dort notierte Gegenmassnahme (nach dem Eintrag per grep
verifizieren) hat diesmal funktioniert, weil ich sie ein zweites Mal
ausgefuehrt habe. Einmal pruefen reicht offenbar nicht, wenn zwischen
Schreiben und Weiterarbeiten Stunden liegen.

## 4. Neues Wissen diese Woche (Papers/Ideen)

**Drei externe Papers vom Nutzer geteilt (2026-09-22), zwei neue PARA-Notizen.**
Die Sichtung lief nach [[backtest-standard-process]] Phase 2 + 3
(Sichtung/Screening) -- **kein Code, kein Backtest, kein Eingriff in einen
laufenden Bot**. Bewusste Prozess-Abgrenzung: Papers laufen laut `CLAUDE.md`
NICHT durch den [[edge-card-workflow]]; dessen Brille wurde stattdessen auf
den ORB gelegt, der als haendisch entwickelte Nutzer-Strategie
dorthin gehoert.

- [[24h-renditestruktur-und-informationskette]] (09-22) -- Destillat aller
  drei Papers. Kerngedanke: New York **produziert** Information (Kinoshita)
  und **erntet keine Risikopraemie** (Bondarenko/Muravyev); Europa erntet die
  Praemie und produziert keine Information fuer NY. Zwei Aussagen ueber
  dasselbe Fenster, beide fuer uns relevant.
- [[eu-open-renditefenster]] (09-22, Status **Kandidat, nicht begonnen**) --
  neuer separater Edge-Kandidat: long Index 05:30-09:30 Berlin. Sharpe 1,67,
  in jedem der 15 Paper-Jahre positiv, MaxDD 8 %, besteht White-Reality-Check
  und Bonferroni, kausal ueber die Sommerzeit-Asymmetrie auf Europas Open
  eingegrenzt. Kollidiert zeitlich nicht mit dem ORB.

**Was NICHT uebernommen wurde, und warum** (gehoert hier genauso hin wie die
Funde):

- **Richtungsfilter aus Europa/Asien fuer den NY-Open: vor dem Bau
  verworfen.** Siehe oben -- der Leg ist tot, und zwar spezifisch der Weg
  nach New York hinein, waehrend alle anderen Legs +10,6 bis +15,0 Punkte
  tragen. Ein sauber begruendeter Nicht-Bau ist hier ein Ergebnis, kein
  verpasster Test.
- **Delta-VIX als ORB-Tagesfilter: nicht weiterverfolgt**, obwohl wir bisher
  nur den VIX-*Level* getestet haben und das Paper zeigt, dass die
  *Aenderung* viel staerker ist (t=4,1 vs. t=1,2). Grund: das gilt fuer die
  Vorhersage des Nachtfensters. Fuer das einzige US-Session-Muster, das das
  Paper testet, ist Delta-VIX **insignifikant (t=0,5)**.
- **Das Beta-Law** (Kinoshita, SSRN 7091018): braucht einen Sektoren-
  Querschnitt innerhalb eines Marktes. Wir handeln drei Indizes, und das
  Paper zeigt selbst, dass die Beziehung **auf Index-/Laenderebene versagt**
  (n=9, p=0,21). Nicht anwendbar.

**Ideen-Inbox**: kein neuer Eintrag aus dieser Sichtung -- die beiden
verwertbaren Straenge sind direkt als PARA-Notiz bzw. als
Dashboard-Rueckfrage gelandet, statt in der Inbox zu parken.

## Offener Punkt zur Report-Automatik

**Fuer KW38/2026 existiert kein Education- und kein Performance-Report**,
obwohl `scripts/reports/mt5_2026-W38.json` da ist -- der Datenabzug lief also,
der Report nicht. Nicht untersucht, hier nur festgehalten, damit es nicht
unbemerkt bleibt.
