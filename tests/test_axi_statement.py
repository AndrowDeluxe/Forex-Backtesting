"""Axi-Statement-Parser (fusion_lab/trades). Fixtures sind woertliche
Ausschnitte aus den echten Statements 2025 (Textextraktion wie pypdf)."""

import pandas as pd
import pytest

from fusion_lab.trades.axi_statement import money, parse_text, positions, equity_at

# Konto 4698524 vollstaendig (2 Seiten, inkl. Seitenumbruch vor "Summary:").
FULL_4698524 = """AxiCorp Financial Services Pty Ltd
Account: 4698524 Name: Andre Gierhold Currency: USD Leverage: 1:1000 2026 July 21, 23:01
Closed Transactions:
Ticket Open Time Type Volume Item Price S / L T / P Close Time Price Commission Taxes Swap Profit
96181794 2025.07.24 01:15:10 buy 2.41 ethusd 3604.790 3604.700 4000.000 2025.08.01 11:05:39 3604.700 0.00 0.00 -33.74 -0.22
[sl]
96413772 2025.08.06 15:53:19 buy 0.15 xagusd.pro 37.739 37.740 0.000 2025.08.11 10:41:02 37.739 -1.05 0.00 -20.64 0.00
[sl]
96413823 2025.08.06 15:54:33 buy 0.21 xauusd.pro 3368.28 3370.00 0.00 2025.08.06 21:14:48 3370.00 -1.47 0.00 0.00 36.12
[sl]
96551526 2025.08.14 10:58:34 buy 0.15 xauusd.pro 3345.07 3342.00 3500.00 2025.08.14 17:01:36 3342.00 -1.05 0.00 0.00 -46.05
[sl]
96644757 2025.08.20 13:45:44 buy 0.07 xagusd.pro 37.085 37.085 0.000 2025.08.20 15:49:14 37.541 -0.49 0.00 0.00 159.60
to #96647823
96647823 2025.08.20 13:45:44 buy 0.08 xagusd.pro 37.085 37.085 0.000 2025.08.22 08:03:57 38.047 -0.56 0.00 -8.80 384.80
from #96644757
96758234 2025.08.27 15:01:05 buy 0.15 xagusd.pro 38.305 38.210 0.000 2025.08.28 15:31:54 38.990 -1.05 0.00 -12.38 513.75
97003337 2025.09.10 04:23:39 buy 0.33 eurusd.pro 1.16920 1.16600 1.19000 2025.09.15 10:21:54 1.17368 -2.31 0.00 -14.03 147.84
to #97103396
97103396 2025.09.10 04:23:39 buy 0.34 eurusd.pro 1.16920 1.16950 1.19000 2025.09.15 13:38:45 1.17571 -2.38 0.00 -14.46 221.34
from #97003337
97479620 2025.10.01 23:19:58 buy 0.03 usdjpy.pro 147.127 145.700 0.000 2025.10.01 23:20:06 147.128 -0.14 0.00 0.00 0.02
96357466 2025.08.06 18:41:03 sell 0.51 gbpjpy.pro 196.900 198.500 0.000 2025.08.08 12:40:24 198.499 -3.57 0.00 -36.05 -552.33
[sl]
96422403 2025.08.06 23:38:46 sell 0.75 usdjpy.pro 147.411 147.880 0.000 2025.08.07 11:27:42 147.097 -5.25 0.00 -29.78 160.10
to #96431483
96431483 2025.08.06 23:38:46 sell 0.76 usdjpy.pro 147.411 147.500 0.000 2025.08.07 17:08:57 147.496 -5.32 0.00 -30.17 -43.80
from #96422403[sl]
96474705 2025.08.11 01:04:53 sell 0.51 gbpjpy.pro 198.490 199.400 0.000 2025.08.12 06:42:54 199.400 -3.57 0.00 -9.02 -312.70
[sl]
97375741 2025.09.29 04:24:10 sell 0.31 xauusd.pro 3772.68 3787.70 0.00 2025.09.29 05:15:19 3787.73 -1.40 0.00 0.00 -466.55
[sl]
97439025 2025.09.30 20:34:30 sell 0.20 eurusd.pro 1.17554 1.17560 0.00000 2025.10.09 18:50:39 1.15547 -0.90 0.00 12.16 401.40
to #97701545
97701545 2025.09.30 20:34:30 sell 1.01 eurusd.pro 1.17554 1.17560 0.00000 2025.10.17 08:52:26 1.17239 -4.55 0.00 106.14 318.15
so: -7.7%/-9.2/118.7
97777046 2025.10.16 01:44:49 sell 1.31 eurusd.pro 1.16500 1.17220 1.15000 2025.10.17 08:52:26 1.17231 -5.90 0.00 7.24 -957.61
so: 7.5%/20.3/271.3
97963441 2025.10.14 20:15:33 sell 0.51 eurusd.pro 1.16048 1.16560 0.00000 2025.10.15 10:51:04 1.16387 -2.30 0.00 2.82 -172.89
to #97981120
97981120 2025.10.14 20:15:33 sell 1.50 eurusd.pro 1.16048 1.16560 0.00000 2025.10.16 03:27:05 1.16559 -6.75 0.00 33.19 -766.50
from #97963441[sl]
96483049 2025.08.11 11:49:06 balance Transfer from 4690858 N1268184 400.00
96824414 2025.08.30 18:16:03 balance Data Truncation 28022025 26.92
98101416 2025.10.20 08:29:52 balance NBA 20.26
-50.01 0.00 -47.52 -975.53
Closed P/L: -1 073.06
Open Trades:
Ticket Open Time Type Volume Item Price S / L T / P Price Commission Taxes Swap Profit
No transactions
0.00 0.00 0.00 0.00
Floating P/L: 0.00
Working Orders:
Ticket Open Time Type Volume Item Price S / L T / P Market Price
No transactions
Summary:
7/21/26, 11:02 PM Statement: 4698524 - Andre Gierhold
file:///C:/Users/Lissa.Mattos/Downloads/Statement_4698524.htm 1/2
Deposit/Withdrawal: 447.18 Credit Facility: 0.00
Closed Trade P/L: -1 073.06 Floating P/L: 0.00 Margin: 0.00
Balance: 0.34 Equity: 0.34 Free Margin: 0.34
7/21/26, 11:02 PM Statement: 4698524 - Andre Gierhold
file:///C:/Users/Lissa.Mattos/Downloads/Statement_4698524.htm 2/2
"""

