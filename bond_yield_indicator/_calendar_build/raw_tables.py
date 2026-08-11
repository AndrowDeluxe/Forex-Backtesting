"""Raw appendix table text transcribed from Yildirim (2024/2025), SSRN 6353258,
Appendix B, Tables 4-9. Parsed programmatically by parse_calendars.py rather
than hand-typed date-by-date, to avoid transcription errors on ~1500 dates.
Row format per year: 'YYYY N D-Mon D-Mon ...' (N = declared meeting count for
that year, used only as a cross-check against how many dates actually parse)."""

ECB_TABLE4 = """
1999 20 4-Mar 18-Mar 8-Apr 22-Apr 6-May 20-May 2-Jun 17-Jun 1-Jul 15-Jul 29-Jul 26-Aug 9-Sep 23-Sep 7-Oct 21-Oct 4-Nov 18-Nov 2-Dec 15-Dec
2000 24 5-Jan 20-Jan 3-Feb 17-Feb 2-Mar 16-Mar 30-Mar 13-Apr 27-Apr 11-May 25-May 8-Jun 21-Jun 6-Jul 20-Jul 3-Aug 31-Aug 14-Sep 5-Oct 19-Oct 2-Nov 16-Nov 30-Nov
2001 24 4-Jan 18-Jan 1-Feb 15-Feb 1-Mar 15-Mar 29-Mar 11-Apr 26-Apr 10-May 23-May 7-Jun 21-Jun 5-Jul 19-Jul 2-Aug 30-Aug 13-Sep 17-Sep 11-Oct 25-Oct 8-Nov 6-Dec
2002 12 3-Jan 7-Feb 7-Mar 4-Apr 2-May 6-Jun 4-Jul 1-Aug 12-Sep 10-Oct 7-Nov 5-Dec
2003 12 9-Jan 6-Feb 6-Mar 3-Apr 8-May 5-Jun 10-Jul 31-Jul 4-Sep 2-Oct 6-Nov 4-Dec
2004 12 8-Jan 5-Feb 4-Mar 1-Apr 6-May 3-Jun 1-Jul 5-Aug 2-Sep 7-Oct 4-Nov 2-Dec
2005 12 13-Jan 3-Feb 3-Mar 7-Apr 4-May 2-Jun 7-Jul 4-Aug 1-Sep 6-Oct 3-Nov 1-Dec
2006 12 12-Jan 2-Feb 2-Mar 6-Apr 4-May 8-Jun 6-Jul 3-Aug 31-Aug 5-Oct 2-Nov 7-Dec
2007 12 11-Jan 8-Feb 8-Mar 12-Apr 10-May 6-Jun 5-Jul 2-Aug 6-Sep 4-Oct 8-Nov 6-Dec
2008 13 10-Jan 7-Feb 6-Mar 10-Apr 8-May 5-Jun 3-Jul 7-Aug 4-Sep 2-Oct 8-Oct 6-Nov 4-Dec
2009 12 15-Jan 5-Feb 5-Mar 2-Apr 7-May 4-Jun 2-Jul 6-Aug 3-Sep 8-Oct 5-Nov 3-Dec
2010 12 14-Jan 4-Feb 4-Mar 8-Apr 6-May 10-Jun 8-Jul 5-Aug 2-Sep 7-Oct 4-Nov 2-Dec
2011 12 13-Jan 3-Feb 3-Mar 7-Apr 5-May 9-Jun 7-Jul 4-Aug 8-Sep 6-Oct 3-Nov 8-Dec
2012 12 12-Jan 9-Feb 8-Mar 4-Apr 3-May 6-Jun 5-Jul 2-Aug 6-Sep 4-Oct 8-Nov 6-Dec
2013 12 10-Jan 7-Feb 7-Mar 4-Apr 2-May 6-Jun 4-Jul 1-Aug 5-Sep 2-Oct 7-Nov 5-Dec
2014 12 9-Jan 6-Feb 6-Mar 3-Apr 8-May 5-Jun 3-Jul 7-Aug 4-Sep 2-Oct 6-Nov 4-Dec
2015 8 22-Jan 5-Mar 15-Apr 3-Jun 16-Jul 3-Sep 22-Oct 3-Dec
2016 8 21-Jan 10-Mar 21-Apr 2-Jun 21-Jul 8-Sep 20-Oct 8-Dec
2017 8 19-Jan 9-Mar 27-Apr 8-Jun 20-Jul 7-Sep 26-Oct 14-Dec
2018 8 25-Jan 8-Mar 26-Apr 14-Jun 26-Jul 13-Sep 25-Oct 13-Dec
2019 8 24-Jan 7-Mar 10-Apr 6-Jun 25-Jul 12-Sep 24-Oct 12-Dec
2020 8 23-Jan 12-Mar 30-Apr 4-Jun 16-Jul 10-Sep 29-Oct 10-Dec
2021 8 21-Jan 11-Mar 22-Apr 10-Jun 22-Jul 9-Sep 28-Oct 16-Dec
2022 8 3-Feb 10-Mar 14-Apr 9-Jun 21-Jul 8-Sep 27-Oct 15-Dec
2023 8 2-Feb 16-Mar 4-May 15-Jun 27-Jul 14-Sep 26-Oct 14-Dec
2024 2 25-Jan 7-Mar
"""

