# Project: Intraday-Momentum mit „Noise Area“ (Zarattini/Aziz/Barbon)

**Status**: **ABGESCHLOSSEN, NEGATIV (2026-10-11): Tresor durchgefallen.**
Nicht bauen. Die Nachbildung trifft das Paper (Jahres-Korrelation 0,92 / 0,85,
brutto 3,6 bps je Trade wie im Paper), aber der Edge schrumpft ab 2023 und ist
in den letzten 12 Monaten auf beiden Indizes negativ. Gleiches Muster wie
[[baltussen-tagesend-momentum]] und [[orb-neues-regime-2026]].

**Nachtrag 14.10.:** Das Regime-2026-Raster (Fade-Gewinner) ist in OOS/Tresor
durchgefallen. **Forward läuft bis 31.03.2027**, Fokus Kontrolle K2 NASDAQ
(siehe Abschnitt „Regime 2026“).

**Querschnitt:** Öl-Mechanismus in [[oel-als-marktregime]], alle Forward-Tests in
[[optimierte-edges-uebersicht]] (auch in Notion: „📁 Optimierte Edges und Tests“).

Skript `scripts/research_noise_area_momentum.py` (Unterbefehle phase4,
phase5, phase6, unseal), Engine `noise_area_momentum/engine.py`, Zahlen in
`noise_area_momentum/results/`. Lock `zarattini_noise_area_20261011`
(19 Versuche).

## Phase 2: Paper

Zarattini, Aziz, Barbon: *Beat the Market: An Effective Intraday Momentum
Strategy for S&P500 ETF (SPY)*, SFI Research Paper N°24-97, SSRN 4824172,
Version 22.09.2025. SPY 1 Min. (IQFeed), 2007 bis 04/2024.

- **These**: Ein Ausbruch aus der „Noise Area“ zeigt ein Ungleichgewicht von
  Angebot und Nachfrage an, das sich intraday fortsetzt. Mechanismus laut
  Paper: Unterreaktion auf News, Gamma-Hedging von Dealern.
- **Regel**: sigma(HH:MM) ist das Mittel der letzten 14 Tage von
  |Close(HH:MM)/Open − 1|. Die Bänder sind max/min(Open, Vortagesschluss)
  × (1 ± sigma). Entscheidungen nur um HH:00 und HH:30, erstmals um 10:00.
  Long über dem oberen Band, short unter dem unteren. Der Trailing-Stop ist
  max(Band, VWAP), der Ausstieg spätestens 16:00. Sizing:
  min(4, 2 % / Tagesvola der letzten 14 Tage).
- **Behauptet**: Sharpe 1,33, 19,6 % p.a. netto, MDD 25 %, 0,09 $/Aktie je
  Trade. Bei 1x: Sharpe 1,24.
- **Warnsignale im Paper selbst**: 2016 −12,8 % und 2017 −6,9 %, und 2025
  bis August nur +1,0 % (Q24, nach der Publikation). Das Paper rechnet mit
  ~0,2–0,9 bps Kosten je Rundturn, bei uns sind es 1,3–1,6 bps.

## Phase 3: Screening

Einfaches Signal ohne State-Machine, 1:1 auf Dukascopy-CFDs (SP500,
NASDAQ, M1, NY-Zeit) nachbaubar. Abweichungen: CFD statt ETF; der VWAP ist
mit Tick-Volumen gewichtet; die Kosten sind gemessen (Spread + Slippage aus
`research_orb_cancel_at_sl_and_hold.py`). US30 ist nicht dabei, weil das
Paper ihn nicht nennt und so weniger Versuche anfallen.

## Phase 4: Nachbau, nur IS (2016-07 bis 2022)

| Netto, 1x | SP500 | NASDAQ |
|---|---|---|
| A Basis (Gegenband) | Sharpe 0,28 | 0,97 |
| **B Band+VWAP** (Paper-Hauptvariante) | **0,60** (t 1,5) | **1,11** (t 2,8) |
| C wie B, dyn. Sizing | 0,74 | 1,10 |
| B brutto | 1,08 | 1,43 |

Kalibrierung: Unsere Jahresrenditen (Variante C) korrelieren mit der
Paper-Tabelle zu 0,92 (SP500) bzw. 0,85 (NASDAQ). Brutto 3,6 bps je Trade
auf SP500 entsprechen den 0,09 $/Aktie des Papers. **Die Nachbildung
stimmt, die Kosten machen den Unterschied.** Wir zählen 0,86 Einstiege pro
Tag, das Paper 1,8 Trades pro Tag. Vermutlich zählt das Paper Ein- und
Ausstieg getrennt.

## Phase 5: Kombination, nur IS

