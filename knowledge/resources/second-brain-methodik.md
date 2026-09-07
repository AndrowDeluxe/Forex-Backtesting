# Second-Brain-Methodik (Meta-Wissen über dieses System selbst)

Anders als die übrigen `resources/`-Dateien: kein Trading-Thema, sondern
Wissen über den Aufbau/die Pflege von `knowledge/` selbst. Hierher gehören
Video-/Artikel-Funde zu Second-Brain-Methodik, Claude-Workflow-Tricks etc.

## Jonas Keil: "Der einfachste Einstieg in Second Brains!"

**Capture**
- Quelle/Link: https://www.youtube.com/watch?v=MN7itWrUlic (referenziert
  darin: Karpathys "LLM Wiki"-Gist, https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- Erfasst am: 2026-09-01
- Weg: Obsidian Web Clipper -> `knowledge/Clippings/Der einfachste Einstieg
  in Second Brains!.md` (Rohdatei bleibt dort unverändert liegen -- passt
  zufällig genau zu Karpathys unten beschriebenem Raw/Wiki-Split:
  `Clippings/` kann als De-facto-RAW-Ordner für web-geclippte Quellen
  dienen, dieser Eintrag hier ist der destillierte WIKI-Teil davon)

**Organize**
- Thema/Tags: Second-Brain-Aufbau, Claude-Workflow
- Verwandte Notizen: [[README]] (unsere eigene PARA/CODE-Struktur)

**Distill**
- Kernthese: Ein Second Brain ist simpel ein Ordner mit Dateien (kein
  Spezial-Tool nötig), strukturiert nach Karpathys drei Tricks: (1)
  Raw/Wiki-Split -- Rohnotizen werden von der KI nie verändert, nur
  destilliertes Wissen landet im "Wiki"-Teil; (2) die KI selbst ist der
  Bibliothekar (pflegt/synthetisiert, nicht der Nutzer manuell); (3) eine
  `CLAUDE.md`/`AGENTS.md` als Betriebsanleitung, die JEDE Session zuerst
  liest.
- Abgleich mit unserem Stand: Trick 2 und 3 sind bei uns bereits 1:1
  umgesetzt (`CLAUDE.md` + Claude pflegt `DASHBOARD.md`/`CHANGELOG.md`
  automatisch). Trick 1 (Raw/Wiki-Split) haben wir NICHT als expliziten
  Ordner (`raw/` vs. `wiki/`), sondern implizit über den CODE-Prozess
  (Capture -> Distill in `resources/<thema>.md`) und jetzt zufällig auch
  über `Clippings/` als Raw-Ablage für Web-Clips.
- Zwei zusätzliche, bei uns noch nicht explizit übernommene Punkte:
  1. **Kontextfenster-Hygiene**: Video empfiehlt, den Chat-Kontext nie über
     ~300k Token laufen zu lassen -- ein sehr langer Chat ist ein Symptom
     für ein schlecht gepflegtes Second Brain (Wissen sollte im Wiki
     stehen, nicht im Chatverlauf mitgeschleppt werden).
  2. **Live-Daten NICHT statisch im Wiki speichern**, sondern als Verweis
     auf die Quelle (Connector/Live-Lookup) -- exakt das Prinzip, das wir
     schon mit dem Split DASHBOARD.md ("was läuft gerade" -- Live-Stand)
     vs. `resources/` (destilliertes, stabiles Wissen) verfolgen, hier
     nochmal von außen bestätigt.
- Empfohlene Wartungsroutine: eine geplante, wiederkehrende Aufgabe
  ("Routine"), bei der die KI das Wiki regelmäßig durchgeht (neue Dateien,
  abgelaufene Fristen, veraltete Einträge) -- entspricht in etwa unserem
  Lint-Check (`CLAUDE.md` Regel 6), aber dort bisher nur "auf Zuruf oder
  nach mehreren Wochen", nicht als geplante Aufgabe automatisiert.

**Express**
- Kein Backtest-Bezug (Meta-Thema), daher kein "bestätigt/widerspricht"-Schritt.
- Zwei mögliche Ergänzungen für `CLAUDE.md`/`DASHBOARD.md` identifiziert
  (Kontextfenster-Hygiene als explizite Regel; Lint-Check als geplante statt
  Zuruf-Aufgabe via `schedule`/`loop`-Skill) -- **nicht eigenmächtig
  übernommen**, da eigene Annahme statt expliziter Anweisung. Als offener
  Punkt in `DASHBOARD.md` unter "Braucht deine Bestätigung" vermerkt.

---

## Torben Platzer: "Claude nutzen wie die Top 1 %: Schritt-für-Schritt-Anleitung"

