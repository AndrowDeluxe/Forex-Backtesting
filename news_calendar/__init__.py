"""US + EUR High-Impact-News-Kalender fuer Backtest-Filter (2026-08-12, auf
Wunsch des Users -- "ganz simpler" Filter, der das Handeln an Tagen mit
grossen US/EUR-Datenveroeffentlichungen einschraenkt).

Zwei offizielle, kostenlose/keylose Quellen (bewusst KEIN Scraping eines
Bot-geschuetzten Anbieters wie ForexFactory -- siehe Diskussion im Chat,
2026-08-12):
- fred_releases.py: FRED-API (braucht kostenlosen Key, siehe
  .streamlit/secrets.toml) -- Employment Situation (NFP), Consumer Price
  Index, Advance Retail Sales, Gross Domestic Product.
- eurostat_calendar.py: Eurostats oeffentlicher iCalendar-Feed (keylos) --
  HICP-Inflation (Flash + final), GDP (Flash + final), plus ein paar weitere
  "Euro indicator release"-Termine.

Bekannte Luecke (bewusst nicht erfunden): kein ISM-PMI-Aequivalent fuer US
oder EUR -- ISM-Daten sind nicht auf FRED verfuegbar (Lizenzgrund), ein
frei zugaengliches EUR-PMI-Kalenderdatum wurde nicht gefunden.

filter.py kombiniert beide zu einer einzigen `is_news_day()`/`news_day_dummy()`
-Funktion, analog zu bond_yield_indicator/calendar.py's event_window_dummy()."""