Raster vorab festgelegt, 8 Punkte je Index: VM 1,0/1,5 × Lookback 14/90 ×
Gate (keins / echtes SPX-GEX vom Vortag unter dem 252-Tage-Median, als
Ersatz für den RSI-Proxy aus Paper-Abschnitt 4.5). Kalman, ADX und EMA200
wurden bewusst nicht getestet: Die Noise Area ist selbst der Trendfilter,
und laut Paper Q21 kostet ein SMA-Richtungsfilter Ertrag.

- Gewinner: **SP500 VM 1,0 / LB 14** (Paper-Standard), **NASDAQ VM 1,0 /
  LB 90**, beide ohne Gate.
- **Das GEX-Gate stützt den Mechanismus, verbessert die Strategie aber
  nicht.** An Tagen mit wenig Gamma steigt der Bruttoertrag je Trade
  (NASDAQ 5,7 auf 8,2 bps, SP500 3,6 auf 4,1 bps). Weil nur noch halb so
  viele Trades übrig bleiben, steigt das Sharpe nicht.
- Hinweis: Im ersten Lauf hat das Gate gesperrte Tage aus der Reihe
  gestrichen, statt sie als 0-Rendite-Tage zu zählen. Dadurch waren CAGR und
  Sharpe aufgebläht. Das wurde vor jeder Auswahl korrigiert.

## Phase 6: Robustheit (IS, vor dem Einfrieren)

| | SP500 | NASDAQ |
|---|---|---|
| Lag 0 / 1 / 5 / 10 Min. (Sharpe 1x) | 0,60 / 0,66 / 0,35 / 0,30 | 1,45 / 1,48 / 1,12 / 0,98 |
| Kosten-Breakeven je Rundturn | ~3,5 bps | > 5 bps |
| Bootstrap Sharpe p5 / p50 (dyn) | 0,19 / 0,77 | 1,03 / 1,58 |
| Stopabstand < 3× Kosten | 36 % der Einstiege | 20 % |
| Hebel dyn: Median / Anteil am 4x-Deckel | 2,6 / 27 % | 1,9 / 8 % |
| **Deflated Sharpe** (19 Versuche) | **0,35** | **0,95** |

## OOS und Tresor (je einmal geöffnet am 11.10.)

| Netto, 1x | IS 2016–22 | OOS 2023–09/25 | **Tresor 10/25–09/26** | nach Publikation (ab 10.05.24) |
|---|---|---|---|---|
| SP500 Sharpe | 0,60 | 0,45 | **−1,29** (−7,1 % p.a.) | −0,60 |
| SP500 brutto bps/Trade | 3,6 | 2,7 | **−1,4** | 0,0 |
| NASDAQ Sharpe | 1,45 | 0,59 | **−0,62** (−5,1 % p.a.) | −0,05 |
| NASDAQ brutto bps/Trade | 7,9 | 4,0 | **−0,9** | 1,0 |

Mit dyn. Sizing: SP500 Tresor −16,5 %, NASDAQ −1,9 %. Long- und Short-Seite
sind im Tresor beide ≤ 0. Bei 5 Min. Lag ist es ebenfalls negativ.

Jahresrenditen netto 1x, NASDAQ: 2018 +33,6 %, 2020 +13,7 %, 2022 +28,9 %,
2023 +9,3 %, 2024 +4,1 %, **2025 −2,0 %, 2026 −2,9 %**.

## Urteil

Verworfen nach dem Tresor. Der Edge war bis 2022 echt (NASDAQ DSR 0,95) und
schmilzt seitdem stetig: brutto je Trade 7,9 → 4,0 → −0,9 bps. Die eigene
Update-Tabelle der Autoren zeigt dasselbe (2025 +1 % bis August, und das
bei ETF-Kosten). Das ist der dritte unabhängige Intraday-Momentum-Edge auf
US-Indizes, der 2025/26 stirbt, nach ORB ([[orb-neues-regime-2026]])
und dem Tagesende-Momentum ([[baltussen-tagesend-momentum]]). Das passt zur
0DTE-/Long-Gamma-Lesart: In den Bruttozahlen dämpfen Dealer mit Long-Gamma
die Bewegungen nach dem Ausbruch.

## Diagnose: Was kippt den Tresor? (12.10., beschreibend)

Unterbefehl `diagnose` (Trade-Listen in `noise_area_momentum/results/diagnose_trades_*.csv`).
Alle drei Perioden sind offen, es wird nichts ausgewählt. Brutto bps je Trade:

