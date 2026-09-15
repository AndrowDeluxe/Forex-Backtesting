# Weekly Checkup - Education - KW37/2026

**Zeitraum:** Montag 2026-09-07 bis Sonntag 2026-09-13.

> **Hinweis zum Lauf:** Dieser Report entstand verspätet am 2026-09-14. Der
> reguläre Sonntagslauf startete durch `StartWhenAvailable` zwar nach (21:21
> statt 18:00), lief dann aber in das 1-Stunden-Zeitlimit des Tasks und wurde
> vom Scheduler abgeschossen — fertig war nur der Performance-Report. Limit
> steht seit 2026-09-14 auf 4h, die Wochen-Auswahl im Report-Prompt ist für
> verspätete Läufe präzisiert (CHANGELOG 2026-09-14). Der
> Performance-Report wurde heute **ergänzt**, nicht ersetzt; sein bis dahin
> offener Punkt 5.1 (FK-Konto nicht erreichbar) ist dabei aufgelöst worden.

## 1. Was stand die Woche an / Hauptfokus

417 Commits, davon wie üblich die große Mehrheit automatische Snapshots
(Bridge-Watchdog alle 30 Min., FK-Bot, OU-Scanner). Die ~25 inhaltlichen
Commits plus die Changelog-Einträge ergeben eine Woche mit einem sehr klaren
roten Faden — und der wurde nicht geplant, sondern von einem einzelnen
Verlusttrade ausgelöst:

- **Montag (09-07) — Aufräumen und Absichern.** Data-Lake-Cold-Start-Fallback
  gebaut (`with_live_fallback()` in allen 3 Bridges), TTP Konto 2 verband seit
  Wochenschluss nicht mehr → Root Cause gefunden (fehlendes `/portable`-Flag
  beim Terminal-Vorstart). Dazu die in KW36 entstandene, aber nie committete
  Second-Brain-Arbeit endlich im Repo (`af96c0e`: Handoff-Skill,
  Edge-Card-Workflow, 6 PARA-Notizen, Lint-Tooling). Das IQ-Konto 15514 flog
  auf Nutzerwunsch aus dem Challenge-Portfolio.
- **Dienstag (09-08) — FK geht scharf.** `DRY_RUN=False` auf expliziten
  Auftrag, zunächst nur die 3 NY-Open-ORB-Beine. Damit gibt es drei
  Echtgeld-Bridges statt zwei. Nebenbei die Plan-Modus-Regel in `CLAUDE.md`
  und die Projekt-Notiz zum agentischen Research-System.
- **Mittwoch (09-09) — der Tag, an dem die Woche gekippt ist.** Morgens um
  10:30 nahm `cls_practical` auf allen drei Challenge-Konten einen
  EUR/USD-Trade, der **16 Sekunden nach dem Entry** ausgestoppt wurde
  (zusammen −1.363 $). Die Fehlersuche dazu hat den Rest der Woche bestimmt
  und nacheinander freigelegt: die Signal-Latenz (M5-Signale werden
  strukturell ~10 Min. zu spät gesehen), den nie angewendeten
  `CAPITAL_WEIGHT` auf EK, den Kommentarlängen-Bug bei `order_send()`, und die
  Phantom-Positionen im simulierten OU-Buch. Am selben Tag außerdem:
  dukascopy-Hang entschärft, `Sync-AndPush` gegen die wiederkehrende
  Git-Push-Lücke, Restlaufzeit-Gate + Task-Offsets in allen 3 Bridges, FKs
  `LIVE_LEGS` auf 7 Beine erweitert, und das JPM-Spillover-Paper durch den
  8-Phasen-Prozess (negatives Ergebnis).
- **Donnerstag (09-10) — EK repariert.** Kapitalverdünnung erstmals
  tatsächlich scharf geschaltet, Mindestlot-Sizing, Portfolio-Kill-Switch,
  Risiko-Neukalibrierung auf 40 % Ziel-Drawdown. Dabei fiel der
  **Bar-Fenster-Bug** auf: alle 3 MT5-nativen Beine rechneten auf **5 Stunden
  alten Bars** (`90ee97a`).