BOE_TABLE5 = """
1997 7 6-Jun 10-Jul 7-Aug 11-Sep 9-Oct 6-Nov 4-Dec
1998 12 8-Jan 5-Feb 5-Mar 9-Apr 7-May 4-Jun 9-Jul 6-Aug 10-Sep 8-Oct 5-Nov 10-Dec
1999 12 7-Jan 4-Feb 3-Mar 8-Apr 6-May 10-Jun 8-Jul 5-Aug 8-Sep 7-Oct 4-Nov 9-Dec
2000 12 13-Jan 10-Feb 9-Mar 6-Apr 4-May 7-Jun 6-Jul 3-Aug 7-Sep 5-Oct 9-Nov 7-Dec
2001 13 11-Jan 8-Feb 8-Mar 5-Apr 10-May 6-Jun 5-Jul 2-Aug 6-Sep 18-Sep 4-Oct 8-Nov 5-Dec
2002 12 10-Jan 7-Feb 7-Mar 4-Apr 9-May 6-Jun 4-Jul 1-Aug 5-Sep 10-Oct 7-Nov 5-Dec
2003 12 9-Jan 6-Feb 6-Mar 10-Apr 8-May 5-Jun 10-Jul 7-Aug 4-Sep 9-Oct 6-Nov 4-Dec
2004 12 8-Jan 5-Feb 4-Mar 8-Apr 6-May 10-Jun 8-Jul 5-Aug 9-Sep 7-Oct 4-Nov 9-Dec
2005 12 13-Jan 10-Feb 10-Mar 7-Apr 9-May 9-Jun 7-Jul 4-Aug 8-Sep 6-Oct 10-Nov 8-Dec
2006 12 12-Jan 9-Feb 9-Mar 6-Apr 4-May 8-Jun 6-Jul 3-Aug 7-Sep 5-Oct 9-Nov 7-Dec
2007 12 11-Jan 8-Feb 8-Mar 5-Apr 10-May 7-Jun 5-Jul 2-Aug 6-Sep 4-Oct 8-Nov 6-Dec
2008 12 10-Jan 7-Feb 6-Mar 10-Apr 8-May 5-Jun 10-Jul 7-Aug 4-Sep 8-Oct 6-Nov 4-Dec
2009 12 8-Jan 5-Feb 5-Mar 9-Apr 7-May 4-Jun 9-Jul 6-Aug 10-Sep 8-Oct 5-Nov 10-Dec
2010 12 7-Jan 4-Feb 4-Mar 8-Apr 10-May 10-Jun 8-Jul 5-Aug 9-Sep 7-Oct 4-Nov 9-Dec
2011 12 13-Jan 10-Feb 10-Mar 7-Apr 5-May 9-Jun 7-Jul 4-Aug 8-Sep 6-Oct 10-Nov 8-Dec
2012 12 12-Jan 9-Feb 8-Mar 5-Apr 10-May 7-Jun 5-Jul 2-Aug 6-Sep 4-Oct 8-Nov 6-Dec
2013 12 10-Jan 7-Feb 7-Mar 4-Apr 9-May 6-Jun 4-Jul 1-Aug 5-Sep 9-Oct 7-Nov 5-Dec
2014 12 9-Jan 6-Feb 6-Mar 9-Apr 8-May 5-Jun 10-Jul 7-Aug 4-Sep 8-Oct 6-Nov 4-Dec
2015 12 8-Jan 5-Feb 5-Mar 9-Apr 8-May 3-Jun 8-Jul 6-Aug 10-Sep 8-Oct 5-Nov 10-Dec
2016 11 14-Jan 4-Feb 17-Mar 14-Apr 12-May 16-Jun 14-Jul 4-Aug 15-Sep 3-Nov 15-Dec
2017 8 2-Feb 16-Mar 11-May 15-Jun 3-Aug 14-Sep 2-Nov 14-Dec
2018 8 8-Feb 22-Mar 10-May 21-Jun 2-Aug 13-Sep 1-Nov 20-Dec
2019 8 7-Feb 21-Mar 2-May 20-Jun 1-Aug 19-Sep 7-Nov 19-Dec
2020 10 30-Jan 11-Mar 19-Mar 26-Mar 7-May 18-Jun 6-Aug 17-Sep 5-Nov 17-Dec
2021 8 4-Feb 18-Mar 6-May 24-Jun 5-Aug 23-Sep 4-Nov 16-Dec
2022 8 3-Feb 17-Mar 5-May 16-Jun 4-Aug 22-Sep 3-Nov 15-Dec
2023 8 2-Feb 23-Mar 11-May 22-Jun 3-Aug 21-Sep 2-Nov 14-Dec
2024 2 1-Feb 21-Mar
"""