| | SP500 IS / OOS / Tresor | NASDAQ IS / OOS / Tresor |
|---|---|---|
| Strategie (mit Stop) | 3,6 / 2,8 / **−1,4** (SE 2,3) | 7,9 / 4,1 / **−0,9** (SE 3,6) |
| Signal ohne Stop (bis 16:00 halten) | 3,2 / 4,2 / **−1,8** | 12,4 / 5,3 / **+3,8** |
| Ø Gewinner (bis 16:00 gehalten) | 40 / 34 / **26** | 58 / 51 / **36** |
| Ø Stop-Verlierer | −16 / −12 / −14 | −20 / −20 / −20 |
| Anteil ausgestoppt | 66 / 68 / 68 % | 64 / 66 / 65 % |
| Ausbruch bis 12:00 hält bis 16:00 (Markt, ohne Strategie) | 43 / 42 / **39 %** | 46 / 50 / 46 % |
| Weite des Schlusses über dem Band (Median) | 27 / 27 / **20 bps** | 38 / 37 / 38 bps |
| SPX-GEX Vortag (Median, Mrd. $) | 2,4 / 4,0 / **5,8** | dito |

**Befund:**
1. **Die Verlierer bleiben gleich, die Gewinner schrumpfen.** Trefferquote
   und Stop-Größe sind unverändert. Die Trendtage laufen weniger weit, das
   Gewinner-Mittel fällt um ein Drittel. Das ist die Signatur gedämpfter
   Trends, kein kaputtes Signal.
2. **SP500: Der Markt selbst hat sich verändert.** Ausbrüche halten seltener
   bis zum Schluss und laufen weniger weit über das Band (20 statt 27 bps).
   Auch das Signal ohne Stop ist negativ.
3. **NASDAQ: Die Marktstruktur ist unverändert** (Haltequote 46 %, Weite
   38 bps wie im IS). Das Signal ohne Stop ist weiter positiv (+3,8 bps).
   Verloren wird über den VWAP-/Band-Stop: Folgetrades nach einem Stop
   kommen auf −4,0 bps, im IS waren es +7,6.
4. **Gamma steigt, die Wirkung ist aber nicht sauber dosisabhängig.** Das
   Dealer-Gamma ist im Tresor 2,4-mal so hoch wie im IS, und 45–50 % der
   Trades fallen auf Tage mit GEX > 6 Mrd. (IS 11 %). Die GEX-Klassen
   zeigen im Tresor keine glatte Abstufung (n 10–107 je Zelle).
5. **Kein Einzelereignis.** Die Verluste verteilen sich über
   Nov./Dez./Jan., Mai, Juli und Sep.; beide Richtungen verlieren.
6. **Statistisch ist der Bruch grenzwertig:** IS gegen Tresor ≈ 1,9 σ
   (SP500) bzw. 2,2 σ (NASDAQ). Ein Jahr mit ~220 Trades unterscheidet
   „Edge tot“ kaum von „schlechtes Jahr“. Das Paper hatte 2016/17 selbst
   zwei Verlustjahre und erholte sich 2018.

## Regime 2026: breites Raster + Forward (14.10.)

Nutzerentscheid nach der Diagnose: wie beim ORB einen Edge auf Basis des
neuen Regimes bauen und forward testen. Skript
`scripts/research_noise_area_regime2026.py` (is / unseal / register /
evaluate), Lock `noise_area_regime2026_20261014`.

- **Split:** IS 10/2025–03/2026, OOS 04–06/2026, Tresor 07–09/2026 (beide
  vorbelastet, weil die Diagnose 2026 schon kennt). Forward ab 15.10.2026,
  Stichtag 31.03.2027.
- **Suchraum:** 9.216 Varianten je Index (VM, Lookback, Momentum/Fade,
  Exit, Seiten, Einstiegsfenster, Gate), 18.432 Trials. Auswahl: ≥ 60
  Trades, netto > 0, Rang nach Median-Sharpe der Nachbarn in VM/Lookback.
- **IS-Bild:** Fade dominiert das Bruch-Halbjahr (SP500 Top 50 = 100 %
  Fade, NASDAQ 72 %). Gewinner: SP500 Fade-short VM 0,5 / LB 90 /
  Exit VWAP, NASDAQ Fade-short VM 0,75 / LB 90 / Exit zurück im Band.
  IS-Sharpe ~1,6, t ≈ 1,1, **DSR 0,003 bzw. 0,002**.

| Netto bps/Trade (Trades) | IS 10/25–03/26 | OOS 04–06/26 | Tresor 07–09/26 |
|---|---|---|---|
| SP500 Gewinner (Fade-short) | +3,8 (77) | **−5,9** (41) | −0,5 (33) |
| SP500 K1 Paper-Original | −2,7 (116) | −1,2 (62) | −5,5 (58) |
| SP500 K2 nur 1. Trade, bis 16:00 | −5,6 (77) | −1,2 (44) | −5,1 (39) |
| NASDAQ Gewinner (Fade-short) | +5,0 (74) | **−8,4** (41) | **−18,5** (16) |
| NASDAQ K1 Paper-Original | −2,4 (122) | −1,0 (55) | −3,4 (40) |
| NASDAQ K2 nur 1. Trade, bis 16:00 | **+5,2** (80) | **+4,8** (35) | **+7,0** (23) |

