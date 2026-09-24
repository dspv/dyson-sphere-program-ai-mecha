# Dyson Sphere Program AI Mecha

A work-in-progress BepInEx bridge and local agent intended to build and verify factories in a visible Dyson Sphere Program game. The first acceptance target is a sustained iron-ingot line on a prepared ordinary save. The [product contract](.ai/01-product.md) and [roadmap](.ai/03-roadmap.md) define the goal.

## Current status

The bridge is compiled and loaded in the Windows DSP client. Stage A observation matched visible UI checks on copied ordinary saves. Stage B issued a guarded walking order through the game's normal order API; the mecha visibly moved to an iron vein, while invalid requests and a paused partial move were reported accurately. In stage C, a bounded normal mining order visibly collected two iron ore on a copied new save. A smelter was placed and built through the ordinary UI on another copy; it had no power or recipe, so this is a construction-path trial rather than a working line. The observer now exposes held items and a bounded recent-entity window for larger factories. Agent-directed construction and factory production are not yet verified. See [build status](.ai/14-build-status.md).

| Track             | Progress |
| ----------------- | -------- |
| Documentation     | 50%      |
| Protocol          | 50%      |
| Bridge            | 50%      |
| Agent             | 0%       |
| Game verification | 50%      |

## Start here

- Developers and coding agents: [CLAUDE.md](CLAUDE.md) and [.ai/00-index.md](.ai/00-index.md).
- Windows game setup: [runbook](docs/RUNBOOK.md) and [research](docs/RESEARCH.md).
- Original request: [archived specification](docs/source-spec.txt).

Run `make check` for documentation and offline client checks. The [runbook](docs/RUNBOOK.md) gives the Windows build and installation commands. Game DLLs, saves, secrets, and raw episodes must stay out of git.
