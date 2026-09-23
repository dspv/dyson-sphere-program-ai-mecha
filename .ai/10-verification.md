# Verification and Evidence

This file owns acceptance evidence. [Build status](14-build-status.md) records which checks have passed.

## Evidence levels

- **Documentation:** Sources and constraints are recorded. No code or game behavior is implied.
- **Offline:** Schemas and deterministic logic pass local tests. This does not prove the bridge loads in DSP.
- **Game loaded:** BepInEx log shows the plugin in a named game version and save; API observations match the visible UI.
- **Game acted:** A command causes a visible change through ordinary mechanics and a fresh observation confirms it.
- **Milestone verified:** A complete production or travel goal meets its `done_when` over several game-time windows, with a reproducible episode.

## Windows handoff evidence

For each run, record game version, plugin build, BepInEx version, save seed and resource setting, Dark Fog setting, copy identifier, session ID, commands and responses, game tick before and after, relevant screenshots or UI observations, BepInEx log, and any known mismatch. Keep the pristine starting save untouched. Do not commit saves, game DLLs, secrets, or raw private episodes.

The first Windows check is stage A: build against that installation's managed DLLs and BepInEx libraries, install the plugin, launch a copied test save, call the observer API, and compare every returned field with the game. Stop at the first uncertain signature and update [research](../docs/RESEARCH.md). Stage B and later require separate evidence.

## Strategy experiments

Episode comparison follows this order: legal and continuable gameplay; milestone completion; sustained output; then game time, resources, actions, and API cost. A candidate skill is tested from a restored copy of the same checkpoint as its baseline. A failure or counterexample stays in the journal and in [strategies](../docs/STRATEGIES.md) before promotion.
