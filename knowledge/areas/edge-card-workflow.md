# Area: Edge-Card-Workflow (Strategie → falsifizierbare Ausgangsthese)

Laufende Verantwortlichkeit ohne Enddatum -- Prozess für den Fall, dass der
Nutzer eine **bereits bestehende, händisch gebacktestete/getradete
Strategie** so tief auseinandernehmen will, dass am Ende eine vollständige,
klare, falsifizierbare und später statistisch testbare Ausgangsthese steht
("Edge Card"). Nutzer-Vorgabe, vollständig übernommen am 2026-09-05.

**Abgrenzung zu [[backtest-standard-process]]**: Der Edge-Card-Workflow
läuft VOR dem 8-Phasen-Backtest-Prozess -- er liefert die präzise,
falsifizierbare These (inkl. Testdesign-Skizze in Feld 05), auf der der
eigentliche Backtest/die Robustheitsprüfung (Phase 6 dort) erst aufbaut.
Nicht verwechseln: Hier wird NICHT gebacktestet, sondern die Idee vor dem
Backtest sauber formuliert.

## Konkrete Verzahnung mit den 8 Phasen (Nutzer bestätigt 2026-09-05)

Klare Abgrenzung nach Ausgangspunkt der Strategie: **Papers/Dokumente**
laufen unverändert durch den vollen 8-Phasen-Prozess (Phase 1-3 Recherche/
Sichtung/Screening bleiben dafür bestehen). Der Edge-Card-Workflow greift
NUR bei **händisch entwickelten/getradeten Strategien** (Ausgangspunkt:
eigene Beobachtung/Erfahrung, kein Paper) -- dort ersetzt die Edge Card
die Phasen 1-3, weil Idee und Plausibilitätsprüfung bereits über Phase 0 +
Feld 01-04 laufen. Ab Phase 4 geht es im bestehenden Prozess weiter:

- **Feld 02 REGEL → Phase 4 (Vertiefung)**: die Regel-Sequenz aus der
  Edge Card ist die 1:1-Spezifikation für das neue Backend-Package --
  genau die Rolle, die im bestehenden Prozess sonst die Paper-Regeln
  einnehmen.
- **Feld 05 TEST (Datenquelle/Zeitraum/Fallzahl) → Phase 4 + Phase 6**:
  legt fest, mit welchen Daten das Package in Phase 4 gebaut wird und
  über welchen Zeitraum/welche Marktphasen in Phase 6 geprüft wird.
- **Feld 04 GEGENPROBE → Phase 6 (Robustheit)**: die aus den Gegenproben
  abgeleiteten Kontrollgruppen (Feld 05 "Vergleich") werden zusätzlich zu
  Walk-Forward/Monte-Carlo/Kosten-Sensitivität als eigene Ablations-Tests
  gefahren -- z.B. "vollständige Sequenz vs. ohne Manipulation" als
  weiterer Robustheits-Check neben dem Out-of-Sample-Split. Das ist der
  eigentliche Mehrwert der Verzahnung: die Gegenprobe ist nicht nur
  Theorie, sie wird zum konkreten Test.
- **Phase 5 (Kombination mit vorhandenen Bausteinen)** bleibt unverändert
  bestehen, kann aber durch No-Trade-Bedingungen aus Phase 0/Feld 02
  motiviert sein.
- **Phase 7 (Dokumentation)**: die fertige Edge Card wird Teil der
  Dokumentation -- verlinkt aus der resultierenden `resources/`-Notiz
  bzw. `app_pages/*.py`-Seite, nicht separat gepflegt.

Nutzerentscheid 2026-09-05: diese Zuordnung passt, Papers/Dokumente bleiben
davon unberührt beim bisherigen 8-Phasen-Prozess.

## Meta-Regel: Claude erfindet keine neue Strategie

Aufgabe ist NICHT, dem Nutzer eine neue Strategie zu bauen. Aufgabe ist,
seine bestehende Strategie gemeinsam mit ihm so tief zu zerlegen, dass eine
vollständige, klare, falsifizierbare und später testbare Ausgangsthese
entsteht. Es wird in exakt diesen 5 Feldern gearbeitet:

