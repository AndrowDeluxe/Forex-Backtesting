# Changelog

Vollständiges, chronologisches Log relevanter Änderungen (neueste oben).
Ein Eintrag pro Änderung: Datum, Bereich, Kurzbeschreibung, Commit-Hash wo
zutreffend. Wird von Claude bei jeder relevanten Änderung ergänzt (siehe
`CLAUDE.md`). Nicht committen vergessen wird hier nichts eingetragen, was
nicht auch tatsächlich passiert ist — dieses Log ist reine Beobachtung,
keine Planung (dafür ist `DASHBOARD.md`).

---

- **2026-09-01** [Infrastruktur] 5 verwaiste MT5-Terminals geschlossen
  (GoldFKBot/16054, CLSPractical/MetaQuotes-Demo, TTP/504069845,
  TTP-Konto2/504072729, generischer Default-Terminal/15514) — alle gehörten
  zu bereits deaktivierten Tasks, waren nach einem Systemneustart automatisch
  wieder aufgegangen. Nur die 2 aktiven Terminals (Tickmill/55918977,
  BeyondIQCapital/17764) blieben offen.
- **2026-09-01** [Challenge Portfolio] CTNL-Reversal-Kaskade auf reales
  3er-Gleichzeitigkeits-Limit gekappt (`_cap_concurrent_reversals`, wie
  FK Instant Funding) + unabhängiger OU-Modell-Import-Kollisions-Fix
  mitcommittet. Commit `69f9ca6`.
- **2026-09-01** [EK-Portfolio] CTNL-Reversal-Kaskade auf reales 3er-Limit
  gekappt (Paper-Bot überzeichnete bis zu 9 gleichzeitige Positionen statt
  der real gültigen 3 — Fund aus einer EK-Jahres-Rekonstruktion, 1122/1417
  Trades betroffen). Commit `c195924`.
- **2026-08-31** [FK Instant Funding] `scan_errors_today`-Tageswechsel von
  UTC- auf echten lokalen Kalendertag umgestellt (Fehler von 01:20 Uhr
  wurden durch den UTC/Lokalzeit-Versatz faelschlich vor dem Tagesabschluss
  wieder zurückgesetzt). Commit `adc7d7c`.
- **2026-08-29** [EK-Portfolio, CTNL-Edge-FK-Paper] Wochenend- +
  Spread-Stunden-Sperre (23:00 lokal) auch hier eingebaut, inkl. bewusster
  Ausnahme für BTC EMA9/21 (24/7-Krypto-Markt, wird bei EK-Portfolio NICHT
  pausiert). Neues gemeinsames Modul `strategy/schedule_guard.py`. Commit
  `5fcf1da`.
- **2026-08-29** [FK Instant Funding] Wochenend- + Spread-Stunden-Sperre
  eingebaut (User-Wunsch: "damit nichts unnötig am Wochenende läuft").
  Dabei gefunden: `DAILY_SUMMARY_HOUR` verglich fälschlich gegen UTC statt
  Lokalzeit (Tagesabschluss feuerte real 2h später als beabsichtigt) — mit
  behoben. Commit `79df9f3`.
- **2026-08-29** [FK Instant Funding] Eigenes Telegram-Layout ("🏦 FK
  INSTANT FUNDING"-Banner) + alle Scan-Ereignisse eines Laufs zu EINER
  Nachricht gebündelt statt je Strategie einzeln; Tagesabschluss bekommt
  System-Status-Zeile (Scan-Fehler heute ja/nein). `telegram_config.py`
  erstmals angelegt (fehlte komplett — Bot hatte vorher NIE eine echte
  Telegram-Nachricht verschickt). Commit `8f9a11a`.
- **2026-08-29** [FK Instant Funding] `CAPITAL_WEIGHT` von Gleichgewichtung
  (1/6) auf Monte-Carlo-optimierte Pro-Bein-Gewichte umgestellt (Gold ASB/
  Trend Pullback/Gold-Silber je 6,06%, CLS Practical 19,19%, CTNL Edge
  25,25%, ORB-Portfolio 37,37%) — sowohl im Paper-Bot als auch in der
  echten Bridge `run_once.py`. Commit `11f8979`.
- **2026-08-29** [FK Instant Funding / Portfolio-Konstruktion] Gewichts-
  Optimierung der 6 Beine, Monte-Carlo-geprüft (CAGR 15,6%→24,8%, MaxDD
  -1,78%→-2,27%, P(Trailing-DD-Bruch>5%) 0,0%→2,1%). Persistiert in
  `fk_instant_funding_final.json` + Streamlit-Tab. Commit `59ba4df`.
- **2026-08-29** [FK Instant Funding] Echte Instant-Funding-Bridge
  (BeyondIQCapital, Login 17764) angebunden und live im DRY_RUN getestet;
  Positionsgrößen-Policy "bei Unterschreitung des Mindestlots auf Mindestlot
  anheben, gedeckelt auf 0,5% Startkapital" implementiert.
- **2026-08-27** [FK Instant Funding] NY-Open ORB als 6. Strategie in den
  Live-Scan integriert (verbessert alle Kennzahlen gleichzeitig). Commits
  `d6d0f42`, `652f88f`.
- **2026-08-27** [EK-Portfolio] Neuer, separater 8-Bein Paper-Forward-Test-
  Bot angelegt (Architektur-Vorbild: FK Instant Funding). Commit `1b48562`.
- **2026-08-26** [FK Instant Funding] Neuer Paper-Forward-Test-Bot (5 Beine)
  angelegt, danach vollständiger Fehler-Audit auf Nutzerwunsch: fehlendes
  `r_multiple` bei Gold ASB/CLS Practical (Trades wurden komplett
  stillschweigend verworfen), Trade-Key-Kollisionsrisiko, Kontostart-
  Mehrjahres-Blend-Bug, EOD-Trailing-DD-Floor-Bug — alle behoben. Commits
  `3c717e3`, `51a783d`, `efa528c`, `d82c979`.

<!-- Älter als diese Session: nicht rückwirkend erfasst, siehe `git log` für vollständige Historie. -->
