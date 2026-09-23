param(
    [Parameter(Mandatory = $true)]
    [string]$GameRoot
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $GameRoot).Path
$managed = Join-Path $root 'DSPGAME_Data\Managed'
$bepinexCore = Join-Path $root 'BepInEx\core'
$files = @(
    'DSPGAME.exe',
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
    managed_directory_present = Test-Path -LiteralPath $managed
    bepinex_core_present = Test-Path -LiteralPath $bepinexCore
    dotnet_available = $null -ne (Get-Command dotnet -ErrorAction SilentlyContinue)
    files = @($inventory)
} | ConvertTo-Json -Depth 4
