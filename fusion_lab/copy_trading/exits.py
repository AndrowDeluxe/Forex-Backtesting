"""Ausstiegs-Varianten (Stufe 3, Nutzerauftrag 21.10.2026): SL, TP, Break-even, Trailing.

Minutengenau auf M1, vektorisiert. Shorts werden gespiegelt (x = -Kurs), dann gilt
ueberall Long-Logik. Konservative Reihenfolge je Kerze: Stop und Trailing werden nur mit
Information bis zur VORKERZE nachgezogen; trifft eine Kerze Stop und Ziel, gilt der Stop.
In der Fuellkerze eines Limits zaehlt nur der Stop.
"""

import numpy as np
import pandas as pd

HORIZON = pd.Timedelta(days=90)   # ANNAHME: Trades ohne Ausstieg werden nach 90 Tagen bewertet


def run(m1: dict, i0: int, d: int, p_in: float, sl0: float, tp: float | None,
        be_r: float | None, trail: tuple | None, atr: float | None,
        swings: tuple[np.ndarray, np.ndarray] | None, fill_bar: bool, events: list | None = None):
    """m1: dict mit Arrays t (int64 ns), o, h, l, c. i0: erste zu pruefende Kerze.
    trail: None | ("atr", k, ab_R) | ("swing",). swings: (Bestaetigungszeit ns, Preis) der
    Chart-TF-Swings auf der Stop-Seite (Long: Tiefs, Short: Hochs), nur nach dem Einstieg.
    events (Stufe 2, Dennis' Anweisungen): Liste (t_ns, art, anteil), art "be" | "close" |
    "partial", wirksam ab der ersten Kerze, die bei/nach t_ns beginnt. Ohne events bitgleich
    zum Stand vor Stufe 2.
    Rueckgabe: (Index Ausstiegskerze, Ausstiegspreis, Grund). Nach einem Teilschluss ist der
    Ausstiegspreis der mengengewichtete Mittelwert (R ist linear im Preis)."""
    t = m1["t"]
    if i0 >= len(t):
        return len(t) - 1, p_in, "offen"
    i1 = int(np.searchsorted(t, t[i0] + HORIZON.value))
    i1 = max(i1, i0 + 1)
    if d > 0:
        H, L, O, C = m1["h"][i0:i1], m1["l"][i0:i1], m1["o"][i0:i1], m1["c"][i0:i1]
    else:
        H, L, O, C = -m1["l"][i0:i1], -m1["h"][i0:i1], -m1["o"][i0:i1], -m1["c"][i0:i1]
    if len(H) == 0:
        return i0, p_in, "offen"
    x_in, x_sl = d * p_in, d * sl0
    x_tp = d * tp if tp is not None else None
    risk = x_in - x_sl
    best_prev = np.maximum.accumulate(np.concatenate(([x_in], H[:-1])))
    stop = np.full(len(H), x_sl)
    if be_r is not None:
        stop = np.where(best_prev >= x_in + be_r * risk, np.maximum(stop, x_in), stop)
    if trail is not None and trail[0] == "atr" and atr:
        k, start_r = trail[1], trail[2]
        active = best_prev >= x_in + start_r * risk
        stop = np.where(active, np.maximum(stop, best_prev - k * atr), stop)
    if trail is not None and trail[0] == "swing" and swings is not None and len(swings[0]):
        st, sp = swings
        tt = t[i0:i1]
        # Swing gilt ab der Kerze, die mit dem Schluss der Bestaetigungskerze beginnt
        j = np.searchsorted(st, tt, side="right") - 1
        xs = d * sp
        lvl = np.maximum.accumulate(np.where(j >= 0, xs[np.clip(j, 0, None)], -np.inf))
        stop = np.maximum(stop, lvl)
    i_close, partials = None, []
    for t_ev, kind, frac in sorted(events or []):
        j = int(np.searchsorted(t[i0:i1], t_ev, side="left"))
        if j <= 0 or j >= len(H):
            continue   # vor dem Einstieg, in der Fuellkerze oder nach dem Horizont: wirkungslos
        if kind == "be" and C[j - 1] > x_in:
            stop[j:] = np.maximum(stop[j:], x_in)
        elif kind in ("be", "close"):
            # ANNAHME (28.10.2026): "BE ziehen", waehrend der Kurs unter dem Entry steht, heisst
            # schliessen zum Kurs (ein Stop ueber dem Kurs loeste sofort aus)
            i_close = j if i_close is None else min(i_close, j)
        elif kind == "partial":
            partials.append((j, frac))
    stop = np.maximum.accumulate(stop)
    sl_hit = L <= stop
    tp_hit = H >= x_tp if x_tp is not None else np.zeros(len(H), bool)
    if fill_bar:
        tp_hit[0] = False
    i_sl = int(np.argmax(sl_hit)) if sl_hit.any() else None
    i_tp = int(np.argmax(tp_hit)) if tp_hit.any() else None
    if i_sl is not None and (i_tp is None or i_sl <= i_tp):
        x_out = min(O[i_sl], stop[i_sl]) if not (fill_bar and i_sl == 0) else stop[0]
        why = ("SL" if abs(stop[i_sl] - x_sl) < 1e-12 else
               "BE" if abs(stop[i_sl] - x_in) < 1e-12 else "Trail")
        i_x, x_x = i_sl, x_out
    elif i_tp is not None:
        i_x, x_x, why = i_tp, x_tp, "TP"
    else:
        i_x, x_x, why = len(H) - 1, C[-1], "offen"
    if i_close is not None and (i_close <= i_x or why == "offen"):
        i_x, x_x, why = i_close, O[i_close], "Anweisung"   # Anweisung vor SL/TP: zum Open raus
    rest, x_part = 1.0, 0.0
    for j, frac in sorted(partials):
        if j < i_x:
            x_part += rest * frac * O[j]
            rest *= 1 - frac
    if rest < 1.0:
        return i0 + i_x, d * (x_part + rest * x_x), why + "+Teil"
    if why == "TP":
        return i0 + i_x, tp, why
    return i0 + i_x, d * x_x, why
