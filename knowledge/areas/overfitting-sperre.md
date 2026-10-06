# Area: Overfitting-Sperre (IS / OOS / Tresor)

Standardprozess seit 2026-10-05 (Nutzerentscheid). Gilt für jede Strategie ab
Phase 4 des [[backtest-standard-process]], auch für händische Strategien nach
dem [[edge-card-workflow]].

## Warum

Bei der NY-Open-ORB-Strategie wurde ab Stage 2 direkt auf OOS-Zahlen
ausgewählt, z. B. in Stage 3 („Alle Zahlen OOS“), in Stage 4a
(„OOS-only-Scan“), im Exit-Gitter („IS und OOS positiv“) und beim
Storno-Entscheid vom 04.10.2026. Am Ende standen 15 auf den Daten gewählte
Entscheidungen und mehrere hundert getestete Varianten, aber kein unberührter
Zeitraum mehr.

Die Ursache war eine Lücke im Prozess. Der OOS-Split stand nur in Phase 6 als
Prüfung („anderer Zeitraum als beim Fitting“). Keine Regel verbot, schon in
Phase 4/5 auf OOS zu schauen, und technisch hielt einen nichts davon ab.
Siehe [[ny-open-orb-sp500]] und [[orb-order-storno-und-haltedauer]].

## Die Regeln

1. **Split zuerst.** Vor dem ersten Test werden drei Zeiträume festgelegt und
   registriert:
   - **IS** zum Entwickeln,
   - **OOS** zum einmaligen Testen,
   - **Tresor** = die letzten 12 Monate.

   Danach ist der Split unveränderlich (`research_lock.Lock.register_split`).
2. **Optimieren nur auf IS.** Parameter, Filter, Instrumente und Exits werden
   nur mit IS-Zahlen gewählt (`Lock.is_only`). Skripte geben in Phase 4/5
   keine OOS-Zahlen aus.
3. **Jede Variante zählt.** Alle getesteten Varianten kommen ins
   Trial-Register (`Lock.log_trials`), auch die verworfenen. Der Gewinner
   braucht eine **Deflated Sharpe > 0,95** gegen diese Anzahl
   (`research_lock.deflated_sharpe`). Es gibt keine harte Parameter-Sperre;
   die Korrektur über die Versuchsanzahl ersetzt sie (Nutzerentscheid).
   **Hinweis (seit 2026-10-06, Richtwert aus dem Kurs):** höchstens **9
   optimierte Punkte je Index/Strategie**. Ein Punkt ist jede Einstellung,
   die auf den Daten gewählt wird, z. B. Richtung, Filter, Stop, Ziel oder
   Teilziel. Fest vorgegebene Regeln zählen nicht. Wer darüber geht, schreibt
   die Begründung dazu.
4. **Einfrieren, dann einmal OOS.** Die gewählte Konfiguration wird mit Hash
   eingefroren (`Lock.freeze`), erst dann wird OOS geöffnet
   (`Lock.unseal("oos")`). Scheitert sie dort, wird **nicht** auf OOS
   nachjustiert. Eine neue Idee braucht einen neuen Zeitraum.
5. **Tresor einmal öffnen.** Das Ergebnis zählt, egal wie
   (`Lock.unseal("tresor")`, technisch nur einmal möglich). Wer danach noch
   etwas ändert, hat keinen Holdout mehr.
6. **Live-Strategien ändern nur mit Forward-Daten.** Nach dem Livegang sind
   nur Daten nach dem Live-Start unberührt. Eine Änderung an einer laufenden
   Strategie wird auf Forward-/Live-Daten geprüft, nicht erneut auf dem alten
   OOS.

## Technik

`research_lock.py` im Repo-Root; Tests in `tests/test_research_lock.py`. Der
Zustand je Strategie liegt git-getrackt unter `knowledge/_research_lock/`:
`<strategie>.json` für Split, Trial-Zahl, Freeze-Hash und geöffnete Stufen,
`.jsonl` als Protokoll. Ein zweites Öffnen, ein Öffnen ohne Freeze oder ein
verschobener Split brechen mit `LockError` ab.

Erste Anwendung: `scripts/research_orb_is_only_reopt.py` (ORB nur auf IS
neu optimiert, 2026-10-05).

## Checkliste

Die Punkte stehen in `app_pages/education_gold_intraday.py`:
- `p4_0`: Split registrieren
- `p5_0`: nur IS + Trial-Register
- `p6_9`: einfrieren + Deflated Sharpe
- `p6_10`: OOS/Tresor je einmal
