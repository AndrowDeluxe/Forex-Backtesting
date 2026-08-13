"""Static matplotlib visual-check chart for a single cls_practical trade -
Asia Range, Settle window + break/sweep level, the fractal pivot ("Pullback"
for Continuation, "Structure Shift" for Reversal), Rückkehr-marker (Reversal
only), entry/SL/TP/exit - so the fractal-trigger mechanics can actually be
SEEN on a real day, not just trusted from a trades table. Matplotlib (not
Altair, unlike the rest of this repo's *.chart modules) because this is a
one-off diagnostic PNG, not a Streamlit page, and vl-convert (needed to
rasterize Altair outside Streamlit) isn't installed.

build_entry_chart() below (added 2026-08-13) is the Streamlit-embeddable
counterpart -- an interactive Altair multi-day candlestick chart with SL/TP
lines and entry/exit markers for the strategy page's chart-verification tab,
same pattern as presettle_breakout/chart.py's build_entry_chart(). Kept in
this module (not a separate file) since both serve the same "see a CLS trade
on a real chart" purpose, just static-single-trade vs. interactive-multi-day."""

import altair as alt
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from strategy.cls_advanced import ASIA_END, ASIA_START, SETTLE_END, to_berlin

_UP, _DOWN = "#26a69a", "#ef5350"
_EXIT_COLORS = {"stop": "#c62828", "take_profit": "#2e7d32", "data_end": "#757575"}


def plot_trade_example(eurusd_m5: pd.DataFrame, trade: pd.Series, asia_high: float, asia_low: float, out_path: str) -> None:
    day = trade["date"]
    berlin_idx = to_berlin(eurusd_m5.index)
    day_mask = berlin_idx.date == day
    day_df = eurusd_m5.loc[day_mask].copy()
    day_df.index = berlin_idx[day_mask]

    window_end = max(trade["exit_time"], pd.Timestamp(day, tz="Europe/Berlin") + pd.Timedelta(hours=13))
    window_end = min(window_end, pd.Timestamp(day, tz="Europe/Berlin") + pd.Timedelta(hours=23))
    plot_df = day_df[day_df.index <= window_end]

    fig, ax = plt.subplots(figsize=(14, 7))
    width = pd.Timedelta(minutes=4)
    for t, row in plot_df.iterrows():
        color = _UP if row["close"] >= row["open"] else _DOWN
        ax.plot([t, t], [row["low"], row["high"]], color=color, linewidth=0.8, zorder=2)
        ax.add_patch(
            plt.Rectangle(
                (mdates.date2num(t - width / 2), min(row["open"], row["close"])),
                mdates.date2num(t + width / 2) - mdates.date2num(t - width / 2),
                max(abs(row["close"] - row["open"]), 1e-6),
                color=color, zorder=3,
            )
        )

    asia_start_t = pd.Timestamp(day, tz="Europe/Berlin") + pd.Timedelta(hours=ASIA_START)
    asia_end_t = pd.Timestamp(day, tz="Europe/Berlin") + pd.Timedelta(hours=ASIA_END)
    settle_end_t = pd.Timestamp(day, tz="Europe/Berlin") + pd.Timedelta(hours=SETTLE_END)
    ax.axvspan(asia_start_t, asia_end_t, color="#90a4ae", alpha=0.15, label="Asia Range (00-06)")
    ax.axhspan(asia_low, asia_high, xmin=0, xmax=1, color="#90a4ae", alpha=0.08)
    ax.axvspan(asia_end_t, settle_end_t, color="#ffca28", alpha=0.12, label="Settle-Fenster (06-09)")
    ax.axhline(asia_high, color="#607d8b", linestyle=":", linewidth=1)
    ax.axhline(asia_low, color="#607d8b", linestyle=":", linewidth=1)

    ax.axvline(trade["pivot_time"], color="#8e24aa", linestyle="--", linewidth=1.2)
    pivot_label = "Pullback (Fraktal)" if trade["setup"] == "continuation" else "Structure Shift (Fraktal)"
    ax.text(trade["pivot_time"], plot_df["high"].max(), pivot_label, color="#8e24aa", rotation=90, va="top", ha="right", fontsize=8)

    if pd.notna(trade["return_time"]):
        ax.axvline(trade["return_time"], color="#00838f", linestyle="--", linewidth=1.2)
        ax.text(trade["return_time"], plot_df["low"].min(), "Rückkehr in Range", color="#00838f", rotation=90, va="bottom", ha="left", fontsize=8)

    ax.axhline(trade["sl"], color="#c62828", linestyle="--", linewidth=1, xmin=0, xmax=1)
    ax.axhline(trade["tp"], color="#2e7d32", linestyle="--", linewidth=1, xmin=0, xmax=1)

    marker = "^" if trade["direction"] == "long" else "v"
    ax.scatter([trade["entry_time"]], [trade["entry_price"]], marker=marker, s=180, color="#1565c0", zorder=5, label="Entry")
    ax.scatter([trade["exit_time"]], [trade["exit_price"]], marker="D", s=110, color=_EXIT_COLORS.get(trade["exit_reason"], "#757575"), zorder=5, label=f"Exit ({trade['exit_reason']})")

    ax.set_title(
        f"{day} - {trade['setup'].capitalize()} {trade['direction'].upper()} - "
        f"Trend={trade['trend_bias']:+.0f}, Rates={trade['rates_ampel']}, Crosses={'ja' if trade['cross_confirmed'] else 'nein'}"
    )
    ax.set_ylabel("EUR/USD")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=day_df.index.tz))
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.2)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