**Befund:**
1. **Die Fade-Gewinner fallen sofort durch.** Das wiederholt die ORB-Lehre
   ([[orb-neues-regime-2026]]): Das Umkehr-Muster aus dem Bruch-Halbjahr
   trägt schon im nächsten Quartal nicht mehr. Bei ~75 IS-Trades und
   18.432 Varianten ist der Gewinner fast reines Fitten.
2. **K2 auf NASDAQ ist der einzige Lichtblick.** Paper-Einstieg, nur der
   erste Trade, ohne VWAP-Stop halten bis 16:00. Das ist in allen drei
   Fenstern 2026 positiv und mit 5 Min. Lag sogar besser (+8,4 / +8,9).
   Das passt zur Diagnose (der Stop kostet, das Signal lebt), ist aber
   vorbelastet, nicht im Raster gewählt, und hat nur 23–80 Trades je
   Fenster (t < 1). Auf SP500 trägt K2 nicht, was ebenfalls zur Diagnose
   passt.
3. **Forward** (alle eingefrorenen Varianten laufen mit): Erfolg je Index =
   Gewinner netto > 0 bps/Trade und besser als K1. Die eigentlich
   interessante Frage für den 31.03.2027 ist, ob **K2 NASDAQ** positiv
   bleibt. Das wäre ein eigenständiger, blind bestätigter Kandidat.

## Öl-Zusammenhänge (14.10., Nutzerauftrag)

Muster wie [[orb-gegenprobe-oel]]. Skript `scripts/research_noise_area_oel.py`
(gegenprobe / beschreibend / filter / evaluate). Für die Öl-Uhr ist die Engine
jetzt längenflexibel; die Regressionsprüfung zeigt identische Paper-Zahlen.
Öl-Kosten 4,75 bps je Rundturn (**Annahme** wie bei ORB). April 2020 ist raus.

**A – Gegenprobe: Strategie auf Öl** (Lock `noise_area_oel_gegenprobe_20261014`,
4 feste Versuche, keine Optimierung)

| Brutto bps/Trade | IS 16–22 | OOS 23–09/25 | Tresor |
|---|---|---|---|
| Öl, Index-Uhr, Paper | −1,0 | −1,6 | **−13,6** |
| Öl, NYMEX-Uhr 09:00–14:30, Paper | +2,4 | 0,0 | −5,5 |
| Öl, NYMEX-Uhr, K2 (1. Trade, bis Schluss) | +4,4 | −1,0 | −7,7 |
| Ausbruch hält bis Schluss (Öl, Index-Uhr) | 39 % | 45 % | **28 %** |

→ **Öl hat keinen Noise-Area-Edge** (netto überall negativ). Die
Paper-FAQ Q13 mit Rohstoffen trägt mit unseren CFD-Kosten nicht.
**Im Tresor bricht die Ausbruchs-Persistenz bei Öl noch stärker ein als bei
den Indizes.** Die Dämpfung der Intraday-Trends 2025/26 ist also nicht
index-spezifisch, was gegen eine reine SPX-Gamma-Erklärung spricht.

**C – beschreibend: Index-Trades nach Öl-Merkmal** (Paper-Config, alle Perioden offen)

- **Die Öl-Index-Korrelation (20 Tage) kippt 2026 ins Negative.** Median
  SP500 2016–25 durchgehend +0,06 bis +0,45, 2026 **−0,45** (NASDAQ −0,32).
- **Im Tresor verdient die Strategie nur an Tagen mit stark negativer
  Korrelation:** K20 < −0,2 bringt SP500 +2,7 (n 123) und NASDAQ +9,5 (n 85).
  Bei K20 ≥ 0 sind es −8,6 bis −9,3 bzw. −3,9 bis −7,7. Im IS war die
  Korrelation egal.
- **An starken Öl-Tagen läuft das Momentum in jeder Periode am besten.**
  NASDAQ im Tresor +9,9 bps, so viel wie im IS; ruhige Öl-Tage −9,4. Das ist
  mit der Bewegung bis 16:00 gemessen, also nicht vorab bekannt.
- „Öl lief gegen die Ausbruchsrichtung“ ist im IS besser (SP500 6,5 statt
  2,1, NASDAQ 12,1 statt 5,0), wie beim ORB. Im Tresor ist der Unterschied weg.

**Lesart (Hypothese):** 2026 gibt es zwei Arten von Tagen. Makro-/Öl-Schock-
Tage (Öl gegen Aktien, große Öl-Bewegung) tragen weiterhin echte Trends. Die
„normalen“ Tage, an denen Öl und Aktien gemeinsam driften, sind
mean-reverting geworden.

