# Dashboard

Die tägliche Cockpit-Ansicht — hier reinschauen, nicht in Task Scheduler,
config.py-Dateien oder Chat-Verläufe wühlen. Funktioniert in jedem Editor,
kein Obsidian nötig. Wird von Claude bei jeder relevanten Änderung
nachgeführt (siehe `CLAUDE.md`).

Research-Wissen (Papers, Strategie-Findings) gehört NICHT hierher, sondern
in die PARA-Struktur (`projects/`, `areas/`, `resources/`, `archive/`,
siehe `README.md`). Hier geht es nur um: was läuft gerade, was ist zuletzt
passiert, was steht an.

---

## Status — was läuft gerade wirklich

| Bot/Bridge | Konto/Broker | Modus | Task Scheduler | Zuletzt geprüft |
|---|---|---|---|---|
| EK-Portfolio-Bridge | Tickmill Live (55918977) | **LIVE — echtes Geld** | Ready (alle 15 Min, Mo–Fr) | 2026-09-01 |
| FKInstantFunding-MT5-Bridge | BeyondIQCapital (17764) | DRY_RUN | Ready (stündlich) | 2026-09-01 |
| FK-Instant-Funding-Paper | — (reine Simulation) | Paper + Telegram | Ready (stündlich) | 2026-09-01 |
| OU-Modell-ScannerHourly | — (nur Signal-Scan, kein Order-Versand) | Scanner | Ready (Mo–Fr, US-Handelszeiten) | 2026-09-01 |
| Forex-Weekly-Report | — | Report-Generator | Ready | 2026-09-01 |
| Challenge Portfolio (TTP/IQ Markets) | — (reine Simulation) | Paper-Bot fertig entwickelt | **Noch KEIN Task angelegt** | 2026-09-01 |
| BTC-EMA-Cross-Bridge/-Scan | Binance | LIVE (war), aktuell pausiert | **Disabled** | 2026-09-01 |
| CLS-Practical-Bridge/-Scan | — | pausiert | Disabled | 2026-09-01 |
| CTNL-Edge-FK-Paper | — | pausiert | Disabled | 2026-09-01 |
| CTNL-Edge-MT5-Bridge | BeyondIQCapital (15514) | pausiert | Disabled | 2026-09-01 |
| Gold-ASB-Scan / GoldASB-MT5-Bridge | BeyondIQCapital (16054) | pausiert | Disabled | 2026-09-01 |
| OU-Modell-MT5-Bridge/-DailyLog/-Heartbeat | TTP Konto1/Konto2 | pausiert | Disabled | 2026-09-01 |
| EK-Portfolio-Paper | — | pausiert | Disabled | 2026-09-01 |

## 🔍 Braucht deine Bestätigung

Punkte, bei denen etwas unklar/widersprüchlich ist oder eine Annahme von mir
noch nicht von dir bestätigt wurde. Erledigte Punkte werden entfernt, nicht
abgehakt-und-liegengelassen.

- **Widerspruch OU-Modell/CTNL-Edge-MT5-Bridge**: Task Scheduler zeigt beide
  als `Disabled`, aber der aktuelle Docstring von `challenge_portfolio/paper_bot.py`
  (von einer parallelen Session/dir selbst geschrieben) beschreibt sie als
  "bereits live laufende Solo-Bots" auf echten TTP-/IQ-Markets-Konten. Läuft
  da noch etwas außerhalb des Windows Task Schedulers, oder ist der
  Docstring veraltet? Bitte einmal klarstellen, dann trage ich es hier ein.

## 💡 Ideen-Inbox (unsortiert, später einordnen)

Kurz einfangen, was gerade auftaucht, ohne das aktuelle Thema zu verlassen —
wird bei Gelegenheit einsortiert (in Offene Aufgaben, PARA-Struktur, oder
bewusst verworfen), nicht hier für immer liegen gelassen. Genau der Ort für
"das könnte auch noch interessant sein", ohne dass es das gerade laufende
Thema verdrängt oder verloren geht.

- **PDFs/Bücher bulk-einbinden** (2026-09-01): viele Bücher/PDFs vorhanden,
  die sinnvoll integriert werden könnten, ohne sie einzeln in den Chat
  schicken zu müssen. Prüfen, ob `paper_dropbox/`/`paper_research/`
  (bestehende "PDF rein, Extraktion + Auto-Backtest raus"-Pipeline, siehe
  README.md) dafür wiederverwendbar ist, oder ob Bücher (anders als
  Research-Paper) einen eigenen Weg brauchen. Noch nicht bearbeitet.

## Offene Aufgaben

**Hoch**
- [ ] Challenge Portfolio (TTP + IQ Markets, 6 Beine) ist fertig entwickelt
  und getestet, aber noch nicht in Task Scheduler eingetragen — bewusst
  scheduled lassen oder erst zeitlich planen?
- [ ] Widerspruch OU-Modell/CTNL-Edge-MT5-Bridge klären (s.o.)

**Mittel**
- [ ] Second-Brain/Dashboard-Struktur (dieses Dokument) — nach ein paar
  Tagen Nutzung Feedback einholen, ob Format/Umfang passt.
- [ ] EK-Portfolio-Bridge: Spread-Stunden-Pause (23:00) fehlt noch —
  Nutzer hat am 2026-08-29 explizit "nicht anfassen" gesagt, da Live-System;
  bei Gelegenheit gemeinsam nochmal bewusst entscheiden.

**Niedrig**
- [ ] `knowledge/`-Altlasten: mehrere `[[wikilinks]]` in `projects/`/`archive/`
  zeigen ins Leere (kein Ziel-File) — irgendwann aufräumen, nicht dringend.

## Letzte Aktivität

_(Auszug — vollständiges Log in [CHANGELOG.md](CHANGELOG.md))_

- 2026-09-01 — 5 verwaiste MT5-Terminals geschlossen, nur die 2 aktiven blieben offen.
- 2026-09-01 — Challenge Portfolio: CTNL-Reversal-Kaskade gekappt + OU-Modell-Import-Fix (`69f9ca6`).
- 2026-09-01 — EK-Portfolio: CTNL-Reversal-Kaskade auf reales 3er-Limit gekappt (`c195924`).
- 2026-08-31 — FK Instant Funding: `scan_errors_today` auf lokalen Kalendertag umgestellt (`adc7d7c`).
- 2026-08-29 — Wochenend-/Spread-Stunden-Sperre auf EK-Portfolio + CTNL-Edge-FK-Paper ausgeweitet (`5fcf1da`).
- 2026-08-29 — FK Instant Funding: Wochenend-/Spread-Stunden-Sperre + UTC/Lokalzeit-Bug behoben (`79df9f3`).
- 2026-08-29 — FK Instant Funding: eigenes Telegram-Layout + gebündelte Nachrichten (`8f9a11a`).
- 2026-08-29 — FK Instant Funding: Gewichts-Optimierung + `CAPITAL_WEIGHT`-Umbau (`59ba4df`, `11f8979`).