BOJ_TABLE6 = """
1997 12 3-Jan 7-Feb 7-Mar 4-Apr 2-May 6-Jun 4-Jul 1-Aug 5-Sep 3-Oct 7-Nov 5-Dec
1998 12 2-Jan 6-Feb 6-Mar 3-Apr 1-May 5-Jun 3-Jul 7-Aug 4-Sep 9-Sep 2-Oct 6-Nov 4-Dec
1999 14 1-Jan 5-Feb 12-Feb 25-Feb 5-Mar 2-Apr 7-May 4-Jun 2-Jul 6-Aug 3-Sep 1-Oct 5-Nov 3-Dec
2000 13 7-Jan 4-Feb 3-Mar 7-Apr 5-May 2-Jun 7-Jul 4-Aug 11-Aug 1-Sep 6-Oct 3-Nov 1-Dec
2001 13 5-Jan 2-Feb 28-Feb 2-Mar 30-Apr 31-May 29-Jun 31-Jul 31-Aug 28-Sep 31-Oct 30-Nov 31-Dec
2002 12 31-Jan 28-Feb 29-Mar 30-Apr 31-May 28-Jun 31-Jul 30-Aug 30-Sep 31-Oct 29-Nov 31-Dec
2003 12 31-Jan 28-Feb 31-Mar 30-Apr 30-May 30-Jun 31-Jul 29-Aug 30-Sep 31-Oct 28-Nov 31-Dec
2004 12 30-Jan 27-Feb 31-Mar 30-Apr 31-May 30-Jun 30-Jul 31-Aug 30-Sep 29-Oct 30-Nov 31-Dec
2005 12 31-Jan 28-Feb 31-Mar 29-Apr 31-May 30-Jun 29-Jul 31-Aug 30-Sep 31-Oct 30-Nov 30-Dec
2006 13 31-Jan 28-Feb 9-Mar 3-Apr 1-May 1-Jun 3-Jul 14-Jul 1-Aug 1-Sep 2-Oct 1-Nov 1-Dec
2007 13 4-Jan 1-Feb 21-Feb 1-Mar 2-Apr 1-May 1-Jun 2-Jul 1-Aug 3-Sep 1-Oct 1-Nov 3-Dec
2008 14 4-Jan 1-Feb 3-Mar 1-Apr 1-May 2-Jun 1-Jul 1-Aug 1-Sep 1-Oct 31-Oct 4-Nov 1-Dec 19-Dec
2009 12 5-Jan 2-Feb 2-Mar 1-Apr 1-May 1-Jun 1-Jul 3-Aug 1-Sep 1-Oct 2-Nov 1-Dec
2010 12 4-Jan 1-Feb 1-Mar 1-Apr 6-May 1-Jun 1-Jul 2-Aug 30-Sep 5-Oct 5-Nov 21-Dec
2011 13 25-Jan 15-Feb 31-Mar 7-Apr 28-Apr 20-May 14-Jun 31-Jul 31-Aug 8-Sep 31-Oct 16-Nov 21-Dec
2012 13 24-Jan 14-Feb 13-Mar 10-Apr 23-May 15-Jun 12-Jul 9-Aug 19-Sep 5-Oct 30-Oct 20-Nov 20-Dec
2013 15 22-Jan 14-Feb 7-Mar 4-Apr 26-Apr 21-May 22-May 11-Jun 11-Jul 8-Aug 5-Sep 4-Oct 31-Oct 21-Nov 20-Dec
2014 17 22-Jan 27-Jan 18-Feb 21-Feb 11-Mar 20-Mar 8-Apr 30-Apr 21-May 13-Jun 15-Jul 8-Aug 4-Sep 7-Oct 31-Oct 19-Nov 19-Dec
2015 16 21-Jan 26-Jan 18-Feb 23-Feb 17-Mar 8-Apr 30-Apr 22-May 19-Jun 15-Jul 7-Aug 15-Sep 7-Oct 30-Oct 19-Nov 18-Dec
2016 9 29-Jan 3-Feb 15-Mar 28-Apr 16-Jun 29-Jul 21-Sep 1-Nov 20-Dec
2017 8 31-Jan 16-Mar 27-Apr 16-Jun 20-Jul 21-Sep 31-Oct 21-Dec
2018 8 23-Jan 9-Mar 27-Apr 15-Jun 31-Jul 19-Sep 31-Oct 20-Dec
2019 8 23-Jan 15-Mar 25-Apr 20-Jun 30-Jul 19-Sep 31-Oct 19-Dec
2020 9 21-Jan 16-Mar 27-Apr 22-May 16-Jun 15-Jul 17-Sep 29-Oct 18-Dec
2021 6 21-Jan 19-Mar 27-Apr 18-Jun 16-Jul 22-Sep 28-Oct 17-Dec
2022 6 18-Jan 18-Mar 28-Apr 17-Jun 21-Jul 22-Sep 28-Oct 20-Dec
2023 8 18-Jan 10-Mar 28-Apr 16-Jun 28-Jul 22-Sep 31-Oct 19-Dec
2024 2 23-Jan 19-Mar
"""