**B – Öl als Filter** (Lock `noise_area_oel_filter_20261014`, 8 vorab feste
Regeln + Regel 9 „Öl bewegt“ nachträglich und vorbelastet, 18 Versuche;
Auswahl nur IS 2016–22)

| Netto bps/Trade | IS | OOS | Tresor |
|---|---|---|---|
| SP500 Basis | +2,0 | +1,2 | −3,0 |
| SP500 **Gewinner „8 Öl ruhig“** | +3,0 | +0,8 | **−1,9** |
| SP500 „3 nur bei K20 < 0“ | +3,5 | −1,5 | +0,8 |
| NASDAQ Basis (kein Gewinner) | +6,6 | +2,7 | −2,2 |
| NASDAQ „7 Öl gegen“ (knapp zu wenig Trades) | +10,0 | +1,4 | −4,3 |
| NASDAQ „3 nur bei K20 < 0“ | +5,9 | +4,0 | +1,7 |

→ **Kein Filter rettet den Tresor.** Auf SP500 halbiert der Gewinner den
Verlust nur, er läuft ab 15.10. im Forward mit (Stichtag 31.03.2027).
NASDAQ erfüllt keine Regel die vorab festgelegten Kriterien. „Nur bei
negativer Öl-Korrelation“ ist die einzige Regel, die im Tresor bei beiden
Indizes positiv ist. Sie war im IS aber dünn, und auf SP500 war das OOS
negativ. Für einen Beleg ist sie zu schwach, als Hinweis passt sie zur
Lesart oben.

## Öl-Optimierung auf 2026: welche Faktoren tragen? (14.10., explorativ)

Nutzerauftrag nach Bestätigung aller Annahmen. Skript
`scripts/research_noise_area_oel_fit2026.py` (screen / fit / evaluate), Lock
`noise_area_oel_fit2026_20261014` (16.848 Versuche). Angepasst auf das ganze
Jahr 10/25–09/26, kein OOS aus 2026, Forward ab 15.10.2026, Stichtag
31.03.2027. Basen: Paper-Config oder K2 (nur 1. Trade, halten bis 16:00).

**Einzelfaktoren, netto bps je Trade** (2016–22 / 2023–09/25 / Fit 10/25–09/26):

| Faktor | NASDAQ K2 | NASDAQ Paper | SP500 Paper |
|---|---|---|---|
| ohne | 10,7 / 4,1 / 5,4 | 6,6 / 2,7 / −2,2 | 2,0 / 1,2 / −3,0 |
| **Öl-Index-Korr. 20 T. < 0** | **13,3 / 6,9 / 12,9** | 5,9 / 4,0 / 1,7 | 3,5 / −1,5 / 0,8 |
| **Öl-Index-Korr. 60 T. < 0** | **24,8 / 6,2 / 11,7** | 10,9 / 1,6 / 4,2 | 3,5 / −0,8 / 0,2 |
| Öl bewegt ≥ 1× Median | 12,8 / 4,4 / 9,4 | 6,2 / 1,6 / −0,2 | 1,1 / 1,6 / −3,5 |
| Öl gleich / gegen Trade | 7,2 / 3,5 / 7,3 · 13,5 / 1,5 / 1,8 | uneinheitlich | uneinheitlich |
| Gap, Öl-Vola, Öl-5-Tage-Trend | uneinheitlich | uneinheitlich | uneinheitlich |

**Raster-Gewinner:**
- **NASDAQ:** K2 + Korrelation 40 T. < −0,1 + Öl hat sich ≥ 0,5× Median bewegt:
  Fit +28,0 bps/Trade (57, t 2,5), **DSR 0,03**. Rückblick: 2016–22 +22,7
  (79), 2023–09/25 **−4,9** (67). Die Top 50 sind fast alle „K2 + negative
  Korrelation“ (37 × K2, 46 × Korrelationsschwelle).
- **SP500:** Kein Kandidat (bester t 1,1, DSR 0,001). Der Gewinner schadet
  im Rückblick (2016–22 −4,3).

**Befund – was den Edge profitabel halten könnte:**
1. **Negative Öl-Index-Korrelation ist der einzige Faktor, der in allen
   drei Perioden trägt**, und das nur auf NASDAQ mit dem K2-Ausstieg. Lesart:
   An Tagen im Öl-/Makro-Schock-Regime gibt es echte Intraday-Trends. 2026
   ist dieses Regime die Regel (Korrelation −0,3 bis −0,45), früher war es
   die Ausnahme. Deshalb waren es früher wenige Trades.
2. **Der Ausstieg ist der zweite Hebel:** nur den ersten Ausbruch nehmen und
   bis Schluss halten statt VWAP-Stop. Das passt zur Tresor-Diagnose.