# Sonderfaelle aus 6059496/4667999: umgebrochener Betrag, Tausender mit
# Leerzeichen, Seitenumbruch mitten im Datensatz, Summenzeile umgebrochen.
EDGE = """Account: 6059496 Name: Andre Gierhold Currency: USD
Closed Transactions:
90439550 2025.06.24 03:01:15 buy 0.25 xauusd.pro 3340.00 3300.00 0.00 2025.06.24 16:39:53 3300.00 -1.75 0.00 0.00
-1
000.00
[sl]
94828051 2025.05.20 11:28:44 buy 0.49 xauusd.pro 3220.91 3220.00 3252.00 2025.05.20 15:37:17 3246.28 -3.43 0.00 0.00 1 243.13
7/21/26, 11:03 PM Statement: 4667999 - Andre Gierhold
file:///C:/Users/Lissa.Mattos/Downloads/Statement_4667999.htm 1/15
from #94827793
90202157 2025.06.07 23:54:16 balance Data Truncation 31122024 4 315.37
90653370 2025.07.02 22:41:01 balance Transfer to 4698524 N1214522
-1
000.00
-5.18 0.00
0.00
243.13
Closed P/L: 237.95
Deposit/Withdrawal: 3 315.37
"""

# USDJPY-Short 02.04.2025 (4667999): eine Position in 8 Tickets.
CHAIN = """Account: 4667999
Closed Transactions:
93482688 2025.04.02 23:15:02 sell 0.75 usdjpy.pro 150.319 150.500 0.000 2025.04.03 01:02:46 148.526 -5.25 0.00 -30.90 905.40
to #93499939
93499939 2025.04.02 23:15:02 sell 0.35 usdjpy.pro 150.319 150.500 0.000 2025.04.03 12:21:21 146.590 -2.45 0.00 -14.42 890.34
to #93542099
93542099 2025.04.02 23:15:02 sell 0.11 usdjpy.pro 150.319 150.500 0.000 2025.04.03 12:40:27 146.552 -0.77 0.00 -4.53 282.75
to #93542913
93542913 2025.04.02 23:15:02 sell 0.11 usdjpy.pro 150.319 150.500 0.000 2025.04.04 14:15:43 144.735 -0.77 0.00 -6.08 424.39
to #93598621
93598621 2025.04.02 23:15:02 sell 0.10 usdjpy.pro 150.319 149.250 0.000 2025.04.09 22:33:17 147.908 -0.70 0.00 -9.70 163.01
to #93775363
93775363 2025.04.02 23:15:02 sell 0.04 usdjpy.pro 150.319 149.250 0.000 2025.04.10 19:09:44 144.340 -0.28 0.00 -5.55 165.69
to #93815090
93815090 2025.04.02 23:15:02 sell 0.03 usdjpy.pro 150.319 149.250 0.000 2025.04.11 05:13:13 143.345 -0.21 0.00 -4.58 145.96
to #93831332
93831332 2025.04.02 23:15:02 sell 0.02 usdjpy.pro 150.319 149.250 140.000 2025.04.22 08:26:41 140.000 -0.14 0.00 -5.67 147.41
from #93815090[tp]
93601959 2025.04.04 15:00:56 sell 1.01 eurusd.pro 1.10540 1.10705 0.00000 2025.04.04 15:19:14 1.10705 -7.07 0.00 0.00 -166.65
[sl]
-17.64 0.00 -81.43 2 958.30
Closed P/L: 2 859.23
Deposit/Withdrawal: 0.00
"""


