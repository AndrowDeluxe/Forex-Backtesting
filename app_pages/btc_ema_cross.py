"""BTC/USDT EMA9/21 -- interactive dashboard for btc_ema_cross/.

Source: "The Backtest Machine" cheat sheet (Miles Deutscher Finance,
companion sheet to a YouTube video) - NOT an academic paper. The sheet's
own headline example: EMA9 crosses above EMA21 -> long, crosses back under
-> flat, no leverage, no take-profit, tested on BTCUSDT daily. Research
thread 2026-08-14/15: reproduced on this repo's own real Binance data
(auction_playbook.data.fetch_klines), extended with risk-based position
sizing, long/short comparison, a funded-challenge compliance check, an
own-capital risk sweep, three crash-filter candidates (all tested negative),
and a BTC+ETH+SOL diversification test (tested, not adopted - see
knowledge/resources/trend-following-momentum.md for the full research log).
"""

import pandas as pd

import streamlit as st
from auction_playbook.data import fetch_klines
from btc_ema_cross.engine import (
    ATR_PERIOD,
    ATR_STOP_MULT,
    COMMISSION,
    simulate_ema_cross,
    simulate_ema_cross_ls,
    simulate_risk_sized,
)

st.set_page_config(page_title="BTC EMA9/21 Crossover", page_icon=":material/currency_bitcoin:", layout="wide")

FULL_START = "2017-08-17"  # BTCUSDT listing date on Binance
END = "2026-08-13"
SHEET_START = "2023-07-01"  # the sheet's own tester window
IS_FRACTION = 0.7
PARAM_GRID = [(8, 20), (9, 21), (10, 22)]


@st.cache_data(ttl="6h", show_spinner="Lade BTCUSDT Daily-Daten (Binance)...")
def load_data() -> pd.DataFrame:
    return fetch_klines("BTCUSDT", "1d", FULL_START, END)


full = load_data()
split_i = int(len(full) * IS_FRACTION)
is_df, oos_split_date = full.iloc[:split_i], full.index[split_i]
windows = [("Full", full, None), ("IS", is_df, None), ("OOS", full, oos_split_date)]

st.markdown("## :material/currency_bitcoin: BTC/USDT EMA9/21 Crossover")
st.caption(
    "Quelle: \"The Backtest Machine\"-Cheat-Sheet (Miles Deutscher Finance) - kein akademisches "
    "Paper, sondern ein Workflow-Leitfaden mit einem konkreten Beispiel-Regelsatz. Auf echten "
    "Binance-Daten dieses Repos nachgerechnet, nicht die Zahlen des Sheets übernommen."
)

with st.sidebar:
    st.markdown("### Konfiguration")
    capital = st.number_input("Startkapital ($)", 1_000, 1_000_000, 100_000, 1_000)
    risk_pct = st.slider(
        "Risiko pro Trade (% des aktuellen Eigenkapitals)", 0.25, 5.0, 1.0, 0.25,
        help="Eigener Zusatz (nicht Teil des Original-Sheets, das keinen Stop-Loss hat) - siehe "
        "Tab 'Risk Management'. Empfehlung aus dem Sweep: 1-3% - OOS-Calmar reagiert kaum auf "
        "höheres Risiko, mehr Risiko heißt vor allem mehr Drawdown ohne bessere risikoadjustierte Rendite.",
    ) / 100
    use_be = st.toggle(
        "Breakeven-Stop aktivieren (ab 1R)", value=False,
        help="Eigener Test (2026-08-14): bewegt CAGR kaum (+3.0%→+3.4% im OOS-Beispiel), halbiert "
        "aber die Win-Rate (33%→23%), weil viele Trades, die sich später erholt hätten, vorzeitig "
        "auf Breakeven gestoppt werden. Standardmäßig AUS.",
    )
    st.caption(f"Datenquelle: Binance BTCUSDT Daily, {FULL_START} bis {END} (gecacht).")

tab_components, tab_backtest, tab_risk, tab_tested = st.tabs(
    [
        ":material/school: Strategiebestandteile",
        ":material/query_stats: Backtest",
        ":material/shield: Risk Management",
        ":material/science: Getestet, nicht übernommen",
    ]
)