3. **SP500 hat keinen tragenden Öl-Faktor.**
4. Der Raster-Gewinner ist überangepasst (2023–25 negativ). Robuster wäre
   die einfache Regel „K2 + Korrelation 60 T. < 0“. Sie wurde aber nicht
   nach der Auswahlregel gewählt und steht deshalb nicht im Forward-Lock
   (Vorschlag an den Nutzer, 14.10.).

## Forward-Kandidat: NASDAQ K2 + Öl-Korrelation 60 T. < 0 (14.10.)

Nutzerentscheid. Skript `scripts/forward_noise_area_k60.py`, Lock
`noise_area_oel_k60_forward_20261014`, Forward 15.10.2026–31.03.2027.
Regel: NASDAQ, Noise Area VM 1 / LB 90, nur erster Ausbruch des Tages
(10:00–15:30), kein Stop, Exit 16:00; nur an Tagen mit Korr(Öl, NASDAQ,
60 T. bis Vortag) < 0. Kosten 1,29 bps.

**Backtest auf 100k, jede Periode startet bei 100k. VORBELASTET:** Die
Regel wurde nach Sicht auf alle Perioden gewählt.
„1 % Risiko“ heißt: Eine Tagesbewegung (Vola 14 T.) kostet 1 % (Hebel ≤ 4),
weil die Regel keinen Stop hat.

| | IS 07/16–12/22 | OOS 01/23–09/25 | Tresor 10/25–09/26 |
|---|---|---|---|
| Trades | 140 | 147 | 87 |
| Filter offen (Anteil Tage) | 15 % | 39 % | 68 % |
| **1x Notional:** Endstand / MaxDD | 140.578 / −3,9 % | 109.234 / −5,9 % | 110.370 / −5,2 % |
| PF / Treffer | 2,15 / 61 % | 1,29 / 54 % | 1,48 / 54 % |
| **1 % Risiko:** Endstand / MaxDD | 129.081 / −3,2 % | 106.974 / −6,2 % | 113.443 / −3,2 % |
| Ø Verlierer / schlimmster Trade (% Konto) | −0,46 / −1,84 | −0,49 / −1,61 | −0,41 / −1,70 |
| Dyn. Paper-Sizing (2 %): Endstand / MaxDD | 162.271 / −6,4 % | 114.241 / −12,2 % | 127.885 / −6,3 % |

Im IS stammen die Trades fast nur aus 2017 und 2022 (2018–21 war der
Filter fast nie offen). Trade-Liste: `noise_area_momentum/results/k60_forward_backtest_trades.csv`.

## SL / TP / Haltedauer für den K60-Kandidaten (15.10.)

Skript `scripts/research_noise_area_k60_sltp.py` (profil / raster), Lock
`noise_area_k60_sltp_20261015`. M1-Simulation; trifft eine Bar SL und TP,
zählt der SL. Abstände in Tagesvola σ (14 T.). Raster mit 9 Punkten
(SL keiner/0,5σ/1σ × TP keins/1σ/2σ × Halten 16:00/240/120 Min.), Auswahl
nur auf IS, OOS und Tresor vorbelastet.

**Haltedauer-Profil, Ø brutto bps seit Einstieg:**

| | 30 Min. | 60 Min. | 120 Min. | 240 Min. | bis 16:00 |
|---|---|---|---|---|---|
| IS | 6,4 | 4,0 | 13,0 | 16,4 | **26,0** |
| OOS | 2,4 | 3,9 | 2,6 | 6,7 | **7,5** |
| Tresor | 2,1 | −1,1 | −1,2 | 2,5 | **13,0** |

→ **Der Ertrag entsteht in den letzten Stunden.** Im Tresor stehen die
ersten 4 Stunden bei ~0. Wer früher aussteigt, verschenkt den Edge.
MAE: Nur ≤ 1 % der Trades fallen unter −1σ und werden danach doch
Gewinner. Unter −0,5σ sind es 5–9 %.

**Raster, netto bps je Trade (IS / OOS / Tresor):**
- **Basis: kein SL, kein TP, bis 16:00: 24,7 / 6,2 / 11,7. Bester IS-Wert,
  also eingefroren. Keine Variante schlägt sie, kein zusätzlicher Forward.**
- TP 1σ oder 2σ: kaum Unterschied (23,1 / 7,0 / 10,2 bzw. 23,8 / 5,7 / 11,7).
- SL 1σ: 22,7 / 4,8 / 7,1. Kostet etwas, deckelt aber den Verlust je Trade.
- SL 0,5σ: Der Tresor kippt (−1,8).
- Halten 240 oder 120 Min.: in jeder Periode schlechter, im Tresor ~0 bzw.
  negativ.

**1 % Risiko auf 100k, Basis gegen SL 1σ** (Endstand / MaxDD / schlimmster Trade):

