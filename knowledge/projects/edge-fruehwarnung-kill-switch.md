# Frühwarnung + Kill-Switch für kippende Edges

**Status: Research abgeschlossen 14.10.2026, Ampel im Weekly Report. Keine Bot-Änderung.**
Nutzerfrage 14.10.: „Wie können wir im Vorhinein feststellen, ab wann der Edge kippt?“
Entscheide: ORB + weitere bekannte Brüche, erst Research + Report, Aktion
Pause + Schattenkonto. Verwandt: [[live-strategien-tresor-check]], [[orb-gegenprobe-oel]],
[[overfitting-sperre]]; Vorbild CTNL-Schalter (`gold_smc_htf_ltf/ctnl_kill_switch.py`).

## Aufbau

- Paket `edge_monitor/` (signals, calibrate, switch, cases), Skript
  `scripts/research_edge_monitor.py` (calibrate / evaluate / status), Tests
  `tests/test_edge_monitor.py` (6 grün: kein Lookahead, Hysterese, CUSUM/SPRT-Werte, Budget).
- Lock `edge_monitor_20261014`: 13 vorab feste Regeln, eingefroren, einmal bewertet.
- **17 Fälle:** 7 Brüche (ORB IS-only SP500/NASDAQ, Zarattini SP500/NASDAQ,
  EU-Open SP500/US30/NASDAQ) + 10 Live-Beine (Tickmill-Liste 04.10.; Nasdaq dort
  noch ohne Storno).
- **Kalibrierung ohne Blick auf den Bruch:** Schwellen nur aus dem Fenster vor dem
  Bruch (ORB/Zarattini IS bis 2022, Live-Beine 2019–2022, EU-Open bis 2020),
  Bootstrap unter „Edge intakt“, Fehlalarm-Budget streng = 1 je 5 Jahre,
  locker = 1 je 2 Jahre. Freigabe auf halbem Weg zurück (Hysterese).
- Schalter: Signal rot → Pause; die Strategie läuft auf dem Schattenkonto weiter
  und kann den Schalter wieder öffnen. Nur zum Einstieg geschlossene Trades zählen.

## Signale

| Signal | misst |
|---|---|
| roll_mean | Ø der letzten 30 Trades unter dem Normalwert (in Standardfehlern) |
| cusum | aufsummierte Unterschreitung des Normalwerts (Page-CUSUM) |
| sprt | Wald-Test „Edge = 0“ gegen „Edge wie früher“ |
| bayes | P(Edge < 0) aus den letzten 60 Trades + Prior |
| drawdown | aktueller Drawdown vom Hoch |
| ribbon_spread (nur ORB) | Ø Trend-Tage minus Ø neutrale Tage (Schatten), letzte 40 |

## Ergebnis (Zeit nach dem Kalibrierfenster)

Δ = Σ mit Schalter − Σ ohne (ORB/Live in R, Zarattini/EU-Open in bps je Trade summiert).

| Regel | Brüche besser | Live-Beine: Kosten | Verzug nach dem letzten Hoch (Median) |
|---|---|---|---|
| **drawdown streng** | **7 von 7** (ORB SP +32, NQ +9 R) | klein (Median −3,4 R, schlimmster −23 R) | ~6 Monate |
| cusum / sprt streng | 6 von 7 | groß (orb_nasdaq −157 R, orb_sp500 −32 R) | ~4 Monate |
| ribbon_spread streng (ORB) | 2 von 2 (SP +32, NQ +1 R) | – | 6–10 Monate |
| 2 von 5 locker | 5 von 7 | sehr groß (Pause 50 % der Zeit) | ~3 Monate |
| roll_mean / bayes | kaum Wirkung | mittel | – |

1. **Verlässlich vorher erkennen geht nicht.** Wo ein Schalter schon vor dem letzten
   Equity-Hoch aus war, hat er dort Gewinne gekostet (z. B. ORB NASDAQ CUSUM −52 R vor
   dem Hoch). Der beste Schalter greift im Median ~6 Monate nach dem Hoch. Er begrenzt den Schaden, er
   sagt den Kipp nicht voraus. Auch das Mechanismus-Signal (Ribbon-Spread) war nicht
   früher.
2. **Bester Kompromiss: Drawdown-Schalter, streng kalibriert.** Hilft in allen 7 Brüchen
   und kostet die gesunden Live-Beine wenig. Genau die Form des CTNL-Schalters, aber
   je Strategie per Bootstrap kalibriert statt fester −6,6 %.
3. **Sequenzielle Tests (CUSUM/SPRT) reagieren schneller, schlagen aber bei
   Strategien mit seltenen großen Gewinnern (ORB, Trefferquote 11–25 %) zu oft an.**
4. **„2 von 5“ ist zu nervös:** halbe Zeit in Pause, kostet die Live-Beine viel.

## Ampel 14.10. (`--stage status`, Trade-Listen Stand 01.10.)

| Bein | drawdown | übrige | Lesart |
|---|---|---|---|
| orb_sp500 | **rot** | alle rot | Schalter wäre aus. Live, echtes Geld → Dashboard 🔍 |
| orb_us30 | **rot** | alle rot | bereits pausiert (04.10.) |
| btc_ema_cross | gelb | 3 rot | nur 29 Trades seit 2023 |
| gold_asb | grün | 2 gelb | beobachten |
| orb_nasdaq | grün | cusum/sprt rot | alte Version ohne Storno in der Liste |
| übrige | grün | | |

## Offen

- Ampel braucht frische Trade-Listen (`python scripts/research_live_legs.py tickmill --refresh`),
  sonst ist sie so alt wie die Liste.
- Bridge-Verdrahtung des Drawdown-Schalters nur nach eigener Freigabe (echtes Geld).