**Capture**
- Quelle/Link: https://www.youtube.com/watch?v=sAQdRSqXxXQ
- Erfasst am: 2026-09-01, verarbeitet: 2026-09-02
- Weg: Obsidian Web Clipper -> `knowledge/Clippings/Claude nutzen wie die
  Top 1 % Schritt-für-Schritt-Anleitung.md`

**Organize**
- Thema/Tags: Claude-Workflow, Connectors, Projects, Skills
- Verwandte Notizen: [[README]], Jonas-Keil-Eintrag oben (gleiche Datei)

**Distill**
- Kernthese: Ein allgemeiner Praxis-Guide zu den Claude-Desktop-Bereichen
  (Chat/Cowork/Code), Connectors (Drive, Gmail, GitHub, Community-MCP für
  Echtzeitdaten, Chrome-Extension für autonome Browser-Steuerung),
  Projects (fester Kontext-Workspace pro Thema) und Skills (gespeicherte
  Abläufe, automatisch getriggert statt manuell zitiert).
- Für uns direkt relevant, weil es *unser* Setup bestätigt/einordnet:
  1. **Chrome-Extension/Browser-Steuerung** ist bei uns kein Thema (wir
     arbeiten repo-lokal über Claude Code, keine Web-Recherche-Workflows).
  2. **Projects mit gesperrter Web-Recherche für Domänenwissen**: der
     Ersteller sperrt in seinem Projekt explizit, dass Claude für
     Social-Media-Strategiefragen im Netz nach "Erfolgsfaktoren" sucht,
     weil das fremdes/unbekanntes Sekundärwissen einschleust statt der
     eigenen Expertise zu folgen. Direkte Parallele zu unserem Ansatz bei
     Backtests: eigene Ergebnisse/Findings sind die Quelle der Wahrheit,
     nicht generische Strategie-Ratschläge aus dem Netz -- wir machen das
     implizit schon so (CODE-Prozess mit "was ist potenziell integrierbar"
     statt blindem Copy-Paste von Paper-Ergebnissen).
  3. **Modellwahl-Heuristik** (deckt sich mit den beiden folgenden Clips,
     siehe unten): Sonnet als Standard-Alltags-Modell (~90% der Fälle),
     Opus für komplexere Analysen (~9%), Fable nur für Kreativität/schwere
     Sonderfälle (~1%) -- explizit NICHT standardmäßig auf dem stärksten
     Modell arbeiten.
  4. Diktierfunktion (Whisperflow o.ä.) als Alternative zum Tippen --
     für uns nicht direkt anwendbar (Interaktion läuft hier primär
     schriftlich/im Editor).
