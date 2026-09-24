# Dyson Sphere Program AI Mecha

A research project for a self-directed agent that learns reusable gameplay skills in a visible Dyson Sphere Program game. The [AI-native research](docs/AI-NATIVE-RESEARCH.md) defines the experimental approach; the [product contract](.ai/01-product.md) defines the gameplay boundary.

## Current status

The bridge is compiled and loaded in the Windows DSP client. Stages A and B have visible checks on copied ordinary saves. An ordinary UI-built iron line produced ingots in two measured game-time windows, but the agent has not built it through bridge commands. Stage C remains partial, and no self-directed gameplay or demonstrated learning has occurred. An offline ledger and one-attempt runner now record goals, predictions, outcomes, and memory references; a structured model adapter is tested with fake HTTP responses. No live model decision or game adapter is connected. The [AI-native research](docs/AI-NATIVE-RESEARCH.md) defines the model-chosen goal loop; see [build status](.ai/14-build-status.md) for evidence.

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
