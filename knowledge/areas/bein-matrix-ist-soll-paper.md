# Bein-Matrix: Soll / Ist / Paper-Bot

**Stand: 2026-09-13** · **Typ:** Area (bei jeder Bein-Freischaltung mitpflegen)

Die Schwester-Seite zu [[bridge-infrastruktur-vergleich]]: dort geht es um die
**Infrastruktur** der drei Bridges, hier um die **einzelnen Beine** — was jedes
Bein laut Config tun SOLL, was es seit Livegang tatsächlich GETAN hat, und ob
es überhaupt einen laufenden Paper-Bot als Vergleichsmaßstab gibt.

Quelle der Ist-Spalten: `bridge_state_*.json` (Funded/FK),
`state/ek_portfolio_55918977.sqlite3` + `logs/run_*.log` (EK), ausgewertet am
2026-09-13. **Nicht geschätzt — gezählt.**

---

## Die Kernaussage in drei Zahlen

| | Signale gesehen | Echte Orders | Quote |
|---|---|---|---|
| **EK-Portfolio-Bridge** (seit 08-29) | — (kein Signalzähler) | **20** (ORB 9, OU 9, CTNL 2) | 4 von 11 Bein-Keys haben je gehandelt |
| **Funded-Portfolio-Bridge** (seit 09-01, 3 Konten) | 80 | **16** | **20 %** |
| **FKInstantFunding** (seit 09-08 live) | 9 | **0** | **0 %** |

Die Bridges laufen, verbinden sich, scannen und protokollieren sauber. Der
Engpass sitzt **nicht** in der Strategie und **nicht** in der Verbindung,
sondern zwischen „Signal erkannt" und „Order liegt beim Broker".

---

## EK-Portfolio-Bridge — Tickmill 55918977, echtes Geld

Equity 2026-09-11 EOD: **3.354,39** (Baseline 09-07: 3.460,62 → −3,1 % in der
Woche, aus vorher eröffneten OU-Positionen, nicht aus neuen Entries).

| Bein | Soll: Risiko/Trade¹ | Ist seit 2026-08-29 | Paper-Bot |
|---|---|---|---|
| `gold_asb` | 2,93 % | **0 Orders** · 12 Scan-Fehler, 4× `risk_cap` | ⛔ Task Disabled seit 08-31 |
| `trend_pullback` | 1,83 % | **0 Orders** · kein Signal beobachtet | ⛔ |
| `btc_ema_cross` | 2,93 % | **0 Orders** · BTC-Bridge aufgelöst | ⛔ |
| `gold_silver` | 2,93 % | **0 Orders** · kein Signal beobachtet | ⛔ |
| `cls_practical` | 0,55 % | **0 Orders** · 1× durch `risk_cap` blockiert (09-09), **104 Scan-Fehler** | ⛔ |
| `ctnl_continuation` | 0,063 % | **2 Orders** (09-08, 09-09) · Exit-Order 16× fehlgeschlagen | ⛔ |
| `ctnl_reversal` | 0,019 % | **0 Orders** · 7 Scan-Fehler | ⛔ |
| `ou_modell` | 0,37 % | **9 Orders** (D, FAST, SPG, SYY, AXP, ADI, EXPE, APD, AMGN) | ⛔ |
| `orb_sp500` | 0,042 % | **3 Orders** (09-01, 09-10, 09-11) · 7× `Invalid stops` am 09-01 | ⛔ |
| `orb_us30` | 0,042 % | **0 Orders** · 213× `risk_cap`, 8× `Invalid stops` | ⛔ |
| `orb_nasdaq` | 0,042 % | **6 Orders** | ⛔ |

¹ `CAPITAL_WEIGHT (1/8) × LEG_RISK_PCT`, Kalibrierung vom 2026-09-10.

**Drei Befunde, die nur auf Bein-Ebene sichtbar werden:**

1. **`cls_practical` ist auf EK faktisch tot** — 104 Scan-Fehler zwischen
   08-31 und 09-11, alle mit derselben Ursache: Lake-Eintrag gilt als
   veraltet → Fallback auf Live-Dukascopy → Hang → 90-s-Timeout → Bein fällt
   aus. Das Bein hat auf EK noch nie eine Order gesendet.
2. **`orb_us30` wurde 213× vom aggregierten Risikodeckel weggeworfen** — der
   Deckel stand bis 09-10 auf 8 % und das Konto klebte dauerhaft daran. Seit
   der Anhebung auf 30 % (09-10) **kein einziger `risk_cap`-Skip mehr**
   (letzter: 09-09). Der Fix wirkt; das Bein hatte seitdem schlicht kein
   Signal.
