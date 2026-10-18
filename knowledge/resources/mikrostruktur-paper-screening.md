# Resource: Mikrostruktur-Paper-Screening (SMH Elite 3, Runde 2)

Paper-Screening für das Team-Feld „Mikrostruktur und Liquidität“ (Briefing
05.10.2026, Folie 5: „Wer sofort handeln will“). Gesucht wurde am 18.10.2026
nach Folie 6 (SSRN plus arXiv q-fin). Das Raster wurde vor dem Lesen
festgelegt: `smh_microstructure/screening_v2.json`. Backtest und Ergebnis
stehen in [[smh-elite-mikrostruktur]] (Abschnitt „Runde 2“).
Verwandt: [[fx-microstructure]], [[overfitting-sperre]].

## Capture

**Zugang:** SSRN blockt jeden automatischen Zugriff mit HTTP 403, betroffen
sind Suche, Abstract-Seiten und PDFs. Gefunden wurden die Papers deshalb über
die Websuche. Die Volltexte kamen aus freien Fassungen:
- Bank of Canada, NBER, NY Fed, Norges Bank, QMUL, UWA
- arXiv über die offene API (17 Treffer)

**Suchmatrix:** Effektbegriff × Markt × Filterwort.
- Effektbegriffe: order flow, price clustering, liquidity provision, spread,
  fixing, overnight drift, periodicity, closing auction, stop clustering.
- Märkte: FX, S&P 500, Nasdaq, Gold, Öl.
- Filterwörter: return predictability, trading strategy, anomaly.

## Organize: Bewertung

Ausschlussgründe (K.-o.):
- **K1:** braucht Daten, die wir nicht haben (Orderbuch, Kundenflows, Volumen).
- **K2:** Mechanismus passt nicht zum Feld.
- **K3:** schon geprüft.
- **K4:** keine Regel formulierbar.

Punkte (je 0–3):
- **P1:** Effekt gegen unsere Kosten
- **P2:** Menge
- **P3:** Beleg
- **P4:** kein Zerfall

| Paper | Quelle | Urteil |
|---|---|---|
| Krohn, Mueller, Whelan: FX Fixings and Returns Around the Clock (JF 2024) | BoC SWP 2021-48 | Europa 9 Punkte → **K4**, Tokio 8 → **K5** |
| Breedon, Ranaldo: Intraday Patterns in FX Returns and Order Flow (2013) | SNB WP 2011-04, QMUL wp694 | 9 Punkte, gleiches Fenster wie K4 → **K4-Variante** |
| Heston, Korajczyk, Sadka: Intraday Patterns in the Cross-Section (JF 2010) | UH-PDF | 8 Punkte (nur Aktien belegt) → **K6** |
| Boyarchenko, Larsen, Whelan: The Overnight Drift (NY-Fed SR 917) | NY Fed | 6 Punkte (1,48 bps < 2,6 bps Kosten, Zerfall seit 2021) → **K7** |
| Ito, Yamada: Puzzles in the Tokyo Fixing (JIE 2017) | NBER w22820 | P1 0: Spitze wirkt nur Sekunden um 9:55. Gotobi als **K5-Variante** |
| Caminschi, Heaney: London PM Gold Fix (JFM 2014) | UWA | P1 0, P4 0: Auktion seit 2015 neu, Effekt nur in den Auktionsminuten |
| CBS-Masterarbeit: Gold Price Dynamics Around the Clock | CBS | P3 0: Masterarbeit, kein SSRN |
| Panagiotou: The WMR Fix (Norges Bank/EFMA 2017) | Norges Bank | K3 (= K2 Runde 1) |
| Evans: Forex Trading and the WMR Fix (JBF 2018) | MPRA | K3 (= K2 Runde 1) |
| Della Corte, Kosowski, Wang: Market Closure and Short-Term Reversal | SSRN 2730304 | K3 (≈ Overnight-Reversal/Nagel), Querschnitt |
| Miwa: Short-Term Return Reversals and Intraday Transactions | SSRN 3174484 | K1 (Einzelaktien) |
| Elaut, Frömmel, Lampaert: Intraday Momentum in FX (JFM 2018) | Elsevier | K3 (Intraday-Momentum), kein freier Volltext |
| Gao, Han, Li, Zhou: Market Intraday Momentum (JFE 2018) | – | K3 |
| Todorov: Leveraged-ETF-Rebalancing | SSRN 3504016 | K1 (ETF-Bestände) |
| St. Gallen: LETF Price Pressure | SSRN 3925725 | K1 |
| Closing-Auction-Preisabweichungen | SSRN 3485840 | K1 (Auktionsdaten, Einzelaktien) |
| Dao, McGroarty, Urquhart: Weekend Overreaction FX (JMFM 2016) | Soton | K3 (≈ Caporale/Plastun Gap-Fade) |
| Burnside, Cerrato, Zhang: Order Flow Risk Factor | SSRN 3275356 | K1 (Kundenflows) |
| Osler: Currency Orders (JF 2003) | – | K3 (= K1 Runde 1) |
| Choi, Larsen, Seppi: TWAP-Benchmarks (2020) | – | K4 (Theorie) |
| Ni, Pearson, Poteshman: Pinning (2005) | – | K1 (Optionsdaten); neuere Studie 2016–25: kein Pinning |
| arXiv q-fin.TR/ST, 17 Treffer | API | K1: Orderbuch, HFT, Theorie |

## Distill

- **Testbares bleibt wenig übrig.** Die meisten Mikrostruktur-Papers brauchen
  Orderbuch, signiertes Volumen oder Kundenflows. Mit M1-OHLC bleiben im
  Wesentlichen Uhrzeit-Effekte rund um Benchmark-Zeitpunkte übrig.
- **Die Papers sagen die Kostenhürde selbst voraus.**
  - Krohn et al.: Mit vollem Spread ist das W negativ, positiv wird es erst
    mit halbem Spread.
  - Boyarchenko et al.: Nach Spread liegt die Sharpe bei −0,5.
  - Die Prämie gehört dem, der Liquidität stellt, nicht dem, der sie nimmt.

## Express

Getestet als K4–K7 in [[smh-elite-mikrostruktur]], Runde 2. Alle vier
Tresore sind negativ.