def test_money():
    assert money("1 243.13") == 1243.13
    assert money("-1\n000.00") == -1000.0
    assert money("-0.22") == -0.22


def test_full_statement_matches_footer():
    st = parse_text(FULL_4698524)
    st.verify()
    assert st.account == "4698524"
    assert len(st.trades) == 20
    assert len(st.balances) == 3
    assert st.trades.loc[st.trades.ticket == 97701545, "exit_tag"].isna().all()
    assert st.trades.loc[st.trades.ticket == 97981120, "exit_tag"].item() == "sl"
    assert st.totals["closed_pl"] == pytest.approx(-1073.06)


def test_edge_cases_and_truncation_date():
    st = parse_text(EDGE)
    st.verify()
    assert st.trades.set_index("ticket").loc[90439550, "profit"] == -1000.0
    assert st.trades.set_index("ticket").loc[94828051, "profit"] == 1243.13
    assert st.trades.set_index("ticket").loc[94828051, "from_ticket"] == 94827793
    trunc = st.balances.set_index("ticket").loc[90202157]
    assert trunc["amount"] == 4315.37
    assert trunc["effective_time"] == pd.Timestamp("2024-12-31 23:59:59")


def test_partial_close_chain_is_one_position():
    st = parse_text(CHAIN)
    st.verify()
    pos = positions(st.trades)
    assert len(pos) == 2
    jpy = pos[pos.symbol == "usdjpy.pro"].iloc[0]
    assert jpy.n_tickets == 8
    assert jpy.gross == pytest.approx(3124.95)
    assert jpy.net == pytest.approx(3124.95 - 10.57 - 81.43)
    assert jpy.last_exit_tag == "tp"
    assert pos.net.sum() == pytest.approx(st.totals["closed_pl"])


def test_equity_uses_truncation_as_opening_balance():
    st = parse_text(EDGE)
    eq = equity_at(st)
    pos = positions(st.trades)
    # 20.05.: nur der Startsaldo 4.315,37 (Truncation per 31.12.2024)
    i = pos.index[pos.open_time == pd.Timestamp("2025-05-20 11:28:44")][0]
    assert eq[i] == pytest.approx(4315.37)


def test_unreadable_record_raises():
    bad = CHAIN.replace("sell 1.01 eurusd.pro 1.10540", "sell 1.01 eurusd.pro ???")
    with pytest.raises(ValueError, match="nicht lesbar"):
        parse_text(bad)
