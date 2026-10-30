"""Stufe 2: Dennis' Nachfass-Anweisungen aus „SMH Daily Update“ auslesen (Edge Card Regel 17,
Nutzerauftrag 28.10.2026). Textnachrichten mit Anweisungs-Stichworten gehen paketweise an
`claude.exe -p` (Abo); je Nachricht kommen Kontext (vorherige Nachrichten, beantwortete
Nachricht, bereits gelesenes Bild-Symbol) mit. Ergebnis je msg_id in instructions.jsonl.

Das OOS-Fenster (01.04.-16.10.2026) wird NICHT gelesen: das OOS ist durch A2 verbraucht,
Stufe 2 wird nur auf IS (Vorab-Blick) und vorwaerts gemessen.

    python -m fusion_lab.copy_trading.instructions --limit 20   # Probe
    python -m fusion_lab.copy_trading.instructions              # Rest (inkrementell)
"""

import argparse
import json
import re
import subprocess
import sys
import time

from fusion_lab.copy_trading.extract import CALLS, CHAT_DIR, OUT_DIR, claude_exe, latest, log, parse_array

INSTR = OUT_DIR / "instructions.jsonl"
BATCH = 20
MODEL = "sonnet"
# v2 (28.10.2026, Nutzer-Stichprobe 20/20 richtig, Grenzfaelle): bedingte Anweisungen = weich,
# Rueckblicke ("ich hoffe ihr habt BE gezogen") = keine Anweisung
PROMPT_VERSION = 2
IS_START, OOS_START, FWD_START = "2025-03-17", "2026-04-01", "2026-10-17"
KW = re.compile(r"\b(b\.?e\.?|break ?even|close[ds]?|schlie(ß|ss)\w*|raus\w*|invali\w*|risi[ck]\w*|"
                r":\s?[23]\b|re-?entry|teil\w*|partial\w*|sl|stop\w*|tp|profit\w*|glattstell\w*|"
                r"absichern|reduz\w*)\b", re.I)

PROMPT = """You classify follow-up messages in a German trading signal group ("SMH Daily Update").
The mentor posts trade ideas as chart images and later writes management instructions for
trades that are already running or pending. For EACH message below decide whether it contains
an instruction a copier should act on. Context lines (earlier messages, replied-to message,
symbol read from an attached chart image) are given to resolve which symbol is meant.

Output ONLY a JSON array, one object per message:
- "msg_id": int
- "instructions": list (empty if the message is no trade-management instruction, e.g. ads,
  events, recaps "full profit", explanations, links). Each item:
  - "action": "be" (move stop to break-even / "BE ziehen" / "close auf be"),
    "close" (close the trade now / "raus" / "schließen" / "out"),
    "invalide" (setup or pending order is invalid / cancelled / "nicht mehr interessant"),
    "partial" (take partial profits / "Teil Profite" / "profits nehmen"),
    "risk_split" (split risk between correlated trades, e.g. "Risiko :3"),
    "reentry_hint" (a re-entry may come / is possible, no concrete order)
  - "strength": "fest" if it is a direct instruction or the mentor says he does it himself
    ("BE ziehen", "bitte be ziehen", "ich zieh gold be", "raus"); "weich" if optional or
    hedged ("könnte", "kann man", "bei Bedarf", "muss man aber nicht", "würde wsh",
    "falls ...  würde ich"), and also "weich" if it is CONDITIONAL on a future price event
    ("closen wenn 1h Close > 102.30", "wenn der Markt über das High geht, raus")
  - Retrospective remarks are NOT instructions: "ich hoffe ihr habt BE gezogen", "wer BE
    gezogen hat ...", "hättet ihr ... können" -> no item.
  - "symbols": list of normalised symbols the instruction refers to: EURUSD, GBPUSD, USDJPY,
    USDCAD, USDCHF, AUDUSD, NZDUSD, EURGBP, EURJPY, GBPJPY, AUDJPY, CHFJPY, AUDNZD, XAUUSD,
    XAGUSD, US500, NAS100, US30, USOIL. Slang: EU=EURUSD, GU=GBPUSD, UJ=USDJPY, UC/UCAD=USDCAD,
    UCHF=USDCHF, AU=AUDUSD, NU=NZDUSD, EG=EURGBP, EJ=EURJPY, GJ=GBPJPY, Gold=XAUUSD,
    Silber=XAGUSD, Nas/Nasdaq=NAS100, Dow/US30=US30, SPX/US500=US500, Öl=USOIL. If the message
    has no symbol, take it from the replied-to message or the attached image symbol, else from
    the immediately preceding messages (same topic, within minutes). Empty list if unclear.
  - "symbol_source": "text" | "reply" | "image" | "context" | "none"
  - "scope": which call it refers to: "today" (setup from today's update), "yesterday",
    "last_week", or "any" (no time reference)
  - "split": integer k for risk_split (e.g. 3 for ":3"), else null
  - "fraction": for partial: fraction to close if stated (0.5 for "Hälfte"), else null
- "note": very short German reason

Messages:
"""


