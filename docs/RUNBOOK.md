# Windows Runbook

This runbook covers the Windows installation, observer, and bounded walking action. Current validation limits are in [build status](../.ai/14-build-status.md).

## Development agent on Windows

Use Windows-native PowerShell with Codex or Orca so the agent can inspect the actual DSP installation. Install Git, Python, Node.js LTS, and a .NET SDK. Install Codex CLI with `npm install -g @openai/codex@latest`, run `codex` once, and sign in. Orca is optional: install its Windows app, add this repository, select Codex as the agent, and use the existing Windows Codex login. Orca runs Codex in the selected worktree; it is the development interface, not the in-game agent.

The current working checkout is in WSL at `/home/ds/dev/dyson-sphere-program-ai-mecha`. Windows accesses the same files at `\\wsl.localhost\Ubuntu\home\ds\dev\dyson-sphere-program-ai-mecha`; do not create a second uncommitted checkout for native builds. From the project root, run `PYTHONPATH=src/Agent python3 -m unittest discover -s tests -v` in WSL.

## Prepare the game machine

1. Open the cloned repository on Windows. Record the Git revision.
2. The current Steam installation is `C:\Program Files (x86)\Steam\steamapps\common\Dyson Sphere Program`. Run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/inspect-windows.ps1 -GameRoot 'C:\Program Files (x86)\Steam\steamapps\common\Dyson Sphere Program'` from WSL. The latest version record is a lead; compare it with the visible game label. Do not copy game DLLs into git.
3. BepInEx 5.4.23.5 Windows x64 is installed in this game root. Its startup log is `BepInEx/LogOutput.log`. For another installation, follow the [official installation guide](https://docs.bepinex.dev/master/articles/user_guide/installation/) and check the scripting backend first.
4. Windows .NET SDK 8.0.425 is installed for this user at `C:\Users\ds\.dotnet\dotnet.exe`. The project restores .NET Framework reference assemblies from NuGet and builds a `net472` plugin against the local game and BepInEx DLLs.
5. The current ordinary test game uses seed `33434023`, 64 stars, 1× resources, Sandbox off, and Enemy Forces off. Keep `DSP-AI-33434023-Pristine.dsv` outside test runs and restore copies for each trial. It has an empty starting inventory; no prepared building stock or technology has been verified.

## Bootstrap build and smoke check

The plugin exposes `GET /v1/health`, bounded `GET /v1/observe`, `POST /v1/move-to-vein`, and `GET /v1/operation`. Stages A and B have visible-game comparisons on copied saves. From native PowerShell, build the shared WSL checkout:

```powershell
$repo = '\\wsl.localhost\Ubuntu\home\ds\dev\dyson-sphere-program-ai-mecha'
$game = 'C:\Program Files (x86)\Steam\steamapps\common\Dyson Sphere Program'
Set-Location -LiteralPath $repo
& "$env:USERPROFILE\.dotnet\dotnet.exe" build src\DspAgentBridge\DspAgentBridge.csproj "-p:GameManagedDir=$game\DSPGAME_Data\Managed" "-p:BepInExCoreDir=$game\BepInEx\core"
```

Copy `src/DspAgentBridge/bin/Debug/net472/DspAgentBridge.dll` to `$game\BepInEx\plugins\DspAgentBridge\`. Start DSP through Steam with `Start-Process 'C:\Program Files (x86)\Steam\steam.exe' -ArgumentList '-applaunch 1366540'`; launching `DSPGAME.exe` directly failed Steam initialization in this environment. Check the BepInEx log for `Loading [DSP Agent Bridge 0.3.0]`. Query from **native PowerShell**: `Invoke-RestMethod http://127.0.0.1:38741/v1/health` and `Invoke-RestMethod http://127.0.0.1:38741/v1/observe`. WSL's own loopback did not reach the Windows listener. Native Windows Python can also run `python -m dsp_agent observe` with `PYTHONPATH` set to the checkout's `src\Agent` directory. Health status `stage_b_unverified` describes the conservative build label, not the later visible test. A `not_loaded` observation is expected at the menu. `embedded_save_name` is not a reliable loaded filename.

## Guarded walking trial

Load a designated experiment copy in the visible game. Observe its fresh `session_id` and nearby `vein_id`; verify the planet and mecha position on screen. From native PowerShell, set `$env:PYTHONPATH` to the checkout's `src\Agent` path and use Windows Python:

```powershell
$operationId = [guid]::NewGuid().ToString('N')
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m dsp_agent move-to-vein --session-id '<observed-session-id>' --vein-id 1 --operation-id $operationId
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m dsp_agent operation --operation-id $operationId
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m dsp_agent observe
```

Replace the vein ID with one returned by that observation. The command queues one ordinary walking order only when the mecha is idle, walking, unpaused, and within 25 game units of the vein. `pending` or `running` is not success: poll the same operation ID, then compare fresh position and the visible mecha. `rejected` means no order was issued; `partial` reports the last observed position and reason, and requires a fresh observation before further action. Pausing the game interrupts an active bridge movement. Operation history is in memory, so a restart makes an unresolved ID unknown; do not automatically resubmit it. Restore the experiment copy for another trial. The physical loaded filename is not exposed by the verified game API and must be selected through the game UI.

## Optional Spherewright read-only probe

The installed DSP `0.10.35.29057` is outside released Spherewright 0.3.3's pinned `0.10.34.28529` support. The package is not installed. If a later release explicitly supports this build, follow its own instructions and run its MCP executable from the extracted package. The [research record](RESEARCH.md) owns the compatibility finding. Run this from the repository root in PowerShell after launching the copied save:

```powershell
$env:PYTHONPATH = 'src\Agent'
py -m dsp_agent spherewright-probe --exe 'C:\Path\To\Spherewright.Mcp.exe' --log 'data\episodes\spherewright-probe.log'
```

The probe reads MCP tool names, the upstream opening playbook, status, and session state. It uses no game write tool. If the executable is absent or the MCP version differs, record the result and stop this path until compatibility is checked. Compare reported game version, save state, and planet with the visible UI. The private stderr log and any raw episode stay outside git.

## Acceptance sequence

Begin with stage A in the [roadmap](../.ai/03-roadmap.md). Build the observer against local game/BepInEx DLLs, install under `BepInEx/plugins`, launch the copied save, call the loopback endpoint, compare it to the visible UI, and keep the log. Proceed to stage B only after observation is accurate. Stage C needs measured ore, power, and ingot flow. Stage D needs a visible pause and post-restart reconciliation.

## Stop and recovery

Stop the external agent first. The bridge must support pause and cancellation before mutation is enabled. If a command times out, poll its operation identity and inspect the world; do not blindly resend it. Restore a copied save to repeat an experiment. Never edit the pristine save to make an acceptance result appear successful.

## Log fields

Record the game and BepInEx versions, plugin revision, save copy, session ID, timestamp, game tick, request and response IDs, operation ID, observed outcome, screenshots/UI comparison, and log location. Raw save and episode files stay local.
