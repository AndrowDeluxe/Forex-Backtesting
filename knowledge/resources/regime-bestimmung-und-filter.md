# Resource: Regime bestimmen und als Trading-Filter nutzen

Stand 02.11.2026. Auftrag Nutzer: Regimekarte (Landi) mit der Regime-Matrix/-Erkennung aus dem
Coaching (Angelo/Dennis) vergleichen, optimale Verbindung finden, Recherche zu guter Regime-
Bestimmung. Bezug: [[htf-daily-trade-edge-card]], [[quant-diskretionaer-fusion]] (Strang 3),
[[regimekarte-wachstum-inflation]], [[makro-faktoren-katalog]].

## 1. Die drei Bausteine im Repo

| Baustein | Quelle | Misst | Takt | Code |
|---|---|---|---|---|
| Regimekarte (Landi) | BIP × CPI First Prints (ALFRED) | Wachstum/Inflation: Vorzeichen, beschleunigt/verlangsamt | 6–7 Wechsel/Jahr, Median 31 Tage | `fusion_lab/macro_regime/` |
| Zinskurven-Regime (Angelo) | US 2y/10y (FRED), heute vs. vor 20 Tagen | Bull/Bear × Steepener/Flattener | **69 Wechsel/Jahr, Median 2 Tage**; 25 % Twist | `htf_daily_trade/macro.py` |
| Risk Regime Matrix (Dennis) | Coaching-Tabelle | Long/Short-Präferenz je Assetklasse je Regime | -- (Zuordnung) | `REGIME_DIR` in `macro.py` |

## 2. Vergleich (2003–2025, rein beschreibend)

- **Die beiden Erkennungen messen Verschiedenes.** Übereinstimmung der 4 Regime 26,6 % (Zufall
  25,2 %); Risk-on/off 51,8 % -- Münzwurf. Jede Zeile der Kreuztabelle ist fast gleich verteilt.
- Die Landi-„signs“-Linse ist 90 % der Zeit „Reflation“ (BIP- und CPI-YoY fast immer > 0) und
  taugt nicht als 4-Regime-Schalter; nur die „change“-Linse ist ausgewogen (je ~25 %).
- Das rohe Zinskurven-Regime ist als Tagesfilter **Rauschen** (Median 2 Tage). Mit 5 Tagen
  Bestätigung: 11 Wechsel/Jahr, Median 20 Tage.

## 3. Sagt die Matrix die Richtung voraus? (IS 2016–21, Lock `regime_quelle_vergleich`, 3 Versuche)

20-Tage-Folgerendite in Matrix-Richtung, nicht überlappend:

| Quelle | USD-Korb | Gold |
|---|---|---|
| Zinskurve roh | −2 bp, t −0,11 | +25 bp, t +0,48 |
| Zinskurve 5 Tage bestätigt | +14 bp, t +0,68 | **+93 bp, t +2,16, 60 % Treffer** |
| Landi change | −25 bp, t −1,37 | +9 bp, t +0,21 |

- **USD-Richtung aus dem US-Regime funktioniert mit keiner Quelle.** Plausibel: Ein Wechselkurs ist
  relativ; ein reines US-Regime sagt nichts über die Gegenwährung.
- **Gold mit bestätigtem Zinskurven-Regime** ist die einzige auffällige Zelle (1 von 6 -- bei 6
  Prüfungen nicht frei von Zufall). Mechanismus vorhanden: Bull-Phasen (fallende Renditen) stützen
  Gold, deckt sich mit WGC-Daten (Bear-Steepener belasten Gold) und mit `memory/residual_edge_gold_traegt_orb_ou_nicht.md`.
- Zusammen mit dem Daily-Edge-Test (`memory/daily_edge_typ_r_ohne_makro_kein_edge.md`): Regime-Gate hob
  Typ R kaum (+0,120 vs +0,116 R), in Typ C nur knapp über „gegen Regime“.

## 3b. Aktueller Stand (FRED bis 30.10.2026)

- Zinskurve roh: Goldilocks seit 29.10. (2y −22 bp, 10y −30 bp, Spread −8 bp in 20 Tagen); 5 Tage
  bestätigt noch Reflation. Matrix in beiden Fällen: USD short, Gold long.
- Landi-Karte: g↓ π↑ (Wachstum verlangsamt, Inflation beschleunigt) seit Anfang September, BIP 2,1 %,
  CPI 4,0 % YoY → Matrix „Inflation“: USD long, Gold short. USD-Signal widersprüchlich; Gold laut
  Zinskurve long. Nutzer 02.11.: Goldilocks = USD short (Matrix) ist richtig.

## 4. Recherche: Was gilt als gute Regime-Bestimmung?

- **Wachstum × Inflation (Bridgewater All Weather)** ist der Standard für die *Assetklassen*-Ebene;
  die Zuordnungen (Aktien/Credit in Goldilocks, Rohstoffe in Reflation, Anleihen in Deflation) sind
  in der Praxis Heuristiken und brauchen Out-of-Sample-Prüfung. Nowcast-Eingänge: PMI, LEI, CPI,
  Breakevens, Rohstoffindizes.
- **Zinskurven-Phasen** (Bull/Bear-Steepener/-Flattener): Praktiker-Evidenz, kleine Stichproben,
  Quellen widersprechen sich teils (Gold). Man: Bull-Flattener positiv für Aktien und USD.
