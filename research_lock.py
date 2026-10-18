"""Overfitting-Sperre: IS / OOS / Tresor technisch trennen.

Regelwerk: knowledge/areas/overfitting-sperre.md (Nutzerentscheid 2026-10-05,
nach dem Befund, dass die ORB-Konfiguration ab Stage 2 direkt auf OOS-Zahlen
ausgewaehlt wurde). Kurzform:

1. Split je Strategie EINMAL registrieren (vor Phase 4) -- danach unveraenderlich.
2. Optimieren nur auf `is_only(...)`-Daten.
3. Jede getestete Variante ins Trial-Register (`log_trials`) -- Grundlage fuer
   die Deflated-Sharpe-Korrektur (`deflated_sharpe`).
4. Gewinner einfrieren (`freeze`), erst dann `unseal("oos")`, danach
   `unseal("tresor")`. Jede Stufe genau einmal; ein zweites Oeffnen bricht ab.
5. Optional (seit 2026-10-18): ein Blindtest-Zeitraum VOR dem IS (`register_blind`,
   vor dem Einfrieren), wenn OOS/Tresor einer Strategie schon verbraucht sind.
   `unseal("blind")` nach `freeze`, genau einmal, unabhaengig von OOS/Tresor.

Zustand liegt git-getrackt unter knowledge/_research_lock/<strategy>.json
(+ .jsonl-Protokoll), damit die Sperre auch ueber Sessions hinweg haelt.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

LOCK_DIR = Path(__file__).resolve().parent / "knowledge" / "_research_lock"
STAGES = ("oos", "tresor", "forward", "blind")


class LockError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def config_hash(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()


@dataclass
class Lock:
    strategy: str
    lock_dir: Path = LOCK_DIR

    @property
    def path(self) -> Path:
        return self.lock_dir / f"{self.strategy}.json"

    @property
    def log_path(self) -> Path:
        return self.lock_dir / f"{self.strategy}.jsonl"

    # --- Zustand ---------------------------------------------------------
    def _load(self) -> dict:
        if not self.path.exists():
            raise LockError(f"{self.strategy}: kein Split registriert (register_split zuerst)")
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, state: dict) -> None:
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    def _log(self, event: str, **data) -> None:
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": _now(), "event": event, **data}, ensure_ascii=False, default=str) + "\n")

    # --- 1. Split ----------------------------------------------------------
    def register_split(self, is_start: str, is_end: str, oos_end: str, tresor_end: str | None = None) -> dict:
        split = {"is_start": is_start, "is_end": is_end, "oos_end": oos_end, "tresor_end": tresor_end}
        if not (pd.Timestamp(is_start) < pd.Timestamp(is_end) < pd.Timestamp(oos_end)):
            raise LockError(f"Split nicht aufsteigend: {split}")
        if self.path.exists():
            state = self._load()
            if state["split"] != split:
                raise LockError(f"{self.strategy}: Split ist bereits {state['split']} -- nachtraegliches "
                                f"Verschieben ist gesperrt")
            return state
        state = {"strategy": self.strategy, "split": split, "registered": _now(), "trials": 0,
                 "frozen": None, "unsealed": {}, "forward": None}
        self._save(state)
        self._log("register_split", **split)
        return state

    def register_forward(self, start: str, eval_date: str, min_trades: int) -> dict:
        """Echter blinder Test auf Live-/Forward-Daten ab `start`. Oeffnen erst,
        wenn `min_trades` erreicht sind ODER `eval_date` erreicht ist -- vorab
        festgelegt, danach unveraenderlich (seit 2026-10-06)."""
        state = self._load()
        fw = {"start": start, "eval_date": eval_date, "min_trades": int(min_trades)}
        if state.get("forward") not in (None, fw):
            raise LockError(f"{self.strategy}: Forward-Regel ist bereits {state['forward']} -- gesperrt")
        if state.get("forward") is None:
            state["forward"] = fw
            self._save(state)
            self._log("register_forward", **fw)
        return state

    def register_blind(self, start: str, end: str) -> dict:
        """Blindtest-Zeitraum vor dem IS (z. B. aeltere, nie benutzte Daten). Nur vor dem
        Einfrieren registrierbar, danach unveraenderlich; muss vollstaendig vor is_start liegen."""
        state = self._load()
        bl = {"start": start, "end": end}
        if not (pd.Timestamp(start) < pd.Timestamp(end) < pd.Timestamp(state["split"]["is_start"])):
            raise LockError(f"{self.strategy}: Blindtest muss aufsteigend und vor is_start liegen: {bl}")
        if state.get("blind") not in (None, bl):
            raise LockError(f"{self.strategy}: Blindtest ist bereits {state['blind']} -- gesperrt")
        if state.get("blind") is None:
            if state["frozen"] is not None:
                raise LockError(f"{self.strategy}: Blindtest nach dem Einfrieren registrieren ist gesperrt")
            state["blind"] = bl
            self._save(state)
            self._log("register_blind", **bl)
        return state

    @property
    def split(self) -> dict:
        return self._load()["split"]

    # --- 2. IS-Zugriff -----------------------------------------------------
    def _slice(self, obj, start, end):
        idx = obj.index
        tz = getattr(idx, "tz", None)

        def ts(x, end_of_day=False):
            t = pd.Timestamp(x)
            if end_of_day:
                t = t + pd.Timedelta(days=1)
            return t.tz_localize(tz) if tz is not None else t

        mask = (idx >= ts(start)) & (idx < ts(end, end_of_day=True))
        return obj[mask]

    def is_only(self, obj):
        s = self.split
        return self._slice(obj, s["is_start"], s["is_end"])

    # --- 3. Trial-Register -------------------------------------------------
    def log_trials(self, n: int, note: str = "") -> int:
        state = self._load()
        if state["frozen"] is not None:
            raise LockError(f"{self.strategy}: Konfiguration ist eingefroren -- neue Versuche "
                            f"waeren Optimierung nach dem Einfrieren")
        state["trials"] += int(n)
        self._save(state)
        self._log("trials", n=int(n), total=state["trials"], note=note)
        return state["trials"]

    @property
    def trials(self) -> int:
        return self._load()["trials"]

    # --- 4. Einfrieren + Entsiegeln ---------------------------------------
    def freeze(self, config: dict) -> str:
        state = self._load()
        h = config_hash(config)
        if state["frozen"] is not None:
            if state["frozen"]["hash"] != h:
                raise LockError(f"{self.strategy}: bereits eine andere Konfiguration eingefroren")
            return h
        state["frozen"] = {"hash": h, "config": config, "ts": _now()}
        self._save(state)
        self._log("freeze", hash=h)
        return h

    def unseal(self, stage: str, cfg_hash: str, n_forward_trades: int | None = None, today: str | None = None):
        """Gibt (start, end) der Stufe frei -- genau einmal je Stufe."""
        if stage not in STAGES:
            raise LockError(f"unbekannte Stufe {stage!r}")
        state = self._load()
        if state["frozen"] is None:
            raise LockError(f"{self.strategy}: erst freeze(), dann unseal({stage!r})")
        if state["frozen"]["hash"] != cfg_hash:
            raise LockError(f"{self.strategy}: Hash passt nicht zur eingefrorenen Konfiguration")
        if stage == "tresor" and "oos" not in state["unsealed"]:
            raise LockError(f"{self.strategy}: Tresor erst nach OOS")
        if stage in state["unsealed"]:
            raise LockError(f"{self.strategy}: {stage} wurde bereits am {state['unsealed'][stage]} geoeffnet")
        if stage == "blind" and state.get("blind") is None:
            raise LockError(f"{self.strategy}: kein Blindtest registriert")
        if stage == "forward":
            fw = state.get("forward")
            if fw is None:
                raise LockError(f"{self.strategy}: keine Forward-Regel registriert")
            if "oos" not in state["unsealed"]:
                raise LockError(f"{self.strategy}: Forward erst nach OOS")
            day = pd.Timestamp(today) if today else pd.Timestamp.now()
            if not ((n_forward_trades or 0) >= fw["min_trades"] or day >= pd.Timestamp(fw["eval_date"])):
                raise LockError(f"{self.strategy}: Forward noch versiegelt -- {n_forward_trades or 0} von "
                                f"{fw['min_trades']} Trades, Stichtag {fw['eval_date']}")
        state["unsealed"][stage] = _now()
        self._save(state)
        self._log("unseal", stage=stage, hash=cfg_hash)
        s = state["split"]
        if stage == "oos":
            return (pd.Timestamp(s["is_end"]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), s["oos_end"]
        if stage == "forward":
            return state["forward"]["start"], None
        if stage == "blind":
            return state["blind"]["start"], state["blind"]["end"]
        return (pd.Timestamp(s["oos_end"]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d"), s["tresor_end"]

    def stage_slice(self, obj, stage: str):
        """Daten einer bereits geoeffneten Stufe (fuer Auswertung, nicht zum Optimieren)."""
        state = self._load()
        if stage not in state["unsealed"]:
            raise LockError(f"{self.strategy}: {stage} ist noch versiegelt")
        s = state["split"]
        if stage == "blind":
            return self._slice(obj, state["blind"]["start"], state["blind"]["end"])
        if stage == "oos":
            start = (pd.Timestamp(s["is_end"]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            return self._slice(obj, start, s["oos_end"])
        start = (pd.Timestamp(s["oos_end"]) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        return self._slice(obj, start, s["tresor_end"] or "2100-01-01")


def deflated_sharpe(sr: float, n_obs: int, n_trials: int, skew: float = 0.0, kurt: float = 3.0,
                    sr_var_trials: float | None = None) -> float:
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014).

    sr: Sharpe je Beobachtung (z. B. Ø R / Std R je Trade), n_obs: Anzahl
    Beobachtungen, n_trials: Anzahl getesteter Varianten. sr_var_trials:
    Varianz der Sharpe-Werte ueber die Versuche (ohne Angabe: 1/n_obs, also
    reines Schaetzrauschen). Rueckgabe: Wahrscheinlichkeit, dass der wahre
    Sharpe > 0 ist, nachdem man den besten von n_trials ausgewaehlt hat.
    """
    from statistics import NormalDist
    nd = NormalDist()
    if n_trials < 1 or n_obs < 2:
        raise ValueError("n_trials >= 1 und n_obs >= 2 noetig")
    var = sr_var_trials if sr_var_trials is not None else 1.0 / n_obs
    gamma = 0.5772156649
    if n_trials == 1:
        sr0 = 0.0
    else:
        sr0 = math.sqrt(var) * ((1 - gamma) * nd.inv_cdf(1 - 1.0 / n_trials)
                                + gamma * nd.inv_cdf(1 - 1.0 / (n_trials * math.e)))
    denom = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4 * sr ** 2))
    return nd.cdf((sr - sr0) * math.sqrt(n_obs - 1) / denom)
