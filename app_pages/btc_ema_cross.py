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

from pathlib import Path

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
from btc_ema_cross.optimization import (
    kelly_from_trades,
    simulate_asymmetric_short,
    simulate_chandelier_exit,
    simulate_dynamic_vol_scaled,
    simulate_volume_exhaustion_exit,
    simulate_with_tp_and_filters,
)

st.set_page_config(page_title="BTC EMA9/21 Crossover", page_icon=":material/currency_bitcoin:", layout="wide")

FULL_START = "2017-08-17"  # BTCUSDT listing date on Binance
END = "2026-08-13"
SHEET_START = "2023-07-01"  # the sheet's own tester window
IS_FRACTION = 0.7
PARAM_GRID = [(8, 20), (9, 21), (10, 22)]

# Committeter Snapshot statt Live-Binance-Fetch (Fix 2026-08-17): Streamlit
# Cloud hat nie den lokalen data_cache_crypto/-Cache (gitignored, frischer
# Checkout pro Deploy) und Binance.com blockiert viele Cloud-IP-Bereiche
# (HTTP 451/403) - siehe scripts/refresh_btc_ema_cross_data_snapshot.py fuer
# die volle Begruendung. Live-Fetch bleibt Fallback fuer lokale Entwicklung,
# falls der Snapshot mal fehlt.
DATA_SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "btc_ema_cross" / "data" / "btcusdt_1d_snapshot.parquet"


@st.cache_data(ttl="6h", show_spinner="Lade BTCUSDT Daily-Daten...")
def load_data() -> pd.DataFrame:
    if DATA_SNAPSHOT_PATH.exists():
        return pd.read_parquet(DATA_SNAPSHOT_PATH)
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
        help="Eigener Sweep (2026-08-15, 0.25R-2.0R): BE@0.75-1.0R ist leicht POSITIV "
        "(OOS PF 1.84→2.06, CAGR +3.6%→+4.0%), obwohl die Win-Rate sinkt (33%→27%) - kein "
        "starker Hebel, aber vertretbar. Standardmäßig AUS, da kein klarer Pflicht-Baustein.",
    )
    st.caption(f"Datenquelle: Binance BTCUSDT Daily, {FULL_START} bis {END} (gecacht).")

tab_components, tab_backtest, tab_risk, tab_tested = st.tabs(
    [
        ":material/school: Strategiebestandteile",
        ":material/query_stats: Backtest",
        ":material/shield: Risk Management",
        ":material/science: Getestet, nicht übernommen",
    ],
    on_change="rerun",
)

