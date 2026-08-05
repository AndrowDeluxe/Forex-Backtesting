"""Grid sweep over (stop_sigma, rr_ratio) for the long-only fixed-CRV bracket exit
(mirrors the live bot's actual SL/TP mechanism, see portfolio.simulate_bracket_portfolio),
on both universes, to see where SL/TP optimization has real, cross-universe-robust room --
not just a single-dataset curve-fit peak."""

import sys
import time

import pandas as pd

import config
import metrics
import portfolio
import run as run_module

STOP_SIGMAS = [1.0, 1.5, 2.0, 2.5, 3.0]
RR_RATIOS = [1.0, 1.5, 2.0, 2.5, 3.0]


def sweep(universe_key: str, universe_variant: str = "full") -> pd.DataFrame:
    panel = run_module.load_panel(universe_key)
    ou_table = pd.read_csv(f"results/{universe_key}/ou_parameters_in_sample.csv", index_col=0)
    if universe_variant == "ou":
        sel = ou_table[
            (ou_table["theta"] > config.THETA_MIN) & (ou_table["p_value"] < config.PVALUE_MAX)
            & (ou_table["half_life"].between(config.HALFLIFE_MIN, config.HALFLIFE_MAX))
        ]
        tickers = sel.index.tolist()
    else:
        tickers = ou_table.index.tolist()

    rows = []
    for stop_sigma in STOP_SIGMAS:
        for rr in RR_RATIOS:
            t0 = time.time()
            eq, trades = portfolio.simulate_bracket_portfolio(
                panel, tickers, config.OUT_SAMPLE_START, config.OUT_SAMPLE_END,
                stop_sigma=stop_sigma, rr_ratio=rr, be_trigger_r=0.5, allowed_directions=(1,),
            )
            m = metrics.summarize(eq.pct_change().fillna(0.0), trades)
            rows.append({
                "stop_sigma": stop_sigma, "rr_ratio": rr,
                "final_equity": eq.iloc[-1], "total_return_pct": m["total_return_pct"],
                "sharpe": m["sharpe"], "sortino": m["sortino"], "calmar": m["calmar"],
                "max_drawdown_pct": m["max_drawdown_pct"], "n_trades": m["n_trades"],
                "win_rate_pct": m["win_rate_pct"],
            })
            print(f"  [{universe_key}/{universe_variant}] sigma={stop_sigma} rr={rr}: "
                  f"final=${eq.iloc[-1]:,.0f} sharpe={m['sharpe']:.2f} calmar={m['calmar']:.2f} "
                  f"({time.time()-t0:.1f}s)")
    return pd.DataFrame(rows)


if __name__ == "__main__":
    universe_key = sys.argv[1] if len(sys.argv) > 1 else "sp500"
    variant = sys.argv[2] if len(sys.argv) > 2 else "full"
    df = sweep(universe_key, variant)
    out_path = config.RESULTS_DIR / universe_key / f"sweep_bracket_{variant}.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved {out_path}")
    print(df.sort_values("sharpe", ascending=False).head(10).to_string())
