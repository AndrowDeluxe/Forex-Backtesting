# Edge Card (in Arbeit): Key Levels – Umkehr oder Durchlauf

Dieser Entwurf wird schrittweise nach dem [[edge-card-workflow]] mit dem
Nutzer erarbeitet. Begonnen am 09.10.2026, Stand 14.10.2026. Ausgangspunkt
ist der Befund aus [[smh-elite-mikrostruktur]]: Runde Zahlen wirken wie ein
Magnet, nicht wie eine Wand. **Status 16.10.2026: Die Edge Card ist fertig
und vom Nutzer bestätigt.** Die finale Fassung steht am Ende dieser Datei.
Die Abschnitte davor dokumentieren den Verlauf.

**Änderung 16.10. (Nutzer):**
- IS beginnt 01/2016 statt 04/2018.
- OOS läuft auch auf den 4 bekannten Paaren. Bei runden und halben Zahlen
  ist es dort nur Vergleich, kein Beleg.
- Der Tresor bleibt den 6 frischen Paaren vorbehalten.

**Wichtig für den Test:** EURUSD, GBPUSD, USDJPY und AUDUSD haben ihre
Zeiträume ab 04/2023 für **runde Zahlen** bereits gesehen (OOS und Tresor
der Teamaufgabe).
- Runde und halbe Zahlen auf diesen 4 Paaren gelten im OOS nur als
  Vergleich, nicht als Beleg.
- Die übrigen Level-Typen zählen dort im OOS normal.
- Der Tresor läuft nur auf den 6 frischen Paaren.

Gesamte finale Fassung im Wortlaut: [[keylevel-edge-card-final]].

## Phase 0 (bestätigt)
- **Markt:** FX-Majors.
- **Level-Typen:**
  1. runde Zahlen x.xx00 und halbe Zahlen x.xx50,
  2. Open der D1- und H4-Engulfing-Kerze,
  3. Vorwochenhoch und -tief,
  4. Session-Hoch und -Tief.
- **Frage:** kleine Umkehr oder Durchlauf, jeweils im Vergleich zu Schein-Leveln.
- **Kontext und Confirmation:** keine.
- **No-Trade:** Rollover 21–23 UTC und Wochenend-Gaps.

## 01 IDEE (bestätigt 09.10.)
Bestimmte Kursmarken sind für sehr viele Teilnehmer gleichzeitig sichtbar.
An ihnen ist das Verhältnis „zuerst G zurück“ gegen „zuerst G weiter“ nicht
ausgeglichen, anders als an einem beliebigen Kurs im gleichen Abstand.

- Runde Zahlen auf vier Majors halten seltener als Schein-Level. Sie wirken
  wie ein Magnet.
- Beim Engulfing-Open erwarten wir eine Richtung: Das Level hält in
  Engulfing-Richtung.
- Offen ist bei den übrigen Leveln, ob sie halten oder durchgelaufen werden,
  und ob sich das mit der Reaktionsgröße ändert.

Die Level stammen aus Tag, Woche und Session. Die Reaktion wird auf M1 als
Berührung beobachtet und auf M15, H1 und H4 als Kerzenschluss am Level.

**Widerlegt ist die Idee, wenn** sich alle Level-Typen über alle Größen
verhalten wie beliebige Kurse.

## 02 REGEL (bestätigt bis auf markierte Annahmen)

### A. Level
- Runde Zahl = Vielfaches von 0,0100 (JPY: 1,00).
- Halbe Zahl = Vielfaches von 0,0050, das kein Vielfaches von 0,0100 ist.
  Beide gelten immer.
- **Engulfing (D1 und H4):**
  - Die Vorkerze läuft in Gegenrichtung.
  - Die Folgekerze schließt jenseits des Opens der Vorkerze (Körper
    umschließt Körper, Nutzerdefinition 1).
  - Das Level ist das Open der Engulfing-Kerze. Es gilt ab ihrem Schluss
    bis zur ersten Berührung.
  - Höchstdauer 5 Kerzen des Engulfing-Timeframes: **ANNAHME, nicht
    bestätigt.**
