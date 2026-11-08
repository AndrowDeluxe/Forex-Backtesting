# Handoff 2026-11-02 23:30 -- Daily-Edge + Schichtenmodell

## Learnings
- Nutzer-Beschreibungen seiner Regeln widersprechen sich teils über mehrere Nachrichten (Typ C kam in
  drei Fassungen). Am verlässlichsten: Nachbau an seinem konkreten Chart-Beispiel prüfen und ihm die
  Kerzen-Tabelle zeigen -- dann korrigiert er präzise. Seine Indikator-Screenshots schlagen seine
  Erinnerung (MA Cross ist 12/20, nicht 20/50).
- Endstand Typ C: Signalkerze = Manipulationskerze selbst (16.10.2026-Beispiel); getestet wird C2
  (Schluss unter den Dochten der 3 Vorkerzen, Manipulation ≤ 7 Tage davor) mit Limit auf 50 % --
  „C1 mit Docht ≥ 50 % der Spanne“ ist meine Lesart, nie bestätigt.

## Fehlannahmen
- Stop S4 (Vortages-Extrem) mit Limit-Einstieg erzeugt Schein-Ergebnisse (winziges Risiko → absurde
  R). Nicht als Befund lesen; bei weiteren Tests mit Limit-Einstieg Mindestabstand Einstieg–Stop
  erzwingen.
- RBA-Download (403) nicht mit Browser-Kopf umgehen -- wurde vom Klassifizierer zu Recht blockiert.
  Nur Spiegel (DBnomics `RBA/F2`) oder manueller Download.

## Offene Fäden
- **C2 + Gold-Filter einfrieren und OOS 2022–24 / Blind 2010–15 öffnen**
  (`python -m htf_daily_trade.c2_goldfilter --oeffnen`): Nutzer hat NICHT eindeutig zugestimmt
  („Danach können wir … weiter angehen“ ist mehrdeutig). Morgen explizit fragen; irreversibel.
- BoE-Codes IUDSNPY/IUDMNPY/IUDLNPY: Laufzeit unklar (vermutlich 5/10/20 J.); für 2y die
  Anderson-Sleath-Spotkurve (ZIP) prüfen.
- `htf_daily_trade/macro.py` importiert die Regime-Logik jetzt aus `fusion_lab/filters/zinskurve_regime.py`;
  `confirmed()` dort lässt Twist nie bestätigen (leicht anders als die 5-Tage-Glättung im ersten
  Diagnose-Lauf, Lock `regime_quelle_vergleich`).
- Alles seit 18.10. zu diesem Strang ist ungecommittet (htf_daily_trade/, fusion_lab/filters/,
  knowledge-Notizen, Locks). Git-Sync-Stash-Gefahr ist seit 23.09. entschärft.

## Nächster Schritt
- Nutzer wünscht morgen zuerst einen Stand + kleine Zusammenfassung (Quelle: CHANGELOG-Einträge
  02.11., Edge Card, [[regime-bestimmung-und-filter]], [[filter-gold-zinskurve]]), dann die
  OOS-Frage, dann FX-Zinsdaten-Loader (EZB, MoF, BoC, BoE) für die FX-Schicht bauen.
