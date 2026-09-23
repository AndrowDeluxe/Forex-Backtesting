# Resource: 24h-Renditestruktur & globale Informationskette

Destillat aus drei vom Nutzer am 2026-09-22 geteilten Papers. Gemeinsames
Thema: **wo im 24-Stunden-Zyklus Rendite bzw. Information tatsächlich
sitzt** -- und damit die Frage, ob unser [[ny-open-orb-sp500]] im richtigen
Fenster arbeitet und ob daneben ein eigenes Fenster frei liegt.

**Prozess-Einordnung**: Papers laufen nach `CLAUDE.md` durch den vollen
8-Phasen-Prozess ([[backtest-standard-process]]), NICHT durch den
[[edge-card-workflow]] (der gilt nur für händisch entwickelte Strategien).
Dieses Dokument ist **Phase 2 (Sichtung) + Phase 3 (Screening)**. Kein Code,
kein Backtest. Die Edge-Card-Felder tauchen unten trotzdem auf -- aber
angewandt auf den ORB, der sehr wohl eine händische Nutzer-Strategie ist.

---

## Paper 1 -- Market Return Around the Clock: A Puzzle

**Capture**
- Autoren/Jahr: Oleg Bondarenko (UIC), Dmitriy Muravyev (MSU), Fassung 2021-08-25
- Quelle: SSRN 3596245, als PDF geteilt
- Erfasst am: 2026-09-22
- Daten: E-mini S&P 500 (ES), 10-Sekunden-Bars, Jan 2004 - Jul 2018,
  + Out-of-Sample 2020; VIX-Futures ab 2014-06-22

**Organize**
- Tags: time-of-day-returns, index-futures, uncertainty-resolution,
  overnight-premium, VIX-futures, intraday-seasonality
- Verwandt: [[ny-open-orb-sp500]], [[orb-exit-logik-neubewertung]],
  [[opening-range-breakout]]

**Distill -- Kernbefunde**

1. **Die gesamte durchschnittliche Aktienmarktrendite entsteht in vier
   Nachtstunden**: 23:30-03:30 ET ("EU-open", = **05:30-09:30 Berlin**,
   ganzjährig konstant, da EU und US beide auf Sommerzeit umstellen).
   +7,60 % p.a., t=6,35, Sharpe 1,67, SD 4,55 %, Skew **+1,64**, MaxDD 8 %.
   In **jedem** der 15 Jahre positiv.
2. **Der Rest des Tages ist ein verrauschtes Null**: -0,80 % p.a., t=-0,17,
   SD 17,79 %, MaxDD 66,4 %.
3. **Die US-Cash-Session trägt ~ nichts** (Tab. IA.2, 09:30-16:15 ET):
   +3,44 % p.a., **t=0,89**, Sharpe 0,23, Skew -0,50, MaxDD 44,55 %.
4. **Zweite Hälfte des Fensters trägt fast alles**: 01:30-03:30 ET
   (07:30-09:30 Berlin, Frankfurt-/London-Open) = 5,90 der 7,60 Punkte.
   Erste Hälfte nur 1,70.
5. **Zig-Zag um den US-Close**: 14:00->15:45 ET +6,11 % p.a. (t=2,81),
   15:45->18:00 -5,44 % (t=-3,36). Davon liegen **-2,83 % (t=-2,89) erst
   NACH 16:15 ET** (Tab. IA.2 "Post US-close") -- also außerhalb jeder
   ORB-Haltedauer.
6. **Mechanismus (Uncertainty Resolution)**: Unsicherheit akkumuliert
   nachts, weil die kritische Masse an Investoren fehlt; sie wird aufgelöst
   -- mit Preisanstieg -- wenn die Europäer eintreffen. Gestützt durch:
   VIX-Futures steigen vor EU-open (+39,6 % p.a., t=2,8) und fallen im
   EU-open (-46,3 %, t=-5,2); Preise werden im EU-open 14 % effizienter
   (Varianz-Ratio 1,08->0,95).
