# Dyson Sphere Program AI Mecha — Documentation Map

The project aims to let a local agent plan and verify actions in a visible Dyson Sphere Program client through a bounded BepInEx bridge. The first game acceptance target is an autonomous iron-ingot line on a prepared, ordinary save. Later milestones cover research, logistics, other planets, and the Dyson sphere. The [archived source specification](../docs/source-spec.txt) preserves the request; this corpus owns current decisions and status.

| File                                     | Owns                            | Read when             |
| ---------------------------------------- | ------------------------------- | --------------------- |
| [01-product.md](01-product.md)           | Scope and trust contract        | Always                |
| [02-architecture.md](02-architecture.md) | Components and protocol         | Building software     |
| [03-roadmap.md](03-roadmap.md)           | Development and game milestones | Planning features     |
| [08-decisions.md](08-decisions.md)       | Accepted ADRs                   | Revisiting choices    |
| [10-verification.md](10-verification.md) | Evidence and experiments        | Testing gameplay      |
| [12-risks.md](12-risks.md)               | Assumptions and open questions  | Expanding scope       |
| [14-build-status.md](14-build-status.md) | Current implementation          | Checking actual state |

Supporting documents: [research](../docs/RESEARCH.md) owns game API findings; [AI-native research](../docs/AI-NATIVE-RESEARCH.md) compares agent approaches and owns the first self-directed experiment; [runbook](../docs/RUNBOOK.md) owns installation and operation; [strategies](../docs/STRATEGIES.md) owns tested gameplay heuristics; [reward and learning](../docs/REWARD-LEARNING.md) owns the offline scoring policy and eventual optimization target.

## Current state

**Last updated: 2026-09-24. Phase: stage C partial implementation and AI-native experiment groundwork.** The project bridge builds against the local Mono game and BepInEx DLLs and has visibly verified stages A and B on copied ordinary saves. On a copy of a new ordinary game, an ordinary UI-built miner, belt, powered sorter, and smelter produced iron ingots over two measured game-time windows; the exact entity counter and visible panel agreed. Bridge-directed construction and self-directed gameplay remain unverified; a new read-only construction-preview route has compiled but has no visible-game check. One private episode was scored; an offline goal ledger with observed-context retrieval, one-attempt runner, mocked Responses API adapter, and fake-tested bridge action adapter are implemented. No live model decision through this runner, paired strategy trial, or demonstrated learning exists. The [AI-native research](../docs/AI-NATIVE-RESEARCH.md) defines the experimental direction; the exact evidence is in [14-build-status.md](14-build-status.md).

## Rules of engagement

The [non-negotiable rules](../CLAUDE.md#non-negotiable-rules) apply to every task. Each game method must be tied to the installed game version and a visible test. Do not turn planned features into completed milestones because code exists. Format tables with `make docs-fmt` and validate with `make check`. Record decisions in [08-decisions.md](08-decisions.md), unknowns in [12-risks.md](12-risks.md), and evidence in [14-build-status.md](14-build-status.md).