- **Freitag (09-11) — die Lehre auf alle drei Bridges ausgerollt.** Pip-Boden
  (5 Pips), R-Detektor (0,50R), Margin-Deckel, `LEG_RISK_PCT` für CLS von
  0,015 auf 0,010 gesenkt. Dazu EK auf absoluten Signal-SL umgestellt, der
  Morgen-Digest von 4 Telegram-Nachrichten auf 1 gekürzt und der
  Bridge-Risiko-Audit von 9 auf 1 Befund abgeräumt.
- **Samstag (09-12) — still.** Erster Tag der Woche ohne inhaltliche Arbeit.
- **Sonntag (09-13) — Wochenschluss-Aufräumen.** Wochenend-Pause für alle
  handelsbezogenen Tasks (`56d36f7`), IQ-Konto auf 5 Beine @ 1/3, EKs
  MT5-Passwort nach einem Broker-seitigen Reset nachgezogen, Wochenauswertung
  + Bein-Audit, CLS-Projekt formal abgeschlossen.

## 2. Aktive Zeiten

**Späte Abende sind das Muster dieser Woche.** Die inhaltlichen Commits
liegen auffällig oft nach 21 Uhr: Dienstag 23:36, Mittwoch 21:47–23:45,
Montag sogar 00:09–00:26. Dazwischen kürzere Mittags-/Nachmittagsblöcke
(Montag 15:03–15:41, Donnerstag 11:33–12:19, Sonntag 13:53–14:39). Das ist
dichter und regelmäßiger als in KW36 — es gab diese Woche keinen einzigen
Tag Mo–Fr ohne Arbeit.

Zwei Beobachtungen, die über "wann wurde gearbeitet" hinausgehen:

- **Freitag (09-11) hat keinen einzigen inhaltlichen Commit** — obwohl es
  gemessen am Changelog der produktivste Tag der Woche war (fünf große
  Einträge: CLS-Umbau auf allen drei Bridges, Margin-Deckel, EK-Umstellung,
  Digest-Fix, Audit-Abschluss). Diese Arbeit kam erst **Sonntag um 14:38** ins
  Repo. Exakt dasselbe Muster wurde schon im KW36-Education-Report notiert
  (dort Freitag/Sonntag) — es ist damit kein Ausrutscher mehr, sondern eine
  Gewohnheit: **an intensiven Arbeitstagen wird nicht committet, das
  Committen passiert gesammelt am Wochenende.**
- **Samstag war zum ersten Mal seit Wochen wirklich frei.** Kein inhaltlicher
  Commit, keine Changelog-Zeile. Das ist keine Lücke, das ist eine Pause —
  und passend dazu wurde am Sonntag die Wochenend-Pause auch für die Bots
  eingeführt.

## 3. Meine Main Erkenntnisse

Die lernintensivste Woche bisher — acht neue Memory-Einträge zwischen 09-09
und 09-10. Die fünf, die wirklich etwas geändert haben:

- **Der Unterschied zwischen zwei Strategie-Ergebnissen war fast vollständig
  die Kostenannahme, nicht die Strategie.** Auf die Frage "warum sieht EK so
  viel besser aus als die Challenge?" gab es eine unangenehme Antwort:
  identische Signale, identischer Code-Pfad, identische Trefferquote (49,7 %)
  und Trade-Zahl (147) — aber Ø R 0,357 bei 0,50 Pips Kosten gegen 0,179 bei
  2,05 Pips. **Faktor 2,0, allein aus einer Zahl, die bei EK geschätzt und bei
  der Challenge gemessen war.** EKs Zahlen sind nicht besser, sondern
  optimistischer angesetzt. Praktische Konsequenz für jede künftige
  Bewertung: **Kennzahlen zweier Bots sind nur vergleichbar, wenn ihre
  Kostenannahmen denselben Status haben** (beide gemessen oder beide
  geschätzt). Details: [[broker-kostenmodell-eurusd]], Memory:
  `cls_practical_cost_model_and_entry_lag` und `cls_entry_lag_dominates_costs`.
