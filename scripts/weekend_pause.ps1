<#
.SYNOPSIS
    Wochenend-Pause fuer alle handelsbezogenen Scheduled Tasks (Stand 2026-09-13).

.DESCRIPTION
    Der Forex-Markt hat Sa/So geschlossen -- es gibt keine neuen Daten und keine
    Orders. Trotzdem liefen mehrere Tasks mit 7-Tage-Triggern rund um die Uhr
    durch (am auffaelligsten EK-Portfolio-Bridge-Fast: alle 2 Minuten, 7 Tage).
    Dieses Skript setzt den Soll-Zustand: jeder Task unten laeuft ausschliesslich
    Mo-Fr und seine Wiederholung endet noch am selben Tag (kein Ueberhang in den
    Samstag).

    Bewusst NICHT enthalten (laufen weiter, Nutzerentscheid 2026-09-13):
      - Forex-Weekly-Report        (So 18:00, kein MT5/Marktdatenbezug)
      - Dashboard-Telegram-Digest  (taeglich 08:00, liest nur DASHBOARD.md)
      - BTC-Tasks                  (unangetastet, ohnehin Disabled)
      - OU-Modell-ScannerHourly    (8 Einzeltrigger, bereits Mo-Fr, keine Wdh.)

    WICHTIG -- Minuten-/Sekunden-Versatz: Die Startzeiten unten sind kein
    Zufall. Der DataLake-Ingest muss VOR dem Bridge-Scan laufen (Fund
    2026-09-09, Task-Offsets). Deshalb uebernimmt jeder Eintrag exakt den
    mm:ss-Versatz des bisherigen Triggers, nur mit Wochentags-Einschraenkung.

.PARAMETER Verify
    Zeigt den Ist-Zustand aller betroffenen Tasks (Trigger + NextRunTime).

.PARAMETER Apply
    Legt zuerst ein XML-Backup an und setzt dann die Soll-Trigger. Idempotent:
    ein zweiter Lauf meldet nur noch "ok".

.PARAMETER Revert
    Spielt die zuletzt gesicherten XML-Definitionen zurueck.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\weekend_pause.ps1 -Verify
    powershell -ExecutionPolicy Bypass -File scripts\weekend_pause.ps1 -Apply
#>
[CmdletBinding(DefaultParameterSetName = 'Verify')]
param(
    [Parameter(ParameterSetName = 'Verify')][switch]$Verify,
    [Parameter(ParameterSetName = 'Apply')][switch]$Apply,
    [Parameter(ParameterSetName = 'Revert')][switch]$Revert,
    [string]$BackupDir = (Join-Path $PSScriptRoot 'task_backups')
)

$ErrorActionPreference = 'Stop'

# Soll-Zustand. Start = Uhrzeit des ERSTEN Laufs am Tag (traegt den Versatz),
# Interval/Duration als ISO-8601 wie im Task Scheduler angezeigt.
# Duration ist jeweils so gewaehlt, dass der letzte Lauf vor 24:00 liegt.
$Spec = @(
    # --- bisher 7-Tage-Trigger, werden auf Mo-Fr umgestellt ---
    @{ Name = 'EK-Portfolio-Bridge-Fast';         Start = '00:00:10'; Interval = 'PT2M';  Duration = 'PT23H58M' }
    @{ Name = 'FKInstantFunding-MT5-Bridge';      Start = '00:14:00'; Interval = 'PT1H';  Duration = 'PT23H'    }
    @{ Name = 'FK-Instant-Funding-Paper';         Start = '00:55:22'; Interval = 'PT1H';  Duration = 'PT23H'    }
    @{ Name = 'DataLake-Ingest-Fast';             Start = '00:10:28'; Interval = 'PT15M'; Duration = 'PT23H45M' }
    @{ Name = 'DataLake-Ingest-Fast5';            Start = '00:01:50'; Interval = 'PT5M';  Duration = 'PT23H55M' }
    @{ Name = 'DataLake-Ingest-Slow';             Start = '00:10:29'; Interval = 'PT1H';  Duration = 'PT23H'    }
    @{ Name = 'Bridge-Watchdog';                  Start = '00:01:23'; Interval = 'PT30M'; Duration = 'PT23H30M' }
    # --- bereits Mo-Fr, aber Wiederholung lief bis in den Samstag (P1D) ---
    @{ Name = 'Funded-Portfolio-Bridge';          Start = '00:13:00'; Interval = 'PT15M'; Duration = 'PT23H45M' }
    @{ Name = 'Funded-Portfolio-Bridge-Fast';     Start = '00:03:00'; Interval = 'PT5M';  Duration = 'PT23H55M' }
    @{ Name = 'FKInstantFunding-MT5-Bridge-Fast'; Start = '00:03:00'; Interval = 'PT5M';  Duration = 'PT23H55M' }
    # --- bereits korrekt, nur zur Vollstaendigkeit (Apply ist hier ein No-Op) ---
    @{ Name = 'EK-Portfolio-Bridge';              Start = '00:14:00'; Interval = 'PT15M'; Duration = 'PT23H45M' }
)

$WeekdayMask = 62  # Mo+Di+Mi+Do+Fr im DaysOfWeek-Bitfeld (So=1, Mo=2, ... Sa=64)
$Weekdays = @('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday')

