"""CTNL-Standalone-Kill-Switch fuer alle drei Bridges.

EINE Stelle statt drei Kopien -- dasselbe Argument wie bei `ribbon_gate`:
die drei Bridges sind schon einmal auseinandergelaufen (Memory
`three_bridges_not_same_state`), und ein Schutzschalter, der auf zwei Konten
anders entscheidet als auf dem dritten, waere genau dieselbe Falle nochmal.

WARUM ES DIESES MODUL GIBT (Nutzerauftrag 2026-09-30)
`live_signal.ctnl_standalone_drawdown()` existiert seit 2026-09-04 und wurde
damals "in alle drei Bots nachgeruestet" -- gemeint waren die PAPER-Bots.
LIVE lief die Pruefung nur in `FKInstantFunding-MT5-Bridge/run_once.py`.
Was das gekostet hat, steht im Weekly Checkup KW39/2026: FKs Schalter war vom
21.-28.09. aktiv und hielt FK aus 7 CTNL-Trades heraus (-8,74 R laut
Soll/Ist), waehrend auf demselben Bein in derselben Woche
**IQ -2.473,94 USD** (20 Trades, 2 Gewinner) und **EK -304,65 EUR**
(12 Trades, 0 Gewinner) verloren.

WAS ES MISST -- UND WAS AUSDRUECKLICH NICHT
Simuliert wird Continuation+Reversal auf einem EIGENEN virtuellen
100k-Konto mit FKs Risikogroessen (FK_RISK_CONT/FK_RISK_REV), voellig
unabhaengig von Equity und Gewichtung der aufrufenden Bridge. Gemessen wird
also die Gesundheit der STRATEGIE, nicht die des Kontos. Genau deshalb ist
der Schalter ohne Neukalibrierung portierbar und alle drei Bridges kommen
zum selben Urteil.

Der Konto-Drawdown ist eine ANDERE Groesse und wird anderswo geprueft
(Trailing-DD-Gate, Offenes-Risiko-Deckel). Dieser Schalter ersetzt sie nicht.

FAIL-SAFE: HIER DURCHLASSEN, NICHT BLOCKIEREN -- anders als ribbon_gate
Laesst sich der Drawdown nicht berechnen (Scanfehler, fehlende Daten), bleibt
der ZULETZT BEKANNTE Zustand stehen; ohne bekannten Zustand wird
durchgelassen. Begruendung: der Ribbon verwirft die schlechtere Haelfte der
Signale und muss bei Datenausfall sperren. Dieser Schalter dagegen greift nur
in einem seltenen Ausnahmezustand. Wuerde er bei jedem Scanfehler sperren,
haette ein Datenproblem dieselbe Wirkung wie ein echter Strategiebruch --
das waere ein stiller Totalausfall des Beins, den niemand als solchen sieht.
Ein Fehlschlag wird stattdessen gemeldet.

HYSTERESE
Aufhebung erst bei Erholung auf die HALBE Schwelle (-3,3 % statt -6,6 %),
damit der Schalter nicht um den Grenzwert flattert. Uebernommen aus FKs
Implementierung, damit das Verhalten identisch bleibt.

STATE
Der Aufrufer reicht sein eigenes State-Dict durch; der Schluessel
`ctnl_kill_switch_active` wird darin gehalten. Teilen sich mehrere Lanes
einer Bridge denselben State (Funded: 15-Min + Fast), gilt der Schalter
kontoweit -- so soll es sein.
"""
from __future__ import annotations

import time

import pandas as pd

from gold_smc_htf_ltf.live_signal import (
    CTNL_KILL_SWITCH_DD_THRESHOLD,
    ctnl_standalone_drawdown,
)

STATE_KEY = "ctnl_kill_switch_active"

# Der Scan ist teuer (voller Trailing-Fenster-Backtest). EKs Fast-Lane laeuft
# alle 2 Minuten -- ohne Cache waere das der teuerste Teil des Laufs. 10 Min.
# sind unkritisch: der Drawdown ist eine Trailing-Groesse ueber Monate, er
# springt nicht innerhalb einer Viertelstunde ueber die Schwelle.
_CACHE_TTL_S = 600.0
_cache: dict[str, tuple[float, float]] = {}  # source -> (timestamp, drawdown)


