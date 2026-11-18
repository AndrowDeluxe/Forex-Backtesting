---
title: ORB NASDAQ — SL an der 15:30-Kerze + Market-Einstieg mit Versatz
datum: 2026-11-18
status: Research, Tresor zu, nicht live
lock: nasdaq_orb_kerzen_sl_20261118
---

# ORB NASDAQ: SL an der 15:30-Kerze + Market-Einstieg mit Versatz

Nutzerauftrag vom 18.11.2026. Anlass waren drei verpasste Short-Tage (13., 16. und 17.11.), die im Chart je ~3R gebracht hätten.
Skript: `scripts/research_orb_nasdaq_kerzen_sl_market.py`. Ergebnisse liegen in `ny_open_orb/results/kerzen_sl_market/`
(`grid.csv`, `status.csv`, `jahre.csv`).

## Warum live nicht gehandelt wurde (Bridge-Logs)

- **13.11.:** Der Kurs war schon unter dem Range-Tief, bevor die Order lag (`breakout_passed`). Seit dem Präzise-Pass (16.09.) ist das an
  ~5–6 von ~25 Tagen passiert.
- **16.11.:** Zuerst kam der Fehlausbruch long (−1R). Die Short-Seite war durch OCO und Storno schon weg.
- **17.11.:** Die Range war breit und der Kurs stand in der Mitte. Damit waren beide geplanten 0,6-ATR-SLs schon berührt, und das Storno
  löschte beide Orders.

## Aufbau

NASDAQ M1, 07/2016 bis 17.05.2026, live-Regeln: beide Richtungen, OCO, ohne Mittwoch, Ausstieg 16:00, Kosten wie alle ORB-Läufe.
Gitter mit 48 Varianten, alle gezählt:

- **SL:** 0,6 ATR (live) oder Hoch/Tief der 15:30-Kerze
- **Storno:** an oder aus
- **Einstieg:**
  - `ideal` = bisheriger Backtest
  - `live` = Order erst nach der 09:45-Minute; ein Ausbruch in dieser Minute ist verpasst
  - `mX` = Market-Einstieg, wenn der Kurs am Ende der 09:45-Minute ≤ X·ATR hinter dem Level steht
- **Ziel:** 16:00 oder 3R

Die `live`-Variante ist eine strenge Untergrenze: Auf M1 ist die ganze erste Minute „blind“, live sind es nur ~3–40 s. Der Market-Kurs ist
der Schluss dieser Minute (konservativ).

## Ergebnis (Ø R je Trade, IS 2016–22 / OOS 2023–05/2026)

| Variante | IS Ø R (t) | OOS Ø R (t) | Trades/J. | MaxDD OOS | Ø R pessimistisch IS |
|---|---|---|---|---|---|
| 0,6 ATR + Storno, ideal (= bisheriger Backtest) | 0,239 (1,3) | 0,152 (0,6) | 70–78 | −48 R | −0,007 |
| 0,6 ATR + Storno, live (Ausbruch 1. Minute verpasst) | 0,019 | −0,110 | 5–7 | — | — |
| 0,6 ATR + Storno, Market ohne Grenze | 0,326 (1,6) | 0,039 (0,2) | 42–51 | −38 R | 0,326 |
| **Kerze-SL, Market ohne Grenze, 16:00** | **0,077 (1,9)** | **0,082 (1,4)** | ~200 | −16 R | 0,077 |
| **Kerze-SL, Market ohne Grenze, 3R** | **0,082 (2,2)** | **0,090 (1,7)** | ~200 | −16 R | 0,082 |
| Kerze-SL, live (1. Minute verpasst), 16:00 | 0,044 (0,9) | 0,052 (0,7) | ~138 | −18 R | 0,044 |
| Kerze-SL, ideal, 3R | 0,088 (2,3) | 0,094 (1,8) | ~205 | −15 R | 0,088 |

## Befunde

1. **Die live-NASDAQ-Regel (0,6 ATR + Storno) handelt praktisch nur Ausbrüche in der ersten Minute nach 09:45 NY.** Von 702 Backtest-Trades
   füllen 655 in der 09:45-Minute. An allen anderen Tagen streicht das Storno beide Seiten, bevor ein Ausbruch kommt. Genau diese
   Minute verpasst die Bridge teilweise (Platzierung 09:45:03 + Polling). Ein großer Teil des Backtest-Edges ist deshalb live nicht
   erreichbar.
