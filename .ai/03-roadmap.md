# Development and Game Roadmaps

This file owns desired sequence. [Build status](14-build-status.md) says what exists; [verification](10-verification.md) says what evidence counts.

## Development stages

- **A — observer:** Run a mod in the actual game. Compare API version, planet, position, inventory, and a small local entity area with the visible UI.
- **B — one action:** Invoke one safe game action through the API. Verify the resulting game state and an invalid request's error.
- **C — deterministic iron line:** From the prepared save, construct a connected and powered mining-to-smelting line without a model. Verify ore transfer and sustained ingot output. Replaying must not duplicate construction.
- **D — model control:** Let the model select validated tools for the iron goal, recover from a controlled failure, support pause, and reconcile state after restart.
- **E — new save bootstrap:** Obtain blue matrices and complete related research from a new peaceful save through ordinary gathering, crafting, power, and building.
- **F — mall:** Produce bounded building stocks and demonstrate replenishment after withdrawal.
- **G — flight:** Scout, travel to a planet in the starting system, obtain titanium, and return with a safe fuel and return plan.
- **H — logistics:** Build and configure stations and vessels, then measure titanium arrival at the destination.
- **I — expansion:** Sustain purple and green matrices and establish verified resource flow beyond the starting system.
- **J — sphere:** Observe positive progress of a sphere component in the game UI.
- **K — later progression:** Sustain white matrices and separately verify `Mission Completed!`.

Stages A–D define MVP. For E–K, maintain a feature-to-game-API-to-verification-to-version record in [research](../docs/RESEARCH.md). A blocked flight or construction method stays a blocker; it must not be bypassed by editing the save.

## Game milestones

The desired graph is encoded in [`data/roadmap.json`](../data/roadmap.json), with symbolic evidence signals and no invented recipe IDs or rates. Runtime planning must use actual in-game recipe and technology dependencies, not hard-coded costs from this document. Desired milestones are: starter mining and smelting; blue science; first mall; red science; first titanium expedition; yellow science; interplanetary logistics; purple science; green science and warpers; interstellar resources; first sphere progress; white science and `Mission Completed!`. The titanium expedition precedes ILS automation because requiring ILS for the first titanium creates a circular dependency. Purple/green science, mall growth, and early sphere work may overlap when resources allow.

Each milestone needs observed prerequisites, a next feasible substep, a named blocker, and measurable `done_when`. Production must persist across multiple windows. On a zero-output window, inspect power, inputs, sorters and belts, blocked outputs, station settings, and mecha fuel as applicable. Recovery of stalled supply outranks expansion. Targets for output, stocks, and windows are configuration until checked in the installed game.

## Improving behavior

Log complete episodes and observed costs before changing strategy. Diagnose a failure, alter one strategy or threshold, and compare baseline and candidate on copies of the same checkpoint; test a second suitable save when possible. Promote a skill only after measured improvement without regressions. Cap retries and API use, and stop repeated identical blockers. Store applicability and counterexamples with skills. The episode store stays local by default; only deliberately anonymized examples enter git.

The [reward and learning policy](../docs/REWARD-LEARNING.md) defines the eventual white-matrix objective, intermediate evidence points, and paired-trial promotion rule. Its evaluator is offline-only until attributed production signals and game episodes are connected.
