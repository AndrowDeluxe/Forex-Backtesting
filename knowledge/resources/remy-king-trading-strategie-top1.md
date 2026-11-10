# E-Book „Trading Strategie der Top 1 %" (Remy King / NGT, 2024)

## Capture

- Autor/Jahr: Remy King, „Next Generation Traders", ©2024, 90 Seiten, deutsch.
- Quelle: PDF, vom Nutzer am 09.11.2026 im Chat geteilt.
- Weg: manuell im Chat. Kein Paper, sondern ein Marketing-E-Book mit einem
  Discord-Trichter. Es enthält keine einzige Statistik, keine Trefferquote,
  keine Equity-Kurve und keinen Verlust-Trade.

## Organize

- Thema/Tags: Makro-FX, Zinsdifferenz, Konsens-Überraschung, Carry, Rohstoff-
  Währungen, SMC (FVG, Order Block, Liquidity Grab), Risiko je Trade.
- Verwandte Notizen: [[makro-wirkketten-und-regeln]] (die SMT-Regeln sind
  strenger und genauer), [[regime-bestimmung-und-filter]] (Schicht „FX
  relativ"), [[filter-gold-zinskurve]], [[bond-yield-spread-indikator]] (Zins-
  Spread V1 ohne Edge), [[monetary-policy-spillover]],
  [[makro-faktoren-katalog]], [[keylevel-edge-card-final]] (S/R widerlegt),
  [[htf-daily-trade-edge-card]] (FVG/POI noch nicht regelbasiert),
  [[oel-als-marktregime]].
- Projekt: [[quant-diskretionaer-fusion]], Strang Makro-Agent.

## Distill

**Kernthese:** Die Richtung kommt aus der Fundamentalanalyse (Zinsen,
Inflation, Wachstum relativ zwischen zwei Ländern, gemessen gegen Konsens und
Pricing). Einstieg, Stop und Ziel kommen aus einfacher Chartanalyse. Den Kern
der Recherche bilden gelesene Bankreports (Bloomberg, ING).

### Faktencheck

