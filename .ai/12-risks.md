# Risks, Assumptions, and Open Questions

Unknowns live here until evidence or an ADR closes them. A target in the [roadmap](03-roadmap.md) is not a measured capability.

## Assumptions

- **`ASSUMPTION-01` — Windows DSP is a moddable Mono build.** Falsified if the owner's installed build uses an incompatible scripting backend or BepInEx fails to load. Check the game folder and startup log before choosing a target framework.
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

- **`OQ-01` — Installed game and BepInEx versions:** Decided by inventory and logs on the owner's Windows machine. Blocks game compilation and stage A.
- **`OQ-02` — Available game DLL signatures for observation and building:** Decided by inspection of that version and a live trial. Blocks stages A–C.
- **`OQ-03` — Prepared save details, seed, resource setting, and inventory:** Decided when the owner creates the control save. Blocks the iron acceptance run.
- **`OQ-04` — Sustained output window and minimum rate:** Decided from a target set for the experiment and game measurement. Blocks final milestone judgment, not instrumentation.
- **`OQ-05` — Model/API budget and credentials:** Decided by the owner before enabling paid planning calls. Blocks stage D, not deterministic stages.

- **`OQ-06` — Reuse or extend Spherewright:** Decided by checking its released tools against the owner's game and iron-line acceptance run. Blocks committing to a game-action implementation path.

## What would falsify the plan

If a visible ordinary game client cannot be controlled through a bounded, game-rule-respecting method, the proposed bridge cannot satisfy the acceptance target. If reliable observation cannot distinguish real production from merely placed objects, the milestone cannot be honestly verified. Either result requires a new ADR and scope decision.
