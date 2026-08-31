# Monthly Checkup - Performance - August 2026

**Zeitraum:** 2026-08-01 bis 2026-08-31.

> **Hinweis zur Ausführung**: Dieser Monatsreport wird zusammen mit dem
> KW35-Wochenreport erzeugt, da Sonntag 2026-08-30 der letzte Sonntag im
> August war (siehe `weekly_report_prompt.md`-Trigger). Die August-
> Wochenreports existieren nur für KW34 und KW35 (die Weekly-Checkup-
> Automation lief erstmals am 2026-08-27) - für 2026-08-01 bis 08-16
> (KW31-KW33) gibt es keine vorab geschriebenen Wochenreports; dieser
> Abschnitt stützt sich dafür direkt auf `git log` und einen frischen
> Monats-Datenabzug per `mt5.history_deals_get()`, nicht auf
> aufsummierte Wochenzahlen (wie im Prompt gefordert).

## 1. Wochenkontext (Monatsbogen)

August 2026 zerfällt klar in zwei Phasen:

- **01.-16.08. (vor jedem Live-Gang)**: reine Strategie-Entwicklung und
  -Validierung im Repo - Gold Asian-Range Breakout, OU-Modell, Trend
  Pullback, CLS Practical und BTC EMA9/21 wurden nacheinander gebaut,
  gebacktestet und (teils mehrfach) mit Out-of-Sample-Tests und Monte-
  Carlo-Robustheit geprüft. Am 10.08. wurde das "Second-Brain"-Prinzip
  (`knowledge/`-Ordner, PARA+CODE) eingeführt - die Grundlage, auf der
  auch dieser Report aufbaut.
- **17.-31.08. (Live-Gänge und Konsolidierung)**: CTNL Edge ging am 20.-21.
  live, Gold ASB und BTC EMA Cross ca. 20.08., OU-Modell lief bereits
  vorher (siehe unten). Ab 27.08. begann die Konsolidierung auf ein
  gemeinsames Portfolio (`EK-Portfolio-Bridge`, 8 Beine), die am 29.08. mit
  echtem Geld live ging. Details in `KW34_2026_performance.md` und
  `KW35_2026_performance.md`.

**Live-Start-Daten (bestätigt über Log-/Config-Historie):**

| Bot | Live seit | Konto(en) |
|---|---|---|
| OU-Modell | vor August (Logs ab mind. 31.07.) | Konto1 (TTP), Konto2 (TTP Demo), Konto3/Tickmill (bis 27.08.) |
| Gold ASB | ca. 20.08. | 15514 (geteilt mit BTC EMA) |
| BTC EMA Cross | 20.08. | 15514 (geteilt), deaktiviert 31.08. |
| CTNL Edge FK (alte Bridge) | 20.-21.08. | 16054, deaktiviert 28.08. |
| CLS Practical | weiterhin DRY_RUN (Papier) | 5053949028 |
| EK-Portfolio-Bridge | 29.08. | 55918977 (Tickmill, übernommenes OU-Modell-Konto3) |
| FKInstantFunding-MT5-Bridge | weiterhin DRY_RUN (Papier) | - |
| Funded-Portfolio-Bridge | weiterhin DRY_RUN (Papier) | 16054, 504072729 (geteilt mit CTNL/OU-Modell) |

## 2. Risk-Management-Compliance

**Kein bestätigter Drawdown-/Kill-Switch-Trigger auf einem echten Konto im
gesamten August.** Die strukturellen Lücken sind über den ganzen Monat
unverändert geblieben: Gold ASB und die alte CTNL-Edge-MT5-Bridge hatten
zu keinem Zeitpunkt einen eigenen Drawdown-Deckel im Bridge-Code (nur
Einzeltrade-Risiko), während BTC EMA/CLS/OU-Modell durchgehend
`check_daily_drawdown()` je Konto verdrahtet hatten und dieser nie
auslöste. Der einzige Kill-Switch-Trigger im ganzen Monat war ein
**Fehlalarm in der Papier-Diagnose von FK Instant Funding** (26.08., durch
einen Kontostart-Gating-Bug, noch am selben Tag behoben) - kein echtes
Kapital betroffen.

Der wiederkehrende Gold-ASB-AutoTrading-Bug (`retcode=10027`) trat im
August **mindestens fünfmal** auf (20.08., 26.08., 27.08., plus zwei
weitere laut `windows`-Tabelle referenzierte Vorfälle) und blieb den
gesamten Monat unbehoben - das durchgängigste offene Risiko-Thema dieses
Reports.

## 3. Was hat gut / nicht gut funktioniert (Monatstrend pro Bot)