def _scan_trades(source: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Holt cont_trades/rev_trades ueber denselben Scan, den die Bridges
    ohnehin benutzen. Import bewusst LAZY: `challenge_portfolio.paper_bot`
    zieht den halben Strategie-Stack nach, und dieses Modul soll auch dort
    importierbar bleiben, wo der Scan gar nicht gebraucht wird."""
    import challenge_portfolio.paper_bot as pb

    # tz-NAIVE UTC, exakt wie run_once.py::main() es baut. Eine tz-bewusste
    # Timestamp laeuft im Scan in "Invalid comparison between
    # dtype=datetime64[us] and Timestamp" -- beim ersten Funktionstest am
    # 2026-09-30 genau so passiert.
    end = pd.Timestamp.now(tz="UTC").tz_localize(None)
    return pb._scan_ctnl(end, force_refresh=True, source=source)


def drawdown(cont_trades: pd.DataFrame | None = None,
             rev_trades: pd.DataFrame | None = None,
             *, source: str = "lake", use_cache: bool = True) -> float:
    """Stand-alone Cont+Rev-Drawdown. Werden Trades uebergeben, werden genau
    die gerechnet (Weg der Bridges, die ohnehin scannen); sonst wird selbst
    gescannt und das Ergebnis gecacht (Weg von EK, das signalbasiert arbeitet
    und keine Trade-Frames hat)."""
    if cont_trades is not None and rev_trades is not None:
        _pruefe_nicht_leer(cont_trades, rev_trades)
        return _dd_gehandelt(cont_trades, rev_trades)

    now = time.monotonic()
    if use_cache:
        hit = _cache.get(source)
        if hit is not None and now - hit[0] < _CACHE_TTL_S:
            return hit[1]

    cont, rev = _scan_trades(source)
    _pruefe_nicht_leer(cont, rev)   # vor dem Cache: eine Luecke darf nicht 10 Min. kleben
    dd = _dd_gehandelt(cont, rev)
    _cache[source] = (now, dd)
    return dd


def _dd_gehandelt(cont_trades: pd.DataFrame, rev_trades: pd.DataFrame) -> float:
    """Drawdown des TATSAECHLICH GEHANDELTEN Satzes (Nutzerentscheid 2026-09-30).

    Bis dahin lief der Schalter auf der UNGEFILTERTEN Strategie -- seit dem
    Ribbon-Gate wird die aber gar nicht mehr gehandelt. Gemessen am 30.09.:
    ungefiltert -7,01 % (Schalter an), ribbon-gefiltert -2,13 % (Schalter aus).
    Ein Schalter, der die Verluste einer abgeschalteten Variante zaehlt,
    sperrt die gehandelte. Jetzt: Ribbon auf beiden Beinen, Spike-Filter auf
    reversal -- dieselben Gates wie live. Schwelle/Hysterese unveraendert
    (-6,6 %/-3,3 %); auf dem Ribbon-Set haette sie 2016-2026 nie ausgeloest
    (MaxDD -43,5R = -6,5 % bei 0,15 %) -- sie bleibt Notbremse fuer einen
    echten Strategiebruch, siehe ctnl-kostenvalidierung.md Befund 19."""
    from gold_smc_htf_ltf import ribbon_gate, spike_gate

    teile, gesperrt = [], False
    for name, tr in (("ctnl_continuation", cont_trades), ("ctnl_reversal", rev_trades)):
        if tr is None or tr.empty:
            teile.append(tr)
            continue
        gef, hinweis = ribbon_gate.filter_trades(tr, source="lake", leg=name)
        if name in spike_gate.GATED_LEGS and not gef.empty:
            gef, hinweis2 = spike_gate.filter_trades(gef, lambda _r: False, leg=name)
            hinweis = f"{hinweis} {hinweis2}".strip()
        # Ribbon-/Spike-Filter verwarf ALLES wegen fehlender Daten -> kein Urteil
        if gef.empty and ("blockiert" in hinweis):
            gesperrt = True
        teile.append(gef)
    if gesperrt and all(t is None or t.empty for t in teile):
        raise KeineDaten("Filter ohne Daten (Ribbon/Spike nicht berechenbar)")
    if all(t is None or t.empty for t in teile):
        return 0.0   # wirklich kein gehandelter Trade im Fenster -> kein Drawdown
    leer = pd.DataFrame(columns=["entry_time", "exit_time", "r_multiple", "exit_reason"])
    cont = teile[0] if teile[0] is not None and not teile[0].empty else leer
    rev = teile[1] if teile[1] is not None and not teile[1].empty else leer
    return ctnl_standalone_drawdown(cont, rev)


class KeineDaten(Exception):
    """Scan ohne einen einzigen Trade -- Datenluecke, kein Strategie-Urteil."""


def _pruefe_nicht_leer(cont_trades, rev_trades) -> None:
    """FLACKER-SCHUTZ (2026-09-30). `_scan_ctnl()` liefert bei fehlenden Bars
    zwei LEERE Frames, und ein leerer Satz ergibt 0,00 % Drawdown. Genau das
    hob FKs Schalter am 29.09. zweimal faelschlich auf ("erholt (0.00%)",
    22:10 und 22:35 Berlin) und setzte ihn Minuten spaeter wieder. Ueber 90
    Tage Historie ist ein wirklich leerer Scan nicht plausibel."""
    def leer(d) -> bool:
        return d is None or len(d) == 0
    if leer(cont_trades) and leer(rev_trades):
        raise KeineDaten("Scan ohne Trades (Datenluecke?)")


def allows(state: dict,
           cont_trades: pd.DataFrame | None = None,
           rev_trades: pd.DataFrame | None = None,
           *, source: str = "lake", tag: str = "") -> tuple[bool, list[str]]:
    """(entries_erlaubt, meldungen). Blockiert NUR ctnl_continuation/
    ctnl_reversal -- alle anderen Beine sind unbeeinflusst.

    `tag` wird den Meldungen vorangestellt (z.B. "[FAST]" oder "[EK]"), damit
    im gemeinsamen Telegram-Kanal erkennbar bleibt, wer gemeldet hat."""
    messages: list[str] = []
    praefix = f"{tag} " if tag else ""

    try:
        dd = drawdown(cont_trades, rev_trades, source=source)
    except KeineDaten as e:
        # Kein Urteil, letzter Zustand bleibt. Nur ins Log, NICHT nach Telegram:
        # die Fast-Lanes wuerden eine Datenluecke sonst im 5-Min-Takt melden.
        print(f"{praefix}CTNL-Kill-Switch: {e} -- kein Urteil, Zustand bleibt "
              f"{'AKTIV' if state.get(STATE_KEY) else 'aus'}.")
        return not state.get(STATE_KEY, False), messages
    except Exception as e:  # noqa: BLE001 -- jeder Scan-/Datenfehler, siehe FAIL-SAFE oben
        messages.append(f"{praefix}⚠️ CTNL-Kill-Switch-Check fehlgeschlagen: {e}")
        return not state.get(STATE_KEY, False), messages

    aktiv = bool(state.get(STATE_KEY, False))

    if dd < CTNL_KILL_SWITCH_DD_THRESHOLD and not aktiv:
        state[STATE_KEY] = True
        messages.append(
            f"{praefix}\U0001F6A8 CTNL-KILL-SWITCH: Stand-alone Cont+Rev-Drawdown {dd:.2%} unter der "
            f"Phase-6-P5-Schwelle ({CTNL_KILL_SWITCH_DD_THRESHOLD:.2%}). Neue CTNL-Entries gestoppt. "
            f"Offene Positionen laufen normal weiter."
        )
    elif dd >= CTNL_KILL_SWITCH_DD_THRESHOLD * 0.5 and aktiv:
        state[STATE_KEY] = False
        messages.append(
            f"{praefix}✅ CTNL-Drawdown erholt ({dd:.2%}) -- CTNL-Kill-Switch aufgehoben."
        )

    return not state.get(STATE_KEY, False), messages
