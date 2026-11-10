import pandas as pd

from fusion_lab.macro_data import calendar, sources, store


def _frame(values):
    return pd.DataFrame([{"key": "US.2y", "date": d, "value": v} for d, v in values])


def test_append_keeps_revision_and_as_of(tmp_path):
    t1, t2 = pd.Timestamp("2026-10-01"), pd.Timestamp("2026-10-02")
    assert store.append("macro", _frame([("2026-09-01", 4.0)]), t1, tmp_path) == 1
    assert store.append("macro", _frame([("2026-09-01", 4.0)]), t2, tmp_path) == 0
    assert store.append("macro", _frame([("2026-09-01", 4.2)]), t2, tmp_path) == 1
    assert store.latest("macro", data_dir=tmp_path)["value"].tolist() == [4.2]
    assert store.latest("macro", as_of=t1, data_dir=tmp_path)["value"].tolist() == [4.0]


def test_parse_number():
    assert calendar.parse_number("0.6%") == (0.6, "%")
    assert calendar.parse_number("-52.5K") == (-52500.0, "K")
    assert calendar.parse_number("") == (None, "")
    assert calendar.parse_number("n/a") == (None, "")


def test_parse_ff_converts_to_utc():
    df = calendar.parse_ff([{"title": "CPI", "country": "USD", "date": "2026-10-26T05:00:00-04:00",
                             "impact": "High", "forecast": "0.3%", "previous": "0.2%"}])
    assert df["event_time"].iloc[0] == pd.Timestamp("2026-10-26 09:00")
    assert df["actual"].iloc[0] == ""


RSS = """<item><title>Australia Private Sector Credit MoM</title>
<pubDate>Fri, 30 Oct 2026 00:30 GMT</pubDate><description>&#60;table&#62;&#60;tr&#62;&#60;td&#62;-35415 seconds&#60;/td&#62;
&#60;td&#62;&#60;span class=&#34;sprite sprite-common sprite-low-impact&#34;&#62;&#60;/span&#62;&#60;/td&#62;
&#60;td&#62; 0.6% &#60;/td&#62;&#60;td&#62; 0.5% &#60;/td&#62;&#60;td&#62; 0.7% &#60;/td&#62;&#60;/tr&#62;&#60;/table&#62;</description></item>
<item><title>Brazil Unemployment Rate</title><pubDate>Fri, 30 Oct 2026 12:00 GMT</pubDate>
<description>&#60;td&#62;x&#60;/td&#62;</description></item>"""


def test_parse_myfxbook_only_g8_and_column_order():
    df = calendar.parse_myfxbook(RSS)
    assert len(df) == 1
    row = df.iloc[0]
    assert (row["currency"], row["title"]) == ("AUD", "Private Sector Credit MoM")
    assert (row["previous"], row["forecast"], row["actual"], row["impact"]) == ("0.6%", "0.5%", "0.7%", "Low")
    assert row["event_time"] == pd.Timestamp("2026-10-30 00:30")


def test_euro_members_do_not_collide_with_euro_area():
    item = ("<item><title>{} Inflation Rate YoY</title><pubDate>Fri, 30 Oct 2026 10:00 GMT</pubDate>"
            "<description>&#60;td&#62;x&#60;/td&#62;&#60;td&#62;y&#60;/td&#62;&#60;td&#62;1%&#60;/td&#62;"
            "&#60;td&#62;2%&#60;/td&#62;&#60;td&#62;3%&#60;/td&#62;</description></item>")
    df = calendar.parse_myfxbook(item.format("Euro Area") + item.format("Italy"))
    assert df["title"].tolist() == ["Inflation Rate YoY", "Italy: Inflation Rate YoY"]
    assert df["currency"].tolist() == ["EUR", "EUR"]


def test_parse_eurostat_maps_position_to_period():
    payload = {"dimension": {"time": {"category": {"index": {"2026-08": 0, "2026-09": 1}}}}, "value": {"1": 6.5}}
    out = sources.parse_eurostat(payload, "EA.unemployment")
    assert out["date"].tolist() == [pd.Timestamp("2026-09-01")]
    assert out["value"].tolist() == [6.5]


def _event(forecast, actual):
    return pd.DataFrame([{"source": "myfxbook", "currency": "USD", "title": "CPI",
                          "event_time": pd.Timestamp("2026-10-30 12:30"), "impact": "High",
                          "forecast": forecast, "previous": "0.2%", "actual": actual}])