2. **Der 0,6-ATR-Edge hängt an der Füll-Minute.** Wird jeder SL-Touch in der Füll-Bar als Stop gewertet, liegt er bei ~0. Market-
   Einstiege haben diese Mehrdeutigkeit nicht und sind im IS stark (0,33). Im OOS fällt das auf 0,04.
3. **Kerze-SL: kleiner Edge je Trade, aber stabil und ehrlich gemessen.** Es gibt keine Füll-Bar-Mehrdeutigkeit (pessimistisch =
   normal). IS und OOS sind gleich groß, auch mit doppelten Kosten positiv (~0,05). Der MaxDD in R ist ein Drittel. 2026 bis Mai liegt
   bei ~−1 bis −3 R. Das Storno ist beim Kerze-SL wirkungslos: Der SL ist das andere Range-Ende, dort löst ohnehin die Gegenseite aus.
4. **Market mit Versatz ist beim Kerze-SL nötig.** Ohne Market bricht der Edge auf ~0,05 ein, weil die Ausbrüche der ersten Minute
   die besten sind. Ein enger Versatz (0,05–0,2 ATR) bringt kaum mehr als „ohne Grenze“.
5. **3R oder 16:00** liegen fast gleichauf, 3R leicht vorn.
6. **Einschränkung:** Deflated Sharpe IS 0,47–0,55 bei 48 Versuchen, also nicht signifikant. t im OOS ~1,4–1,8. Das ist ein Kandidat,
   kein Beweis. Der Tresor (18.05.–17.11.2026) ist noch zu.

## Tresor (18.05.–17.11.2026): durchgefallen

Nutzerfreigabe 18.11. Eingefroren wurde: Kerze-SL, Market ohne Grenze, Storno an, 3R (Hash `859efcbabb14…`).
Skript `scripts/research_orb_nasdaq_kerzen_sl_tresor.py`, Ergebnis `ny_open_orb/results/kerzen_sl_market/tresor.csv`. Der erste Lauf
brach nach `unseal()` ab, bevor ein Ergebnis ausgegeben wurde (leere Kontext-Variante). Danach wurde dieselbe Konfiguration erneut
ausgelesen.

| | n | Ø R | t | Σ R | PF | MaxDD |
|---|---|---|---|---|---|---|
| **Kandidat (3R)** | 102 | **−0,163** | −1,5 | −16,6 | 0,69 | −22 R |
| Kontext: Kandidat mit Ausstieg 16:00 | 102 | −0,186 | −1,8 | −19,0 | 0,65 | −22 R |
| Kontext: live-Regel, Backtest ideal | 46 | +1,318 | 1,5 | +60,6 | 2,56 | −13 R |
| Kontext: live-Regel, 1. Minute verpasst | 0 | — | — | — | — | — |

- Der Kandidat verliert in 5 von 7 Monaten. Die drei Anlass-Tage gewinnt er (13.11. +0,77, 16.11. +0,80, 17.11. +2,99 R). Das sind
  am Chart ausgesuchte Tage, eine typische Auswahlverzerrung.
- Kontext, kein gültiger Test (die live-Regel wurde am 04.10. mit Blick auf 2026 gewählt): Ihr ganzer Tresor-Gewinn stammt aus
  Ausbrüchen der ersten Minute. Mit „erste Minute verpasst“ bleibt kein einziger Trade.
- **Urteil: Kerze-SL wird nicht live geschaltet.** Dieser Lock ist verbraucht. Nachbesserungen am Kerze-SL sind auf diesen Daten
  nicht mehr prüfbar, nur noch vorwärts.

## Soll/Ist: Erste-Minute-Ausbrüche 05.10.–17.11. (TTP, Funded-Bridge)

