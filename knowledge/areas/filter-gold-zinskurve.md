# Area: Filter-Baustein „Gold-Zinskurve“

Wiederverwendbarer Richtungsfilter für Gold-Strategien -- Schicht „Zinsen“ im Schichtenmodell
([[regime-bestimmung-und-filter]], Nutzerentscheid 02.11.2026: „So gehen wir das an“). Seit 02.11.2026
separat festgehalten, damit er an anderen Edges geprüft werden kann (Nutzerauftrag).

## Definition

- Code: `fusion_lab/filters/zinskurve_regime.py` → `GoldZinskurvenFilter(lag=20, confirm=5)`;
  `allows(side, date)`, `direction(date)` (+1 nur long, −1 nur short, 0 beide), `regime_at(date)`.
- Regime nach Angelo (OneNote „Elite 2 / Makro Angelo / Zusammenfassung Regime“): US 10y−2y-Spread,
  2y und 10y (FRED DGS2/DGS10) heute gegen vor 20 Handelstagen → Bull/Bear × Steepener/Flattener;
  gegenläufige Renditen = Twist.
- **Geglättet:** ein Regime gilt erst nach 5 Tagen Bestand; Twist bestätigt nie; bis dahin bleibt
  das letzte bestätigte Regime. (Roh wechselt das Regime 69×/Jahr, Median 2 Tage -- unbrauchbar.)
- Gold-Richtung aus Dennis' Risk Regime Matrix: Goldilocks/Reflation **long**, Inflation **short**,
  Deflation ohne Angabe (beide).
- Kein Vorgriff: Abfrage nutzt nur FRED-Werte bis zum Vortag.

## Belege bisher (alle IS 2016–2021)

1. Richtung allein (Lock `regime_quelle_vergleich`): 20-Tage-Goldrendite in Filter-Richtung
   +93 bp, t 2,16, 60 % Treffer (1 von 6 geprüften Zellen; USD-Richtung trägt mit keiner Quelle).
2. Daily-Edge Typ C2 (Continuation mit Limit-Einstieg), nur Gold ([[htf-daily-trade-edge-card]]):
   mit Filter +0,70 / +0,64 R je Trade (n 24/23, t 1,47/1,61), gegen den Filter −0,22 / −0,07 R;
   ohne Filter +0,35 R. DSR 0,12–0,16 (Locks mit 154 Versuchen).
3. Daily-Edge Typ R (Reversal), nur Gold: **keine** klare Wirkung (einmal besser, einmal schlechter).

Lesart: Der Filter passt zu Strategien **in Trendrichtung** (Continuation, Breakout, Trendfolge),
nicht zu Gegentrend-Einstiegen. Stichproben noch klein -- Beleg steht aus.

## Prüfprotokoll für andere Edges

1. Nur Strategien, die Gold handeln; Richtung des Trades muss bekannt sein.
2. Vor dem Test festlegen: welche Variante, Parameter unverändert (lag 20, confirm 5) -- jede
   Abweichung ist ein neuer, gezählter Versuch ([[overfitting-sperre]]).
3. Drei Läufe auf IS der jeweiligen Strategie: ohne / mit Filter / gegen Filter (Kontrolle).
   Erwartung: mit > ohne > gegen. „Gegen“ besser als „mit“ = Filter passt nicht zur Strategie.
4. Ergebnis hier unter „Belege“ nachtragen, mit Lock-Name und Versuchszahl.

Kandidaten (noch nicht geprüft): Gold ASB (Breakout, live), gold_silver, CTNL-Continuation,
trend_pullback auf Gold, OU-Gold-Bein.

## Datenquellen für die FX-Schicht (Recherche 02.11.2026)

Tägliche Staatsanleihen-Renditen, kostenlos, ohne Schlüssel (Abruf am 02.11. getestet):