- **Tag/Woche:** 17:00–17:00 New York.
  - Vorwochenhoch und -tief gelten die ganze Folgewoche.
- **Sessions (UTC):** Asia 00–08, London 08–13, New York 13–21.
  - Hoch und Tief der zuletzt abgeschlossenen Session.
  - Gültig 24 Stunden ab Sessionende: **ANNAHME, nicht widersprochen.**
- Überschneidungen verschiedener Level-Typen werden markiert.

### B. Frischer Anlauf
Seit das Level gilt (bzw. seit der letzten Berührung) war der Kurs
mindestens G vom Level entfernt, auf der Anlaufseite. Je Level und Größe
zählt nur das erste Ereignis.

### C. Ereignis
- **M1:** Das Bid berührt das Level. Die Messung startet am Level-Preis.
- **M15, H1, H4:** Die Signalkerze erreicht das Level, die Vorkerze schloss
  auf der Anlaufseite.
  - Schluss zurück auf der Anlaufseite = respektiert. Signal gegen den
    Anlauf.
  - Schluss jenseits des Levels = gebrochen. Signal mit dem Anlauf.
  - Die Messung startet am Schlusskurs.

### D. Messung
- Zuerst +G = Treffer, zuerst −G = Fehlschlag.
- Nichts davon im Fenster = unentschieden, bewertet zum Schlusskurs.
- +G und −G in derselben M1-Kerze = Fehlschlag.

| Timeframe | G (Pips) | Fenster |
|---|---|---|
| M1 | 10/20 | 1 Tag |
| M15 | 20/30 | 2 Tage |
| H1 | 30/50 | 5 Tage |
| H4 | 50/100 | 10 Tage |

- D1-Engulfing wird mit den H1- und H4-Kombinationen gemessen, H4-Engulfing
  mit M15 und H1.

### E. Ausschlüsse
Keine Ereignisse 21–23 UTC. Ein Gap über das Wochenende wird zum
Montags-Eröffnungskurs bewertet.

## 03 MECHANISMUS (Entwurf 14.10.)
- **A. Runde und halbe Zahlen (Magnet):**
  - Orders ballen sich an der Zahl, Stops knapp dahinter (Osler 2005).
  - Kurzfristige Händler drücken den Kurs in die Stops.
  - Die ausgelösten Stops beschleunigen den Kurs kurz, bringen aber keine
    neue Information.
  - Folge: Durchstechen ist wahrscheinlich, ein nachhaltiger Weiterlauf
    nicht.
  - Wer verliert: der Stop-Halter.
- **B. Vorwochen- und Session-Hochs/-Tiefs:**
  - Stops liegen hinter offensichtlichen Hochs und Tiefs (externe
    Liquidität), der Kurs wird hingezogen.
  - Offen: Sweep und dann Umkehr, oder echter Ausbruch? (Frage an den
    Nutzer.)
- **C. Engulfing-Open (Wand):**
  - Die Vorkerze lockt Trader an, die Engulfing-Kerze fängt sie.
  - Bei Rückkehr zum Open sind sie bei plus minus null und steigen aus, das
    erzeugt Gegenfluss am Level.
  - Wer den Move verpasst hat, steigt dort neu ein.
  - Folge: Das Level hält in Engulfing-Richtung.
  - Wer verliert: der gefangene Vorkerzen-Trader.

Das ist eine Mechanismus-Hypothese, nicht bewiesen.

### Ergänzt am 14.10. (Nutzer)
- **Teil B hat zwei Szenarien je nach Kontext:**
  - **B1 Sweep und Umkehr:** Die Kerze sticht durch und schließt davor
    (respektiert).
  - **B2 Durchbruch und Retest:**
    - Ein Schluss jenseits des Levels, danach die erste Rückkehr von der
      neuen Seite innerhalb von N Kerzen (Vorschlag N = 5, **ANNAHME**),
      nach einem Abstand von mindestens G.
    - Die Retest-Kerze schließt auf der Durchbruchseite. Signal in
      Durchbruchrichtung.
  - Mechanismus B2 wie bei C: Gefangene „Halten“-Trader steigen bei plus
    minus null aus, Verpasser steigen ein.
