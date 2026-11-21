import pandas as pd
import pytest

from signal_hub import __main__ as hub
from signal_hub import config, journal, paper, risk, telegram
from signal_hub.setups import h4_spike

TZ = "Europe/Berlin"


@pytest.fixture(autouse=True)
def no_telegram(monkeypatch):
    calls = []
    for fn in ("answer", "edit_caption", "edit_markup", "send_text", "send_photo"):
        monkeypatch.setattr(telegram, fn, lambda *a, _fn=fn, **k: calls.append((_fn, a)))
    return calls


def _journal(**kw):
    row = {"id": "EURUSD_2026111211_s", "markt": "EURUSD", "seite": "short", "status": "offen", "message_id": 5,
           "caption": "Text", "stop": 1.11027, "einstieg": pd.Timestamp("2026-11-12 15:00", tz=TZ),
           "gueltig_bis": pd.Timestamp("2026-11-12 19:00", tz=TZ), "erinnern_um": pd.NaT}
    row.update(kw)
    return pd.DataFrame([row])


def test_ja_klick_setzt_status_und_zeit():
    now = pd.Timestamp("2026-11-12 14:07", tz="UTC")
    j = hub.handle_callback(_journal(), {"id": "c1", "data": "sh|EURUSD_2026111211_s|yes"}, now)
    assert j["status"].iat[0] == "ja"
    assert j["entschieden_um"].iat[0] == now.tz_convert(TZ)


def test_nein_braucht_grund_und_fremde_daten_werden_ignoriert(no_telegram):
    now = pd.Timestamp("2026-11-12 14:07", tz="UTC")
    j = hub.handle_callback(_journal(), {"id": "c1", "data": "sh|EURUSD_2026111211_s|no"}, now)
    assert j["status"].iat[0] == "offen"                       # erst Grund-Auswahl
    j = hub.handle_callback(j, {"id": "c2", "data": "sh|EURUSD_2026111211_s|no|trend"}, now)
    assert j["status"].iat[0] == "nein" and j["grund"].iat[0] == "trend"
    j2 = hub.handle_callback(j, {"id": "c3", "data": "anderer_bot|x"}, now)
    assert j2["status"].iat[0] == "nein"


def test_verfall_nach_gueltigkeit():
    j = hub.maintenance(_journal(), pd.Timestamp("2026-11-12 18:30", tz="UTC"))
    assert j["status"].iat[0] == "verfallen"


def test_risiko_sperre_max_trades_und_offene_position():
    now = pd.Timestamp("2026-11-12 14:00", tz="UTC")
    conf = pd.DataFrame([{"id": f"X{i}", "markt": m, "status": "ja", "entschieden_um": now.tz_convert(TZ),
                          "p_conf_status": "geschlossen", "p_conf_r": 1.0, "p_conf_exit_t": now}
                         for i, m in enumerate(["GBPUSD", "AUDUSD", "USDJPY"])])
    ok, why = risk.check(conf, "EURUSD", now)
    assert not ok and "max. 3" in why
    offen = pd.DataFrame([{"id": "Y", "markt": "EURUSD", "status": "ja", "entschieden_um": now.tz_convert(TZ),
                           "p_conf_status": "offen"}])
    ok, why = risk.check(offen, "EURUSD", now)
    assert not ok and "offene Position" in why


def test_lots_fx_und_gold():
    assert risk.lots("EURUSD", 1.1000, 1.0950, 500) == 1.0          # 50 Pips, 10 $/Pip
    assert risk.lots("XAUUSD", 2000.0, 1990.0, 500) == 0.5          # 10 $ x 100 oz


def test_paper_be_nach_1r_und_ziel(monkeypatch):
    monkeypatch.setattr("htf_daily_trade.twin_trade.swap_r", lambda *a, **k: 0.0)
    idx = pd.date_range("2026-11-12 14:00", periods=5, freq="15min", tz="UTC")
    bars = pd.DataFrame({"Open": [1.0, 1.0, 1.0, 1.0, 1.0], "High": [1.0, 1.0, 1.005, 1.0, 1.0],
                         "Low": [0.995, 0.989, 0.995, 0.97, 0.97], "Close": [1.0] * 5}, index=idx)
    s = paper.simulate(bars, "short", idx[0], 1.01, 0.0, "EURUSD")   # Risiko 0,01; 1R = 0,99 -> BE; dann Stop auf 1,0
    assert s["status"] == "geschlossen" and abs(s["r"]) < 1e-9
    s2 = paper.simulate(bars.assign(High=0.999), "short", idx[0], 1.01, 0.0, "EURUSD")   # BE nie beruehrt -> 3R
    assert s2["status"] == "geschlossen" and abs(s2["r"] - 3.0) < 1e-9


def test_letzte_abgeschlossene_h4_kerze():
    now = pd.Timestamp("2026-11-12 14:05", tz="UTC")          # 15:05 Berlin -> Kerze 11-15 Uhr Berlin fertig
    assert h4_spike.last_closed_bar_end(now).tz_convert(TZ).hour == 15


def test_journal_sperre_und_rundreise(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "LOCKFILE", tmp_path / "l.lock")
    p = tmp_path / "j.csv"
    with journal.locked():
        journal.save(_journal(), p)
    j = journal.load(p)
    assert j["gueltig_bis"].iat[0] == pd.Timestamp("2026-11-12 19:00", tz=TZ)


def test_journal_gemischte_zeitformate_gehen_nicht_verloren(tmp_path):
    # 20.11.: Zeile mit Mikrosekunden + Zeile ohne -> pandas leitete das Format aus Zeile 1 ab und machte Zeile 2 zu NaT
    p = tmp_path / "j.csv"
    j = pd.concat([_journal(id="A", gueltig_bis=pd.Timestamp("2026-11-19 16:28:24.640954", tz=TZ)),
                   _journal(id="B", gueltig_bis=pd.Timestamp("2026-11-21 03:00", tz=TZ))], ignore_index=True)
    journal.save(j, p)
    assert journal.load(p)["gueltig_bis"].notna().all()
