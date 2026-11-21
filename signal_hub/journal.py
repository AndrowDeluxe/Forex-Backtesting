"""Journal (CSV) mit einfacher Datei-Sperre, weil Scan- und Listener-Task gleichzeitig schreiben koennen."""

from __future__ import annotations

import contextlib
import json
import os
import time

import pandas as pd

from signal_hub import config

TIME_COLS = ("signal", "einstieg", "gueltig_bis", "erstellt", "entschieden_um", "erinnern_um",
             "p_sig_einstieg_t", "p_sig_exit_t", "p_conf_einstieg_t", "p_conf_exit_t")


@contextlib.contextmanager
def locked(timeout: float = 60.0):
    config.LOCKFILE.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    while True:
        try:
            fd = os.open(config.LOCKFILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                if time.time() - config.LOCKFILE.stat().st_mtime > 300:   # verwaiste Sperre
                    config.LOCKFILE.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            if time.time() - t0 > timeout:
                raise TimeoutError("Journal-Sperre nicht frei")
            time.sleep(0.5)
    try:
        yield
    finally:
        os.close(fd)
        config.LOCKFILE.unlink(missing_ok=True)


def load(path=None) -> pd.DataFrame:
    path = path or config.JOURNAL
    if not os.path.exists(path):
        return pd.DataFrame(columns=["id", "status"])
    df = pd.read_csv(path, dtype={"id": str, "status": str})
    for c in TIME_COLS:
        if c in df:
            df[c] = pd.to_datetime(df[c], utc=True, errors="coerce", format="ISO8601").dt.tz_convert(config.TZ)
    return df


def save(df: pd.DataFrame, path=None) -> None:
    path = path or config.JOURNAL
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def upsert(df: pd.DataFrame, row: dict) -> pd.DataFrame:
    if "id" in df and (df["id"] == row["id"]).any():
        i = df.index[df["id"] == row["id"]][0]
        for k, v in row.items():
            df.loc[i, k] = v
        return df
    return pd.concat([df, pd.DataFrame([row])], ignore_index=True)


def update(df: pd.DataFrame, sid: str, **kw) -> pd.DataFrame:
    i = df.index[df["id"] == sid]
    for k, v in kw.items():
        if k not in df:
            df[k] = pd.Series([None] * len(df), dtype=object)
        df.loc[i, k] = v
    return df


def load_state() -> dict:
    try:
        return json.loads(config.STATE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    config.STATE.parent.mkdir(parents=True, exist_ok=True)
    config.STATE.write_text(json.dumps(state, indent=1, default=str), encoding="utf-8")