BOC_TABLE7 = """
1999 4 4-Jan 31-Mar 4-May 17-Nov
2000 3 3-Feb 22-Mar 17-May
2001 9 23-Jan 6-Mar 17-Apr 29-May 17-Jul 28-Aug 17-Sep 23-Oct 27-Nov
2002 4 15-Jan 16-Apr 4-Jun 16-Jul
2003 4 4-Mar 15-Apr 15-Jul 3-Sep
2004 5 20-Jan 2-Mar 13-Apr 8-Sep 19-Oct
2005 3 7-Sep 18-Oct 6-Dec
2006 4 24-Jan 7-Mar 25-Apr 24-May
2007 5 29-May 10-Jul 5-Sep 16-Oct 4-Dec
2008 9 22-Jan 4-Mar 22-Apr 10-Jun 15-Jul 3-Sep 8-Oct 21-Oct 9-Dec
2009 8 20-Jan 3-Mar 21-Apr 4-Jun 21-Jul 10-Sep 20-Oct 8-Dec
2010 8 19-Jan 2-Mar 20-Apr 1-Jun 20-Jul 8-Sep 19-Oct 7-Dec
2011 8 18-Jan 1-Mar 12-Apr 31-May 19-Jul 7-Sep 25-Oct 6-Dec
2012 8 17-Jan 8-Mar 17-Apr 5-Jun 17-Jul 5-Sep 23-Oct 4-Dec
2013 8 23-Jan 6-Mar 17-Apr 29-May 17-Jul 4-Sep 23-Oct 4-Dec
2014 8 22-Jan 5-Mar 16-Apr 4-Jun 16-Jul 3-Sep 22-Oct 3-Dec
2015 8 21-Jan 4-Mar 15-Apr 27-May 15-Jul 9-Sep 21-Oct 2-Dec
2016 8 20-Jan 9-Mar 13-Apr 25-May 13-Jul 7-Sep 19-Oct 7-Dec
2017 8 18-Jan 1-Mar 12-Apr 24-May 12-Jul 6-Sep 25-Oct 6-Dec
2018 8 17-Jan 7-Mar 18-Apr 30-May 11-Jul 5-Sep 24-Oct 5-Dec
2019 8 9-Jan 6-Mar 24-Apr 29-May 10-Jul 4-Sep 30-Oct 4-Dec
2020 10 22-Jan 4-Mar 13-Mar 27-Mar 15-Apr 3-Jun 15-Jul 9-Sep 28-Oct 9-Dec
2021 8 20-Jan 10-Mar 21-Apr 9-Jun 14-Jul 8-Sep 27-Oct 8-Dec
2022 8 26-Jan 2-Mar 13-Apr 1-Jun 13-Jul 7-Sep 26-Oct 7-Dec
2023 8 25-Jan 8-Mar 12-Apr 7-Jun 12-Jul 6-Sep 25-Oct 6-Dec
2024 3 24-Jan 6-Mar 10-Apr
"""

