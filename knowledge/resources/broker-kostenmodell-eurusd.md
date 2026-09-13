# Resource: Broker-Kostenmodell EUR/USD (gemessen, je Broker)

Echte, aus den MT5-Terminals gemessene Handelskosten der Broker, auf denen
dieses Projekt live handelt — als Ersatz für die bis dahin unbelegten
Kostenannahmen in den Backtest-Engines. Angelegt 2026-09-09 nach dem
CLS-Vorfall desselben Tages (siehe `CHANGELOG.md`), auf Nutzerauftrag
"validiere das Kostenmodell mit den unterschiedlichen Spreads separat auf
Funded und EK".

Verwandt: [[fx-microstructure]] (Mikrostruktur-Effekte allgemein; hier geht
es um die konkreten Kosten der eigenen Broker, nicht um Paper-Befunde).

Messskript: `scripts/measure_broker_spreads.py` (rein lesend, nutzt
`mt5.copy_ticks_range` / `copy_rates_range` / `history_orders_get` /
`history_deals_get`). Rohdaten: `knowledge/_data/broker_spreads_eurusd.json`.

---

## Warum das nötig war

Das Repo hat **keinen historischen Bid/Ask-Feed**. Dukascopy
(`cls_practical/data.py`) liefert nur OHLC-Mid, der `data_lake` speichert
dasselbe weiter. Alle Kostenparameter der Engines waren deshalb *gesetzte
Annahmen*, keine Messwerte — `cls_practical/engine.py` etwa mit
`spread_bps=0.3` und `slippage_bps=0.0`, während `challenge_portfolio/
paper_bot.py:458` für CTNL `spread_bps=8.0` ansetzt. Die einzige Quelle für
die echten Kosten sind die Broker-Terminals selbst.

---

## Messwerte (2026-09-09, Fenster 08:00–12:30 Berlin, 30 Tage Rückblick)

Messfenster bewusst auf die Handelszeit von `cls_practical` beschränkt
(`test_hour=9.0` bis `entry_cutoff="12:00"`) — ein 24h-Mittel wäre durch
Asien-Session und Rollover verzerrt.

| Broker | Portfolio | Spread (Tick-Median) | Stichprobe | Kommission Round-Trip | Slippage Entry | Slippage Exit | **Gesamt Round-Trip** |
|---|---|---|---|---|---|---|---|
| TTPMarkets-Server | Funded (Challenge) | 0,30 Pips | 346.627 Ticks / 23 Tage | $4,00/Lot = 0,40 Pips | 0,70 Pips | 0,60–0,70 Pips | **~2,05 Pips** |
| BeyondIQCapital-Server | Funded (Challenge) | 0,10 Pips | 250.588 Ticks / 22 Tage | $5,00/Lot = 0,50 Pips | 0,30 Pips | 0,40 Pips | **~1,30 Pips** |
| TickmillEU-Live | EK (echtes Geld) | 0,10 Pips ⚠️ | **nur 15 Ticks im Fenster** | $0,00 über 331 Lots | nicht messbar | nicht messbar | **nicht belastbar** |

### Belastbarkeit — wichtig

- **Spread TTP/IQ: belastbar.** Hunderttausende Ticks über gut drei Wochen.
- **Kommission: belastbar der Größenordnung nach.** TTP $4,00/Lot und IQ
  $5,00/Lot Round-Trip stammen zwar aus je einer Position, sind aber
  Tarifgrößen, keine Marktzufälle. Bei IQ wird die volle Kommission auf der
  **Einstiegsseite** belastet, bei TTP hälftig auf beiden.
- **Slippage: n=1.** Beide Werte stammen aus dem einen realen CLS-Trade vom
  2026-09-09 — und der lief in einen schnellen Move (Position lebte 16
  Sekunden). Die Zahlen sind eher pessimistisch verzerrt. Deshalb ist die
  Kosten-Sensitivität (Sweep) die tragende Aussage, nicht dieser Punktwert.
- **EK/Tickmill: Spread NICHT gemessen.** Die Tickhistorie des Terminals
  deckt 08:00–12:30 mit 15 Ticks praktisch nicht ab; der Median über *alle*
  Tageszeiten liegt bei 0,20 Pips (22.342 Ticks, p90 1,50, max 11,40). Das
  M1-`spread`-Feld füllt Tickmill durchgehend mit 0, dieser Weg ist dort
  versperrt. Der zur Messzeit (22:20 Berlin, nahe Rollover) live abgefragte
  Spread lag bei 1,80 Pips — nicht repräsentativ für die Handelszeit, aber
  ein Hinweis, dass die Spanne bei diesem Broker stark schwankt. **Um EK
  sauber zu beziffern, braucht es Vorwärts-Sampling während der Handelszeit.**

---

## Umrechnung in Engine-Parameter

Bei EUR/USD ≈ 1,164 gilt: **1 Pip ≈ 0,86 bps**.

`cls_practical/engine.py` verrechnet Kosten so (dort verifiziert):

```
entry_price = trigger_level ± half_spread          # half_spread = price * spread_bps / 10_000 / 2
Stop-Exit   = current_sl   ∓ half_spread ∓ slip    # slip = price * slippage_bps / 10_000
TP-Exit     = tp           ∓ half_spread
```

`spread_bps` ist also die **Round-Trip**-Größe (halb beim Ein-, halb beim
Ausstieg), `slippage_bps` kommt **nur beim Stop-Exit** dazu.

Für Live-Vergleiche gehören alle Kostenblöcke in `spread_bps`: der Live-Bot
setzt **keinen Broker-TP** (`target=None` in
`Funded-Portfolio-Bridge/run_once.py`), jeder Ausstieg ist eine Marktorder
und slippt real — Kosten auf *alle* Ausstiege zu legen ist näher an der
Realität als "nur auf Stops".

---

## Übertragbarkeit

Gilt so nur für **EUR/USD**. Andere Symbole derselben Broker (XAUUSD,
Indizes, Einzelaktien) haben eigene Spreads und eigene Kommissionsmodelle
und sind hier **nicht** gemessen — `scripts/measure_broker_spreads.py`
nimmt das Symbol aber als Parameter, die Messung ist also wiederholbar.

Offen: dieselbe Messung für die übrigen Beine (`gold_asb`,
`ctnl_continuation`, `orb_*`, `ou_modell`), deren Engines ebenfalls mit
gesetzten statt gemessenen Kosten rechnen.
