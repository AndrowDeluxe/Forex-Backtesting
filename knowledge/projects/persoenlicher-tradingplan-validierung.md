# Project: Persönlicher Tradingplan -- Validierung

**Ziel**: Jeden Bestandteil des aktuellen persönlichen Tradingplans einzeln
durchgehen, backtesten und validieren. Was robust funktioniert wird
übernommen und als geprüfter Baustein (Parameter/Filter/Modell) festgehalten
-- am Ende eine handverlesene Sammlung, auf die man händisch zugreifen kann,
statt eines ungeprüften Regelwerks im Kopf.

**Status**: Setup -- Bestandteile-Liste wird gerade erstellt, noch nichts
validiert.

**Vorgehen pro Bestandteil**:
1. Bestandteil isolieren + präzise definieren (Regel/Parameter/Schwelle,
   nicht nur vage Idee)
2. Backtest bauen/laufen lassen (bestehende Infrastruktur wiederverwenden,
   wo möglich -- Instrument/Zeitraum an bereits gecachte Daten anpassen)
3. Validieren: robust über Zeit (IS/OOS-Split) und ggf. über Instrumente?
   Kein Overfitting auf eine Teilperiode?
4. Validiert -> in `resources/persoenlicher-tradingplan.md` als Baustein
   festhalten, mit Link zum Ergebnis (Commit/Streamlit-Seite).
5. Nicht validiert -> als verworfen dokumentieren (mit Grund), nicht
   stillschweigend löschen -- verworfene Ideen sind auch Erkenntnis.

## Bestandteile-Checklist

<!-- Liste der einzelnen Tradingplan-Bestandteile -- wird gemeinsam befüllt,
     dann Stück für Stück abgearbeitet. -->

- [ ] <Bestandteil 1>
- [ ] <Bestandteil 2>
- [ ] <Bestandteil 3>

**Verknüpfung**: [[paper-verarbeitung]] (ähnlicher Prozess, hier ist die
Quelle aber der eigene Tradingplan statt ein externes Paper)