- **Eine dokumentierte Formel ist keine angewendete Formel.** `CAPITAL_WEIGHT
  = 1/8` stand seit Einrichtung als Formel im `config.py`-Docstring von
  EK-Portfolio-Bridge — und wurde nirgends im Code benutzt. Jedes Bein
  handelte ~8x größer als validiert, auf echtem Geld, wochenlang. Der
  Backtest-Gegencheck: mit Verdünnung −16,1 % Max-Drawdown, ohne **−73,7 %**.
  Die verallgemeinerbare Lehre ist die Prüfmethode, nicht der Bug: **eine
  Risikozahl-Beschriftung sagt nie, ob sie Risiko je Kapitalscheibe oder aufs
  Gesamtkonto meint — das muss gegen ein publiziertes Szenario zurückgerechnet
  werden.** Memory: `ek_capital_weight_never_applied` und
  `backtest_zahlen_gegen_szenario_pruefen`; Prozess daraus:
  [[paper-bot-zu-live-bridge]].
- **Zwischen "Signal gültig" und "Signal handelbar" liegen zehn Minuten, und
  die entscheiden über den Edge.** Der 16-Sekunden-Stop vom 09-09 war kein
  Ausreißer, sondern Systematik: M5-Signale werden durch den Ingest-/Scan-
  Versatz strukturell erst ~10 Min. nach ihrem Zeitstempel gesehen. Der
  Entry-Lag kostet mehr Edge als sämtliche Broker-Kosten zusammen. Memory:
  `bridge_signal_latency_vs_trade_lifetime` und
  `cls_entry_lag_dominates_costs`; daraus entstand die neue Pflicht-Probe
  [[realkosten-und-ausfuehrungs-probe]] als Teil von Phase 6.
- **"Sind alle drei Portfolios auf dem gleichen Stand?" war jahrelang mit Ja
  beantwortet worden — und es ging um die falsche Ebene.** Gemeint war die
  Infrastruktur (Datenquelle, Timeouts, Lock-Handling, SL-Behandlung), nicht
  die Strategie-Logik. Und die ist systematisch auseinandergedriftet: EK
  dupliziert seine Risikowerte in eine eigene `config.py` (und war genau
  deshalb abgedriftet), Funded und FK importieren ihren Paper-Bot zur Laufzeit
  und **können** strukturell nicht abdriften. Memory:
  `three_bridges_not_same_state`; Referenz:
  [[bridge-infrastruktur-vergleich]].
- **Ein Bug, der einmal behoben wurde, ist eine Bug-Klasse, keine erledigte
  Aufgabe.** Der zu lange MT5-Order-Kommentar (Tickmill lehnt mit
  `result=None`, ganz ohne Retcode, ab) wurde am 09-04 in genau einem Bein
  gefixt. Am 09-09 hat dieselbe Ursache eine CTNL-Position auf EK vier Stunden
  lang nicht schließen lassen — und auf FK sterben bis heute Entries daran
  (`FKIF cls_practical` = 18 Zeichen gegen ein 16-Zeichen-Limit). Lehre:
  **einen bein-spezifischen Fix immer sofort auf die gemeinsame Ebene ziehen**
  (auf EK wurde daraus `core/order_send.py`) und gegen alle Geschwister
  prüfen. Memory: `mt5_comment_length_order_reject`.

**Nach Wochenschluss, aber inhaltlich über genau diese Woche** (09-13/09-14,
gehört sinngemäß hierher):

- **"Live" heißt nicht "handelt".** Die Bein-Zählung über alle drei Bridges
  ergab: Funded platziert 16 von 80 Signalen (20 %), EK hat in nur 4 von 11
  Bein-Keys je eine Order gesendet, **FK seit dem Live-Gang null von neun**.
  Die Statustabelle zeigt eine Modus-Spalte ("LIVE — echtes Geld"), aber keine
  Spalte "letzter echter Entry" — eine Bridge, die sich verbindet, scannt und
  saubere Logs schreibt, sieht dort genauso aus wie eine, die tatsächlich
  handelt. **Der schwerere Teil daran:** die fünf nacheinander eingebauten
  Schutzschichten sind zusammen zum dominanten Effekt geworden und verwerfen
  systematisch die *schnellen Verlierer*. Das klingt nach Vorteil, heißt aber:
  ein Backtest, dessen Verlierer man live überspringt, validiert den
  Live-Betrieb nicht mehr. Memory: `live_ist_nicht_gleich_handelt`; Details:
  [[bein-matrix-ist-soll-paper]] und [[systemlandkarte]].
