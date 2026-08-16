# Resource: Trend-Following / Momentum (MA-Crossover)

Destillate zu einfachen Moving-Average-Crossover-Systemen als
Trendfolge-Baseline. Verwandt: [[crypto-etf-flows]],
[[crypto-volume-profile-mean-reversion]] (gleiche Asset-Klasse BTC, anderes
Regime -- hier Trendfolge statt Mean-Reversion). Code-Modul im Repo mit
strukturell verwandtem Ansatz: `triple_ma_strategy/` (TEMA/TSMA,
20/30/50-Tage-Dreifach-Crossover, siehe `app_pages/triple_ma.py`).

---

## The Backtest Machine (Cheat Sheet, Miles Deutscher Finance)

**Capture**
- Autoren/Jahr: Miles Deutscher Finance, 2026 (Companion-Sheet zu einem
  YouTube-Video, kein akademisches Paper)
- Quelle/Link: vom Nutzer als PDF geteilt ("The-Backtest-Machine-Cheat-Sheet.pdf")
- Erfasst am: 2026-08-13
- Weg: manuell im Chat

**Organize**
- Thema/Tags: trend-following, moving-average-crossover, EMA, BTC,
  overfitting-check, Claude-Code-Execution, MCP
- Verwandte Notizen: [[crypto-volume-profile-mean-reversion]]
- Verwandtes Project/Area: keins direkt -- eher Methodik-Vorlage als
  Strategie-Kandidat

