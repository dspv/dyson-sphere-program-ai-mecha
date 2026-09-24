# Risks, Assumptions, and Open Questions

Unknowns live here until evidence or an ADR closes them. A target in the [roadmap](03-roadmap.md) is not a measured capability.

## Assumptions

- **`ASSUMPTION-02` — A game-supported construction path can automate the iron line.** Falsified if the installed build exposes no controllable placement route that obeys inventory, construction range, and drone rules. Inspect build tools and run a single-object trial.
- **`ASSUMPTION-03` — A prepared ordinary save can hold the needed items and research without weakening acceptance.** Falsified if the controlled setup changes mechanics or cannot be reproduced from a documented save copy.
- **`ASSUMPTION-04` — Loopback HTTP works in the installed Mono runtime.** Falsified by listener startup failure, unresponsive polling, or measured game stalls. ADR-003 permits a transport change.

## Risks

**`RISK-01` — Game API drift.** Public mod examples may target other builds. The bridge could compile yet read the wrong fields or corrupt an operation. Pin the actual game version and validate every method against its DLL and a copied save.

**`RISK-02` — False success from placement.** A building can exist without power, input, output, or production. Require several production windows and observed item flow before marking the iron goal complete.

**`RISK-03` — Duplicate or partial mutations.** A retry after timeout can place extra entities or hide half-built lines. Require idempotency keys, stable operation IDs, polling, and a partial-completion report.

**`RISK-04` — Unsafe travel.** Fuel, visibility, and return feasibility can fail after takeoff. Keep flight out of MVP and require a verified route and fuel budget before later execution.

**`RISK-05` — Strategy overfitting.** A lesson from one save can degrade another. Compare a baseline and candidate from checkpoint copies, retain counterexamples, and gate skill promotion on observed improvement.

## Open questions

- **`OQ-02` — Behavior of installed building signatures:** Ordinary UI construction produced a physical iron line, but bridge-directed placement, belt routing, sorter endpoints, and replay-safe construction are still unverified. Inspect and test the installed build-tool path on a copied checkpoint. Blocks autonomous stage C.
- **`OQ-03` — Reproducible ordinary bootstrap:** A pristine ordinary seed `33434023` save and a later iron-line checkpoint exist. Mining, crafting, and research were performed through normal gameplay, but their complete action sequence is not yet programmatically reproducible. Blocks autonomous new-save progression.
- **`OQ-04` — Sustained output window and minimum rate:** Decided from a target set for the experiment and game measurement. Blocks final milestone judgment, not instrumentation.
- **`OQ-05` — Model/API budget and credentials:** Decided by the owner before enabling paid planning calls. Blocks stage D, not deterministic stages.

- **`OQ-07` — Counter behavior after a recipe change:** The exact Arc Smelter iron cycle counter matched visible ingot output across two windows, output withdrawal, and one checkpoint reload after the game update. Recipe-switch behavior remains unknown. Keep the adapter restricted to the checked recipe and require a fresh baseline after each load.
- **`OQ-09` — Reliable loaded-file identity:** `GameMain.gameName` is an embedded label and retained the pristine name after loading a renamed copy. No verified installed API reports the physical loaded filename. Stage B actions must require a fresh session and user-designated experiment context without treating the embedded name as proof of file identity.
- **`OQ-10` — Operation identity after restart:** Stage B's movement operation cache is bounded and in memory. A restart loses it, so the local journal and fresh world observation must reconcile any unresolved action before retry. Stage C construction needs stronger duplicate prevention across restarts.
- **`OQ-11` — Paired live strategy learning:** One private UI-built iron-line episode was scored from exact entity windows, and its two progress points did not promote a strategy. Baseline and changed strategies have not been run on matched checkpoint copies. Complete the configured paired trials, inspect score components and regressions, and test policy gaming before enabling promotion.

- **`OQ-12` — AI-native action and transfer test:** A model has not chosen or executed a gameplay goal in DSP. The bridge has no ordinary construction command. Test a bounded construction surface, then compare model-chosen experiments with and without retrieved skills on matched copies and another seed. The design is in [AI-native research](../docs/AI-NATIVE-RESEARCH.md).

## What would falsify the plan

If a visible ordinary game client cannot be controlled through a bounded, game-rule-respecting method, the proposed bridge cannot satisfy the acceptance target. If reliable observation cannot distinguish real production from merely placed objects, the milestone cannot be honestly verified. Either result requires a new ADR and scope decision.
