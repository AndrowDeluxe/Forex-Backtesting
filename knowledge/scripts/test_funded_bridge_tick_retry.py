"""Offline-Tests fuer den Fix vom 2026-09-15 (frisch selektiertes Symbol ->
0-Tick -> dauerhaft verbranntes Signal). Gestubbtes MT5, DRY_RUN erzwungen,
kein Netz, keine Order."""
import sys, types, time
from pathlib import Path

BRIDGE = Path(r"C:\Users\andre\Funded-Portfolio-Bridge")
sys.path.insert(0, str(BRIDGE))


class Tick:
    def __init__(self, bid, ask):
        self.bid, self.ask, self.time = bid, ask, 1789426499


class Info:
    def __init__(self, visible):
        self.visible = visible


class FakeMT5(types.ModuleType):
    """Bildet genau das reale Verhalten nach: nach symbol_select() liefert
    symbol_info_tick() erst N mal bid=ask=0.0, danach den echten Kurs."""

    def __init__(self):
        super().__init__("MetaTrader5")
        self.quote = {}
        self.visible = {}
        self.selected = []
        self.ticks_after_select = {}
        self._zero_left = {}

    def symbol_info(self, s):
        return Info(self.visible.get(s, False)) if s in self.quote else None

    def symbol_select(self, s, on=True):
        self.selected.append(s)
        self._zero_left[s] = self.ticks_after_select.get(s, 0)
        self.visible[s] = True
        return True

    def symbol_info_tick(self, s):
        q = self.quote.get(s)
        if q is None:
            return None
        if self._zero_left.get(s, 0) > 0:
            self._zero_left[s] -= 1
            return Tick(0.0, 0.0)
        return Tick(*q)


fake = FakeMT5()
sys.modules["MetaTrader5"] = fake

import executor                    # noqa: E402
import run_once as slow            # noqa: E402
import pandas as pd                # noqa: E402

slow.DRY_RUN = True                # harte Sicherung: nie eine echte Order

ok, fail = 0, 0