| | IS | OOS | Tresor |
|---|---|---|---|
| Basis (1σ = 1 %, ohne Stop) | 128.966 / −3,3 % / −1,83 % | 106.976 / −6,2 % / −1,61 % | 113.424 / −3,2 % / −1,71 % |
| SL 1σ (echtes 1R = 1 %) | 128.266 / −2,8 % / −1,03 % | 103.851 / −7,5 % / −1,03 % | 109.549 / −3,9 % / −1,01 % |

→ Mit SL 1σ wird „1 % Risiko“ zu einem echten 1R mit Deckel. Das kostet
im OOS und Tresor etwa 3–4 Prozentpunkte Ertrag.

## K60 auf einem TTP-Konto (16.10., für Fremdkapital)

Skript `scripts/research_noise_area_k60_ttp.py` (beschreibend, vorbelastet).
Setup: 1 % der aktuellen Equity je Trade, **SL 1σ** (echtes 1R), **Exit
15:55** (Puffer vor dem Kassaschluss; 16:00 zum Vergleich). TTP-USTEC-Kosten
gemessen: 0,56 bps Spread + Slippage = 1,32 bps. TTP-Regeln: Tageslimit 3 %
(intraday), Gesamt-DD 7 % trailing, Ziel +10 %.

| Exit 15:55, ab 100k | IS 07/16–12/22 | OOS 01/23–09/25 | Tresor 10/25–09/26 |
|---|---|---|---|
| Trades / Treffer | 140 / 62 % | 147 / 55 % | 87 / 51 % |
| Endstand | 131.435 | 102.783 | 109.716 |
| MaxDD Schluss / intraday | −2,5 / −3,1 % | −6,7 / **−7,2 %** | −3,5 / −4,0 % |
| PF / Ø R | 2,07 / +0,20 | 1,08 / +0,02 | 1,50 / +0,11 |
| Ø Gewinner / Verlierer (R) | +0,61 / −0,48 | +0,46 / −0,52 | +0,63 / −0,42 |
| schlechtester Trade | −1.315 | −1.091 | −1.103 |
| max. Verluste in Folge | 5 | 6 | 3 |
| Tageslimit- / 7-%-Brüche | 0 / 0 | 0 / **1** | 0 / 0 |
| Ziel +10 % | 10.08.2017 | nein | nein (+9,7 %; mit Exit 16:00 am 16.06.2026) |

**Befund:** Mit Stop ist das Risiko sauber gedeckelt (kein Trade über
~1,3 %). Allein ist die Strategie für eine TTP-Challenge aber zu langsam
und zu dünn. 2023–25 lief sie ~seitwärts, und 2025 brach sie einmal das
7-%-Trailing-Limit. Die Challenge-Simulation (Start alle 5 Tage, max.
1 Jahr) bestand im OOS 0 %, 25 % der Starts brachen. Im Tresor ist die
Quote durch das kurze Fenster verzerrt. Sinnvoll ist sie eher als
zusätzliches Bein im Funded-Portfolio (wenig Trades, nur Öl-Schock-Regime)
als allein.

## Kombination K60 + Öl-gefilterte ORB auf TTP (16.10.)

Skript `scripts/research_kombi_k60_orb_oel.py` (beschreibend, alles eingefroren).
ORB-Bausteine aus [[orb-gegenprobe-oel]]: **O1** = IS-validiert („Öl 09:00–09:45
gegen Ausbruch“, DSR 0,96/0,99), **O2** = 2026-Fit (Korrelationsregime → Trend-Tage +
Öl gegen; DSR ~0, auf den Tresor angepasst). SP500 + NASDAQ, R netto.
Korrelation der Tages-P&L K60 ↔ ORB: +0,07 bzw. +0,09 über alle Tage, +0,4 an
den ~100 Tagen mit beiden Trades.

**Alles mit 1 % je Trade:** Die ORB dominiert das Risiko. MaxDD ORB 17–39 %,
das 7-%-Trailing-Limit bricht in jeder Periode in den ersten Wochen. Die
Kombi ist dann nicht TTP-tauglich (Bestehensquote 38–48 %, ab 2023 25–34 %).

**Risiko-Aufteilung** (ab 100k je Periode; Bestehensquote = Start alle 5 Tage, 1 Jahr Laufzeit):

| ORB / K60 je Trade | Tresor Endstand / MaxDD | bestanden / gebrochen (2016–25) | bestanden / gebrochen (ab 2023) |
|---|---|---|---|
| O1 0,25 % + K60 0,5 % | 93.485 / −11,0 % | 56 / 3 % | 26 / 10 % |
| **O1 0,25 % + K60 1 %** | 97.840 / −11,2 % | **64 / 11 %** | 45 / 28 % |
| O1 0,5 % + K60 1 % | 87.066 / −21,0 % | 75 / 22 % | 64 / 36 % |
| O2 0,25 % + K60 0,5 % | 128.771 / −3,3 % | 51 / 7 % | 30 / 0 % |
| **O2 0,25 % + K60 1 %** | 134.664 / −5,0 % | **63 / 7 %** | 42 / 0 % |
| O2 0,5 % + K60 1 % | 163.675 / −6,5 % | 55 / 45 % | 39 / 59 % |

