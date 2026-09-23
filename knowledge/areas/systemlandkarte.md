# Systemlandkarte: wie aus einem Kurs eine Order wird

**Stand: 2026-09-14** (Datenbasis der Zählungen: 2026-09-13) · **Typ:** Area

Diese Seite beantwortet **nicht** „was läuft gerade" — das steht im
`DASHBOARD.md`. Sie beantwortet: **wie hängt das alles zusammen, und an
welcher Stelle verliert es unterwegs was.** Gedacht zum Wiedereinsteigen,
wenn der Überblick weg ist.

Bein-für-Bein-Zahlen: [[bein-matrix-ist-soll-paper]].
Infrastruktur-Unterschiede der drei Bridges: [[bridge-infrastruktur-vergleich]].

---

## Teil 1 — Die eine Kette

Alles, was im System passiert, läuft durch dieselben sechs Stufen. Es gibt
drei Bridges, aber nur **eine** Kette:

```
 ①  Datenquelle      Dukascopy · yfinance · TradingView · MT5-nativ
        ↓
 ②  Data Lake        data_lake_store/ + manifest.json (Frischefenster)
        ↓
 ③  Scan             die drei paper_bot.py IM REPO — hier lebt die Strategie
        ↓
 ④  Gates            Alter · Restlaufzeit · R-Detektor · Risikodeckel · Kill-Switch
        ↓
 ⑤  Sizing           risk_dollars / |Live-Kurs − SL|  →  Lots
        ↓
 ⑥  order_send()     MT5 → Broker
```

**Der wichtigste Satz zum Verständnis:** die Strategie-Logik liegt nicht in
den Bridges, sondern im Repo. Funded und FK **importieren** `paper_bot.py` zur
Laufzeit; EK hat Teile davon kopiert. Deshalb ist ein Commit an
`challenge_portfolio/paper_bot.py` eine Änderung an einem Echtgeld-Bot, und
deshalb driftet ausgerechnet EK am ehesten ab.

### Wo die drei Bridges auf dieser Kette sitzen

| | EK (Tickmill) | Funded (TTP ×2 + IQ) | FK (BeyondIQ) |
|---|---|---|---|
| Konten | 1 | 3 | 1 |
| Beine | 8 (+ORB ×3) | 6 (+ORB ×3) | 9, davon 7 live |
| ① Daten | MT5-nativ für ORB/Gold-Silber/Trend-Pullback, sonst Lake | Lake für alles | MT5-nativ für ORB, sonst Lake |
| ③ Scan-Quelle | `ek_portfolio.paper_bot` (teils kopiert) | `challenge_portfolio.paper_bot` (importiert) | `fk_instant_funding.paper_bot` (importiert) |
| Takt | 15 Min + 2 Min | 15 Min + 5 Min | 60 Min + 5 Min |

Seit 2026-09-13 laufen alle handelsbezogenen Tasks **nur Mo–Fr** — ein leeres
Wochenend-Log ist kein Ausfall.

---

## Teil 2 — Wo es unterwegs verlorengeht

Das ist der Kern. Die Kette funktioniert technisch; sie verliert nur an fast
jeder Stufe etwas, und in Summe kommt kaum noch etwas an.

### Stufe ② — Der Lake läuft regelmäßig trocken

Das Frischefenster steht auf **35 Minuten** für alle M5/M15/H1/H4-Daten
(`data_lake/manifest.py::_STALENESS_MINUTES`). Ist ein Eintrag älter, gilt er
als veraltet, und der Leser fällt auf einen **Live-Fetch bei Dukascopy**
zurück. Genau dort hängt die Bibliothek dann 20–90 Sekunden und reißt das Bein
mit.

Gezählt in den Logs:

| Bridge | Lake-Fallbacks | Häufigster Datensatz |
|---|---|---|
| EK | 774 | `EURUSD_M5` (124×) |
| Funded | > 1.400 | `SP500_M15` (282×) |
| FK | 728 | `EURUSD_M5` |

**Alle** davon sind `LakeStaleDataError` — kein einziger „Datensatz fehlt".
Das Problem ist nicht der Ingest an sich (585 von 587 Fast-Läufen beendeten
sauber), sondern dass Ingest und Bridge **gemeinsam** aussetzen, wenn der
Kurztakt-Task nicht feuert. Am 2026-09-11 schwiegen beide in zwei Fenstern
(00:14–02:29 und 13:16–14:38) — in genau diesen Stunden liegen sämtliche
Scan-Fehler des Tages, in allen übrigen null.

> **Ein 35-Minuten-Fenster bei 15-Minuten-Kadenz verzeiht genau einen
> ausgefallenen Lauf.** Das ist die eigentliche Auslegungsfrage, nicht der
> einzelne Task-Ausfall.

Folge, konkret: `cls_practical` hat auf EK **104 Scan-Fehler** gesammelt und
noch nie eine Order gesendet.

