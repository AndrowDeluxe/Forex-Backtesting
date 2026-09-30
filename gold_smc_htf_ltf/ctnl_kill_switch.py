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
        return ctnl_standalone_drawdown(cont_trades, rev_trades)

    now = time.monotonic()
    if use_cache:
        hit = _cache.get(source)
        if hit is not None and now - hit[0] < _CACHE_TTL_S:
            return hit[1]

    dd = ctnl_standalone_drawdown(*_scan_trades(source))
    _cache[source] = (now, dd)
    return dd


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