- **Ein nicht ausführbares Bein ist kein Nullbeitrag, sondern ein
  stillgelegter Kapitalanteil.** IQ Markets bietet gar keine Einzelaktien an —
  die Ticker stehen formal in der Symbolliste und lassen sich per
  `symbol_select` wählen, liefern aber nie einen Kurs. Das Konto fuhr dadurch
  seit Go-Live faktisch 5 Beine mit dem Kapitalanteil von 6. Lehre:
  **Symbolliste und `symbol_select` beweisen keine Handelbarkeit, nur ein Tick
  tut das.** Memory: `iq_no_stocks_leg_weight_coupling`.
- **Kontostand ≠ Bot-Ergebnis** (neu aus diesem Report-Lauf, 2026-09-14). Das
  FK-Konto sah fünf Tage lang nach "+0,13 %" aus. Am Broker gegengeprüft: der
  Kontostand stand die ganze Woche unverändert bei 100.000,00 $, die gesamte
  Bewegung war der schwebende Gewinn **einer von Hand eröffneten**
  EUR/USD-Position. Sie ist inzwischen ins Minus gedreht. Bemerkenswert ist
  die Asymmetrie dahinter: der Trailing-DD-Kill-Switch der Bridge rechnet auf
  der Konto-Equity **inklusive** dieser fremden Position, ihr
  Offenes-Risiko-Deckel sieht sie dagegen **nicht**. Siehe
  `KW37_2026_performance.md` Punkte 5.1 und 5.11.

## 4. Neues Wissen diese Woche (Papers/Ideen)

**Acht neue PARA-Notizen** — die mit Abstand ergiebigste Research-Woche
bisher, wobei sieben davon aus der eigenen Fehlersuche stammen und nur eine
aus einem externen Paper:

- [[broker-kostenmodell-eurusd]] (09-09) — echte, aus den MT5-Terminals
  gemessene Handelskosten je Broker, als Ersatz für die bis dahin unbelegten
  Kostenannahmen in den Backtest-Engines. Messskript:
  `scripts/measure_broker_spreads.py`, rein lesend.
- [[cls-practical-kostenvalidierung]] (09-13, Status **abgeschlossen**) — das
  Projekt zum Vorfall vom 09-09: Messung, Phase-6-Validierung, Umbau,
  Risikosenkung. Ergebnis: das Bein läuft weiter, aber **auf Bewährung**.
- [[realkosten-und-ausfuehrungs-probe]] (09-10) — neue Dauerverantwortung:
  vier zusätzliche Proben als Pflichtteil von Phase 6, verankert als
  `p6_5`–`p6_8`. Begründung: **jede der vier hat beim CLS-Fall einen realen
  Fehler gefunden, den p6_1–p6_4 nicht gefunden hätten.**
- [[paper-bot-zu-live-bridge]] (09-10) — Standardprozess für den Übergang
  Paper-Bot → Live-Bridge, direkte Folge des `CAPITAL_WEIGHT`-Funds.
- [[bridge-infrastruktur-vergleich]] (09-10) — der Soll-Ist-Vergleich der drei
  Bridges auf Infrastruktur-Ebene (nicht Strategie-Ebene).
- [[cross-asset-momentum-spillover]] (09-09) — Destillat des JPM-Papers
  (Salopek/Tzotchev): Momentum eines Assets als Prädiktor für ein *anderes*.
- [[fx-momentum-spillover]] (09-09) — der Nachbau auf den 7 FX-Majors,
  durch den 8-Phasen-Prozess gelaufen. **Ergebnis: negativ**, kein
  integrierbarer Strategie-Kandidat. Ein sauber dokumentierter negativer
  Befund ist hier ausdrücklich ein Ergebnis, kein verlorener Abend.