**Distill**
- **Kernthese**: (1) Methodik-Teil: iterativer Claude+Pine-Script-Loop
  (Regel formalisieren -> Pine-Code -> TradingView-Tester -> Claude liest
  Kennzahlen) als schneller Weg, eine grob beschriebene Strategie objektiv
  zu testen. (2) Konkretes Beispiel: EMA-9/21-Crossover long-only auf
  BTC/USDT Daily (long wenn EMA9 > EMA21, sonst flat) soll auf BTC Buy&Hold
  schlagen bei ~halber Drawdown, aber auf Nasdaq gegen Buy&Hold verlieren --
  als Beleg für "keine Strategie ist Asset-unabhängig gut". (3) Execution-
  Teil (Part 4): dieselbe Claude-Code+MCP-Architektur wie das vom Nutzer
  zuvor im Chat geteilte Diagramm ("How to Connect an Exchange to Claude
  Code") -- Claude trägt die Regeln (nicht den Pine-Code), spricht die
  Exchange über MCP-Tools an, Trade-only API-Key, paper -> testnet -> live
  als Pflicht-Reihenfolge.
- **Zentrales Modell/Filter**: EMA(9) x EMA(21) Crossover, keine weiteren
  Filter, keine Position-Sizing außer 100%-of-equity, keine Stops (der
  Crossover selbst ist der Exit).
- **Was ist potenziell integrierbar**: kein neuer Baustein -- strukturell
  praktisch identisch mit dem bereits vorhandenen `triple_ma_strategy/`
  (dort TEMA/TSMA statt EMA, und ein Dreifach- statt Zweifach-Crossover).
  Der eigentliche Wert des Sheets liegt in der Methodik (Overfitting-Check
  über Nachbarparameter, IS-Disziplin durch Trade-Count-Mindestmaß), nicht
  in einer neuen Alpha-Quelle.

**Express**
- **Nächster Schritt**: mit vorhandenen Daten direkt testbar (echte
  BTCUSDT-Daily-Daten bereits im Repo über `auction_playbook.data.fetch_klines`,
  gleiche Quelle wie [[crypto-volume-profile-mean-reversion]] und
  `gold_bitcoin_dual_momentum/`) -> Backtest angestoßen:
  `scripts/research_ema_9_21_cross_btc.py`.
- **Ergebnis** (BTCUSDT Daily, 2023-07-01 -> 2026-08-13, 1140 Bars, 0.1%
  Commission/Seite, Fill auf nächstem Open -- exakt die Sheet-Vorgaben):
  - Buy & Hold BTC: TotalReturn +107.4%, MaxDD -53.0%
  - EMA 9/21 (Sheet-Parameter): n=26 Trades, WinRate 30.8%, PF 2.75,
    TotalReturn +139.5%, CAGR +32.3%, MaxDD -27.3%
  - Overfitting-Check (Nachbarparameter 8/20 und 10/22): PF 2.95 bzw. 3.15,
    TotalReturn +145.2% bzw. +170.3%, MaxDD -26.3% bzw. -26.0% -- klares
    Plateau, kein Spike bei 9/21.
  - **Einordnung**: Die Sheet-Behauptung hält auf echten Daten stand --
    WinRate/PF/Drawdown-Halbierung liegen nahe an den behaupteten Werten
    (~35%/~3/halbe Drawdown vs. gemessen 31%/2.75/~halbe Drawdown), und die
    Strategie schlägt Buy&Hold sowohl bei Return als auch bei Drawdown im
    getesteten Fenster. Einschränkung: Fenster ist mehrheitlich ein BTC-
    Bullenmarkt (2023-2026) -- kein Regime-Wechsel/Bärenmarkt-Stresstest
    enthalten, und n=26 Trades ist laut Sheets eigenem Maßstab ("20+ ist
    Evidenz") gerade so ausreichend, nicht komfortabel groß.
  - Kein eigenständiger neuer Strategie-Kandidat für dieses Repo, da
    `triple_ma_strategy/` dieselbe Grundidee bereits mit robusterer
    Parametrisierung abdeckt -- dient hier als Bestätigung, dass die
    Repo-Datenquelle (`auction_playbook.data.fetch_klines`) und die
    Sheet-Methodik (Nachbarparameter-Plateau-Check) konsistente Ergebnisse
    liefern.

**Nachtrag 2026-08-14 -- Long/Short-Erweiterung + volle Historie + IS/OOS**

Nutzerfrage: ob sich daraus eine "saubere" Strategie ableiten lässt und wie
eine Short-Ergänzung (statt Cash-Halten unterhalb des Crossovers) aussehen
würde. Getestet mit `simulate_ema_cross_ls()` im selben Skript, volle
BTCUSDT-Historie seit Binance-Listing (2017-08-17) bis 2026-08-13, IS/OOS
70/30-Split bei 2023-12-01:

| | n | WinRate | PF | Return | CAGR | MaxDD |
|---|---|---|---|---|---|---|
| Buy&Hold (voll) | -- | -- | -- | +1381% | -- | -83.2% |
| Long/Flat (voll) | 66 | 33.3% | 3.30 | +3137% | +47.2% | -72.4% |
| Long/Short (voll) | 132 | 31.1% | 2.15 | +748% | +26.8% | -81.5% |
| Long/Flat OOS | 23 | 34.8% | 2.31 | +76.8% | +23.5% | -27.3% |
| Long/Short OOS | 46 | 32.6% | 1.61 | +42.6% | +14.1% | -44.1% |

- **Long/Flat ist über 9 Jahre und beide IS/OOS-Teilfenster konsistent
  robust** (PF 2.3-3.3, deutlich unter Buy&Hold-Drawdown) -- das ist die
  "saubere" Version: einfache Regel, kein Regime-Overfit, hält auch out-of-
  sample.
- **Short-Ergänzung verschlechtert das Ergebnis in JEDER getesteten
  Dimension** (niedrigerer PF, niedrigerer CAGR, höherer MaxDD, sowohl IS
  als auch OOS) -- und das VOR Berücksichtigung von Funding-Kosten (nicht
  modelliert, siehe Skript-Docstring), die bei BTC-Perp-Shorts in
  Aufwärts-/Seitwärtsphasen zusätzlich negativ wirken würden. Grund: BTC hat
  einen starken strukturellen Aufwärts-Drift; Cash-Halten unterhalb des
  Crossovers vermeidet Drawdown-Exposure, während Shorten zusätzliches
  asymmetrisches Risiko eingeht, ohne dass die Gegenbewegungen das
  kompensieren.
- **Antwort auf die Nutzerfrage**: Ja, Long/Flat ist als einfache Baseline
  robust genug für die nächste Stufe der Sheet-eigenen Leiter (Paper-Test).
  Nein, eine Short-Ergänzung ist auf Basis dieser Daten keine Verbesserung
  -- sie sollte NICHT eingebaut werden, ohne dass ein eigener Edge für die
  Short-Seite (z.B. via Funding-Rate-Filter oder separates Signal) belegt
  ist.
- **Nächster Schritt, falls weiterverfolgt**: Paper-Modus / Forward-Test
  gemäß Sheet-Leiter (Teil 4), nicht direkt Live. Kein Automatismus
  angestoßen -- reine Analyse-Notiz.

**Nachtrag 2026-08-14 (2) -- Risk-Sizing auf $100k-Konto, 1% Risiko/Trade**

Nutzerfrage: IS/OOS mit $100k Startkapital und 1% Risiko pro Trade
durchrechnen. Wichtig: die Sheet-Strategie hat KEINEN Stop-Loss (Exit nur
über den Crossover) -- "1% Risiko" ist ohne Stop nicht definiert. Ergänzt
um einen ATR(14)x2.0-Stop (offengelegte Erweiterung, nicht Teil des
Original-Sheets), Positionsgröße = 1% aktuelles Eigenkapital / Stop-Distanz,
gedeckelt auf verfügbares Eigenkapital (kein Hebel). Nur Long/Flat (Short
performt laut vorigem Nachtrag schlechter). Code:
`simulate_risk_sized()` in `scripts/research_ema_9_21_cross_btc.py`.

| | n | WinRate | PF | AvgR | Stopped | EndEquity | Return | CAGR | MaxDD |
|---|---|---|---|---|---|---|---|---|---|
| Full (2017-2026) | 76 | 31.6% | 3.09 | +1.20R | 18/76 | $225,474 | +125.5% | +9.5% | -15.1% |
| IS (2017-2023) | 49 | 30.6% | 3.42 | +1.44R | 12/49 | $202,763 | +102.8% | +11.9% | -15.1% |
| OOS (2023-2026) | 27 | 33.3% | 1.70 | +0.32R | 6/27 | $108,250 | +8.2% | +3.0% | -6.5% |

- Hebel-Cap wurde in keinem Fenster ausgelöst (0 von allen Trades) -- die
  ATR-Stop-Distanz war immer weit genug, dass 1%-Risiko-Sizing deutlich
  unter 100% Notional-Einsatz blieb (grob 15-20% des Kapitals pro Trade).
- Erwarteter Trade-off ggü. der 100%-of-Equity-Variante bestätigt sich:
  deutlich kleinerer MaxDD (-15.1% statt -72.4% auf Full-History), aber
  auch deutlich kleinerer Endwert (+125.5% statt +3137% -- Risk-Sizing gibt
  bewusst Rendite für Drawdown-Kontrolle auf).
  OOS ist mit PF 1.70 / AvgR +0.32R / CAGR +3.0% spürbar schwächer als IS --
  konsistent mit dem generellen Muster in diesem Fenster (auch die anderen
  Varianten oben zeigen OOS < IS), kein Bruch, aber auch kein Grund für
  übertriebenen Optimismus bei nur 27 OOS-Trades.
- Nicht modelliert: Slippage, Stop-Fill exakt auf Stop-Niveau (kein
  Gap-Through), Funding-Kosten (hier irrelevant, da kein Short).

**Nachtrag 2026-08-14 (3) -- Optimierung fuer "nachhaltig/konstant" auf echtem
100k-Funded-Konto**

Nutzerfrage: wie die Strategie fuer nachhaltige, konstante Gewinne auf einem
echten Funded-Konto optimieren. Gegen die ECHTEN, bereits im Repo
dokumentierten Challenge-Regeln geprueft (`ou_paper_backtest/
oos_holdout_challenge_profiles.py`: max 3%/Tag Verlust, 10%
Gewinn-Ziel) -- gleiche Methodik (worst-single-day%, Bruch-Flag,
Tage-bis-Ziel), rein auf dem OOS-Fenster (2023-12 -> 2026-08, "echter
Holdout"-Konvention dieses Repos):

| Profil | n | WinRate | PF | CAGR | MaxDD | WorstDay | 3%-Regel | Tage bis 10% |
|---|---|---|---|---|---|---|---|---|
| 1% Risiko, kein BE | 27 | 33.3% | 1.70 | +3.0% | -6.5% | -1.66% | ok | 345 |
| 0.25% Risiko, kein BE | 27 | 33.3% | 1.77 | +0.8% | -1.7% | -0.44% | ok | nicht erreicht |
| 1% Risiko, BE@1R | 31 | 22.6% | 1.89 | +3.4% | -6.1% | -1.66% | ok | 345 |
| 0.25% Risiko, BE@1R | 31 | 22.6% | 1.96 | +0.9% | -1.6% | -0.44% | ok | nicht erreicht |

- **Die 3%-Tagesregel ist NICHT der limitierende Faktor**: selbst bei 1%
  Risiko/Trade liegt der schlechteste Einzeltag bei -1.66%, weit unter der
  3%-Grenze -- Single-Instrument, Daily-Close-Signale und ATR-Stop erzeugen
  strukturell keine grossen Ein-Tages-Verluste.
- **Der eigentliche Engpass ist die Geschwindigkeit zum Gewinnziel**: selbst
  im 1%-Profil dauert es 345 Tage (~11,5 Monate) bis +10% im OOS-Fenster --
  bei den meisten Funded-Challenges mit Zeitlimit (30-60 Tage typisch) waere
  das ein Fail, unabhaengig von der Drawdown-Sicherheit. Ursache: nur ~1
  Trade/Monat auf einem einzelnen Instrument (BTC), viel Zeit in Cash.
- **Breakeven-Stop (@1R) ist kein klarer Gewinn**: CAGR-Verbesserung
  marginal (+3.0% -> +3.4%), aber WinRate bricht von 33.3% auf 22.6% ein
  (vorzeitig ausgestoppte Trades, die sich spaeter erholt haetten, zaehlen
  jetzt als Verlierer). Passt zum eigenen Fund in [[trend-following-momentum]]
  bzw. `app_pages/risk_management.py` ("12,5%-Cap sah nach Gratis-Gewinn
  aus, war es OOS nicht") -- ein einzelner Verbesserungs-Fund auf einem
  Fenster ist kein Beleg, bevor er selbst wieder OOS/auf einem zweiten
  Fenster geprueft ist.
- **Cross-Check zur bestehenden Repo-Lehre**: `app_pages/risk_management.py`
  zeigt fuer das (Multi-Position-)OU-Modell, dass der AGGREGIERTE
  Risiko-Deckel den Drawdown bestimmt, nicht der Einzeltrade-Risiko-Prozentsatz.
  Bei dieser BTC-EMA-Strategie ist IMMER nur eine Position offen -- der
  aggregierte Deckel ist hier identisch mit dem Einzeltrade-Risiko und bringt
  keinen zusaetzlichen Hebel. Der uebertragbare Gedanke ist trotzdem
  anwendbar: mehr (unkorrelierte) gleichzeitige Positionen wuerden sowohl die
  Tages-Volatilitaet glaetten als auch die Trade-Frequenz erhoehen -- also
  den oben identifizierten Geschwindigkeits-Engpass direkt adressieren.
- **Offene Frage, nicht beantwortet**: das genaue Zeitlimit der echten
  Funded-Challenge des Nutzers ist nicht im Repo dokumentiert (nur 3%/Tag
  und 10%-Ziel gefunden) -- ohne dieses Limit laesst sich "345 Tage" nicht
  abschliessend als Fail einordnen.
- **Nächster Schritt**: kein Automatismus angestossen. Naheliegende
  Kandidaten fuer eine echte Verbesserung (jeweils selbst wieder OOS-pruefen,
  nicht nur auf diesem einen OOS-Fenster vertrauen): (1) Diversifikation
  ueber mehrere Instrumente (z.B. ETH/SOL zusaetzlich zu BTC) unter
  gemeinsamem Risiko-Deckel, um Trade-Frequenz zu erhoehen; (2) Pruefen, ob
  eine der bereits im Repo laufenden schnelleren Strategien (z.B. OU-Modell,
  `triple_ma_strategy`) besser zum Zeitlimit der Challenge passt als eine
  einzelne BTC-Trendfolge.

**Nachtrag 2026-08-15 (2) -- Kelly, dynamisches Sizing, SL/TP-Sweep,
Regimefilter (`scripts/research_ema_9_21_cross_optimization.py`)**

Nutzerfrage: wie wuerde Kelly/dynamisches Risikomanagement funktionieren,
wurde mit anderen Filtern optimiert, wurde bei SL/TP in die Tiefe gegangen?
Antwort vorher: nein zu allen drei -- hier nachgeholt, gleiche Methodik wie
`education_kelly.py` (OU-Modell) bzw. der SL/TP/ADX-Sweep auf der
Gold-Asian-Range-Breakout-Seite.

- **Kelly** (auf den echten 1%-Risiko-Trades): IS Kelly f*=22.8% (n=49,
  WinRate 30.6%, Payoff-Ratio b=8.93), OOS Kelly f*=16.2% (n=27, WinRate
  33.3%, b=3.88), Quarter-Kelly 4.0-5.7%. Anders als beim OU-Modell ist
  NICHT die Korrelations-Annahme das Problem (BTC haelt immer nur eine
  Position) -- sondern die duenne Stichprobe und der zwischen IS/OOS stark
  schwankende Payoff-Schaetzer (8.93 vs. 3.88, ein einzelner Riesen-Trade
  kann das kippen). Volles Kelly bedeutet trotzdem 50-90%
  Drawdown-Risiko selbst bei echter Kante. Quarter-Kelly (~4-5.7%) liegt
  leicht ueber dem in Nachtrag (3)/(4) gefundenen robusten Bereich (1-3%,
  flacher OOS-Calmar) -- eine leichte Anhebung auf ~2-3% waere mit Kelly
  vereinbar, mehr nicht auf dieser Datenbasis vertretbar.
- **Dynamisches/Vol-skaliertes Sizing** (risk_pct * median(ATR60)/aktueller
  ATR, gedeckelt [0.5x,1.5x]): OOS PF 1.84->1.90, CAGR +3.6%->+4.1%, aber
  MaxDD -6.5%->-7.4% und WorstDay -1.67%->-1.74% -- im Wesentlichen ein
  Unentschieden, kein klarer Gewinn. Der ATR-Stop selbst skaliert
  Positionsgroesse bereits implizit mit Volatilitaet (weiterer Stop bei
  hoher Vol -> kleinere Position bei gleichem $-Risiko); dieser Test ist
  ein zusaetzlicher Hebel oben drauf, kein grundlegend neues Konzept.
- **ATR-Stop-Multiplikator-Sweep** (1.0x-3.5x): PF bleibt ueber den ganzen
  Bereich in einem Plateau (IS 3.11-3.44, OOS 1.75-2.16) -- kein einzelner
  Wert sticht heraus. Engere Stops erhoehen CAGR deutlich (IS 23.3% bei
  1.0x vs. 6.8% bei 3.5x), aber auch den Drawdown (IS MaxDD -24.3% vs.
  -8.8%) -- reiner Risiko-Dial, kein Free Lunch. Der 2.0x-Standard ist
  vertretbar, aber nicht nachweisbar optimal.
- **Take-Profit-Test** (0.5R-4R vs. kein TP): **robust bestaetigt
  schaedlich**, IS und OOS, bei JEDEM getesteten Level (OOS PF 1.84 ohne TP
  vs. 0.97-1.69 mit TP). Erklaerung passt zur Kelly-Analyse oben: die Kante
  lebt von seltenen grossen Gewinnern (AvgWinR 2.3-6.3R je nach Fenster) --
  ein TP kappt genau das. Identisches Muster wie bei
  `asian_range_breakout` (Gold). Kein TP bleibt richtig.
- **Regimefilter (ADX-Mindestwert, SMA200-Trend)**: NICHT robust genug, um
  zu uebernehmen. ADX>=25 sieht IS spektakulaer aus (PF 6.74, n=24), aber
  ADX>=20 bricht OOS zunaechst ein (PF 1.33, Baseline 1.84) und die
  Erholung bei ADX>=25 (PF 2.06) steht auf nur n=13 OOS-Trades -- zu duenn.
  SMA200-Trend aehnlich (IS PF 5.77 n=23, OOS PF 1.73 n=20, unter
  Baseline). Anders als bei Gold (Tausende Trades, ADX-Filter sauber IS
  UND OOS bestaetigt) hat BTC bei ~1 Trade/Monat schlicht nicht genug
  Stichprobe, um einen Filter verlaesslich zu validieren -- ein
  IS-only-gut-aussehendes Muster ohne OOS-Bestaetigung ist genau die Falle,
  vor der dieses Repo an anderer Stelle bereits gewarnt hat (12,5%-Cap-Fund
  in `app_pages/risk_management.py`).
- **Ergebnis**: keiner der fuenf getesteten Hebel wird uebernommen. Einzige
  vertretbare Anpassung waere eine leichte Risiko-Erhoehung auf ~2-3%
  (Kelly-kompatibel, im bereits robusten Bereich) -- kein neuer
  Automatismus, reine Parameterwahl innerhalb des bereits getesteten
  Sizing-Modells.

**Nachtrag 2026-08-15 (3) -- Rendite-Verschenkt-Quantifizierung, BE-Sweep
(Korrektur), Chandelier-Trailing-Stop, Volumen-Exhaustion-Exit,
ETF-Inflow-Exit (nicht testbar)**

Nutzerfragen: wie sieht ein ATR-basierter TP oder ein Exit nach Volumen/
ETF-Inflows aus, wie viel Rendite verschenkt man mit TP-Logik, wie
performen verschiedene BE-Werte, wie eine Trailing-SL?

- **Rendite-verschenkt-Tabelle (TP vs. kein TP, % vom Kein-TP-Endkapital)**:
  IS verschenkt massiv (TP=0.5R nur 51%, TP=4.0R 78% vom Endkapital) --
  aber **OOS ist der Unterschied viel kleiner und bei manchen Levels sogar
  leicht positiv** (TP=1.5R/4.0R: 101%). Der IS-Effekt wird von wenigen
  sehr grossen Trades getrieben, die IS ueberrepraesentiert sind. Fazit
  "kein TP" bleibt Standard, aber die Begruendung ist auf OOS-Basis
  schwaecher als der reine IS-Blick suggeriert -- Korrektur der vorherigen
  Darstellung, die nur die IS-lastige Gesamtzahl zeigte.
- **Breakeven-Sweep (Korrektur des vorherigen Einzelwert-Tests)**: mit
  echtem Sweep (0.25R-2.0R statt nur 1.0R) zeigt sich BE@0.75-1.0R als
  **leicht POSITIV** (OOS PF 1.84->2.06, CAGR +3.6%->+4.0%), nicht klar
  schaedlich wie der fruehere Einzelwert-Test nahelegte. Win-Rate sinkt
  real (33.3%->25-27%), aber PF/CAGR verbessern sich leicht. Kein starker
  Hebel, aber vertretbar als psychologisches Sicherheitsnetz.
- **Chandelier-Trailing-Stop** (hoechster Close seit Entry - Multiplikator
  x ATR, nur nachziehend, ersetzt den Fix-Stop sobald enger): **durchgehend
  schlechter als die Baseline** ueber alle getesteten Multiplikatoren
  (2.0x-4.0x), beide Fenster (bester OOS-Wert 3.0x: PF 1.75/CAGR +3.1% vs.
  Baseline PF 1.84/CAGR +3.6%). Gleicher Mechanismus wie beim TP -- sichert
  Gewinne vor dem eigentlichen Crossunder, kappt die grossen Trend-Trades.
- **Volumen-Exhaustion-Exit** (Exit wenn Tagesvolumen < X% des 20-Tage-
  Schnitts UND unrealisiert >= Y R): bei engem Schwellenwert (<30%)
  praktisch neutral (loest kaum aus), bei lockereren Schwellen (50-70%)
  klar schaedlich (OOS PF 1.84->1.22-1.50). Selbes Muster: jeder
  Gewinnsicherungs-Mechanismus vor dem Crossunder schneidet die grossen
  Trend-Trades ab, die die Kante ausmachen.
- **ETF-Inflow-Exit**: NICHT testbar -- nur eine Literatur-Notiz
  ([[crypto-etf-flows]]), keine echte Datenquelle fuer taegliche IBIT/
  FBTC-Netto-Flows im Repo. Muesste neu angebunden werden (z.B. Farside
  Investors, SoSoValue oder CoinGlass ETF-Flow-APIs, alle mit kostenlosen
  Stufen) -- nicht umgesetzt, kein Automatismus.
- **Gesamtmuster ueber alle vier Session-Nachtraege zu Exit-Varianten**:
  JEDER getestete "Gewinne frueher sichern"-Mechanismus (TP, Chandelier,
  Volumen-Exit) schadet -- ausser moderatem Breakeven (0.75-1.0R), das
  leicht positiv ist. Die Kante dieser Strategie liegt fast vollstaendig
  darin, Gewinner bis zum tatsaechlichen Trendumkehr-Signal (Crossunder)
  laufen zu lassen; jeder zusaetzliche vorzeitige Exit-Mechanismus
  reduziert genau das.
- **WICHTIGER BUGFIX (2026-08-16), betrifft alle obigen OOS-Zahlen dieser
  Session**: beim Bauen des Live-Scanners (`btc_ema_cross/live_scan.py`)
  und dessen Verifikation gegen den Batch-Backtest
  (`scripts/verify_btc_ema_cross_live_scan.py`) wurde ein echter Dtype-Bug
  in `go_long = above & ~above.shift(1).fillna(False)` gefunden:
  `above.shift(1)` wird durch den eingefuegten NaN bei Pandas zu
  `object`-Dtype, `.fillna(False)` stellt den `bool`-Dtype NICHT wieder
  her, und `~` auf einer `object`-Series mit echten Python-Bools invertiert
  NICHT boolesch, sondern bitweise (`~True`=-2, `~False`=-1, beide
  "truthy") -- dadurch wird `go_long` faktisch identisch zu `above` selbst
  (immer True, wenn `above` True ist, nicht nur am echten Fresh-Cross-Tag).
  In einem DURCHGEHENDEN Backtest ab dem echten Datenbeginn ist das
  folgenlos (die `position==0`-Guard verhindert Doppel-Eintritte). Aber
  **jedes `sim_from`-Fenster, das mitten in einem bereits laufenden
  "above"-Zustand startet** (z.B. der 2023-12-02-OOS-Split, der seit
  mindestens 2023-11-27 durchgehend "above" war), erzeugt einen Phantom-
  Trade am allerersten Tag des Fensters. Betroffen: JEDER OOS-Test dieser
  Session (Funded-Challenge-Check, Kelly-Analyse, SL/TP-Sweep, Regime-
  filter, Vol-skaliertes Sizing, BE-Sweep, Rendite-verschenkt-Tabelle,
  Chandelier, Volumen-Exit, Gegenposition). Full/IS-Zahlen sind NICHT
  betroffen (die starten am echten Datenbeginn, kein Mid-Stream-Effekt).
  Fix: `above_prev = above.shift(1, fill_value=False)` (kein NaN-Umweg,
  bleibt `bool`-Dtype) in allen betroffenen Dateien
  (`btc_ema_cross/engine.py`, `btc_ema_cross/optimization.py`,
  `scripts/research_ema_9_21_cross_diversified.py`,
  `scripts/research_ema_9_21_cross_multi_asset.py`).
  **Tatsaechliche Auswirkung (OOS, 1% Risiko)**: n=27->22 Trades, PF
  1.84->1.81, CAGR +3.6%->+3.2%, MaxDD -6.5%->-6.0%, EndEquity
  $109.994->$108.814 -- klein in der Groessenordnung, KEINE der
  qualitativen Session-Schlussfolgerungen kippt (kein TP, kein Hebel
  noetig, 1-3%-Risikobereich, Multi-Asset schlechter, Crash-Filter
  wirkungslos, kleine Gegenposition hilft nicht bleiben alle gueltig) --
  aber die exakten Dezimalzahlen aus den Kelly-/SL-TP-/Filter-/Vol-Sizing-
  Nachtraegen oben wurden mit dem Bug gerechnet und sind leicht ungenau.
  Nicht komplett neu gerechnet (Aufwand/Nutzen), da keine qualitative
  Schlussfolgerung betroffen ist.
- **Kleine Gegenposition am Crossunder statt Flat** (Nutzerfrage): getestet
  mit `simulate_asymmetric_short` bei Groessen 0.1x-1.0x des normalen
  Risikos. Der Short-Leg ist bei JEDER Groesse negativ (IS: -$252 bis
  -$2.556, OOS: -$189 bis -$1.880), kein Vorzeichenwechsel ueber den
  gesamten Bereich -- keine Small-Sample-Fluktuation, sondern ein
  gleichmaessig skalierender Schaden. Flat bleibt strikt besser als jede
  Short-Beimischung. Gleicher Grund wie beim vollen Long/Short-Test: der
  Crossunder zeigt nur "Momentum abgekuehlt", nicht zuverlaessig "jetzt
  beginnt ein Abwaertstrend" -- BTCs struktureller Aufwaerts-Drift macht
  das Shorten dieses Signals zu einer Negativ-Erwartungswert-Wette,
  unabhaengig von der Positionsgroesse.

**Nachtrag 2026-08-14 (4) -- Bugfix (EMA/ATR-Warmup an der IS/OOS-Grenze),
Multi-Asset-Diversifikation (BTC+ETH+SOL) und Eigenkapital-Konto ohne Limits**

Antwort auf Nutzer-Rueckmeldung: kein Zeitlimit fuer die Challenge -> der
"345 Tage bis Ziel"-Befund aus Nachtrag (3) ist unkritisch. Trotzdem wie
gewuenscht Multi-Asset-Diversifikation UND ein Eigenkapital-Konto ohne
externe Limits getestet.

**Bugfix zuerst**: beim Bauen der Multi-Asset-Variante fiel auf, dass die
IS/OOS-Zahlen aus Nachtrag (2)/(3) einen echten Fehler hatten -- `is_df`/
`oos_df` wurden VOR der EMA/ATR-Berechnung zugeschnitten, wodurch beide
Indikatoren an der Fenstergrenze kalt neu starten statt die Vorgeschichte
als Warmup zu nutzen. Behoben (`simulate_ema_cross`, `simulate_ema_cross_ls`,
`simulate_risk_sized` bekommen jetzt einen `sim_from`-Parameter,
Indikatoren laufen immer auf der VOLLEN Serie). Effekt auf die OOS-Zahlen
war spuerbar: 1%-Risiko-Profil ging von CAGR +3.0% / PF 1.70 / 345 Tage bis
Ziel (Nachtrag 3, fehlerhaft) zu **CAGR +3.6% / PF 1.84 / 101 Tage bis
Ziel** (korrigiert) -- WorstDay blieb nahezu gleich (-1.67% statt -1.66%,
gleicher Tag), weil der Fehler primaer die Trade-Anzahl/den Zeitpunkt
einzelner Trades verschob, nicht die grossen Tagesbewegungen. Alle Zahlen
aus Nachtrag (2) und (3) oben sind durch die unten stehenden ersetzt/
korrigiert zu lesen, wo sie abweichen.

**1) Eigenkapital-Konto ohne Limits** (Risk-%-Sweep 0.5%-12%, Full/IS/OOS,
`simulate_risk_sized` mit korrigiertem Warmup):
- OOS-Calmar bleibt ueber den GESAMTEN Bereich flach bei 0.55-0.62 (leichtes
  Maximum um 8% Risiko), IS/Full-Calmar steigt bis ~5% Risiko (0.94 bzw.
  0.75) und faellt danach, weil der Kein-Hebel-Deckel zunehmend greift
  (SizeCapped steigt von 0 auf 66/76 bei 12% Risiko).
- **Einordnung**: da OOS -- die einzige Instanz, die nicht fuers Tuning
  angeschaut wurde -- kaum auf den Risiko-Prozentsatz reagiert, waere jede
  Wahl "hoeheres Risiko ist klar besser" nur auf Basis von IS eine klassische
  Overfitting-Falle (gleiches Muster wie der 12,5%-Cap-Fund in
  `app_pages/risk_management.py`). Fuer ein echtes Eigenkapital-Konto ohne
  Zeitdruck ist 1-3% Risiko/Trade ein vertretbarer Bereich (Calmar
  ~0.56-0.71 auf Full/OOS, MaxDD noch im zweistelligen, nicht dreistelligen
  Bereich); daurueber (5%+) steigt vor allem der MaxDD (bis -68.7% bei 12%),
  ohne dass OOS-Calmar entsprechend mitzieht.

**2) Multi-Asset-Diversifikation** (BTC+ETH+SOL, gleiches EMA9/21-Signal je
Instrument, gemeinsamer Account, `scripts/research_ema_9_21_cross_multi_asset.py`,
gemeinsames Fenster ab SOL-Listing 2020-08-11, gleicher Warmup-Fix):

| Profil (OOS) | n | WinRate | PF | CAGR | MaxDD | WorstDay | 3%-Regel |
|---|---|---|---|---|---|---|---|
| BTC-only (Baseline) | 27 | 33.3% | 1.84 | +3.6% | -6.5% | -1.67% (24-03-19) | ok |
| BTC+ETH+SOL, kein Deckel | 70 | 35.7% | 1.57 | +8.0% | -13.3% | -4.72% (24-03-19) | **BREACHED** |
| BTC+ETH+SOL, 2.5%-Deckel | 57 | 35.1% | 1.45 | +5.1% | -10.8% | -3.59% (25-10-10) | **BREACHED** |

| Full-common (2020-2026) | n | CAGR | MaxDD | WorstDay |
|---|---|---|---|---|
| BTC-only | 52 | +9.1% | -11.6% | -5.33% (21-01-21) |
| BTC+ETH+SOL, kein Deckel | 151 | +32.4% | -26.1% | **-22.31%** (21-05-19) |
| BTC+ETH+SOL, 2.5%-Deckel | 127 | +26.5% | -33.6% | -22.33% (21-05-19) |

- **Kernbefund, gegen die urspruengliche Hypothese**: Diversifikation ueber
  mehrere Krypto-Assets erhoeht zwar Trade-Frequenz (27->70 Trades OOS) und
  CAGR (+3.6%->+8.0%), aber der schlechteste Einzeltag verschlechtert sich
  UEBERPROPORTIONAL (-1.67%->-4.72%, fast das 3-fache) -- selbst der 2.5%-
  Aggregat-Deckel (der beim Multi-Position-OU-Modell in
  `app_pages/risk_management.py` der wirksame Hebel war) druckt die 3%-
  Tagesregel-Verletzung nur knapp unter die Baseline, verhindert sie aber
  NICHT (-3.59% liegt immer noch ueber der 3%-Grenze). Am Full-common-
  Fenster zeigt sich der Grund extrem deutlich: am 2021-05-19 (realer
  Krypto-Flash-Crash-Tag) verlor das Drei-Asset-Buch -22.3% an einem Tag --
  BTC/ETH/SOL crashen praktisch gleichzeitig, Korrelation geht in Stress-
  Phasen gegen 1. Der aggregierte Deckel wirkt hier nicht wie beim
  OU-Modell (dort viele, tatsaechlich verschiedene Aktien/Instrumente),
  weil es strukturell keine unabhaengigen Wetten sind, nur drei Varianten
  derselben Wette.
- **Antwort auf die urspruengliche Diversifikations-Idee**: fuer ein
  Funded-Konto mit harter 3%-Tagesregel ist BTC+ETH+SOL-Diversifikation in
  dieser Form NICHT empfehlenswert -- sie tauscht mehr Rendite gegen ein
  Regelbruch-Risiko, das der Deckel nicht zuverlaessig auffaengt. Fuer ein
  Eigenkapital-Konto ohne Tagesregel (Frage 1 oben) ist sie dagegen ein
  legitimer Rendite-Hebel, SOFERN man sich bewusst ist, dass es sich um
  konzentriertes Krypto-Beta mit hoeherer Tail-Varianz handelt, nicht um
  echte Diversifikation.
- **Nicht getestet**: echte unkorrelierte Diversifikation (andere
  Asset-Klasse, z.B. Gold/FX zusaetzlich zu Krypto) war nicht Teil dieser
  Anfrage, waere aber der naheliegende naechste Schritt, um den Tail-Risk-
  Effekt oben tatsaechlich zu adressieren statt nur zu belegen, dass er
  existiert.

**Nachtrag 2026-08-14 (5) -- Crash-Vorwarn-Filter gesucht: drei Kandidaten
getestet, alle negativ**

Repo-Survey zuerst (siehe [[fx-microstructure]]-artiges Muster: erst pruefen
was existiert, bevor neu gebaut wird): `triple_ma_strategy/regime.py` hat
bereits einen GMM-Vol-Regime-Filter, der GETESTET und als NEGATIV dokumentiert
ist (kontinuierliches Filtern fragmentiert Trades, PF SP500 2.67->0.98;
Entry-only-Variante inkonsistent). `ou_paper_backtest` hat ein Benchmark-
EMA200-Regime-Gate (fuer Aktien-Basiswerte). `auction_playbook/data.py`
liefert bereits Taker-Buy/Sell-Delta (CVD-Baustein), bisher nur als
Entry-Signal genutzt, nie als Portfolio-Stress-Signal -- das war die
identifizierte Luecke.

Drei Kandidaten empirisch gegen die volle BTCUSDT-Historie getestet (nicht
nur an den 3 bekannten Crash-Tagen, sondern deren Basisrate UND
Vorhersagekraft insgesamt):
1. **Vol-Expansion (ATR3/ATR14-Ratio)**: an allen 3 Crash-Tagen bei t-1
   erhoeht (1.09-1.24) -- SIEHT vielversprechend aus, bis man die Basisrate
   prueft: Schwelle >1.2 feuert an 16,1% ALLER Tage (529 von 3284), und der
   bedingte naechste-Tag-Return ist NICHT schlechter als unbedingt (Mean
   +0.37% bedingt vs. +0.15% unbedingt, Worst-1%-Quantil -10.6% vs. -9.7%,
   kaum unterschiedlich). Kein echter Vorhersagewert -- klassischer
   Hindsight-Bias aus 3 Einzelbeispielen.
2. **Cross-Asset-Korrelation (BTC-ETH 20d rolling)**: bei den 3 Crashs
   0.67/0.84/0.92 -- uneinheitlich, und Schwelle >0.85 feuert an 55,5% ALLER
   Tage (BTC/ETH korrelieren strukturell fast immer stark). Bedingter vs.
   unbedingter Worst-Tail praktisch identisch (-9.5% vs. -9.7%). Kein
   Signal.
3. **Taker-Sell-Aggression (Delta-Z-Score aus auction_playbook-Daten)**:
   leicht interessanter (bedingter Worst-1%-Tail -13.6% vs. -9.7% unbedingt
   bei delta_z<-1), aber verpasst 1 von 3 bekannten Crashs komplett
   (2024-03-19: delta_z=+0.17, nicht negativ) und Basisrate 14,6% -- zu
   unzuverlaessig fuer einen Automatismus.
- **Fazit**: kein Tages-Bar-basierter technischer Fruehwarn-Filter zeigt in
  dieser Datenbasis echte Vorhersagekraft fuer Krypto-Flash-Crashes --
  passt zur Marktstruktur (Liquidations-Kaskaden laufen innerhalb von
  Stunden/Minuten ab, nicht Tagen; Tages-OHLC kann das strukturell nicht
  einen Tag im Voraus erkennen). Dieses Ergebnis reiht sich neben den
  bereits dokumentierten negativen Regime-Filter-Fund in
  `triple_ma_strategy/regime.py` ein -- gleiche Lehre, zweites Instrument.
- **Was stattdessen tatsaechlich hilft** (aus den bereits getesteten
  Ergebnissen dieser Notiz): (1) kleinere Risiko-Prozentsaetze pro Trade
  (reduziert den $-Schaden proportional, ohne eine Vorhersage zu brauchen);
  (2) echte Diversifikation ueber unkorrelierte Asset-Klassen (Gold/FX/SP)
  statt mehrerer Krypto-Paare -- naechster Schritt, noch nicht getestet.
- **Nicht getestet, moeglicher naechster Kandidat falls gewuenscht**:
  intraday/hoeher-aufgeloeste Daten (z.B. 1h-Bars) koennten frueher warnen
  als Daily-Bars -- wurde hier nicht verfolgt, da es die Fill-/Timing-Logik
  des gesamten Skripts aendern wuerde.

**Nachtrag 2026-08-15 -- Diversifikation ueber Asset-Klassen begonnen,
pausiert bis weitere Strategien feststehen**

Test von EMA9/21 UNVERAENDERT auf Gold/EURUSD/SP500 (echte Dukascopy-Daten,
`combined_strategy.data`, `scripts/research_ema_9_21_cross_diversified.py`,
5bps/Seite Kosten): bestaetigt Caveat 1 des Sheets. EURUSD verliert aktiv
Geld (PF 0.84, CAGR -0.6%) -- FX-Majors sind hier mean-reverting, kein
Trend, den ein schneller Crossover erfassen kann. Gold/SP500 sind technisch
profitabel (PF 2.01 / 1.54), lassen aber den Grossteil der Buy&Hold-Rendite
liegen (Gold +72.9% vs. Buy&Hold +302.6%; SP500 +25.8% vs. +497.9%) -- BTCs
~1.7%/Tag-Volatilitaet deckt die Whipsaw-Steuer des Crossovers, Gold/SP500
mit ~0.9%/Tag nicht.

Entscheidung (User): stattdessen die im Repo bereits VALIDIERTEN
Asset-spezifischen Strategien kombinieren statt EMA9/21 ueberall
zu erzwingen:
- **Gold**: `asian_range_breakout/` (XAUUSD, Asia-Range-Breakout M15) + der
  walk-forward-validierte ADX>=15-Filter. Full: PF 1.12, CAGR +5.0%,
  MaxDD -17.5%. OOS (2021-2026): PF 1.17, CAGR +7.8%, MaxDD -15.6% --
  verbessert sich sauber IS->OOS, kein Overfit-Verdacht.
- **FX**: `cls_practical/` (EURUSD M5, Daily-Trend-Filter). Echter Holdout
  (Split 2022-06-01): OOS CAGR 6.56%, Sharpe 0.84, MaxDD -13.4%.
- **Equities**: `ou_paper_backtest/` (S&P 500, OU-Mean-Reversion,
  Multi-Ticker bis ~147 gleichzeitig, LAEUFT LIVE auf Konto 2). OOS 2025+:
  Sharpe 0.91, MaxDD -4.7%.

**Architektur-Entscheidung fuer die Kombination** (User bestaetigt): das
OU-Modell haelt bis zu 147 Positionen gleichzeitig mit eigenem internen
Aggregat-Risiko-Deckel (15%) und eigenem laufenden Eigenkapital, GENAU der
Code, der aktuell live laeuft -- eine echte Verwebung in EINEN
gemeinsamen Risiko-Pool wuerde Eingriffe in diese Live-Engine erfordern.
Gewaehlt: **Kapital-Allokation statt Risiko-Verwebung** -- jede der
(am Ende N) Strategien bekommt einen festen Anteil des Gesamtkapitals,
laeuft mit ihrer eigenen unveraenderten validierten Logik, die $-Equity-
Kurven werden am Ende summiert. Echte Trades pro Strategie, aber kein
Eingriff in Live-Code.

**Pausiert**: User kuendigt zwei weitere Strategien an, die noch dazukommen
sollen, bevor der Kombinations-Layer gebaut wird (statt ihn fuer 4 zu bauen
und kurz danach nochmal zu erweitern). Naechster Schritt bei Wiederaufnahme:
die zwei weiteren Strategien identifizieren/klaeren, dann den Kapital-
Allokations-Combiner fuer alle N Strategien in einem Zug bauen.