# =============================================================================
# Tab: Strategiebestandteile
# =============================================================================
def _render_tab_components():
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
def _render_tab_backtest():
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
def _render_tab_risk():
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

    st.divider()
    st.markdown("### :material/calculate: Kelly-Formel (auf den echten 1%-Risiko-Trades)")
    st.caption(
        "Gleiche Methodik wie 'Kelly-Formel & Risk Management' (Education-Track, OU-Modell): "
        "f* = WinRate - (1-WinRate)/PayoffRatio, aus den tatsächlichen R-Multiples der Baseline-Trades."
    )
    kelly_is_m = simulate_risk_sized(is_df, 9, 21, 100_000.0, 0.01, ATR_PERIOD, ATR_STOP_MULT, sim_from=None)
    kelly_oos_m = simulate_risk_sized(full, 9, 21, 100_000.0, 0.01, ATR_PERIOD, ATR_STOP_MULT, sim_from=oos_split_date)
    col_kis, col_koos = st.columns(2)
    for col, (klabel, kdata) in zip([col_kis, col_koos], [("IS", kelly_is_m), ("OOS", kelly_oos_m)]):
        k = kelly_from_trades(kdata["trades"], klabel)
        with col:
            with st.container(border=True):
                st.markdown(f"**{klabel}**")
                st.markdown(
                    f"- n={k['n_trades']}, WinRate {k['win_rate']:.1%}\n"
                    f"- AvgWinR {k['avg_win_r']:+.2f}, AvgLossR {k['avg_loss_r']:+.2f}, Payoff-Ratio b={k['payoff_ratio_b']:.2f}\n"
                    f"- **Kelly f\\* = {k['kelly_f']:.1%}**, Half-Kelly {k['half_kelly_f']:.1%}, "
                    f"Quarter-Kelly {k['quarter_kelly_f']:.1%}"
                )
    st.warning(
        "Kelly sagt 16-23% Risiko/Trade wäre \"optimal\" - **kein Freibrief**. Anders als beim "
        "OU-Modell ist hier nicht die Korrelations-Annahme das Problem (BTC hält immer nur eine "
        "Position) - sondern die dünne Stichprobe (n=27-49) und der zwischen IS und OOS stark "
        "schwankende Payoff-Schätzer (8.93 vs. 3.88) - ein einzelner Riesen-Trade kann das kippen. "
        "Volles Kelly bedeutet trotzdem 50-90% Drawdown-Risiko selbst bei echter Kante. "
        "Quarter-Kelly (~4-5.7%) liegt leicht über dem robusten 1-3%-Bereich oben - eine leichte "
        "Anhebung auf ~2-3% wäre Kelly-kompatibel, mehr nicht auf dieser Datenbasis vertretbar.",
        icon=":material/warning:",
    )

    with st.expander(":material/tune: Dynamisches/Vol-skaliertes Risk-Sizing -- getestet, kein klarer Gewinn"):
        st.caption(
            "Risiko skaliert mit median(ATR60)/aktuellem ATR, gedeckelt [0.5x, 1.5x] - weniger "
            "Risiko bei erhöhter Vol, mehr bei ungewöhnlich ruhigem Markt."
        )
        rows_dyn = []
        for dlabel, dsim in [("IS", None), ("OOS", oos_split_date)]:
            dpart = full if dsim is not None else is_df
            m_static = simulate_risk_sized(dpart, 9, 21, 100_000.0, 0.01, ATR_PERIOD, ATR_STOP_MULT, sim_from=dsim)
            m_dyn = simulate_dynamic_vol_scaled(dpart, 100_000.0, 0.01, ATR_PERIOD, ATR_STOP_MULT,
                                                 vol_lookback=60, scale_min=0.5, scale_max=1.5, sim_from=dsim)
            rows_dyn.append({"Fenster": dlabel, "Variante": "Statisch 1%", "PF": f"{m_static['profit_factor']:.2f}",
                              "CAGR": f"{m_static['cagr']:+.1%}", "MaxDD": f"{m_static['max_dd']:.1%}",
                              "WorstDay": f"{m_static['worst_day_pct']:+.2f}%"})
            rows_dyn.append({"Fenster": dlabel, "Variante": "Vol-skaliert", "PF": f"{m_dyn['profit_factor']:.2f}",
                              "CAGR": f"{m_dyn['cagr']:+.1%}", "MaxDD": f"{m_dyn['max_dd']:.1%}",
                              "WorstDay": f"{m_dyn['worst_day_pct']:+.2f}%"})
        st.dataframe(pd.DataFrame(rows_dyn), hide_index=True, width="stretch")
        st.caption(
            "Leicht besser bei PF/CAGR, leicht schlechter bei MaxDD/WorstDay - im Wesentlichen ein "
            "Unentschieden. Der ATR-Stop selbst skaliert Positionsgröße bereits implizit mit "
            "Volatilität (weiterer Stop bei hoher Vol → kleinere Position); dieser Test ist ein "
            "zusätzlicher Hebel oben drauf, kein grundlegend neues Konzept. **Nicht übernommen.**"
        )