- [[agentisches-research-system-und-self-learning-bot]] (09-08) — das in der
  Planungssession geklärte Konzept (autonome Ideen-Findung, Hybrid ML/RL,
  Alpaca Paper-Trading). Bau frühestens in einigen Wochen.

Dazu wurden am 09-07 die **sechs in KW36 entstandenen, aber nie committeten
Notizen** endlich ins Repo geholt ([[edge-card-workflow]],
[[backtest-standard-process]], [[second-brain-methodik]],
[[opening-range-breakout]], [[order-flow-trading]],
[[strategie-backlog-inventar]]) — der im letzten Education-Report notierte
Rückstand ist damit abgearbeitet.

**Ideen-Inbox** — drei neue Einträge diese Woche, alle noch unsortiert:

- **NY-Open ORB komplett von dukascopy lösen** (09-09) — die Entry-Daten
  direkt per `mt5.copy_rates_range()` holen, so wie EKs Fast-Lane es bereits
  tut. Bewusst zurückgestellt: braucht neuen Code + Validierung.
- **Volles 42-Asset-Futures-Universum aus dem JPM-Spillover-Paper** (09-09,
  siehe [[cross-asset-momentum-spillover]]) — Commodities, Aktienindizes,
  US-Treasury-Futures über den aktuellen FX/Gold-Fokus hinaus.
- **Agentisches Research-System + Self-Learning-Bot** (09-07) — siehe oben.

Bemerkenswert: ein vierter Eintrag hat diese Woche seinen **kompletten
Lebenszyklus** durchlaufen. Der "Gegen das Signal"-Check kam am 09-09 rein,
wurde am 09-11 als R-Detektor (`MAX_CONSUMED_R_FOR_ENTRY = 0.50`) gebaut und
am 09-13 aus der Inbox entfernt. Das ist das erste Mal, dass die Ideen-Inbox
nicht nur gesammelt, sondern auch geleert hat — genau so war sie gedacht.

**Unverändert liegen geblieben:** die **14 unverarbeiteten Clippings** in
`knowledge/Clippings/` (Stand seit dem Lint vom 09-09, vorher 12 seit
09-03). Diese Woche kam kein einziges davon durch den CODE-Prozess — was
angesichts der acht selbst erzeugten Notizen verständlich ist, den Stapel
aber weiter wachsen lässt.

## 5. Verbesserungen

- **EK-Portfolio-Bridge grundlegend repariert** (09-10): Kapitalverdünnung
  erstmals wirksam (statt ~8x Übergröße), Mindestlot-Sizing,
  Portfolio-Kill-Switch (`TRAILING_DD_PCT = 0.45`), Einzeltrade-Cap 3 %,
  Risiko-Neukalibrierung gegen Monte Carlo statt gegen freie Optimierung
  (die lieferte CAGR 531 % — und P(MaxDD>40 %) = 32,8 %).
- **Bar-Fenster-Bug behoben** (09-10, `90ee97a`): alle 3 MT5-nativen Beine auf
  EK rechneten auf 5 Stunden alten Bars.
- **Ausführungs-Schutzschicht in allen drei Bridges** (09-11): Pip-Boden
  (5 Pips), R-Detektor (0,50R), Margin-Deckel über `mt5.order_calc_margin()`
  statt selbstgebauter Nominalwerte. CLS-Risiko gesenkt statt erhöht
  (0,25 % → 0,1667 %), weil das Bein allein 40 % des TTP-Drawdown-Budgets zog.
- **Restlaufzeit-Gate + Task-Offsets** (09-09) gegen bereits tote Signale;
  Ingest läuft jetzt **vor** dem Scan statt danach.
- **dukascopy-Hang entschärft** (09-09): Slow-Pfad-Retry von 6x/8s/90s auf
  3x/3s/20s, Worst Case je Bein ~9,7 Min. → ~66 s.