3. **`ou_modell` sendet Orders, obwohl die Config das Gegenteil behauptet.**
   `config.py` begründet `CAPITAL_WEIGHT = 1/8` mit „OU-Modell zählt mit
   (eigenes echtes Konto, **keine Order hier**)" — die Logs zeigen 9 gesendete
   OU-Orders von genau dieser Bridge. Die alte `OU-Modell-MT5-Bridge` ist
   deaktiviert, EK hat das Bein übernommen; der Kommentar wurde nie
   nachgezogen. **Risiko-relevant**, weil er die Herleitung der Kapitalscheibe
   trägt.

## Funded-Portfolio-Bridge — TTP ×2 + IQ Markets, echtes Geld

Gelesen als „platzierte Orders / gesehene Signale".

| Bein | Soll: Risiko/Trade² | TTP (K2) | TTP1 (K1) | IQ Markets | Paper-Bot |
|---|---|---|---|---|---|
| `gold_asb` | 0,33 % | 1/1 ✅ | — (Konto später dazu) | 1/1 ✅ | ⛔ nie gelaufen |
| `cls_practical` | 0,17 %³ | 1/3 | 1/3 | 1/3 | ⛔ |
| `trend_pullback` | 0,083 % | kein Signal | kein Signal | kein Signal | ⛔ |
| `ctnl_continuation` | 0,083 % | 1/2 | 1/2 | 1/2 | ⛔ |
| `ctnl_reversal` | 0,025 % | kein Signal | kein Signal | kein Signal | ⛔ |
| `ou_modell` | 0,17 % | 6/9 ✅ | 2/5 | **0/7** → ausgeschlossen | ⛔ |
| `orb_sp500` | 0,056 % | **0/5** | 0/3 | **0/5** | ⛔ |
| `orb_us30` | 0,056 % | 1/3 | 0/1 | 1/3 | ⛔ |
| `orb_nasdaq` | 0,056 % | **0/8** | 0/6 | **0/8** | ⛔ |

² `CAPITAL_WEIGHT (1/6) × LEG_RISK_PCT`, gedeckelt bei 1 % je Position.
³ zusätzlich seit 2026-09-13 der Rates-Multiplikator (Median 1,75 ×).

**ORB ist auf Funded seit dem 2026-09-02 vollständig ausgefallen.** Von 24
ORB-Signalen quer über die drei Konten wurden **2** platziert, beide am 09-02.
Jedes weitere endete mit derselben Zeile:

> `orb_nasdaq USTEC war bereits offen UND geschlossen (stop), bevor diese
> Bridge es je gesehen hat -- verpasst, keine Aktion möglich.`

Die Re-Simulation löst den Trade also schon beim ersten Scan wieder auf. Das
trifft **systematisch die schnellen Verlierer** — was zunächst gut klingt, aber
bedeutet, dass die Live-Stichprobe nicht mehr die Verteilung des Backtests hat.

**`ou_modell` auf dem IQ-Konto: 0 von 7 — inzwischen behoben.** 68× „kein
Live-Kurs für ou_modell (…)": die US-Einzelaktien stehen bei BeyondIQCapital
formal in der Symbolliste und lassen sich sogar per `symbol_select()` wählen,
liefern aber nie einen Kurs (ask/bid bleiben 0). Der `check_symbols.py`-Lauf
vom 08-29 hatte sie deshalb fälschlich als „ähnlich gefunden" gemeldet.
Seit 2026-09-13 steht `excluded_legs=("ou_modell",)` in der Config, und das
frei werdende Budget geht über `capital_weight=1/3` (statt 1/6) an die
verbleibenden fünf Beine — Nutzerentscheid, Monte-Carlo-belegt (CAGR
10,7 → 22,3 %, MaxDD 2,2 → 4,4 %, `p_breach` 0,000 → 0,005).
**Der Fehlermodus bleibt trotzdem lehrreich:** ein Symbol kann existieren,
wählbar sein und trotzdem nie handelbar sein. `check_symbols.py` prüft das
nicht — es braucht eine echte Tick-Abfrage, nicht nur `symbols_get()`.

## FKInstantFunding-MT5-Bridge — BeyondIQCapital 17764, echtes Geld

