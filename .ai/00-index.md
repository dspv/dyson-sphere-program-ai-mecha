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

Supporting documents: [research](../docs/RESEARCH.md) owns external API findings; [runbook](../docs/RUNBOOK.md) owns installation and operation; [strategies](../docs/STRATEGIES.md) owns tested gameplay heuristics; [reward and learning](../docs/REWARD-LEARNING.md) owns the offline scoring policy and eventual optimization target.

## Current state

**Last updated: 2026-09-24. Phase: stage C partial implementation.** The project bridge builds against the local Mono game and BepInEx DLLs and has visibly verified stages A and B on copied ordinary saves. The observer reports bounded partial scans, a recent-entity window, held items, and UI-matched local-planet production totals; guarded walking and a two-ore normal mining order have visible-game checks. A single smelter was placed and built through the ordinary game UI on a copied save, but bridge-directed construction and agent-made factory production remain unverified. An offline reward scorer and strategy memory exist; live learning has not run. The exact next action and evidence are in [14-build-status.md](14-build-status.md).

## Rules of engagement

The [non-negotiable rules](../CLAUDE.md#non-negotiable-rules) apply to every task. Each game method must be tied to the installed game version and a visible test. Do not turn planned features into completed milestones because code exists. Format tables with `make docs-fmt` and validate with `make check`. Record decisions in [08-decisions.md](08-decisions.md), unknowns in [12-risks.md](12-risks.md), and evidence in [14-build-status.md](14-build-status.md).
