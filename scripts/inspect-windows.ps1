param(
    [Parameter(Mandatory = $true)]
    [string]$GameRoot
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $GameRoot).Path
$managed = Join-Path $root 'DSPGAME_Data\Managed'
$bepinexCore = Join-Path $root 'BepInEx\core'
$versionFile = Join-Path $root 'Updates\Versions.txt'
$logFile = Join-Path $root 'BepInEx\LogOutput.log'
$localDotnet = Join-Path $env:USERPROFILE '.dotnet\dotnet.exe'
$dotnetCommand = Get-Command dotnet -ErrorAction SilentlyContinue
$dotnetExe = if ($dotnetCommand) { $dotnetCommand.Source } elseif (Test-Path -LiteralPath $localDotnet) { $localDotnet } else { $null }
$versionRecord = if (Test-Path -LiteralPath $versionFile) {
    [string](Get-Content -LiteralPath $versionFile | Where-Object { $_.Trim() } | Select-Object -Last 1)
} else { $null }
$logLines = if (Test-Path -LiteralPath $logFile) { @(Get-Content -LiteralPath $logFile -TotalCount 200) } else { @() }
$files = @(
    'DSPGAME.exe',
    'MonoBleedingEdge\EmbedRuntime\mono-2.0-bdwgc.dll',
    'GameAssembly.dll',
    'DSPGAME_Data\il2cpp_data\Metadata\global-metadata.dat',
    'DSPGAME_Data\Managed\Assembly-CSharp.dll',
    'DSPGAME_Data\Managed\mscorlib.dll',
    'DSPGAME_Data\Managed\netstandard.dll',
    'DSPGAME_Data\Managed\UnityEngine.CoreModule.dll',
    'BepInEx\core\BepInEx.dll',
    'BepInEx\LogOutput.log'
)

$inventory = foreach ($relative in $files) {
    $path = Join-Path $root $relative
    $item = Get-Item -LiteralPath $path -ErrorAction SilentlyContinue
    if ($null -eq $item) {
        [pscustomobject]@{ file = $relative; present = $false; version = $null }
    } else {
        [pscustomobject]@{
            file = $relative
            present = $true
            version = if ($item.PSIsContainer) { $null } else { $item.VersionInfo.FileVersion }
        }
    }
}

[pscustomobject]@{
    inspected_at_utc = (Get-Date).ToUniversalTime().ToString('o')
    game_root = $root
    latest_version_record = $versionRecord
    scripting_backend_evidence = if ((Test-Path -LiteralPath (Join-Path $root 'MonoBleedingEdge')) -and (Test-Path -LiteralPath (Join-Path $managed 'Assembly-CSharp.dll'))) { 'Mono files present' } elseif (Test-Path -LiteralPath (Join-Path $root 'GameAssembly.dll')) { 'IL2CPP files present' } else { 'unknown' }
    managed_directory_present = Test-Path -LiteralPath $managed
    bepinex_core_present = Test-Path -LiteralPath $bepinexCore
    dotnet_executable = $dotnetExe
    dotnet_sdks = if ($dotnetExe) { @(& $dotnetExe --list-sdks) } else { @() }
    bepinex_startup_complete = @($logLines | Where-Object { $_ -match 'Chainloader startup complete' }).Count -gt 0
    bepinex_log_header = [string]($logLines | Where-Object { $_ -match 'BepInEx [0-9].* - DSPGAME' } | Select-Object -First 1)
    files = @($inventory)
} | ConvertTo-Json -Depth 4