- **Git-Sync-Lücke an der Wurzel behoben** (09-09, `a34cb8a`): gemeinsame
  `Sync-AndPush` fetcht+merged jetzt vor jedem Push, eingebunden in alle 11
  Task-Skripte. Die 64-Commit-Divergenz aus KW36 ist auf 5 geschrumpft.
- **Wochenend-Pause** (09-13, `56d36f7`): sieben Tasks liefen mit 7-Tage-
  Trigger, allein EKs 2-Minuten-Lane ~1.440 Leerläufe pro Wochenende.
  Deklarativ hinterlegt in `scripts/weekend_pause.ps1` (`-Verify`/`-Apply`/
  `-Revert` mit XML-Backups), damit ein neu angelegter Task nicht still wieder
  auf 7 Tage zurückfällt.
- **Morgen-Digest von 4 Telegram-Nachrichten auf 1** (09-11, 16.066 → 1.580
  Zeichen) plus neue Health-Zeilen aus den echten Logs statt nur aus dem
  Dashboard.
- **IQ-Konto auf 5 Beine @ 1/3** (09-13): das brachliegende Sechstel des
  Risikobudgets ist wieder im Einsatz — laut Monte Carlo CAGR 10,7 % → 22,3 %,
  MaxDD 2,2 % → 4,4 % (bewusst die risikofreudigste von vier vorgelegten
  Stufen).
- **Bridge-Risiko-Audit von 9 auf 1 Befund** (09-11), inkl. neuer
  automatischer Drift-Prüfung Bridge ↔ Paper-Bot — gegengeprobt, damit sie
  nicht nur zufällig "OK" sagt.

## 6. Verschlechterungen / offene Probleme

- **🔴 FK Instant Funding handelt seit dem Live-Gang nicht.** Fünf Handelstage
  scharf, 9 Signale, **0 platzierte Orders**, drei Fehlversuche mit drei
  verschiedenen Fehlerbildern (2x `order_send()=None`, 1x `retcode=10016
  "Invalid stops"`). Der gesamte Live-Rollout von 7 Beinen existiert bisher
  nur auf dem Papier.
- **🔴 Kurztakt-Tasks fallen wiederkehrend 1–2 Stunden aus** — inzwischen vier
  belegte Vorfälle, und am 09-11 mit nachweisbarem Schaden: in den zwei
  Fenstern lief der Lake trocken, alle drei Bridges fielen auf Live-dukascopy
  zurück und sammelten dort ihre **kompletten** Tages-Scan-Fehler ein (null in
  allen übrigen Stunden). Ursache weiter unbestätigt. Neu diese Woche: es
  trifft nicht nur Kurztakt-Tasks — der Weekly-Report-Task selbst startete am
  09-13 mit 3h21 Verspätung.
- **🔴 `cls_practical` hat auf EK noch nie eine Order gesendet** — 104
  Scan-Fehler seit 08-31, immer dieselbe Kette (Lake veraltet → Live-Fallback
  → Hang → 90-s-Timeout → Bein fällt aus). Das Bein ist dort faktisch nicht im
  Portfolio, obwohl es mit 0,55 % Risiko/Trade eingeplant ist.
- **Das 35-Minuten-Frischefenster des Data Lake passt nicht zur
  15-Minuten-Kadenz** — es verzeiht genau einen ausgefallenen Ingest-Lauf.
  Gezählt: 774 Lake-Fallbacks bei EK, >1.400 bei Funded, 728 bei FK,
  **ausnahmslos** `LakeStaleDataError`, kein einziges "Datensatz fehlt".
- **Zwei von drei Paper-Zwillingen laufen nicht** (EK Task Disabled seit
  08-31, Challenge nie angelegt). Dadurch lässt sich bei einem schwachen
  Live-Ergebnis nicht unterscheiden, ob es von der *Strategie* oder von der
  *Ausführung* kommt — und genau das ist gerade die offene Frage. Besonders
  unangenehm: `challenge_portfolio/paper_bot.py` hat als Simulation nie einen
  Trade gemacht, wird aber zur Laufzeit von der Echtgeld-Bridge importiert.