### Stufe ④ — Die Gates fressen inzwischen mehr als der Edge bringt

Über die Zeit sind fünf Schutzschichten dazugekommen, jede einzeln gut
begründet. Zusammen sind sie der dominante Effekt geworden:

| Gate | Wofür gebaut | Was es real kostet |
|---|---|---|
| **Signal-Alter** | nicht einem gelaufenen Kurs hinterherjagen | — |
| **Restlaufzeit** (`signal_already_stopped`) | nicht in ein totes Signal einsteigen | **Funded-ORB: 22 von 24 Signalen** |
| **R-Detektor** (0,75R) | Hebel-Aufblähung nach Vorlauf deckeln | greift selten, wirkt |
| **Aggregierter Risikodeckel** | Stapelrisiko begrenzen | EK `orb_us30`: **213 Skips** bis 09-10 |
| **Kill-Switch / Trailing-DD** | Ruin verhindern | bisher nie ausgelöst |

Der Restlaufzeit-Filter ist dabei der teuerste — und der heikelste: er trifft
**systematisch die schnellen Verlierer**. Das klingt nach einem Vorteil, heißt
aber, dass die Live-Stichprobe nicht mehr die Verteilung des Backtests hat.
**Ein Backtest, dessen Verlierer man live überspringt, validiert den
Live-Betrieb nicht mehr.**

Der Risikodeckel dagegen ist ein gelöster Fall: seit der Anhebung von 8 % auf
30 % am 2026-09-10 gab es **keinen einzigen** `risk_cap`-Skip mehr.

### Stufe ⑥ — Die Order-Ebene ist die jüngste und schwächste

Erst seit wenigen Tagen gehen überhaupt Orders raus, und hier häufen sich drei
Fehlerbilder:

1. **`retcode=10016 "Invalid stops"`** — EK (SP500/US30, 15× am 09-01…09-03)
   **und** FK (SP500, 09-11 16:03). Zwei Bridges, derselbe Fehler, unabhängig
   voneinander aufgetreten. Zwei ungeprüfte Kandidaten: SL nicht auf Tickgröße
   gerundet (der abgelehnte SL hatte 12 Dezimalstellen) oder Stopabstand unter
   dem Broker-Mindestabstand (4,93 Punkte = 0,064 %). Eine `symbol_info`-Abfrage
   (`digits`, `trade_stops_level`) klärt beides.
2. **`order_send() = None`** — kein Retcode, keine Diagnose. Bekannter
   Auslöser: zu langer Order-Kommentar (Broker-Limit 16 Zeichen). Traf EK am
   09-04 und 09-09, FK vermutlich am 09-09 bei zwei Echtgeld-Entries.
3. **Exit-Orders scheitern still** — EKs CTNL-Exit 16×, die
   ORB-Session-Schließung 332×. Ein Entry, der nicht mehr geschlossen werden
   kann, ist gefährlicher als ein verpasster Entry.

> **Muster:** jedes dieser Probleme wurde schon einmal in *einem* Bein
> behoben und kam in einem anderen zurück. Härtungen gehören in den
> gemeinsamen Engpass (`core/order_send.py`), nicht ins Bein — siehe
> [[paper-bot-zu-live-bridge]], Abschnitt „Ein Fix pro Bein ist kein Fix".

---

## Teil 3 — Die Bilanz

| | Signale | Echte Orders | Quote |
|---|---|---|---|
| EK (seit 08-29) | — | 20 | 4 von 11 Bein-Keys haben je gehandelt |
| Funded (seit 09-01) | 80 | 16 | 20 % |
| FK (seit 09-08) | 9 | **0** | **0 %** |

FK gilt seit fünf Handelstagen als live und hat **nichts ausgeführt**. Die
Bridge verbindet sich, scannt, rechnet Lots und schreibt saubere Logs — sie
bringt nur nichts zum Broker. Das ist der Unterschied zwischen „läuft" und
„handelt", und im Dashboard war er bisher nicht sichtbar.

---

## Teil 4 — Lücken und Optimierungen, nach Gewicht

**🔴 Zuerst — ohne das ist alles andere Ratespiel**

1. **Die Order-Ebene reparieren** — **Stand 2026-09-17: Ursachen beide
   geklärt, akute Fälle behoben, eine Härtung offen.**
   - `Invalid stops` = SL nicht aufs Tick-Raster gerundet (`SPX500.gbe`:
     Tickgröße 0,1 bei 2 Nachkommastellen). Behoben *pfadweise* von der
     Parallel-Session: FK-Market-Pfad und Funded-Stop-Order-Pfad runden.
   - `order_send()=None` auf FK war **nicht** die Kommentarlänge (so hatte ich
     es übernommen), sondern ein `SizingResult`-Objekt im `volume`-Feld —
     am 2026-09-09 behoben, seither kein einziges Vorkommen mehr.
   - **Offen:** Funded rundet im *Market*-Pfad nicht. Aktuell harmlos, weil
     dort nur Symbole mit regulärem Raster laufen — aber latent. Die Härtung
     im gemeinsamen `_send_order()` wurde vom Auto-Mode-Classifier blockiert
     (Echtgeld-Order-Code) und wartet auf deine Freigabe, siehe DASHBOARD.
