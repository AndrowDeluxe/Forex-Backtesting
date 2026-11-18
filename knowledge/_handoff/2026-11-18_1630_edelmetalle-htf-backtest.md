# Handoff 18.11.2026 16:30 -- Edelmetalle HTF-Backtest (Plan freigegeben, noch kein Code)

## Nächster Schritt
- Am PC umsetzen, was unten im freigegebenen Plan steht (Nutzer hat den Plan am 18.11. per ExitPlanMode
  freigegeben). Es existiert noch **keine Zeile Code** für `fusion_lab/metals_htf/`, und der Lock
  `metals_htf_v1` ist **noch nicht registriert**. Als Erstes `Lock("metals_htf_v1").register_split("2004-01-01",
  "2017-12-31", "2026-05-10", "2026-11-13")` und die Merkmalsliste (Abschnitt „Merkmale“) unverändert als
  Vorab-Registrierung committen, bevor irgendein Test läuft.

## Learnings
- Die Cloud-Session kommt nicht an FRED/CFTC/Yahoo/stooq/investing/barchart (Proxy 403). Deshalb Nutzerentscheid:
  Lauf am PC. Lokal im Repo liegen nur `scripts/frozen_data/*_20261004.csv` (Gold/Silber/Kupfer/Öl/Bonds/EURUSD/
  USDJPY/IRX, bis 02.10.2026, **kein Platin, kein DXY, kein Realzins, kein COT**) – taugt nur als Rauchtest.
- Wiederverwendbar: `fusion_lab/gold_confirm/data.py` (`fetch_fred` mit Key aus `news_calendar._secrets`,
  `fetch_cftc`, `fetch_gld`, `fetch_imf`, `fetch_yf`-Muster, Parquets unter `fusion_lab/data/gold_confirm/`).
  Für Platin fehlen: PL=F, PPLT, CFTC-Code 076651; für die Kurve zusätzlich DGS10; DBC für rel. Stärke.
- Trade-Listen für die Filter-Stufe: `asb_trades`, `ctnl_trades`, `c2_trades` in `scripts/research_gold_confirm.py`.
  Achtung: Beim Import wird dort `LOCK = Lock("gold_confirm_v1")` angelegt; dessen `keep_vs_drop` nutzt den
  **alten** Split (IS 2010–19) – für `metals_htf_v1` eine eigene Version schreiben.
- `research_lock`: OOS frei (`oos_only`), Tresor einmalig nach `freeze`; `log_trials` sperrt nach `freeze`.

## Fehlannahmen / Vorsicht
- Der Rohstoff-Screener (Commit `943e0c9`) wertet COT **contrarian**. `gold_confirm` hat gezeigt, dass Managed Money
  **mit** dem Preis läuft – die Annahme ist also eher falsch; deshalb im Plan beide Vorzeichen testen.
- Gold-Tresor 11.05.–10.11.2026 ist durch `gold_confirm_v1` (Realzins/USD-Veto) schon geöffnet → für Gold-Makro
  nicht mehr unberührt. Silber/Platin sind die saubere Gegenprobe. Im Ergebnis offen sagen.
- Kurzfristig (1–5 T) hatte kein Gold-Baustein einen Edge, und der Score-„Edge“ war nur Golds Drift + Limit-Preis.
  Darum ist die Kontrolle „immer long“ + Zufalls-Timing mit gleicher Exposure Pflicht, sonst wiederholt sich das.

## Offene Fäden (meine Design-Skizze, noch nicht mit dem Nutzer abgestimmt)
- Wochen-Frame Freitagsschluss; jede Quelle per as-of erst ab Veröffentlichung (CFTC Bericht+3 T, FRED/GLD +1 T,
  IMF Monatsende+2 M); Normierung gleitendes Perzentil 156 W (min. 52 W).
- IC: Rang-z von Merkmal (mit erwartetem Vorzeichen) × Rang-z der Forward-Log-Rendite, Mittelwert = IC,
  Newey-West-t mit h−1 Lags.
- Regime: Perzentil > 2/3 long, < 1/3 short, sonst flat; Signal Fr t → Rendite t→t+1; Kosten je Positionswechsel
  (Vorschlag Gold 5, Silber 10, Platin 15 bps je Seite – noch Annahme, ins Dashboard „Braucht Bestätigung“).
- Zufallskontrolle: Positionsreihe permutieren (Exposure bleibt gleich), 1.000 Läufe, Perzentil der Sharpe.
- `--frozen`-Modus nur als Rauchtest, schreibt nach `results_frozen/` und zählt **keine** Trials.

## Der freigegebene Plan (sonst nur in der Cloud-Session gespeichert)
### Plan: Edelmetalle HTF – Score-Bausteine + Makro-Indikatoren backtesten (Gold, Silber, Platin)

#### Context

