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

Supporting documents: [research](../docs/RESEARCH.md) owns external API findings; [runbook](../docs/RUNBOOK.md) owns installation and operation; [strategies](../docs/STRATEGIES.md) owns tested gameplay heuristics.

## Current state

**Last updated: 2026-09-23. Phase: foundation.** The corpus, health-only bridge source, local HTTP and MCP clients, journal, and offline planning components are built on macOS and tested offline. No DSP installation, Windows game version, game DLL, or live game acceptance run is available here. The exact next action and component states are in [14-build-status.md](14-build-status.md).

## Rules of engagement

The [non-negotiable rules](../CLAUDE.md#non-negotiable-rules) apply to every task. Each game method must be tied to the installed game version and a visible test. Do not turn planned features into completed milestones because code exists. Format tables with `make docs-fmt` and validate with `make check`. Record decisions in [08-decisions.md](08-decisions.md), unknowns in [12-risks.md](12-risks.md), and evidence in [14-build-status.md](14-build-status.md).
