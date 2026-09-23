# Dyson Sphere Program AI Mecha

A work-in-progress BepInEx bridge and local agent intended to build and verify factories in a visible Dyson Sphere Program game. The first acceptance target is a sustained iron-ingot line on a prepared ordinary save. The [product contract](.ai/01-product.md) and [roadmap](.ai/03-roadmap.md) define the goal.

## Current status

Read-only bootstrap source, a local client, and a durable command journal exist, but no plugin has been compiled or loaded in the game, and no gameplay milestone has been verified. This repository is being prepared on macOS; integration must run against the owner's Windows DSP installation. See [build status](.ai/14-build-status.md).

| Track             | Progress |
| ----------------- | -------- |
| Documentation     | 50%      |
| Protocol          | 20%      |
| Bridge            | 0%       |
| Agent             | 0%       |
| Game verification | 0%       |

## Start here

- Developers and coding agents: [CLAUDE.md](CLAUDE.md) and [.ai/00-index.md](.ai/00-index.md).
- Windows game setup: [runbook](docs/RUNBOOK.md) and [research](docs/RESEARCH.md).
- Original request: [archived specification](docs/source-spec.txt).

Run `make check` for documentation and offline client checks. The [runbook](docs/RUNBOOK.md) gives the Windows build and installation commands. Game DLLs, saves, secrets, and raw episodes must stay out of git.