01 IDEE -- 02 REGEL -- 03 MECHANISMUS -- 04 GEGENPROBE -- 05 TEST

Schritt für Schritt, NICHT direkt zum fertigen Ergebnis springen.

## Grundregeln

1. **Nichts erfinden.** Reichen die Informationen für einen Punkt nicht,
   konkret sagen was fehlt + gezielte Rückfrage stellen. Plausible
   Hypothesen sind erlaubt, aber ausdrücklich als Hypothese kennzeichnen,
   nie als bewiesene Tatsache.
2. **Nutzer-Begriffe und -Definitionen verwenden**, nicht eigene
   Marktlogik unterschieben. Begriffe wie HTF, LTF, Internal/External
   Liquidity, BOS, Manipulation, Inducement, Trap, Invalidierung,
   Protected High/Low, Sweep etc. so übernehmen wie der Nutzer sie
   definiert -- bei Uneindeutigkeit nachfragen.
3. **Strikt unterscheiden zwischen**:
   - BEOBACHTUNG -- Was sehen wir?
   - REGEL -- Wann genau liegt die Situation objektiv vor?
   - MECHANISMUS -- Warum könnte genau diese Situation einen Vorteil
     erzeugen?
   - GEGENPROBE -- Was müsste passieren, damit die Erklärung wahrscheinlich
     falsch ist?
   - TEST -- Wie könnten wir die Hypothese später fair prüfen?
4. **Ein Backtest ist KEIN Mechanismus.** "Funktioniert im Backtest",
   "Kurs reagiert dort oft", "hohe Winrate", "Institutionen machen das"
   reichen für Feld 03 nicht. Der Mechanismus muss erklären, WARUM
   Marktteilnehmer in dieser Situation wiederholt ein bestimmtes Verhalten
   zeigen könnten.
5. **Keine Scheingenauigkeit.** Ist der konkrete Marktteilnehmer nicht
   bekannt, das nicht behaupten. "Unsere Hypothese ist, dass ..." statt
   "Banken machen hier immer ...".
6. **Kaskadierende Updates.** Jede neue Information des Nutzers kann
   mehrere Felder betreffen -- z.B. ändert eine REGEL-Bedingung ggf. auch
   IDEE, MECHANISMUS, GEGENPROBEN und TESTDESIGN. Alle logischen Folgen
   automatisch mitziehen, nicht nur das direkt angesprochene Feld.

## Phase 0 -- Strategie verstehen

Bevor die Edge Card ausgefüllt wird: eigene Zusammenfassung der Strategie
liefern (aus Nutzerbeschreibung, Screenshots, PDFs, Regeln, Daten --
vollständig einbeziehen was hochgeladen wird), mindestens getrennt nach:

Markt/Asset, HTF-Kontext, relevante Struktur, relevante Liquidität,
Bedingungen vor dem Setup, Confirmation, Entry, Invalidierung, Stop,
Target, No-Trade-Bedingungen, Execution-Timeframe.

Danach fragen: "Ist das eine korrekte Beschreibung deiner Strategie oder
muss etwas angepasst werden?" Erst nach Bestätigung weiter zu Feld 01.

## 01 IDEE

Leitfrage: "Was glauben wir ursprünglich beobachtet zu haben?" -- NICHT
die fertige Entry-Regel, sondern die Marktbeobachtung, aus der die
Strategie entstanden ist. Herausarbeiten: Ausgangszustand, normales
Marktverhalten in diesem Zustand, was sich verändert, die ungewöhnliche
Diskrepanz/Sequenz, welche HTF-/LTF-Ebenen wirklich zur Beobachtung
gehören, was weiterhin passieren darf ohne die Idee zu invalidieren, was
NICHT mehr passieren darf, welche Struktur/Liquidität/welches High-Low
exakt relevant ist. Ausführlich und präzise formulieren, nicht künstlich
kürzen wenn dadurch Logik verloren geht.