SNB_TABLE8 = """
2000 5 20-Jan 3-Feb 23-Mar 15-Jun 14-Sep 8-Dec
2001 5 22-Mar 14-Jun 17-Sep 24-Sep 7-Dec
2002 6 21-Mar 2-May 4-Jun 26-Jun 19-Sep 13-Dec
2003 4 20-Mar 13-Jun 18-Sep 12-Dec
2004 4 18-Mar 17-Jun 16-Sep 16-Dec
2005 4 17-Mar 16-Jun 15-Sep 15-Dec
2006 4 16-Mar 15-Jun 14-Sep 14-Dec
2007 4 15-Mar 14-Jun 13-Sep 13-Dec
2008 6 13-Mar 19-Jun 18-Sep 8-Oct 6-Nov 20-Nov 11-Dec
2009 4 12-Mar 18-Jun 17-Sep 10-Dec
2010 4 11-Mar 17-Jun 16-Sep 16-Dec
2011 7 17-Mar 16-Jun 3-Aug 10-Aug 17-Aug 15-Sep 15-Dec
2012 4 15-Mar 14-Jun 13-Sep 13-Dec
2013 4 14-Mar 20-Jun 19-Sep 12-Dec
2014 4 20-Mar 19-Jun 18-Sep 11-Dec
2015 5 15-Jan 19-Mar 18-Jun 17-Sep 10-Dec
2016 4 17-Mar 16-Jun 15-Sep 15-Dec
2017 4 16-Mar 15-Jun 14-Sep 14-Dec
2018 4 15-Mar 21-Jun 20-Sep 13-Dec
2019 4 21-Mar 13-Jun 19-Sep 19-Dec
2020 4 19-Mar 18-Jun 24-Sep 17-Dec
2021 4 25-Mar 17-Jun 23-Sep 16-Dec
2022 4 24-Mar 16-Jun 22-Sep 15-Dec
2023 4 23-Mar 22-Jun 21-Sep 14-Dec
2024 1 21-Mar
"""

