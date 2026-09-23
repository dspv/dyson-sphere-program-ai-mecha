# Build Status

**Last updated: 2026-09-24. Phase: stage B research. Next: implement and visibly test one bounded movement order on the new game's experiment copy.** The [verification policy](10-verification.md) defines what each status means.

## Progress by track

These are coarse implementation indicators, not gameplay success rates. The same values appear in [README.md](../README.md).

| Track             | Progress | State                       |
| ----------------- | -------- | --------------------------- |
| Documentation     | 50%      | Corpus and handoff drafted  |
| Protocol          | 20%      | Offline clients under test  |
| Bridge            | 50%      | Live read-only observer     |
| Agent             | 0%       | No model-driven gameplay    |
| Game verification | 20%      | Stage A UI comparisons pass |

## Milestones

| Stage             | Status      |
| ----------------- | ----------- |
| A observer        | verified    |
| B one action      | not started |
| C iron line       | not started |
| D model control   | not started |
| E–K later roadmap | not started |

## What is true now

- The repository was a documentation template before this work. The source specification is archived in `docs/source-spec.txt`.
- WSL ext4 hosts the only checkout; native PowerShell builds it through `\\wsl.localhost\Ubuntu\home\ds\dev\dyson-sphere-program-ai-mecha`. The installed game is Mono DSP `0.10.35.29057` by its version record, with BepInEx `5.4.23.5` and user-local Windows .NET SDK `8.0.425`. [Research](../docs/RESEARCH.md) owns exact paths and evidence.
- Released Spherewright 0.3.3 pins an older DSP build and was not installed. The project bridge is the integration path for this installation (ADR-007).
- The `net472` bridge loaded through BepInEx and answered health and observer calls from native PowerShell and Windows Python. At the Steam-launched menu, `/v1/observe` returned `not_loaded`; in a copied ordinary save it returned Ancha II, the same latitude/longitude shown in the UI, an empty inventory matching the open panel, and six iron veins totaling 57,655 reserves, matching the hovered cluster. A second copied ordinary save showed positive inventory and factory belts matching the visible factory. The mature save exceeded the scan and result caps, and the response marked both limits. Stage A's returned fields have live UI comparisons; no gameplay action or production milestone is verified.
- The local HTTP and MCP clients, command journal, offline planner, production verifier, and model proposal adapter remain offline-tested. No game action, production run, or live paid model call has occurred.

## Log

### 2026-09-24 — Live observer comparison on a copied ordinary save

Created an ordinary non-sandbox game with seed `33434023`, 64 stars, 1× resources, and Enemy Forces off. Saved a pristine file outside Git and loaded a byte-identical experiment copy. The observer's planet, geographic coordinates, empty inventory, and nearby iron reserve total matched the visible UI; a pause-menu read also reported `paused=true`. The observer's `GameMain.gameName` value remained the pristine save's embedded label after loading the renamed copy, so it is being labeled as embedded name with an unknown loaded filename. Menu-demo and landing-intro false positives were fixed with a stricter ready gate. On a second copied ordinary save, the observer found 2,132 Mk.I conveyor belts in inventory, matching seven visible stacks of 300 plus one of 32. The local scan reported `proto_id=2001` belts where the visible world showed belts and a belt tooltip; it signaled both incomplete pool scanning and a 64-result cap. Session ID changed on load. Stage A is verified for these read-only fields with explicit partial-scan limits. Exact local signatures and evidence are in [research](../docs/RESEARCH.md).

### 2026-09-24 — Windows bootstrap loaded and read-only observer candidate built

Fast-forwarded from `93939f6` to `e64eae4` before changes. `make check` and 21 offline unit tests passed at that revision. Installed BepInEx 5.4.23.5 and user-local .NET SDK 8.0.425, then built the bridge against local game DLLs. The initial build failed for a missing `UnityEngine.dll` reference; after adding it, the `net472` build succeeded with zero warnings and errors. BepInEx logged the plugin load, and native PowerShell returned the health response. Direct executable launch later quit after Steam initialization failed; launching through Steam reached a responsive menu. The first observer candidate falsely classified the menu demo as a loaded save because it has a `GameData` and inventory; explicit game menu-demo flags fixed that case. The latest version record and exact signatures are in [research](../docs/RESEARCH.md).

### 2026-09-23 — Read-only MCP and offline planning foundation

Added a bounded stdio MCP client, a probe for Spherewright status and session state, a tri-state milestone planner, a counter-based production verifier, and a Responses API proposal adapter. Local tests use a fake MCP peer and mocked HTTP; no Windows executable, game session, or paid API call has been exercised. The Windows handoff now includes an optional read-only Spherewright probe.

### 2026-09-23 — Durable command recording added

Added a local SQLite journal that deduplicates commands by session and idempotency key, prevents rewriting terminal outcomes, and flags unresolved operations after a save/session change. Offline checks cover restart and reconciliation; no DSP action uses this journal yet.

### 2026-09-23 — Project documentation and research started

Converted the template into project-specific scope, architecture, roadmap, decisions, risks, and acceptance rules. Added a loopback health-only BepInEx plugin source and local Python client; three offline client checks pass. The missing local game and SDK make Windows compilation and stage A the next integration gate. No game milestone has been met.
