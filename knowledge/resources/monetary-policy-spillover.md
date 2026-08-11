# Resource: Monetary-Policy-Spillover auf Staatsanleiherenditen

Destillate der Papers, die geldpolitische Ankündigungen und ihre
grenzüberschreitende Übertragung auf lange Renditen untersuchen -- Basis
für alles, was Zins-Spreads zwischen Ländern als FX-Signal nutzen will.

---

## Global Real Interest Rate Dynamics and Monetary Policy Announcements

**Capture** -- Yıldırım, A. (2024/2025, Central Bank of the Republic of Türkiye /
Uni Bonn MSc-Thesis); erfasst 2026-08-10, manuell im Chat (SSRN 6353258).

**Organize** -- Tags: monetary-policy, yield-spillover, event-study, FX-liquidity,
global-financial-cycle. Verwandt: [[fx-microstructure]] (Corwin-Schultz wird dort
noch nicht genutzt, aber gleiche Methodik-Familie). Verwandtes Project:
[[bond-yield-spread-indikator]].

**Distill**
- **Kernthese**: Erweitert Hillenbrand (2022) von US-only auf 6 fortgeschrittene
  Volkswirtschaften (DE, UK, JP, CA, CH, AU) -- der säkulare Renditerückgang ist
  in schmalen 3-Tage-Fenstern um FOMC-/heimische Notenbank-Ankündigungen
  konzentriert, nicht gleichmäßig strukturell. Massive Länder-Heterogenität in
  der Sensitivität gegenüber US-Zinsüberraschungen.
- **Zentrales Modell**:
  - Event-Dummy `D_FOMC_t` (Tag vor/von/nach Meeting) -- Kalender vollständig für
    Fed/ECB/BoE/BoJ/BoC/SNB/RBA 1997-2024 im Appendix (Tables 4-9), direkt
    kopierbar.
  - Baseline-Spillover: `Δ10yr_home,t = β0 + β1·Δ10yr_US,t` innerhalb der
    FOMC-Fenster. Standardisiertes β*: Kanada 0.81, UK 0.49, Deutschland 0.44,
    Schweiz 0.18, Japan 0.10, Australien 0.10 -- keine uniforme "Global Financial
    Cycle", sondern klar länderspezifisch.
  - Reduced-Form-Panel mit FX-Friktion als Moderator:
    `Δ10yr = β0 + β1·D_FOMC + β2·FXF + β3·(D_FOMC × FXF)`, FXF = Corwin-Schultz
    Bid-Ask-Spread-Schätzer (Appendix A, Formeln 4-7), berechenbar rein aus
    täglichen High/Low-Preisen -- **keine echten Quotes nötig**. β3 positiv (im
    Paper nur schwach signifikant): höhere FX-Friktion dämpft die Transmission.
  - IV/2SLS mit gelaggtem FXF als Instrument gegen Simultanität/Reverse
    Causality -- Robustheitscheck, bestätigt Richtung, aber nicht signifikant.
  - Erklärung der Heterogenität: unkonventionelle GP (QE-Programme brechen die
    Transmission strukturell, sichtbar an 2009-2012 Break bei DE/JP), aktive
    FX-Interventionspolitik (SNB koppelt CH ab), finanzielle/geografische
    Verflechtung mit den USA (CA extrem hoch).
- **Potenziell integrierbar**:
  1. Corwin-Schultz-Schätzer -- sofort auf vorhandene FX-OHLC-Daten anwendbar,
     unabhängig von Yield-Daten, als allgemeiner Liquiditäts-/Friktionsfilter
     für beliebige FX-Strategien im Repo (nicht nur diese hier).
  2. Event-Kalender Fed/ECB/BoE/BoJ/BoC/SNB/RBA als Timing-Overlay für jede
     Strategie, die um Notenbank-Termine herum Exposure anpassen will.
  3. Rollierendes länderspezifisches β als Sensitivitätsgewicht -- Grundlage für
     [[bond-yield-spread-indikator]].

**Express** -- Kein direkter Backtest aus diesem Paper allein möglich, da es nur
Yield-auf-Yield regressiert, keine FX-Returns. Als Baustein in
[[bond-yield-spread-indikator]] aufgenommen und dort vollständig zu einem
Composite-Indikator + Backtest ausgebaut (2026-08-10). Ergebnis: kein
belastbarer Edge in der FRED-Monatsdaten-Auflösung für 6 der 7 Länder --
s. Projekt-Notiz für Details und die vermutete Ursache.
