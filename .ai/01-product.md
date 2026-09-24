# Product and Acceptance

This file owns product scope and promises. [Architecture](02-architecture.md) owns implementation; [roadmap](03-roadmap.md) owns sequencing; [verification](10-verification.md) owns evidence.

## One-liner

A self-directed local agent learns reusable ordinary-game skills in a visible Dyson Sphere Program client, using bounded actions and game measurements to check its own goals.

## Core loop

```text
visible game → bounded snapshot → self-chosen feasible goal and prediction → one bounded action → observed result → verified skill or counterexample → repeat
```

The user watches the game and can pause or stop the agent. The developer agent, in-game AI agent, and bridge are distinct components. The [AI-native research](../docs/AI-NATIVE-RESEARCH.md) owns the experimental learning loop.

## First acceptance target

On a separate prepared save in ordinary construction mode with Dark Fog disabled, the agent must locate iron, build mining, power, transport, and smelting through normal mechanics, set the recipe, and demonstrate sustained measured iron-ingot output. Prepared inventory and researched technologies may be part of the starting save. Neither bridge nor agent may create free items during the run. Record the seed, resource settings, and game version; keep the original save separate from experimental copies.

The MVP is accepted only after development stages A–D in [03-roadmap.md](03-roadmap.md) have run in the real visible client. A compiled bridge or offline test is a narrower result.

After the MVP, the desired optimization target is sustained white-matrix output. The [reward and learning policy](../docs/REWARD-LEARNING.md) defines how intermediate progress and strategy comparisons support that target; it does not change the first iron-line acceptance requirement.

## Trust contract

- A `plan_*` request only reads state and calculates an option; it never changes the world.
- The bridge validates the loaded save, session, planet, snapshot, bounds, and game prerequisites before mutation.
- Network handling queues work; game objects are accessed on the game thread.
- Each action returns an operation identity and observed result, including partial completion.
- Unknown information stays unknown; unscouted systems never appear as explored facts.
- The OpenAI key stays in the external process, never inside the game or bridge config.
- The human can pause, resume, cancel an operation, or stop the process.

## Scope boundary

Combat and technology dependent on Dark Fog drops are excluded. High-frequency keyboard control, direct save editing, injected resources, hidden-map reads, and arbitrary C# execution from the model are excluded. [03-roadmap.md](03-roadmap.md) describes desired later capabilities, not MVP claims.