def check(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print("  PASS  " + name)
    else:
        fail += 1
        print("  FAIL  " + name + "   " + str(extra))


print("")
print("[1] executor.wait_for_tick")
fake.quote["AAA"] = (10.0, 10.1)
fake.ticks_after_select["AAA"] = 3
fake.symbol_select("AAA")
t0 = time.monotonic()
tk = executor.wait_for_tick("AAA")
dt = time.monotonic() - t0
check("liefert den Kurs, sobald er da ist", tk is not None and tk.bid == 10.0, tk)
check("wartet dafuer, bricht nicht sofort ab", dt >= 0.1, round(dt, 3))

fake.quote["ZERO"] = (0.0, 0.0)
t0 = time.monotonic()
tk = executor.wait_for_tick("ZERO", timeout_s=0.3)
dt = time.monotonic() - t0
check("dauerhaft 0 -> sauber None (kein 0-Tick als Notbehelf)", tk is None, tk)
check("und laeuft dabei in den Timeout", 0.25 <= dt < 1.0, round(dt, 3))
check("unbekanntes Symbol -> None", executor.wait_for_tick("GIBTSNICHT", timeout_s=0.1) is None)

print("")
print("[2] run_once._select_and_wait")
fake.quote["BBB"] = (20.0, 20.1)
fake.ticks_after_select["BBB"] = 4
t0 = time.monotonic()
slow._select_and_wait("BBB", Info(visible=False))
dt = time.monotonic() - t0
check("unsichtbares Symbol: wartet auf den ersten Kurs", dt >= 0.15, round(dt, 3))
check("danach liegt ein echter Kurs an", fake.symbol_info_tick("BBB").bid == 20.0)

fake.quote["CCC"] = (30.0, 30.1)
fake.ticks_after_select["CCC"] = 0
t0 = time.monotonic()
slow._select_and_wait("CCC", Info(visible=True))
dt = time.monotonic() - t0
check("bereits sichtbares Symbol: kein Zeitverlust", dt < 0.05, round(dt, 3))

print("")
print("[3] run_once._process_leg -- Retry statt verbranntem Signal")


class Acct:
    symbol_map, symbol_suffix, excluded_legs = {}, "", ()
    capital_weight, rules, name = 1 / 6, "ttp", "TEST"


placed = []


class FakeExec:
    wait_for_tick = staticmethod(executor.wait_for_tick)

    @staticmethod
    def place_market_entry(symbol, direction, sl, risk, target=None, comment="", dry_run=True):
        placed.append(symbol)
        return {"status": "dry_run", "ticket": 999, "entry_price": 105.7, "lots": 1.0}

    @staticmethod
    def signal_already_stopped(*a, **k):
        return False, ""


slow.executor = FakeExec

entry = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
trades = pd.DataFrame([{"entry_time": entry, "entry_price": 106.29, "sl": 100.78,
                        "direction": 1, "exit_reason": "data_end"}])
state = {"account_start": entry - pd.Timedelta(days=5), "positions": {}}

# TROW quotiert, liefert nach dem Abo aber dauerhaft 0 -> erzwingt den 09-14-Fall
fake.quote["TROW"] = (105.64, 105.76)
fake.visible["TROW"] = False
fake.ticks_after_select["TROW"] = 10 ** 6

msgs = slow._process_leg(Acct(), state, 98930.0, "ou_modell (TROW)", trades, "TROW", risk_pct=0.55)
key = next(iter(state["positions"]))
check("1. Lauf ohne Kurs: kein Entry", placed == [], placed)
check("1. Lauf: status ist 'retry', nicht 'missed'", state["positions"][key]["status"] == "retry",
      state["positions"][key])
check("1. Lauf: Zaehler steht auf 1", state["positions"][key]["retry_attempts"] == 1)
check("1. Lauf: meldet 'wird erneut versucht'", any("erneut versucht" in m for m in msgs), msgs)

fake.ticks_after_select["TROW"] = 0
fake._zero_left["TROW"] = 0
msgs = slow._process_leg(Acct(), state, 98930.0, "ou_modell (TROW)", trades, "TROW", risk_pct=0.55)
check("2. Lauf mit Kurs: Entry wird platziert", placed == ["TROW"], placed)
check("2. Lauf: Signal ist jetzt getrackt", state["positions"][key]["status"] == "dry_run",
      state["positions"][key])
check("2. Lauf: meldet ENTRY", any("ENTRY" in m for m in msgs), msgs)

print("")
print("[4] Notnagel: dauerhaft kursloses Symbol (IQ-Fall)")
placed.clear()
fake.quote["NIX"] = (105.0, 105.1)
fake.visible["NIX"] = False
fake.ticks_after_select["NIX"] = 10 ** 6
state2 = {"account_start": entry - pd.Timedelta(days=5), "positions": {}}
seen = []
for _ in range(slow.MAX_TRANSIENT_ENTRY_RETRIES):
    seen += slow._process_leg(Acct(), state2, 98930.0, "ou_modell (NIX)", trades, "NIX", risk_pct=0.55)
k2 = next(iter(state2["positions"]))
check("nach " + str(slow.MAX_TRANSIENT_ENTRY_RETRIES) + " Versuchen endgueltig 'missed'",
      state2["positions"][k2]["status"] == "missed", state2["positions"][k2])
check("nie eine Order gesendet", placed == [], placed)
check("genau 2 Meldungen (erster Versuch + Aufgeben), kein Spam", len(seen) == 2, seen)
check("Aufgeben-Meldung nennt excluded_legs", any("excluded_legs" in m for m in seen), seen)
more = slow._process_leg(Acct(), state2, 98930.0, "ou_modell (NIX)", trades, "NIX", risk_pct=0.55)
check("danach still: keine weitere Meldung", more == [], more)

print("")
print("[5] Regression: dauerhafte Skip-Gruende bleiben endgueltig")
alt = pd.DataFrame([{"entry_time": entry - pd.Timedelta(days=9), "entry_price": 106.29,
                     "sl": 100.78, "direction": 1, "exit_reason": "data_end"}])
state3 = {"account_start": entry - pd.Timedelta(days=30), "positions": {}}
fake.quote["OLD"] = (105.0, 105.1)
fake.visible["OLD"] = True
fake.ticks_after_select["OLD"] = 0
slow._process_leg(Acct(), state3, 98930.0, "ou_modell (OLD)", alt, "OLD", risk_pct=0.55)
k3 = next(iter(state3["positions"]))
check("'Signal zu alt' bleibt 'missed'", state3["positions"][k3]["status"] == "missed",
      state3["positions"][k3])
check("und wird nicht erneut versucht",
      slow._process_leg(Acct(), state3, 98930.0, "ou_modell (OLD)", alt, "OLD", risk_pct=0.55) == [])

state4 = {"account_start": entry - pd.Timedelta(days=5), "positions": {}}
nosl = pd.DataFrame([{"entry_time": entry, "entry_price": 106.29, "sl": float("nan"),
                      "direction": 1, "exit_reason": "data_end"}])
fake.quote["NOSL"] = (105.0, 105.1)
fake.visible["NOSL"] = True
slow._process_leg(Acct(), state4, 98930.0, "ou_modell (NOSL)", nosl, "NOSL", risk_pct=0.55)
k4 = next(iter(state4["positions"]))
check("'kein SL' bleibt 'missed'", state4["positions"][k4]["status"] == "missed", state4["positions"][k4])

print("")
print("[6] executor.place_market_entry gegen 0-Tick")
fake.quote["ZERO2"] = (0.0, 0.0)
r = executor.place_market_entry("ZERO2", 1, 100.0, 150.0, dry_run=True)
check("0-Tick -> no_tick statt Sizing gegen Nullpreis", r.get("reason") == "no_tick", r)

print("")
print("[7] Broker-Ablehnung: transient vs. dauerhaft")


def leg_with_retcode(retcode, symbol):
    """Ein Lauf, bei dem der Broker mit `retcode` ablehnt."""
    class Rejecting(FakeExec):
        @staticmethod
        def place_market_entry(*a, **k):
            return {"status": "error", "reason": "OrderSendResult(...)", "retcode": retcode}
    slow.executor = Rejecting
    fake.quote[symbol] = (105.0, 105.1)
    fake.visible[symbol] = True
    fake.ticks_after_select[symbol] = 0
    st = {"account_start": entry - pd.Timedelta(days=5), "positions": {}}
    m = slow._process_leg(Acct(), st, 98930.0, "ou_modell (" + symbol + ")", trades, symbol, risk_pct=0.55)
    return st, m


# 10018 = Market closed -- genau der Fall, der am 2026-09-02 ADI und FAST kostete
st, m = leg_with_retcode(10018, "MCLOSED")
k = next(iter(st["positions"]))
check("10018 'Market closed' -> 'retry', nicht 'missed'", st["positions"][k]["status"] == "retry",
      st["positions"][k])
check("10018: Grund wird im State festgehalten",
      st["positions"][k]["retry_reason"] == "broker_retcode_10018", st["positions"][k])
check("10018: meldet 'voruebergehend'", any("voruebergehend" in x for x in m), m)

# und danach mit offenem Markt: derselbe Eintrag wird wieder angefasst
slow.executor = FakeExec
placed.clear()
slow._process_leg(Acct(), st, 98930.0, "ou_modell (MCLOSED)", trades, "MCLOSED", risk_pct=0.55)
check("nach Marktoeffnung wird der Entry nachgeholt", placed == ["MCLOSED"], placed)

# 10016 = Invalid stops -- aendert sich nicht von selbst
st, m = leg_with_retcode(10016, "BADSTOP")
k = next(iter(st["positions"]))
check("10016 'Invalid stops' bleibt endgueltig 'missed'", st["positions"][k]["status"] == "missed",
      st["positions"][k])
check("10016: meldet den vollen Fehlertext", any("Entry fehlgeschlagen" in x for x in m), m)

# 10019 = No money
st, _ = leg_with_retcode(10019, "NOMONEY")
k = next(iter(st["positions"]))
check("10019 'No money' bleibt endgueltig 'missed'", st["positions"][k]["status"] == "missed",
      st["positions"][k])

# retcode None = order_send() selbst abgelehnt (zu langer Kommentar, 2026-09-09)
st, _ = leg_with_retcode(None, "SENDNONE")
k = next(iter(st["positions"]))
check("retcode None (Code-/Config-Fehler) bleibt 'missed'", st["positions"][k]["status"] == "missed",
      st["positions"][k])

slow.executor = FakeExec

print("")
print("==== " + str(ok) + " PASS, " + str(fail) + " FAIL ====")
sys.exit(1 if fail else 0)
