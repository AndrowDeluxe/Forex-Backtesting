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
# Aufruf-Konvention: Skript ruft NACH einem bereits erfolgten lokalen Commit
# (Working Tree also sauber) `Sync-AndPush -Log ${function:Log}` auf, wobei
# `Log` die im aufrufenden Skript bereits definierte Logfunktion ist.
function Sync-AndPush {
    param(
        [Parameter(Mandatory = $true)][scriptblock]$Log
    )

    & git fetch origin 2>&1 | ForEach-Object { & $Log $_ }
    $fetchExit = $LASTEXITCODE

    if ($fetchExit -eq 0) {
        & git merge --no-edit --quiet FETCH_HEAD 2>&1 | ForEach-Object { & $Log $_ }
        if ($LASTEXITCODE -ne 0) {
            & $Log "WARNUNG: git merge von origin/main fehlgeschlagen (Exit $LASTEXITCODE), vermutlich ein echter Konflikt -- Merge abgebrochen, Push uebersprungen. Lokaler Commit bleibt unveraendert liegen, bitte manuell pruefen (git status im Repo)."
            & git merge --abort 2>&1 | Out-Null
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
}
