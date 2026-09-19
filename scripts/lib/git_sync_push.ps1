# Gemeinsame Push-Logik fuer alle scripts\*_task.ps1-Wrapper.
#
# Vorher pushte jedes Skript direkt, ohne vorher zu fetchen/mergen. Sobald
# irgendeine andere Session (z.B. ein paralleler Cloud-Agent) zwischenzeitlich
# auf origin/main gepusht hatte, schlugen ALLE folgenden lokalen Pushes mit
# "fetch first" fehl -- nur als Warnung geloggt, nie eskaliert, wodurch sich
# ueber Stunden ein Rueckstand aufbaute, den GitHub/Streamlit Cloud nie sah,
# obwohl die Bots lokal weiterliefen (siehe DASHBOARD.md/CHANGELOG.md
# 2026-09-08 "Git-Sync-Reparatur"). Fix: vor jedem Push erst fetchen+mergen.
#
# 2026-09-17/19: genau dieser Merge blockierte dann 3 Tage lang JEDEN Push
# (240 Commits Rueckstand). Grund war NICHT ein Inhaltskonflikt, sondern
# "Your local changes to the following files would be overwritten by merge"
# -- die Auto-Tasks committen nur ihre EIGENEN Dateien, Aenderungen einer
# laufenden Session an knowledge/*.md bleiben unterwegs liegen. Fasst der
# Remote dieselbe Datei an, bricht der Merge ab. Zwei Korrekturen:
#   (a) Offene Aenderungen werden vor dem Merge selbst weggestasht und danach
#       zurueckgeholt -- der Working Tree sieht hinterher aus wie vorher.
#   (b) Die Warnung trennt jetzt nach Ursache, statt pauschal "vermutlich ein
#       echter Konflikt" zu behaupten (das war 3 Tage lang eine Fehldiagnose).
#
# Warum HIER von Hand gestasht wird und nicht per -c merge.autoStash=true:
# getestet am 2026-09-19 im Wegwerf-Repo -- autoStash holt die Aenderungen
# zurueck, BEVOR feststeht, ob das ohne Konflikt geht. Ueberschneiden sich
# Remote-Aenderung und offene Aenderung (genau der Fall vom 09-16), stehen
# danach Konfliktmarker mitten in der Datei einer laufenden Session, und der
# Stash bleibt zusaetzlich liegen. Hier gilt stattdessen: erst mergen+pushen
# (GitHub ist damit in jedem Fall aktuell), dann zurueckholen -- klappt das
# nicht sauber, bleibt die Datei auf dem gemergten Stand OHNE Marker und die
# offene Aenderung liegt vollstaendig im Stash (eine Zeile zum Zurueckholen).
#
# Aufruf-Konvention: Skript ruft NACH einem bereits erfolgten lokalen Commit
# `Sync-AndPush -Log ${function:Log}` auf, wobei `Log` die im aufrufenden
# Skript bereits definierte Logfunktion ist. Ein nicht sauberer Working Tree
# (Aenderungen anderer Sessions) ist dabei ausdruecklich erlaubt.
function Sync-AndPush {
    param(
        [Parameter(Mandatory = $true)][scriptblock]$Log
    )

    & git fetch origin 2>&1 | ForEach-Object { & $Log $_ }
    $fetchExit = $LASTEXITCODE

    $stashed = $false
    if ($fetchExit -eq 0) {
        # Offene Aenderungen (andere Sessions) beiseitelegen, damit der Merge
        # nicht an ihnen scheitert. --include-untracked bewusst NICHT: neue,
        # noch nicht getrackte Dateien einer Session sollen unangetastet
        # liegenbleiben, sie koennen einen Merge ohnehin nicht blockieren.
        if (& git status --porcelain --untracked-files=no) {
            & git stash push --quiet --message "git_sync_push: vor Merge beiseitegelegt" 2>&1 | ForEach-Object { & $Log $_ }
            if ($LASTEXITCODE -eq 0) {
                $stashed = $true
                & $Log "HINWEIS: offene Aenderungen vor dem Merge gestasht (werden nach dem Push zurueckgeholt)."
            } else {
                & $Log "WARNUNG: git stash fehlgeschlagen - Merge wird trotzdem versucht."
            }
        }

        # Ausgabe einsammeln statt direkt durchreichen: sie wird unten zur
        # Ursachen-Unterscheidung gebraucht (und trotzdem vollstaendig geloggt).
        $mergeOutput = & git merge --no-edit FETCH_HEAD 2>&1
        $mergeExit = $LASTEXITCODE
        $mergeOutput | ForEach-Object { & $Log $_ }

        if ($mergeExit -ne 0) {
            $text = ($mergeOutput | Out-String)
            if ($text -match 'CONFLICT|Automatic merge failed') {
                & $Log "WARNUNG: git merge hat einen ECHTEN Inhaltskonflikt (Exit $mergeExit) -- Merge abgebrochen, Push uebersprungen. Lokaler Commit bleibt liegen; bitte manuell aufloesen (git merge origin/main im Repo)."
            } elseif ($text -match 'would be overwritten|local changes') {
                & $Log "WARNUNG: git merge abgebrochen (Exit $mergeExit), weil nicht committete Aenderungen im Weg sind, die der Remote ebenfalls geaendert hat -- KEIN Inhaltskonflikt. Push uebersprungen. Die offenen Aenderungen committen oder stashen, dann loest sich das von selbst."
            } else {
                & $Log "WARNUNG: git merge fehlgeschlagen (Exit $mergeExit), Ursache unklar -- Merge abgebrochen, Push uebersprungen. Bitte manuell pruefen (git status im Repo)."
            }
            # Schlaegt --abort fehl (z.B. weil gar kein Merge im Gange war),
            # ist das unkritisch.
            & git merge --abort 2>&1 | Out-Null
            Restore-SyncStash -Log $Log -Stashed $stashed
            return
        }
    } else {
        & $Log "WARNUNG: git fetch fehlgeschlagen (Exit $fetchExit) - Push wird trotzdem versucht, kann bei zwischenzeitlicher Divergenz erneut fehlschlagen."
    }

    & git push 2>&1 | ForEach-Object { & $Log $_ }
    if ($LASTEXITCODE -ne 0) {
        & $Log "WARNUNG: git push fehlgeschlagen (Exit $LASTEXITCODE) trotz vorherigem Merge-Versuch - Commit liegt lokal vor, aber nicht auf GitHub bis zum naechsten erfolgreichen Push."
    } else {
        & $Log "Commit + Push erfolgreich."
    }

    Restore-SyncStash -Log $Log -Stashed $stashed
}

