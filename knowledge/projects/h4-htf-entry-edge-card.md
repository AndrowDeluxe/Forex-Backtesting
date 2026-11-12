# Project: Edge Card „Final H4 HTF Entry Model“ (A6)

**Status (12.11.2026):** Phase 0 abgeschlossen. **Mechanischer Test (456 Varianten): kein Edge, brutto ≈ 0.** Offen: was deine Auswahl von der Regel unterscheidet. Prozess: [[edge-card-workflow]]. Teil der Inventur (Strang 0) im
[[quant-diskretionaer-fusion]], Eintrag A6 in [[persoenlicher-tradingplan-validierung]]. Ziel (Nutzer 11.11.):
Bestandteil eines Portfolios aus den händischen Edges, getrennt vom Quant-Portfolio.

Quelle: OneNote „Meine Trading Edges / ✅️ Final H4 HTF Entry Model“ (22.10.2024, 10 Bilder; Rohtext
`fusion_lab/raw/onenote/.../✅️ Final H4 HTF Entry Model__f8a7a22d51.md`). Backtest EURUSD H4 2023 mit 30
Beispielen, gemeinsam mit Jakob erarbeitet (Nutzer 11.11.). Screenshots: TradingView, FXCM, Konto „Jakob_ro1“.

## Phase 0 -- Strategieverständnis

Regeln wörtlich (Confis):
1. Mit dem BIAS
2. H4-Timeframe
3. Manipulation → mind. 2 Candle raus manipuliert (großer Wick)
4. Entweder 1 Candle nach Manip. abwarten (safe) oder Marketorder in Candle nach Manipulation
5. 1:3 CRV oder Liq.-Ziele
6. Entry am Closing Price -- SL unter/über Manipulation

Geklärt (Nutzer 11.11.):
- **Manipulation** = EINE H4-Kerze sticht mit dem Docht über das Hoch/Tief von mindestens 2 vorherigen Kerzen
  und schließt wieder zurück (Sweep).
- **BIAS** = Daily-Struktur bzw. H4-Struktur; zusätzlich mit den Trendfiltern der Daily-Matrix testen
  (u. a. EMA-Filter, Faber, MA 12/20).
- **Märkte**: die 9 Märkte des Daily-Tests (EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY, USDCAD, USDCHF, Gold, Silber).
- **Quelle**: gemeinsamer Backtest mit Jakob.

Beispiele 2023 (Bildtexte): Mehrheit TP mit 1:3 oder bis zur nächsten Liquidität, mehrere BE
(„unschöne Liq gebaut, Gefahr Major Inducement“). Mehrere Trades gegen den übergeordneten BIAS
(Nr. 1, 8, 9, 14, 21, 22, 25: „Retracement Point“, „IPDA-Shift“, „Korrektur“).

Geklärt (Nutzer 12.11.):
- **BE** nach neuer Struktur: Stop auf Einstieg, sobald nach dem Einstieg eine neue Struktur (BOS/Liquidität) in
  Trade-Richtung entsteht.
- **Gegen-BIAS-Trades**: jede Manipulation handeln, getrennt nach mit/gegen BIAS auswerten (wie Daily-Matrix).
- **Ziel**: 1:3, nächstes H4-Swing-Hoch/-Tief und Vortag/Vorwoche als Varianten vergleichen.
- **Einstieg**: beide Varianten aus der Regel (Market zum Schluss der Kerze nach der Manipulation bzw. Schluss
  der Manipulationskerze; „safe“ = eine Kerze abwarten).

## Entwurf Feld 01 IDEE / 02 REGEL (zur Bestätigung)

01 IDEE: Eine H4-Kerze holt mit dem Docht die Liquidität über/unter mindestens zwei Vorkerzen und schließt
zurück; danach läuft der Preis in die Gegenrichtung des Sweeps, bevorzugt mit dem BIAS.

02 REGEL (Sequenz):
1. H4-Kerze k: Hoch > max(Hoch k−1, k−2) und Schluss < dieses Max (Short-Manipulation), bzw. Tief < min(Tief k−1,
   k−2) und Schluss > dieses Min (Long-Manipulation). „Großer Wick“: Docht-Anteil als Variante (ohne / ≥ 50 %).
