param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f]{32}$')]
    [string]$ExpectedSession,
    [ValidateRange(1, 30)]
    [int]$MaxAttempts = 12,
    [ValidateRange(1, 60)]
    [int]$MaxMinutes = 20
)

$ErrorActionPreference = 'Stop'
$python = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
$project = '\\wsl.localhost\Ubuntu\home\ds\dev\dyson-sphere-program-ai-mecha'
$env:PYTHONPATH = Join-Path $project 'src\Agent'
$dataDir = Join-Path $env:LOCALAPPDATA 'DSPAgent\codex-experiments-20260924'
$statusPath = Join-Path $dataDir 'live-agent-status.json'
$stopPath = Join-Path $dataDir 'live-agent.stop'
$logPath = Join-Path $dataDir 'live-agent-console.log'
$lockPath = Join-Path $dataDir 'live-agent.lock'
$bridge = 'http://127.0.0.1:38741'
$codexCommand = 'wsl.exe --exec /home/ds/.local/bin/codex'
$started = Get-Date
$completed = 0
$lastAction = ''

if (-not (Test-Path -LiteralPath $python)) { throw "Windows Python is unavailable: $python" }
if (-not (Test-Path -LiteralPath $dataDir)) { New-Item -ItemType Directory -Path $dataDir | Out-Null }
if (Test-Path -LiteralPath $stopPath) { throw "Stop file exists: $stopPath" }
$lock = [System.IO.File]::Open($lockPath, 'OpenOrCreate', 'ReadWrite', 'None')

function Set-AgentStatus([string]$state, [int]$count, [string]$message) {
    $status = [ordered]@{
        updated_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        state = $state
        completed_attempts = $count
        max_attempts = $MaxAttempts
        expected_session = $ExpectedSession
        message = $message
        last_action = $script:lastAction
        stop_file = $stopPath
    }
    $temporary = "$statusPath.tmp"
    $status | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $statusPath -Force
    Write-Host "[$($status.updated_at_utc)] $state $count/$MaxAttempts - $message"
}

Start-Transcript -Path $logPath -Append | Out-Null
try {
    Write-Host 'Press Esc in DSP to pause and stop after the current attempt, or Ctrl+C here.'
    Write-Host "Live status: $statusPath"
    Set-AgentStatus 'starting' 0 'Checking the visible game session.'
    for ($count = 0; $count -lt $MaxAttempts; $count++) {
        if (Test-Path -LiteralPath $stopPath) {
            Set-AgentStatus 'stopped' $count 'Stop file requested by the user.'
            break
        }
        if ((Get-Date) -ge $started.AddMinutes($MaxMinutes)) {
            Set-AgentStatus 'stopped' $count 'Wall-clock limit reached.'
            break
        }
        $observation = Invoke-RestMethod -Uri "$bridge/v1/observe" -TimeoutSec 5
        if ($observation.status -ne 'ok' -or $observation.session_id -ne $ExpectedSession) {
            Set-AgentStatus 'stopped' $count 'The designated game session changed or unloaded.'
            break
        }
        if ($observation.paused -ne $false) {
            Set-AgentStatus 'stopped' $count 'The game is paused.'
            break
        }
        if ($observation.planet.id -ne 102) {
            Set-AgentStatus 'stopped' $count 'The game left the designated planet.'
            break
        }
        Set-AgentStatus 'planning' $count 'Codex is choosing a goal and one bounded action.'
        $output = & $python -m dsp_agent experiment-once --bridge $bridge `
            --codex-command $codexCommand --data-dir $dataDir --allow-game-write 2>&1
        if ($LASTEXITCODE -ne 0) {
            $message = ($output | Out-String).Trim()
            Set-AgentStatus 'error' $count $message
            break
        }
        $attempt = ($output | Out-String | ConvertFrom-Json)
        $nextCount = $count + 1
        $completed = $nextCount
        $message = "Goal: $($attempt.near_term_goal); action: $($attempt.action.kind); args: $(($attempt.action.args | ConvertTo-Json -Compress)); verdict: $($attempt.verdict); attempt: $($attempt.attempt_id)"
        $lastAction = $message
        Set-AgentStatus 'completed' $nextCount $message
        if ($attempt.verdict -ne 'achieved') {
            Set-AgentStatus 'stopped' $nextCount 'A non-achieved result requires review before another action.'
            break
        }
        if ($nextCount -eq $MaxAttempts) {
            Set-AgentStatus 'stopped' $nextCount 'Attempt limit reached.'
            break
        }
        Start-Sleep -Seconds 2
    }
} catch {
    Set-AgentStatus 'error' $completed $_.Exception.Message
} finally {
    Stop-Transcript | Out-Null
    $lock.Dispose()
}