- **Neuer Level-Typ: HTF-Pivots.**
  - Klassische Floor-Pivots P, R1/S1, R2/S2 aus der Vortages-, Vorwochen-
    und Vormonatskerze (17:00 New York). **ANNAHME.**
  - Mechanismus wie bei runden Zahlen: frei sichtbar, Orders ballen sich.
- **Stufe 2, Kontext (jeder Faktor einzeln, Richtung vorab festlegen,
  erst dann kombinieren):**
  1. HTF-Struktur mit oder gegen den Anlauf,
  2. Art des Anlaufs (impulsiv oder auslaufend),
  3. Konfluenz mehrerer Level,
  4. Entscheidung am Kerzenschluss (steckt schon in der Ereignisregel),
  5. entgegengesetztes Volumen am Level. Hypothese: mehr verteidigte
     Positionen führen eher zur Umkehr. **Definition offen; FX-Spot hat
     nur Tick-Volumen.**

### Ergänzt am 16.10. (Nutzer): Volumen
Der Nutzer hält alle vier Volumen-Varianten für relevant. Im Coaching:
TradingView Fixed Range Volume Profile vom letzten Hoch bis zum letzten
Tief (die letzte Range), angepasst an den Timeframe.

**Testbar:**
- **FRVP-Nachbau aus Dukascopy-Tick-Volumen.** TradingView nutzt bei FX
  ebenfalls Feed-Tick-Volumen.
  - Range = letztes Swing-Hoch bis letztes Swing-Tief vor dem Ereignis, auf
    dem Signal-Timeframe.
  - Swing = k Kerzen beidseitig, Vorschlag k = 3 (**ANNAHME**). Ein Swing
    gilt erst nach Schluss der k Folgekerzen (kein Lookahead).
- **COT wöchentlich als grober Kontext.**

**Heute noch nicht:** Open Interest der CME-Futures bzw.
Retail-Sentiment, Orderbuch.

**„Viel entgegengesetztes Volumen“ (Nutzer: Variante 1, 16.10.):** Das
Level liegt in einer High-Volume-Zone, wenn eine von zwei Bedingungen gilt:
- Die Preisstufe des Levels gehört zu den oberen 20 % nach Volumen
  (Stufenbreite G/10).
- Oder der POC liegt höchstens G/4 vom Level entfernt.

Die Schwellen sind eine **ANNAHME**. Richtung: High-Volume-Zone → eher
Sweep und Umkehr; Low-Volume-Zone → eher Durchlauf bzw. Durchbruch und
Retest.

## 04 GEGENPROBE (Entwurf 16.10.)
- **Schein-Level** (zufällig verschoben) je Level-Typ gleich gut →
  Sichtbarkeit und Orderballung sind nicht der Grund.
- **Stop-Mechanismus:** Direkt hinter dem Level ist der Kurs nicht
  schneller als hinter einem Schein-Level, oder er beschleunigt schon davor
  → die Stop-Erklärung ist falsch.
- **Gefangene Trader (Engulfing):**
  - Das Open einer normalen Kerze hält gleich gut.
  - Kerzenmitte oder Close halten gleich gut wie das Open.
  - Eine kleine Vorkerze hält gleich gut wie eine große.
  → In allen drei Fällen ist die Falle bzw. der Plus-minus-null-Punkt nicht
  der Grund.
- **Retest an Schein-Leveln** gleich gut → nur Ausbruchs-Momentum, nicht
  levelspezifisch.
- **B2 und C verhalten sich grundverschieden** → die gemeinsame Erklärung
  „Gefangene steigen aus“ ist unwahrscheinlich.
- **Pivots aus der vorletzten Kerze** gleich gut → Sichtbarkeit ist nicht
  der Grund.
- **Volumen:**
  - Level in High-Volume-Zonen halten nicht häufiger als in Low-Volume-
    Zonen → Volumen wirkt nicht.
  - Beliebige Preise in High-Volume-Zonen halten gleich gut → reiner
    Volumen-Effekt, kein Key-Level-Effekt.
