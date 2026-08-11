# Resource: Crypto Volume-Profile Mean-Reversion

Destillate von Papers, die Volume-Profile/Value-Area-Konzepte (POC, VAH,
VAL) als Mean-Reversion-Signal auf Krypto-Instrumenten einsetzen. Verwandt:
[[crypto-etf-flows]] (gleiche Asset-Klasse, anderes Thema).

---

## Volume Profile Mean Reversion Strategy with Tape Speed Confirmation (SOL/USDT)

**Capture** -- Perera, L N H (2026, Independent Market Researcher, Research
White Paper, June 13, 2026); erfasst 2026-08-11, manuell im Chat.

**Organize** -- Tags: crypto, volume-profile, point-of-control, value-area,
mean-reversion, tape-speed, transaction-costs, SOL. Verwandtes bestehendes
Code-Modul: `auction_playbook/` (siehe Cross-Check -- fast identische
Kernidee, bereits gebaut, echte Binance-Daten).

**Distill**
- **Kernthese**: LONG bei Preis <= Vortages-VAL + Tape-Speed-Bestätigung
  (Volumen-gewichtetes Momentum-Signal >= 0.5), SHORT bei Preis >=
  Vortages-VAH, Ziel = aktueller Tages-POC, fixer Stop in %. Kernbefund des
  Papers: die Stop-Loss-Distanz relativ zu Transaktionskosten entscheidet
  über Viabilität, nicht die Signalqualität selbst -- 0.15% SL ist wegen
  Kosten (0.14% Round-Trip bei Binance-Futures-Konditionen) mathematisch
  unviable (98.3% Stop-Hit-Rate, -470% Net-P&L über 1.701 Trades), 2.00% SL
  liefert angeblich Sharpe 3.98, Profit-Faktor 2.83, +354% über 5 Jahre.
- **Kritischer Vorbehalt (nicht nur Nacherzählen)**: Sämtliche 5 Jahre
  Kursdaten sind SYNTHETISCH generiert (GBM + Mean-Reversion mit 30-Tage-
  Halbwertszeit + Student-t-Fat-Tails df=3), keine echten SOL/USDT-Daten.
  Die Begründung im Paper ("keine frei verfügbaren 5-Min-SOL/USDT-Daten für
  5 Jahre") ist sachlich falsch -- echte SOL/USDT-5m-Daten sind über die
  Binance-API seit dem SOL-Listing frei verfügbar, exakt dieselbe
  Datenquelle, die dieses Repo für BTCUSDT/ETHUSDT bereits nutzt
  (`auction_playbook/data.py`). Weitere Red Flags: zugegebener Look-Ahead-
  Bias (Tages-POC wird aus vollständigen Tagesdaten berechnet, in Live
  erst am Tagesende bekannt -- verzerrt die berichtete 71%-Zieltrefferquote
  systematisch nach oben), keine Funding-Fees, Marketing-Duktus
  ("FATAL FINDING"-Boxen), und die "Monte-Carlo-Validierung" zieht
  Bootstrap-Samples aus denselben 1.701 synthetischen Trades -- kein
  echter Out-of-Sample-Test, nur eine Pfad-Resampling-Illustration derselben
  (synthetischen) Verteilung. Die berichteten Kennzahlen sind daher keine
  belastbare Evidenz für echte Märkte.
- **Zentrales Modell/Filter**: (1) Volume-Profile-Value-Area (POC/VAH/VAL,
  70%-Volumen-Schwelle, Vortages-Referenz als Kontext) -- Standard-Auction-
  Market-Theory-Konstrukt, nichts Neues ggü. bereits im Repo Vorhandenem.
  (2) "Tape Speed" = sign(5-Perioden-Preismomentum) × (Volumen /
  5-Perioden-Volumen-MA), 3-Perioden-geglättet, Schwelle 0.5 -- das ist der
  einzige im Repo noch nicht vorhandene Baustein. (3) Kosten-vs-Stop-Ratio
  als Viabilitätskriterium für Stop-Wahl -- allgemein übertragbare,
  plausible Heuristik unabhängig vom Rest des Papers.
- **Was ist potenziell integrierbar**: Nicht die synthetischen
  Performance-Zahlen. Die STRUKTUR (Vortages-Value-Area als Kontext,
  POC-Ziel, Fade bei Value-Area-Ausbruch) ist praktisch deckungsgleich mit
  dem bereits existierenden `auction_playbook`-Mean-Reversion-Setup -- dort
  aber mit echten Daten gebaut. Der Tape-Speed-Indikator ist ein möglicher
  Zusatz-/Alternativ-Filter zum dortigen CVD-Aggressions-Filter (Taker-Delta-
  Z-Score), aber kein eigenständig integrierbarer Baustein ohne echten Test.

**Express**
- **Cross-Check statt neuem Backtest**: Da `auction_playbook/` bereits eine
  strukturell fast identische Value-Area-Mean-Reversion-Strategie auf echten
  Binance-Daten implementiert (`indicators.py`: POC/VAH/VAL-Berechnung,
  `signals.py`: Fade zur Vortages-POC bei gescheitertem Ausbruch), wurde
  statt eines neuen Backtests der bestehende Real-Daten-Test herangezogen
  (`scripts/research_auction_playbook.py`, BTCUSDT/ETHUSDT, Aug 2025-Jul
  2026, echte Taker-Buy/Sell-Volumendaten statt Tape-Speed als Konfirmation):
  - BTCUSDT 5m (Default-Config, n=30): Win-Rate 46.7%, Profit-Faktor **0.83**,
    ø R-Multiple -0.21, Median -0.40 -- netto negativ.
  - ETHUSDT 5m (gleiche Config, n=42): Win-Rate 47.6%, Profit-Faktor **0.84**,
    ø R-Multiple -0.20, Median -0.54 -- netto negativ.
  - BTCUSDT 15m (n=10, kleine Stichprobe): Win-Rate 60%, Profit-Faktor 1.51,
    ø R-Multiple +0.14 -- leicht positiv, aber bei 10 Trades statistisch
    nicht belastbar.
  - **Unterschiede zu beachten** (kein 1:1-Vergleich): anderes Symbol
    (BTC/ETH statt SOL), Ziel ist die VORTAGES-POC (nicht die
    Look-Ahead-behaftete aktuelle Tages-POC wie im Paper), Konfirmation ist
    CVD-Aggression statt Tape-Speed, kein fixer %-Stop sondern ATR-Puffer.
  - **Einordnung**: Auf echten Daten mit der strukturell nächstliegenden
    bereits gebauten Strategie zeigt sich kein robuster Edge auf der
    Standard-Auflösung (5m) -- passend zum wiederkehrenden Muster in
    diesem Repo (s. [[fx-microstructure]]: Paper-Edges verschwinden häufig
    auf echten Daten). Das stützt die oben geäußerte Skepsis gegenüber den
    synthetischen 2.00%-SL-Ergebnissen des Papers.
- **Nächster Schritt**: Kein eigenständiger neuer Backtest-Kandidat. Falls
  die Tape-Speed-Konfirmation isoliert interessant erscheint, könnte sie als
  alternativer Konfirmations-Filter in `auction_playbook/signals.py` gegen
  echte SOL/USDT-Daten (Binance, frei verfügbar, nicht in `data_cache_crypto/`
  gecacht) getestet werden -- aber kein Automatismus, da die bestehende
  Mean-Reversion-Variante auf 5m bereits keinen Edge zeigt.
- **Ergebnis**: kein integrierbarer Baustein. Bestehender Code:
  `scripts/research_auction_playbook.py`, `app_pages/auction_playbook.py`.
