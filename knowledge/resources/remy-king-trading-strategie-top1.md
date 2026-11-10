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

## Status

Nichts getestet (09.11.2026). Die Reihenfolge, wenn der Nutzer zustimmt:
zuerst 4 (Exposure-Deckel, ohne Test machbar), dann 1/2/5 (warten auf den
2J-Loader), dann 9 (FVG, mit vorhandenen Daten sofort testbar).