- **Kontext:**
  - Gegen die HTF-Struktur gibt es nicht häufiger einen Sweep → der Kontext
    erklärt nichts.
  - Reiner HTF-Trendhandel ohne Level ist gleich gut → die Level sind
    überflüssig.
- **Effekt nur in einer von 40 Kombinationen** aus Timeframe und Größe,
  nicht bei den Nachbargrößen → Zufall.
- **News- und Hochvola-Phasen** (Nutzer 16.10.) wirken genauso wie ruhige
  Phasen → die Orderballung erklärt den Effekt nicht. Diese Ereignisse
  werden als Kontrollgruppe mitgemessen, nicht verworfen.

### Ausschlüsse ergänzt (16.10., Nutzerhinweis)
Bei News, Makro-Schocks oder starker Vola werden Level oft ignoriert.
- **News-Fenster:** 30 Minuten vorher bis 2 Stunden nachher (bei H4 der
  ganze Tag) um High-Impact-Termine einer der beiden Währungen:
  - FRED: US-CPI, NFP, Retail Sales, GDP,
  - Eurostat,
  - FOMC, EZB, BoE, BoJ, RBA, BoC, SNB.
  - Bei Nicht-US-Daten ohne Uhrzeit: der ganze Tag.
- **Hochvola-Regime:** 20-Tage-Vola über dem 90. Perzentil des Vorjahres
  (Werte bis zum Vortag).
- Fenster und Perzentil sind eine **ANNAHME**.
- Mechanismus: Der Informationsfluss übersteigt die Orders am Level.

## 05 TEST (Entwurf 16.10.)
- **Daten:**
  - Dukascopy M1 Bid (UTC) mit Tick-Volumen, daraus M15/H1/H4/D1/W1.
  - Kosten je Paar (TTP/IQ).
  - Kalender und COT aus dem Repo.
- **Aufteilung:**
  - IS 04/2018–03/2023: 4 bekannte Majors + frische Paare.
  - OOS 04/2023–09/2025: nur frische Paare.
  - Tresor 10/2025–heute: nur frische Paare.
  - Optional Forward.
- **Frische Paare (Vorschlag):** USDCAD, USDCHF, NZDUSD, EURJPY, GBPJPY,
  EURGBP.
- **Fallzahl:** alle Regel-Ereignisse; eine Kombination nur bei ≥ 100
  IS-Ereignissen.
- **Stufe 1 weiter, wenn:**
  - t > 3 gegen Schein-Level,
  - die Nachbargrößen dasselbe Vorzeichen haben,
  - der 1:1-Trade netto positiv ist (bei G = 10 sind ~56 % Trefferquote
    nötig).
- **Stufe 2:** Kontext je Faktor einzeln. Versuche zählen, Deflated Sharpe
  ausweisen.
- **Heute noch nicht:** Open Interest bzw. Sentiment, Orderbuch, Uhrzeiten
  für Nicht-US-Daten.

## 05 TEST: offen


---

## FINALE EDGE CARD (16.10.2026)

Die finale Fassung steht im Chat vom 16.10.2026 und folgt exakt der Struktur
aus [[edge-card-workflow]]. Ihre Inhalte entsprechen den Abschnitten oben,
mit diesen Fixierungen:

- **Split:**
  - IS 01/2016–03/2023: 10 Paare, nämlich EURUSD, GBPUSD, USDJPY, AUDUSD
    sowie die frischen USDCAD, USDCHF, NZDUSD, EURJPY, GBPJPY, EURGBP.
  - OOS 04/2023–09/2025: alle 10 Paare. Runde und halbe Zahlen auf den 4
    bekannten Paaren nur als Vergleich.
  - Tresor 10/2025–heute: nur die 6 frischen Paare.
- **Pivots:** klassisch, P = (H + L + C) / 3, R1 = 2P − L, S1 = 2P − H,
  R2 = P + (H − L), S2 = P − (H − L). Berechnet aus D1, W1 und Monat.
- **Kontext-Richtungen (vorab):**
  - gegen die Struktur → Sweep; mit der Struktur → Durchbruch und Retest,
  - impulsiver Anlauf → Durchbruch; auslaufender Anlauf → Sweep,
  - Konfluenz → stärkere Reaktion,
  - High-Volume-Zone → Umkehr; Low-Volume-Zone → Durchlauf.
