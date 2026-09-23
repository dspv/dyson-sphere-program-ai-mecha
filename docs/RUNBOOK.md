# Windows Runbook

This runbook describes the intended handoff. Current build state is in [build status](../.ai/14-build-status.md); no plugin compilation or installation has been verified.

## Development agent on Windows

Use Windows-native PowerShell with Codex or Orca so the agent can inspect the actual DSP installation. Install Git, Python, Node.js LTS, and a .NET SDK. Install Codex CLI with `npm install -g @openai/codex@latest`, run `codex` once, and sign in. Orca is optional: install its Windows app, add this repository, select Codex as the agent, and use the existing Windows Codex login. Orca runs Codex in the selected worktree; it is the development interface, not the in-game agent.

The foundation is committed locally but has not been pushed to the remote. A plain Git clone of the remote does not yet include it. Transfer the workspace archive prepared for this handoff, which includes Git history, or sync the commits before opening the project on Windows. Extract it to a Windows drive for direct access to DSP and PowerShell. From the project root, run `py -m unittest discover -s tests -v` before game setup.

## Prepare the game machine

1. Open the extracted repository on Windows. Record the Git revision.
2. Locate the DSP installation and record the version shown by the game. Run `powershell -File scripts/inspect-windows.ps1 -GameRoot "C:\Path\To\Dyson Sphere Program"` to inventory local DLLs and BepInEx. Inspect the scripting backend. Do not copy game DLLs into git.
3. Install a BepInEx distribution matching that game build using the [official installation guide](https://docs.bepinex.dev/master/articles/user_guide/installation/). Launch once and retain `BepInEx/LogOutput.log`.
4. Install a .NET SDK capable of building the provisional `net472` target. The project restores the .NET Framework reference assemblies from NuGet. Confirm the target against the local managed DLLs before extending the plugin.
5. Create a separate ordinary test save with Dark Fog disabled. Record seed, resources, version, prepared inventory, and technologies. Keep the pristine save outside test runs and restore copies for each trial.

## Bootstrap build and smoke check

The current plugin only exposes `GET http://127.0.0.1:38741/v1/health`. It cannot observe or change DSP state. Its `net472` target is provisional until the installed game's managed runtime is checked. From PowerShell, set paths to the local DLL directories and build:

```powershell
$gameManaged = 'C:\Path\To\Dyson Sphere Program\DSPGAME_Data\Managed'
$bepinexCore = 'C:\Path\To\Dyson Sphere Program\BepInEx\core'
dotnet build src/DspAgentBridge/DspAgentBridge.csproj -p:GameManagedDir="$gameManaged" -p:BepInExCoreDir="$bepinexCore"
```

If the installed runtime does not support `net472`, record that finding and change the project target before compiling. Copy `src/DspAgentBridge/bin/Debug/net472/DspAgentBridge.dll` to `BepInEx/plugins/DspAgentBridge/`, start DSP, and check the BepInEx log for the bootstrap listener line. From the repository root, query it with `curl.exe http://127.0.0.1:38741/v1/health` or `python -m dsp_agent` with `PYTHONPATH=src/Agent`. The expected status is `bootstrap_only`; it proves only that the plugin loaded and loopback transport works. Stop the game to stop the listener.

## Optional Spherewright read-only probe

If the installed DSP version matches a released Spherewright package, install that package following its own instructions and run its MCP executable from the extracted package. The [research record](RESEARCH.md) states the version and release caveats. Run this from the repository root in PowerShell after launching the copied save:

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
