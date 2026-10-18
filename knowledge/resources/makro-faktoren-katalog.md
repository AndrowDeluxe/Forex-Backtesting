# Makro-Faktoren-Katalog (entdoppelt aus drei OneNote-Teilinventuren)

Konsolidierter Faktor-Katalog als Grundlage für (a) einen Makro-Agenten, der
wöchentlich Reports im Format "SMT Macro Desk" schreibt (Regime, G8-Ranking
Makro/Rates/Preis/Quant, Szenarien mit Signposts, Trades mit 5 Gates, Kein-
Trade-Regeln) und (b) spätere Tests nach dem Backtest-Prozess. Reines
Sammel-/Ordnungsdokument: **nichts hier ist getestet oder bewertet**, und es
steht nur drin, was in den drei Teil-Katalogen steht. Eigene Ordnungshinweise
sind mit [Anm.] markiert.

Kürzel für Quellen: **T1** = Makro Education (OneNote-Ordner "Makro
Education"), **T2** = Breakdowns und Bankreports, **T3** = News und
Auswirkungen / Quick Notes / Incentive-Kurs 2025. Dahinter der OneNote-
Seitenname bzw. die Bank. Eigene Kurzbeschreibungen, keine Zitate.

## Capture

- Quelle: OneNote "Finanzielle Freiheit Neu / Smart Money Trading", importiert
  10/2026 nach `fusion_lab/raw/onenote/`; Teilinventur vom 12.10.2026 (drei
  Teil-Kataloge in `fusion_lab/data/onenote_macro/`, dort nur lesend
  inventarisiert).
- Das Material ist gemischt: Kursfolien, Bank-PDFs (maschinell übersetzte
  OCR, oft verstümmelt), fremde Lehrtexte und wenige Seiten eigener
  Ausarbeitung. Wo die Teil-Kataloge Herkunft (eigen vs. Fremdmaterial)
  benennen, bleibt das unten im Hinweis "Güte" erhalten. Behauptungen ohne
  Beleg im Material (z. B. "manipulierte Daten", Gewichte 33-66 %) gelten als
  nicht belegt.

## Organize

- Thema/Tags: Makro, FX, G8, Regime, Faktorkatalog, Makro-Agent
- Verwandte Notizen: [[quant-diskretionaer-fusion]] (Dachprojekt, dort der
  "SMT Macro Desk"-Report und G8-Ranking als Baustein),
  [[bond-yield-spread-indikator]] (bereits getesteter Zins-Spread-Ansatz,
  kein Edge in V1), [[monetary-policy-spillover]] (Paper-Grundlage dazu),
  [[overfitting-sperre]] (gilt für jeden hier abgeleiteten Test)

## Distill

### Faktoren

Legende Rolle im Report: **R** = Regime, **K** = Ranking (G8; Säule Makro /
Rates / Preis / Quant, [Anm.] die Teil-Kataloge definieren kein G8-Ranking, die
Zuordnung der Säulen ist nur Vorschlag), **S** = Szenario-Signpost, **G** =
Gate (Katalysator / Rates / Preis / Cross-Asset / Gegenfaktor), **N** =
Kein-Trade. Daten: FRED-IDs stammen aus den Teil-Katalogen (teils dort selbst
[Anm.]) und sind nicht auf Existenz/Frequenz geprüft; "?" = unklar.
Testbar: ja / teilweise / nein.

| Faktor | Wirkung laut Notizen | Märkte | Rolle | Daten | testbar | Quelle(n) |
|---|---|---|---|---|---|---|
| **Zinsen / Notenbank** | | | | | | |
| Eingepreister Zinspfad / Cut-Erwartungen (FedWatch, OIS, Dots) | Nicht das Niveau, sondern die Abweichung vom eingepreisten Pfad bewegt; weniger Cuts als erwartet stützt die Währung, mehr Cuts schwächen sie. | USD, alle FX, UST | S, G (Rates), K (Rates) | CME FedWatch (Historie ?), OIS/SOFR-Futures ?; Proxy FRED DGS2 | teilweise (Futures-Historie kostenpflichtig) | T1 Macro Report 20.10.2024, Big Makro Stuff; T2 Breakdown 20.01., USD 14.04., Macro Trades; T3 Wochenausblick |
| Notenbank-Divergenz / "Wer senkt zuerst" | Wer zuerst und stärker senkt, wird schwächer (Zinsdifferenz); Marktthema bestimmt, welche Daten wirken. | EURUSD, GBPUSD, EURGBP, AUD/NZD/CAD | R (Thema), K (Rates), G (Rates) | OIS je Währung ?; Leitzinsen FRED/EZB/BoE | teilweise | T1 Top Down Teil 2; T2 Macro Trades, Makro 18.08.; ING |
| Notenbank-Rhetorik / Reaktionsfunktion (hawkish/dovish, Mandat, Minutes) | Doppelmandat, Preisstabilität zuerst; Fed 2024: Arbeitsmarkt darf nicht kippen; Daten schwach bei hawkisher Rhetorik: Markt preist Wende vor der Bank ein; bei gleicher Rhetorik entscheiden Daten. | USD, UST, FX | G (Katalysator), K (Rates) | Fed-/EZB-Texte (Text-Scoring ?) | teilweise (subjektiv) | T1 Top Down Teil 2, Macro Report 20.10.2024; T2 Breakdown USD, Meeting Minutes USD, Goldman; T3 Newsflow |
| Neutralzins r* / Taylor-Regel / Phillips-Kurve | Höheres r* = weniger restriktiv = USD-stützend; Taylor: Leitzins aus Inflations- und Produktionslücke; Parameter fehlen. | USD, EUR, AUD | S | NY-Fed-HLW ?, FOMC-SEP; Potenzialproduktion ? | teilweise | T1 Taylor Zins Regel, Blueprint 2024; T2 Breakdown USD, Bankreports 26.02.; T3 Bond Yield Curve |
| Zinsdifferenz / Carry (2y-Rendite-Differenz, Swap-Differenz) | Kapital folgt der Rendite; laut Trader-Regression erklären Renditeänderungen FX besser als Niveaus. | G10-FX, GBP, JPY | K (Rates), G (Rates) | FRED DGS2, Länder-2y (OECD/EZB/BoE) ? | ja | T1 Macro Report 20.10.2024; T2 Breakdown EUR/USD, Master News 21.05.; T3 Hausaufgabe 2 |
| Carry-to-Vol, Vol-Monitor | Hohe Carry/Vol-Währungen (EM) schlagen andere; fallende Vol stützt Carry; JPY als Finanzierungswährung. | EM-FX, JPY-Crosses | K (Quant), R | Zinsdifferenz + implizite FX-Vol ? | teilweise (Vol-Daten ?) | T2 Goldman, BNPP (nur Titel), ING 07.05. |
| UST-JGB-Spread, BoJ/MoF-Intervention | USDJPY korreliert laut Bank ca. 90 % mit dem 10y-Spread (täglich, seit 01/2022); Interventionsgebiet ab ca. 152; Eingriffe wirken überraschend am besten. | USDJPY, EURJPY | G (Preis/Gegenfaktor), N | FRED DGS10; JGB (MoF Japan) ? | teilweise (Eingriffe selten) | T2 Bank Report 05.03.2024 (UniCredit), Goldman, Wirtschaft Heute; T1 Big Makro Stuff |
| **Inflation** | | | | | | |
| Headline-CPI / PCE | Inflation über Erwartung: Zinsanhebungs-/weniger-Cuts-Erwartung, Währung stärker (nur ohne wirtschaftliche Schwäche); PCE ist Fed-bevorzugt. | USD, UST, FX | G (Katalysator), K (Makro) | Kalender (Ist/Konsens); FRED PCEPILFE; [Anm.] Headline-CPI z. B. CPIAUCSL (nicht aus den Notizen) | ja | T1 Inflation Angelo, Top Down Teil 2; T3 CPI Analyse, Zusammenfassung News; T2 CPI Bericht |
| Core-CPI / Services / Supercore (3M/6M annualisiert, m/m vor y/y) | Core ist Fokus von Markt und Notenbank (Löhne, Dienste); schnelleres Supercore = Inflation verankert, Fed bleibt straffer. | USD, UST | S, G (Katalysator), K (Makro) | FRED CPILFESL; Supercore selbst berechenbar | ja | T1 Blueprint 2024, Macro Report 2024; T2 CPI Angelo, 29.07.2024, Macro Breakdown Inflation |
| CPI-Komponenten (Miete, Kfz-Versicherung, Gebrauchtwagen, Energie) | Waren fallen, Dienste heizen sich auf; Bank-Vorschauen bauen CPI bottom-up. | USD | S | BLS-Komponenten ? | teilweise (Aufwand) | T2 Goldman CPI-Vorschau, CPI Angelo |
| Inflationsbreite / Autokorrelation | Anteil der CPI-Komponenten über 2 % als Diffusionsmaß; Inflation kann sich selbst nähren. | USD, UST | S | BLS-Komponenten ? | teilweise | T1 Inflation Angelo |
| PPI / Erzeugerpreise / Pass-Through | Vorläufer der Konsumenteninflation; Stufen 1-3, Final-Demand-Dienste. | USD | S | FRED PPIFIS; Kalender | ja | T3 PPI USD; T2 PPI Bericht, Makro 20.02.2024 |
| Inflationserwartungen (Breakeven T10YIE, 5y5y, Michigan) | Nominal = Real + Breakeven; Breakeven läuft der Inflation voraus; Michigan-Erwartung stützt Lohn-/Zweitrundeneffekte. | USD, UST, Gold | S, R | FRED T10YIE, T5YIFR, MICH; ETF RINF | ja | T1 Anleihenmarkt, Curves; T2 Breakdown USD 14.04., CPI Angelo; T3 News-Übersicht |
| Inflationsüberraschung (Ist minus Konsens; Citi-Index) | Surprise über 0 = Inflation über Erwartung; "Folge der Richtung der Daten". | USD, UST | G (Katalysator), K (Quant) | Eigenbau aus Kalender-Konsens; Citi proprietär | teilweise (Konsensdaten nötig) | T1 Top Down Teil 2; T2 CPI Bericht, Macro Breakdown Inflation |
| **Wachstum / Arbeitsmarkt** | | | | | | |
| BIP, Wachstumsdifferenz, 7-Phasen-Zyklus | Stärke gegen Schwäche handeln; sinkendes BIP macht die Notenbank dovisher; immer relativ zur Gegenwährung. | alle FX, Indizes | R, K (Makro) | Kalender; FRED GDPC1 | ja | T1 GDP, Top Down Teil 2; T3 GDP, Prelim GDP, Wirtschaftszyklus |
| BIP-Komponenten (Konsum, Investitionen, Staat, Netto-Export) und BIP-Qualität (Lager) | Konsum ca. zwei Drittel des US-BIP; Investitionen am zinssensibelsten, langlebige Güter inflationssensibel, Dienste lohngetrieben. | USD, Indizes | S | BEA-Tabelle; FRED | teilweise | T1 Zusammensetzung GDP, Macro Report 2024, USA Finish; T2 Macro Breakdown Inflation |
| Nowcast (GDPNow) vs. Surprise-Index | Positives Nowcast neben negativem Überraschungsindex = Erwartungs-Realitäts-Lücke. | USD | S | FRED GDPNOW | ja | T2 Macro Breakdown Inflation, Bankreports 26.02. |
| Arbeitsmarkt (NFP, U-Rate, Löhne/AHE/ECI, JOLTS, Claims, Hiring) | Starker Arbeitsmarkt: weniger Cuts, USD stark; Löhne treiben Dienste-Inflation; Revisionen/Haushalts- vs. Unternehmensumfrage beachten. | USD, CAD, alle FX | G (Katalysator), K (Makro), S | FRED PAYEMS, UNRATE, ICSA, CES0500000003, JTSJOL; Kalender | ja | T1 Macro Report 20.10.2024; T2 NFP Angelo, Breakdown USD; T3 NFP 2024, Jolt |
| PMI/ISM inkl. Preis-/Beschäftigungskomponenten | Über/unter 50 = Expansion/Kontraktion; Dienste-PMI als Zinssenkungs-Thema; PMI-Preise laut Bank zuletzt kein verlässlicher CPI-Prädiktor. | alle FX, Indizes | K (Makro), S | Kalender (S&P Global/ISM) | ja | T1 Top Down Teil 2; T2 USD 4/02.2023, Breakdown GBP; T3 ISM, PMI, Newsflow |
| PMI-Differenz US minus Deutschland vs. DXY | PMI-Differenz als Treiber der Währungsrelation. | USD, EUR | K (Makro) | S&P Global/ISM/HCOB | ja | T2 Breakdown USD (Chart) |
| Konsum (Retail Sales, Consumer Confidence/UMich, Sparquote, Konsum-Aktien) | Vertrauen führt zu Ausgaben; Retail Sales als Echtzeitstatus; zyklische Konsumaktien als Frühindikator. | USD, Indizes | S, K (Makro) | FRED RSAFS, UMCSENT, PSAVERT; Kalender | ja | T1 Konsumausgaben, Zusammensetzung GDP; T2 Bank Reports 16.04.; T3 CB Consumer Confidence, Core Retail Sales |
| Immobilien, Lager/Umsatz, M2-Velocity | Baubeginne als Kredit-/Investitions-Frühindikator; hohes Lager/Umsatz heißt kein Nachfragedruck. | USD | S | FRED HOUST, PERMIT, MORTGAGE30US, ISRATIO, M2V | ja | T2 Bank Reports 16.04., Breakdown CPI Angelo; T3 Newsflow |
| Haushaltsbilanz (Kreditausfälle, Schuldendienst, Sparpuffer) | Aufgebrauchte Puffer und steigende Ausfälle schwächen späteren Konsum. | USD | S | FRED TDSP, PSAVERT | ja | T2 29.07.2024, 25.06.2024; T1 Big Makro Stuff |
| Rezessionssignale (Sahm Rule, U-Rate-Tief + 7-15 Monate, Erstanträge über ca. 250k, defensive vs. zyklische Aktien) | Sahm: Anstieg um 0,5 PP; nach dem Tief der Arbeitslosenquote steigt sie laut Trader-Muster 7-15 Monate später sprunghaft. | USD, Risk, Gold | R, S, N | FRED UNRATE, ICSA, SAHMREALTIME | ja | T2 Rezession 05.08.2024, Bank Reports 16.04. |
| Wirkkette Nachfrage→Lager→PMI→Entlassungen→Spreads | Reihenfolge der Schwäche; Glieder dienen als Signposts. | Multi-Asset | S | siehe Einzelreihen | teilweise | T1 Macro Report 2024; T2 Macro Breakdown Inflation |
| Fiskal/Schulden/Rating, Zinskosten | Zinsausgaben könnten Verteidigung übersteigen; Rating-Downgrade, höhere Renditen; prozyklische Fiskalpolitik verlängert den Zyklus. | USD, UST, Gold | S, R | CBO, FRED | teilweise (langsam) | T1 Haushaltsdesaster, USA Finish, Trader Magazin; T2 25.06.2024 (DB) |
| **Liquidität** | | | | | | |
| Makro-Liquidität (Menge + Preis des Geldes) | Nettoimpuls auf Risikoassets; positive Liquidität bullisch, negative bärisch (Regel für BTC). | BTC, Aktien, Gold | R, G (Cross-Asset) | FRED M2SL, WALCL, WRESBAL; Realzins DFII10 | ja | T1 BTC Dynamik, Macro Report 2024, Trader Magazin |
| QT, RRP, TGA, Treasury-Emission (QRA), Term Premium | Bilanzabbau entzieht Reserven erst, wenn RRP/TGA erschöpft sind; QRA kann Duration-Abverkauf auslösen; QT-Taper entlastet Langzinsen. | UST, USD, Aktien | S, R | FRED WALCL, RRPONTSYD, WTREGEN, WRESBAL; ACM Term Premium | ja | T1 Trader Magazin; T2 Macro Breakdown NFP Woche, Meeting Minutes USD; T3 Newsflow |
| Funding/Repo/Anleihe-Liquidität, Cross-Currency-Basis | Enge Finanzierung: Qualitätsflucht in Treasuries, Spreads auf Corporates steigen; negative Basis = USD-Knappheit; in Illiquidität USD/JPY als Hedge. | UST, USD, JPY, EURUSD | R, N | SOFR [Anm.]; Basis ? (nicht frei) | teilweise (Daten schwer) | T1 Bonds Liq 1, Repo; T3 Currency Basic Swaps (nur Text-Fragment) |
| Geldpolitik-Verzögerung (Lag) | Zinsanhebung wirkt ca. 2 Jahre verzögert auf Rezession/Vola. | Aktien, VIX | R | Fed Funds, VIX | ja (Historienstudie) | T1 Big Makro Stuff, Trader Magazin |
| **Zinskurve / Anleihen** | | | | | | |
| Zinskurve (2s10s, 3m10s, Steepener/Flattener, Inversion) | Inversion drückt Bankmargen (Liquiditätsbasis der Rezession), kein Garant; Steepener-Typ bestimmt die Lesart; Spread-Vorsprünge zum Timing. | UST, USD, Aktien | R, S | FRED T10Y2Y, T10Y3M | ja | T1 Curves, Macro Report 2024; T2 Macro breakdown; T3 Bond Yield Curve, Hausaufgabe 2 |
| 2y-/10y-Rendite als Signalgeber, US10Y-US02Y als DXY-Signal | 2y läuft Fed-Entscheidungen voraus; Aufsteilen bei sinkendem 2y = Cut-Erwartung eingepreist, DXY short. | DXY, USD-Paare | K (Rates), G (Rates) | FRED DGS2, DGS10 | ja | T3 Newsflow, Hausaufgabe 2; T2 Breakdown 20.01. |
| 10y-Niveau/Key-Levels, Realzins (DFII10), Nominalzins | Steigende positive Realzinsen belasten Risikoassets; Key-Level z. B. 4,50 %; Nominal = Netto aus Breakeven und Real. | USD, Aktien, Gold, BTC | G (Rates), S | FRED DGS10, DFII10; ETF TIP, IEF | ja | T1 Anleihenmarkt, Curves; T2 Breakdown 20.01., Breakdwon S&P 500 |
| Realzins-Spread 10y-2y | Flach/negativ = Wachstumspessimismus; bewegt sich mit BTC. | Risikoassets, BTC | G (Cross-Asset) | FRED TIPS-Renditen | ja | T1 Curves |
| Anleihemathematik (Duration, Konvexität, Kupon) | Erwartete fallende Zinsen: lange Duration; steigende: kurze. | Anleihen | nur Hintergrund | Rechenregel | nein | T1 Market Risk, Pricing a Bond; T3 Bonds |
| Kreditspreads (HY-OAS, BBB, SLOOS) | Enge Spreads = Optimismus; Weitung = Rezessionsrisiko; SLOOS führt das BIP um Quartale. | Aktien, USD | R, S, N | FRED BAMLH0A0HYM2, SLOOS | ja | T1 Big Makro Stuff; T2 USA JM ZSM, 25.06.2024 |
| Banken-Stress (BTFP-Auslauf, Regionalbanken, unrealisierte Verluste) | Mögliche Stressquelle bei hohen Langzinsen. | Banken, USD | S, N | FRED/FDIC | teilweise | T2 Breakdwon S&P 500, Meeting Minutes USD; T1 Blueprint 2024 |
| **Positionierung / Flows** | | | | | | |
| COT-Positionierung (CFTC) | Extreme Netto-Positionen als Trendumkehr-/Katalysator-Hinweis (Wochenfrequenz). | USD, Gold, FX-Futures | G (Preis/Gegenfaktor), K (Quant) | CFTC COT | ja | T1 Blueprint 2024, Top Down Teil 2; T2 Dollar Nachfrage, Ultra Breakdown 30.04.; T3 Checkliste, Cot Analyse (nur Titel) |
| Positionierungsindizes und Optionspositionierung (PIX, Risk Reversals, Momentum-Scores) | Je Währung über-/unterkauft; extreme GBP-Risk-Reversals laut Spectra-Beispiel kontrarär (n=17). | G10-FX | K (Quant), G (Gegenfaktor) | COT + Risk Reversals ?; Flussdaten proprietär | teilweise | T2 Credit Agricole, BTC 01.24, Spectra |
| Fonds-/ETF-Flows, systematische Flows (CTA, Vol-Control) | Positionsgröße folgt der Vola, daher beeinflusst Vola Flows direkt; Fonds extrem USD-short. | Indizes, FX | G (Gegenfaktor), N | VIX; COT (CTA-Proxy) [Anm.]; EPFR/iFlow proprietär | teilweise | T1 Algos und Flows, Goldman Hedhefunds; T2 Bank Report 30.01., Breakdown USD Angelo |
| Monats-/Quartalsende-Flows, Rebalancing | Drücken USD temporär; DXY-Saisonalität. | USD, GBP | G (Gegenfaktor) | Kalender + DXY | ja | T2 Breakdown USD, Macro Trades, USD 4/02.2023 |
| **Risiko-Stimmung / Cross-Asset** | | | | | | |
| Dollar-Smile, Risk-on/off-Regime | USD stark bei US-Zins-Repricing und bei Risk-off; Risiko-Währungen (AUD, CAD, NZD, NOK, ZAR) gegen Safe Haven; Markov-/Fuzzy-Ansatz zur Quantifizierung. | USD, G10 | R, G (Cross-Asset) | Aktienindex, Vola, Zinsdifferenz | ja (aus Preisen) | T2 01.2024 (Citi), Breakdown Angelo USD; T1 Risk on Risk Off Assets |
| Intermarket (Aktien, Anleihen, USDJPY, Gold, BTC, DXY) | Risikokurve: USDJPY und Aktien steigend heißt Risikoappetit; Intermarket 10-15 % der Gewichtung (unbelegt). | alle | G (Cross-Asset) | Kurse | ja | T1 BTC Dynamik, Marktschwerpunkte; T3 FITS |
| T-Bond-Future (ZB1!) als DXY-Vorläufer | Long-BOS im ZB1! deutet auf Short-BOS im DXY in den folgenden Tagen. | DXY | G (Cross-Asset) | ZB1!-Kurse | ja (Lead-Lag) | T3 Checkliste, Wochenausblick |
| Citi Economic Surprise / LEI | Summe Ist minus Prognose; über 0 = besser als erwartet. | alle FX, Indizes | R, K (Quant) | MacroMicro; Eigenbau ? | teilweise | T1 Top Down Teil 2; T2 Macro Breakdown Inflation, Bank Report 05.03. |
| Aktienmarkt-Struktur (Konzentration, CAPE, Buffett-Indikator, Breite) | Euphorie-/Überbewertungsindikatoren; Schwellen unbelegt. | US-Aktien | R | FRED WILL5000INDFC, GDP; Shiller-CAPE | teilweise | T1 Big Makro Stuff; T2 25.06.2024 (DB), Rezession 05.08. |
| Narrative / Sentiment / Marktthema | Das Hauptthema bestimmt, welche Daten wirken; Narrative können länger dominieren. | alle | R (Thema) | ? (Text-Analyse) | teilweise | T1 Macro Report 20.10.2024, Marktschwerpunkte; T3 Checkliste |
| **FX-spezifisch** | | | | | | |
| Relative Stärke (stark gegen schwach), FX-Momentum | Aus FITS die stärkste gegen die schwächste Währung handeln; Livechart-Stärke nur Bestätigung. | FX-Crosses | K (Preis) | Kurse | ja | T3 Checkliste; T2 BTC 01.24 (Spectra) |
| FX-Fair-Value / Bewertung (BEER, PPP, Output-Gap) | USD laut Banken überbewertet; langfristiges Fair-Value-Signal. | G10, EM | K (Quant), S | OECD/BIS ? | teilweise | T2 BNPP (nur Titel), Outlook USD 26.01.2024 |
| USD-Nachfrage-Rahmen | Strukturelle USD-Nachfrage (Aktienflüsse, Rohstoff-Settlement, Hedging, Reserven, Vertrauensspread). | USD | S | gemischt | teilweise (nicht operationalisiert) | T2 Dollar Nachfrage |
| China (Deflation, PBoC-Fixing, Stimulus) | Chinesische Schwäche belastet CNY/AUD und stützt den USD; Stimulus stützt EUR und AUD; Welt "importiert Deflation". | CNY, AUD, EUR | S, G (Gegenfaktor) | Kalender; PBoC-Fixing ? | teilweise | T1 19.07.2024, Big Makro Stuff; T2 Citi |
| Politik/Wahlen/Geopolitik (US-Wahl, Frankreich-Spread, Iran, Rotes Meer) | Kurzfristige Sentimentumschaltung (Tactical View); OAT-Bund-Spread belastet EUR; Risk-off in USD/JPY/CHF. | FX, Gold, Öl | S, N | Ereignislisten ?; FRED/OECD Spreads | teilweise (n klein) | T1 Top Down Teil 1; T2 USD 07.2024, Makro Dennis, Macro US 21.04. |
| Handels-/Leistungsbilanz | Starke Währung verbilligt Importe, verteuert Exporte. | FX | S | Kalender | teilweise | T1 Zusammensetzung GDP; T3 Newsflow |
| **Rohstoffe / Gold** | | | | | | |
| Öl/Energie/Frachtraten | Ölanstieg belastet EUR (Divergenz) und treibt Inflation; Öl-Reversal trotz Geopolitik als Schwäche gelesen. | EUR, CAD, NOK, Inflation | S, G (Gegenfaktor) | FRED DCOILWTICO; Brent, WCI ? | ja | T1 Top Down Teil 2, Big Makro Stuff; T2 Breakdown USD Angelo; T3 Newsflow |
| Rohstoffe als Inflations-Frühindikator (Kupfer, Agrar) | Steigende Preise: Inflation/Wachstum zieht an; Kupfer als Frühindikator. | Rohstoffe | S | Futures/GSCI | ja (Lead-Lag) | T3 Newsflow |
| Baltic Dry Index | Läuft Weltwirtschaft/S&P 500 ca. 8-12 Monate voraus; invers zum USD. | Aktien, USD | R | BDI (Baltic Exchange) ? | ja | T1 Trader Magazin |
| Gold (Vorlauf, Schuldenquote, Zentralbanknachfrage) | Gold-ATH als Absicherungs-/Rezessionspreisung; Treiber Zentralbank-/China-Nachfrage statt Fed-Cuts. | Gold, USD, Risk | R, G (Cross-Asset) | Goldpreis; WGC ? | ja | T2 Breakdown Angelo USD; T1 Big Makro Stuff, Trader Magazin |
| **Saisonalität / Zeit** | | | | | | |
| Termin-/Zeitfaktoren (Veröffentlichungszeit, Sperrfrist, Wochenkalender) | Daten vor London-Open geben Banken eine Stunde Vorsprung; Wochenkatalysatoren QRA/FOMC/NFP; High-Impact-News Mi-Fr: Montag nicht erzwingen. | alle | G (Katalysator), N | Kalender | ja | T2 Master News 21.05., Ultra Breakdown; T3 Checkliste |
| Session-/Tageszeit-Statistik, Tages-TP | London/NY je ca. 46 Pips, Asia 30; Tages-TP = Ø-Tagespips x 0,7-0,8 (News-Tag x 1,2-1,5); Zeitverteilung von Tageshoch/-tief. Stichprobe/Instrument nicht genannt. | FX | (Ausführung, kein Makrofaktor) | Intraday-Kurse | ja | T3 Zusammenfassung Time and Price, Checkliste |
| Wirtschaftszyklus-Phase | Fünf bzw. sieben Phasen ordnen Indikatoren und Notenbankverhalten ein. | alle | R | kombiniert | teilweise (subjektiv) | T1 GDP, Wirtschaftszyklen und Goldilock; T3 Wirtschaftszyklus |
| Demografie / Immigration | Alterung: Arbeitskräftemangel, Löhne; Immigration treibt Lohnprognosen. | USD | S | ? | nein (zu langsam) | T1 USA Finish; T2 Breakdown USD Angelo |
| Gamma / Optionsflows | Calls → Hedge-Käufe → Squeeze; nur Einzelaktien. | Einzelaktien | N | Optionsdaten ? | teilweise | T1 Gamma Squeeze |

[Anm.] Nicht aufgenommen, weil kein Faktor im Sinn eines Datenpunkts: Marktschwerpunkt-
Gewichtung (33-66 % Fundamental etc., unbelegt, T1 Marktschwerpunkte bestimmen),
KI/Strom und BTC-ETF-Flows (kein FX-Bezug, T2), Random-Walk-Theorie (T3),
Länder-Checkliste (siehe "Analyse-Ablauf"). Gamma-Zeile bleibt als Abgrenzung.

### Regime-Schemata

Güte: Quad-Tabelle (Hedgeye), Goldman-Taktik, Peccatiello-Quadranten sind
Fremdmaterial; Wachstum x Inflation x Liquidität stammt aus den eigenen
Report-Entwürfen, lehnt sich aber laut Teil-Katalog stark an Fremdkonzepte an.

| Regime | Definition laut Notizen | Typische Asset-Reaktion | Quelle |
|---|---|---|---|
| Quad 1 Goldilocks | Wachstum und Disinflation günstig | Besser: Aktien, Kredit, Rohstoffe, FX; schwächer: Anleihen, USD; Tech/zyklisch, High Beta/Momentum | T1 Wirtschaftszyklen und Goldilock |
| Quad 2 Reflation | Wachstum und Inflation steigen | Besser: Rohstoffe, Aktien, Kredit, FX; schwächer: Anleihen, USD; Small Caps, Cyclical Growth | T1 ebd. |
| Quad 3 Stagflation | Wachstum fällt, Inflation steigt | Besser: Gold, Rohstoffe, Anleihen (Long Bond, TIPS); schwächer: Kredit/HY; Low Beta/Quality | T1 ebd. |
| Quad 4 Deflation | Wachstum und Inflation fallen | Besser: Anleihen, Gold, USD; schwächer: Rohstoffe, Aktien, Kredit, FX; Defensive/Value | T1 ebd. |
| Wachstum x Inflation x Liquidität (4 Kombinationen) | Drei Treiber der Vermögenspreise; Szenario 1 disinflationäre Rezession (Wachstum bricht, Core fällt, Fed lockert, Spreads weiten); Szenario 2 stagflationäre Rezession (Wachstum nur leicht langsamer, Core hoch, Fed hebt weiter); weitere Szenarien im Text abgeschnitten | je Asset unterschiedlich; Szenario 1: Spreads weiten; Szenario 2: Fed straffer | T1 Macro Report 2024, Vermögensverwaltung; T2 Macro Breakdown Inflation |
| Angriff/Verteidigung (Wachstums-Beschleunigung) | Wachstum, Geldpolitik, Inflation als Quadranten | Angriff: Aktien, Kredit, Rohstoffe, EM; Verteidigung: US-Anleihen, Gold, USD | T1 Trader Magazin |
| Liquiditäts-Regime | Makro-Liquidität positiv/negativ | positiv: Risikoassets (BTC) bullisch, Momentum + Buy-the-Dip; negativ: bärisch; Kurvenphasen als Teilbild | T1 BTC Dynamik |
| Kurven-Regime | Bull/Bear Steepener/Flattener x Geldpolitik (expansiv/kontraktiv) x Zyklus x Inflationserwartung | je Quadrant unterschiedlich (im Text nicht ausformuliert) | T1 Curves; T3 Wirtschaftszyklus |
| Risk-on / Risk-off | Zustand in Zahlen ausdrücken (Markov, gestapelte Definitionen); Liste "was steigt bei Risk-off" steht NICHT im Material | USD/JPY als sichere Währungen bei Illiquidität (T1 Bonds Liq 1); Risiko-Währungen vs. Safe Haven (T2) | T1 Risk on Risk Off Assets; T2 Dollar-Smile |
| Zyklus 5/7 Phasen | Aufschwung bis Rezession (T3, 5 Phasen) bzw. Expansion bis Erholung (T1, 7 Phasen) | Währung folgt der Phase; Boom = Wendepunkt höchste Inflation | T1 GDP; T3 Wirtschaftszyklus |
| Konsolidierung vs. Ausbruch | Markt wartet auf Daten: Seitwärts; Ausbruch richtungsabhängig vom Datum | Seitwärts bis Katalysator | T1 Macro Report 20.10.2024 |
| Fundamental vs. Tactical View | Fundamentaler Bias = Trend, taktische Sicht = kurzfristiges Gegenszenario | Timing über die taktische Sicht | T1 Top Down Teil 1 |
| Datenkonstellation Goldilocks-Check | PMI über 50, Preiskomponenten fallen, stabiler Arbeitsmarkt, BIP über CBO-Schätzung | Raum für USD-Rallye (laut Notiz) | T2 Breakdown USD Angelo |

### Regeln/Heuristiken

Entdoppelt, Wenn-Dann, mit Quelle. **WIDERSPRUCH** = Aussagen der Quellen
passen nicht zusammen; sie sind unaufgelöst nebeneinander belassen.

Daten → Währung/Preis
1. Inflation über Erwartung → Währung stärker (Anhebung wird eingepreist, Markt läuft ca. 6 Monate voraus), aber nur ohne wirtschaftliche Schwäche. (T1 Top Down Teil 2; T3 Checkliste: "Actual > Forecast gut für die Währung")
2. BIP sinkt → Notenbank dovisher → Währung schwächer, immer relativ; bei zwei schwachen gewinnt die weniger schwache. (T1 Top Down Teil 2)
3. Zinsanhebung bei schwacher Wirtschaft kann die Währung trotzdem short lassen (EUR-Beispiel). (T1 Top Down Teil 2)
4. Fallende CPI ist keine automatische Senkung: bei klebriger Dienste-Inflation prüfen Dienste-PMI-Preise, NFP, Löhne. (T1 Top Down Teil 2; T2 Breakdown USD 14.04.)
5. Starker Arbeitsmarkt → weniger Cuts → USD positiv; schwacher → dovisher → USD schwächer. (T1 Macro Report 20.10.2024; T2 Breakdown USD)
6. Weniger Cuts als eingepreist → USD gestützt; bei Preisung um 125 bp und Erwartung unter 100 bp → DXY nach oben; bei 150 bp stark negativ (Beispielschwellen eines Reports). (T1 Macro Report 20.10.2024)
7. Supercore steigt schneller → Inflation verankert → Fed straffer → Senkung später. (T1 Blueprint 2024; T2 29.07.2024: m/m vor y/y)
8. Arbeitsmarkt schlechter → Core-CPI sinkt → Geldpolitik lockerer; NFP gegen Rückgang von 10y/Inflation = verzerrtes Bild. (T1 Macro Report 2024)
9. Dienste-PMI unter 50 stützt das Senkungsthema (GBP short); Core-Inflation + Lohnwachstum fallend → BoE kann senken. (T1 Top Down Teil 2)
10. Notenbank hawkish, Daten schwach → Markt preist Dovish vor offizieller Änderung → Währung short, Anleihen long. (T1 Top Down Teil 2)
11. BoE hawkish + robuste Dienste + Zinsdifferenz → GBP positiv (Carry); Risiken Budget, BIP, langsamere Cuts. (T1 Macro Report 20.10.2024)
12. EUR bärisch bei schwachen PMIs (DE/FR), Inflation unter Ziel, sinkenden Erwartungen; kurzfristig gestützt durch hawkishe EZB und China-Stimulus. (T1 Macro Report 20.10.2024)
13. Zinsdifferenz: Kapital folgt der Rendite; Renditeänderungen erklären FX besser als Niveaus (Trader-Regression, ohne Statistik). (T2 Breakdown EUR/USD)
14. Weniger-Cuts-eingepreist-Währung ist relativ stärker (GBP mit wenigsten Senkungen). (T2 GBP 14.04.)
15. Aufsteilen von US10Y-US02Y bei sinkendem 2y → Cut-Erwartung eingepreist → DXY short (EU/GU/AU/NU long, UJ/UChf short). (T3 Hausaufgabe 2)
16. Öl steigt stark → EUR belastet; Öl-Reversal trotz Geopolitik = Schwäche. (T1 Top Down Teil 2; T2 Breakdown USD 14.04.)
17. China schwach → AUD belastet, auch bei fundamental Long; Stimulus stützt EUR/AUD. (T1 19.07.2024, Top Down Teil 1)
18. Realzinsen steigen und werden positiv → Risikoassets (Aktien, BTC) fallen. (T1 Curves, BTC Dynamik)
19. Liquidität positiv → BTC Buy (Momentum + Buy-the-Dip), negativ → Sell; SL unter den "Punkt, wo der Markt nicht hinkommen darf". (T1 BTC Dynamik)
20. USDJPY und Aktien steigen → Risikoappetit → BTC-Rally. (T1 BTC Dynamik)
21. Liquiditätsengpass → Risikoprämien steigen, in Illiquidität USD/JPY als Hedge. (T1 Bonds Liq 1)
22. BDI fällt/Divergenz zum S&P → Korrekturwahrscheinlichkeit steigt (8-12 Monate Vorlauf); DXY mitprüfen. (T1 Trader Magazin)
23. Wirkkette: reale Nachfrage↓ → Lager/Umsatz↑ → PMI↓ → Entlassungen → Erstanträge↑, Spreads weiten. (T1 Macro Report 2024)
24. Invertierte Kurve ist nur belastbar, wenn NFP/U-Rate, Industrieproduktion und Retail Sales mitbrechen. (T3 Newsflow) Zinszyklus: "Treppe hoch, Aufzug runter". (T1 Top Down Teil 2)
25. Fonds-/Flow-Regeln: Monatsende-Flows stützen/drücken USD temporär; Risk-Reversal extrem → Kontra-Lesart (GBP-Beispiel n=17). (T2 Breakdown USD, BTC 01.24)
26. USDJPY im Interventionsgebiet (ab ca. 152) meiden; Intervention wirkt überraschend am besten. (T2 Breakdown USD, Goldman)
27. Gold-ATH wird als Rezessions-/Absicherungspreisung gelesen. (T2 Breakdown Angelo USD)

Vorgehen, Disziplin, Kein-Trade
28. Fundamentals first, Technik für Entry und Risiko; Fundamentals legen "nur Longs oder nur Shorts" fest. (T1 Top Down Teil 1/2)
29. Nicht jede News traden; bei bedeutenden Terminen nicht kurz davor/danach einsteigen; bis NFP Volatilität abwarten. (T1 Trader Magazin, Macro Report 20.10.2024, Top Down Teil 2)
30. Frühindikatoren nur zur Vorbereitung; handeln erst bei Bestätigung durch Echtzeit-Indikatoren. (T3 Newsflow/Newsworkflow)
31. Nur gegen den eingepreisten Konsens positionieren; Monatsstopp bei 1 Standardabweichung, Verlust max. 2 %, ca. 7-10 unkorrelierte Positionen. (T1 Trader Magazin, Fremdmaterial)
32. Intraday 5-15 Min. ohne Informations-/Geschwindigkeitsvorteil gegen HFT wenig aussichtsreich; Edge nur durch Informationsvorsprung (Daten gegen Konsens) oder andere Zeitpräferenz. (T1 Einführung Intraday)
33. Montag nicht erzwingen, wenn Mi-Fr High-Impact-USD-News liegen. (T3 Checkliste)
34. Daten schwach, Währung steigt: nur ein Puzzleteil, Relativstärke prüfen. (T1 Top Down Teil 2)
35. Gates als Einzelaussagen der Breakdowns: kein EUR-Long bei Divergenz Fed vor EZB; kein USDJPY-Long im Interventionsgebiet; Fundamentals mit bärischer Trendstruktur kombinieren. (T2 Breakdown Angelo EUR, USD)
36. Gamma: bei parabolischer Bewegung Gewinne mitnehmen. (T1 Gamma Squeeze; nur Einzelaktien)
37. Gewichtung bei Konflikt Makro vs. Technik, Newswochen vs. Trend: s. Widerspruch 6.

**Widersprüche und Spannungen (unaufgelöst):**
1. **WIDERSPRUCH CPI vs. NFP:** CPI hat stärkere Reaktion als NFP, Hauptfokus CPI (T1 Blueprint, Feb 2024) gegen Fed gewichtet Arbeitsmarkt vor Inflation (T1 Macro Report 20.10.2024). Teil-Katalog 1 vermerkt: themenabhängig. T2 stützt den Inflationsfokus für Frühjahr 2024 (NFP-Wirkung klein solange Inflationsfokus).
2. **WIDERSPRUCH USD-Richtung:** kurzfristig stark, langfristig schwach (T2 USD Angelo, Apr) gegen "starker USD bis zur Wahl" (T2 25.07.2024, Bankquelle).
3. **WIDERSPRUCH Safe-Haven-Liste:** T2 Breakdown Angelo USD führt EUR bei den sicheren Häfen (als [sic] markiert); T1 Bonds Liq 1 nennt nur USD/JPY, T2 Dollar-Smile USD/CHF/JPY.
4. **WIDERSPRUCH Frühindikatoren:** Markt reagiert auf PMI/ISM-Preiskomponenten solange Fed auf Inflation schaut (T2 Breakdown USD Angelo), aber PMI-Preise sind zuletzt kein verlässlicher CPI-Prädiktor (T2 USD 4/02.2023) und "handle erst bei Bestätigung durch Echtzeit-Daten" (T3). Bedingung statt Gegensatz: vermutlich Frühindikator = Vorbereitung, Reaktion = Preiseffekt, im Material nicht aufgelöst [Anm.].
5. **WIDERSPRUCH Kurveninversion Vorlauf:** Inversion ging allen letzten Rezessionen voraus (T1 Curves/Macro Report 2024) gegen nur belastbar mit mitbrechenden Echtzeitdaten (T3 Newsflow); Vorlaufzeit 12-18 Monate (T3) gegen ca. 2 Jahre / 25 Monate Fed-Funds-Verschiebung (T1 Big Makro Stuff, Trader Magazin).
6. **WIDERSPRUCH Makro vs. Technik:** Bei Widerspruch gewichtet Makro mehr (T3 Wochenausblick) gegen im laufenden Trend sind technische Dinge wichtiger (T1 Marktschwerpunkte).
7. **Spannung Fed-Futures:** Futures preisen Cuts immer zu früh ein, "Märkte sind kein guter Indikator für Zinsen" (T1 Big Makro Stuff) gegen Futures/FedWatch als Hauptmaß der Erwartungsabweichung (T1 Macro Report 20.10.2024, T2, T3).
8. **Spannung Steepening:** Aufsteilen bei sinkendem 2y = DXY short (T3 Hausaufgabe 2) gegen steile Kurve = Boom/Inflation (T3 Zinsstrukturkurve) bzw. steilere Kurve = Wachstums-/Inflationserwartung (T2); die Unterscheidung Bull/Bear Steepener ist nur in T1 Curves angelegt.
9. **Unklar:** "Macro Master Setup" (fallende Realzinsen + Breakeven über 2 % → Fed hebt, positionieren): USD-Richtung im Originaltext unklar (T1 Anleihenmarkt).

### Analyse-Ablauf

Konsolidierter Top-down-Ablauf (Variante A bis E des Materials zusammengeführt):

1. **Zustand/Zyklus**: Wirtschaftszyklus-Phase und Regime bestimmen (Quad bzw. Wachstum x Inflation x Liquidität); Zinsen, Inflation, Arbeitsmarkt, Bonds zuerst. (T1 Top Down, Wirtschaftszyklen; T3 Zusammenfassung 06.04.2025)
2. **Marktthema**: globales Thema aus Bankreports/News ("wer senkt zuerst", "wie aggressiv senkt die Fed"); Frage: welche Daten stützen es, zeigen sich Risse. (T1 Top Down Teil 2, Macro Report 20.10.2024; T2 Breakdown-Prüfreihenfolge)
3. **Daten sammeln** je Land und Gegenland (Tradingeconomics bzw. Forex Factory), Trend je Datenpunkt, je Punkt "stützt das mein Thema, ja/nein". Primär GDP, Inflation, Zinsen; bei Senkungsthema Inflation + Arbeitsmarkt; dann PMI-Komponenten, Retail, Housing, Surprise-Indizes.
4. **Marktreaktion**: 2y/10y, OIS/FedWatch-Wahrscheinlichkeiten, Gold, Öl, Aktien, Breakeven/Realzins. Vorlaufende (PMI, UMich, Bonds, Kurve, Indizes, Rohstoffe) zur Vorbereitung, Echtzeit-Daten (NFP, CPI, Retail, PCE, GDP, Industrieproduktion) zur Bestätigung, dann Injections/Withdrawals der Notenbanken. (T3 Newsworkflow)
5. **Notenbank**: Rhetorik gegen Daten, Mandat, Divergenz; FOMC-Statement gegen Vormonat, Dots, Pressekonferenz-Ton.
6. **Relativvergleich** der Volkswirtschaften ("Stärke gegen Schwäche"; man handelt wirtschaftliche Ansichten, keine Währungen).
7. **Zusatzchecks**: COT/Positionierung, Cross-Asset-Korrelationen, Citi Surprise, Bankreports/Konsens (Tabelle von 13 Banken für den Fed-Pfad als Konsens-Check), Flows (Monatsende), Politik/Geopolitik.
8. **Overall View** (EURUSD 3-6 Monate, Markt 6-12 Monate) und **Tactical View** (Grund gegen die Richtung, Timing).
9. **Erst dann Technik** (Entry/Risiko); Wochenplan: Sonntags-Ausblick, News-Kalender, Bias, Session. (T3 Wochenausblick, Checkliste)

Abweichungen/Varianten:
- Wochenreport (Macro Report 20.10.2024): Rückblick, Thema, je Währung (Daten, nächste Woche, Szenarien stark/schwach, Up-/Downside-Risiken, Bias), Bankprognosen, Handelshinweis. Ein G8-Ranking ist dort nicht definiert. (T1)
- 3 Säulen (Trader Magazin): Liquidität, Markterwartungen/Konsens eingepreist?, Risikomanagement. (T1)
- Marktschwerpunkte: Gewichtung Fundamental/Sentiment/Intermarket/Charttechnik je Marktphase; Gewichte (33-66 % / 10-15 % / 10-15 %) unbelegt. (T1)
- Attributsanalyse: Einflussfaktoren identifizieren → quantifizieren (Regression, Korrelation, Eventstudie) → Performance zuordnen → entscheiden; Beispielfaktoren EURUSD: Wachstumsdifferenz, Zinsdifferenz, Politik, Handelsbilanz, Inflationsdifferenz, Sentiment, QE/Fiskal. (T1 Anleihenmarkt)
- Länderanalyse-Checkliste: Profil/Regime → BIP-Mechanik → Unternehmen/Löhne/Arbeit → Sektoren → Indikatoren → Handelsbilanz → Preise → Kapitalstruktur. (T2 Länderanalyse)
- Hausaufgaben-Schema "Fed-Entscheidung": Inflation, Arbeitsmarkt, Kurve → Entscheidung begründen. (T3)
- Disziplin-Erweiterung: Tages-TP und Session-Zeitfenster (T3 Checkliste) gehören zur Ausführung, nicht in den Makro-Report [Anm.].

### Testkandidaten

Priorisiert nach Datenverfügbarkeit (frei, tagesgenau) und eindeutiger Hypothese.
Jeder Test läuft unter [[overfitting-sperre]] (Split IS/OOS/Tresor vorab, jede
Variante zählen). "Test im Repo" geprüft per Stichwortsuche in
`knowledge/projects/` und `knowledge/resources/` (Stand 12.10.2026); Treffer nur
über Dateinamen/Stichwort, keine inhaltliche Prüfung darüber hinaus.

1. **CPI/Core-Surprise → FX-Reaktion.** Mechanismus: Ist über Konsens führt zu Cut-Rückbau und stärkerem USD. Daten: Kalender-Konsens (Historie ?) + Dukascopy-M1. Test im Repo: nein (kein Treffer "Surprise"); T3 liefert nur 3 Release-Zeilen und ein Einzelchart (n=1).
2. **Änderung der 2y-Zinsdifferenz (Cut-Erwartungs-Revision) → G10-Paare.** Mechanismus: Renditeänderungen erklären FX besser als Niveaus. Daten: FRED DGS2 + Länder-2y. Test im Repo: teilweise, [[bond-yield-spread-indikator]] (V1 ohne belastbaren Edge, Trefferquote 48-51 %); der Ansatz "Änderung statt Niveau" wird dort nicht ausdrücklich genannt [Anm.].
3. **COT-Extrempositionierung als Kontra-Signal (FX, Gold).** Mechanismus: überfüllte Positionen sind Trendumkehr-Brennstoff. Daten: CFTC COT (wöchentlich). Test im Repo: Baustein vorhanden (`asian_range_breakout/cot.py` laut [[quant-diskretionaer-fusion]]), ein eigener Makro-Test nicht gefunden.
4. **Liquiditäts-Regime (WALCL/RRP/TGA/M2, Realzins DFII10) → Aktien/Gold/BTC.** Mechanismus: positiver Nettoimpuls trägt Risikoassets. Daten: FRED. Test im Repo: nein.
5. **Sahm Rule / U-Rate-Tief + 7-15 Monate → Risk-off.** Mechanismus: nichtlineare Arbeitsmarktwende. Daten: FRED UNRATE, SAHMREALTIME, ICSA. Test im Repo: nein (kein Treffer "Sahm"); Stichprobe nur wenige Rezessionen.
6. **HY-OAS-Ausweitung als Rezessions-/Risk-off-Gate.** Mechanismus: Kreditmarkt preist Schwäche früher. Daten: FRED BAMLH0A0HYM2. Test im Repo: nein.
7. **UST-JGB-10y-Spread → USDJPY (inkl. Interventionszone).** Mechanismus: Renditedifferenz treibt USDJPY (Bank: ca. 90 % Korrelation). Daten: FRED DGS10 + JGB (MoF). Test im Repo: nur indirekt ([[bond-yield-spread-indikator]], 6 Paare); Niveau-Korrelation täglich kann Scheinkorrelation sein [Anm.].
8. **Monats-/Quartalsende-Flows und DXY-Saisonalität.** Mechanismus: Rebalancing drückt USD temporär. Daten: DXY-Preise + Kalender. Test im Repo: kein DXY-Test gefunden (Saisonalität nur in anderen Notizen).
9. **ZB1!-Future als DXY-Vorläufer (Lead-Lag).** Mechanismus: Anleihe-BOS führt die Dollarstruktur um Tage. Daten: ZB1!/DXY-Kurse. Test im Repo: nein.
10. **Realzins-Spread / Breakeven-Cross-Asset (DFII10, T10YIE) → BTC/Gold.** Mechanismus: Realzinsen steigen und werden positiv, Risikoassets fallen. Daten: FRED. Test im Repo: nein (Breakeven-Treffer betreffen andere Themen).
11. **Kurveninversion 2s10s/3m10s → Rezessionsvorlauf (Lag-Verteilung).** Mechanismus: Bankmargen/Kredit. Daten: FRED T10Y2Y, T10Y3M. Test im Repo: nein; die Quellen nennen widersprüchliche Lags (Widerspruch 5).
12. **Tages-TP und Session-Verteilung (Ø-Pips x 0,7-0,8).** Mechanismus: Tagesbewegung als Vielfaches der Durchschnittspips. Daten: Intraday-Kurse. Test im Repo: verwandt [[24h-renditestruktur-und-informationskette]]; Stichprobe der Quelle unbekannt.

### Lücken

- **Bild-only-Seiten ohne Text (Inhalt nicht erfasst):** Endogene Analyse (10 Seiten), Exogene Analyse (5), Gatekeeping (3), Reflektion und Optimierung (15), 9 von 11 Seiten "Incentive live"-Stoff (u. a. Titel Repo Markt, Carry Trades, M2 Geldmenge, Cot Analyse, Statistiken Time and Price), How To NFP Report, Currency Basic Swaps (nur Text-Fragment), eine Seite ohne Titel. Titel zeigen behandelte Faktoren, Schwellen/Regeln stecken in PNGs.
- **OCR-Qualität:** Bank-PDFs maschinell übersetzt, stark verstümmelt; bei BNPP-Monthly, UniCredit-Wochenreports, Fed-MPR und Teilen der Deutschen Bank nur Folientitel lesbar; Kalenderzeilen (Actual/Forecast/Previous) mit unsicherer Spaltenzuordnung; mehrere Seiten sind Doppelungen; Datumsangaben in Dateinamen teils falsch.
- **Fehlende Schwellen/Parameter:** Taylor-Regel (Potenzialproduktion), r*, "positive Liquidität" (Schwelle nicht definiert), Risk-on/off-Zustandsliste, Weitere Szenarien der Wachstum-x-Inflation-Matrix (Text abgeschnitten), Gewichte der Marktschwerpunkte (unbelegt), PIX/BEER-Formeln, Stichprobe der Tageszeit-Statistik (Instrument, Zeitzone), Interventionsschwelle nur als Zahl ohne Beleg.
- **Kein G8-Ranking im Material:** weder Methodik noch Gewichte; Ranking-Säulen Makro/Rates/Preis/Quant sind Vorschlag [Anm.]. Gates-Schema 5 Gates fehlt ebenfalls als geschlossene Regel (nur Einzelaussagen).
- **Eigene Auswertungen fehlen:** keine Trefferquoten, Pip-Bewegungen oder Stichprobengrößen zu News-Reaktionen im Text (T3 Abschnitt 0); der CPI-Backtest steckt in Charts/Handschrift.
- **Herkunft/Belegqualität:** viel Fremdmaterial (Bank-Reports, Chartbook, Hedgeye-Tabelle, Interview), nicht von eigener Erkenntnis trennbar; Behauptungen ohne Beleg (u. a. "manipulierte Daten", Banken pumpen Geld in China) als nicht belegt behandelt.
- **Datenlücken:** FedWatch-/OIS-Historie, Citi Surprise, PIX/Flussdaten, Basis-Swaps, Konsensdaten, BDI, JGB-Reihe sind nicht frei oder unklar.

## Express

[Anm.] Aus dem Material ableitbar, keine Entscheidung. Der Makro-Agent kann die
Tabelle "Faktoren" als Checkliste je Report-Abschnitt nutzen: Regime aus den
Faktoren mit Rolle R, G8-Ranking aus K (Säulen frei zugeordnet), Szenarien-
Signposts aus S, Gates aus G, Kein-Trade aus N. Jede Aussage im Report sollte
den Datenpunkt und die Quelle (z. B. FRED-ID) nennen, weil das Material
Einzelregeln statt eines geschlossenen Entscheidungsschemas liefert; die
Regeln mit WIDERSPRUCH nicht stillschweigend auflösen, sondern als
Unsicherheit ausweisen. Hypothesen aus dem Abschnitt Testkandidaten gelten als
ungetestet, bis sie den Backtest-Prozess und die Overfitting-Sperre
durchlaufen haben.
