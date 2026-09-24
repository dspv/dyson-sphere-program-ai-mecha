# Dyson Sphere Program AI Mecha

A research project for a self-directed agent that learns reusable gameplay skills in a visible Dyson Sphere Program game. The [AI-native research](docs/AI-NATIVE-RESEARCH.md) defines the experimental approach; the [product contract](.ai/01-product.md) defines the gameplay boundary.

## Current status

The bridge has loaded in the Windows DSP client, and stages A and B have visible checks on copied ordinary saves. An ordinary UI-built iron line produced ingots in two measured game-time windows. The bridge confirmed one valid Arc Smelter preview into a visible building on a copied save and rejected a colliding preview; selecting the site and item still required the game UI. The agent uses the signed-in Codex CLI without an API key. On copied saves, the model chose exact entity inspections, guarded mining actions, and a walk. A visible status window shows the worker's state and has a stop button; its first 12-attempt run reached its limit and stopped after six mines, five entity reads, and one walk. Checked snapshots and a bridge operation established one live iron inventory change `7→12` that was initially misclassified by a planning-time budget; the ledger was reconciled and the budget now uses the action's bridge start tick. A later UI-prepared smelter build request was rejected with `build_conditions_changed`. Stages C and D remain partial: autonomous construction, factory production, and demonstrated learning remain open. The optional Responses API adapter remains fake-tested. The [AI-native research](docs/AI-NATIVE-RESEARCH.md) defines the model-chosen goal loop; see [build status](.ai/14-build-status.md) for evidence.

| Track             | Progress |
| ----------------- | -------- |
| Documentation     | 50%      |
| Protocol          | 50%      |
| Bridge            | 50%      |
| Agent             | 25%      |
| Game verification | 50%      |

## Start here

- Developers and coding agents: [CLAUDE.md](CLAUDE.md) and [.ai/00-index.md](.ai/00-index.md).
- Windows game setup: [runbook](docs/RUNBOOK.md) and [research](docs/RESEARCH.md).
- Original request: [archived specification](docs/source-spec.txt).

Run `make check` for documentation and offline client checks. The [runbook](docs/RUNBOOK.md) gives the Windows build and installation commands. Game DLLs, saves, secrets, and raw episodes must stay out of git.