`LIVE_LEGS` = 7 Beine seit 2026-09-09 (`orb_×3`, `gold_asb`, `cls_practical`,
`ctnl_continuation`, `ctnl_reversal`); `trend_pullback`/`gold_silver` bewusst
weiterhin nur geplant.

| Bein | Ist seit `DRY_RUN=False` (2026-09-08) | Paper-Bot |
|---|---|---|
| `orb_nasdaq` | 0/4 — alle „bereits offen und geschlossen" | ✅ läuft (nur noch trend_pullback/gold_silver) |
| `orb_sp500` | 0/2 — einer **vom Broker abgelehnt** (`10016 Invalid stops`) | ✅ |
| `orb_us30` | kein Signal | ✅ |
| `cls_practical` | 0/1 | ✅ |
| `ctnl_continuation` | 0/2 — einer geplant, **kein Ticket** | ✅ |
| `gold_asb` / `ctnl_reversal` | kein Signal | ✅ |

**Fünf Handelstage live, null ausgeführte Orders.** Die Bridge verbindet sich,
scannt, rechnet Lots aus und schreibt saubere Logs — sie bringt nur nichts zum
Broker. Ursachen laut Log: 1× echte Ablehnung (`Invalid stops`), 2×
`order_send()=None` (Verdacht Kommentarlänge, siehe CHANGELOG 2026-09-13),
Rest durch die Restlaufzeit-Gates verworfen.

---

## Die Paper-Bot-Spalte: der eigentliche blinde Fleck

Der Vergleich, um den es in dieser Spalte gehen sollte, **ist derzeit nicht
möglich** — für zwei der drei Portfolios existiert kein laufender
Paper-Zwilling:

| Paper-Bot | Scheduled Task | Letzter Stand | Trades je |
|---|---|---|---|
| `ek_portfolio/paper_bot.py` | **Disabled** seit 2026-08-31 | `paper_state.json` 08-31 | eingefroren |
| `challenge_portfolio/paper_bot.py` | **existiert nicht** | `paper_state.json` 08-28 | **0 — nie ein Trade** |
| `fk_instant_funding/paper_bot.py` | Ready, stündlich | 09-11 22:55 | 24 |

Besonderheit bei Challenge: `challenge_portfolio/paper_bot.py` hat als
*Simulation* nie gearbeitet, wird aber als *Bibliothek* zur Laufzeit von der
Echtgeld-Bridge importiert (Scan-Funktionen, `LEG_RISK_PCT`,
`ORB_EXIT_CFG_BY_INSTRUMENT`). Ein Commit an dieser Datei wirkt beim nächsten
Bridge-Lauf auf echtes Geld — ohne dass je ein Paper-Lauf ihn gegengeprüft
hätte.

**Der einzige echte Paper-vs-Live-Vergleich, FK, geht weit auseinander:**

| | Paper-Bot | Live-Konto |
|---|---|---|
| Equity 2026-09-11 | 98.981,60 (−1,02 %) | 100.159,75 (+0,16 %) |
| Trades gesamt | 24 | 0 |
| Letzter Trade | 2026-09-08 | — |

Der Paper-Bot verlor 1 %, weil er die Signale nahm; das Live-Konto steht leicht
im Plus, weil es keines nahm. Das ist **kein Vorteil** — es heißt, dass die
Live-Kurve gerade nichts über die Strategie aussagt.

---

## Was daraus folgt

1. **Ohne laufenden Paper-Zwilling ist jede Live-Kurve unlesbar.** Man sieht
   nicht, ob ein schwaches Ergebnis von der Strategie oder von der Ausführung
   kommt. Die zwei pausierten Paper-Tasks wieder scharfzustellen ist der
   billigste Erkenntnisgewinn im ganzen System.
2. **Die Gates sind inzwischen der dominante Effekt, nicht der Edge.** 80 % der
   Funded-Signale und 100 % der FK-Signale sterben in Gates oder an der
   Order-Ebene. Jede Strategie-Optimierung wirkt nur auf den kleinen Rest.
3. **„Live geschaltet" ≠ „handelt".** FK gilt seit fünf Tagen als live und hat
   nichts ausgeführt. Für die Statustabelle im `DASHBOARD.md` braucht es neben
   dem Modus eine Spalte „letzter echter Entry".

Verwandt: [[bridge-infrastruktur-vergleich]] · [[systemlandkarte]] ·
[[paper-bot-zu-live-bridge]] · `DASHBOARD.md` · `CHANGELOG.md`
