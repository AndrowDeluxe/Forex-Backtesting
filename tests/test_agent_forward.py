"""TradingAgents-Forward: Ledger/Auswertung (Repo-Python) und Abo-Adapter (nur mit langchain_core, TA-venv)."""

import pytest

from fusion_lab.agent_forward import ledger as L


def row(datum, ticker, quelle, rating, alpha=None):
    return {"datum": datum, "ticker": ticker, "quelle": quelle, "rating": rating,
            "score": "" if rating is None else str(L.C.SCORE[rating]),
            "rendite_5t": "" if alpha is None else str(alpha), "alpha_5t": "" if alpha is None else str(alpha),
            "abgerechnet": "", "begruendung": "", "fehler": ""}


def test_controls_reproducible_and_momentum_sign():
    a = L.control_ratings("2026-11-23", "NVDA", 0.05)
    b = L.control_ratings("2026-11-23", "NVDA", 0.05)
    assert a == b
    assert a["always_buy"] == "Buy" and a["momentum"] == "Buy"
    assert L.control_ratings("2026-11-23", "NVDA", -0.01)["momentum"] == "Sell"
    assert L.control_ratings("2026-11-23", "NVDA", None)["momentum"] is None


def test_pnl_direction_and_hold():
    assert L.pnl(2, 0.03) == 0.03
    assert L.pnl(-1, 0.03) == -0.03
    assert L.pnl(0, 0.03) == 0


def test_summary_weekly_t_and_probe_excluded():
    rows = [row("2026-11-20", "NVDA", "agent", "Buy", 0.5)]          # Probe, vor Start
    weeks = ["2026-11-23", "2026-11-30", "2026-12-07", "2026-12-14"]
    for i, d in enumerate(weeks):
        rows.append(row(d, "NVDA", "agent", "Sell", -0.01 - 0.001 * i))   # Short richtig
        rows.append(row(d, "NVDA", "always_buy", "Buy", -0.01 - 0.001 * i))
    rows.append(row("2026-12-14", "JPM", "agent", "Hold"))              # offen
    s = L.summarize(rows, start="2026-11-23")
    a, b = s["quellen"]["agent"], s["quellen"]["always_buy"]
    assert a["abgerechnet"] == 4 and a["offen"] == 1 and s["probe_eintraege"] == 1
    assert a["richtungs_alpha"] > 0 > b["richtungs_alpha"]
    assert a["trefferquote"] == 100 and a["wochen"] == 4 and a["t_woche"] > 2
    assert len(s["kurve"]["agent"]) == 4 and s["kurve"]["agent"][-1] > 0
    assert s["letzte"][0]["datum"] == "2026-12-14" and s["letzte"][-1]["probe"]


def test_csv_roundtrip(tmp_path):
    p = tmp_path / "d.csv"
    L.write([row("2026-11-23", "XOM", "random", "Hold", 0.01)], p)
    back = L.read(p)
    assert back[0]["ticker"] == "XOM" and back[0]["score"] == "0"
    assert L.has_entry(back, "2026-11-23", "XOM", "random")


def test_parse_reply_tool_calls_text_and_garbage():
    pytest.importorskip("langchain_core")
    from fusion_lab.agent_forward.claude_llm import parse_reply
    m = parse_reply('```json\n{"tool_calls": [{"name": "get_stock_data", "args": {"start_date": "2026-11-01"}}]}\n```',
                    {"get_stock_data"})
    assert m.tool_calls[0]["name"] == "get_stock_data" and m.tool_calls[0]["args"]["start_date"] == "2026-11-01"
    assert not parse_reply("Final report: trend up.", {"get_stock_data"}).tool_calls
    assert not parse_reply('{"tool_calls": [{"name": "unknown"}]}', {"get_stock_data"}).tool_calls
    assert not parse_reply('{"tool_calls": [', {"get_stock_data"}).tool_calls
    assert not parse_reply('{"tool_calls": [{"name": "get_stock_data"}]}', set()).tool_calls