# =============================================================================
# Tab: Getestet, nicht uebernommen
# =============================================================================
def _render_tab_tested():
    st.markdown("## :material/science: Getestet, nicht übernommen")
    st.caption(
        "Vollständiger Forschungsverlauf: `knowledge/resources/trend-following-momentum.md`. "
        "Reproduzierbar über `scripts/research_ema_9_21_cross_diversified.py`, "
        "`scripts/research_ema_9_21_cross_multi_asset.py`, "
        "`scripts/research_ema_9_21_cross_exits.py`."
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

    st.markdown("### ATR-Stop-Multiplikator-Sweep (1.0x - 3.5x)")
    rows_sl = []
    for slabel, ssim in [("IS", None), ("OOS", oos_split_date)]:
        spart = full if ssim is not None else is_df
        for mult in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]:
            sm = simulate_risk_sized(spart, 9, 21, 100_000.0, 0.01, ATR_PERIOD, mult, sim_from=ssim)
            rows_sl.append({
                "Fenster": slabel, "ATR-Mult": f"{mult}x", "n": sm["n_trades"],
                "PF": f"{sm['profit_factor']:.2f}", "CAGR": f"{sm['cagr']:+.1%}", "MaxDD": f"{sm['max_dd']:.1%}",
            })
    st.dataframe(pd.DataFrame(rows_sl), hide_index=True, width="stretch")
    st.warning(
        "PF bleibt über den ganzen Bereich in einem Plateau (IS 3.11-3.44, OOS 1.75-2.16) - kein "
        "einzelner Wert sticht heraus. Engere Stops erhöhen CAGR deutlich (mehr Positionsgröße pro "
        "$-Risiko), aber auch den Drawdown - reiner Risiko-Dial, kein Free Lunch. Der 2.0x-Standard "
        "ist vertretbar, aber auf dieser Datenbasis nicht nachweisbar optimal.",
        icon=":material/warning:",
    )

    st.markdown("### Take-Profit-Test (0.5R - 4R vs. kein TP)")
    rows_tp = []
    for tlabel, tsim in [("IS", None), ("OOS", oos_split_date)]:
        tpart = full if tsim is not None else is_df
        m_notp = simulate_with_tp_and_filters(tpart, 100_000.0, 0.01, ATR_PERIOD, ATR_STOP_MULT, sim_from=tsim)
        rows_tp.append({"Fenster": tlabel, "Variante": "Kein TP", "PF": f"{m_notp['profit_factor']:.2f}",
                         "CAGR": f"{m_notp['cagr']:+.1%}"})
        for tp in [0.5, 1.0, 1.5, 2.0, 3.0, 4.0]:
            m_tp = simulate_with_tp_and_filters(tpart, 100_000.0, 0.01, ATR_PERIOD, ATR_STOP_MULT, tp_r_mult=tp, sim_from=tsim)
            rows_tp.append({"Fenster": tlabel, "Variante": f"TP={tp}R", "PF": f"{m_tp['profit_factor']:.2f}",
                             "CAGR": f"{m_tp['cagr']:+.1%}"})
    st.dataframe(pd.DataFrame(rows_tp), hide_index=True, width="stretch")
    st.error(
        "**Robust bestätigt schädlich** - jedes getestete TP-Level verschlechtert PF gegenüber "
        "\"kein TP\", sowohl IS als auch OOS. Erklärung passt zur Kelly-Analyse oben: die Kante lebt "
        "von seltenen großen Gewinnern (AvgWinR 2.3-6.3R) - ein TP kappt genau das. Identisches "
        "Muster wie bei Gold Asian-Range-Breakout. **Kein TP bleibt richtig.**",
        icon=":material/dangerous:",
    )

    st.markdown("### Breakeven-Sweep (0.25R - 2.0R)")
    rows_be = []
    for belabel, besim in [("IS", None), ("OOS", oos_split_date)]:
        bepart = full if besim is not None else is_df
        m0 = simulate_risk_sized(bepart, 9, 21, 100_000.0, 0.01, ATR_PERIOD, ATR_STOP_MULT, be_trigger_r=None, sim_from=besim)
        rows_be.append({
            "Fenster": belabel, "BE-Trigger": "Kein BE", "n": m0["n_trades"], "WinRate": f"{m0['win_rate']:.1%}",
            "PF": f"{m0['profit_factor']:.2f}", "CAGR": f"{m0['cagr']:+.1%}", "MaxDD": f"{m0['max_dd']:.1%}",
        })
        for be in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]:
            m = simulate_risk_sized(bepart, 9, 21, 100_000.0, 0.01, ATR_PERIOD, ATR_STOP_MULT, be_trigger_r=be, sim_from=besim)
            rows_be.append({
                "Fenster": belabel, "BE-Trigger": f"@{be}R", "n": m["n_trades"], "WinRate": f"{m['win_rate']:.1%}",
                "PF": f"{m['profit_factor']:.2f}", "CAGR": f"{m['cagr']:+.1%}", "MaxDD": f"{m['max_dd']:.1%}",
            })
    st.dataframe(pd.DataFrame(rows_be), hide_index=True, width="stretch")
    st.success(
        "**Einzige Ausnahme vom Muster \"jeder frühere Exit schadet\"**: BE@0.75-1.0R ist OOS leicht "
        "POSITIV (PF 1.84→2.06, CAGR +3.6%→+4.0%), obwohl die Win-Rate real sinkt (33%→25-27% - mehr "
        "Trades werden am Breakeven statt mit Gewinn oder mit vollem Verlust beendet). Kein starker "
        "Hebel, aber vertretbar als psychologisches Sicherheitsnetz gegen den Fall \"Gewinn wird "
        "wieder zu Verlust\". **Nicht als Standard übernommen** (Effekt zu klein, um die zusätzliche "
        "Logik-Komplexität im Live-Scanner zu rechtfertigen), aber die einzige der hier getesteten "
        "Exit-Varianten, die es wert wäre, bei Bedarf nachzurüsten.",
        icon=":material/check_circle:",
    )

    st.markdown("### Chandelier-Trailing-Stop (2.0x - 4.0x ATR)")
    rows_ch = []
    for chlabel, chsim in [("IS", None), ("OOS", oos_split_date)]:
        chpart = full if chsim is not None else is_df
        for mult in [2.0, 2.5, 3.0, 3.5, 4.0]:
            m = simulate_chandelier_exit(chpart, 100_000.0, 0.01, ATR_PERIOD, ATR_STOP_MULT, mult, sim_from=chsim)
            rows_ch.append({
                "Fenster": chlabel, "Chandelier": f"{mult}x", "n": m["n_trades"], "WinRate": f"{m['win_rate']:.1%}",
                "PF": f"{m['profit_factor']:.2f}", "CAGR": f"{m['cagr']:+.1%}", "MaxDD": f"{m['max_dd']:.1%}",
            })
    st.dataframe(pd.DataFrame(rows_ch), hide_index=True, width="stretch")
    st.error(
        "Trailing-Stop auf Basis des höchsten Close seit Entry minus Vielfaches des ATR - zieht den "
        "Stop nur nach, gibt aber nie mehr Puffer. **Durchgehend schlechter als die feste-Stop-"
        "Baseline** über jeden getesteten Multiplikator, beide Fenster (bester OOS-Wert 3.0x: PF "
        "1.75/CAGR +3.1% vs. Baseline PF 1.84/CAGR +3.6%). Gleicher Mechanismus wie beim TP: sichert "
        "Gewinne vor dem eigentlichen Crossunder und kappt genau die großen Trend-Trades, die die "
        "Kante ausmachen. **Nicht übernommen.**",
        icon=":material/dangerous:",
    )

    st.markdown("### Volumen-Exhaustion-Exit (Tagesvolumen < X% des 20-Tage-Schnitts, ab Y R Gewinn)")
    rows_ve = []
    for velabel, vesim in [("IS", None), ("OOS", oos_split_date)]:
        vepart = full if vesim is not None else is_df
        for thresh in [0.3, 0.5, 0.7]:
            for minr in [0.5, 1.0]:
                m = simulate_volume_exhaustion_exit(vepart, 100_000.0, 0.01, ATR_PERIOD, ATR_STOP_MULT, 20, thresh, minr, sim_from=vesim)
                rows_ve.append({
                    "Fenster": velabel, "Vol-Schwelle": f"<{thresh:.0%}", "ab R": f"{minr}R", "n": m["n_trades"],
                    "PF": f"{m['profit_factor']:.2f}", "CAGR": f"{m['cagr']:+.1%}",
                })
    st.dataframe(pd.DataFrame(rows_ve), hide_index=True, width="stretch")
    st.error(
        "Exit am nächsten Open, wenn das Tagesvolumen unter die Schwelle fällt UND der Trade "
        "mindestens Y R im Gewinn ist (\"Teilnahme trocknet aus, Gewinn mitnehmen\"). Bei enger "
        "Schwelle (<30%) praktisch neutral, weil es kaum auslöst - bei lockereren Schwellen (50-70%) "
        "klar schädlich (OOS PF 1.84→1.22-1.50). Gleiches Muster wie TP/Chandelier: jeder "
        "Gewinnsicherungs-Mechanismus vor dem Crossunder schneidet die großen Trend-Trades ab. "
        "**Nicht übernommen.**",
        icon=":material/dangerous:",
    )

    st.markdown("### Kleine Gegenposition am Crossunder statt Flat (0.1x - 1.0x Risiko)")
    rows_short = []
    for slabel2, ssim2 in [("IS", None), ("OOS", oos_split_date)]:
        spart2 = full if ssim2 is not None else is_df
        m0 = simulate_asymmetric_short(spart2, 100_000.0, 0.01, 0.0, ATR_PERIOD, ATR_STOP_MULT, sim_from=ssim2)
        rows_short.append({
            "Fenster": slabel2, "Short-Größe": "Flat (Baseline)", "Short-PnL": "-",
            "PF": f"{m0['profit_factor']:.2f}", "CAGR": f"{m0['cagr']:+.1%}",
        })
        for frac in [0.1, 0.25, 0.5, 0.75, 1.0]:
            m = simulate_asymmetric_short(spart2, 100_000.0, 0.01, frac, ATR_PERIOD, ATR_STOP_MULT, sim_from=ssim2)
            rows_short.append({
                "Fenster": slabel2, "Short-Größe": f"{frac}x", "Short-PnL": f"${m['short_pnl']:+,.0f}",
                "PF": f"{m['profit_factor']:.2f}", "CAGR": f"{m['cagr']:+.1%}",
            })
    st.dataframe(pd.DataFrame(rows_short), hide_index=True, width="stretch")
    st.error(
        "Statt am Crossunder flat zu gehen, eine kleine Short-Position eröffnen (analog zur Long-"
        "Logik, eigener ATR-Stop). Der Short-Leg ist bei **jeder** getesteten Größe negativ, beide "
        "Fenster, ohne Vorzeichenwechsel über den gesamten Bereich - kein Small-Sample-Zufall, "
        "sondern ein gleichmäßig mit der Größe skalierender Schaden. Grund: ein Crossunder zeigt nur "
        "\"Momentum abgekühlt\", nicht zuverlässig \"jetzt beginnt ein Abwärtstrend\" - BTCs "
        "struktureller Aufwärts-Drift macht das Shorten dieses Signals zu einer Negativ-Erwartungswert"
        "-Wette. **Flat bleibt strikt besser. Nicht übernommen.**",
        icon=":material/dangerous:",
    )

    st.markdown("### Regimefilter (ADX-Mindestwert, SMA200-Trend)")
    rows_f = []
    for flabel, fsim in [("IS", None), ("OOS", oos_split_date)]:
        fpart = full if fsim is not None else is_df
        m_nofilt = simulate_with_tp_and_filters(fpart, 100_000.0, 0.01, ATR_PERIOD, ATR_STOP_MULT, sim_from=fsim)
        rows_f.append({"Fenster": flabel, "Filter": "Kein Filter", "n": m_nofilt["n_trades"], "PF": f"{m_nofilt['profit_factor']:.2f}"})
        for adx_min in [15, 20, 25]:
            m_f = simulate_with_tp_and_filters(fpart, 100_000.0, 0.01, ATR_PERIOD, ATR_STOP_MULT, adx_min=adx_min, sim_from=fsim)
            rows_f.append({"Fenster": flabel, "Filter": f"ADX>={adx_min}", "n": m_f["n_trades"], "PF": f"{m_f['profit_factor']:.2f}"})
        m_trend = simulate_with_tp_and_filters(fpart, 100_000.0, 0.01, ATR_PERIOD, ATR_STOP_MULT, trend_sma=200, sim_from=fsim)
        rows_f.append({"Fenster": flabel, "Filter": "SMA200-Trend", "n": m_trend["n_trades"], "PF": f"{m_trend['profit_factor']:.2f}"})
    st.dataframe(pd.DataFrame(rows_f), hide_index=True, width="stretch")
    st.error(
        "**Nicht robust genug, um zu übernehmen.** ADX>=25 sieht IS spektakulär aus (PF 6.74), aber "
        "ADX>=20 bricht OOS zunächst ein (PF 1.33 vs. 1.84 Baseline) und die Erholung bei ADX>=25 "
        "steht auf nur n=13 OOS-Trades - zu dünn. SMA200-Trend ähnlich (IS PF 5.77, OOS PF 1.73, "
        "unter Baseline). Anders als bei Gold (Tausende Trades, ADX-Filter sauber IS UND OOS "
        "bestätigt) hat BTC bei ~1 Trade/Monat schlicht nicht genug Stichprobe, um einen Filter "
        "verlässlich zu validieren.",
        icon=":material/dangerous:",
    )

    st.info(
        "**Was stattdessen funktioniert**: kleineres Risiko pro Trade (reduziert den $-Schaden "
        "proportional, ohne Vorhersage nötig) und echte Diversifikation über unkorrelierte "
        "Asset-Klassen statt mehrerer Krypto-Paare - siehe \"Portfolio Management\".",
        icon=":material/lightbulb:",
    )


# ============================================================ Lazy dispatch
# st.tabs() renders ALL tab bodies on every rerun by default, even hidden ones.
# on_change="rerun" above makes tab.open reflect the actually-selected tab; only
# that one's render function runs now (2026-08-20 Streamlit Cloud memory-limit fix,
# see app_pages/portfolio_construction.py for the original instance of this fix).
# Sidebar widgets (capital, risk_pct, use_be) execute unconditionally above,
# outside any tab, so tab_risk can read them regardless of which tab is open.
for _tab, _render in [
    (tab_components, _render_tab_components),
    (tab_backtest, _render_tab_backtest),
    (tab_risk, _render_tab_risk),
    (tab_tested, _render_tab_tested),
]:
    if _tab.open:
        with _tab:
            _render()
