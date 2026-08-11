"""Visual entry-signal chart for the Pre-Settle Range Breakout: M5
candlesticks + the pre-settle range box, the resting Buy-Stop/Sell-Stop
levels, entry/exit markers - adapted from asian_range_breakout/chart.py for
EUR/USD's price scale (5 decimals instead of Gold's 2).
"""

import altair as alt
import pandas as pd

_UP_COLOR = "#26a69a"
_DOWN_COLOR = "#ef5350"
_LONG_COLOR = "#2e7d32"
_SHORT_COLOR = "#e65100"
_EXIT_COLORS = {"stop": "#c62828", "take_profit": "#2e7d32", "data_end": "#757575"}


def build_entry_chart(price: pd.DataFrame, trades: pd.DataFrame) -> alt.LayerChart:
    """price: OHLC frame (lower-case columns), already sliced to the window
    to display. trades: output of simulate_presettle_breakout, already
    sliced to trades whose window falls within (roughly) that same window."""

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
                scale=alt.Scale(domain=["up", "down"], range=[_UP_COLOR, _DOWN_COLOR]),
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
            x="time:T",
            y="low:Q",
            y2="high:Q",
            color=alt.Color("direction:N", scale=alt.Scale(domain=["up", "down"], range=[_UP_COLOR, _DOWN_COLOR]), legend=None),
        )
    )
    layers = [candle_wick, candle_body]

    if not trades.empty:
        range_box = (
            alt.Chart(trades)
            .mark_rect(color="#90a4ae", opacity=0.18)
            .encode(x="window_start:T", x2="window_end:T", y="range_low:Q", y2="range_high:Q")
        )
        layers.append(range_box)

        level_lines = pd.concat(
            [
                trades.assign(level=trades["range_high"], label="Buy-Stop")[
                    ["window_end", "exit_time", "level", "label"]
                ],
                trades.assign(level=trades["range_low"], label="Sell-Stop")[
                    ["window_end", "exit_time", "level", "label"]
                ],
            ],
            ignore_index=True,
        )
        stop_lines = (
            alt.Chart(level_lines)
            .mark_rule(strokeDash=[4, 3], strokeWidth=1, color="#607d8b")
            .encode(x="window_end:T", x2="exit_time:T", y="level:Q", tooltip=["label:N", alt.Tooltip("level:Q", format=".5f")])
        )
        layers.append(stop_lines)

        sl_lines = (
            alt.Chart(trades)
            .mark_rule(strokeDash=[2, 2], strokeWidth=1, color="#c62828")
            .encode(x="entry_time:T", x2="exit_time:T", y="sl:Q", tooltip=[alt.Tooltip("sl:Q", format=".5f", title="Stop-Loss")])
        )
        tp_lines = (
            alt.Chart(trades)
            .mark_rule(strokeDash=[2, 2], strokeWidth=1, color="#2e7d32")
            .encode(x="entry_time:T", x2="exit_time:T", y="tp:Q", tooltip=[alt.Tooltip("tp:Q", format=".5f", title="Take-Profit")])
        )
        layers.extend([sl_lines, tp_lines])

        entries = (
            alt.Chart(trades)
            .mark_point(shape="triangle-up", size=140, filled=True)
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
                    alt.Tooltip("direction:N"),
                    alt.Tooltip("sl:Q", format=".5f", title="Stop"),
                    alt.Tooltip("tp:Q", format=".5f", title="Ziel"),
                ],
            )
        )
        layers.append(entries)

        exits = (
            alt.Chart(trades)
            .mark_point(shape="diamond", size=110, filled=True)
            .encode(
                x="exit_time:T",
                y="exit_price:Q",
                color=alt.Color(
                    "exit_reason:N",
                    scale=alt.Scale(domain=list(_EXIT_COLORS), range=list(_EXIT_COLORS.values())),
                    legend=alt.Legend(title="Exit-Grund"),
                ),
                tooltip=[
                    alt.Tooltip("exit_time:T", title="Exit"),
                    alt.Tooltip("exit_price:Q", format=".5f"),
                    alt.Tooltip("exit_reason:N"),
                    alt.Tooltip("return_pct:Q", format=".3%"),
                ],
            )
        )
        layers.append(exits)

    return alt.layer(*layers).properties(height=480).interactive(bind_y=False)