| Aussage im Buch | Befund |
|---|---|
| FX-Tagesvolumen „über 6 Bio. $" | Stimmt, ist aber veraltet. BIS 2022: 7,5 Bio., BIS 2025: ca. 9,6 Bio. |
| Lot, Hebel, Spread, Pip-Rechnung, Reihenfolge der Kürzel | Stimmt. Ein Pip ist aber nicht mehr die „kleinste Einheit": Quotiert wird fünfstellig, das zeigt der eigene Screenshot (0,6 Pip). |
| SNB senkte am 21.03.2024 überraschend von 1,75 auf 1,50 % | Stimmt, ebenso die Senkung im Juni auf 1,25 %. |
| EZB senkte am 06.06.2024 von 4,50 auf 4,25 %, EURGBP stieg danach | Der Hauptrefi-Satz stimmt. Der Einlagensatz ging von 4,00 auf 3,75 %. Es ist eine einzige Anekdote. |
| NFP 07.06.2024: 272k gegen erwartet 182k; US-CPI 11.07.2024: −0,1 % gegen 0,1 % | Stimmt. |
| AU-CPI 24.04.2024: 3,6 % gegen 3,4 %; UK-CPI 14.02.2024: 4,0 % gegen 4,1 % | Stimmt. |
| „UK in Rezession" ließ GBPUSD über Wochen fallen (S. 36) | **Rückschau-Fehler.** Der markierte Rückgang lief von Juli bis Oktober 2023. Die Rezessionszahlen kamen erst am 22.12.2023 und am 15.02.2024. Danach fiel GBPUSD nicht weiter. |
| USDJPY 2023 stieg, weil die US-Wirtschaft boomte und „der USD sich stärkte" | Nur halb richtig. Der DXY fiel 2023 um etwa 2 %. Treiber war die Zinsdifferenz zum Yen (BoJ mit Kurvensteuerung). |
| „Inflation stieg auf fast 10 %" | Der Gesamt-CPI lag bei 9,1 % (06/2022). Das Buch zeigt aber den Kern-CPI, der bei etwa 6,6 % gipfelte. |
| Leitzins = Satz, zu dem Banken bei der Zentralbank leihen | Ungenau. Die Fed Funds Rate ist ein Interbankensatz. Bei der Notenbank leiht man zum Diskontsatz. |
| Bund 10J 1,7 % gegen Gilt „nur" 3,2 % (S. 75) | Die Zahlen sind falsch (2024: etwa 2,5 % gegen 4,1 %) und das „nur" ist verdreht. Die Richtungslogik stimmt aber: Die Differenz spricht für GBP. |
| Niedrige Inflation ist schlecht für die Währung (CHF) | Zu grob. Niedrige Inflation heißt höhere Realzinsen, und der CHF war jahrelang trotzdem stark. |
| Gold ist negativ mit USD/Zinsen korreliert | Stimmt über lange Zeit. 2022–24 brach der Zusammenhang aber: Gold stieg trotz hoher Realzinsen, wegen der Käufe der Notenbanken. |
| 60–75 % des Handels laufen über Algorithmen | Plausible Größenordnung, ohne Quelle. |
| RBA-Fall (ING erwartete eine Erhöhung am 06.08.2024) | Die RBA hielt still. Das Buch erwähnt das nicht. |
| Eigene Erfolgsbilanz (siebenstelliges AuM, Bestenlisten) | Im Buch nicht belegt. Alle 8 Fallbeispiele sind Gewinner und wurden im Nachhinein ausgewählt. |
| Innere Widersprüche | „TA niemals für den Bias" und „TA ist wie Sternbilder erkennen", trotzdem lehrt das Buch FVG/Order Block ohne jeden Beleg. Der Trendumkehr-Fall verlangt einen BOS, bevor gehandelt wird. Damit bestimmt TA doch die Richtung mit. |

**Unterm Strich:** Die Grundlagen und Makrozusammenhänge sind lehrbuchartig
und größtenteils richtig. Die Kausalbeispiele sind im Nachhinein ausgewählt.
Ein Edge ist nicht belegt.

### Vier-Fragen-Check (nur Hypothesen, noch keine IS-Daten)

1. **Warum verdient es Geld?** Weil sich die Zins- und
   Wachstumsdifferenz langsamer im Kurs niederschlägt, als die Daten sie
   verschieben. Dazu kommt Carry.
2. **Wo verliert es am meisten?** Wenn die These schon eingepreist ist (das
   Buch nennt das selbst), bei Risk-off (Carry-Crash) und bei Einstiegen gegen
   einen laufenden Trend.
3. **Was ist dort anders?** Das Pricing ist schon extrem, die Turbulenz ist
   hoch, und Positionierung und Trend stehen gegen die These.