def _img_symbols() -> dict:
    out = {}
    if CALLS.exists():
        for r in latest(CALLS):
            x = r.get("read") or {}
            if x.get("symbol"):
                out[r["msg_id"]] = x["symbol"]
    return out


def _in_window(date: str) -> bool:
    return IS_START <= date < OOS_START or date >= FWD_START


def candidates(msgs: list[dict]) -> list[dict]:
    return [r for r in msgs if _in_window(r["date"]) and KW.search(r["text"] or "")]


def pending(msgs: list[dict]) -> list[dict]:
    done = set()
    if INSTR.exists():
        for l in open(INSTR, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                if r.get("prompt_version") == PROMPT_VERSION and r.get("read") is not None:
                    done.add(r["msg_id"])
    return [r for r in candidates(msgs) if r["id"] not in done]


def _fmt(r: dict, img: dict) -> str:
    sym = img.get(r["id"])
    t = (r["text"] or "").replace("\n", " / ")[:400]
    return f'[{r["date"][:16]} UTC, sender {r["sender_id"]}{", image symbol " + sym if sym else ""}] "{t}"'


def run_batch(exe: str, batch: list[dict], by_id: dict, msgs: list[dict], img: dict) -> list[dict]:
    pos = {r["id"]: i for i, r in enumerate(msgs)}
    blocks = []
    for r in batch:
        i = pos[r["id"]]
        ctx = [m for m in msgs[max(0, i - 4):i] if m["date"][:10] >= r["date"][:10]][-3:]
        lines = [f"### msg_id {r['id']}: {_fmt(r, img)}"]
        if r.get("reply_to") in by_id:
            lines.append(f"  replied-to: {_fmt(by_id[r['reply_to']], img)}")
        for m in ctx:
            lines.append(f"  earlier: {_fmt(m, img)}")
        blocks.append("\n".join(lines))
    res = subprocess.run([exe, "-p", "--model", MODEL, "--output-format", "json"],
                         input=PROMPT + "\n\n".join(blocks), capture_output=True, text=True,
                         encoding="utf-8", timeout=900, cwd=str(OUT_DIR))
    if res.returncode != 0:
        raise RuntimeError(f"claude.exe rc={res.returncode}: {(res.stderr or res.stdout)[-500:]}")
    items = parse_array(json.loads(res.stdout).get("result", ""))
    got = {int(x["msg_id"]): x for x in items if "msg_id" in x}
    return [{"msg_id": r["id"], "date": r["date"], "sender_id": r["sender_id"], "text": r["text"],
             "reply_to": r.get("reply_to"), "model": MODEL, "prompt_version": PROMPT_VERSION,
             "read": got.get(r["id"])} for r in batch]


def load() -> list[dict]:
    """Je msg_id der letzte gelesene Datensatz der aktuellen Prompt-Version."""
    best = {}
    if INSTR.exists():
        for l in open(INSTR, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                if r.get("prompt_version") == PROMPT_VERSION and r.get("read") is not None:
                    best[r["msg_id"]] = r
    return sorted(best.values(), key=lambda r: r["msg_id"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--limit", type=int)
    args = ap.parse_args(argv)
    msgs = [json.loads(l) for l in open(CHAT_DIR / "messages.jsonl", encoding="utf-8")]
    by_id = {r["id"]: r for r in msgs}
    img = _img_symbols()
    todo = pending(msgs)
    if args.limit:
        todo = todo[:args.limit]
    exe = claude_exe()
    log(f"Anweisungen: {len(todo)} Nachrichten offen, Pakete zu {BATCH}")
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        recs, attempt, wait_min = None, 0, 0
        while attempt < 4:   # gleiche Abo-Limit-Logik wie extract.py
            time.sleep(wait_min * 60)
            try:
                recs = run_batch(exe, batch, by_id, msgs, img)
                break
            except Exception as e:
                if "usage_limit_reached" in str(e):
                    log(f"  Paket ab {batch[0]['id']}: Abo-Kontingent leer, warte 30 Min.")
                    wait_min = 30
                    continue
                attempt += 1
                wait_min = (5, 10, 20, 0)[attempt - 1]
                log(f"  Paket ab {batch[0]['id']}: Versuch {attempt} fehlgeschlagen: {str(e)[-300:]}")
        if recs is None:
            continue
        with open(INSTR, "a", encoding="utf-8") as fh:
            for rec in recs:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        log(f"  {min(i + BATCH, len(todo))}/{len(todo)}")
    log("Anweisungen fertig")
    return 0


if __name__ == "__main__":
    sys.exit(main())
