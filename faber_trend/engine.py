"""Tages-Engine fuer den Faber-Monatstrend mit SL, Positionsclose und Sizing.

Konventionen (Spezifikation 2026-10-04 + Plan binary-enchanting-breeze):
- Monatssignal von Monat M wird am Schluss des ersten Handelstags des
  Zielinstruments in M+1 ausgefuehrt (Entry, Close, Wechsel).
- SL broker-seitig, ab dem Tag NACH dem Entry auf Tages-High/Low geprueft;
  Gap durch den SL -> Fill zum Open. Nach SL: Re-Entry erst beim naechsten
  Monatssignal (auch wenn das Ziel unveraendert ist).
- Sizing: Nominal = Risiko / SL-Abstand (in %), auf Mindestlot/Lot-Schritt
  abgerundet; liegt das Mindestlot ueber dem Zielrisiko, wird der Trade
  NICHT genommen (gezaehlt).
- Kosten: Spread-Anteil je Ein-/Ausstieg aufs Nominal, Swap je Kalendertag
  aufs gehaltene Nominal (long und short gleich).
- Waehrung: alle P&L als Kontowaehrung behandelt, ausser USDJPY (JPY-P&L
  wird ueber den Kurs in USD umgerechnet).
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import signals as S

# Kontrakt-Annahmen (Tickmill/TTP-Standard, NICHT per symbol_info verifiziert)
CONTRACT = {
    "SP500": 1, "NASDAQ": 1, "US30": 1, "DAX": 1, "GOLD": 100, "SILVER": 5000,
    "OIL": 1000, "COPPER": 25000, "TNOTE10": 1000, "TBOND30": 1000,
    "EURUSD": 100000, "USDJPY": 100000, "BTC": 1,
}
MIN_LOT, LOT_STEP = 0.01, 0.01


@dataclass
class Account:
    name: str
    equity0: float
    min_lot_check: bool = True


@dataclass
class Costs:
    spread: float = 0.0005
    swap_pa: float = 0.025


@dataclass
class StopRule:
    kind: str = "none"          # none | pct | atr | trail | mae_pct | mae_atr
    param: object = None        # float oder {instrument: float}
    daily_sma_exit: bool = False
    sizing_pct_if_none: float = 0.20

    def p(self, inst):
        return self.param[inst] if isinstance(self.param, dict) else self.param


@dataclass
class Sleeve:
    name: str
    targets: pd.Series          # PeriodIndex(M) -> (instrument|None, dir)
    weight: float = 1.0


@dataclass
class Sizing:
    risk_pct: float = 0.005
    open_risk_cap: float = None  # B2, Anteil der Equity
    vol_target: float = None     # B3, Jahres-Vola je Position (Anteil Equity)
    vol_filter_half: bool = False  # C3
    rebalance: bool = True       # Monats-Rebalancing aufs Risikobudget (Faber-FAQ)


@dataclass
class Pos:
    inst: str
    dir: int
    units: float
    entry_px: float
    entry_day: pd.Timestamp
    stop: float
    sleeve: str
    hi: float
    mae: float = 0.0
    exit_flag: bool = False


def prepare(df_by_inst):
    """Je Instrument: ATR20, Vola20, expandierender Vola-Median, taegliches
    SMA10-Niveau des letzten abgeschlossenen Monats, Monatsschluesse."""
    out = {}
    data_end = max(d.index[-1] for d in df_by_inst.values())
    for k, d in df_by_inst.items():
        d = d.copy()
        if "ref" not in d:
            d["ref"] = d["close"]
        pc = d["close"].shift(1)
        tr = pd.concat([d["high"] - d["low"], (d["high"] - pc).abs(), (d["low"] - pc).abs()], axis=1).max(axis=1)
        d["atr"] = tr.rolling(20).mean()
        r = d["close"].pct_change()
        d["vol20"] = r.rolling(20).std() * np.sqrt(252)
        d["volmed"] = d["vol20"].expanding(252).median()
        me = S.complete_month_ends(d["close"], data_end)
        _, sma = S.sma_signal(me, 10)
        lvl = sma.reindex(d.index).shift(1).ffill()  # erst ab Folgetag bekannt
        d["sma_lvl"] = lvl
        out[k] = {"df": d, "me": me}
    return out


def exec_days(prep):
    """inst -> {Period M: erster Handelstag in M+1}"""
    res = {}
    for k, v in prep.items():
        idx = v["df"].index
        first = pd.Series(idx, index=idx).groupby(idx.to_period("M")).first()
        res[k] = {m - 1: day for m, day in first.items()}
    return res


def _notional_value(inst, units, px):
    return units if inst == "USDJPY" else units * px


def _pnl(inst, units, d_px, px):
    return units * d_px / px if inst == "USDJPY" else units * d_px


def run(prep, sleeves, stop: StopRule, sizing: Sizing, costs: Costs, account: Account,
        start=None, end=None, lag_days=0):
    xd = exec_days(prep)
    cal = sorted(set().union(*[v["df"].index for v in prep.values()]))
    cal = pd.DatetimeIndex(cal)
    if start is not None:
        cal = cal[cal >= pd.Timestamp(start)]
    if end is not None:
        cal = cal[cal <= pd.Timestamp(end)]
    dfs = {k: v["df"] for k, v in prep.items()}
    rows = {k: {d: i for i, d in enumerate(v.index)} for k, v in dfs.items()}

    # Ereignisplan: Tag -> Liste (sleeve, Monat, Rolle) ; Rolle 'close'/'open'
    events = {}
    for sl in sleeves:
        prev = (None, 0)
        for m, tgt in sl.targets.items():
            tgt = tuple(tgt) if tgt is not None else (None, 0)
            # Close des alten Ziels und Open des neuen werden jeden Monat
            # neu bewertet (Re-Entry nach SL).
            for role, inst in (("close", prev[0]), ("open", tgt[0])):
                if inst is None or m not in xd.get(inst, {}):
                    continue
                day = xd[inst][m]
                if lag_days:
                    idx = dfs[inst].index
                    i = idx.get_loc(day) + lag_days
                    if i >= len(idx):
                        continue
                    day = idx[i]
                events.setdefault(day, []).append((sl, m, role, tgt))
            prev = tgt

    eq = account.equity0
    open_pos: dict[str, Pos] = {}
    eq_curve, trades, skipped = [], [], 0
    prev_bar = {}

    def close_pos(p, px, day, reason):
        nonlocal eq
        val = _notional_value(p.inst, p.units, px)
        eq -= val * costs.spread
        r_risk = p.units * abs(p.entry_px - p.stop) if p.stop else p.units * p.entry_px * stop.sizing_pct_if_none
        pnl_total = _pnl(p.inst, p.units, (px - p.entry_px) * p.dir, px)
        trades.append({"sleeve": p.sleeve, "inst": p.inst, "dir": p.dir, "entry_day": p.entry_day,
                       "exit_day": day, "entry_px": p.entry_px, "exit_px": px, "reason": reason,
                       "r": pnl_total / r_risk if r_risk else np.nan, "mae_pct": p.mae,
                       "notional": _notional_value(p.inst, p.units, p.entry_px), "pnl": pnl_total,
                       "days": (day - p.entry_day).days})
        del open_pos[p.sleeve]

    for day in cal:
        day_start_eq = eq
        # 1) bestehende Positionen bewerten: Swap, SL, Mark-to-Market
        for p in list(open_pos.values()):
            d = dfs[p.inst]
            if day not in rows[p.inst]:
                continue
            i = rows[p.inst][day]
            bar = d.iloc[i]
            if day == p.entry_day:
                prev_bar[p.sleeve] = (day, bar.close)
                continue
            pday, pclose = prev_bar[p.sleeve]
            days = (day - pday).days
            eq -= _notional_value(p.inst, p.units, pclose) * costs.swap_pa * days / 365.0
            adverse = (bar.low if p.dir > 0 else bar.high)
            p.mae = max(p.mae, (p.entry_px - adverse) * p.dir / p.entry_px)
            hit = p.stop and ((p.dir > 0 and bar.low <= p.stop) or (p.dir < 0 and bar.high >= p.stop))
            if hit:
                fill = min(bar.open, p.stop) if p.dir > 0 else max(bar.open, p.stop)
                eq += _pnl(p.inst, p.units, (fill - pclose) * p.dir, fill)
                close_pos(p, fill, day, "sl")
                continue
            if p.exit_flag:
                eq += _pnl(p.inst, p.units, (bar.close - pclose) * p.dir, bar.close)
                close_pos(p, bar.close, day, "daily_sma")
                continue
            eq += _pnl(p.inst, p.units, (bar.close - pclose) * p.dir, bar.close)
            prev_bar[p.sleeve] = (day, bar.close)
            if stop.kind == "trail":
                p.hi = max(p.hi, bar.close) if p.dir > 0 else min(p.hi, bar.close)
                k = stop.p(p.inst)
                new = p.hi - p.dir * k * bar.atr
                p.stop = max(p.stop, new) if p.dir > 0 else min(p.stop, new)
            if stop.daily_sma_exit and not np.isnan(bar.sma_lvl):
                if (p.dir > 0 and bar.close < bar.sma_lvl) or (p.dir < 0 and bar.close > bar.sma_lvl):
                    p.exit_flag = True  # Ausfuehrung am Schluss des naechsten Handelstags

        # 2) Monatsereignisse: erst Closes, dann Opens
        evs = sorted(events.get(day, []), key=lambda e: 0 if e[2] == "close" else 1)
        for sl, m, role, tgt in evs:
            p = open_pos.get(sl.name)
            if role == "close":
                if p is not None and (p.inst, p.dir) != tgt and day in rows[p.inst]:
                    close_pos(p, dfs[p.inst].iloc[rows[p.inst][day]].close, day, "signal")
                continue
            inst, direction = tgt
            if inst is None or direction == 0 or day not in rows[inst]:
                continue
            cur = open_pos.get(sl.name)
            if cur is not None and not sizing.rebalance:
                continue
            bar = dfs[inst].iloc[rows[inst][day]]
            px = bar.close
            if np.isnan(bar.atr):
                continue
            # SL-Abstand in Preis
            if stop.kind in ("pct", "mae_pct"):
                dist = stop.p(inst) * px
            elif stop.kind in ("atr", "trail", "mae_atr"):
                dist = stop.p(inst) * bar.atr
            else:
                dist = stop.sizing_pct_if_none * px
            risk = sizing.risk_pct * sl.weight * eq
            if sizing.vol_filter_half and not np.isnan(bar.volmed) and bar.vol20 > bar.volmed:
                risk *= 0.5
            units = risk / (dist / px if inst == "USDJPY" else dist)
            if sizing.vol_target and bar.vol20 > 0:
                cap_notional = sizing.vol_target * sl.weight * eq / bar.vol20
                units = min(units, cap_notional if inst == "USDJPY" else cap_notional / px)
            if sizing.open_risk_cap is not None:
                used = sum(_notional_value(q.inst, q.units, q.entry_px) *
                           (abs(q.entry_px - q.stop) / q.entry_px if q.stop else stop.sizing_pct_if_none)
                           for q in open_pos.values() if q.sleeve != sl.name)
                room = max(0.0, sizing.open_risk_cap * eq - used)
                per_unit = dist / px if inst == "USDJPY" else dist
                units = min(units, room / per_unit)
            if account.min_lot_check:
                ref_scale = bar.ref / px  # Broker-Preisniveau / Reihenpreis (SP500TR)
                lots_per_unit = ref_scale / CONTRACT[inst]
                lots = np.floor(units * lots_per_unit / LOT_STEP + 1e-9) * LOT_STEP
                if lots < MIN_LOT:
                    units = 0.0
                else:
                    units = lots / lots_per_unit
            if units <= 0:
                if cur is not None:   # Rebalancing unter Mindestlot -> ganz schliessen
                    close_pos(cur, px, day, "rebalance_minlot")
                else:
                    skipped += 1
                continue
            stop_px = (px - direction * dist) if stop.kind != "none" else 0.0
            if cur is not None:
                # Monats-Rebalancing (Faber-FAQ): Stueckzahl + SL neu, Spread nur aufs Delta
                if stop.kind == "trail" and cur.stop:
                    stop_px = max(stop_px, cur.stop) if direction > 0 else min(stop_px, cur.stop)
                delta = abs(units - cur.units)
                eq += _notional_value(inst, cur.units, px) * costs.spread  # close_pos zieht Spread ab
                close_pos(cur, px, day, "rebalance")
                eq -= _notional_value(inst, delta, px) * costs.spread
                hi = max(cur.hi, px) if direction > 0 else min(cur.hi, px)
            else:
                eq -= _notional_value(inst, units, px) * costs.spread
                hi = px
            open_pos[sl.name] = Pos(inst, direction, units, px, day, stop_px, sl.name, hi)
            prev_bar[sl.name] = (day, px)
        eq_curve.append((day, eq))
    eqs = pd.Series(dict(eq_curve))
    return {"equity": eqs, "trades": pd.DataFrame(trades), "skipped": skipped,
            "open_at_end": len(open_pos)}


def metrics(eqs):
    eqs = eqs[eqs.index.dayofweek < 5] if len(eqs) else eqs
    if len(eqs) < 2:
        return {}
    yrs = (eqs.index[-1] - eqs.index[0]).days / 365.25
    cagr = (eqs.iloc[-1] / eqs.iloc[0]) ** (1 / yrs) - 1
    dd = (eqs / eqs.cummax() - 1).min()
    dr = eqs.pct_change().dropna()
    return {"cagr_pct": round(cagr * 100, 3), "maxdd_pct": round(dd * 100, 2),
            "ratio": round(cagr / abs(dd), 3) if dd < 0 else np.nan,
            "worst_day_pct": round(dr.min() * 100, 2),
            "vol_pct": round(dr.std() * np.sqrt(252) * 100, 2)}