- **OU-Modell Konto1 (TTP, real)**: 27 Trades im Monat, 33% Winrate,
  **-$2.713,44**. Trend: starke erste Woche (KW32 +$916,69), dann eine
  sehr schlechte Woche (KW33 -$2.483,43, praktisch der gesamte
  Monatsverlust), danach **sich verbessernd** (KW34 -$863,42, KW35
  -$283,28 - die Verluste schrumpfen von Woche zu Woche). Zu früh, um von
  einer echten Trendwende zu sprechen, aber die Richtung stimmt.
- **OU-Modell Konto2 (TTP, Demo)**: 19 Trades, 42% Winrate, **+$290,44** -
  positiv für den Monat trotz einer neutralen KW33. Als Demo-Konto ohne
  reales Kapital, aber strukturell dieselbe Strategie wie Konto1 - der
  Unterschied zu Konto1s Monatsverlust ist auffällig und nicht durch
  öffentlich bekannte Parameterunterschiede erklärt; wert, einmal
  gegenzuprüfen, ob die beiden Konten wirklich identisch konfiguriert sind.
- **OU-Modell Konto3 / EK-Portfolio-Tickmill (55918977)**: 20 Trades, netto
  praktisch **flach (+€1,71)** für den Monat - bemerkenswert stabil für
  ein kleines (~€3,4k) Konto, das die ersten vier Wochen unter alter
  OU-Modell-Logik lief und erst am Monatsende unter neuer EK-Portfolio-
  Logik. Trend: früh positiv (KW32 +€169,25), dann leicht negativ
  (KW33/KW34/KW35), am Monatsende praktisch ausgeglichen.
- **Gold ASB / BTC EMA (geteiltes Konto 15514)**: 4 Trades im Monat, **alle
  vier Verluste**, netto **-$1.234,84** (siehe Hinweis unten zur
  Kommission). Drei dieser vier Trades sind der bereits in KW34
  dokumentierte, nicht zuordenbare EURUSD-Trade (19.08., -$920 inkl.
  Kommission) plus zwei weitere frühe Verluste (KW33). **Weder Gold ASB
  noch BTC EMA haben laut eigener State-Datenbank auch nur einen einzigen
  dieser vier Trades selbst ausgelöst** - der reale Monatsverlust auf
  diesem Konto stammt vollständig aus nicht zuordenbaren/externen
  Vorgängen, während beide Bots operativ 0 eigene Fills produzierten
  (durch fehlende Signale und den wiederholten AutoTrading-Bug).
- **CTNL Edge FK**: **0 Trades im gesamten August** - Kontostand exakt
  $100.000,00 seit Live-Gang. Die Strategie hat im gehandelten Zeitraum
  bislang schlicht nie ausgelöst; kein Datenproblem (siehe KW35-Report,
  Punkt 6).
- **CLS Practical (Demo)**: nur 1 Trade im ganzen Monat (06.08.,
  **-€2.406,30**) - fällt zeitlich vor die Phase, in der die aktuelle
  `DRY_RUN=True`-Bridge nachweislich lief; vermutlich ein manueller
  Test-Trade auf dem Demo-Konto, nicht die Bot-Logik. Kein reales Kapital
  betroffen, Ursache nicht abschließend verifizierbar.
- **EK-Portfolio-Bridge (eigene neue Logik)**: erst seit 31.08. mit
  eigenen echten Trades aktiv (1 Position, D/OU-Modell-Bein) - zu neu für
  eine Monatsbewertung.
- **FK Instant Funding, Funded-Portfolio-Bridge**: den ganzen Monat
  `DRY_RUN=True`, kein echtes Kapital betroffen.

## 4. Trades, Winrate, Gewinn ($/%) - Summary (frischer Monatsabzug)

Quelle: `mt5.history_deals_get()` direkt vom jeweiligen Broker (read-only)
für 2026-08-01 00:00 bis 2026-09-01 00:00 - **nicht** aus den Wochenzahlen
aufsummiert (frischer Abzug, wie gefordert). Nur geschlossene Trades.

| Bot / Konto | Währung | Trades (Monat) | Winrate | PnL (Monat) | PnL (%, approx.) |
|---|---|---|---|---|---|
| Gold ASB + BTC EMA FK (15514) | USD | 4 | 0% (0/4) | **-$1.234,84** (s. Hinweis) | ≈ -1,24% |
| CTNL Edge FK (16054) | USD | 0 | - | $0,00 | 0,00% |
| CLS Practical Challenge (5053949028) | EUR | 1 | 0% (0/1) | **-€2.406,30** (s. Hinweis) | ≈ -2,41% |
| OU-Modell Konto1 (TTP) | USD | 27 | 33% (9/18) | **-$2.713,44** | ≈ -2,72% |
| OU-Modell Konto2 (TTP, Demo) | USD | 19 | 42% (8/11) | **+$290,44** | ≈ +0,29% |
| OU-Modell Konto3 / EK-Portfolio (55918977) | EUR | 20 | ≈35% (7/13) | **+€1,71** | ≈ 0,00% |
| **Summe USD (real, ohne Demo-Konto2)** | USD | 31 | 29% (9/22) | **-$3.948,28** | - |
| **Summe USD inkl. Demo-Konto2** | USD | 50 | 34% (17/33) | **-$3.657,84** | - |
| **Summe EUR (real)** | EUR | 21 | 33% (7/14) | **-€2.404,59** | - |
| FKInstantFunding-MT5-Bridge / Funded-Portfolio-Bridge | - | 0 | - | $0 (DRY_RUN) | 0,00% |