7. **DST-Test trennt Ursache sauber**: Asien hat keine Sommerzeit. Das
   Muster bleibt in europäischer Zeit fest und verschiebt sich in
   asiatischer -- also **Europas Open, nicht Asiens Close**.
8. **EU-Feiertage als Gegenprobe** (81 Tage, London+Frankfurt zu, US offen):
   EU-open-Rendite fällt auf -0,49 % (vs. +7,78 %, Differenz t=-2,2,
   signifikant). Die Rendite verschiebt sich nach hinten in die US-Stunden
   (+9,49 % vs. -0,37 %) -- **diese zweite Differenz hat aber nur t=1,5,
   ist also NICHT signifikant.** Richtung stimmt, Beleg ist schwach.
9. **Data-Snooping sauber adressiert**: Bonferroni über alle 4h-Fenster ->
   p=5x10^-8; White (2000) Reality Check, 99 %-Perzentil der Max-t-Verteilung
   = 3,7 für 4h-Fenster, EU-open erreicht 6,35.
10. **Handelbar, aber kostenempfindlich**: naive Version (täglich rein/raus)
    7,76 % -> **2,58 % nach Kosten** (Sharpe 1,65 -> 0,55). Konditionale
    Version (nur die ~40 % Tage mit hoher erwarteter Rendite, Prädiktoren
    Delta-VIX + Overnight-Realized-Vol, OOS R2=6,57 %) -> **4,61 % nach
    Kosten, t=4,57, Sharpe 1,20**. Kapazität ~9 Mrd. USD.
11. Gilt auch für **E-mini Nasdaq 100 und E-mini Dow** (Fig. IA.2).

**Wichtige Vorbehalte**
- Sample endet Jul 2018 (+2020). **Acht Jahre unbekannter Decay bis heute.**
- Kosten im Paper = CME-Futures (1 Tick, ~1,71 bps + 2,50 USD/RT).
  Unsere Index-CFDs sind tagsüber mit 0,48-0,84 bps gemessen -- aber
  **nicht in diesem Nachtfenster**, wo CFD-Spreads typisch aufgehen.
- Der Zig-Zag ist der schwächste Befund des Papers und wird von den Autoren
  selbst so markiert: Peak um 10 Min. verschoben halbiert ihn
  (15:35 -> 7,76 %, 15:55 -> 5,30 %); nach Kosten bleibt +0,98 % (t=0,38);
  2017 +0,2 %, 2018 -6,2 %.
- Die konditionalen Prädiktoren (Delta-VIX, Overnight-Vol) sind **für das
  EU-open-Fenster** belegt. Für das einzige US-Session-Muster, das das
  Paper testet (Zig-Zag, Tab. 8 Panel B), ist **Delta-VIX insignifikant
  (t=0,5)**, und die gesamte Vorhersagbarkeit verschwindet (R2 2,0 %->0,2 %),
  wenn man die 10 % höchsten VIX-Tage entfernt.

---

## Paper 2 -- The Global Relay (Kinoshita 2026, SSRN 7276738)

**Capture**
- Ryo Kinoshita, Kobe University; Working Paper (preliminary draft)
- Daten: yfinance-Tagesdaten ab Dez 2009; Walk-Forward-Logit, 1.250-Tage-Fenster

**Distill -- Kernbefunde**
1. **Drei-Markt-Schleife** NY -> Asien -> Europa -> NY. Gemessen wird der
   "Boost": Zugewinn an Directional Accuracy über die Eigenmomentum-Baseline
   des Zielmarkts.
   - Leg 1 NY->Asien: **+15,0 pt** (9 Ziele)
   - Leg 2 Asien->Europa: **+13,8 pt** (12 Paare)
   - Leg 3 Europa->**NY**: **+0,07 pt** (12 Paare, Spanne -0,36 bis +0,48)
   - Gegenrichtung Europa->Asien: **+10,6 pt** -- also kein "Hop-Count"-Zerfall
