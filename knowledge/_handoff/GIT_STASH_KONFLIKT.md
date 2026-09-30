# Git-Stash-Konflikt: offene Arbeit liegt im Stash

**2026-09-30 20:56:33** -- `git_sync_push` konnte den vor dem Merge beiseitegelegten Stand
nicht konfliktfrei zurueckholen (der Remote hat dieselben Zeilen geaendert).

Der Working Tree steht auf dem **gemergten** Stand, ohne Konfliktmarker. Die
offene Arbeit ist NICHT verloren, sie liegt vollstaendig in `stash@{0}`.

Betroffene Dateien: fk_instant_funding_logs/task_run.log, ou_paper_backtest/results/scanner_task_run.log

Zurueckholen:

    git stash show -p "stash@{0}"      # ansehen
    git stash pop                       # zurueckholen und Konflikt aufloesen

Wenn du in einer Session mittendrin warst und deine Aenderungen verschwunden
sind: das hier ist die Ursache. Datei nach dem Aufloesen loeschen.
