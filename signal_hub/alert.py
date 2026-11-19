"""Alarm: Chartbild (matplotlib) + Legende + Knoepfe."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from signal_hub import config

AMPEL = {"gruen": "🟢", "gelb": "🟡", "rot": "🔴"}
REASONS = [("Trend", "trend"), ("Lage/Range", "lage"), ("Kerze", "kerze"), ("Makro", "makro"),
           ("Momentum", "momentum"), ("Sonstiges", "sonst")]


def buttons(sid: str, gesperrt: bool = False) -> list:
    if gesperrt:
        return [[("❌ Nein", f"sh|{sid}|no"), ("👍 Gesehen", f"sh|{sid}|seen")]]
    return [[("✅ Ja", f"sh|{sid}|yes"), ("❌ Nein", f"sh|{sid}|no"), ("⏸ Später", f"sh|{sid}|later")]]


def reason_buttons(sid: str) -> list:
    rows = [[(t, f"sh|{sid}|no|{c}") for t, c in REASONS[:3]], [(t, f"sh|{sid}|no|{c}") for t, c in REASONS[3:]]]
    return rows + [[("↩ zurück", f"sh|{sid}|back")]]


def fmt(x: float, markt: str) -> str:
    return f"{x:.2f}" if markt in ("XAUUSD", "XAGUSD") else (f"{x:.3f}" if "JPY" in markt else f"{x:.5f}")


def caption(s: dict) -> str:
    m = s["markt"]
    star = "⭐ " if s.get("stern") else ""
    lines = [
        f"{star}H4-Spike {s['seite'].upper()} {m} · Einstieg ab {s['einstieg']:%a %d.%m. %H:%M}",
        f"Kurs ~{fmt(s['kurs'], m)} | Stop {fmt(s['stop'], m)} | 3R {fmt(s['ziel_3r'], m)} | Swing {fmt(s['ziel_swing'], m)}",
        f"Kerze {s['spanne_atr']:.1f}×ATR · Docht {s['docht_anteil']:.0%} · Körper {s['koerper_anteil']:.0%} · "
        f"Swings {int(s['swings_geholt'])} · Kerzen gesweept {int(s['n_sweep'])}",
        f"Schluss {s['schluss_unter_marke_atr']:.2f} ATR hinter Marke · Aktivität {s['akt12']:.2f}",
        f"Lage Vormonat {s['lage_VM']:.2f} · Daily-Swing {s['lage_DS']:.2f} · Struktur D {s['DS']} / H4 {s['HS']}",
        f"RSI-ML H4 {s['rsiml_h4']:.0f} · RSI D {s['rsi_d']:.0f} · ADX D {s['adx_d']:.0f} · BB außen {'ja' if s['bb_aussen'] else 'nein'}",
        f"Makro {AMPEL[s['ampel']]} {s['ampel_text']}",
        f"Risiko: {s['sizing']}",
    ]
    if s.get("gesperrt_grund"):
        lines.append(f"🔒 Gesperrt: {s['gesperrt_grund']} – kein Trade")
    lines.append(f"Gültig bis {s['gueltig_bis']:%H:%M} · ID {s['id']}")
    return "\n".join(lines)


def chart(x: pd.DataFrame, k: int, s: dict, path) -> str:
    """Letzte ~60 H4-Kerzen bis zur Signalkerze k."""
    v = x.iloc[max(0, k - 59):k + 1]
    fig, ax = plt.subplots(figsize=(11, 5.5))
    fig.patch.set_facecolor("#1e1e1e")
    ax.set_facecolor("#1e1e1e")
    for j, (_, r) in enumerate(v.iterrows()):
        col = "#3b82f6" if r.Close >= r.Open else "#d1d5db"
        ax.plot([j, j], [r.Low, r.High], color=col, lw=1)
        ax.add_patch(plt.Rectangle((j - 0.35, min(r.Open, r.Close)), 0.7, max(abs(r.Close - r.Open), 1e-9), color=col))
    js = len(v) - 1
    ax.add_patch(plt.Rectangle((js - 0.5, v["Low"].iat[-1]), 1.0, v["High"].iat[-1] - v["Low"].iat[-1],
                               fill=False, ec="#facc15", lw=1.5))
    right = js + 8
    for lvl, col, txt in ((s["kurs"], "#e5e7eb", "Einstieg"), (s["stop"], "#ef4444", "Stop"),
                          (s["ziel_3r"], "#22c55e", "3R"), (s["ziel_swing"], "#14b8a6", "Swing"),
                          (s["marke"], "#f97316", "Marke")):
        ax.plot([js, right], [lvl, lvl], color=col, lw=1.2, ls="--" if txt in ("Marke", "Swing") else "-")
        ax.text(right + 0.2, lvl, txt, color=col, fontsize=8, va="center")
    ax.add_patch(plt.Rectangle((js + 0.5, min(s["kurs"], s["stop"])), right - js - 0.5, abs(s["kurs"] - s["stop"]),
                               color="#ef4444", alpha=0.18))
    ax.add_patch(plt.Rectangle((js + 0.5, min(s["kurs"], s["ziel_3r"])), right - js - 0.5,
                               abs(s["ziel_3r"] - s["kurs"]), color="#22c55e", alpha=0.12))
    for key, col in (("vm_hoch", "#a78bfa"), ("vm_tief", "#a78bfa")):
        if np.isfinite(s.get(key, np.nan)):
            ax.axhline(s[key], color=col, lw=0.8, ls=":")
    idx = v.index.tz_convert(config.TZ)
    ticks = list(range(0, len(v), 6))
    ax.set_xticks(ticks)
    ax.set_xticklabels([idx[t].strftime("%d.%m %H:%M") for t in ticks], color="white", fontsize=7, rotation=30)
    ax.tick_params(axis="y", colors="white", labelsize=8)
    ax.set_xlim(-1, right + 4)
    lo = min(v["Low"].min(), s["stop"], s["ziel_3r"])
    hi = max(v["High"].max(), s["stop"], s["ziel_3r"])
    pad = (hi - lo) * 0.05
    ax.set_ylim(lo - pad, hi + pad)
    star = "⭐ " if s.get("stern") else ""
    ax.set_title(f"{star}{s['markt']} H4 {s['seite'].upper()} – Signalkerze gelb, violett = Vormonats-Range (Zeit Berlin)",
                 color="white", fontsize=9)
    plt.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)
    return str(path)
