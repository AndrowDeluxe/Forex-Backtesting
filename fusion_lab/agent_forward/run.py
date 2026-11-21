"""Tageslauf: offene Entscheide abrechnen, Agenten + Kontrollen fuer heute entscheiden lassen, Summary schreiben.

Das Analyse-Datum ist IMMER der heutige Tag (nach US-Schluss). Ein aelteres Datum behandelt TradingAgents als
historisch und haelt dann Fundamentaldaten zurueck (Schutz vor Vorgriff) -- der Lauf waere ein anderer Test.
"""

from __future__ import annotations

import re
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fusion_lab.agent_forward import config as C
from fusion_lab.agent_forward import ledger as L


def log(msg: str) -> None:
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}", flush=True)


def session_today(force: bool = False, datum: str | None = None) -> str | None:
    """Heutiges Datum, wenn heute ein US-Handelstag ist und der Schluss vorbei ist.

    `datum` (nur fuer Tests): ein frueherer Handelstag. TradingAgents laeuft dann im historischen Modus
    (ohne Fundamentaldaten), und weil er vor C.START liegt, zaehlt er nur als Probe."""
    from tradingagents.dataflows.vendors.yahoo.market import get_closes
    today = date.fromisoformat(datum) if datum else date.today()
    if datum:
        log(f"TEST mit Datum {datum}: historischer Modus, zaehlt nicht")
    ny = datetime.now(ZoneInfo("America/New_York"))
    if not force and not datum and (ny.date() != today or (ny.hour, ny.minute) < (16, 10)):
        log(f"US-Schluss heute noch nicht vorbei (New York {ny:%Y-%m-%d %H:%M}) -> kein Lauf")
        return None
    closes = get_closes(C.BENCHMARK, (today - timedelta(days=10)).isoformat(), (today + timedelta(days=1)).isoformat())
    if closes.empty or closes.index[-1].date() != today:
        log(f"{today} ist kein US-Handelstag (letzter SPY-Schluss {None if closes.empty else closes.index[-1].date()})")
        return None
    return today.isoformat()


def ret_20d(ticker: str, datum: str) -> float | None:
    from tradingagents.dataflows.vendors.yahoo.market import get_closes
    d = date.fromisoformat(datum)
    c = get_closes(ticker, (d - timedelta(days=45)).isoformat(), (d + timedelta(days=1)).isoformat())
    c = c[c > 0]
    return None if len(c) < 21 else float(c.iloc[-1] / c.iloc[-21] - 1)


def settle(rows: list[dict]) -> int:
    """Rendite + Alpha nach HOLDING_DAYS fuer alle offenen Zeilen, gleiche Messung fuer alle Quellen."""
    from tradingagents.memory.settlement import fetch_returns
    done, cache = 0, {}
    for r in rows:
        if r["alpha_5t"] or r["score"] == "":
            continue
        key = (r["ticker"], r["datum"])
        if key not in cache:
            try:
                cache[key] = fetch_returns(r["ticker"], r["datum"], C.HOLDING_DAYS, benchmark=C.BENCHMARK)
            except Exception as e:  # noqa: BLE001 -- Kursabruf faellt aus: naechster Lauf versucht es wieder
                log(f"Abrechnung {key} nicht moeglich: {e}")
                cache[key] = (None, None, None, None)
        raw, alpha, _, resolved = cache[key]
        if raw is not None:
            r["rendite_5t"], r["alpha_5t"], r["abgerechnet"] = f"{raw:.6f}", f"{alpha:.6f}", resolved
            done += 1
    return done


def summary_of(decision: str) -> str:
    m = re.search(r"Executive Summary\**:?\**\s*(.+?)(?:\n\s*\n|\n#|\n\*\*Investment Thesis|\Z)", decision or "", re.S)
    text = (m.group(1) if m else decision or "").strip()
    return re.sub(r"\s+", " ", text)[:600]