- Was ist NEU ggü. unserem aktuellen Setup (nicht übernommen, nur notiert):
  Scheduled Tasks für wiederkehrende Datenabfragen ("hole dir jeden Morgen
  X") -- konzeptionell das, was wir bereits mit dem Bridge-Watchdog/
  Lint-Check über `schedule`/`loop` machen, hier nur als allgemeines Muster
  bestätigt.

**Express**
- Kein Backtest-Bezug (Meta-Thema).
- Keine Handlungsempfehlung ausgelöst -- Inhalte bestätigen größtenteils
  bereits gelebte Praxis in diesem Repo, ohne neue konkrete Lücke
  aufzuzeigen.

---

## Everlast AI: "Nie wieder Claude-Limits: 12 Tipps für 20x mehr Leistung aus deinem Claude-Plan!"

**Capture**
- Quelle/Link: https://www.youtube.com/watch?v=KZAJeq5n-m8
- Erfasst am: 2026-09-01, verarbeitet: 2026-09-02
- Weg: Obsidian Web Clipper -> `knowledge/Clippings/Nie wieder Claude-Limits
  12 Tipps für 20x mehr Leistung aus deinem Claude-Plan!.md`

**Organize**
- Thema/Tags: Claude-Workflow, Kontextfenster-Management, Prompt-Caching,
  Kosten-Optimierung, Subagenten
- Verwandte Notizen: [[README]], Jonas-Keil-Eintrag oben (gleiche Datei,
  Kontextfenster-Hygiene-Punkt), Lisa-Zachmann-Eintrag unten (Überlappung
  bei Modellwahl/Compact vs. Clear)
- **Achtung**: Marketing-Video eines Kursanbieters, konkrete Zahlen
  (Kostenmultiplikatoren, Benchmark-Prozentwerte, "1/10 Cache-Read-Preis")
  sind NICHT gegen offizielle Anthropic-Doku gegengeprüft -- als Claims der
  Quelle behandeln, nicht als verifizierte Fakten.

**Distill**
- Kernthese: Deutlich technischeres Video als die anderen beiden
  Claude-Workflow-Clips, mit einem eigenen Framework ("BASE": Basis/
  Anpassungen/Sitzung/Eingabe) für die Zusammensetzung des Kontextfensters
  und mehreren Claude-Code-spezifischen Mechaniken (Prompt-Caching-Verfall,
  Subagenten-Orchestrierung, Hooks).
- Zentrale Konzepte:
  - **BASE-Framework**: Basis (System-Prompt/-Tools, nicht beeinflussbar) ->
    Anpassungen (`CLAUDE.md`, Skills, Memory-Files, MCP-Tools -- volle
    Kontrolle, aber: eine leere/knappe CLAUDE.md spart massiv Tokens ggü.
    einer seitenlangen generischen) -> Sitzung (wächst mit jeder Nachricht,
    größter Posten) -> Eingabe (aktuelle Nachricht/Anhänge, z.B. kostet ein
    HD-Screenshot laut Quelle ~2700 Tokens).
  - **Prompt-Caching**: laut Quelle verfällt der Cache nach 1 Stunde
    Inaktivität -- danach wird die nächste Nachricht wieder komplett neu
    (teuer) berechnet, unabhängig von Chat-Länge/-Wert davor. Relevant bei
    Remote-Zugriff (Handy/"Dispatch"), wo Pausen >1h wahrscheinlicher sind.
  - **Umgang mit vollem Kontextfenster**: Auto-Compact (Standard) laut
    Quelle der ungünstigste Zeitpunkt (zu spät, teuerste Stelle); `/clear`
    verliert alles; `/compact` fasst zusammen, kann aber Nuancen verlieren;
    empfohlener dritter Weg: ein **selbstgebauter Handoff-Skill**, der die
    Zusammenfassung NICHT im Kontextfenster hält, sondern als Markdown-Datei
    auf die Festplatte schreibt -- Vorteil: sauber verfügbar für künftige
    Sessions statt nur im (irgendwann verworfenen) Chat-Verlauf.
  - **Modell-/Effort-Steuerung**: laut Quelle skaliert der Tokenverbrauch
    bei gleicher Aufgabe etwa Haiku 1x / Sonnet 3x / Opus 5x / Fable 10x.
    Höherer "Thinking Effort" ist nicht automatisch besser -- die Quelle
    zitiert einen Benchmark, in dem Opus 5 auf "Medium" vor "High"/"Extra
    High"/"Max" liegt, bei geringeren Kosten. Empfehlung: Effort gezielt
    VOR der Aufgabe wählen, nicht standardmäßig hochdrehen, und nicht
    mitten in der Sitzung wechseln (verwirft laut Quelle sofort den Cache).
  - **Modell-Mixing**: andere Anbieter (z.B. GPT/Codex) über Plugin oder
    Proxy zusätzlich in Claude Code einbinden, wenn günstiger/besser
    geeignet für bestimmte Teilaufgaben. Achtung: laut Quelle von Anthropic
    ausdrücklich nicht unterstützt (Account-Risiko) -- für uns ohnehin
    irrelevant, da wir nicht plattformübergreifend arbeiten.
  - **Orchestrator-/Advisor-Subagenten**: starkes Modell (Opus/Fable)
    delegiert Teilaufgaben an günstigere Subagenten (Sonnet/Haiku) über
    `.claude/agents/`-Dateien (jeder Subagent bekommt eigenes
    Kontextfenster) -- ODER umgekehrt: günstiges Modell arbeitet primär,
    zieht per `/advisor` ein starkes Modell nur bei Bedarf hinzu.
  - **Prime Commands**: bei großen Wissensbasen (genau unser Second-Brain-
    Fall) nicht bei jeder Session alles lesen lassen, sondern über
    `/prime` bzw. themenspezifische `/prime <thema>`-Befehle gezielt nur
    die relevanten Dateien laden.
  - **Automatisierte Handoff-Dateien via Hook**: Schwelle festlegen (z.B.
    80% Kontextfenster) -> Claude schlägt automatisch eine Handoff-Datei
    vor. Handoff-Template fragt bewusst NICHT nach Aufgaben/Schritten
    (rekonstruierbar aus Code/Git-Historie), sondern nach dem, was sonst
    nirgendwo landet: Learnings, Fehlannahmen, Stellen mit Verbesserungspotenzial.
  - **`/doctor`-Befehl** (Bonus): prüft Skills/MCP-Server/Plugins auf lange
    ungenutzte, aber weiterhin Kontext kostende Einträge, weist auf
    veraltete Hooks hin, schlägt Kürzungen der `CLAUDE.md` vor.
- Bezug zu unserem Setup: wir haben aktuell weder einen Handoff-Skill noch
  `/prime`-Commands noch `/doctor`-Routine noch Subagenten-Delegation für
  die Second-Brain-Pflege -- alles vier potenziell nützlich für dieses
  Repo, aber jeweils eine Architekturentscheidung, keine Bugfix-Ergänzung.

**Express**
- Kein Backtest-Bezug (Meta-Thema).
- Vier mögliche Ergänzungen identifiziert (Handoff-Skill statt Auto-Compact/
  `/clear`; `/prime`-Command für `knowledge/`; periodischer `/doctor`-Check;
  ggf. CLAUDE.md-Kürzung/Review) -- Nutzerentscheid 2026-09-04:
  1. **Handoff-Skill: umgesetzt** -- `.claude/skills/handoff/SKILL.md` +
     `knowledge/_handoff/` als Inbox, CLAUDE.md "Kontextfenster-Hygiene"
     referenziert den Skill jetzt.
  2. **`/prime`-Command: verworfen** -- löst ein Problem, das dieses Repo
     nicht hat (Claude liest hier nicht blind das ganze Second Brain bei
     Sessionstart, sondern greift gezielt per Tool zu; CLAUDE.md Punkt 4
     verweist bereits auf `DASHBOARD.md` als ersten Anlaufpunkt).
  3. **`/doctor`-Check: zurückgestellt** -- aktuell nur ein eigener Skill
     (`second-brain-lint`) und keine MCP-Server, die Altlast-Gefahr besteht
     noch nicht in nennenswertem Umfang. In DASHBOARD.md Ideen-Inbox
     vermerkt, revisit sobald mehr Skills/Hooks dazukommen.
  4. **CLAUDE.md auf Englisch: verworfen** -- Ersparnis bei der kurzen Datei
     marginal, Kosten ist echte Lesbarkeit für den Nutzer (DASHBOARD/
     CHANGELOG bleiben ohnehin Deutsch), Verhältnis passt nicht.

---

## Lisa Zachmann: "Du verschwendest Tokens in Claude - ändere diese 5 Einstellungen!"

**Capture**
- Quelle/Link: https://www.youtube.com/watch?v=pCb2Vhmx-yI
- Erfasst am: 2026-09-01, verarbeitet: 2026-09-02
- Weg: Obsidian Web Clipper -> `knowledge/Clippings/Du verschwendest Tokens
  in Claude - ändere diese 5 Einstellungen!.md`

**Organize**
- Thema/Tags: Claude-Workflow, Kontextfenster-Management, Modellwahl
- Verwandte Notizen: [[README]], Jonas-Keil- und Everlast-AI-Einträge oben
  (gleiche Datei, deutliche inhaltliche Überlappung)

**Distill**
- Kernthese: Einsteigerfreundlichere, weniger technische Variante derselben
  Grundaussagen wie im Everlast-AI-Clip oben -- deckt sich fast vollständig,
  fügt aber einen eigenen, einfachen Frühwarn-Trick hinzu.
- Überschneidend mit Everlast AI (nicht doppelt ausgeführt, siehe dort):
  Kontextfenster wächst mit jeder Nachricht ("Schreibtisch"-Analogie: je
  voller, desto eher gehen Infos "unter" -> Claude verliert den Bezug oder
  halluziniert), Modellwahl nach Aufgabe (Haiku/Sonnet/Opus/Fable), Effort-
  Stufe zusätzlich zum Modell relevant, `/compact` vs. `/clear`, neues
  Thema = neuer Chat statt bestehenden vollzustopfen.
- **Ein Punkt, der bei Everlast AI fehlt**: Custom-Instructions/
  Benutzereinstellungen als einfaches Frühwarnsystem für Kontextverlust --
  z.B. "sprich mich in jeder Antwort mit meinem Namen an" in die
  Personalisierung schreiben; sobald Claude das plötzlich unterlässt, ist
  das ein sichtbares Zeichen, dass frühe Kontextinformationen bereits "vom
  Schreibtisch gefallen" sind, ohne dass man das Kontextfenster-Prozent
  aktiv beobachten muss.

**Express**
- Kein Backtest-Bezug (Meta-Thema).
- Keine eigene Handlungsempfehlung über den Everlast-AI-Eintrag hinaus --
  der Frühwarn-Trick (Name in Custom Instructions) ist eine reine
  claude.ai-Account-Einstellung außerhalb dieses Repos, daher kein
  Dashboard-Punkt.