## 02 REGEL

Leitfrage: "Wann genau liegt diese Situation vor?" -- komplette Sequenz
Schritt für Schritt, nur die tatsächlich relevanten Punkte aus:
Ausgangskontext, notwendige HTF-Struktur, erlaubte Bewegungen,
verbotene/entscheidende Veränderung, relevante Liquidität, relevante
Manipulation, notwendiger BOS, relevantes High/Low, Confirmation,
Trap/Invalidierung, Übergang zur Execution, Entry, Invalidierung, Target.

Jede Formulierung so konkret, dass ein anderer Trader ohne Rückfrage
dieselbe Situation im Chart markieren könnte. Ungenaue Begriffe ("relevantes
High", "erstes Low", "Manipulation") zur exakten Definition zwingen.
Präzisions-Beispiel: nicht "Das relevante Low wird gebrochen", sondern "Das
erste Low, dessen Move das zuvor definierte manipulierte HTF High aus dem
Markt genommen und dadurch den ersten bullishen Internal BOS erzeugt hat,
wird anschließend aus dem Markt genommen."

## 03 MECHANISMUS

Leitfrage: "Warum könnte genau diese Sequenz einen Vorteil erzeugen?"
Schritt für Schritt aus der Strategie herausbauen, insbesondere: Wer wird
möglicherweise induced? Warum bekommt dieser Marktteilnehmer einen Grund
sich zu positionieren? Welche Marktinformation sieht weiterhin
bullish/bearish aus? Wo entsteht eine Diskrepanz zwischen interner und
externer Struktur? Wer positioniert sich anschließend? Wer könnte später
trapped sein? Welche Struktur/Liquidität/Invalidierung nimmt diesen
Marktteilnehmer wieder aus dem Markt? Warum könnte daraus eine Bewegung
entstehen?

HTF und LTF strikt auseinanderhalten -- ein High/Low aus dem HTF-Kontext
nicht nachträglich als beliebiges LTF-High uminterpretieren. Mechanismus
als Kette formulieren (Beispiel-Schema, nicht 1:1 übernehmen: HTF Sellers
Induced → External Low Respect → Buyers Induced → Buyers Trapped → erst
danach Confirmation/Execution). Abschließend ausdrücklich: "Das ist unsere
Mechanismus-Hypothese. Sie ist noch nicht bewiesen."

## 04 GEGENPROBE

Leitfrage: "Welche Beobachtung würde zeigen, dass unsere Erklärung
wahrscheinlich falsch oder zumindest unvollständig ist?" NICHT einfach
"Verliert die Strategie Geld?" -- die Gegenprobe greift den angenommenen
MECHANISMUS an, nicht nur die Performance. Für jeden wichtigen
Mechanismus-Baustein überlegen: Was wäre, wenn dieser Bestandteil fehlt?
Was wäre beim Gegenteil? Was wäre, wenn ein allgemeineres Signal genauso
gut funktioniert? Was wäre, wenn das angeblich relevante HTF-Level gar
nicht relevant ist? Was wäre, wenn ein beliebiges LTF-Level dieselben
Ergebnisse bringt? Was wäre, wenn das Trap-Event keinen zusätzlichen
Informationswert liefert? Was wäre, wenn die erwartete External-Struktur
doch fortgesetzt wird? Was wäre, wenn die Performance auch ohne den
angenommenen Auslöser entsteht?

4-8 konkrete, auf die tatsächliche Ausgangsthese bezogene Gegenproben.
Grundsatz: "Eine gute Gegenprobe greift nicht nur die Performance an. Sie
greift die angenommene Ursache an."

## 05 TEST

Leitfrage ausschließlich: "Wie müssten wir diese Hypothese später fair
testen?" -- Backtest an dieser Stelle NICHT zwangsläufig durchführen,
nur Testdesign definieren:

- **Datenquelle**: welche Daten, welche Timeframes, OHLC oder Tick,
  zusätzliche Daten nötig, was ist noch unbekannt.
- **Zeitraum**: welche Marktphasen müssen enthalten sein, wie wird eine
  reine "schöne Phase" vermieden, was muss vor Testbeginn fixiert werden.
- **Fallzahl**: wie entstehen Fälle objektiv aus den Regeln (kein
  Cherry-Picking), alle passenden Situationen müssen erfasst werden.
- **Vergleich/Kontrollgruppen**: direkt aus den Gegenproben in Feld 04
  abgeleitet (z.B. vollständige Sequenz vs. ohne bestimmten HTF-Zustand,
  ohne External-Low-Respect, ohne Manipulation, beliebiges statt
  spezifischem HTF-High, ohne Origin-Low, ohne Trap, mit/ohne
  Confirmation, mit/ohne Execution-Filter -- nur was zur jeweiligen
  Strategie passt).

Noch keine Ergebnisse erfinden.

## Arbeitsweise im Gespräch

Wirklich Schritt für Schritt. Fehlt ein wichtiger Punkt: EINE konkrete
Frage stellen, auf Antwort warten, Antwort verarbeiten, automatisch alle
betroffenen Felder aktualisieren, dann nächste Frage. Bei eigener
plausibler Erklärung: "Die logischste Hypothese wäre aus meiner Sicht ..."
+ kurze Begründung + Rückfrage ob das zur Strategie passt. Korrigiert der
Nutzer etwas, die Korrektur vollständig übernehmen und alle logischen
Folgen anpassen (siehe Grundregel 6).

## Qualitätscheck vor Abschluss

Vor Ausgabe der finalen Edge Card selbst prüfen:

- Ist die IDEE wirklich eine Beobachtung, keine fertige Entry-Regel?
- Ist die REGEL objektiv genug, dass jemand anderes dieselben Situationen
  finden könnte?
- Sind HTF und LTF sauber getrennt?
- Ist jedes relevante High/Low exakt definiert?
- Ist der MECHANISMUS eine plausible Ursache, keine reine Beschreibung?
- Sind Hypothesen klar von bewiesenen Tatsachen getrennt?
- Greifen die GEGENPROBEN wirklich die Ursache an?
- Leiten sich die Kontrollgruppen im TEST direkt aus den Gegenproben ab?
- Wurde irgendwo etwas angenommen, das der Nutzer nie gesagt hat?
- Wurden alle späteren Änderungen konsequent durch die komplette Logik
  gezogen?

Bei offenen Punkten zuerst daran weiterarbeiten, nicht vorzeitig
abschließen.

## Finale Ausgabe -- Format

Kein Design, keine Tabellen, keine Marketing-Sprache -- schlicht wie ein
sauber geschriebenes Textdokument, exakt in dieser Struktur:

```
EDGE CARD

[Markt / Strategie]

Vollständige Ausgangsthese

01 IDEE
[Vollständige finale Formulierung]

02 REGEL
1. ...
2. ...
...
Merksatz: [falls sinnvoll]

03 MECHANISMUS
1. ...
2. ...
...
Wichtig: Das ist eine Mechanismus-Hypothese. Wir behaupten noch nicht,
dass sie bewiesen ist.

04 GEGENPROBE
• ...
• ...
...
Kern: Eine gute Gegenprobe greift nicht nur die Performance an. Sie
greift die angenommene Ursache an.

05 TEST
Datenquelle: ...
Zeitraum: ...
Fallzahl: ...
Vergleich: ...
Heute noch nicht: ...

Ergebnis: Eine vollständige, falsifizierbare und testbare Ausgangsthese.
```

Keine relevante Logik kürzen, nur damit die Edge Card schöner aussieht --
bei komplexer Strategie darf die Edge Card ausführlich sein. Ziel ist
nicht eine schöne Zusammenfassung, sondern eine Formulierung präzise
genug, dass Research, Datenerhebung, Backtest, Validation, Robustheit und
später Live-Monitoring sauber darauf aufbauen können.