_CANDLE_UP, _CANDLE_DOWN = "#26a69a", "#ef5350"
_LONG_COLOR, _SHORT_COLOR = "#2e7d32", "#e65100"
_EXIT_COLORS_ALT = {"take_profit": "#2e7d32", "stop": "#c62828", "breakeven": "#607d8b", "data_end": "#757575"}


def build_entry_chart(price: pd.DataFrame, trades: pd.DataFrame) -> alt.LayerChart:
    """Interactive multi-day M5 candlestick chart + SL/TP levels + entry/exit
    markers, for the Streamlit chart-verification tab. price: OHLC frame
    (lower-case columns, Berlin-tz index), already sliced to the window to
    display. trades: output of simulate_cls_practical, already sliced to
    trades whose entry_time falls within (roughly) that same window."""

    p = price.reset_index().rename(columns={price.index.name or "index": "time"})
    p["direction"] = (p["close"] >= p["open"]).map({True: "up", False: "down"})

    candle_body = (
        alt.Chart(p)
        .mark_bar(width=3)
        .encode(
            x=alt.X("time:T", title="Zeit (Berlin)"),
            y=alt.Y("open:Q", title="Preis", scale=alt.Scale(zero=False)),
            y2="close:Q",
            color=alt.Color(
                "direction:N",
                scale=alt.Scale(domain=["up", "down"], range=[_CANDLE_UP, _CANDLE_DOWN]),
                legend=alt.Legend(title="Kerze"),
            ),
            tooltip=[
                alt.Tooltip("time:T", title="Zeit"),
                alt.Tooltip("open:Q", format=".5f"),
                alt.Tooltip("high:Q", format=".5f"),
                alt.Tooltip("low:Q", format=".5f"),
                alt.Tooltip("close:Q", format=".5f"),
            ],
        )
    )
    candle_wick = (
        alt.Chart(p)
        .mark_rule(strokeWidth=1)
        .encode(
            x="time:T", y="low:Q", y2="high:Q",
            color=alt.Color("direction:N", scale=alt.Scale(domain=["up", "down"], range=[_CANDLE_UP, _CANDLE_DOWN]), legend=None),
        )
    )
    layers = [candle_wick, candle_body]

    if not trades.empty:
        t = trades.copy()
        t["exit_time_line"] = t["exit_time"].fillna(p["time"].max())

        sl_lines = (
            alt.Chart(t)
            .mark_rule(strokeDash=[2, 2], strokeWidth=1, color="#c62828")
            .encode(x="entry_time:T", x2="exit_time_line:T", y="sl:Q", tooltip=[alt.Tooltip("sl:Q", format=".5f", title="Stop-Loss")])
        )
        tp_lines = (
            alt.Chart(t)
            .mark_rule(strokeDash=[2, 2], strokeWidth=1, color="#2e7d32")
            .encode(x="entry_time:T", x2="exit_time_line:T", y="tp:Q", tooltip=[alt.Tooltip("tp:Q", format=".5f", title="Take-Profit")])
        )
        layers.extend([sl_lines, tp_lines])

        entries = (
            alt.Chart(t)
            .mark_point(shape="triangle-up", size=160, filled=True)
            .encode(
                x="entry_time:T",
                y="entry_price:Q",
                color=alt.Color(
                    "direction:N",
                    scale=alt.Scale(domain=["long", "short"], range=[_LONG_COLOR, _SHORT_COLOR]),
                    legend=alt.Legend(title="Entry-Richtung"),
                ),
                angle=alt.condition("datum.direction == 'short'", alt.value(180), alt.value(0)),
                tooltip=[
                    alt.Tooltip("entry_time:T", title="Entry"),
                    alt.Tooltip("entry_price:Q", format=".5f"),
                    alt.Tooltip("setup:N", title="Setup"),
                    alt.Tooltip("direction:N"),
                    alt.Tooltip("sl:Q", format=".5f", title="Stop"),
                    alt.Tooltip("tp:Q", format=".5f", title="Ziel"),
                ],
            )
        )
        layers.append(entries)

        exits = (
            alt.Chart(t.dropna(subset=["exit_price"]))
            .mark_point(shape="diamond", size=120, filled=True)
            .encode(
                x="exit_time:T",
                y="exit_price:Q",
                color=alt.Color(
                    "exit_reason:N",
                    scale=alt.Scale(domain=list(_EXIT_COLORS_ALT), range=list(_EXIT_COLORS_ALT.values())),
                    legend=alt.Legend(title="Exit-Grund"),
                ),
                tooltip=[
                    alt.Tooltip("exit_time:T", title="Exit"),
                    alt.Tooltip("exit_price:Q", format=".5f"),
                    alt.Tooltip("exit_reason:N"),
                    alt.Tooltip("pnl_usd:Q", format="+.0f", title="PnL ($)"),
                ],
            )
        )
        layers.append(exits)

    return alt.layer(*layers).properties(height=520).interactive(bind_y=False)