function Get-SpecTrigger {
    param($Item)
    $t = [datetime]::ParseExact($Item.Start, 'HH:mm:ss', $null)
    $at = (Get-Date).Date.AddHours($t.Hour).AddMinutes($t.Minute).AddSeconds($t.Second)

    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Weekdays -At $at
    # New-ScheduledTaskTrigger kennt -RepetitionInterval nur bei -Once; das
    # Repetition-Objekt eines Once-Triggers laesst sich aber uebernehmen.
    $helper = New-ScheduledTaskTrigger -Once -At $at `
        -RepetitionInterval ([System.Xml.XmlConvert]::ToTimeSpan($Item.Interval)) `
        -RepetitionDuration ([System.Xml.XmlConvert]::ToTimeSpan($Item.Duration))
    $trigger.Repetition = $helper.Repetition
    return $trigger
}

function Test-SpecMatch {
    param($Task, $Item)
    if ($Task.Triggers.Count -ne 1) { return $false }
    $tr = $Task.Triggers[0]
    if ($tr.CimClass.CimClassName -ne 'MSFT_TaskWeeklyTrigger') { return $false }
    if ([int]$tr.DaysOfWeek -ne $WeekdayMask) { return $false }
    if (([datetime]$tr.StartBoundary).ToString('HH:mm:ss') -ne $Item.Start) { return $false }
    if ($tr.Repetition.Interval -ne $Item.Interval) { return $false }
    if ($tr.Repetition.Duration -ne $Item.Duration) { return $false }
    return $true
}

function Show-State {
    foreach ($item in $Spec) {
        $task = Get-ScheduledTask -TaskName $item.Name -ErrorAction SilentlyContinue
        if (-not $task) {
            Write-Host ("{0,-36} FEHLT" -f $item.Name) -ForegroundColor Red
            continue
        }
        $info = Get-ScheduledTaskInfo -TaskName $item.Name
        $match = Test-SpecMatch -Task $task -Item $item
        $color = if ($match) { 'Green' } else { 'Yellow' }
        $tr = $task.Triggers[0]
        $days = if ($tr.PSObject.Properties.Name -contains 'DaysOfWeek' -and $tr.DaysOfWeek) { "Mo-Fr($($tr.DaysOfWeek))" } else { 'ALLE TAGE' }
        Write-Host ("{0,-36} {1,-26} {2,-12} {3,-6}/{4,-9} next={5}" -f `
                $item.Name,
            $tr.CimClass.CimClassName.Replace('MSFT_Task', ''),
            $days,
            $tr.Repetition.Interval,
            $tr.Repetition.Duration,
            $info.NextRunTime) -ForegroundColor $color
    }
}

function Backup-Tasks {
    if (-not (Test-Path $BackupDir)) { New-Item -ItemType Directory -Path $BackupDir | Out-Null }
    $stamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
    foreach ($item in $Spec) {
        $xml = & schtasks.exe /Query /TN $item.Name /XML ONE 2>$null
        if ($LASTEXITCODE -ne 0) { Write-Host "  Backup uebersprungen (Task fehlt): $($item.Name)" -ForegroundColor Yellow; continue }
        $file = Join-Path $BackupDir "$($item.Name).$stamp.xml"
        $xml | Out-File -FilePath $file -Encoding unicode
    }
    Write-Host "Backup abgelegt in $BackupDir (Stempel $stamp)" -ForegroundColor Cyan
}

function Apply-Spec {
    Backup-Tasks
    foreach ($item in $Spec) {
        $task = Get-ScheduledTask -TaskName $item.Name -ErrorAction SilentlyContinue
        if (-not $task) { Write-Host ("{0,-36} FEHLT -- uebersprungen" -f $item.Name) -ForegroundColor Red; continue }
        if (Test-SpecMatch -Task $task -Item $item) {
            Write-Host ("{0,-36} ok (unveraendert)" -f $item.Name) -ForegroundColor DarkGray
            continue
        }
        $trigger = Get-SpecTrigger -Item $item
        Set-ScheduledTask -TaskName $item.Name -Trigger $trigger | Out-Null
        Write-Host ("{0,-36} gesetzt: Mo-Fr ab {1}, alle {2}, bis {3}" -f $item.Name, $item.Start, $item.Interval, $item.Duration) -ForegroundColor Green
    }
}

function Revert-Tasks {
    if (-not (Test-Path $BackupDir)) { throw "Kein Backup-Verzeichnis: $BackupDir" }
    foreach ($item in $Spec) {
        $file = Get-ChildItem -Path $BackupDir -Filter "$($item.Name).*.xml" -ErrorAction SilentlyContinue |
            Sort-Object Name | Select-Object -Last 1
        if (-not $file) { Write-Host ("{0,-36} kein Backup gefunden" -f $item.Name) -ForegroundColor Yellow; continue }
        & schtasks.exe /Create /TN $item.Name /XML $file.FullName /F | Out-Null
        Write-Host ("{0,-36} zurueckgespielt aus {1}" -f $item.Name, $file.Name) -ForegroundColor Green
    }
}

if ($Apply) { Apply-Spec; Write-Host ''; Write-Host 'Ist-Zustand danach:' -ForegroundColor Cyan; Show-State }
elseif ($Revert) { Revert-Tasks; Write-Host ''; Show-State }
else { Show-State }