# =============================================================================
# Tab: Strategiebestandteile
# =============================================================================
with tab_components:
    st.markdown("## :material/school: Regeln")
    st.markdown(
        "1. **Long**, wenn EMA9 auf Schlusskursbasis über EMA21 kreuzt.\n"
        "2. **Flat**, wenn EMA9 zurück unter EMA21 kreuzt.\n"
        "3. **Kein Take-Profit** - der Crossover selbst ist der einzige geplante Exit.\n"
        "4. Fill am **Open der nächsten Kerze** nach dem Signal (kein Same-Bar-Fill).\n"
        "5. Kein Hebel, Long-only im Original."
    )
    st.info(
        "**Warum es laut Sheet auf BTC funktioniert, nicht überall**: BTC bewegt sich ~1.7%/Tag "
        "und trendet gewaltsam - ein schneller 9/21-Crossover zahlt eine \"Whipsaw-Steuer\", die "
        "nur sehr volatile Trendmärkte abdecken. Eigener Test bestätigt das (Tab \"Getestet, nicht "
        "übernommen\"): dieselbe Regel unverändert auf Gold/EURUSD/S&P 500 verliert auf EURUSD "
        "aktiv Geld und lässt auf Gold/S&P den Großteil der Buy&Hold-Rendite liegen.",
        icon=":material/info:",
    )
    st.markdown("### Kosten & Annahmen")
    st.markdown(
        f"- Kommission: **{COMMISSION:.2%} pro Seite** (Ein- und Ausstieg), matched das Sheet\n"
        "- Slippage: nicht modelliert\n"
        "- Datenquelle: Binance Spot-Klines (`auction_playbook.data.fetch_klines`), UTC\n"
        f"- Volle Historie: {FULL_START} (Binance-Listing) bis {END}"
    )
    st.warning(
        "Das Original-Sheet hat **keinen Stop-Loss** - \"Risiko pro Trade\" ist ohne Stop nicht "
        "definiert. Der ATR-Stop im Tab \"Risk Management\" ist eine offengelegte eigene "
        "Erweiterung, kein Sheet-Bestandteil.",
        icon=":material/warning:",
    )

# =============================================================================
# Tab: Backtest
# =============================================================================
with tab_backtest:
    st.markdown("## :material/query_stats: Backtest (100%-of-Equity, wie im Sheet)")

    sheet_start_ts = pd.Timestamp(SHEET_START, tz="UTC")
    bh_window = full.loc[full.index >= sheet_start_ts, "close"]
    bh_ret = bh_window.iloc[-1] / bh_window.iloc[0] - 1
    bh_dd = ((bh_window / bh_window.iloc[0]) / (bh_window / bh_window.iloc[0]).cummax() - 1).min()

    st.markdown(f"### Sheet-Reproduktion ({SHEET_START} -> {END})")
    st.caption(f"Buy & Hold BTC im selben Fenster: TotalReturn={bh_ret:+.1%}, MaxDD={bh_dd:.1%}")
    cols = st.columns(3)
    for col, (fast, slow) in zip(cols, PARAM_GRID):
        m = simulate_ema_cross(full, fast, slow, sim_from=sheet_start_ts)
        with col:
            with st.container(border=True):
                st.markdown(f"**EMA {fast}/{slow}**" + (" (Sheet-Wert)" if (fast, slow) == (9, 21) else ""))
                st.markdown(
                    f"- {m['n_trades']} Trades\n"
                    f"- WinRate {m['win_rate']:.1%}, PF {m['profit_factor']:.2f}\n"
                    f"- Return {m['total_return']:+.1%}, CAGR {m['cagr']:+.1%}\n"
                    f"- MaxDD {m['max_dd']:.1%}"
                )
    st.success(
        "**Überfitting-Check (Sheets eigenes Caveat 4) bestanden**: Nachbarparameter (8/20, 10/22) "
        "bilden ein Plateau um 9/21, kein isolierter Spike - die Sheet-Behauptung (WinRate ~35%, "
        "PF ~3, halber Drawdown ggü. Buy&Hold) hält auf echten Daten stand.",
        icon=":material/check_circle:",
    )

    st.divider()
    st.markdown("### Volle Historie, Long/Flat vs. Long/Short, IS/OOS-Split")
    st.caption(
        f"IS: {is_df.index[0].date()} -> {is_df.index[-1].date()} ({len(is_df)} Bars)  |  "
        f"OOS: {oos_split_date.date()} -> {full.index[-1].date()} ({len(full) - split_i} Bars)"
    )
    for label, part, sim_from in windows:
        w_start = sim_from.date() if sim_from is not None else part.index[0].date()
        m_lf = simulate_ema_cross_ls(part, 9, 21, allow_short=False, sim_from=sim_from)
        m_ls = simulate_ema_cross_ls(part, 9, 21, allow_short=True, sim_from=sim_from)
        with st.container(border=True):
            st.markdown(f"**{label}** ({w_start} -> {part.index[-1].date()})")
            col_lf, col_ls = st.columns(2)
            col_lf.markdown(
                f"Long/Flat: n={m_lf['n_trades']}, WinRate {m_lf['win_rate']:.1%}, "
                f"PF {m_lf['profit_factor']:.2f}, CAGR {m_lf['cagr']:+.1%}, MaxDD {m_lf['max_dd']:.1%}"
            )
            col_ls.markdown(
                f"Long/Short: n={m_ls['n_trades']}, WinRate {m_ls['win_rate']:.1%}, "
                f"PF {m_ls['profit_factor']:.2f}, CAGR {m_ls['cagr']:+.1%}, MaxDD {m_ls['max_dd']:.1%}"
            )
    st.error(
        "**Long/Short ist in jedem Fenster schlechter als Long/Flat** (niedrigerer PF, niedrigerer "
        "CAGR, höherer MaxDD) - und das VOR Funding-Kosten (nicht modelliert, bei Perp-Shorts in "
        "Aufwärts-/Seitwärtsphasen zusätzlich negativ). Grund: BTCs starker struktureller "
        "Aufwärts-Drift - Cash halten unterhalb des Crossovers vermeidet Drawdown-Exposure, "
        "Shorten geht zusätzliches asymmetrisches Risiko ein, das sich nicht auszahlt. "
        "**Nicht empfohlen.**",
        icon=":material/dangerous:",
    )

