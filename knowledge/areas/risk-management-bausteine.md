# Area: Risk-Management-Bausteine (optional im Backtest)

Seit 2026-11-20 (Nutzerauftrag). Anlass: Lektion 4 des Prosper-AI-Kurses „AI Day Trader
Quick Start“ (Risk Management) nennt sieben Schutzregeln. Einige davon bauen unsere
Backtests nicht standardmäßig ein. Diese Notiz hält sie als Bausteine fest.
**Seit 2026-11-20 (Nutzerentscheid) werden sie bei jedem neuen Edge in Phase 5 des
[[backtest-standard-process]] geprüft.** Ob ein Baustein danach in die Regel übernommen wird,
entscheidet das Ergebnis: Er muss in IS und OOS besser sein als pauschal weniger Risiko.
Bestehende Live-Beine bleiben unverändert. Der ORB-S&P-Kandidat (P3) wird vorerst nicht
weiterverfolgt, also auch kein Schattenlauf (Nutzer, 20.11.: „passt erstmal so“).

**Ablauf für einen neuen Edge:** Trade-Liste mit `entry_time`, `exit_time`, `r`, `daily`
(True bei Tagesdaten) bauen, dann aus `scripts/research_risk_bausteine.py` `diagnose(d)` und
`run(d, rule, ...)` für die `VARIANTS` aufrufen und `metrics()` je IS/OOS vergleichen. Die
Varianten mit `log_trials` im Lock des Edges zählen.

## Grundsatz: Bausteine schaffen keinen Edge

Eine Pause oder Risikosenkung ändert nicht den Ø R je Trade. Sie lässt Trades aus oder
macht sie kleiner. Sie hilft nur, wenn **Verluste gehäuft auftreten**, also wenn ein Trade
nach einem Verlust schlechter ist als der Durchschnitt. Ist es umgekehrt (nach SL eher
besser, so bei CTNL), schneidet die Bremse gerade die guten Trades ab.

Deshalb vor jedem Baustein einmal auf IS prüfen: Ø R der Trades nach 1, 2, 3 Verlusten in
Folge gegen den Ø R aller Trades. Liegt er nicht klar darunter, bringt eine Serienbremse
nichts.

Auf Prop-Konten (TTP, IQ, FK) geht es bei Tageslimit und Kill-Switch nicht um Rendite,
sondern ums Überleben. Dort ist das Maß P(Kontogrenze gerissen), nicht der Sharpe.

## Die Bausteine

| # | Baustein | Bei uns live? | Bisher getestet |
|---|---|---|---|
| 1 | **Tageslimit**: ab −X % Equity am Tag keine neuen Einstiege bis Tagesende | nur TTP (−3 %) | CTNL: Tages-/Wochen-Kill verworfen, alle Kennzahlen schlechter. Gesamtportfolio 2016: Brüche nur gezählt, nicht als Sperre simuliert |
| 2 | **Pause nach Verlustserie**: nach N Verlusten in Folge K Trades/Tage aussetzen | nein | CTNL: verworfen (nach SL eher bessere Trades) |
| 3 | **Risikosenkung nach Verlustserie**: nach N Verlusten Risiko × f, zurück nach Gewinn | nein | CTNL: verworfen (erst Vorgriff-Artefakt, sauber gerechnet weniger Ertrag, Sharpe gleich). ORB: ungetestet |
| 4 | **Drawdown-Kill-Switch, bleibt stehen**: ab −X % vom Hoch keine Einstiege bis Hand-Reset | Funded ja. EK prüft jeden Lauf neu und gibt Einstiege wieder frei, sobald die Equity über der Grenze liegt | Edge-Monitor 14.10.: bester Schadensbegrenzer bei Brüchen, kostet gesunde Beine Median −3,4 R |
| 5 | **Gesamtrisiko-Deckel**: Summe des offenen Risikos ≤ X % | EK (`MAX_TOTAL_RISK_PCT`), Funded über max. offene Positionen je Bein | Gesamtportfolio 2016 (`open_cap` je Konto) |
| 6 | **Positionswert-Limit**: Nominalwert je Position ≤ X % der Equity | nein (bei CFDs wenig aussagekräftig) | nein |
| 7 | **Datenprüfung**: NaN, Preis ≤ 0, Hoch < Tief, Open/Close außerhalb der Spanne → Bar verwerfen und melden | verstreut je Bein | [[vorgriff-waechter]] prüft Vorgriffe, nicht Kursplausibilität |

## Regeln für den Test

1. **Nur geschlossene Trades zählen.** Serien- und Zustandsregeln rechnen nur mit Trades,
   deren `exit_time ≤ entry_time` des neuen Trades ist. Sonst entsteht ein Vorgriff
   (CTNL-Risikohalbierung 30.09.).
2. **Tageslimit auf Equity mit offenen Positionen.** Realisierte und unrealisierte Verluste
   zählen, wie beim Broker. Bei D1-Daten ist das nur grob möglich, das im Ergebnis vermerken.
