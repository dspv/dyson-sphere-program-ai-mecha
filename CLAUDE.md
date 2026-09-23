# Dyson Sphere Program AI Mecha — Agent Context

A BepInEx bridge and local AI agent intended to play a visible, ordinary Dyson Sphere Program save through verified game actions. The first acceptance target is a measured iron-ingot production line. **Status: foundation; no game integration verified.** See [.ai/14-build-status.md](.ai/14-build-status.md).

## Start here

Read [.ai/00-index.md](.ai/00-index.md), [.ai/14-build-status.md](.ai/14-build-status.md), and [.ai/01-product.md](.ai/01-product.md). Then follow the index's task routing.

## Non-negotiable rules

1. **Never claim a gameplay milestone without a reproducible run in the visible game.** A mock or compiled DLL cannot establish that a factory works.
2. **Use ordinary game mechanics.** Do not mutate factory pools or saves, spawn resources, teleport the mecha, or treat unscouted systems as known.
3. **Keep the human able to stop the agent.** Bound commands, access game objects on the game thread, check save and planet before mutation, and report partial completion honestly.
4. **All code, commits, PR titles, descriptions, and docs are in English.** Use Conventional Commits.
5. **No invented measurements.** Mark goals as targets and unknown figures as open questions.
6. **Keep documentation current with behavior.** Update [.ai/14-build-status.md](.ai/14-build-status.md), [.ai/00-index.md](.ai/00-index.md), and README progress together.
7. **Record closed debates in [.ai/08-decisions.md](.ai/08-decisions.md).** Cross-link facts instead of copying them.
8. **Run `make docs-fmt` after editing Markdown tables and `make check` before committing.** Tables contain short values only.

## Commands

```sh
make help
make docs-fmt
make check
```