def save_report(datum: str, ticker: str, state: dict) -> None:
    C.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    parts = [f"# {ticker} · {datum}"]
    for title, key in [("Final decision (Portfolio Manager)", "final_trade_decision"),
                       ("Trader plan", "trader_investment_plan"), ("Research plan", "investment_plan"),
                       ("Market report", "market_report"), ("News report", "news_report"),
                       ("Fundamentals report", "fundamentals_report")]:
        if state.get(key):
            parts.append(f"## {title}\n\n{state[key]}")
    (C.REPORTS_DIR / f"{datum}_{ticker}.md").write_text("\n\n".join(parts), encoding="utf-8")


def run(tickers: list[str] | None = None, force: bool = False, datum_test: str | None = None) -> int:
    from fusion_lab.agent_forward.claude_llm import USAGE, install
    install(C.QUICK_MODEL, C.DEEP_MODEL, C.LLM_TIMEOUT)
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.memory.settlement import settle_all_pending

    t_run = time.time()
    rows = L.read()
    n_settled = settle(rows)
    L.write(rows)
    log(f"abgerechnet: {n_settled}")

    cfg = C.ta_config()
    graph = TradingAgentsGraph(selected_analysts=C.ANALYSTS, config=cfg)
    USAGE.reset()
    s = settle_all_pending(graph.memory_log, graph.reflector, cfg)   # Lektionen fuer kuenftige Laeufe
    log(f"Lektionen geschrieben: {len(s.settled)}, fehlgeschlagen: {len(s.failed)}")
    calls_total, cost_total = USAGE.calls, USAGE.cost_usd

    datum = session_today(force, datum_test)
    ok = err = 0
    hinweis = "" if datum else "kein Handelstag / vor US-Schluss"
    for ticker in (tickers or C.TICKERS) if datum else []:
        if L.has_entry(rows, datum, ticker, "agent"):
            log(f"{ticker} {datum}: schon im Ledger")
            continue
        USAGE.reset()
        t0 = time.time()
        row = {"datum": datum, "ticker": ticker, "quelle": "agent", "rating": "", "score": "", "rendite_5t": "",
               "alpha_5t": "", "abgerechnet": "", "begruendung": "", "fehler": ""}
        try:
            state, signal = graph.propagate(ticker, datum)
            if signal in C.SCORE:
                row["rating"], row["score"] = signal, str(C.SCORE[signal])
            else:
                row["rating"], row["fehler"] = str(signal), "Rating nicht erkennbar"
            row["begruendung"] = summary_of(state.get("final_trade_decision", ""))
            save_report(datum, ticker, state)
            ok += 1
        except Exception as e:  # noqa: BLE001 -- ein Titel faellt aus, der Lauf geht weiter
            row["fehler"] = f"{type(e).__name__}: {str(e)[:300]}"
            err += 1
        row.update(sekunden=f"{time.time() - t0:.0f}", llm_aufrufe=str(USAGE.calls), kosten_usd=f"{USAGE.cost_usd:.4f}")
        calls_total += USAGE.calls
        cost_total += USAGE.cost_usd
        log(f"{ticker}: {row['rating'] or '-'} {row['fehler']} ({row['sekunden']} s, {USAGE.calls} Aufrufe)")
        rows.append(row)
        try:
            r20 = ret_20d(ticker, datum)
        except Exception:  # noqa: BLE001
            r20 = None
        for q, rating in L.control_ratings(datum, ticker, r20).items():
            if rating and not L.has_entry(rows, datum, ticker, q):
                rows.append({"datum": datum, "ticker": ticker, "quelle": q, "rating": rating,
                             "score": str(C.SCORE[rating]), "rendite_5t": "", "alpha_5t": "", "abgerechnet": "",
                             "begruendung": "", "fehler": ""})
        L.write(rows)                                   # nach jedem Titel sichern

    L.append_run({"lauf": datetime.now().strftime("%Y-%m-%d %H:%M"), "datum": datum or "", "titel_ok": ok,
                  "titel_fehler": err, "abgerechnet": n_settled, "sekunden": f"{time.time() - t_run:.0f}",
                  "llm_aufrufe": calls_total, "kosten_usd": f"{cost_total:.4f}", "hinweis": hinweis})
    L.write_summary()
    log(f"fertig: {ok} ok, {err} Fehler, {calls_total} Aufrufe, Abo-Gegenwert {cost_total:.2f} USD")
    return 1 if err and not ok else 0