2. ~~**Die zwei pausierten Paper-Bots wieder scharfstellen**~~ — **verworfen
   2026-09-14** (Nutzerentscheid). Ersetzt durch den Soll/Ist-Vergleich
   (`scripts/reports/soll_ist.py`), der wöchentlich im Report läuft.
3. ~~**Den Restlaufzeit-Filter gegen den Backtest rechnen.**~~ — **für ORB
   überholt 2026-09-16.** Die Parallel-Session hat die viel grundsätzlichere
   Frage beantwortet (2.336 Trades): ORB per Market-Order zum Bar-Schluss hat
   **PF 0,82, Ø R −0,144, P(Ø R<0) 99,7 %**; per ruhender Stop-Order am Level
   PF 1,36. Der Filter hat also einen strukturell verlustbringenden
   Ausführungsweg gebremst — passt zum KW37-Soll/Ist, in dem die Gates
   Verluste verhinderten. Die Antwort ist nicht ein anderer Filter, sondern
   Stop-Orders. **Die laufen bisher nur auf den zwei Funded-Demokonten**;
   Funded-Echtgeld (TTP1), FK und EK handeln ORB weiter per Market-Order.
   Für CLS/CTNL ist die Frage über die R-Detektor-Studie (2026-09-10/11)
   bereits beantwortet.

**🟡 Danach**

4. **Frischefenster des Lake an die Kadenz koppeln** — **Stand 2026-09-17:
   Voraussetzung hat sich verschoben, braucht deine Entscheidung.** Meine
   Annahme war, das 35-Minuten-Fenster sei zu knapp. Inzwischen ist belegt,
   dass die Stale-Fenster vor allem dort liegen, wo Ingest *und* Bridge
   gleichzeitig ausfielen — durch die springende Windows-Zeitzone (jeder
   Vorwärtssprung ≈ 1 h ausgefallene Tasks) und Rechner-Schlaf. Ein weiteres
   Fenster würde das eher verdecken als beheben. Sinnvoll bleibt ein Teil:
   **H1/H4/D1-Reihen** brauchen kein 35-Minuten-Fenster, M5 schon.
5. ~~**Hard-Timeout je Bein bei Funded und FK**~~ — **2026-09-16 geprüft:
   Lücke bestand so nicht.** Jeder Datenabruf ist dort bereits auf ~66 s
   begrenzt (strenger als EKs 600 s). Ein Timeout um die Order-Verarbeitung
   wäre schädlich — ein abgebrochener, aber doch durchgegangener
   `order_send()` fehlt im State und wird beim nächsten Lauf doppelt gesendet.
   Details: [[bridge-infrastruktur-vergleich]], Lücke 2.
6. ~~**`check_symbols.py` auf echte Tick-Abfrage umstellen.**~~ — **erledigt
   2026-09-16** (Funded + FK). Prüft jetzt je Symbol: auflösbar über die
   Bridge-eigene Zuordnung, Handel freigeschaltet, echter Kurs nach dem
   Wählen (mit 3 s Wartezeit gegen den bekannten 0-Tick-Fehlalarm), plus
   Tickgröße/Nachkommastellen/Stopabstand/Mindestlot. Erster Lauf zeigte
   gleich zwei Dinge: `SPX500.gbe` hat **2 Nachkommastellen, aber Tickgröße
   0,1** — Ursache von „Invalid stops", und sie betrifft neben FK auch das
   **Funded-IQ-Konto**; und Platin hat überall ein Mindestlot von 1,0.

**🟢 Aufräumen**

7. ~~**EKs `config.py`-Kommentar zur Kapitalscheibe korrigieren**~~ —
   **erledigt 2026-09-16.** Zahl 1/8 unverändert, nur die Begründung.
8. ~~**Spalte „letzter echter Entry" in die Dashboard-Statustabelle**~~ —
   **erledigt 2026-09-16**, gespeist über
   `python scripts/reports/soll_ist.py --last-entries`. Trennt Bridge-Trades
   von Fremdpositionen — auf FK liegen wiederholt manuelle Positionen, die
   sonst wie Bridge-Aktivität aussähen.

---

Verwandt: [[bein-matrix-ist-soll-paper]] · [[bridge-infrastruktur-vergleich]] ·
[[paper-bot-zu-live-bridge]] · [[mt5-bot-deployment]] · `DASHBOARD.md`