3. **Auf dem gehandelten Satz messen.** Die Bremse sieht nur die Trades, die live auch
   gehandelt werden (gefiltert), nicht die Rohstrategie (CTNL-Kill-Switch bis 30.09.).
4. **Kontrolle: pauschal kleineres Risiko.** Jeder Baustein muss besser sein als einfach
   dauerhaft weniger Risiko mit demselben Max DD. Sonst ist er nur eine teure Art, kleiner
   zu handeln.
5. **Kennzahlen:** ΣR, Ø R, Trades, Sharpe, Max DD, P(Kontogrenze 12 M) aus Monte Carlo,
   jeweils mit und ohne Baustein.
6. **Jede Parametrierung ist eine gezählte Variante** (`log_trials`) unter der
   [[overfitting-sperre]]. N, K, X auf IS wählen, nicht auf OOS suchen.
7. **Mit Ausstiegen nichts sperren.** Der Baustein blockiert nur neue Einstiege, offene
   Positionen laufen normal weiter (wie in beiden Bridges).

## Ergebnis 20.11.2026: alle Edges durchgerechnet

Skript `scripts/research_risk_bausteine.py`, Ergebnisse in
`portfolio_construction/results/risk_bausteine/`. Lock `risk_bausteine_20261120`: IS 2016–2022,
OOS 2023-01 bis 2026-05-19, Tresor zu. 69 gezählte Varianten. Trades: Live-Beine aus dem
Gesamtportfolio-Backtest (TTP-Kosten, `gold_silver`/`btc_ema_cross` aus EK), H4-Spike = Signal-Hub-Alarm
(Q & A, 3R + BE nach 1R), Daily = eingefrorener C2 (`c2_kandidat_trades.csv`, TTP-Swap).

Varianten: P2/P3 = nach 2/3 Verlusten die nächsten 3 Signale auslassen; H2/H3 = Risiko halbieren ab
2/3 Verlusten bis zum nächsten Gewinn; T1R/T2R = Tageslimit je Bein −1/−2 R; TTP-Konto-Tageslimit 1/2/3 %.

**Diagnose: Bei fast allen Beinen sind Trades nach Verlusten gleich gut oder besser.** CLS, CTNL,
Gold ASB (nach 1–2), Trend Pullback, OU, C2 (nach 1–2): Ø R nach Verlust ≥ Durchschnitt. Eine
Serienbremse schneidet dort die Erholung ab. Ausnahmen nur im IS: ORB S&P fällt stetig (0,36 → 0,13 R
nach 3 Verlusten), ORB NASDAQ und Gold ASB nach 3 Verlusten. Im OOS bestätigt sich das nicht klar.

| Bein | Ergebnis |
|---|---|
| **ORB S&P** | **P3 einziger Kandidat**: Sharpe IS 0,85 → 0,91, OOS 1,07 → 1,32; Ø R OOS 0,44 → 0,71; ΣR OOS 67,8 → 72,2; Max DD OOS −17,8 → −13,6 R; lässt ~⅓ der Trades aus. Bei 69 Varianten kann das Zufall sein. Live nur über Forward-Schattenlauf ([[overfitting-sperre]] Punkt 5) |
| CTNL | Halbierung (H2/H3): Rendite/DD besser, Sharpe nicht (1,25 → 1,22; 2,22 → 2,03). Wirkt wie pauschal kleineres Risiko, bestätigt 30.09. |
| ORB NASDAQ | H3 IS Sharpe 0,51 → 0,62, OOS 0,39 → 0,34. Kein Kandidat |
| CLS, Gold ASB, Gold/Silber, OU, Trend Pullback, BTC | Alle Bausteine gleich oder schlechter (in IS und OOS nicht gleichzeitig besser) |
| Daily C2 | Pause/Halbierung schaden; T1R nur OOS besser (IS schlechter). Kein Kandidat |
| H4-Spike | Basis negativ (IS −0,05, OOS −0,19 R); Bausteine verkleinern nur Verluste, kein Edge |
| Tageslimit je Bein | Fast wirkungslos: kaum ein Bein hat mehrere Trades am selben Tag |
| TTP-Konto-Tageslimit | Greift nie: schlechtester realisierter Tag −0,95 % (IS) / −0,84 % (OOS). Nur realisierte Verluste gemessen, offene Positionen fehlen |

Nicht gerechnet: der bleibende Kill-Switch (Baustein 4) und die Datenprüfung (7). Beide ändern keine
Trade-Liste, sondern schützen den Betrieb.

Quellen: Memory `ctnl_serienstopp_vs_risikohalbierung.md`, `edge_kipp_nicht_vorhersagbar.md`,
`gesamtportfolio_backtest_2016.md`; [[ctnl-kostenvalidierung]] Befund 19;
[[challenge-portfolio-ttp-icapital]]; [[prosper-bot-trendregel-echtdaten]].