function Restore-SyncStash {
    # Holt die vor dem Merge beiseitegelegten Aenderungen zurueck. Laesst sich
    # der Stash nicht sauber anwenden (Remote und offene Aenderung betreffen
    # dieselben Zeilen), wird NICHT halb angewendet: der Working Tree bleibt
    # auf dem gemergten Stand ohne Konfliktmarker, der Stash bleibt vollstaendig
    # erhalten. Der Push ist zu diesem Zeitpunkt schon durch -- GitHub ist also
    # aktuell, und die offene Arbeit haengt an genau einem `git stash pop`.
    param(
        [Parameter(Mandatory = $true)][scriptblock]$Log,
        [Parameter(Mandatory = $true)][bool]$Stashed
    )
    if (-not $Stashed) { return }

    & git stash pop --quiet 2>&1 | ForEach-Object { & $Log $_ }
    if ($LASTEXITCODE -eq 0) {
        & $Log "Offene Aenderungen wieder zurueckgeholt, Working Tree wie vorher."
        return
    }

    # pop hat Konflikte erzeugt -> Arbeitsstand sauber zuruecksetzen, Stash
    # behalten. `reset --hard` statt `checkout -- .`: nach einem
    # fehlgeschlagenen pop stehen die Konflikt-Stufen im INDEX, ein checkout
    # aus dem Index wuerde die Marker wieder herausschreiben (getestet
    # 2026-09-19). Die verworfenen Aenderungen liegen vollstaendig im Stash.
    & git reset --hard --quiet HEAD 2>&1 | Out-Null
    & $Log "WARNUNG: die offenen Aenderungen liessen sich nach dem Merge nicht konfliktfrei zurueckholen (Remote hat dieselben Zeilen geaendert). Der Push ist durch, der Working Tree steht auf dem gemergten Stand OHNE Konfliktmarker. Die offene Arbeit liegt vollstaendig im Stash: mit 'git stash list' ansehen und 'git stash pop' von Hand zurueckholen/aufloesen."
}
