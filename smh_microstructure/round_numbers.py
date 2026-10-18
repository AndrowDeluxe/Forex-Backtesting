"""K1 -- Runde Zahlen (Osler 2003, 2005).

Mechanismus: Take-Profit-Orders ballen sich auf runden Kursen (x.xx00), dort
prallt der Kurs ueberdurchschnittlich oft ab. Stop-Orders liegen knapp
dahinter; wird die Zahl durchbrochen, loesen sie eine Kaskade aus und der
Kurs beschleunigt. Wer verliert: wer seine Orders vorhersehbar an runde
Zahlen legt (Fill exakt am Cluster, Stop-Kaskade zum schlechtesten Preis).

Zwei Varianten aus demselben Mechanismus:
  fade     -- Limit an der runden Zahl gegen die Anlaufrichtung.
  cascade  -- Stop-Order `breach` Pips hinter der Zahl in Durchbruchsrichtung.

Gegenprobe: dieselbe Mechanik an Schein-Leveln (offset, z. B. x.xx37).
Haben runde Zahlen keinen Sondereffekt, sind die Schein-Level gleich gut.

Ausfuehrung auf M1-Bid (UTC). Konservativ: Stop und Ziel im selben Bar ->
Stop zaehlt; Stop im Einstiegsbar -> Stop zaehlt.
"""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from smh_microstructure.costs import PIP, roundtrip_cost


@dataclass(frozen=True)
class Config:
    mode: str = "fade"          # fade | cascade
    step_pips: float = 100.0    # Abstand der Level: 100 = x.xx00 ("big figure")
    offset_pips: float = 0.0    # 0 = runde Zahl; >0 = Schein-Level (Gegenprobe)
    approach_pips: float = 20.0  # frischer Anlauf: Kurs war seit letzter Beruehrung so weit weg
    stop_pips: float = 15.0     # jenseits des Stop-Clusters (Osler 2005: wenige Pips hinter der Zahl)
    target_pips: float = 15.0   # symmetrisch zum Stop -> Trefferquote zeigt den Effekt direkt
    breach_pips: float = 3.0    # nur cascade: Einstieg so weit hinter der Zahl
    hold_min: int = 60          # Zeit-Exit (Osler misst Effekte im Stundenbereich)
    cost_mult: float = 1.0

    def as_dict(self):
        return asdict(self)


ROLLOVER_UTC = (21, 22)  # Spreads explodieren um den Tageswechsel -> keine Einstiege


def _first_touch_events(df: pd.DataFrame, sym: str, cfg: Config) -> list[tuple[int, float, int]]:
    """(Bar-Index, Level, Anlaufrichtung +1 = von unten, -1 = von oben) je frischer Beruehrung."""
    pip = PIP[sym]
    step, off = cfg.step_pips * pip, cfg.offset_pips * pip
    hi, lo, cl = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    idx = df.index
    hours = idx.hour.to_numpy()
    gap = np.diff(idx.asi8, prepend=idx.asi8[0]) > 60 * 60 * 1e9  # Wochenende/Luecke
    appr = cfg.approach_pips * pip
    last_touch: dict[int, int] = {}
    events = []
    k_lo = np.ceil((lo - off) / step - 1e-9).astype(np.int64)   # kleinstes Level >= low
    k_hi = np.floor((hi - off) / step + 1e-9).astype(np.int64)  # groesstes Level <= high
    for i in np.nonzero(k_hi >= k_lo)[0]:
        if i == 0:
            continue
        for k in range(k_lo[i], k_hi[i] + 1):
            lvl = k * step + off
            prev = last_touch.get(k)
            last_touch[k] = i
            if gap[i] or hours[i] in ROLLOVER_UTC:
                continue
            start = max(prev + 1 if prev is not None else i - 1440, 0)
            if start >= i:
                continue
            if cl[i - 1] < lvl:      # Anlauf von unten
                if lo[start:i].min() <= lvl - appr:
                    events.append((i, lvl, +1))
            elif cl[i - 1] > lvl:    # Anlauf von oben
                if hi[start:i].max() >= lvl + appr:
                    events.append((i, lvl, -1))
    return events


def run(df: pd.DataFrame, sym: str, cfg: Config) -> pd.DataFrame:
    pip = PIP[sym]
    hi, lo, cl, op = (df[c].to_numpy() for c in ("high", "low", "close", "open"))
    idx = df.index
    n = len(df)
    stop, tgt = cfg.stop_pips * pip, cfg.target_pips * pip
    rows, busy_until = [], -1
    for i, lvl, came_from in _first_touch_events(df, sym, cfg):
        if i <= busy_until:
            continue
        if cfg.mode == "fade":
            side = -came_from                       # gegen die Anlaufrichtung
            e_bar, entry = i, lvl
        else:
            side = came_from                         # mit dem Durchbruch
            trig = lvl + came_from * cfg.breach_pips * pip
            e_bar = None
            for j in range(i, min(i + cfg.hold_min, n)):
                if (hi[j] >= trig) if side > 0 else (lo[j] <= trig):
                    e_bar = j
                    break
                # zurueck ueber das Level -> Durchbruch gescheitert, kein Trade
                if j > i and ((cl[j] < lvl) if side > 0 else (cl[j] > lvl)):
                    break
            if e_bar is None:
                continue
            entry = max(trig, op[e_bar]) if side > 0 else min(trig, op[e_bar])  # Gap -> schlechterer Fill
        sl, tp = entry - side * stop, entry + side * tgt
        exit_px, exit_bar, why = None, None, None
        # Einstiegsbar: nur Stop pruefen (Reihenfolge im Bar unbekannt -> konservativ)
        if (lo[e_bar] <= sl) if side > 0 else (hi[e_bar] >= sl):
            exit_px, exit_bar, why = sl, e_bar, "stop"
        last = min(e_bar + cfg.hold_min, n - 1)
        j = e_bar + 1
        while exit_px is None and j <= last:
            if (lo[j] <= sl) if side > 0 else (hi[j] >= sl):
                exit_px, exit_bar, why = sl, j, "stop"
            elif (hi[j] >= tp) if side > 0 else (lo[j] <= tp):
                exit_px, exit_bar, why = tp, j, "target"
            j += 1
        if exit_px is None:
            exit_px, exit_bar, why = cl[last], last, "time"
        cost = roundtrip_cost(sym, entry, cfg.cost_mult)
        pnl = side * (exit_px - entry) - cost
        rows.append({"sym": sym, "entry_time": idx[e_bar], "exit_time": idx[exit_bar], "side": side,
                     "level": lvl, "entry": entry, "exit": exit_px, "why": why,
                     "pnl_pips": pnl / pip, "pnl_r": pnl / stop})
        busy_until = exit_bar
    return pd.DataFrame(rows)


def run_all(data: dict[str, pd.DataFrame], cfg: Config) -> pd.DataFrame:
    parts = [run(df, sym, cfg) for sym, df in data.items()]
    parts = [p for p in parts if len(p)]
    if not parts:
        return pd.DataFrame(columns=["sym", "entry_time", "pnl_r"])
    return pd.concat(parts).sort_values("entry_time").reset_index(drop=True)
