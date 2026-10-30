"""Chartbilder aus „SMH Daily Update“ per Claude Code (Abo, `claude.exe -p`) auslesen.

Edge Card Regel 2: je Bild Symbol, Timeframe, Typ, Richtung, Level. Je Paket gehen
BATCH Bilder an einen claude.exe-Aufruf (nur Read-Tool), die Antwort ist ein JSON-Array.
Ergebnis je msg_id in fusion_lab/data/copy_trading/calls.jsonl; schon gelesene Bilder
werden uebersprungen, ein Abbruch verliert hoechstens das laufende Paket.

    python -m fusion_lab.copy_trading.extract --since 2026-07-16 --limit 16   # Probe
    python -m fusion_lab.copy_trading.extract --since 2026-07-16              # Rest
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from fusion_lab._secrets import RAW_DIR

CHAT_DIR = RAW_DIR / "telegram" / "SMH Daily Update__2552394198"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "copy_trading"
CALLS = OUT_DIR / "calls.jsonl"
LOG = OUT_DIR / "extract.log"
BATCH = 8
MODEL = "sonnet"
# v2 (21.10.2026, nach Nutzer-Stichprobe 9/50 falsch): Status je Setup, Ordertyp,
# Alternativen, Zielzonen, Richtung beim Positionswerkzeug aus den Farben
# v3 (21.10.2026): Watch-Charts nur objektiv lesen (erster Schenkel, Umkehrpunkt, Pfadende);
# ob die Zone Einstieg oder Ziel ist, entscheidet die Simulation (Nutzer: beide Lesarten testen)
PROMPT_VERSION = 3
LINK_PREVIEWS = ("zoom.us", "youtu", "kahoot", "whatsapp", "checkout.", "tiktok", "pricing/")

PROMPT = """You read TradingView chart screenshots posted in a German trading signal group.
Use the Read tool to open each image file listed below, look at it carefully, then answer.

For EACH image return one JSON object. Output ONLY a JSON array of these objects, no prose.

Fields:
- "msg_id": int (given below)
- "is_call": true if the image shows a forward-looking trade setup: either (A) a TradingView
  long/short position tool (red + green/teal boxes with price labels on the right axis), or
  (B) a marked zone (grey/coloured rectangle) together with a drawn path or arrow that shows
  the expected direction. false otherwise.
- "no_call_reason": null or one of "dxy_or_not_tradeable", "recap_already_played_out",
  "active_trade_only", "info_only", "no_levels_or_path", "not_a_chart", "other"
- "symbol": normalised: EURUSD, GBPUSD, USDJPY, USDCAD, USDCHF, AUDUSD, NZDUSD, EURGBP, EURJPY,
  GBPJPY, AUDJPY, CHFJPY, AUDNZD, XAUUSD, XAGUSD, US500, NAS100, US30, USOIL, DXY, or other
  ticker as written
- "chart_tf": timeframe from the header, e.g. "M5","M15","H1","H4","D1"
- "chart_created": text after "erstellt mit TradingView.com," in the top line, e.g.
  "Okt 08, 2026 23:49 UTC+2", or null
- "data_source": broker/feed in the header, e.g. "FXCM", "OANDA"
- "last_price": price of the last candle (header C value or the highlighted current price)
- "extends_right": true if the position tool / zone / drawn path extends to the right of the
  last candle (i.e. into the future)
- "setups": list (usually one). Each setup:
  - "type": "A" (position tool) or "B" (zone + path/arrow, no position tool)
  - "status": "new" (entry not reached yet, a fresh idea), "active" (the trade is already
    running/triggered: candles have already entered the position tool or the entry zone after
    it was drawn), or "info" (only context/levels, no trade intended)
  - "direction": "long" or "short". For a position tool decide ONLY from the colours: if the
    red (loss) box is ABOVE the entry it is a SHORT, if the red box is BELOW the entry it is a
    LONG.
  - "order_type": "limit" (entry better than current price: buy below / sell above), "stop"
    (entry beyond the current price in trade direction: buy stop above / sell stop below, e.g.
    after a liquidity grab or breakout), "market" (entry at the current price), or "zone"
    (type B zone without a precise entry price)
  - "alternative_group": null, or the same small integer for setups that are offered as
    ALTERNATIVES for the same idea (e.g. "either buy stop above 4200 or buy limit at 4143")
  - "entry", "sl", "tp": type A only: the exact prices printed in the axis labels of the
    position tool (entry = the grey/neutral label at the border between the red and green box,
    sl = the end of the red box, tp = the end of the green box). If a label is not printed,
    estimate from the axis and add the field name to "estimated".
  - "zone_top", "zone_bottom": price of the upper and lower edge of the marked zone (type B; for
    type A the zone if one is drawn too), estimated from the price axis
  - "path_end": price where the drawn path/arrow ends (type B), estimated from the axis
  - "leg1_direction": type B: "up" or "down" = direction of the FIRST segment of the drawn path,
    starting near the current price
  - "turn_price": type B: price where the drawn path changes direction (the hook/turning
    point), null if the path is straight. "direction" for type B = direction of the LAST
    segment (after the turn); for a straight path = leg1_direction.
  - Report what is DRAWN, do not decide whether a zone is meant as entry or as target. If the
    path ends inside a second zone, report that zone's middle as "path_end" and the zone where
    the path turns as the setup zone. If the path does not touch any zone, report the zone
    closest to the turning point.
  - "estimated": list of field names that were estimated rather than read from a printed label
- "confidence": 0..1 how sure you are about the levels
- "notes": short free text, e.g. "two zones", "label partly hidden"

