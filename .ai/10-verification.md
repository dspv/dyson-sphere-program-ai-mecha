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

The optional Spherewright probe can establish only MCP connectivity, available tools, and reported session state. Compare those fields with the visible client and retain the stderr log. It does not prove a game action or production. For an iron-ingot milestone, the verifier requires an adapter to a cumulative game production counter tied to one session, planet, entity, and item. Set the window duration and required count in the experiment record; a positive inventory delta is not evidence of production. No such counter adapter has been verified against the owner's game.

## Strategy experiments

Episode comparison follows this order: legal and continuable gameplay; milestone completion; sustained output; then game time, resources, actions, and API cost. A candidate skill is tested from a restored copy of the same checkpoint as its baseline. A failure or counterexample stays in the journal and in [strategies](../docs/STRATEGIES.md) before promotion.

The offline [reward and learning policy](../docs/REWARD-LEARNING.md) narrows promotion to paired trials with attributed evidence. A score calculated from caller-supplied proofs is still an offline result until those proofs are tied to visible game observations. Inspect the source and identity of every production window before a strategy promotion is treated as gameplay learning.
