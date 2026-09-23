# Build Status

**Last updated: 2026-09-23. Phase: foundation. Next: inventory the owner's Windows DSP installation, compile and load the bootstrap, then implement stage A against its verified DLLs.** The [verification policy](10-verification.md) defines what each status means.

## Progress by track

These are coarse implementation indicators, not gameplay success rates. The same values appear in [README.md](../README.md).

| Track             | Progress | State                          |
| ----------------- | -------- | ------------------------------ |
| Documentation     | 50%      | Corpus and handoff drafted     |
| Protocol          | 20%      | Offline foundation in progress |
| Bridge            | 0%       | No compiled or loaded plugin   |
| Agent             | 0%       | No model-driven gameplay       |
| Game verification | 0%       | No client available here       |

## Milestones

| Stage             | Status      |
| ----------------- | ----------- |
| A observer        | not started |
| B one action      | not started |
| C iron line       | not started |
| D model control   | not started |
| E–K later roadmap | not started |

## What is true now

- The repository was a documentation template before this work. The source specification is archived in `docs/source-spec.txt`.
- macOS inspection found no DSP install or `dotnet` command in the local path. The target game runs on the owner's separate Windows client.
- Public BepInEx, BuildToolOpt, BlueprintTweaks, and Spherewright sources provide research leads; no installed game signature has been verified. Spherewright may supply the guarded game action surface, pending Windows compatibility checks.
- The read-only bridge bootstrap source, local client, and durable command journal exist. A desired, non-executable milestone graph is encoded in `data/roadmap.json`. The bridge has not been compiled or loaded; offline checks pass. This is not a working game mod.

## Log

### 2026-09-23 — Durable command recording added

Added a local SQLite journal that deduplicates commands by session and idempotency key, prevents rewriting terminal outcomes, and flags unresolved operations after a save/session change. Offline checks cover restart and reconciliation; no DSP action uses this journal yet.


### 2026-09-23 — Project documentation and research started

Converted the template into project-specific scope, architecture, roadmap, decisions, risks, and acceptance rules. Added a loopback health-only BepInEx plugin source and local Python client; three offline client checks pass. The missing local game and SDK make Windows compilation and stage A the next integration gate. No game milestone has been met.
