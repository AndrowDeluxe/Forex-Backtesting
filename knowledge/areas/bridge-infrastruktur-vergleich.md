# Bridge-Infrastruktur: Soll-Ist-Vergleich der drei Portfolios

**Stand: 2026-09-10** _(bei jeder Infrastruktur-Änderung an einer der drei
Bridges mitpflegen — sonst ist diese Seite schlimmer als keine.)_

## Wozu diese Seite

Auf die Frage "sind alle drei Portfolios auf demselben Stand?" wurde bisher
regelmäßig mit **Ja** geantwortet — bezogen auf die *Strategie-Logik*
(gleiche Beine, gleiche Signal-Engines, gleiche Kill-Switches). Das stimmt
auch. Gemeint war aber die **Infrastruktur darunter**, und die ist
systematisch auseinandergedriftet (Nutzerfeedback 2026-09-09).

Ursache ist strukturell: Muster werden zwischen den Bridges immer nur
**anlassbezogen** "1:1 übernommen" — nie als vollständiger Abgleich. Und weil
alle drei Bridge-Ordner außerhalb des Git-Repos liegen, gibt es keinen Diff,
der die Drift sichtbar machen würde (siehe Memory
`external-bridge-files-no-git-safety-net`).

Deshalb hier eine nachschlagbare Tabelle statt einer Behauptung.

## Die drei Bridges

| | **EK-Portfolio-Bridge** | **Funded-Portfolio-Bridge** | **FKInstantFunding-MT5-Bridge** |
|---|---|---|---|
| Broker / Konten | Tickmill Live 55918977 (1) | TTP ×2 + BeyondIQCapital 16054 (3) | BeyondIQCapital 17764 (1) |
| Echtes Geld | ja | ja (`DRY_RUN=False`) | ja (`DRY_RUN=False`, `LIVE_LEGS` 7 von 9) |
| Repo-Modul (`pb`) | `ek_portfolio.paper_bot` | `challenge_portfolio.paper_bot` | `fk_instant_funding.paper_bot` |
| Slow-Takt | **15 Min** (Limit 14 Min) | **15 Min** (Limit 14 Min) | **stündlich** (Limit 30 Min) |
| Fast-Takt | **2 Min** (Limit 2 Min) | **5 Min** (Limit 4 Min) | **5 Min** (Limit 4 Min) |
| Fast-Beine | ORB, Gold-Silber, Trend-Pullback | ctnl_continuation, ORB ×3, cls_practical | ctnl_continuation, ORB, cls_practical |

## Infrastruktur im Detail

| Aspekt | EK | Funded | FK |
|---|---|---|---|
| **ORB-Datenquelle** | MT5-nativ (`fetch_recent_mt5`) | Lake + Live-Fallback (dukascopy) | **MT5-nativ** seit 09-09, Fallback auf Lake |
| **Server-TZ-Behandlung** | `SERVER_TZ_NAME` + `verify_server_offset()` je Lauf | **keine** | `SERVER_TZ_NAME` + `verify_server_offset()` (seit 09-09) |
| **Hard-Timeout je Bein** | `LEG_TIMEOUT_S = 600` | **keiner** | **keiner** |
| **Retry Slow-Pfad** | `_retry` 6/8s/90s (dukascopy-Beine) | 3/3s/20s (seit 09-08) | 3/3s/20s (seit 09-08) |
| **Retry Fast-Pfad** | entfällt weitgehend (MT5-nativ) | 3/3s/20s | 3/3s/20s |
| **Cross-Prozess-Lock** | nicht nötig (SQLite-State) | `account_state_lock()` pro Konto, 45s | `state_lock()` global, 45s |
| **Lock-Timeout abgefangen** | entfällt | ja, in beiden Pfaden | ja (seit 09-08; vorher unbehandelter Absturz) |
| **Restlaufzeit-Gate** | `core/signal_liveness.py` + 6 Beine | `executor.py` | `executor.py` |
| **Scan-Deduplizierung** | entfällt (1 Konto) | ja (`run_shared_scans`, 1×/Lauf seit 09-03) | entfällt (1 Konto) |
| **ORB-Symbolnamen** | `US500` / `US30` / `USTEC` | TTP wie EK; IQ `SPX500.gbe` / `US30.gbe` / `NAS100.gbe` | `SPX500.gbe` / `US30.gbe` / `NAS100.gbe` |

## Offene Lücken (der eigentliche Soll-Ist-Delta)

1. ~~**🔴 EK: ORB rechnet auf 5 Stunden alten Bars.**~~ — **behoben 2026-09-10.**
   Der Fehler saß nicht nur im ORB-Bein, sondern in **allen drei** Beinen mit
   MT5-Bar-Abfrage (ORB, Gold-Silber, Trend-Pullback), jeweils als eigene Kopie
   derselben Fensterlogik. Neu: `core/mt5_bars.py` als gemeinsamer Helfer, die
   drei Beine rufen ihn auf. Verifiziert an den echten Funktionen: ORB M5/M15
   liefern jetzt Bars, die **3,4 Minuten** alt sind (vorher ~300), Gold-Silber
   H4 78 Min., Trend-Pullback H1 18 Min. — alles im normalen Bereich des
   jeweiligen Timeframes. `gold_asb` war nie betroffen (nutzt den Lake-Weg).
2. **Funded + FK haben keinen Hard-Timeout je Bein.** EK kappt jedes Bein bei
   600s (gebaut nach einem Vorfall mit 23 nie beendeten `python.exe`). Die
   beiden anderen verlassen sich allein auf Retry-Timeouts plus das
   Task-Scheduler-Limit.
3. **Funded holt ORB weiterhin über Lake/dukascopy.** Phase 2 der Umstellung
   wartet auf einen beobachteten echten ORB-Entry bei FK (Nutzerentscheid
   2026-09-09: erst FK, dann Funded, dort mit einem Referenz-Terminal für alle
   3 Konten).
4. **Funded hat keine Server-TZ-Behandlung** — wird mit Phase 2 zwingend, weil
   MT5-Bars ohne korrekte Zeitzone die Session-Grenzen verschieben.

## Was zuletzt angeglichen wurde

- **2026-09-09** ORB auf MT5-native Bars (nur FK; EK hatte es schon, Funded offen).
- **2026-09-08** Slow-Pfad-Retry auf 3/3s/20s (Funded + FK) und FKs
  Lock-Timeout-Absturz behoben — beides Angleichungen an bereits Bestehendes.
- **2026-09-09** Pull-vor-Push in allen Auto-Commit-Skripten
  (`scripts/lib/git_sync_push.ps1` + `Bridge-Watchdog/watchdog.py`).

## Merkregel

Wird an einer Bridge etwas an der Infrastruktur repariert, gehört **im selben
Zug geprüft**, ob die anderen beiden dieselbe Lücke haben — und das Ergebnis
hier eingetragen, auch wenn es "betrifft die anderen nicht" lautet.

Verwandt: [[second-brain-lint]] · `DASHBOARD.md` · `CHANGELOG.md`
