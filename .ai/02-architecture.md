# Architecture and Protocol

This file owns component responsibilities and the target wire contract. Game-specific method findings belong in [research](../docs/RESEARCH.md).

```text
DSP visible client
  ↕ verified game APIs on main thread
BepInEx bridge: observation, validation, bounded execution
  ↕ versioned JSON over loopback HTTP (provisional, ADR-003)
Local agent: state, planner, journal, verification
  ↕ structured tool calls
OpenAI Responses API
```

## Current bridge

`src/DspAgentBridge` exposes loopback health and a bounded read-only `/v1/observe` route. The listener queues observation requests; `Plugin.Update()` reads game objects on the Unity thread, one request per frame, and the HTTP worker waits at most two seconds. The response caps inventory, entity, and vein scans, identifies a loaded `GameData` session, and marks truncated scans. Its returned fields have been compared with the visible UI on copied ordinary saves. It also includes local-planet all-time iron ore and ingot production totals. These cannot attribute production to one line. `POST /v1/move-to-vein` submits one nearby walking order through the game's order system. `POST /v1/mine-vein` submits a normal vein-mining order and stops after one to five iron ore are measured in inventory and depleted from the vein. Both require a session ID, an explicit operation ID, a valid vein within 25 units, an unpaused game, and an idle walking player. `GET /v1/operation` returns pending, rejected, running, completed, or partial state. Reusing the same operation ID cannot issue a second order in the current plugin process. A pause interrupts an active order and returns a partial position. Operation history is in memory; after restart, unknown outcomes require visible reconciliation before any retry.

The observer's first entity window scans up to 4096 pool indices; a separate `recent_entities` window scans at most the last 1024 in descending ID order, with exact start/end indices and result truncation. Newest-first results keep a just-built entity visible even when nearby belts fill the response cap. Neither window claims full coverage when the pool is larger. `inhand_item` reports an item held by the cursor separately from package slots, which matters when the player enters construction mode. These fields support readback after a UI construction trial; they do not authorize direct pool changes.

`src/Agent/dsp_agent` validates health, observation, and movement responses and includes a durable SQLite command journal. The journal deduplicates command keys, preserves terminal results, and marks unresolved operations for reconciliation when a session changes. The CLI currently requires the caller to supply an operation ID; it is not yet wired to that journal automatically. Fresh observation remains necessary to substantiate the outcome.

The agent also has a bounded read-only MCP stdio client for probing a compatible Spherewright installation. It negotiates MCP `2025-06-18`, lists tools, reads the upstream opening playbook, and calls only an explicit inspection allowlist. The roadmap planner selects a milestone from explicit tri-state evidence. A production verifier requires positive deltas from one game entity's cumulative counter across multiple game-time windows. A Responses API adapter can request one strictly typed proposal from a configured model; its operations are limited to inspection, planning, pausing, or reporting a blocker. The adapter does not execute the proposal or call game write tools. These planning paths have only offline test evidence. The broader construction contract below remains a design target.

An offline reward evaluator scores verified episode outcomes, and a local SQLite strategy memory promotes a candidate only after paired checkpoint trials improve without regression. One private UI-built line episode was adapted from checked entity windows and scored; no paired live trial or autonomous learning has occurred. The [reward and learning policy](../docs/REWARD-LEARNING.md) owns the objective and evidence boundary.

## Bridge

The network listener binds only to loopback. It parses and bounds requests, then queues game work. The Unity game thread reads or mutates game state. Mutation validates session, save load, planet, snapshot freshness, and game prerequisites, and returns a truthful status on partial completion. An idempotency key prevents repeated placement. Long operations expose polling and cancellation. The bridge never holds an OpenAI key.

Observations use a compact summary plus bounded `inspect_area` and `inspect_entity` detail. They include game and mod versions, session and tick, current planet/mecha, inventory, relevant technologies and recipes, nearby resources and buildings, power and production, and incomplete actions. Later scopes add technology-tree detail, exploration, logistics, storage, and flight. Stable entity IDs and explicit `unknown` values prevent false zeros and confusion across sessions.

## Agent

The proposed agent keeps a revisable strategic objective, near-term goal, and tactical experiment with predictions, issued action IDs, observations, blockers, and verified skills or counterexamples in a local journal. It submits one bounded action, observes again, records what changed and why it thinks that happened, and revises its hypothesis on mismatch. The model chooses goals and actions among validated tools; deterministic code owns game-rule checks, geometry, budgets, and evidence. Model names and call budgets are configuration, not game logic. Restoring a save invalidates assumed completion until fresh observation confirms it. A retrieved skill carries prerequisites and past failures; it is rechecked before reuse. The full [experiment contract](../docs/AI-NATIVE-RESEARCH.md#strategy-tactics-and-experiment-contract) is not yet a game-controlling agent.

`experiments.py` is the first offline piece of that contract. Its SQLite ledger records a strategic goal, near-term goal, prediction, falsifier, action intent, before/after references, outcome, and a proposed explanation. It requires an external evidence reference for achieved or failed outcomes, keeps terminal verdicts immutable, blocks new attempts while a partial or unknown attempt awaits reconciliation, and rejects an unchanged retry of a failed experiment in the same state. Retrieval currently matches near-term goal text exactly; it does not rank context or check evidence references itself. No model, verifier, bridge command, or game session is connected to this ledger yet.

## Wire contract

The target contract uses `protocol_version`, `request_id`, `session_id`, `action`, and validated `args`. Mutations additionally require `snapshot_tick` and `idempotency_key`. Responses echo request identity and include `status`, `operation_id` when relevant, observed entity IDs, error code, and a concrete next step. `plan_*` is read-only. The error vocabulary includes `not_loaded`, `wrong_planet`, `out_of_range`, `locked_tech`, `insufficient_items`, `invalid_placement`, `stale_plan`, `partial_completion`, `timeout`, and `unknown`. The exact shape evolves against the installed game version; examples in the archived spec are goals, not verified DSP signatures.

## Capability sequence

Observation starts with version, planet, position, inventory, and local entities. Walking and bounded mining are confirmed. The UI-built iron line provides a measurement baseline; a bounded ordinary construction surface is still missing. The next research gate is a self-chosen goal and action episode in a copied new game, followed by matched skill-reuse trials. Each later capability needs its own visible game acceptance result; see the [development roadmap](03-roadmap.md).
