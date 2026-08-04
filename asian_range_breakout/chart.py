"""Visual entry-signal chart for the Gold Asian-Range Breakout: M15
candlesticks + the Asian-range box, the resting Buy-Stop/Sell-Stop levels,
entry/exit markers - so a trade can actually be SEEN, not just read as a
row in a table. Built for a bounded recent window (candlesticks over the
full 10.5y history would be unreadable and slow to render).

Color choices follow the dataviz skill's job-based rule: direction is
identity (categorical, fixed hue per direction, never cycled), exit reason
is state (status-like - stop is the "bad" outcome, time_exit/take_profit
are "good"), candle up/down uses the universal green/red price convention
(the one well-established exception to "no arbitrary rainbow" - every
trading terminal uses it, redefining it would hurt readability, not help
it). One shared x (time) axis throughout; price is the only y encoding -
no dual axis."""

import altair as alt
import pandas as pd

_UP_COLOR = "#26a69a"
_DOWN_COLOR = "#ef5350"
_LONG_COLOR = "#2e7d32"
_SHORT_COLOR = "#e65100"
_EXIT_COLORS = {"stop": "#c62828", "time_exit": "#1565c0", "take_profit": "#2e7d32", "data_end": "#757575"}


def build_entry_chart(price: pd.DataFrame, trades: pd.DataFrame) -> alt.LayerChart:
    """price: OHLC frame (lower-case columns), already sliced to the window
    to display. trades: output of simulate_asian_breakout, already sliced to
    trades whose entry_time falls within (roughly) that same window."""

    p = price.reset_index().rename(columns={price.index.name or "index": "time"})
    p["direction"] = (p["close"] >= p["open"]).map({True: "up", False: "down"})

    candle_body = (
        alt.Chart(p)
        .mark_bar(width=3)
        .encode(
            x=alt.X("time:T", title="Zeit (NY)"),
            y=alt.Y("open:Q", title="Preis (USD)", scale=alt.Scale(zero=False)),
            y2="close:Q",
            color=alt.Color(
                "direction:N",
                scale=alt.Scale(domain=["up", "down"], range=[_UP_COLOR, _DOWN_COLOR]),
                legend=alt.Legend(title="Kerze"),
            ),
            tooltip=[
                alt.Tooltip("time:T", title="Zeit"),
                alt.Tooltip("open:Q", format=".2f"),
                alt.Tooltip("high:Q", format=".2f"),
                alt.Tooltip("low:Q", format=".2f"),
                alt.Tooltip("close:Q", format=".2f"),
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
            .encode(x="window_end:T", x2="exit_time:T", y="level:Q", tooltip=["label:N", alt.Tooltip("level:Q", format=".2f")])
        )
        layers.append(stop_lines)

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
                    alt.Tooltip("entry_price:Q", format=".2f"),
                    alt.Tooltip("direction:N"),
                    alt.Tooltip("sl:Q", format=".2f", title="Stop"),
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
                    alt.Tooltip("exit_price:Q", format=".2f"),
                    alt.Tooltip("exit_reason:N"),
                    alt.Tooltip("return_pct:Q", format=".2%"),
                ],
            )
        )
        layers.append(exits)

    return alt.layer(*layers).properties(height=480).interactive(bind_y=False)