| Währung | Quelle | Abruf | Status |
|---|---|---|---|
| USD | FRED DGS2 / DGS10 | `fusion_lab.g8.data.fetch_fred` | läuft |
| EUR | EZB Data Portal, Euro-Zinskurve (AAA), Reihe `YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y` (10Y: `SR_10Y`), ab 09/2004 | `https://data-api.ecb.europa.eu/service/data/...?format=csvdata` | ✅ |
| JPY | Japanisches Finanzministerium, JGB-Referenzrenditen 1–40 J. ab 1974 | `mof.go.jp/.../interest_rate/jgbcme.csv` (laufender Monat) + `historical/jgbcme_all.csv` | ✅ im Loader (10.11.) |
| CAD | Bank of Canada Valet API, `BD.CDN.2YR.DQ.YLD` / `BD.CDN.10YR.DQ.YLD` | `bankofcanada.ca/valet/observations/<Reihe>/csv` | ✅ im Loader (10.11.) |
| GBP | BoE IADB: `IUDSNPY`/`IUDMNPY`/`IUDLNPY` = 5/10/20 J. Par (M = 10 J. bestätigt: 5,14 % = TVC GB10Y); 2y nur in der Spotkurven-ZIP (xlsx) | im Loader stattdessen TradingView `TVC:GB02Y`/`GB10Y` | ✅ über TVC (10.11.) |
| AUD | RBA Tabelle F2; RBA selbst blockt (403), Spiegel DBnomics `RBA/F2` (`FCMYGBAG2D`/`10D`), ~4 Tage Verzug | `api.db.nomics.world/v22/series/RBA/F2/<Reihe>` | ✅ im Loader (10.11.) |
| CHF | SNB-Würfel `rendeiduebd` (D0 = CHF, `2J`/`10J`), täglich, aber wöchentlich veröffentlicht (~10 Tage Verzug). `rendoblid` ist monatlich. TVC CH02Y als Ersatz verworfen: Wochen-Korrelation zur SNB nur 0,51 | `data.snb.ch/api/cube/rendeiduebd/data/csv/en` | ✅ im Loader, Verzug |
| NZD | RBNZ B2 blockt (403, nicht umgehen) | TradingView `TVC:NZ02Y`/`NZ10Y` | ✅ über TVC (10.11.) |

Abgleich TVC gegen amtlich (10.11., 2024–26, 2J): Tagesänderungen korrelieren bei US/JP/CA mit
0,90–0,96 ohne Tagesversatz (Datumszuordnung stimmt), AU nur 0,52 (anderer Schnappschuss-Zeitpunkt,
Woche 0,87), CH 0,15 (Woche 0,51). GB/NZ sind darum über TVC brauchbar für Wochenveränderungen,
Tageswerte mit Vorsicht.
| EUR (DE) | Bundesbank-Zeitreihen | `api.bundesbank.de` | Abruf brach ab (Zeitüberschreitung); EZB reicht |

## Quellen

- [readecb (ECB Data Portal, Zinskurve)](https://cran.r-project.org/web/packages/readecb/readme/README.html)
- [QuantConnect: ECB Euro Yield Curve](https://www.quantconnect.com/docs/v2/writing-algorithms/datasets/european-central-bank/euro-yield-curve)
- [Bank of England: Yield curve terminology](https://www.bankofengland.co.uk/statistics/yield-curves/terminology-and-concepts)
- [boe R-Paket: Anderson-Sleath-Kurven](https://cran.r-project.org/web/packages/boe/vignettes/yield-curves.html)
- [DBnomics: RBA F2](https://db.nomics.world/RBA/F2)
- [MoF Japan: JGB-Zinsen Q&A](https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/qa.htm)
- [Bank of Canada: Canadian bonds](https://www.bankofcanada.ca/rates/interest-rates/canadian-bonds)
- [Bank of Canada Valet: 2-year](https://www.bankofcanada.ca/valet/observations/BD.CDN.2YR.DQ.YLD/json?recent=1)