2. **Nur der Leg IN New York hinein ist tot.** Gilt unabhängig davon, welcher
   Markt als Startpunkt gewählt wird; überlebt Cluster-robuste SE
   (zweiseitig geclustert, p<0,0001); reproduziert sich in einem separaten
   Energie-Kanal (XLE/1618.T/EXH1.DE: +15,98 / +9,90 / **-0,33**).
3. **Null-Parameter-Regel**: einfach dem Vorzeichen der Quell-Rendite folgen
   erreicht auf Leg 1/2 fast die volle Logit-Genauigkeit (69,78 vs. 70,97;
   66,11 vs. 67,50). Auf Leg 3: **48,89 %, also UNTER Zufall, und unter 50 %
   für jedes einzelne Paar.**
4. **Achtung Fallstrick**: Leg 3 sah zunächst nach DA~72 % aus -- reine
   Scheinkorrelation (europäische Handelszeit überlappt mit der Zeit NACH
   dem NY-Open). Erst die Kontrolle auf NY-Eigenmomentum ließ ihn auf null
   zusammenfallen.
5. **Eigenmomentum-Baselines der US-Indizes** (Tab. 4, NY sagt den eigenen
   Opening-Gap vorher): S&P 500 56,01 %, Dow 52,76 %, NDX 55,91 %,
   Russell 55,55 %.

## Paper 3 -- What Crosses Borders? (Kinoshita 2026, SSRN 7091018)

**Capture**: Dez 2009 - Jan 2024, 9 Asien-Pazifik-Märkte + 17 TOPIX-Sektoren

**Distill -- Kernbefunde**
1. **Träger ist die NY-Cash-Session, nicht die Nacht**: Open->Close allein
   reproduziert **98,6 %** der vollen Close-to-Close-Vorhersagekraft;
   Cash-Session schlägt Overnight in **26 von 26** Zielen (+6,6 pp Ø).
2. **Futures-Drift nach dem NY-Close trägt nichts** (-0,4 pt) -- schließt
   Live-Futures-Leakage aus.
3. **Beta-Law**: Gap-DA = 60,07 + 16,26 x Beta, R2=0,49, p=0,0018. Unter
   disjunktem Sample fällt es auf R2=0,13, p=0,15; repliziert aber in
   11 europäischen Sektoren (R2=0,535). **Versagt auf Länderebene** (n=9,
   p=0,21).
4. **Energie ist der einzige Sektor mit eigenem Träger** (+6,6 Punkte, ~6 Sigma).

**Vorbehalte zu 2+3**: Preprints eines einzelnen Doktoranden, nicht
peer-reviewed. Zielgröße ist durchgehend der **Opening-Gap**
(log(Open/Vorclose)), nicht die Richtung der Intraday-Bewegung danach.

---

## Synthese: was das für uns heißt

Die drei Papers beschreiben dieselbe Landkarte aus zwei Richtungen:

| Fenster (Berlin) | Paper 1: Rendite | Kinoshita: Information |
|---|---|---|
| 05:30-09:30 (EU-Open) | **die ganze Jahresrendite** | -- |
| 15:30-22:00 (US-Cash) | ~ 0 (t=0,89) | **die Quelle für alle anderen** |
| 22:00-05:30 (Asien) | ~ 0 | Empfänger |
| Europa -> NY | -2,83 % nach Close | **tot (+0,07 pt)** |

New York **produziert** Information und **erntet keine Risikoprämie**.
Europa **erntet die Prämie** und **produziert keine Information für NY**.
Das sind zwei verschiedene Aussagen über dasselbe Fenster, und beide sind
für unseren ORB relevant -- siehe [[ny-open-orb-sp500]], Abschnitt
"Externe Paper-Einordnung 2026-09-22", und den neuen Edge-Kandidaten
[[eu-open-renditefenster]].