- **Annahmen pauschal bestätigt:** Engulfing 5 Kerzen, Session 24 Stunden,
  Retest 5 Kerzen, Swing k = 3, High-Volume-Zone = obere 20 % bzw. POC ≤
  G/4, News-Fenster −30 Minuten bis +2 Stunden, Hochvola = 90. Perzentil.

**Nächster Schritt:**
1. M1-Daten 2016–2017 für die 4 Paare nachladen, die 6 frischen Paare
   2016–heute neu laden (`smh_microstructure/data.py`, FIRST_YEAR = 2016).
2. Neuen Lock registrieren.
3. Stufe 1 rechnen.


## Ergebnis Stufe 1 (16.10.2026, nur IS 01/2016–03/2023, 10 Paare)
Code: `keylevels/` und `scripts/research_keylevels.py`. Ergebnisse in
`keylevels/results/stage1_is_report.csv`. Lock `keylevels_v1`: 226 Versuche
gezählt, OOS und Tresor versiegelt. Live-Protokoll auf der Notion-Seite
„Backtest: Key Levels – Stufe 1 (IS)“.

- **Der Magnet ist bestätigt und breit.** Gemessen ist die Umkehrquote bei
  M1-Berührung und G = 10, jeweils gegen Schein-Level:
  - Vorwoche 43,3 % gegen 48,5 % (z −4,5),
  - Session 47,4 % gegen 49,5 % (z −7,6),
  - runde Zahl 48,2 % gegen 50,2 % (z −7,8),
  - halbe Zahl 48,9 % gegen 50,2 % (z −5,1).

  In 38 von 40 Paar×Level-Kombinationen ist das Vorzeichen negativ, in beiden
  IS-Hälften gleich stark. Je sichtbarer das Level, desto stärker der Sog.
- **Pivots sind kein Key Level.** Sie verhalten sich wie Schein-Level und wie
  die Pivots der vorletzten Kerze.
- **Engulfing-Open hält nicht.** Es hält nicht besser als ein Schein-Level
  und nicht besser als das Open einer normalen Kerze. Die Falle-These ist im
  IS nicht gestützt.
- **HTF-Kerzenschluss (respektiert/gebrochen):** kein Effekt. Retests sind zu
  selten.
- **News und Hochvola:** Die Level halten dort noch schlechter. Das bestätigt
  die Nutzerbeobachtung, mit Ausnahme der Vorwoche.
- **Weitergegeben wird nur:** Vorwochenhoch/-tief, M1, G = 20, Richtung
  Durchlauf. Netto +0,016 G je Trade (t 0,9). Bei G = 10 fressen die Kosten
  den Magnet auf.
- **Nächster Schritt:** Stufe 2 (Kontext einzeln) nur auf dieser Zelle.


## Ergebnis Stufe B: Doppel-BOS-Einstieg (18.10.2026, nur IS)
Nutzeridee: am Level zwei BOS abwarten (A: 2× M5, B: M15 + M5), Einstieg als
Stop-Order beim zweiten BOS, beide Richtungen, Volumen als Varianten (HVN,
Druck-Näherung). Code: `keylevels/bos.py`, `keylevels/volume.py`, Befehle
`bos-events` und `bos-report`. Ergebnisse in `keylevels/results/bos_*`. Die
Rechnung wurde von Hand und automatisch geprüft. Notion-Seite „Backtest: Key
Levels – Doppel-BOS-Einstieg (IS)“.

- **0 von 240 Zellen bestehen.** Die mittlere Trefferquote liegt bei 50,2 %
  (Schein-Level 50,3 %), mit HVN bei 50,7 % (50,3 %), mit Druck bei 51,3 %
  (51,2 %).
- Der Anteil der Zellen mit z > 2 liegt bei 2,1 %, die Zufallsquote bei
  2,3 %. Auch die Doppel-BOS-Folge ohne Level trifft nur etwa 50 %.