Hinweise zur Tabelle:
- Der Gold-ASB/BTC-Betrag (-$1.234,84) zählt nur die "Close"-Deals; der in
  KW34 präzise aufgeschlüsselte EURUSD-Trade hatte zusätzlich eine
  **separate -$40 Kommission auf der Open-Seite**, die diese Deal-Ebene-
  Summe nicht automatisch erfasst - der tatsächliche Monatsverlust auf
  diesem Konto liegt daher eher bei **≈ -$1.275**.
- CLS Practicals -€2.406,30 ist ein einzelner, zeitlich isolierter Trade
  auf einem Demo-Konto, mit unklarer Herkunft (siehe Abschnitt 3) - hier
  aus Vollständigkeit mitgezählt, aber nicht als Bot-Performance zu
  interpretieren.
- CLS EK und BTC EK (beide MT4/Axi, dateibasiert) sind weiterhin nicht per
  `MetaTrader5`-Python-Paket verifizierbar und fehlen daher in dieser
  Tabelle - unverändert seit KW34.

## 5. Portfolio vs. Einzelkonten - Referenzpunkt

Ein echter Live-Vergleich (konsolidiertes Portfolio vs. dieselbe
Kapitalbasis auf Einzelkonten) ist für August **noch nicht möglich**:
`EK-Portfolio-Bridge` hat erst am 31.08. ihren ersten eigenen Trade
platziert, und `FKInstantFunding-MT5-Bridge` (die andere Portfolio-
Kandidatin) ist weiterhin `DRY_RUN=True`. Als **Referenzpunkt** dient der
bereits vorhandene Backtest-Vergleich aus
`portfolio_construction/results/fk_instant_funding_final.json`
(gemeinsames Fenster 2024-08-01 bis 2026-07-29, 728 Tage):

| | CAGR | Sharpe | Max DD | Calmar |
|---|---|---|---|---|
| **6-Strategien-Portfolio** | 24,81% | 2,718 | **-2,27%** | 10,943 |
| Gold ASB (einzeln) | 12,85% | 1,135 | -8,31% | - |
| CLS Practical (einzeln) | 20,33% | 1,787 | -5,70% | - |
| Trend Pullback (einzeln) | 9,83% | 1,185 | -4,80% | - |
| CTNL Edge (Gold SMC, einzeln) | 21,69% | 1,822 | -7,95% | - |
| Gold-Silber-Divergenz (einzeln) | 11,67% | 1,373 | -6,59% | - |
| NY-Open ORB Portfolio (einzeln) | 34,72% | 1,664 | -9,26% | - |

Der Backtest zeigt eine deutlich geringere Max-Drawdown (-2,27% vs. -4,8%
bis -9,26% je Einzelstrategie) bei höherem risikoadjustiertem Ertrag
(Sharpe 2,718 vs. 1,135-1,822) - die Kernthese hinter der Konsolidierung.
Ob sich das real bestätigt, lässt sich erst nach mehreren echten Monaten
mit `EK-Portfolio-Bridge` beurteilen, nicht schon jetzt.

## 6. Auffälligkeiten / offene Punkte (Monatsrollup)

Die folgenden Punkte sind über mehrere Wochenreports hinweg unverändert
offen geblieben - siehe die jeweiligen Wochenreports für Details, hier nur
als Monatsübersicht:

1. **Nicht zuordenbarer EURUSD-Trade (19.08.) und die daraus resultierende
   USDJPY-Restposition auf Konto 15514** - seit drei Wochen offen, floating
   jetzt -$199,97.
2. **Gold-ASB-AutoTrading-Bug** - mindestens 5 Wiederholungen im August,
   nie behoben.
3. **TrendPullback FK1/FK2** - seit 19./22.08. tot, inzwischen fachlich
   redundant durch `EK-Portfolio-Bridge`.
4. **CTNL Edge FK: zwei neue unbehandelte Dukascopy-Exceptions** (27./28.08.,
   siehe KW35-Report), unmittelbar vor der Konsolidierungs-Pause.
5. **BTC-EMA-Cross-Bridge und CTNL-Edge-FK-Paper am 31.08. ohne
   dokumentierte Begründung deaktiviert** - siehe KW35-Report Punkt 1,
   Klärung steht aus.
6. **OU-Modell-MT5-Bridge war bis KW34 in keiner Bridge-Liste dokumentiert**
   - seit KW34 fester Bestandteil jedes Checkups (dieser Report
   eingeschlossen).
