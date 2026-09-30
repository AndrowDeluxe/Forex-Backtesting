# Handoff 2026-09-30 — CTNL-Kill-Switch + EK-Mindestlot

Nur das, was sonst nirgends steht. Der Rest ist in CHANGELOG/DASHBOARD und
`projects/ek-risiko-kalibrierung-audit.md`.

## 1. WICHTIG: die Kill-Switch-Verdrahtung ist NICHT git-gesichert

Das geteilte Modul `gold_smc_htf_ltf/ctnl_kill_switch.py` ist committet
(`99605b1`). **Die Verdrahtung liegt in den Bridge-Ordnern ausserhalb des
Repos und ist nicht git-getrackt** (siehe Memory
`external_bridge_files_no_git_safety_net`). Betroffen:

- `Funded-Portfolio-Bridge/run_once.py` — Import, `_check_ctnl_kill_switch()`,
  Aufruf im `scans["ctnl_edge"]`-Block, `ctnl_entries_allowed` an beide
  `_process_leg`-Aufrufe
- `Funded-Portfolio-Bridge/run_once_fast.py` — `rev_trades` wird jetzt als
  `results["_ctnl_rev_trades"]` aufgehoben (vorher verworfen!) + Gate vor
  `_process_leg`
- `EK-Portfolio-Bridge/legs/ctnl_edge/executor.py` — Import + Block in
  `_send_entry()` direkt nach `entries_allowed()`

**Geht eine dieser Dateien verloren oder wird sie von einer anderen Session
ueberschrieben, faellt der Schalter still aus** — genau das Muster, das ihn
ueberhaupt noetig gemacht hat ("in alle Bots nachgeruestet" hiess Paper-Bots).
Pruefbefehl:

    grep -c ctnl_kill_switch ~/Funded-Portfolio-Bridge/run_once.py \
      ~/Funded-Portfolio-Bridge/run_once_fast.py \
      ~/EK-Portfolio-Bridge/legs/ctnl_edge/executor.py
    # erwartet: 3 / 1 / 5  (Stand 30.09.)

## 2. Der Schalter ist AKTIV, nicht schlafend

Gemessener Stand-alone-Drawdown am 30.09.: **-7,01 %** gegen Schwelle
-6,60 %. Funded und EK sperren ab dem naechsten Lauf neue CTNL-Entries.
**Das ist gewollt** — aber wer die Bridges morgen anschaut und "keine
CTNL-Entries" sieht, soll nicht nach einem Bug suchen. Aufhebung erst bei
Erholung auf -3,30 % (Hysterese).

FK bleibt bewusst bei seiner eigenen Implementierung — sie funktioniert und
ist die Referenz. Die Doppelung ist bekannt und nicht aufgeraeumt.

## 3. Nicht getestet

Der Funktionstest lief gegen den **Lake** und gegen die Entscheidungslogik
(6 Faelle). **Kein Lauf gegen ein echtes MT5-Terminal** — der naechste
regulaere Bridge-Lauf ist der erste Ernstfall. Bei EK ist die Meldung
ueber die Tages-Dedup verdrahtet (`already_notified("ctnl_kill_switch", leg)`);
ob sie im Telegram ankommt, ist ungeprueft.

## 4. Eine Fehlannahme von mir, die korrigiert wurde

Ich hatte zuerst einen `_check_ctnl_kill_switch()` **lokal in Funded**
gebaut. Das war falsch — es haette die vierte Kopie derselben Logik
ergeben, in einem System, das genau daran schon einmal gescheitert ist
(`three_bridges_not_same_state`). Deshalb jetzt ein geteiltes Modul nach dem
`ribbon_gate`-Muster. Falls jemand die alte lokale Funktion in einem Backup
findet: sie ist ueberholt, nicht parallel zu pflegen.

## 5. Offen, mit Zahlen unterlegt, wartet auf Entscheidung

- **EK-Mindestlot, drei Wege** (Dashboard): Konto auf ~12.400 EUR und
  `ctnl_reversal` streichen / CTNL-Beine auf EK abschalten / alles lassen.
  `ctnl_reversal` braeuchte **143.787 EUR**, um in kalibrierter Groesse zu
  handeln — auf diesem Konto strukturell nicht darstellbar.
- **`ou_modell` laeuft mit Faktor 4,40x statt dokumentierter 2,20x** — ich
  habe angeboten, es zurueckzuziehen, keine Antwort. Steht seit 23.09.
- **Split-Schutz fehlt in allen drei Bridges**, waehrend `ou_modell` auf
  Funded und EK Einzelaktien handelt. Vom MNST-Punkt abgetrennt, damit es
  nicht mit dem abgeschriebenen ttp1-Konto stillschweigend mituntergeht.

## 6. Stash-Problem: Ursache behoben, Wirkung unbeobachtet

`scripts/lib/git_sync_push.ps1` stasht auf einem schmutzigen Baum nicht mehr
(`git stash push` kommt im Skript nicht mehr vor, `reset --hard` unerreichbar).
**Ob die Stash-Zahl jetzt wirklich bei 0 bleibt, ist noch nicht beobachtet** —
der Fix ist Stunden alt. Gegenprobe in ein paar Tagen: `git stash list | wc -l`
sollte 0 sein, und `git log origin/main..HEAD` darf zeitweise Rueckstand
zeigen (das ist gewollt, nicht der Fehler).