def test_surprise_uses_consensus_from_before_the_print(tmp_path):
    calendar.append_events(_event("0.3%", ""), pd.Timestamp("2026-10-30 06:00"), tmp_path)
    calendar.append_events(_event("0.5%", "0.4%"), pd.Timestamp("2026-10-30 22:00"), tmp_path)
    assert calendar.append_events(_event("0.5%", "0.4%"), pd.Timestamp("2026-10-30 23:00"), tmp_path) == 0
    out = calendar.surprises(pd.read_parquet(tmp_path / "calendar.parquet"))
    assert out["forecast"].iloc[0] == 0.3
    assert round(out["surprise"].iloc[0], 6) == 0.1
    assert bool(out["forecast_before_print"].iloc[0]) is True


def test_surprise_skips_mixed_units_and_open_events(tmp_path):
    calendar.append_events(_event("0.3%", "150K"), pd.Timestamp("2026-10-30 06:00"), tmp_path)
    assert calendar.surprises(pd.read_parquet(tmp_path / "calendar.parquet")).empty
    assert calendar.surprises(_event("0.3%", "").assign(fetched_at=pd.Timestamp("2026-10-30"))).empty


def test_cftc_date_is_publication_not_report():
    rows = pd.DataFrame([{"cftc_contract_market_code": "099741", "report_date_as_yyyy_mm_dd": "2026-10-20T00:00:00.000",
                          "open_interest_all": "100", "lev_long": "30", "lev_short": "50"}])
    out = sources.cftc_long(rows, {"099741": "EUR"}, {"lev": ("lev_long", "lev_short")})
    net = out[out["key"] == "EUR.lev_net"].iloc[0]
    assert net["value"] == -20
    assert net["date"] == pd.Timestamp("2026-10-23")


def test_cot_index_bounds_and_warmup():
    idx = sources.cot_index(pd.Series([0.0, 10.0, 5.0, 20.0]), 3)
    assert idx.isna().tolist() == [True, True, False, False]
    assert idx.iloc[2] == 50
    assert idx.iloc[3] == 100


def test_fed_contracts_rolls_over_year():
    c = sources.fed_contracts(pd.Timestamp("2026-11-15"), months=3)
    assert c == {"2026-11": "ZQX26.CBT", "2026-12": "ZQZ26.CBT", "2027-01": "ZQF27.CBT"}


def test_period_start_handles_all_frequencies():
    out = sources.period_start(pd.Series(["2026-09", "2026-Q3", "2026-09-14"]))
    assert out.tolist() == [pd.Timestamp("2026-09-01"), pd.Timestamp("2026-07-01"), pd.Timestamp("2026-09-14")]


def test_parse_mof_skips_title_and_dashes():
    text = ("Interest Rate,,,,(Unit : %)\nDate,1Y,2Y,3Y,10Y\n"
            "1974/9/24,10.3,9.36,8.83,-\n2026/11/5,1.658,1.86,1.953,2.806\n")
    df = sources.parse_mof(text)
    assert df[df["key"] == "JP.2y"]["value"].tolist() == [9.36, 1.86]
    assert df[df["key"] == "JP.10y"]["date"].tolist() == [pd.Timestamp("2026-11-05")]


def test_parse_boc_reads_after_observations():
    text = ('"TERMS AND CONDITIONS"\n"x"\n\n"SERIES"\n"id","label"\n\n"OBSERVATIONS"\n'
            '"date","BD.CDN.10YR.DQ.YLD","BD.CDN.2YR.DQ.YLD"\n"2026-11-06","3.65","3.12"\n')
    df = sources.parse_boc(text).set_index("key")
    assert df.loc["CA.2y", "value"] == 3.12 and df.loc["CA.10y", "value"] == 3.65


def test_parse_snb_only_chf_tenors():
    text = ('"CubeId";"rendeiduebd"\n"PublishingDate";"2026-11-02 14:30"\n\n"Date";"D0";"D1";"Value"\n'
            '"2026-10-30";"CHF";"2J";"0.238"\n"2026-10-30";"EUR";"2J";"2.1"\n"2026-10-30";"CHF";"10J";"0.505"\n')
    df = sources.parse_snb(text).set_index("key")
    assert df.loc["CH.2y", "value"] == 0.238 and df.loc["CH.10y", "value"] == 0.505


def test_tvc_session_date_moves_evening_bars_forward():
    idx = pd.DatetimeIndex(["2026-11-09 23:00", "2026-11-09 08:00", "2026-11-09 12:00"])
    assert list(sources.tvc_session_date(idx).day) == [10, 9, 9]