Der Rohstoff-Screener vom 18.11. arbeitet mit Gewichten, die nicht getestet sind: Trend 30, Momentum 25, rel. Stärke 15,
COT contrarian 20, 52-Wochen-Lage 10. Der Nutzer will für die Edelmetalle wissen, welche Bausteine und welche eigenen
Makro-Indikatoren und Filter **auf hohem Zeitrahmen (Wochen/Monate) die Richtung tragen**. Die Analyse soll professionell
und belastbar sein.

**Nutzerentscheide vom 18.11.:**
- Gold + Silber + Platin
- Ziel ist ein Richtungs-Bias **und** ein Filter
- **Long und Short gleichwertig**
- Der Lauf findet **auf dem PC** statt, weil FRED, CFTC und Yahoo in der Cloud gesperrt sind. Hier entstehen Code und Tests,
  dazu ein Rauchtest auf `scripts/frozen_data/`.

**Vorwissen, damit nichts doppelt läuft** ([[gold-confirmation-score]], Lock `gold_confirm_v1`):
- Auf **1–5 Tage** hatte kein Gold-Baustein einen Edge.
- COT Managed Money läuft **mit** dem Preis. Die Contrarian-Annahme im Screener ist also unbelegt und wird ausdrücklich
  geprüft.
- Einziger Fund war der Makro-Block (Realzins + USD) als Veto auf CTNL. Er ist live, der Tresor 11.05.–10.11.2026 ist
  dafür **verbraucht**.
- Neu ist hier der **Wochen-/Monatshorizont**, dazu Silber und Platin und die Screener-Bausteine.

#### Overfitting-Sperre (CLAUDE.md)

- `research_lock.Lock("metals_htf_v1").register_split`: IS 2004–2017, OOS 2018–10.05.2026 (frei), Tresor 11.05.2026–heute
  (einmalig, nur nach `freeze`).
- ⚠️ Für Gold ist der Tresor durch `gold_confirm_v1` schon berührt (Realzins/USD). Das wird im Ergebnis offen gesagt.
  Silber und Platin bleiben die unberührte Gegenprobe.
- Alle Merkmale, Lookbacks und erwarteten Vorzeichen werden **vor** dem ersten Test fest registriert. Jede Variante läuft
  über `log_trials` und geht in die Deflated Sharpe ein.
- Richtwert: höchstens 9 optimierte Punkte. Optimiert wird nur der Lookback aus {4, 13, 26} Wochen, alles andere ist
  fest.

#### Merkmale (vorab festgelegt, mit Wirkkette und erwartetem Vorzeichen)

| Gruppe | Merkmal | Quelle (Veröffentlichungs-Lag) | Erwartung |
|---|---|---|---|
| Screener | Trend (SMA50/200, `scoring.trend_points`) | Kurs | + |
| | Momentum 26 W − 4 W, vola-skaliert | Kurs | + |
| | rel. Stärke gegenüber DBC 13 W | Yahoo | + |
| | 52-W-Lage | Kurs | + (Trend) |
| | COT-Index Managed Money 3 J. | CFTC (Fr → nächste Woche) | **beide Vorzeichen** testen (contrarian gegen Trend) |
| Makro | Realzins 10J (DFII10): Δ13 W und Abstand zum 52-W-Mittel | FRED (+1 T) | − |
| | Dollar (DXY) Δ13 W | Yahoo | − |
| | Breakeven 10J Δ13 W | FRED | + |
| | 2J-Rendite Δ13 W (Fed-Erwartung) | FRED | − |
| | Zinskurve 10J−2J, Δ13 W | FRED | + (Steilerwerden) |
| | GLD-Bestand Δ13 W (ETF-Fluss) | SPDR (+1 T) | + |
| | Zentralbanken netto 12 M | IMF (+2 M) | + |
| | GVZ-Niveau (Vola-Regime) | FRED | ± (nur Info) |
| Relativ | Gold/Silber-Ratio z-Score 52 W | Kurs | Silber: + bei hohem Ratio |
| | Kupfer/Gold Δ13 W (Wachstum) | Kurs | Silber/Platin: + |
| | Faber-10-Monats-SMA als Trend-Referenz | Kurs | + |

#### Ablauf (8-Phasen-Prozess, Phase 6 vor Portfolio-Arbeit)

1. **Daten** (`fusion_lab/metals_htf/data.py`):
   - Die Fetcher aus `fusion_lab/gold_confirm/data.py` wiederverwenden: `fetch_fred`, `fetch_cftc`, `fetch_gld`, `fetch_imf`
     und `fetch_yf`-Muster.
   - Ergänzt werden Platin (PL=F, CFTC 076651, PPLT), DBC, DXY und HG.
   - Daraus entsteht ein Wochen-Frame (Freitagsschluss). Jedes Merkmal wird erst ab seinem Veröffentlichungstag benutzt.
   - Normierung über ein **gleitendes** 3-Jahres-Perzentil, also ohne Vorgriff.