# =============================================================================
# Tab: Risk Management
# =============================================================================
with tab_risk:
    st.markdown("## :material/shield: Risiko-basiertes Sizing")
    st.caption(
        f"ATR({ATR_PERIOD})x{ATR_STOP_MULT}-Stop (eigene Erweiterung, siehe Strategiebestandteile), "
        f"kein Hebel, Long/Flat (Long/Short performt schlechter, siehe Backtest-Tab). "
        f"Konfiguration aus der Sidebar: ${capital:,.0f} Startkapital, {risk_pct:.2%} Risiko/Trade"
        + (", Breakeven-Stop @1R aktiv" if use_be else "") + "."
    )

    for label, part, sim_from in windows:
        m = simulate_risk_sized(
            part, 9, 21, capital, risk_pct, ATR_PERIOD, ATR_STOP_MULT,
            be_trigger_r=1.0 if use_be else None, sim_from=sim_from,
        )
        w_start = sim_from.date() if sim_from is not None else part.index[0].date()
        calmar = m["cagr"] / abs(m["max_dd"]) if m["max_dd"] < 0 else float("nan")
        with st.container(border=True):
            st.markdown(f"**{label}** ({w_start} -> {part.index[-1].date()})")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Trades", m["n_trades"])
            c2.metric("Profit Factor", f"{m['profit_factor']:.2f}")
            c3.metric("CAGR", f"{m['cagr']:+.1%}")
            c4.metric("Max Drawdown", f"{m['max_dd']:.1%}")
            c5.metric("Calmar", f"{calmar:.2f}")
            st.caption(
                f"EndEquity=${m['end_equity']:,.0f}  |  Schlechtester Tag {m['worst_day_pct']:+.2f}% "
                f"({m['worst_day_date'].date()})  |  StoppedOut {m['n_stopped']}/{m['n_trades']}  |  "
                f"SizeCapped (Hebel-Deckel) {m['n_capped']}/{m['n_trades']}"
            )

    st.divider()
    st.markdown("### Empfehlung: 1-3% Risiko/Trade")
    st.markdown(
        "Eigener Risk-%-Sweep (0.5-12%, siehe `scripts/research_ema_9_21_cross_btc.py`) zeigt: "
        "**OOS-Calmar bleibt über den gesamten Bereich flach (~0.55-0.62)**, während IS-Calmar mit "
        "steigendem Risiko bis ~5% steigt und danach durch den Kein-Hebel-Deckel wieder fällt. Da "
        "OOS die einzige echte Holdout-Instanz ist, wäre \"mehr Risiko = besser\" nur aus IS "
        "abgeleitet eine klassische Überanpassung. **1-3% Risiko/Trade** ist der vertretbare Bereich "
        "für ein Konto ohne Zeitlimit - darüber steigt vor allem der Drawdown, ohne dass sich das "
        "OOS-Chance-Risiko-Verhältnis entsprechend verbessert."
    )

    with st.expander(":material/military_tech: Funded-Challenge-Compliance-Check (100k, max 3%/Tag, 10%-Ziel)"):
        st.caption(
            "Gleiche Regeln/Methodik wie `ou_paper_backtest/oos_holdout_challenge_profiles.py` - "
            "ausgewertet auf OOS (der echte Holdout)."
        )
        challenge_profiles = [
            ("1% Risiko, kein BE", 0.01, None),
            ("0.25% Risiko, kein BE", 0.0025, None),
            ("1% Risiko, BE@1R", 0.01, 1.0),
            ("0.25% Risiko, BE@1R", 0.0025, 1.0),
        ]
        rows = []
        for clabel, crisk, cbe in challenge_profiles:
            cm = simulate_risk_sized(full, 9, 21, 100_000.0, crisk, ATR_PERIOD, ATR_STOP_MULT,
                                      be_trigger_r=cbe, sim_from=oos_split_date)
            rows.append({
                "Profil": clabel, "n": cm["n_trades"], "CAGR": f"{cm['cagr']:+.1%}",
                "MaxDD": f"{cm['max_dd']:.1%}", "Schlechtester Tag": f"{cm['worst_day_pct']:+.2f}%",
                "3%-Regel": "verletzt" if cm["breached_3pct_daily_rule"] else "ok",
                "Tage bis +10%": str(cm["days_to_10pct_target"]) if cm["days_to_10pct_target"] is not None else "nicht erreicht",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.info(
            "Die 3%-Tagesregel ist bei keinem Profil das Problem (schlechtester Tag bleibt weit "
            "darunter) - Single-Instrument, Daily-Close-Signale und ATR-Stop erzeugen strukturell "
            "keine großen Ein-Tages-Verluste.",
            icon=":material/insights:",
        )

# =============================================================================
# Tab: Getestet, nicht uebernommen
# =============================================================================
with tab_tested:
    st.markdown("## :material/science: Getestet, nicht übernommen")
    st.caption(
        "Vollständiger Forschungsverlauf: `knowledge/resources/trend-following-momentum.md`. "
        "Reproduzierbar über `scripts/research_ema_9_21_cross_diversified.py`, "
        "`scripts/research_ema_9_21_cross_multi_asset.py`."
    )

    st.markdown("### EMA9/21 unverändert auf Gold/EURUSD/S&P 500")
    st.error(
        "**EURUSD verliert aktiv Geld** (PF 0.84, CAGR -0.6%) - FX-Majors sind mean-reverting, "
        "kein Trend für einen schnellen Crossover. **Gold und S&P sind technisch profitabel, "
        "lassen aber fast die gesamte Rendite liegen** (Gold +72.9% vs. Buy&Hold +302.6%; S&P "
        "+25.8% vs. +497.9%). Bestätigt Sheet-Caveat 1: dieselbe Regel ist kein universeller "
        "Trendfolge-Baustein, sondern ein BTC-spezifischer Edge.",
        icon=":material/dangerous:",
    )

    st.markdown("### Diversifikation über BTC+ETH+SOL (gleiches Signal je Asset)")
    st.error(
        "Erhöht Trade-Frequenz und CAGR (OOS +3.6% → +8.0%), aber der schlechteste Einzeltag "
        "verschlechtert sich überproportional (-1.67% → -4.72%, fast das 3-fache) - selbst mit "
        "einem 2.5%-Aggregat-Risiko-Deckel bleibt es bei -3.59%. Grund: BTC/ETH/SOL crashen "
        "praktisch gleichzeitig (Korrelation geht in Stress-Phasen gegen 1) - kein echtes "
        "diversifiziertes Risiko, nur konzentriertes Krypto-Beta mit drei Hebeln auf dieselbe "
        "Wette. Für ein Funded-Konto mit Tagesregel nicht empfehlenswert.",
        icon=":material/dangerous:",
    )

    st.markdown("### Drei Crash-Vorwarn-Filter-Kandidaten")
    st.error(
        "Vol-Expansion (ATR3/ATR14), Cross-Asset-Korrelation (BTC-ETH) und Taker-Sell-Aggression "
        "(CVD-Delta) empirisch gegen die volle Historie getestet, nicht nur an den bekannten "
        "Crash-Tagen: alle drei feuern zu häufig (14-55% aller Tage) und zeigen keine belastbare "
        "Vorhersagekraft (bedingte vs. unbedingte Tail-Verteilung praktisch identisch). Passt zur "
        "Marktstruktur - Liquidationskaskaden laufen in Stunden/Minuten ab, kein Tages-Bar kann "
        "das einen Tag im Voraus erkennen.",
        icon=":material/dangerous:",
    )

    st.info(
        "**Was stattdessen funktioniert**: kleineres Risiko pro Trade (reduziert den $-Schaden "
        "proportional, ohne Vorhersage nötig) und echte Diversifikation über unkorrelierte "
        "Asset-Klassen statt mehrerer Krypto-Paare - siehe \"Portfolio Management\".",
        icon=":material/lightbulb:",
    )
