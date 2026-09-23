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

## Current bootstrap

`src/DspAgentBridge` currently exposes only a loopback health response with `bootstrap_only` status. `src/Agent/dsp_agent` validates that response and includes a durable SQLite command journal. The journal deduplicates command keys, preserves terminal results, and marks unresolved operations for reconciliation when a session changes. It does not prove a game action succeeded without a fresh bridge observation.

The agent also has a bounded read-only MCP stdio client for probing a Spherewright installation. It negotiates MCP `2025-06-18`, lists tools, reads the upstream opening playbook, and calls only an explicit inspection allowlist. The roadmap planner selects a milestone from explicit tri-state evidence. A production verifier requires positive deltas from one game entity's cumulative counter across multiple game-time windows. A Responses API adapter can request one strictly typed proposal from a configured model; its operations are limited to inspection, planning, pausing, or reporting a blocker. The adapter does not execute the proposal or call game write tools. All of these paths have only offline test evidence. The gameplay contract below remains a design target; no project-owned observation or action route exists yet.

## Bridge

The network listener binds only to loopback. It parses and bounds requests, then queues game work. The Unity game thread reads or mutates game state. Mutation validates session, save load, planet, snapshot freshness, and game prerequisites, and returns a truthful status on partial completion. An idempotency key prevents repeated placement. Long operations expose polling and cancellation. The bridge never holds an OpenAI key.

Observations use a compact summary plus bounded `inspect_area` and `inspect_entity` detail. They include game and mod versions, session and tick, current planet/mecha, inventory, relevant technologies and recipes, nearby resources and buildings, power and production, and incomplete actions. Later scopes add technology-tree detail, exploration, logistics, storage, and flight. Stable entity IDs and explicit `unknown` values prevent false zeros and confusion across sessions.

## Agent

The agent keeps a goal, bounded candidate plans, issued action IDs, observations, blockers, and next goal in a local journal. It submits one action or a small dependent group, observes again, and replans on mismatch. The model selects among validated tools; deterministic code owns geometry, placement checks, and retries. Model names and call budgets are configuration, not game logic. Restoring a save invalidates assumed completion until fresh observation confirms it.

## Wire contract

The target contract uses `protocol_version`, `request_id`, `session_id`, `action`, and validated `args`. Mutations additionally require `snapshot_tick` and `idempotency_key`. Responses echo request identity and include `status`, `operation_id` when relevant, observed entity IDs, error code, and a concrete next step. `plan_*` is read-only. The error vocabulary includes `not_loaded`, `wrong_planet`, `out_of_range`, `locked_tech`, `insufficient_items`, `invalid_placement`, `stale_plan`, `partial_completion`, `timeout`, and `unknown`. The exact shape evolves against the installed game version; examples in the archived spec are goals, not verified DSP signatures.

## Capability sequence

Observation starts with version, planet, position, inventory, and local entities. Then one safe mutation is confirmed. Next comes a deterministic iron line, and only then model-directed construction. Research, mall, travel, logistics, and sphere capabilities follow the [development roadmap](03-roadmap.md) and each needs its own game acceptance result.
