"""mt5-robot-tester unter der Overfitting-Sperre laufen lassen.

Umschliesst ~/.claude/skills/mt5-robot-tester/scripts/mt5_batch_tester.py:
  - vor dem Lauf: Sperre muss existieren und darf nicht eingefroren sein, der
    Tester-Zeitraum (common.from/to) muss komplett im IS liegen, und das
    Terminal darf keines sein, das eine *-Bridge benutzt (Live-Konten).
  - nach dem Lauf: neu gelaufene Tester-Durchgaenge aus state.json zaehlen und
    per Lock.log_trials() eintragen.

Aufruf (alle uebrigen Argumente gehen unveraendert an den Tester):
    python scripts/mt5_tester_lock.py --lock <sperre> --config cfg.json \
        --output-dir skill_test/results/mt5_pipeline [--terminal-path ...] [--dry-run]

Regelwerk: knowledge/areas/overfitting-sperre.md. Zaehlung Runde 3: der Tester
speichert die Einzel-Passes nicht, deshalb Bereichsformel (2*range/step + 1 je
Parameter) -- eher zu viel als zu wenig gezaehlt.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from research_lock import Lock, LockError  # noqa: E402

TESTER = Path.home() / ".claude/skills/mt5-robot-tester/scripts/mt5_batch_tester.py"
BRIDGE_ROOT = Path.home()
RICHTWERT_PUNKTE = 9
_TERMINAL_RE = re.compile(r"[A-Za-z]:\\[^\"'\n]*?terminal64\.exe", re.IGNORECASE)


def _norm(p: str | Path) -> str:
    return os.path.normcase(os.path.normpath(str(p)))


def bridge_terminals(root: Path = BRIDGE_ROOT) -> set[str]:
    """Alle terminal64.exe-Pfade, die in *-Bridge-Ordnern vorkommen (nur lesen)."""
    found: set[str] = set()
    for bridge in root.glob("*-Bridge"):
        for f in bridge.rglob("*"):
            if f.suffix.lower() not in {".py", ".json", ".ps1", ".bat", ".ini"} or not f.is_file():
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            found.update(_norm(m.replace("\\\\", "\\")) for m in _TERMINAL_RE.findall(text))
    return found


def _tester_date(s: str) -> pd.Timestamp:
    return pd.Timestamp(s.replace(".", "-"))


def resolve_terminal(cli: str | None, config: dict) -> str | None:
    # gleiche Reihenfolge wie im Tester: CLI > Config > Umgebungsvariable
    return cli or config.get("terminal_path") or os.environ.get("MT5_TERMINAL_PATH")


def preflight(lock: Lock, config: dict, terminal: str | None, dry_run: bool,
              bridges: set[str] | None = None) -> None:
    split = lock.split  # LockError, wenn keine Sperre registriert ist
    if lock._load()["frozen"] is not None:
        raise LockError(f"{lock.strategy}: eingefroren -- weitere Tester-Laeufe waeren Optimierung "
                        f"nach dem Einfrieren")
    common = config.get("common", {})
    if "from" not in common or "to" not in common:
        raise LockError("Tester-Config ohne common.from/common.to -- Zeitraum muss explizit im IS liegen")
    start, end = _tester_date(common["from"]), _tester_date(common["to"])
    is_start, is_end = pd.Timestamp(split["is_start"]), pd.Timestamp(split["is_end"])
    if start < is_start or end > is_end:
        raise LockError(f"Tester-Zeitraum {start.date()}..{end.date()} liegt nicht im IS "
                        f"{is_start.date()}..{is_end.date()} der Sperre {lock.strategy}")
    if dry_run:
        return
    if not terminal:
        raise LockError("Kein terminal_path -- bitte ein eigenes Test-Terminal explizit angeben")
    bridges = bridge_terminals() if bridges is None else bridges
    if _norm(terminal) in bridges:
        raise LockError(f"{terminal} wird von einer Live-Bridge benutzt -- nur ein eigenes "
                        f"Test-Terminal ist erlaubt")


def passes_per_bot(st: dict, r3_values_per_param: int) -> int:
    n = len(st.get("round1_passes") or [])
    if st.get("round2"):
        n += 1
    r3 = st.get("round3") or {}
    n += len(r3.get("per_param") or []) * r3_values_per_param
    if r3.get("final_metrics") and r3.get("status") == "ok":
        n += 1
    return n


def count_passes(state_path: Path, config: dict) -> tuple[int, int]:
    """(Durchgaenge gesamt, optimierte Parameter gesamt) laut state.json."""
    if not state_path.exists():
        return 0, 0
    state = json.loads(state_path.read_text(encoding="utf-8"))
    r3 = config.get("round3", {})
    per_param = int(round(2 * r3.get("range_pct", 0.5) / r3.get("step_pct", 0.05))) + 1
    total = params = 0
    for st in (state.get("bots") or {}).values():
        total += passes_per_bot(st, per_param)
        params += len((st.get("round3") or {}).get("per_param") or [])
    return total, params


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lock", required=True, help="Name der research_lock-Sperre")
    ap.add_argument("--config", required=True)
    ap.add_argument("--output-dir", default="reports/mt5_pipeline")
    ap.add_argument("--terminal-path", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args, rest = ap.parse_known_args(argv)

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    lock = Lock(args.lock)
    terminal = resolve_terminal(args.terminal_path, config)
    preflight(lock, config, terminal, args.dry_run)

    state_path = Path(args.output_dir) / "state.json"
    before, params_before = count_passes(state_path, config)

    cmd = [sys.executable, str(TESTER), "--config", args.config, "--output-dir", args.output_dir, *rest]
    if args.terminal_path:
        cmd += ["--terminal-path", args.terminal_path]
    if args.dry_run:
        cmd.append("--dry-run")
    rc = subprocess.run(cmd).returncode

    if args.dry_run:
        print("Dry-Run: nichts gezaehlt.")
        return rc
    after, params_after = count_passes(state_path, config)
    neu = max(after - before, 0)
    if neu:
        total = lock.log_trials(neu, note=f"mt5-robot-tester {args.output_dir}")
        print(f"{neu} Tester-Durchgaenge gezaehlt, Sperre {lock.strategy} jetzt bei {total} Versuchen.")
    else:
        print("Keine neuen Tester-Durchgaenge -- nichts gezaehlt.")
    if params_after > RICHTWERT_PUNKTE:
        print(f"WARNUNG: {params_after} optimierte Parameter -- ueber dem Richtwert von "
              f"{RICHTWERT_PUNKTE}; bitte begruenden (knowledge/areas/overfitting-sperre.md).")
    return rc


if __name__ == "__main__":
    try:
        sys.exit(main())
    except LockError as e:
        print(f"ABBRUCH: {e}", file=sys.stderr)
        sys.exit(2)
