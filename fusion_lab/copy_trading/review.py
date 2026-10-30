"""Stichprobe fuer den Nutzer: lokale HTML-Seite mit N zufaelligen Bildern neben den
gelesenen Werten (Edge Card 05 TEST: Ziel <= 5 % Lesefehler bei den Leveln). Je Bild
„stimmt“/„falsch“ ankreuzen und einen Kommentar schreiben, dann CSV exportieren.
Nur lokal oeffnen, nicht veroeffentlichen (private Chatbilder).

    python -m fusion_lab.copy_trading.review --n 50
"""

import argparse
import html
import json
import random
import sys

from fusion_lab.copy_trading.extract import CALLS, CHAT_DIR, OUT_DIR

PAGE = OUT_DIR / "stichprobe.html"


def row_html(r: dict) -> str:
    x = r.get("read") or {}
    img = (CHAT_DIR / "media" / r["media_file"]).as_uri()
    fields = {k: x.get(k) for k in ("is_call", "no_call_reason", "symbol", "chart_tf", "extends_right",
                                      "confidence", "notes")}
    setups = "".join(
        "<li>" + html.escape(", ".join(f"{k}={v}" for k, v in s.items() if v not in (None, []))) + "</li>"
        for s in x.get("setups") or [])
    meta = "<br>".join(f"<b>{k}</b>: {html.escape(str(v))}" for k, v in fields.items())
    cap = html.escape((r.get("caption") or "")[:200])
    mid = r["msg_id"]
    return f"""<section><a href="{img}" target="_blank"><img src="{img}" loading="lazy"></a>
<div class="info"><h3>#{mid} · {r['date'][:16]} · „{cap}“</h3><p>{meta}</p><ul>{setups}</ul>
<label><input type="radio" name="v{mid}" value="stimmt"> stimmt</label>
<label><input type="radio" name="v{mid}" value="falsch"> falsch</label>
<input type="text" id="c{mid}" placeholder="Was ist falsch?"></div></section>"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20261020)
    a = ap.parse_args(argv)
    from fusion_lab.copy_trading.extract import latest
    recs = latest(CALLS)
    recs = [r for r in recs if r.get("read") and r["read"].get("is_call")]  # Level pruefen = Calls
    random.Random(a.seed).shuffle(recs)
    sample = sorted(recs[:a.n], key=lambda r: r["msg_id"])
    ids = json.dumps([r["msg_id"] for r in sample])
    PAGE.write_text(f"""<!doctype html><html lang="de"><meta charset="utf-8">
<title>Stichprobe Calls</title><style>
:root{{--bg:#f6f4ef;--fg:#1d1d1b;--card:#fff;--line:#d9d4c7}}
@media (prefers-color-scheme:dark){{:root{{--bg:#1b1b1a;--fg:#ecebe6;--card:#262624;--line:#3a3935}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif;margin:0 auto;max-width:1400px;padding:16px}}
section{{display:grid;grid-template-columns:minmax(0,3fr) minmax(0,2fr);gap:16px;background:var(--card);
border:1px solid var(--line);border-radius:8px;padding:12px;margin:12px 0}}
img{{width:100%;border-radius:4px}} h3{{margin:0 0 6px;font-size:15px}} ul{{padding-left:18px}}
input[type=text]{{width:100%;margin-top:6px;padding:4px}}
@media (max-width:800px){{section{{grid-template-columns:1fr}}}}
button{{position:sticky;top:8px;padding:8px 14px;font-size:15px}}</style>
<h1>Stichprobe: {len(sample)} gelesene Calls</h1>
<p>Bitte je Bild prüfen: Symbol, Timeframe, Richtung, Entry/SL/TP bzw. Zone und Pfadende.
Kleine Abweichungen bei geschätzten Zonenrändern sind ok, falsch ist z. B. ein falscher Level-Wert,
falsche Richtung oder ein Rückblick, der als Call gelesen wurde.</p>
<button onclick="exp()">CSV exportieren</button>
{''.join(row_html(r) for r in sample)}
<script>const IDS={ids};
function exp(){{let s="msg_id;urteil;kommentar\\n";for(const i of IDS){{
const v=document.querySelector(`input[name=v${{i}}]:checked`);const c=document.getElementById("c"+i).value.replace(/;/g,",");
s+=`${{i}};${{v?v.value:""}};${{c}}\\n`;}}
const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([s],{{type:"text/csv"}}));
a.download="stichprobe_urteil.csv";a.click();}}</script></html>""", encoding="utf-8")
    print(f"{PAGE} ({len(sample)} Calls)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
