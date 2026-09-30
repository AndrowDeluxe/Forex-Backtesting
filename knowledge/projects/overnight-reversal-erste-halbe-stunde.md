# Project: Overnight-Reversal in der ersten halben Stunde (US-Indizes)

**Status**: **ABGESCHLOSSEN, NEGATIV (2026-09-30), verworfen in Phase 3/4.**
Nicht bauen. Der Effekt ist auf unseren Daten 3-8x schwaecher als im Paper,
die Paper-Strategie ist nach Kosten negativ, und die einzige Teilvariante mit
t~2 lebt ausschliesslich in den ersten fuenf Minuten nach dem Open-Print --
eine M5-Bar spaeter eingestiegen ist sie auf allen drei Indizes ~0.
Skript: `scripts/research_overnight_reversal_fh.py`, Rohzahlen:
`Claude outputs/overnight_reversal_fh.json`.

## Phase 2 -- Paper

Iwanaga/Sakemoto, *Does overnight return predict the first half-hour return
for U.S. market indices?* (SSRN 5807282, 5. Aug. 2026). SPY 1-Min (LSEG,
Mid-Preise), 1996-2024, n=7.188.

- **These**: hohe Overnight-Rendite (Close 16:00 t-1 -> Open 09:30 t) sagt
  eine NEGATIVE Rendite der ersten 30 Minuten voraus. Erklaerung:
  "opposing clienteles" -- Retail kauft ueber Nacht, Arbitrageure verkaufen
  tagsueber (Berkman 2012, Akbas 2022, Lou 2019).
- **Regel** (Gl. 6, keine freien Parameter): R_ON < 0 -> long 09:30-10:00,
  sonst short. Taeglich flat.
- **Behauptet**: b = -9,19 (t=-5,16, R^2 3,8 %); SPY 7,76 % p.a., SR 1,51
  brutto; mit Bid-Ask 4,83 % / SR 0,94. Auch QQQ/IWM/DIA/XLF, NICHT
  international.
- **Warnsignale schon im Paper**: 2010-2024 nur b=-5,99, **t=-1,90**
  (Tab. 4d); Fig. 2 ist ab ~2010 flach bis auf den Sprung 2020; getragen
  von GFC und COVID-Phase I (Tab. 5). Die Hochvola-Splits (Tab. 3) sortieren
  nach der Vola der ersten 30 Min. selbst -- nicht ex ante handelbar.

## Phase 3 -- Screening

Einfaches Signal, keine State-Machine, 1:1 nachbaubar auf unseren
Dukascopy-Index-CFDs (SP500/NASDAQ/US30, M5, NY-Zeit). Pflichtcheck aus
[[eu-open-renditefenster]] zuerst: Sample-Ende (2024) und Jahresreihe ohne
bestes Jahr, vor jedem Weiterbau.

## Phase 4 -- Nachbau 2016-07 bis 2026-09 (~2.530 Tage je Index)

**Regression R_FH auf R_ON** (b in Paper-Einheiten, Newey-West-t):

| | Paper SPY | SP500 | NASDAQ | US30 |
|---|---|---|---|---|
| gesamt | -9,19 (t -5,2) | -1,23 (t -0,9) | -3,47 (t -2,3) | -3,25 (t -1,6) |
| ohne 2020 | -- | -1,07 (t -0,7) | -3,18 (t -1,8) | -0,40 (t -0,2) |
| 2025-26 (nach Paper) | -- | -3,19 (t -1,0) | -6,59 (t -1,9) | -0,98 (t -0,3) |

Vorzeichen von b wechselt jahresweise (SP500: 4 von 11 Jahren positiv).

**Paper-Strategie (Gl. 6)**, brutto -> 1 bp Round-Trip:

| | SP500 | NASDAQ | US30 |
|---|---|---|---|
| brutto gesamt | +1,44 % p.a., t 1,07 | +1,80 %, t 0,87 | +0,97 %, t 0,65 |
| brutto ohne 2020 | +0,48 %, t 0,35 | +1,23 %, t 0,58 | -0,03 %, t -0,02 |
| 1 bp, ohne 2020 | -2,04 % | -1,29 % | -2,55 % |

Die Short-Haelfte (short nach positivem ON) verliert auf allen drei
Indizes. Das Paper hat das Problem selbst schon angedeutet (Tab. A4: nach
negativem ON staerker).

**Teilvariante "nur long nach negativem ON"** -- der einzige Lichtblick:
+1,8 / +2,9 / +1,9 bps je Trade, t 2,0 / 2,3 / 2,0, Sharpe ~0,9. Drei
Gruende, warum sie trotzdem nicht traegt:

1. **Entry-Lag (Phase-6-Punkt p6_6, vorgezogen)**: Einstieg zum Open der
   09:35-Bar statt 09:30 -> **+0,27 / +0,13 / +0,14 bps**, t ~0,1-0,3.
   Der gesamte Effekt sitzt im 09:30-09:35-Fenster, also im Open-Print
   selbst. Ob das echte Liquiditaetsprovision oder ein Artefakt der
   CFD-Quote zur Cash-Eroeffnung ist, spielt keine Rolle: ein Bot, der per
   Scan-Zyklus einsteigt, kommt da nicht heran, und der Spread ist genau in
   dieser Minute am breitesten.
2. **Vergleich zu "immer long 09:30-10:00"**: das bringt schon +1,0 / +1,8 /
   +1,3 bps. Der Aufschlag durch das Signal ist ~0,6-1,1 bps.
3. **Kosten**: bei 1 bp ohne das beste Jahr 0,24 / 1,29 / 0,37 bps, t < 1.

**Konditionierung (nur ex-ante-Groessen)**: Vortags-RV20 ueber Median hilft
nur auf NASDAQ (t 2,1, ohne 2020 t 1,9), bei SP500/US30 nicht; oberes
Terzil |R_ON| hilft nirgends robust. Der Dukascopy-VIX beginnt erst
2022-10, daher RV20 statt VIX. Kein Kandidat, der ueber Mehrfachtest-Niveau
kaeme.

## Urteil

Verworfen in Phase 4. Phase 5/6 nicht angefangen -- Phase 6 auf einem
Erwartungswert von ~0 waere Theater (Lehre aus [[eu-open-renditefenster]]).
Konsistent mit dem Muster aus [[24h-renditestruktur-und-informationskette]]:
publizierte Intraday-Zeitfenster-Edges in US-Indizes, deren Sample in den
2010ern schon schwaecher wird, sind bei uns ab 2016 weg.

**Uebertragbare Lehre**: Ein Open-Reversal, der brutto mit t~2 auftaucht,
zuerst mit einer Bar Einstiegsverzoegerung rechnen. Hier hat diese eine
Zeile das Ergebnis vollstaendig erklaert -- vor jeder Kosten- oder
Robustheitsarbeit.

**Nicht verfolgt (nur notiert)**: Wechselwirkung mit unserem ORB
([[opening-range-breakout]]). Der Effekt liegt komplett in der
Range-bildenden ersten Bar und traegt danach nichts, deshalb ist kein
Richtungsfilter fuer ORB-Entries nach dem Range-Ende zu erwarten.
