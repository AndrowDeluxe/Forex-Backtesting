# SMH-Elite-Call "Session Pips und Wahrscheinlichkeiten": nachgerechnet

Quelle: Aufzeichnung des Smartmoneyhour-Elite-3-Calls (~42 Min.), lokal unter
`OneDrive\...\Institutial Mandate\Calls\`. Das Transkript liegt daneben und
nicht im Repo, weil es bezahlter Kursinhalt ist. Transkribiert wurde am
2026-10-27 mit Whisper. Gezeigt wurde ein Tool "Zeit-Heatmap FX" des Mentors
(nach seinen Angaben 6 Paare, 1-Minuten-Daten 01/2015–03/2025, MEZ/MESZ).
Verwandt: [[smh-cls-praxis-call]], [[cls-practical-kostenvalidierung]],
[[overfitting-sperre]].

## Aussagen des Calls
1. **Stundenprofil:** Die Median-Range je Stunde und Wochentag ist "zu
   97–99 % jedes Jahr gleich". Nutzen laut Mentor: Ziele und Stops an die
   Stunde anpassen, nicht in Bewegungen hineinlesen, die nur dem
   Stundendurchschnitt entsprechen.
2. **Ruck zu festen Terminen:** Range der 5 Minuten nach dem Termin gegen
   die 5 Minuten davor. Laut Mentor 07:00 1,4× ("der CLS-Effekt ist
   gemessen"), 08:00 1,9×, 09:00 1,5×, 11:00 1,1× (Kontrolle ohne Termin),
   14:30 1,9×, 16:00 1,3×. Regel: "kurz vor 08:00 und 14:30 keine neuen
   Einstiege mit engem Stop".
3. **02–03 Uhr:** aktivste Asia-Stunde (LCH öffnet 02:30), dort entsteht
   besonders oft das Tageshoch oder -tief.
4. **Ausschöpfung:** Hat eine Stunde ihren Durchschnitt an Pips schon
   gelaufen, wird eine Umkehr wahrscheinlicher. Daraus folgen POI, Stop und
   Ziel. Stundenranges darf man **nicht** einfach addieren, weil sie sich
   überlappen (korrekt).
5. **Sonstiges ohne Testwert:** CLS netted ~5 Bio. $/Tag auf ~80 Mrd. am
   Markt; IPDA-20-Tage-Zyklen; ein noch unveröffentlichter
   "Regressions-Indikator" (Reaktionswahrscheinlichkeit 81–91 % an Hochs
   und Tiefs). Dazu die These, Edge Cards fehle Kontext/Makro/Sentiment.

## Nachrechnung auf unseren Daten
`scripts/research_session_pips_heatmap.py`, EUR/USD M5 Dukascopy, Berlin,
12/2018–10/2026, rein beschreibend.

| Aussage | Ergebnis | Urteil |
|---|---|---|
| 1 Profil stabil | Korrelation des Jahresprofils mit dem Gesamtprofil 0,98–0,99 (2018: 0,94). Unsere Zellen treffen seine fast genau (z. B. Mo 02 Uhr 10,5 vs. 10,9). **Das Niveau schwankt aber stark:** Median-Stundenrange je Jahr 8,2 (2019) bis 15,3 Pips (2022). | **Form bestätigt, absolute Pips nicht.** Ein 10-Jahres-Median ist in einzelnen Jahren um bis zu Faktor 1,5–2 daneben. Nur ein aktuelles Fenster taugt (sein Indikator nutzt die letzten 20 Tage, das ist richtig). |
| 2 Ruck | 08:00 **1,56×**, 09:00 1,33×, 14:30 **1,50×** (Mittel 2,18×, News-Ausreißer), 16:00 1,31×, 15:30 1,21×, **07:00 nur 1,10×**, Kontrolle 11:00 1,16×, 06:00 1,06×, 17:00 0,93× | 08:00, 14:30, 16:00 bestätigt. **Der 07:00-"CLS-Effekt" repliziert nicht**: Er ist nicht von der Kontrollstunde zu unterscheiden. Möglicher Grund für seine 1,4×: Sommer-/Winterzeit nicht sauber umgerechnet, sodass ein Teil des 08:00-Rucks auf 07:00 fällt (Vermutung). |
| 3 02–03 Uhr | 02 Uhr ist tatsächlich die aktivste Asia-Stunde. Tageshoch/-tief fallen dort aber nur an 4,4 % bzw. 4,8 % der Tage (Gleichverteilung 4,2 %). Gehäuft liegen sie bei 08–09 Uhr und 14–16 Uhr (16 Uhr: 17,9 % Hoch oder Tief). | **Aktivität bestätigt, Hoch/Tief-Häufung nicht.** |
| 4 Ausschöpfung | nicht gerechnet | testbar, siehe unten |

## Was wir mitnehmen können
- **Für die CLS-Begründung:** Unsere CLS-Strategie hängt nicht am
  07:00-Ruck. Ihr Edge ist separat validiert ([[cls-practical-kostenvalidierung]]).
  Die Erzählung "CLS bewegt um 07:00 messbar den Markt" ist auf
  Volatilitätsebene aber nicht belegt. Der Ruck kommt um 08:00/09:00 mit
  Frankfurt/London.
- **Kandidat A: Einstiegssperre vor 08:00 und 14:30** (Regel 2) für Beine
  mit engem Stop. **Am 2026-10-27 nach der Bestandsaufnahme ohne Test
  verworfen** (`scripts/research_termin_sperre_inventur.py`, Live-
  Trade-Listen TTP 2019–2026, nur IS bis 05/2022, keine Versuche verbraucht):
  - Einstiege in den 15 Minuten vor dem Termin: über alle Beine nur 13 im
    IS (Gold ASB 7 vor 08:00, CTNL 2 vor 08:00 und 4 vor 14:30). CLS, ORB
    und Trend Pullback steigen dort nie ein. ORB öffnet erst nach 15:30.
  - Über den Termin gehaltene Positionen werden binnen 30 Minuten danach
    nicht auffällig oft gestoppt: 08:00 überall 0 %, 14:30 0–3 %, nur CLS
    2/12 (17 %). Die CLS-Kontrolle 11:00 liegt bei 14 % (5/37). Gold ASB hält
    alle 80 Trades über 14:30, keiner wird dort gestoppt.

  Die Regel schützt enge Stops kurz vor Terminen. Diese Konstellation kommt
  bei unseren Beinen praktisch nicht vor. Wiedervorlage nur, wenn ein neues
  Bein mit engem Stop um 07:45–08:00 oder 14:15–14:30 dazukommt.
- **Kandidat B: Stunden-Ausschöpfung als Fade-Signal** (Aussage 4).
  **Am 2026-10-28 im IS verworfen**: `scripts/research_session_pips_fade.py`,
  Lock `session_pips_fade` mit 1 Versuch. Märkte, Stunden und Auslöser hat
  der Nutzer vorab festgelegt: 6 FX-Majors + Gold, 08–17 Uhr, laufende
  Spanne erreicht den 20-Tage-Median derselben Stunde. Einstieg zum
  Schluss der Auslöse-Bar, Ausstieg zum Stundenende. IS 2016–2022 mit
  53.912 Ereignissen.
  - **Brutto existiert der Effekt:** +0,019 T (t +5,8, Tages-Cluster),
    Trefferquote 51–54 %. Das sind aber nur 0,0–0,36 Pips je Ereignis
    (Gold 0,01 bps).
  - **Netto ist er negativ:** −0,122 T (t −37), 0/7 Märkte positiv. Auch
    jede einzelne Stunde liegt bei −0,10 bis −0,17 T. Die Kosten für die
    nicht gemessenen Majors sind angenommen, das Ergebnis hängt bei einem
    Faktor 6–200 zwischen Kosten und Brutto aber nicht davon ab.
  - **Vier-Fragen-Check:** (1) Geld verdient hier, wer Liquidität stellt:
    Die Mini-Umkehr ist die Spanne des Market Makers, siehe
    [[smh-elite-mikrostruktur]]. (2)–(4) entfallen, weil netto nirgends
    ein Edge übrig ist. Eine Filterregel würde nur Rauschen auswählen.
  - OOS und Tresor bleiben versiegelt.
- **Nicht übernehmen:** Stunden-Pips als Stop/Ziel für CLS. Volatilitäts-
  und Session-Stops sowie TP-Varianten sind dort bereits verworfen
  ([[smh-cls-praxis-call]], Kostenvalidierung Befund 6).