RBA_TABLE9 = """
2000 4 2-Feb 5-Apr 3-May 2-Aug
2001 6 7-Feb 7-Mar 4-Apr 5-Sep 3-Oct 5-Dec
2002 2 8-May 5-Jun
2003 2 5-Nov 3-Dec
2005 1 2-Mar
2006 3 3-May 2-Aug 8-Nov
2007 3 8-Aug 7-Nov 5-Dec
2008 11 5-Feb 4-Mar 1-Apr 6-May 3-Jun 1-Jul 5-Aug 2-Sep 7-Oct 4-Nov 2-Dec
2009 11 3-Feb 3-Mar 7-Apr 5-May 2-Jun 7-Jul 4-Aug 1-Sep 6-Oct 3-Nov 1-Dec
2010 11 2-Feb 2-Mar 6-Apr 4-May 1-Jun 6-Jul 3-Aug 7-Sep 5-Oct 2-Nov 7-Dec
2011 11 1-Feb 1-Mar 5-Apr 3-May 7-Jun 5-Jul 2-Aug 6-Sep 4-Oct 1-Nov 6-Dec
2012 11 7-Feb 6-Mar 3-Apr 1-May 5-Jun 3-Jul 7-Aug 4-Sep 2-Oct 6-Nov 4-Dec
2013 11 5-Feb 5-Mar 2-Apr 7-May 4-Jun 2-Jul 6-Aug 3-Sep 1-Oct 5-Nov 3-Dec
2014 11 4-Feb 4-Mar 1-Apr 6-May 3-Jun 1-Jul 5-Aug 2-Sep 7-Oct 4-Nov 2-Dec
2015 11 3-Feb 3-Mar 7-Apr 5-May 2-Jun 7-Jul 4-Aug 1-Sep 6-Oct 3-Nov 1-Dec
2016 11 2-Feb 1-Mar 5-Apr 3-May 7-Jun 5-Jul 2-Aug 6-Sep 4-Oct 1-Nov 6-Dec
2017 11 7-Feb 7-Mar 4-Apr 2-May 6-Jun 4-Jul 1-Aug 5-Sep 3-Oct 7-Nov 5-Dec
2018 11 6-Feb 6-Mar 3-Apr 1-May 5-Jun 3-Jul 7-Aug 4-Sep 2-Oct 6-Nov 4-Dec
2019 11 5-Feb 5-Mar 2-Apr 7-May 4-Jun 2-Jul 6-Aug 3-Sep 1-Oct 5-Nov 3-Dec
2020 12 4-Feb 3-Mar 19-Mar 7-Apr 5-May 2-Jun 7-Jul 4-Aug 1-Sep 6-Oct 3-Nov 1-Dec
2021 11 2-Feb 2-Mar 6-Apr 4-May 1-Jun 6-Jul 3-Aug 7-Sep 5-Oct 2-Nov 7-Dec
2022 11 1-Feb 1-Mar 5-Apr 3-May 7-Jun 5-Jul 2-Aug 6-Sep 4-Oct 1-Nov 6-Dec
2023 11 7-Feb 7-Mar 4-Apr 2-May 6-Jun 4-Jul 1-Aug 5-Sep 3-Oct 7-Nov 5-Dec
2024 2 6-Feb 19-Mar
"""

TABLES = {
    "ECB": ECB_TABLE4,
    "BOE": BOE_TABLE5,
    "BOJ": BOJ_TABLE6,
    "BOC": BOC_TABLE7,
    "SNB": SNB_TABLE8,
    "RBA": RBA_TABLE9,
}