IMPORTANT number format: the charts use German notation. "157,778" means 157.778 and
"7.823,2" means 7823.2. Always output plain JSON numbers with a dot as decimal separator.
Images that already show the outcome (candles already inside/through the box, posted to show
profit) are recaps: is_call false, reason "recap_already_played_out".
If an image shows an already running trade AND additionally a NEW zone/level for a further or
second entry, report the running trade with status "active" and the new entry as its own setup
with status "new". is_call is true only if at least one setup has status "new".
If several entry levels/zones are drawn for the same idea (e.g. first entry and re-entry
levels), report each as its own setup.

Images:
"""


def claude_exe() -> str:
    exts = sorted((Path.home() / ".vscode" / "extensions").glob("anthropic.claude-code-*"),
                  key=lambda p: [int(x) for x in re.findall(r"\d+", p.name.split("-")[2])[:3]],
                  reverse=True)
    for e in exts:
        exe = e / "resources" / "native-binary" / "claude.exe"
        if exe.exists():
            return str(exe)
    raise FileNotFoundError("claude.exe nicht gefunden (Claude-Code-Extension)")


def log(msg: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def pending(since: str, until: str | None) -> list[dict]:
    done = set()
    if CALLS.exists():
        for l in open(CALLS, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                if r.get("prompt_version", 1) == PROMPT_VERSION and r.get("read") is not None:
                    done.add(r["msg_id"])
    out = []
    for l in open(CHAT_DIR / "messages.jsonl", encoding="utf-8"):
        r = json.loads(l)
        f = r.get("media_file") or ""
        if not f.lower().endswith((".jpg", ".png")) or r["id"] in done:
            continue
        if r["date"] < since or (until and r["date"] >= until):
            continue
        if any(k in (r["text"] or "").lower() for k in LINK_PREVIEWS):
            continue  # Vorschaubild eines Zoom-/YouTube-/Shop-Links, kein Chart
        out.append(r)
    return out


def latest(path=CALLS) -> list[dict]:
    """Je msg_id nur der Datensatz der hoechsten Prompt-Version (spaeter gelesen gewinnt)."""
    best = {}
    for l in open(path, encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            v = r.get("prompt_version", 1)
            if r["msg_id"] not in best or v >= best[r["msg_id"]].get("prompt_version", 1):
                best[r["msg_id"]] = r
    return sorted(best.values(), key=lambda r: r["msg_id"])


def parse_array(text: str) -> list:
    m = re.search(r"\[.*\]", text, flags=re.S)
    if not m:
        raise ValueError("kein JSON-Array in der Antwort")
    return json.loads(m.group(0))


def run_batch(exe: str, batch: list[dict]) -> list[dict]:
    lines = []
    for r in batch:
        cap = (r["text"] or "").replace("\n", " ")[:300]
        lines.append(f'- msg_id {r["id"]}, posted {r["date"]} UTC, sender {r["sender_id"]}, '
                     f'caption "{cap}": {CHAT_DIR / "media" / r["media_file"]}')
    prompt = PROMPT + "\n".join(lines)
    res = subprocess.run([exe, "-p", "--model", MODEL, "--allowedTools", "Read",
                          "--output-format", "json"],
                         input=prompt, capture_output=True, text=True, encoding="utf-8",
                         timeout=900, cwd=str(CHAT_DIR))
    if res.returncode != 0:
        raise RuntimeError(f"claude.exe rc={res.returncode}: {(res.stderr or res.stdout)[-500:]}")
    env = json.loads(res.stdout)
    items = parse_array(env.get("result", ""))
    by_id = {int(x["msg_id"]): x for x in items if "msg_id" in x}
    out = []
    for r in batch:
        x = by_id.get(r["id"])
        rec = {"msg_id": r["id"], "date": r["date"], "sender_id": r["sender_id"],
               "caption": r["text"], "media_file": r["media_file"], "model": MODEL,
               "prompt_version": PROMPT_VERSION}
        rec.update({"read": x} if x else {"read": None, "error": "fehlt in Antwort"})
        out.append(rec)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--since", default="2026-07-16")
    ap.add_argument("--until")
    ap.add_argument("--limit", type=int, help="hoechstens so viele Bilder (Probe)")
    args = ap.parse_args(argv)
    exe = claude_exe()
    todo = pending(args.since, args.until)
    if args.limit:
        todo = todo[:args.limit]
    log(f"Start: {len(todo)} Bilder offen, Pakete zu {BATCH}, Modell {MODEL}")
    n_ok = 0
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        recs, attempt, wait_min = None, 0, 0
        while attempt < 4:
            # Abo-Ratenlimit: nach ~25 Min. Dauerlauf brachen Aufrufe ab (20.10.). Bei
            # "usage_limit_reached" (Kontingent leer, 429) wird gewartet, bis es wieder frei ist,
            # statt das Paket aufzugeben (22.-26.10. fehlten so ~1.100 Bilder).
            time.sleep(wait_min * 60)
            try:
                recs = run_batch(exe, batch)
                break
            except Exception as e:  # ein Paket darf den Lauf nicht stoppen
                if "usage_limit_reached" in str(e):
                    log(f"  Paket ab {batch[0]['id']}: Abo-Kontingent leer, warte 30 Min.")
                    wait_min = 30
                    continue
                attempt += 1
                wait_min = (5, 10, 20, 0)[attempt - 1]
                log(f"  Paket ab {batch[0]['id']}: Versuch {attempt} fehlgeschlagen: {str(e)[-300:]}")
        if recs is None:
            continue
        with open(CALLS, "a", encoding="utf-8") as fh:
            for rec in recs:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        n_ok += sum(1 for r in recs if r["read"])
        log(f"  {min(i + BATCH, len(todo))}/{len(todo)} ({n_ok} gelesen)")
    log("Fertig")
    return 0


if __name__ == "__main__":
    sys.exit(main())