4. **Welche eine Regel könnte helfen?** Nur handeln, wenn sich die
   Zinsdifferenz *in den letzten 5–20 Tagen* in Thesenrichtung bewegt hat. Der
   Stand allein reicht nicht (vgl. SMT-Regel „Wochenveränderung ist das
   Signal"). Das ist eine gezählte Variante unter [[overfitting-sperre]].

### Abgleich mit dem, was wir schon getestet haben

| Buch-Baustein | Unser Stand |
|---|---|
| Bankreports lesen und der Richtung folgen (der eigentliche „Edge" des Buchs) | **Widerlegt** im direkten Analogon: SMH-Reports, Markteinstieg in Report-Richtung −0,03 R (n 604). Nur mit Rücksetzer-Limit +0,06 R (p 0,06) und bei 5 Sternen / Gold besser (Hypothesen). |
| S/R an runden Zahlen „halten" | **Widerlegt.** Key Levels wirken als Magnet statt als Wand (z −4,5…−7,8, 482 Versuche). |
| Liquidity Grab → Umkehr | Indirekt widerlegt. Nach einer Berührung wird eher durchstoßen. Doppel-BOS am Level 0/240. |
| Trendumkehr per BOS | Doppel-BOS ohne Effekt, `london-range-bos-retest` archiviert. |
| Trend-Pullback: Limit auf 50 % des letzten Swings, Stop unter dem letzten Tief, Ziel am letzten Hoch | Gibt es schon (Haupt-Bot trend_pullback, Typ C mit Limit 50 %). Kein neuer Baustein. |
| Range-Ausbruch + Retest | Gibt es als ORB/ASB. Den Retest-Einstieg statt Stop-Einstieg haben wir noch nicht getestet. |
| Fair Value Gap / Order Block | **Nicht getestet.** In [[htf-daily-trade-edge-card]] als POI vorgesehen, aber noch nicht regelbasiert. |
| Zinsdifferenz als Treiber | V1 mit Monats-10J ohne Edge (Trefferquote 48–51 %). Täglicher 2J-Loader ist in Arbeit (Handoff 08.11.). |
| „Eingepreist / buy the rumour" | Schon schärfer in [[makro-wirkketten-und-regeln]] (≥ 75 %-Regel). Der CB-Event-Fenster-Dummy fiel bei Gold ASB durch (p 0,42–0,62). |
| Gold gegen USD/Zinsen | Getestet: Die geglättete Zinskurve hilft bei Gold-Continuation ([[filter-gold-zinskurve]]). Die rohe 10J-Rendite als Filter war instabil. |
| G8-/Währungsstärke | Nachgebaut, als Signal negativ, nur Kontext. |
| 1 % Risiko je Trade, ein Trade pro These | Deckt sich mit unserem Vorgehen. Ein **Währungs-Netto-Exposure-Deckel über alle Beine** fehlt live aber bislang (nur in der CTNL-Sim gibt es einen Deckel). |
| Mehr Risiko bei hoher Überzeugung | Vorsicht. Einziger Hinweis aus SMH: 5 Sterne +0,20 R, 3–4 Sterne negativ (n klein, Hypothese). |

## Express: Filter und Anwendungen

Für alle Punkte gilt [[overfitting-sperre]]: Split registrieren, nur IS,
Varianten zählen.

### A. Direkt als eigenständiger Edge testbar (mit Literaturrückhalt)

1. **Zinsdifferenz-„Fair Value"-Lücke** (S. 75–77). Den Paar-Kurs per
   rollierender Regression auf die 2J-Differenz abbilden. Gehandelt wird, wenn
   das Residuum > k·σ ist UND sich die Differenz frisch bewegt hat; Ziel ist
   die Rückkehr zum Fair Value. Daten: Der 2J-Loader (EZB/MoF/BoC/BoE) muss
   fertig sein. Erwartung: Gleichzeitig ist der Zusammenhang stark, als
   Vorhersage schwach. Das Buch sagt selbst, dass Algos solche Lücken schnell
   schließen.
2. **Carry-Korb** (NZDCHF-Fall). Long die 2–3 G8-Währungen mit dem höchsten
   Zins, short die mit dem niedrigsten. Bei hoher FX-Turbulenz wird das Risiko
   halbiert ([[regime-bestimmung-und-filter]] sagt, das verbessert Carry).
   Literatur: Carry-Prämie mit Crash-Risiko (Lustig/Verdelhan). Für uns
   entscheidend sind die **echten Broker-Swaps** (TTP/Tickmill) statt der
   Leitzinsdifferenz. Die Swap-Abschläge können die Prämie auffressen.
3. **Drift nach einer Konsens-Überraschung** (NFP-Fall S. 37–38: „auch nach
   der Veröffentlichung noch shorten"). Einstieg 1–4 h nach dem Release in
   Richtung der Überraschung (Ist − Konsens, standardisiert). Die Literatur
   findet meist einen sofortigen Sprung ohne lange Drift. Blocker: Kalender
   mit Konsens (FMP-Free sperrt das; das `fxmacrodata-calendar`-Skill oder ein
   eigener Scraper wären zu prüfen).

### B. Als Baustein/Filter integrierbar (Veto oder Größe, kein Einstieg)

4. **Währungs-Netto-Exposure-Deckel** über alle Beine und Bridges (S. 69,
   „ein Trade pro Sichtweise"). Zum Beispiel höchstens 2 R Netto-USD. Das ist
   reine Risikologik, kein Edge-Test nötig. Prüfen lässt sich aber, wie oft
   die Beine heute gleichzeitig dieselbe Währung tragen.
5. **Differenz-Veto für FX-Beine**: kein Long in einer Währung, deren
   2J-Differenz in 20 Tagen klar gegen die Position gelaufen ist. Das ist die
   Schicht „FX relativ" aus dem Schichtenmodell. Testen ohne/mit/gegen an
   CTNL-FX und Daily-Edge.
6. **Rohstoff-Veto für Rohstoffwährungen**: kein AUD-Long bei fallendem
   Kupfer (20-Tage-Trend), kein CAD-Long bei fallendem Öl, NZD/Milch (GDT).
   Literatur (Chen/Rogoff; Ferraro/Rogoff/Rossi): gleichzeitig ja, Vorlauf
   kaum. Deshalb nur als Veto, nicht als Lead-Lag-Einstieg.
7. **Notenbank-Pricing-Gate**: ist der nächste Schritt zu ≥ 75 % eingepreist,
   gibt es keinen „These"-Trade auf diesen Termin. Schon Regel bei SMT; hier
   nur bestätigt. Blocker: OIS-Daten sind kostenpflichtig.
8. **Risk-off-Schicht**: Bei hoher Turbulenz steigen CHF/JPY (und USD). Als
   Größen-Faktor gibt es das schon im Schichtenmodell.

### C. Einstiegs-Bausteine (TA), noch offen

9. **FVG mechanisch** (3-Kerzen-Lücke: Hoch₁ < Tief₃ bzw. Tief₁ > Hoch₃).
   Wird die Lücke häufiger als bei Schein-Lücken nur bis zur Mitte gefüllt und
   danach in Lückenrichtung verlassen? Gleiches Prüfdesign wie bei den Key
   Levels (gegen Schein-Level). Danach als POI-Baustein in die Daily-Edge Card.
10. **Order Block** = letzte Gegenkerze bzw. enge Range vor einem Impuls ≥ x
    ATR. Prüfung wie bei 9. Achtung: Das „Magnet"-Ergebnis spricht eher für
    ein Durchstoßen.
11. **Ausbruch → Retest-Limit** statt Stop-Einstieg bei ORB/ASB, als
    gezählte Variante. Die Einstiege laufen ohnehin schon zu 58–65 % in der
    ersten Bar ([[ny-open-orb-sp500]]).

### Verworfen / nicht übernehmen

- Den Bias aus Bankreports übernehmen: im SMH-Test ohne Edge.
- S/R-Abpraller und Liquidity-Grab-Fade: widerlegt.
- Größe je „Überzeugung" ohne Maß: nur mit einem messbaren Überzeugungs-Score
  (z. B. Zahl zustimmender Schichten), so wie im Schichtenmodell schon
  vorgesehen.

## Test-Ergebnisse (10.11.2026, nur IS)

Alle drei Kandidaten unter [[overfitting-sperre]], Splits vorab registriert
(`knowledge/_research_lock/remy_a*.json`), OOS/Tresor **versiegelt**. Daten:
Zins-Langhistorie ab 2003 in `data_cache/remy/rates_history.parquet`
(`scripts/remy_rates_history.py`: BIS-Leitzinsen, FRED, EZB, MoF, BoC, BoE-GLC);
JP-Leitzins vor 03/2006 = 0,0 gesetzt (BIS-Lücke, Mengensteuerung).

### A2 Carry-Korb → **Baustein „Carry-Signal"** (Nutzer 10.11.: festhalten für Kombinationen)

`scripts/research_remy_a2_carry.py`, IS 2003–2016, 6 Varianten. Monatsende nach
Leitzins sortieren, long Top-k / short Bottom-k, Kurs + Zinsdifferenz − 1 % p.a.
Swap-Aufschlag − Spread.

| Variante | Rendite p.a. | Vol p.a. | Sharpe | t | MaxDD | Schiefe |
|---|---|---|---|---|---|---|
| k=1, Risk-off an | 5,0 % | 10,7 % | **0,47** | 1,75 | −19 % | −1,0 |
| k=1, Risk-off aus | 5,0 % | 14,0 % | 0,36 | 1,35 | −27 % | −2,4 |
| k=2, Risk-off an | 3,5 % | 8,5 % | 0,41 | 1,53 | −22 % | −0,5 |
| k=3 | ≈ 0 | | 0,03–0,10 | | | |

- DSR 0,81, aber t 1,75 < 2 → nach dem vorab gesetzten Kriterium **kein
  eigenständiger Edge**; OOS bewusst nicht geöffnet.
- Inhalt: praktisch AUD/NZD long gegen JPY (CHF) short. Schlechteste IS-Jahre
  2008 (−6 %), 2015, 2007. Risk-off (halbe Größe bei VIX-Vortag > 21,2 = IS-p75)
  halbiert die Schiefe und verbessert jede Variante.
- **Warum Baustein statt Verwerfung:** Die Prämie ist positiv, breit literatur-
  gestützt und nahezu unabhängig von unseren Intraday-Beinen. Zu schwach allein,
  aber als **Richtungs-/Größenschicht** kombinierbar, z. B.: Daily-Edge/Typ R
  nur in Carry-Richtung, Carry × Regimekarte (Risk-on), Carry × COT-Extrem,
  Carry × Zinskurven-Schicht aus dem Schichtenmodell ([[regime-bestimmung-und-filter]]).
- **Regel für die Kombination:** Jede Kombination ist eine weitere gezählte
  Variante im Lock `remy_a2_carry` (Trials steigen → DSR strenger). Erst die
  fertige Kombination einfrieren, dann OOS einmal öffnen.
- Wiederverwendbar: `month_end_weights(pr, k)` liefert die Monatsgewichte je
  Währung (+1/k long, −1/k short, Abstand < 0,25 Pp → flat).

#### Carry-Kombinationen K1–K4 (10.11.2026, IS + OOS nach neuer Regel)

`scripts/research_remy_carry_combos.py`. Neue Sperr-Regel (OOS frei, Tresor 6 Monate,
siehe [[overfitting-sperre]]); Lock-Grenze OOS/Tresor auf 09.05.2026 verschoben.
OOS = 2017-01-01 … 2026-05-09. Versuche im Lock: 14.

| Variante | aktiv (IS) | IS Rend. p.a. | IS Sharpe | IS t | IS DSR | OOS Rend. p.a. | OOS Sharpe | OOS MaxDD |
|---|---|---|---|---|---|---|---|---|
| Carry Basis (k=1, Risk-off) | 100 % | 5 % | 0,47 | 1,75 | 0,87 | −1 % | **−0,18** | −28 % |
| K2 Wachstum fällt → halb | 93 % | 4 % | 0,44 | 1,65 | 0,84 | −1 % | −0,19 | −29 % |
| K2 Wachstum fällt → flat | 93 % | 4 % | 0,40 | 1,49 | 0,80 | −1 % | −0,21 | −30 % |
| K3 COT überfüllt → halb | 72 % | 6 % | 0,60 | 2,24 | 0,94 | −1 % | −0,18 | −24 % |
| **K3 COT überfüllt → flat** | 72 % | 6 % | **0,69** | **2,60** | 0,97 | −1 % | −0,17 | **−21 %** |
| K4 Deflation → halb | 88 % | 5 % | 0,51 | 1,93 | 0,90 | −1 % | −0,17 | −29 % |
| K4 Deflation → flat | 88 % | 5 % | 0,54 | 2,05 | 0,92 | −1 % | −0,16 | −29 % |

- **Carry selbst kippt im OOS** (Sharpe 0,47 → −0,18). Schwerstes Jahr 2022 (−11,6 %,
  Zinswende: NZD long fiel mit), bestes 2023 (+11,8 %). Deckt sich mit der Literatur:
  G10-Carry war nach 2008 rund ein Jahrzehnt flach bis negativ.
- **COT-Filter (K3)** ist der einzige Zusatz, der IS deutlich hebt (t 1,75 → 2,60,
  DSR 0,97) und im OOS den Drawdown senkt (−28 → −21 %), aber das OOS bleibt negativ.
  Hilft gegen Crashs (überfüllte Carry-Trades), schafft keine Prämie.
- **Regimekarte (K2)** schadet leicht; **Zinskurve (K4)** hilft minimal (IS t 2,05, OOS −0,16).
- Kombinationen K2–K4 untereinander noch nicht getestet.

| K1 Daily-Edge Typ R (E2 S1 alle X4), FX | IS n | IS Ø R | IS t | OOS n | OOS Ø R | OOS t |
|---|---|---|---|---|---|---|
| Typ R alle | 615 | −0,13 | −2,58 | 432 | +0,08 | 1,15 |
| nur Carry-Richtung | 259 | −0,15 | −1,98 | 131 | **+0,21** | 1,39 |
| ohne Gegen-Carry | 389 | −0,19 | −3,11 | 281 | +0,11 | 1,15 |
| nur Gegen-Carry | 226 | −0,03 | −0,33 | 151 | +0,04 | 0,36 |

- Typ R ist 2004–2016 klar negativ. Im OOS liegt der Carry-Richtungs-Filter vorn
  (+0,21 R gegen +0,04 R gegen Carry), im IS nicht → kein stabiler Zusammenhang.
- Achtung: Typ R wurde auf 2016–2021 ausgewählt, das liegt in diesem OOS
  (Kontamination, OOS von K1 ist zu optimistisch).

**Fazit Carry-Baustein:** Als eigenständige Prämie seit 2017 nicht vorhanden; der
COT-Crowding-Filter ist der wertvollste Teil (Crash-Schutz). Weiter verwendbar als
Risiko-/Veto-Schicht („keinen Trade in einen überfüllten Carry-Trade“), nicht als
Richtungsgeber.

### A1 Zinsdifferenz-Fair-Value → verworfen

`scripts/research_remy_a1_fairvalue.py`, IS 2005–2018, 4 Paare, 9 Varianten.
Beste (|z| ≥ 1,5, 10 Tage): 390 Trades, Ø +12,9 bp, Sharpe 0,28, t 1,08,
DSR 0,54. Längere Haltedauer/höhere Schwelle durchgehend schlechter, ein Tag
Verzögerung → Sharpe 0,06. Schlechteste Jahre 2013/14 (Abenomics, USD-Rally:
Kurs löst sich monatelang vom Zins-Fair-Value). Deckt sich mit
[[bond-yield-spread-indikator]] (V1 ohne Edge).

### A3 Konsens-Überraschung → läuft

ForexFactory-Wochenhistorie ab 2007 (Ist/Konsens/Vorwert, `scripts/remy_ff_history.py`
→ `data_cache/remy/ff_calendar.parquet`), H1 ab 2007 von Dukascopy. Test:
`scripts/research_remy_a3_surprise.py`.

## Status

10.11.2026: A1 verworfen, A2 als Baustein festgehalten, A3 läuft.
Ursprüngliche Planung (09.11.2026): Die Reihenfolge, wenn der Nutzer zustimmt:
zuerst 4 (Exposure-Deckel, ohne Test machbar), dann 1/2/5 (warten auf den
2J-Loader), dann 9 (FVG, mit vorhandenen Daten sofort testbar).
