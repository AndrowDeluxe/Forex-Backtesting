"""Echte NASDAQ-Deals je Broker: Stop-Order-Slippage (Fill gegen Stop-Level) und Kommission. REIN LESEND.

  python scripts/pull_broker_nasdaq_deals.py --days 200
"""
import argparse, sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT))
import measure_broker_spreads as M  # noqa: E402
from pull_broker_ticks_nasdaq import SHORT  # noqa: E402


def main():
    import MetaTrader5 as mt5
    ap = argparse.ArgumentParser(); ap.add_argument("--days", type=int, default=200); a = ap.parse_args()
    rows, seen, started = [], set(), []
    for t in M._load_targets(("NASDAQ",)):
        if t.terminal_path in seen:
            continue
        seen.add(t.terminal_path)
        was = M._terminal_running(t.terminal_path)
        try:
            with M.account_state_lock(t):
                M._connect(mt5, t)
                if not was:
                    started.append(t.terminal_path)
                to = datetime.now() + timedelta(days=1); fr = to - timedelta(days=a.days)
                orders = {int(o.ticket): o for o in (mt5.history_orders_get(fr, to) or [])}
                for d in mt5.history_deals_get(fr, to) or []:
                    if d.symbol != t.symbol:
                        continue
                    o = orders.get(int(d.order))
                    stop_types = (mt5.ORDER_TYPE_BUY_STOP, mt5.ORDER_TYPE_SELL_STOP)
                    ref = float(o.price_open) if o is not None and o.type in stop_types else (
                        float(o.price_open) if o is not None and d.entry == mt5.DEAL_ENTRY_OUT and o.price_open > 0 else None)
                    worse = None
                    if ref:
                        worse = (d.price - ref) if d.type == mt5.DEAL_TYPE_BUY else (ref - d.price)
                    rows.append({"broker": SHORT.get(t.server, t.server), "time_server": datetime.fromtimestamp(d.time),
                                 "entry": "in" if d.entry == mt5.DEAL_ENTRY_IN else "out",
                                 "order_type": None if o is None else int(o.type), "price": d.price, "ref": ref,
                                 "slip_pts": worse, "volume": d.volume, "commission": d.commission, "comment": d.comment})
        except Exception as exc:  # noqa: BLE001
            print("FEHLER", t.server, exc)
    mt5.shutdown()
    for p in started:
        M._stop_terminal(p)
    df = pd.DataFrame(rows)
    out = ROOT / "ny_open_orb" / "results" / "premarket_0900" / "broker_nasdaq_deals.csv"
    df.to_csv(out, index=False)
    print(df.groupby(["broker", "entry"]).agg(n=("price", "size"), slip_med=("slip_pts", "median"),
          slip_mean=("slip_pts", "mean"), comm_sum=("commission", "sum"), vol=("volume", "sum")).round(3))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8"); main()
