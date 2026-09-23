# Build Status

**Last updated: 2026-09-24. Phase: stage C research. Next: verify a single-entity iron-smelter counter and normal mining/construction APIs, prepare ordinary materials on a copied save, then build one connected iron segment.** The [verification policy](10-verification.md) defines what each status means.

## Progress by track

These are coarse implementation indicators, not gameplay success rates. The same values appear in [README.md](../README.md).

| Track             | Progress | State                      |
| ----------------- | -------- | -------------------------- |
| Documentation     | 50%      | Corpus and handoff drafted |
| Protocol          | 50%      | Live operation polling     |
| Bridge            | 50%      | Observer and walking order |
| Agent             | 0%       | No model-driven gameplay   |
| Game verification | 50%      | Stages A and B visible     |

## Milestones

| Stage             | Status      |
| ----------------- | ----------- |
| A observer        | verified    |
| B one action      | verified    |
| C iron line       | research    |
| D model control   | not started |
| E–K later roadmap | not started |

## What is true now

- The repository was a documentation template before this work. The source specification is archived in `docs/source-spec.txt`.
- WSL ext4 hosts the only checkout; native PowerShell builds it through `\\wsl.localhost\Ubuntu\home\ds\dev\dyson-sphere-program-ai-mecha`. The installed game is Mono DSP `0.10.35.29057` by its version record, with BepInEx `5.4.23.5` and user-local Windows .NET SDK `8.0.425`. [Research](../docs/RESEARCH.md) owns exact paths and evidence.
- Released Spherewright 0.3.3 pins an older DSP build and was not installed. The project bridge is the integration path for this installation (ADR-007).
- The `net472` bridge loaded through BepInEx and answered health and observer calls from native PowerShell and Windows Python. At the Steam-launched menu, `/v1/observe` returned `not_loaded`; in a copied ordinary save it returned Ancha II, the same latitude/longitude shown in the UI, an empty inventory matching the open panel, and six iron veins totaling 57,655 reserves, matching the hovered cluster. A second copied ordinary save showed positive inventory and factory belts matching the visible factory. The mature save exceeded the scan and result caps, and the response marked both limits. Stage A's returned fields have live UI comparisons.
- The first project-owned action, a bounded walking order to a nearby vein, visibly moved the mecha on the new game's experiment copy. Invalid vein and stale-session requests were rejected; replaying the same operation ID returned its prior result. Pausing a second move returned a partial result and stopped the order. This verifies stage B only. The MCP client, journal, offline planner, production verifier, and model proposal adapter remain offline-tested; no production run or live paid model call has occurred.
- The observer now exposes local-planet all-time produced counters for iron ore and iron ingots. Both matched the visible Production Statistics totals on an active copied save, allowing for one item produced between the game-thread read and UI hover. These planet-wide counters include pre-existing production and cannot prove a specific new iron line. The candidate per-assembler total was withheld because it has no visible UI check yet.

## Log

### 2026-09-24 — Planet production counters checked against the visible UI

On the copied existing save, the bridge's `FactoryProductionStat.productPool[index].total[6]` reported iron ore item `1001` total `321,414` at tick `5,296,509`; the visible Production Statistics panel showed `321,415` on the subsequent hover. Iron ingot item `1101` was `259,131` at tick `5,307,227`, followed by `259,132` in the UI. Each one-item difference is consistent with the active factory advancing between reads. These are local-planet totals, not output from an identified line. A candidate per-assembler output total was removed from the API pending a visible comparison. No mining, construction, or line production was performed by this agent.

The finalized DLL built against the local game and BepInEx assemblies with zero warnings/errors, was installed, and was loaded through Steam. On the copied existing save, the finalized `/v1/observe` returned `status=ok`, planet `? Leonis Minoris III`, and local ore/ingot totals `319,948`/`256,950` at tick `5,274,516`; the unused candidate `/v1/entity` route returned HTTP 404. `make check` passed 23 offline tests. The earlier UI tooltip comparisons establish the counter semantics; this later response establishes that the trimmed DLL still runs in the visible game.

### 2026-09-24 — Stage B walking action verified in the visible game

Built bridge `0.3.0` against the installed game and BepInEx DLLs with zero warnings/errors and loaded it through Steam. On the byte-identical seed `33434023` experiment copy, a command to vein ID 1 used `Player.Order(OrderNode.MoveTo(...), false)` and completed from tick `14930` to `15146`. The response moved from `(181.77948, -5.71299, 87.05093)` to `(173.272583, 1.52417254, 103.055573)` near the target `(172.380371, 1.71512282, 103.146187)`. The visible mecha stood beside the iron cluster; the geographic UI changed from `1°37′ S, 115°35′ E` to `0°29′ N, 120°51′ E`, matching fresh observation. Invalid vein ID `999999` returned `rejected/invalid_vein`; a wrong session returned `rejected/session_mismatch`. Repeating the completed operation ID returned its original result without a new order. After reloading the copy, a second move was paused after nine game ticks: it returned `partial/paused` with a changed position, and the mecha remained stopped after resuming. `make check` passed 23 offline tests, but those tests alone would not establish this gameplay result. No save or factory pool was edited directly.

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
