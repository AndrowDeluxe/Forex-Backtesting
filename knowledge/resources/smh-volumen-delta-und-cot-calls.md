# SMH-Calls "Volumen und Delta" + "COT Teil 1": Anwendungen, Edges, Filter

> **Nachtrag 2026-11-10:** Den Ton zu „COT Teil 1“ gibt es inzwischen als „COT HTF Volume“. Die Transkripte bestätigen die Lesarten unten, die Auswertung steht in [[smh-dennis-cot-volumen-calls]].

Quelle: zwei Bildschirmaufnahmen unter
`OneDrive\...\Institutial Mandate\Calls\` (bezahlter Kursinhalt, nicht im Repo):
- `Volumen und Delta.mp4` (53 Min., Live-Call vom 2026-11-02 ca. 20:14–21:06,
  Euro-FX-Futures 6E, 1 Min. bis 8 h)
- `COT Teil 1.mp4` (27 Min.; abgefilmt wird das Kursvideo
  "COT/HTF Volume alighment", Länge 56:51, bis Videominute 38:19; ab
  Aufnahmeminute ~20 steht das Bild still). Gezeigt werden 6E-Tageskerzen
  07/2025–10/2026.

**Einschränkung:** Beide Dateien haben nur **9 bzw. 20 Sekunden Ton**, der Rest
ist stumm (geprüft mit ffmpeg: Die Tonspur endet dort, die Datei ist nicht
defekt). Ein Whisper-Transkript ist darum nicht möglich. Alles hier ist aus
Bildtafeln gelesen (Bild alle 30 s plus Einzelbilder). Ausgewertet sind
Zeichnungen, Beschriftungen und Indikatoren, nicht die Erklärungen dazu.
Verwandt: [[smh-session-pips-call]], [[smh-cls-praxis-call]],
[[smh-elite-mikrostruktur]], [[order-flow-trading]],
[[crypto-volume-profile-mean-reversion]], [[htf-daily-trade-edge-card]],
[[skill-test-orb-ctnl]], [[makro-faktoren-katalog]], [[overfitting-sperre]].

## Was gezeigt wird

### Volumen und Delta (6E intraday)
1. **"Marketmaker low":** Ein Sweep unter ein Tief. An der Lunte steht ein
   Fixed-Range-Volumenprofil mit großem roten Delta-Balken, also viel
   aggressiver Verkauf, der aufgefangen wird (Absorption). Danach dreht der
   Kurs. Das Muster wird auf 10 Min., 15 Min. und 1 Min. wiederholt.
2. **Delta-Rechnung** an einer Preisstufe: "224 × 120 → 224 − 120 = 104"
   (Ask- gegen Bid-Volumen, Netto-Aggression).
3. **Profil von Swing zu Swing** (4 h/1 h, FRVP, Value Area laut
   Einstellungsfenster 80): Swing-Hochs und -Tiefs sind als rote Punkte
   markiert, das Profil wird dazwischen gezogen. POC und Hochvolumen-Knoten
   sind orange als POI markiert, mit Retest-Pfeilen.
4. **"delta seller":** Skizze mit Abverkauf, Rücklauf an die Stufe der
   Delta-Verkäufer und Fortsetzung nach unten.
5. **Profilformen** (Skizzen am Ende): "fair value range" (breite
   Verteilung) und **"vom Extrem zum POC"**. Dazu "fair value poi" am POC.
   Gemeint ist offenbar: Ein Profil-Extrem wird angelaufen, Ziel ist der
   POC.
6. Ein Beispieltrade auf 1 Min.: Short aus der oberen Zone, Ziel tiefer.
   Statistik wird keine gezeigt.

### COT Teil 1 (6E Tageskerzen)
1. **Intermarket-Skizze:** S&P, Apple, Öl, Euro, Gold/Silber(?) und
   "SDAOY" (unleserlich) als Netz. Beschriftung "Rohstoff, Indic,
   Währungen".
2. **Phasenmodell:** "Ruhepuls: Fair-Value-Aufbau von Orders und
   effizientes Handeln" (enge Range) → "Neuorientierung des Markets,
   Impuls, Neubepreisung der Bücher, Liq-Sweep" (grauer Block) → großer
   Trend.
3. **Beispiel EUR 2025/26:** orange Box = Range 07/2025–01/2026 mit
   Volumenprofil. Darin verlaufen die COT-Linien (Commercials blau,
   zweite Gruppe orange) flach und eng (grau hinterlegt). Danach kommt
   ein Sweep-Hoch (Ende Jan. 2026, orange Kerze) und eine blaue
   Rebalancing-Zone am Profil. Ab April 2026 laufen die COT-Linien
   auseinander (rote Trendlinien). Der Kurs fällt von ~1,20 auf ~1,14.
4. **COT-Tabelle** im Chart, je EUR und USD: Commercials / Institutional /
   Retail Traders mit Netto-Kontrakten und Long-/Short-Anteil. Das ist die
   Legacy-Einteilung (Commercial / Non-Commercial / Non-Reportable). Für
   EUR stehen Commercials netto long (+151k, 56 % long) gegen
   Institutional netto short (−138k, 62 % short).

## Abgleich mit dem, was wir schon wissen
- **COT als Kontra-Extrem ist zweimal gescheitert:** als Gold-ASB-Filter
  (Zhang & Laws, 2026-08-08, keine robuste Kante) und als
  `cot-contrarian-detector`-Filter für ORB/CTNL (−0,12 R, nur 13 Tage
  "crowded"). Das Modell des Calls ist aber ein anderes: COT als
  **Richtungsbestätigung nach einem Range-Ausbruch**, Horizont Wochen bis
  Monate. Das ist noch ungetestet.
- **Profil-Ziele passen zu "Magnet statt Wand"**
  ([[keylevel-edge-card-final]]): Key Levels werden nach
  Berührung öfter durchstoßen. "Vom Extrem zum POC" ist dieselbe
  Magnet-Logik, nur auf Volumenebene. Der Value-Area-Fail/Hold aus dem
  `auction_playbook` (BTC, Taker-Volumen) hatte keinen robusten Edge.
- **Intraday-Mikrostruktur:** Die Fade-Prämie gehört dem Maker
  ([[smh-elite-mikrostruktur]], 8/8 Kandidaten brutto = Spread). Ein
  1-Min.-Absorptions-Scalp muss diese Hürde netto erst nehmen.
- **Daten:** Echtes Delta braucht Bid/Ask-Aggressor-Volumen aus CME-Futures
  (6E, GC, ES). Das haben wir nicht. Dukascopy liefert nur Tick-Volumen
  (Anzahl Quotes). Für die **Lage** eines Profils (POC/HVN auf 1 h bis
  Tag) taugt es als Näherung, für **Delta** nicht. COT gibt es frei bei der
  CFTC (`asian_range_breakout/cot.py`, Legacy-Report; Veröffentlichung Fr.
  für Di., 3 Tage Versatz eingebaut).

## Kandidaten, nach Testbarkeit geordnet

| # | Idee | Art | Daten da? | Einschätzung |
|---|---|---|---|---|
| A | **COT-Richtung als Filter für HTF Daily-Trade** (Typ C/R nur, wenn die Commercials-Netto-Änderung der letzten 4–8 Wochen in Trade-Richtung zeigt) | Filter | ja (CFTC + Dukascopy D1) | Am billigsten und passt zum laufenden Projekt [[htf-daily-trade-edge-card]]. Gezählte Variante unter der Overfitting-Sperre. Wenige Trades, darum wohl nur ein grobes Signal. |
| B | **"Vom Extrem zum POC"**: Wird ein Profil-Extrem (VAH/VAL des letzten Swing-Profils, 1 h/4 h) berührt, wird der POC dann öfter erreicht als von einem gleich weit entfernten Kontrollpunkt? | Ziel-/Edge-Regel | Näherung (Tick-Volumen) | Erst beschreibend wie bei den Key Levels. Wenn ja: POC als TP-Regel für bestehende Beine prüfen. Kosten spielen bei 1 h/4 h kaum eine Rolle. |
| C | **COT-Range-Ausbruch als eigener HTF-Edge**: lange Range mit flachem COT → Sweep → Einstieg im Rebalancing an Profil/POC in die Richtung, in die die COT-Gruppen auseinanderlaufen | Edge | ja (Wochen-COT, D1) | Mechanismus plausibel (Positionierung baut sich auf, dann wird neu bepreist). Die Boxen sind im Video aber im Nachhinein gezogen. Braucht eine Edge Card mit festen Regeln für Range und "flach". n klein (~1–3 Fälle je Markt und Jahr). |
| D | **Marketmaker low / Absorption** (Sweep mit großem Gegen-Delta → Umkehr), dazu "delta seller"-Retest | Einstieg | **nein** (Footprint fehlt) | Nicht testbar ohne CME-Tickdaten mit Aggressor-Seite (z. B. Databento, kostenpflichtig). Proxy über Tick-Regel auf Dukascopy-Quotes ist zu schwach. Als diskretionäre Bestätigung nutzbar, als Bot-Regel nicht. |

**Empfehlung:** A zuerst. Das ist eine Variante im laufenden HTF-Projekt und
kostet wenig. B als zweiten Test, weil er unsere Magnet-Befunde direkt
fortsetzt. C nur über eine Edge Card. D erst, wenn Futures-Tickdaten da sind.

## Offen
- Die Aufnahmen ohne Ton machen die Erklärungen unauswertbar. Für ein
  Transkript bräuchte es eine Neuaufnahme mit Systemton oder das
  Originalvideo.
- COT Teil 1 ist unvollständig (Aufnahme bis Videominute 38:19 von 56:51,
  Standbild ab ~20 Min.).
