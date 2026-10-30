# Residual-Edge-Check der Live-Beine (28.10.2026)

**Frage:** Verdient ein Bein eigenes Geld, oder bildet es nur das Halten des Basiswerts
nach (zum Beispiel „Gold ASB ist verkappt Gold long“)?
**Werkzeug:** Skill `residual-edge-analyzer` (tradermonty). OLS mit HAC-t-Werten nach
Newey-West, rollierend über 63 Tage, Gegenproben, Regime.
**Status:** abgeschlossen, diagnostisch. Es wurde nichts optimiert und keine Größe geändert.
Unter der [[overfitting-sperre]] ist das keine Variante.

## Aufbau (vorab festgelegt)
- **Strategie:** simulierte Trades mit gemessenen TTP-Kosten
  (`portfolio_construction/results/live_trades_ttp_2019_2026.csv`). gold_silver kommt aus
  der Tickmill-Liste `ampel`, weil es in der TTP-Liste fehlt. R × 1 % Risiko, nach
  Exit-Tag summiert.
- **Fenster:** OOS + Tresor je Bein. ORB, Gold ASB, gold_silver und OU ab 2023. CLS ab
  06/2022. trend_pullback ab 07/2024. CTNL ab 08/2024, ohne sauberes OOS, darum als
  `in_sample` deklariert.
- **Hauptmodell:** Basiswert halten: SPX, NDX, DJI, Gold, EURUSD. Bei OU ist SPX nur eine
  Näherung für den Aktienkorb, bei trend_pullback ist Gold nur eine Näherung für die
  Multi-Märkte.
- **Gegenproben:**
  - Basiswert + 12-Monats-Trendfaktor
  - Gold + Silber (bei den Gold-Beinen)
- **Regime:** Wachstum × Inflation aus `fusion_lab/data/macro_regime/labels.parquet`. Im
  Fenster war das Wachstum immer steigend, es gibt also nur 4 Zellen.
- **Code und Ergebnisse:** `portfolio_construction/residual_edge/build_inputs.py` →
  `portfolio_construction/results/residual_edge/`.

## Ergebnis (Hauptmodell)

| Bein | Alpha t | Beta zum Basiswert (t) | R² | Edge-Ratio | Alpha-Fenster positiv | Anteil Basiswert am Ertrag |
|---|---|---|---|---|---|---|
| trend_pullback | **2,96** | 0,169 (5,6) | 0,086 | 1,81 | 92 % | 19 % |
| gold_silver | **2,59** | 0,097 (5,3) | 0,063 | 1,26 | 72 % | 20 % |
| gold_asb | **2,42** | 0,023 (2,5) | 0,009 | 1,23 | 67 % | 9 % |
| ctnl_reversal (IS) | 2,15 | 0,157 (2,9) | 0,027 | 1,44 | 81 % | 12 % |
| cls_practical | 1,91 | 0,039 (1,3) | 0,002 | 0,81 | 60 % | 1 % |
| orb_sp500 | 1,24 | 0,110 (2,4) | 0,007 | 0,60 | 53 % | 17 % |
| orb_nasdaq | 1,09 | −0,031 (−0,2) | 0,000 | 0,54 | 56 % | ≈0 |
| ou_modell | 0,38 | 0,027 (3,9) | 0,018 | 0,22 | 57 % | 47 % |
| orb_us30 | −0,03 | 0,034 (0,9) | 0,001 | −0,02 | 42 % | — (kein Ertrag) |

## Was das heißt
1. **Kein Bein ist verkapptes Halten des Basiswerts.** R² liegt überall unter 9 %. Das
   passt dazu, dass die Beine intraday handeln oder nur kurz halten.
2. **Eigener Ertrag mit t > 2 nur bei den Gold-Beinen:** trend_pullback, gold_silver,
   gold_asb, dazu CTNL, dort aber nur In-Sample. Das deckt sich mit
   [[gold-asb-is-only-neuanalyse]] und [[mt5-haupt-bot-trend-pullback]].
3. **Die Gold-Beine haben Rückenwind durch Gold:** Das Beta ist signifikant positiv. Bei
   gold_silver und trend_pullback stammen rund 20 % des Ertrags aus dem steigenden Gold
   (2023–2026). In einer Gold-Baisse fällt dieser Teil weg oder dreht ins Minus.
4. **ORB und OU zeigen im OOS + Tresor keinen gesicherten eigenen Ertrag** (t 1,2 / 1,1 /
   0 / 0,4). orb_us30 liegt bei null, passend zur Pause seit 04.10. Bei OU stammt fast die
   Hälfte des kleinen Ertrags aus dem S&P-Beta. Das bestätigt
   [[ou-modell-kostenvalidierung]] und [[orb-neues-regime-2026]].
5. **cls_practical liegt knapp unter der Schwelle** (t 1,91) und verliert in einem Regime
   (Wachstum beschleunigt × Inflation langsamer, Sharpe −1,65). Gemeint ist
   [[cls-practical-kostenvalidierung]].

**Fortsetzung:** Den Skill-Test über ORB und CTNL mit den zwei eingefrorenen Filtern
beschreibt [[skill-test-orb-ctnl]].

## Grenzen
- Der Skill vergibt bei allen Beinen `RESIDUAL_FRAGILE` und `REVIEW_REQUIRED`. Das hat
  zwei technische Gründe, die mit der Edge nichts zu tun haben:
  1. Die Kostenbasis ist bewusst gemischt: Strategie netto, Basiswert brutto.
  2. Der Trendfaktor ist in vielen 63-Tage-Fenstern singulär, weil Gold und die Indizes
     2023–2026 fast durchgehend über ihrer 12-Monats-Rendite lagen. Die rollierenden
     Schätzungen der Trend-Gegenprobe fallen darum aus.

  Aussagekräftig sind die Werte des Hauptmodells.
- Bei trend_pullback und CTNL entfällt die Trend-Gegenprobe, weil der Trendfaktor im
  ganzen Fenster identisch mit dem Basiswert war.
- Es sind simulierte Trades, keine echten Fills. Simulation ist optimistischer als live,
  siehe den Memory-Eintrag „Simulation optimistischer als live“.
- Die Höhe des Alphas hängt von der 1-%-Normierung ab. t-Wert, R² und Status hängen nicht
  davon ab.