- MFE ≈ MAE (Median-Verhältnis 1,03). Eine SL/TP-Optimierung auf diesem
  Einstieg würde nur Rauschen anpassen.
- **Deutung:** Der Magnet wirkt bei der Berührung. Bis zur Füllung des
  zweiten BOS vergehen im Median etwa 105 Minuten, dann ist er verbraucht.
- **Schwäche im Design:** Für die HVN-Zellen gibt es keine Vergleichsgruppe
  „ohne Level“, weil Zufallszeitpunkte kein Level haben. Dort ist nur der
  Vergleich mit Schein-Level möglich. Für das Urteil spielt das keine Rolle,
  denn keine HVN-Zelle hat gegen Schein-Level z > 3.
- **Versuche gesamt:** 466 im Lock `keylevels_v1`.

## Vier Fragen (Stand 18.10.)
1. **Warum verdient es Geld?** Durch den Magnet an sichtbaren Leveln: Stops
   hinter dem Level ziehen den Kurs durch. Das ist belegt, aber klein.
2. **Wo verliert es am meisten?** Bei kleinen G (10 Pips): Die Kosten fressen
   den Vorteil. Nach einer Bestätigungsphase (Doppel-BOS) gibt es keinen
   Vorteil mehr.
3. **Was ist dort anders?** Der Zeitpunkt. Der Vorteil sitzt an und kurz vor
   der Berührung, nicht Stunden danach.
4. **Welche eine Regel könnte helfen?** In Richtung Level handeln, bevor es
   berührt wird (Magnet-Trade). Neue Hypothese, noch ungetestet, in der
   Ideen-Inbox.


## Ergebnis Stufe C: Magnet-Trade (19.10.2026, nur IS)
Einstieg vor dem Level, in Richtung Level (Regeln 31–34). Code
`keylevels/magnet.py`, Befehle `magnet-events` und `magnet-report`.
Ergebnisse in `keylevels/results/magnet_*`. Etwa 917.000 Einstiege.

**Geprüft:** 600 Stichproben, unabhängig nachgerechnet, 0 Abweichungen.

**Messregel korrigiert vor dem Lauf:** Ein Stop in der Füll-Minute wurde
fälschlich gezählt, obwohl das Extrem vor der Füllung lag (9,8 %). Jetzt
entscheidet in der Füll-Minute nur der Schluss. Danach liegen die
Schein-Level exakt auf der Zufallsquote.

Dieselbe Regel steckte im Doppel-BOS-Test, dort aber nur bei 0,5–4,5 % der
Fälle und bei allen Gruppen gleich. Das Urteil bleibt.

**Ergebnis: 0 von 16 Zellen.** Die Erreich-Quote gegen Schein-Level:

| Level | Ziel Level (1:1), D = 10 | z |
|---|---|---|
| Vorwoche | 49,7 % gegen 52,5 % | −2,5 |
| Session | 48,6 % gegen 50,2 % | −5,7 |
| runde Zahl | gleich | +0,1 |
| halbe Zahl | etwas weniger | −1,8 |

- Einziger Ausreißer: runde Zahl, Ziel hinter dem Level. z = +3,0 bei
  D = 10 und +2,4 bei D = 20. Netto liegt er bei −0,18 D, die Kosten sind
  größer als der Effekt.
- Versuche gesamt: 482.

## Gesamtfazit Key Levels (Stand 19.10., nur IS)
Der Magnet existiert nur **ab** der Berührung: Ein berührtes Level wird
öfter durchstoßen als ein beliebiger Kurs.

- **Vorher** zieht nichts (Stufe C).
- **Nach einer Bestätigung** ist es vorbei (Stufe B).
- **Im kurzen Fenster dazwischen** ist der Effekt zu klein für Taker-Kosten
  (Stufe 1).

Kein Kandidat darf OOS oder Tresor öffnen.

**Praktischer Nutzen für das diskretionäre Trading:** Stops knapp hinter
offensichtlichen Leveln werden überdurchschnittlich oft abgeholt.
Gemeint sind Vorwoche, Session, runde Zahl. Das ist ein Hinweis für die
Stop-Platzierung, noch kein Edge.
