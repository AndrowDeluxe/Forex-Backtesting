"""Ledger (decisions.csv, runs.csv), Kontroll-Ratings und Auswertung (summary.json). Nur Standardbibliothek."""

from __future__ import annotations

import csv
import json
import math
import random
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path

from fusion_lab.agent_forward import config as C

FIELDS = ["datum", "ticker", "quelle", "rating", "score", "rendite_5t", "alpha_5t", "abgerechnet",
          "begruendung", "sekunden", "llm_aufrufe", "kosten_usd", "fehler"]
RUN_FIELDS = ["lauf", "datum", "titel_ok", "titel_fehler", "abgerechnet", "sekunden", "llm_aufrufe", "kosten_usd",
              "hinweis"]
RATINGS = list(C.SCORE)


# --- Ein-/Ausgabe ---------------------------------------------------------------------------------------------

def read(path: Path = C.DECISIONS) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(rows: list[dict], path: Path = C.DECISIONS, fields: list[str] = FIELDS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def append_run(row: dict, path: Path = C.RUNS) -> None:
    rows = read(path)
    rows.append(row)
    write(rows, path, RUN_FIELDS)


def has_entry(rows: list[dict], datum: str, ticker: str, quelle: str) -> bool:
    return any(r["datum"] == datum and r["ticker"] == ticker and r["quelle"] == quelle for r in rows)


# --- Kontrollen -----------------------------------------------------------------------------------------------

def control_ratings(datum: str, ticker: str, ret_20d: float | None) -> dict[str, str | None]:
    """Drei Vergleichsregeln, reproduzierbar: immer Buy, Zufall (Seed Datum+Titel), Momentum 20 Tage."""
    rnd = random.Random(f"{datum}|{ticker}")
    return {
        "always_buy": "Buy",
        "random": rnd.choice(RATINGS),
        "momentum": None if ret_20d is None else ("Buy" if ret_20d > 0 else "Sell"),
    }


# --- Auswertung -----------------------------------------------------------------------------------------------

def _f(x) -> float | None:
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None


def _sign(x: float) -> int:
    return (x > 0) - (x < 0)


def pnl(score: float, alpha: float) -> float:
    """Richtungs-Alpha eines Entscheids: Long bei positivem, Short bei negativem Score, Hold = 0."""
    return _sign(score) * alpha


def week_of(datum: str) -> str:
    y, w, _ = date.fromisoformat(datum).isocalendar()
    return f"{y}-W{w:02d}"


def t_stat(values: list[float]) -> float | None:
    if len(values) < 3:
        return None
    sd = statistics.stdev(values)
    return None if sd == 0 else statistics.mean(values) / (sd / math.sqrt(len(values)))


def summarize(rows: list[dict], runs: list[dict] | None = None, start: str = C.START) -> dict:
    official = [r for r in rows if r["datum"] >= start]
    probe = [r for r in rows if r["datum"] < start]
    weeks_all = sorted({week_of(r["datum"]) for r in official if _f(r["alpha_5t"]) is not None})
    quellen, kurve = {}, {}
    for q, label in C.SOURCES.items():
        mine = [r for r in official if r["quelle"] == q and _f(r["score"]) is not None]
        settled = [r for r in mine if _f(r["alpha_5t"]) is not None]
        p = [pnl(_f(r["score"]), _f(r["alpha_5t"])) for r in settled]
        weekly: dict[str, list[float]] = {}
        for r, v in zip(settled, p):
            weekly.setdefault(week_of(r["datum"]), []).append(v)
        wmeans = [statistics.mean(weekly[w]) for w in sorted(weekly)]
        directional = [(r, v) for r, v in zip(settled, p) if _f(r["score"]) != 0]
        je_rating = {}
        for rt in RATINGS:
            a = [_f(r["alpha_5t"]) for r in settled if r["rating"] == rt]
            je_rating[rt] = {"n": len(a), "alpha": None if not a else 100 * statistics.mean(a)}
        quellen[q] = {
            "label": label, "n": len(mine), "offen": len(mine) - len(settled), "abgerechnet": len(settled),
            "richtungs_alpha": None if not p else 100 * statistics.mean(p),
            "summe": None if not p else 100 * sum(p),
            "trefferquote": None if not directional else 100 * sum(v > 0 for _, v in directional) / len(directional),
            "wochen": len(wmeans), "t_woche": t_stat(wmeans), "je_rating": je_rating,
        }
        cum, acc = [], 0.0
        for w in weeks_all:
            if w in weekly:
                acc += 100 * statistics.mean(weekly[w])
            cum.append(round(acc, 4))
        kurve[q] = cum

    agent_rows = sorted((r for r in rows if r["quelle"] == "agent"), key=lambda r: (r["datum"], r["ticker"]),
                        reverse=True)
    letzte = [{"datum": r["datum"], "ticker": r["ticker"], "rating": r["rating"] or "–",
               "alpha": None if _f(r["alpha_5t"]) is None else 100 * _f(r["alpha_5t"]),
               "rendite": None if _f(r["rendite_5t"]) is None else 100 * _f(r["rendite_5t"]),
               "begruendung": r["begruendung"], "fehler": r["fehler"], "probe": r["datum"] < start}
              for r in agent_rows[:25]]
    a, ctrl = quellen["agent"], [quellen[q] for q in C.SOURCES if q != "agent"]
    schlaegt = (a["richtungs_alpha"] is not None
                and all(c["richtungs_alpha"] is not None and a["richtungs_alpha"] > c["richtungs_alpha"] for c in ctrl))
    eval_ab = (datetime.fromisoformat(start) + timedelta(weeks=C.EVAL_AFTER_WEEKS)).date().isoformat()
    return {
        "stand": max((r["datum"] for r in rows), default=None),
        "start": start, "auswertung_ab": eval_ab, "huerde": C.HURDLE,
        "korb": C.TICKERS, "haltedauer": C.HOLDING_DAYS, "benchmark": C.BENCHMARK,
        "modelle": {"schnell": C.QUICK_MODEL, "tief": C.DEEP_MODEL},
        "quellen": quellen, "wochen": weeks_all, "kurve": kurve,
        "wochen_start": [date.fromisocalendar(int(w[:4]), int(w[6:]), 1).isoformat() for w in weeks_all],
        "zwischenstand": {"schlaegt_kontrollen": schlaegt, "t_ok": (a["t_woche"] or 0) > 2},
        "probe_eintraege": len(probe), "letzte": letzte, "laeufe": (runs or [])[-10:][::-1],
    }


def write_summary(path: Path = C.SUMMARY) -> dict:
    s = summarize(read(), read(C.RUNS))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(s, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return s