**Befund:** K60 mit 1 % neben einer kleinen ORB (0,25 %) ist die beste
Mischung. Mehr K60 hebt die Bestehensquote (O1: 56 → 64 %). Mehr ORB-Risiko
bringt schnellere Ziele, aber viel mehr Brüche. **O1 verliert im Tresor**
(Kombi −2 bis −13 %), K60 federt das nur ab. **O2 sieht im Tresor stark
aus, ist aber genau darauf angepasst** und belegt nichts. Entscheiden kann
erst der Forward-Test (alle drei Bausteine bis 31.03.2027).

## Challenge-Gewichtung TTP / IQ (16.10., MC + Walk-Forward)

Nutzerauftrag, Plan freigegeben. Skript `scripts/research_challenge_k60_orb_gewichtung.py`
(optimise / check / register / evaluate), Lock `challenge_k60_orb_oel_gewichtung_20261016`
(4.368 Versuche). Methode wie die FK-Gewichtung (03.10.). Ziel: höchster Median-Ertrag
pro Jahr bei P(Bruch) ≤ 5 % (Block-Bootstrap, 2.000 Pfade). Wahl: K60 aus / SL 1σ /
ohne Stop; ORB SP500 und NASDAQ je aus / O1 / O2; max. Trades pro Tag 1–3;
Risiko 0,25–1 % je Bein.

**Ergebnis (eingefroren, Forward 19.10.2026–31.03.2027):**

| | TTP | IQ |
|---|---|---|
| Gewinner | **K60 ohne Stop 1,0 % + ORB NASDAQ O2 0,25 %, max. 2/Tag** | **K60 ohne Stop 0,75 % + ORB NASDAQ O2 0,25 %, max. 2/Tag** |
| MC: Median / P(Bruch) / P(Ziel vor Bruch) | +8,2 % / 5,0 % / 46 % | +7,1 % / 5,0 % / 53 % |
| ohne O2 (O1 statt O2) | +7,8 % / 4,0 % / 42 % | +6,7 % / 3,1 % / 48 % |
| Ereignis-Sim Endstand IS / OOS / Tresor | 161.590 / 116.021 / 126.591 | 150.816 / 114.513 / 122.829 |
| dito ohne O2 | 173.797 / 116.297 / 110.823 | 162.209 / 114.788 / 107.507 |
| MaxDD intraday (max. über Perioden) | −5,8 % (ohne O2 −5,8 %) | −4,6 % (ohne O2 −4,5 %) |
| Kosten ×2 | kein Bruch, Tresor 123.909 | kein Bruch, Tresor 120.541 |
| Bestehensquote 1 Jahr (alle / ab 2023), 0 % Brüche | 35 / 39 % (ohne O2 35 / 9 %) | 43 / 51 % (ohne O2 47 / 14 %) |

- **Struktur ist eindeutig:** K60 trägt das Risiko. ORB läuft nur auf NASDAQ mit
  0,25 %, SP500-ORB fällt raus. K60 **ohne Stop** schlägt SL 1σ bei beiden
  Challenges. Auch mit konservativem ORB-Tief (jeder Trade −1R) bleibt die Wahl gleich.
- **Walk-Forward** (IS bis Y−1 → Jahr Y): wählt jedes Jahr K60 0,5–1 % + ORB-O1
  0,25 %, nie O2. OOS-Jahre TTP −1,4 / +24,9 / +11,4 / +4,5 / +3,7 / +1,0 %, IQ
  +0,2 / +13,9 / +9,5 / +8,8 / +1,5 / +5,2 %. Der MaxDD blieb jedes Jahr unter dem
  Limit (TTP ≤ 5,7 %, IQ ≤ 5,9 % bei 6 % Grenze, also knapp).
- **Vorbelastet:** Der Vorteil von O2 kommt nur aus 2026, auf das O2 angepasst ist.
  Ohne O2 sinkt die Bestehensquote ab 2023 auf 9–14 %. Die Ziele sind langsam
  (Median ~160 Tage).

**Übertragbare Lehre**: Wenn die Paper-Nachbildung brutto exakt trifft,
entscheidet bei Intraday-Index-Strategien die Kostendifferenz zwischen
ETF und CFD (Faktor 3–5) über die Hälfte des Sharpe. Das zuerst rechnen.

**Nicht verfolgt (nur notiert)**: das Diversifikations-Portfolio aus
Paper Q13 (33 Futures, Sharpe 1,65). Das bräuchte Futures-Daten, siehe
Ideen-Inbox „CFDs → echte Futures“.