Backtest der live-Regel auf Dukascopy-M1 je Tag, abgeglichen mit den TTP-Logs. Die Tabelle liegt im Scratchpad dieser Session, Skript
siehe CHANGELOG. 24 Handelstage ohne Mittwoch. Davon hatten 11 im Backtest einen Trade, alle in der 09:45-Minute. Zusammen bringen sie
Σ ≈ +13,5 R: 9× −1 R, dazu 05.11. +16,6 R und 09.11. +6,3 R. Die Range war an allen 24 Tagen 1,9–5,6 ATR breit, sonst gab es keinen
Trade (Storno).

| Ergebnis | Tage | Backtest-R |
|---|---|---|
| Bridge getroffen, gleiche Richtung | 10-05, 10-09, 10-22, **11-05**, 11-06 | ≈ +12,4 |
| Verpasst, Ausbruch vor der Platzierung (`breakout_passed`; 11-09 Order abgelehnt „Invalid price“) | 10-23, 11-03, **11-09**, 11-13 | ≈ +3,2 |
| Verpasst, Bridge lief nicht | 10-15, 10-20 | ≈ −2,1 |
| Bridge-Trade ohne Gegenstück im Backtest (Feed-Unterschied am Range-Hoch) | 11-16 | live −1 R |

Die Bridge trifft also ~5 von 9 Ausbrüchen, wenn sie läuft. Der netto verpasste Wert ist mit +3,2 R klein und hängt an einem Tag (09.11.).
Den großen Gewinner (05.11.) hat sie getroffen. Die Stichprobe ist zu klein für eine Aussage über den Wert eines Market-Einstiegs.

## Kontrolle: live-Regel mit Market-Einstieg (18.11., nur Überprüfung)

Skript `scripts/research_orb_nasdaq_market_einstieg_check.py`, Ergebnis `market_einstieg_check.csv`. Die live-Regel ist
0,6 ATR + Storno + Ausstieg 16:00. Für sie sind Tresor und Herbst 2026 nicht unberührt (Wahl am 04.10.). Σ R je Periode:

| Einstieg | IS 16–22 | OOS 23–05/26 | Tresor 05–11/26 | 05.10.–17.11. |
|---|---|---|---|---|
| ideal (bisheriger Backtest) | +105 (0,24) | +40 (0,15) | +61 (1,32) | +13,5 (11 Tr.) |
| live, erste Minute verpasst | +0,5 | −2,3 | 0 Trades | 0 Trades |
| Market ≤ 0,1 ATR | +40 | −14 | +11 | +20,8 (4 Tr.) |
| **Market ohne Grenze** | **+88 (0,33)** | **+7 (0,04)** | **+36 (1,33)** | **+19,8 (5 Tr.)** |

- **Market statt Überspringen:** Auf Tagen, an denen der Ausbruch vor der Order kam, ist Market ohne Grenze in allen vier Perioden
  besser als Überspringen. Die Erste-Minute-Market-Trades bringen IS +88, OOS +9, Tresor +36 R.
- **Grenze:** Ein enger Versatz (≤ 0,05–0,2 ATR) ist im OOS negativ. Gerade die weiten Ausbrüche tragen.
- **Gesamtbild:** Der Edge der ganzen Regel ist dünn und hängt an wenigen großen Tagen. 2024 hat −12 R, OOS t 0,2.
- **Modell:** Market-Kurs = Schluss der 09:45-Minute. Live liegt die Order nach ~3 s und füllt viele Tage direkt per Stop. Die
  Wirklichkeit liegt zwischen „ideal“ und „Market ohne Grenze“.

## Umsetzung (18.11., Nutzerentscheid)

Market-Rückfall ohne Grenze ist live auf Funded, FK und EK, nur für NASDAQ. Bedingungen: genau eine Seite gebrochen, ihr geplanter SL
unberührt, ≤ 120 s nach Range-Ende. Sonst wird wie bisher übersprungen, und liegt der Kurs zurück in der Range, gelten die normalen
Stop-Orders. Details stehen im CHANGELOG vom 18.11.

## Offen

- Den ersten echten Market-Rückfall prüfen: Fill, SL, Lots (Ideen-Inbox).

Verwandt: [[orb-order-storno-und-haltedauer]], [[nasdaq-orb-vorboersen-range]], [[ny-open-orb-sp500]].