2. **Stufe 1 – Einzel-IC (nur IS):**
   - Spearman-IC je Merkmal × Metall × Horizont 4/13/26 W, mit Newey-West-t (überlappende Fenster).
   - Kandidat ist ein Merkmal nur bei IS-|t| ≥ 2 **mit** dem erwarteten Vorzeichen **und** gleichem Vorzeichen bei
     mindestens 2 von 3 Metallen.
   - Dazu Stabilität über die Teilzeiträume 2004–10 und 2011–17.
   - OOS wird nur zum Vergleich daneben gezeigt.
3. **Stufe 2 – Regime-Regel je Kandidat:**
   - Wöchentlich long im oberen Drittel, short im unteren, sonst flat. Die Drittel-Grenzen kommen aus dem gleitenden
     Perzentil.
   - Mit Kosten und Roll-Hinweis.
   - Long- und Short-Bein getrennt ausgewiesen.
   - **Kontrollen:**
     - „immer long“
     - Zufalls-Timing mit gleicher Exposure (Bootstrap, 1.000 Läufe)
     - Faber-SMA
   - Erfolg heißt: schlägt beide Kontrollen in IS **und** OOS (Lehre aus `gold_confirm`, wo der „Edge“ nur der Drift war).
4. **Stufe 3 – Komposit:**
   - Gleichgewichteter Mittelwert der überlebenden Merkmale, keine gefitteten Gewichte.
   - Damit wird der Screener-Score nachgebaut: alt (Gewichte vom 18.11., COT contrarian) gegen neu (Komposit) gegen
     „nur Trend“.
5. **Stufe 4 – als Filter:**
   - Bias als Veto auf die Live-Gold-Edges ASB, CTNL und C2. Die Trade-Listen kommen aus `asb_trades`, `ctnl_trades`
     und `c2_trades` in `scripts/research_gold_confirm.py`, die Wiederverwendung läuft über einen Import.
   - Behalten und gesperrt werden getrennt ausgewertet, mit `keep_vs_drop` plus Zufalls-Wegnahme-p-Wert.
   - Der bestehende CTNL-Makro-Veto wird ausdrücklich herausgerechnet, damit nichts doppelt zählt.
6. **Stufe 5 – Robustheit (Phase 6):**
   - Jahresreihe
   - Bootstrap-KI
   - Monte-Carlo-Drawdown
   - Lookback-Nachbarschaft 4/13/26 W: Funktioniert nur ein Wert, ist der Kandidat verworfen.
   - Deflated Sharpe über alle gezählten Varianten
   - Vier-Fragen-Check je Fund
7. **Tresor:** Nur auf Nutzerfreigabe nach `freeze`, einmalig.

#### Dateien

- Neu: `fusion_lab/metals_htf/{__init__,data,features,backtest}.py`
- Neu: `scripts/research_metals_htf.py --stage data|ic|regime|composite|filter|robust`, Muster
  `scripts/research_gold_confirm.py`
- Ergebnisse nach `fusion_lab/data/metals_htf/results/*.csv`
- Neu: `tests/test_metals_htf.py`:
  - kein Vorgriff (Lag pro Quelle, gleitendes Perzentil)
  - Wochen-Resampling
  - Regime-Rendite gegen Handrechnung
  - Kontrollen
  - Lock-Integration
- Doku:
  - neue PARA-Notiz `knowledge/projects/edelmetalle-htf-makro.md` mit Methode, Tabellen und Vier-Fragen-Check
  - `CHANGELOG.md`
  - `DASHBOARD.md` (Fokus Dachprojekt, „Als Nächstes“: Lauf auf dem PC)
  - Annahmen unter „Braucht deine Bestätigung“: Split, Merkmalsliste, Drittel-Regel, Kosten
- Der Screener (`config.WEIGHTS_COMMODITIES`) wird **nicht** geändert. Ein Vorschlag für Version 1.1 kommt erst nach den
  Ergebnissen und deiner Entscheidung.

#### Verification

- Hier in der Cloud:
  - `pytest tests/test_metals_htf.py tests/test_screener.py`
  - Rauchtest `python scripts/research_metals_htf.py --stage ic --frozen` auf `scripts/frozen_data/`: Gold, Silber,
    Kupfer; 10J-Note und IRX als Zins-Ersatz; EURUSD als Dollar-Ersatz. Er prüft nur, ob die Pipeline läuft. Diese
    Ergebnisse werden **nicht** berichtet.
- Auf dem PC:
  - `python scripts/research_metals_htf.py --stage data`, dann alle Stufen der Reihe nach
  - Ergebnisse committen
  - Ich werte sie anschließend in einer Session aus und schreibe die Analyse.