- **FX braucht relative Makro-Daten.** Macrosynergy/JPMaQS: Wachstums-, Inflations- und
  Arbeitsmarkt-*Differenzen* sowie Terms of Trade sagen FX-Trends voraus -- nicht das Regime eines
  Landes.
- **Statistische Regime (HMM, Gaussian/t-Mixture):** Two Sigma (GMM auf 17 Faktoren, 4 Cluster),
  State Street (t-Mixture + GARCH). Für FX bescheidene, positive Out-of-Sample-Evidenz (Dueker &
  Neely); Hauptgefahr Look-ahead durch Anpassung auf die ganze Historie → nur mit rollierender
  Schätzung.
- **Turbulenz (Kritzman & Li 2010):** Mahalanobis-Abstand der Renditen; sagt den Beginn nicht
  voraus, hält aber Wochen an; Senken des Risikos bei FX-Turbulenz verbesserte Carry. Ein
  **Risiko-**, kein Richtungsfilter.

## 5. Empfehlung: wie verbinden

Nicht zu *einem* Regime verschmelzen (sie widersprechen sich statistisch), sondern als Schichten mit
klarer Rolle -- und als **Veto** statt Pflicht-Bestätigung, damit die Fallzahl bleibt:

1. **Strategisch (langsam):** Landi-Karte (change-Linse) → Assetklassen-Kontext für den Makro-
   Agenten, angezeigt, nicht gehandelt (`memory/regime_richtung_je_asset_ueberangepasst.md`).
2. **Taktisch Zinsen (mittel):** Zinskurven-Regime nach Angelo, **geglättet** (Bestätigung ≥ 5
   Tage oder längerer Vergleich, z. B. 60 Tage, plus Mindestbewegung in bp gegen Twist-Rauschen).
   Einsatz zuerst für **Gold** (einzige tragende Zelle) und zinssensible Assets.
3. **FX relativ:** Zinsdifferenz-Trend (2y Inland vs. 2y Ausland) und Wachstums-/Inflations-
   differenzen statt US-Regime; G8-Stärke nur für Continuation (bei Reversals schadet sie).
4. **Risiko:** Turbulenz-/Volatilitätsregime → Positionsgröße, nie Richtung.
5. **Ausgabe je Markt:** Score −1…+1 je Schicht; Trade-Filter = „keine Schicht dagegen“ (Veto),
   Risikostufe = Zahl der zustimmenden Schichten (passt zu den Risikostufen des Nutzers).

Spielregeln: wenige Parameter (eine Regel je Korb, nicht je Asset), jede Kombination ist eine
gezählte Variante; erst IS, dann OOS/Blind je einmal, dann Forward.

**Nutzerentscheid 02.11.2026: Schichtenmodell wird so umgesetzt.** Erster Baustein: [[filter-gold-zinskurve]]
(Zinsen-Schicht, wiederverwendbar). Zinsdaten-Quellen für die FX-Schicht dort recherchiert (EZB, MoF
Japan, Bank of Canada, Bank of England ✅; RBA blockt automatisierte Abrufe).

**Datenlücke (ursprünglich):** Tägliche 2y-Renditen für DE/UK/JP/AU sind auf FRED nicht frei (nur monatlich, und
OECD-Reihen enden still, `memory/oecd_reihen_auf_fred_tot.md`) → Quelle klären, bevor Schicht 3 gebaut wird.

## Quellen

- [FTSE Russell: Balancing exposure to macro regimes](https://www.lseg.com/en/ftse-russell/index-ideas/balancing-exposure-to-macro-regimes)
- [Growth × Inflation Quadrants (Überblick)](https://clawterminal.ai/blog/macro-regime-quadrants)
- [Two Sigma: A Machine Learning Approach to Regime Modeling](https://www.twosigma.com/articles/a-machine-learning-approach-to-regime-modeling)
- [State Street: Decoding market regimes with machine learning](https://www.ssga.com/library-content/assets/pdf/global/pc/2026/decoding-market-regimes-machine-learning-insights.pdf)
- [Kritzman & Li 2010, Skulls, Financial Turbulence, and Risk Management](https://rpc.cfainstitute.org/research/financial-analysts-journal/2010/skulls-financial-turbulence-and-risk-management)
- [Alpha Architect zu Kritzman & Li](https://alphaarchitect.com/skulls-financial-turbulence-and-risk-management/)
- [Man Group: A bull flattener – what happens next?](https://www.man.com/maninstitute/views-from-the-floor-2021-jun-29)
- [World Gold Council, Marktkommentar Aug. 2023 (Zinskurvenphasen)](https://www.gold.org/goldhub/research/gold-market-commentary-august-2023)
- [Macrosynergy: FX trading signals with regression-based learning](https://macrosynergy.com/?p=47467)
- [Macrosynergy: FX trading signals – common sense and machine learning](https://macrosynergy.com/research/tag/economic-data)
- [J.P. Morgan Macrosynergy Quantamental System](https://www.jpmorgan.com/insights/global-research/jpmaqs)
- [arXiv 2107.05535: asset-unabhängiges HMM](https://arxiv.org/pdf/2107.05535)
- [QuantStart: HMM-Regimefilter](https://www.quantstart.com/articles/market-regime-detection-using-hidden-markov-models-in-qstrader/)