- **EK läuft bei 42,6 % Margin für EINE normale Position** (Funded zum
  Vergleich: 7,7 %) — Folge der Kalibrierung vom 09-10, keine Fehlfunktion,
  aber bei 8 Beinen und Tickmill-Hebel 1:30 können zwei bis drei gleichzeitig
  offene Positionen die Margin ausreizen. Der Margin-Deckel steht dort deshalb
  auf 80 % und kann strukturell wenig ausrichten.
- **Ein Broker-seitiger Passwortwechsel legt still alle Bridges eines Kontos
  lahm** (09-13 auf EK passiert) — der Fehler taucht erst im nächsten
  geplanten Lauf auf, nicht beim Wechsel selbst.
- **EKs ORB-Bein riskiert nach der Kalibrierung 0,042 % je Trade** und ist
  damit faktisch wirkungslos (alle fünf ORB-Trades der Woche zusammen: −7,63 €,
  ein einziger OU-Stop-out: −32,23 €).
- **14 Clippings weiterhin unverarbeitet**, unverändert seit dem 09-09-Lint.

## 7. Optimierungsmöglichkeiten

Nach Gewicht sortiert — was diese Woche an Einsicht gebracht hat, ist zum
großen Teil noch nicht in Handlung übersetzt:

1. **FKs Order-Ebene reparieren, bevor irgendetwas anderes an FK passiert.**
   Beide Verdachtsmomente sind in Minuten prüfbar: Kommentarlänge
   (`run_once.py:484` kappt auf 31 statt 16 Zeichen — der Fix existiert auf EK
   bereits zentral in `core/order_send.py`) und die abgelehnte ORB-Order (eine
   `symbol_info`-Abfrage auf `digits`/`trade_stops_level` klärt Rundung und
   Mindestabstand). Solange das offen ist, ist FK eine Echtgeld-Bridge ohne
   Ausführung — und Phase 2 des ORB-MT5-Pfads auf Funded wartet darauf.
2. **Die Ausführungsquote zur ersten Kennzahl machen.** Der Befund "live ≠
   handelt" ist die wichtigste Erkenntnis dieser Woche und hat noch keine
   Anzeige: eine Spalte "letzter echter Entry" in der Statustabelle plus eine
   Signal→Order-Quote je Bein würde genau das sichtbar machen, was fünf Tage
   lang unbemerkt blieb.
3. **Die Gates gegen den Backtest halten.** Wenn das Restlaufzeit-Gate allein
   22 von 24 ORB-Signalen verwirft und dabei systematisch die schnellen
   Verlierer trifft, ist die live gefahrene Strategie nicht mehr die
   getestete. Der saubere Weg ist, die Gates **in den Backtest zu übernehmen**
   und neu zu validieren, statt sie nur live wirken zu lassen — sonst
   optimiert jede weitere Arbeit auf dem kleinen Rest, der durchkommt.
4. **Kurztakt-Task-Ausfälle und Lake-Frischefenster gemeinsam angehen.** Sie
   sind dieselbe Geschichte von zwei Seiten: die Ausfälle erzeugen die
   Staleness, das zu enge Fenster macht sie sofort wirksam. Zwei
   Stellschrauben: Fenster an die Kadenz koppeln (2,5 × Ingest-Intervall statt
   fix 35 Min.) und den Live-Fallback hart deckeln — 90 s Hang für ein Bein,
   das ohnehin nur alle 15 Min. scannt, ist der falsche Tausch.
5. **Mindestens einen Paper-Zwilling wieder anwerfen.** Ohne ihn bleibt die
   Kernfrage dieser Woche (Strategie oder Ausführung?) unbeantwortbar. Steht
   als Entscheidung im Dashboard.
6. **Die Freitags-Commit-Lücke schließen.** Zweite Woche in Folge ist die
   Arbeit des produktivsten Tages erst Tage später im Repo gelandet. Das ist
   kein Datenverlust-Risiko mehr (`Sync-AndPush` läuft), aber es macht die
   Rekonstruktion einer Woche unnötig mühsam — dieser Report musste dafür
   erneut auf Changelog und Datei-Zeitstempel ausweichen.
7. **Den Clipping-Stapel abbauen**, bevor er die dritte Woche übersteht.