2. BIAS-Zustand je Trade: Daily-Struktur, H4-Struktur, Trendfilter der Daily-Matrix → mit / gegen / neutral.
3. Einstieg E1 = Schluss der Kerze k (Market in der Folgekerze); E2 „safe“ = Schluss der Kerze k+1, nur wenn
   sie die Manipulation nicht bricht.
4. Stop hinter dem Docht der Manipulationskerze.
5. Ziel: 1:3 | nächstes H4-Swing | Vortag/Vorwoche. BE nach neuer Struktur in Trade-Richtung (Variante: ohne BE).


## Bisherige Repo-Befunde mit ähnlicher Mechanik (nur Hinweis, kein Ersatz für den Test)

- Daily C1 (Daily-Manipulationskerze, Docht ≥ 50 % über 3 Vorkerzen) war im Daily-Test schwächer als C2.
- CRT (Sweep der Vorkerzen-Range und Schluss zurück, M15–H4, Gold + EURUSD) war brutto negativ; der
  Vorteil „Early Ones“ kam nur über den weiteren Stop ([[crt-manipulation-ist-stopweiten-mechanik]]).
  Folgerung fürs Testdesign: Varianten immer bei gleicher Stopweite/CRV vergleichen.

## Feld 05 / Test 1: mechanische Regel, 9 Märkte (12.11.2026, Lock `h4_manip`, 456 Versuche)

`python -m htf_daily_trade.h4_manip` → `h4_manip_varianten.csv`, `h4_manip_trades.csv`; Tests `tests/test_h4_manip.py`.
H4 zur Broker-Serverzeit (NY+7), IS 2016–21, OOS 2022 bis 11.05.2026 (Tresor letzte 6 Monate und Blind 2010–15 zu).
24 Grundvarianten (Docht W0/W1 × Einstieg E1/E2 × Ziel 3R/H4-Swing/Vortag-Vorwoche × BE ohne/nach BOS) × 9 BIAS-Filter
(Daily-/H4-Struktur, T1–T7) mit/gegen. Kosten Spread + Kommission + TTP-Swap.

- **Alle 24 Grundvarianten sind in IS und OOS negativ** (IS −0,12 bis −0,23 R, OOS −0,06 bis −0,20 R, je ~6.000–22.000
  Trades), 0–1 von 11 Jahren positiv, 0–1 von 9 Märkten.
- **Brutto liegt alles bei ≈ 0** (IS −0,04 bis +0,01 R). Die Kosten fressen 0,10–0,20 R, weil der Stop hinter einem
  H4-Docht klein ist.
- **Gegenprobe Zufallseinstieg** (gleiche Seite, gleiche Stopweite, 3 R): brutto IS −0,05 / OOS −0,09 R gegen Signal
  −0,04 / −0,04 R → die Manipulationskerze trägt keine Information über den Zufall hinaus.
- **BIAS:** Kein Filter dreht ins Plus. Gegen den Trend leicht besser als mit (bester T5 Ribbon gegen: brutto IS +0,065,
  OOS +0,01 R; netto −0,08). Gleiche Richtung wie beim Daily-C2 (trägt nur gegen den HTF-Trend), aber hier zu schwach.
- **Abgleich EURUSD 2023:** Die Regel liefert 185 Signale (W1 E1 3R mit BE) statt deiner 30 Beispiele; 21 % Ziel,
  70 % Stop. Deine 30 Beispiele (26 TP, 0 SL) sind also eine starke Auswahl aus den mechanischen Signalen.
- **Folgerung:** Der Edge (falls vorhanden) liegt nicht in der Kerze selbst, sondern in der Auswahl: Ort der
  Manipulation (welche Liquidität, Key Level, Session), Kontext oder Rückblick-Effekt beim händischen Backtest.
  Nächster sinnvoller Schritt nur mit Nutzerinput: Merkmale benennen, die deine 30 Beispiele von den übrigen
  ~155 Signalen 2023 trennen, oder echte H4-Trades aus dem Journal 2025 nehmen.

