"""Flankengesteuerte Signal-Meldungen: eine Nachricht beim Wechsel, nicht je Lauf.

EINE Stelle fuer alle drei Bridges -- dasselbe Argument wie bei `ribbon_gate`
und `spike_gate` (Memory `three_bridges_not_same_state`).

DAS PROBLEM (Nutzerauftrag 2026-10-01)
Mehrere Sperren melden ZUSTAENDE, nicht Ereignisse: "Positionsdeckel
erreicht", "nicht trendkonform", "Signalkerze zu klein". Solange der Zustand
anhaelt, wiederholt sich die Meldung bei JEDEM Lauf -- bei 15-Minuten-Takt
also bis zu 96-mal am Tag, je Konto. Am 2026-10-01 standen allein 128
Ribbon-Zeilen im Funded-Log.

DIE REGEL
Gemeldet wird nur der WECHSEL:
  handelnd  -> gesperrt   : eine Nachricht ("ab jetzt uebersprungen, Grund")
  gesperrt  -> handelnd   : eine Nachricht ("wieder angenommen")
Bleibt der Zustand, kommt nichts. Der Grund wird mitgefuehrt: aendert sich
der Grund (z.B. von "Positionsdeckel" zu "gegen den Trend"), ist das ein
neuer Wechsel und wird gemeldet -- sonst wuerde eine echte
Ursachenaenderung still untergehen.

WARUM IM STATE UND NICHT IM PROZESS
Die Bridges laufen als EINZELNE Prozesse je Scheduled-Task-Trigger; eine
Variable im Modul waere nach jedem Lauf weg und wuerde jede Meldung erneut
senden. Der Zustand gehoert deshalb in die bridge_state_*.json, die ohnehin
je Lauf geschrieben wird.

ABSICHTLICH NICHT GEDAEMPFT: Fehler und Ausnahmen. Dieses Modul ist fuer
erwartbare Sperren gedacht ("die Regel greift"), nicht fuer Stoerungen.
Ein Datenausfall oder ein Order-Reject soll weiterhin jedes Mal auffallen.
"""

from __future__ import annotations

_STATE_KEY = "signal_notify"


def melde_wechsel(state: dict, schluessel: str, *, gesperrt: bool,
                  grund: str = "", text_gesperrt: str = "",
                  text_frei: str = "") -> str | None:
    """Gibt den Meldetext zurueck -- oder None, wenn sich nichts geaendert hat.

    `schluessel` identifiziert die Sperre eindeutig, ueblicherweise
    "<konto>:<bein>". `grund` wird mitgespeichert: ein Wechsel des Grundes
    bei weiterhin bestehender Sperre gilt als neuer Wechsel.

    Der Aufrufer entscheidet, was mit dem Text passiert (queue_message,
    print, beides) -- dieses Modul kennt kein Telegram.
    """
    buch = state.setdefault(_STATE_KEY, {})
    vorher = buch.get(schluessel)
    jetzt = {"gesperrt": bool(gesperrt), "grund": grund}

    if vorher is not None and vorher.get("gesperrt") == jetzt["gesperrt"] \
            and vorher.get("grund") == jetzt["grund"]:
        return None  # unveraendert -> schweigen

    buch[schluessel] = jetzt

    # Allererster Lauf und NICHT gesperrt: kein Grund, "laeuft wieder" zu
    # melden -- es lief nie etwas anderes.
    if vorher is None and not gesperrt:
        return None

    if gesperrt:
        return text_gesperrt or f"{schluessel}: Signale werden uebersprungen -- {grund}"
    return text_frei or f"{schluessel}: Signale werden wieder angenommen."


def zuruecksetzen(state: dict, schluessel: str) -> None:
    """Vergisst den gemerkten Zustand -- der naechste Lauf meldet wieder.

    Gedacht fuer Faelle, in denen der Zusammenhang abreisst (Kontowechsel,
    State-Neuaufbau). Nicht im Normalbetrieb noetig.
    """
    state.get(_STATE_KEY, {}).pop(schluessel, None)
