# Reward and Strategy Learning

This file owns the long-term optimization objective and the current offline reward policy. The [development roadmap](../.ai/03-roadmap.md) owns capability order; [verification](../.ai/10-verification.md) owns what counts as game evidence. Reward code cannot establish gameplay success by itself.

## Objective

The eventual optimization target is sustained white-matrix output per game tick in an ordinary, visible, continuable save. Throughput is evaluated across multiple positive production windows. Intermediate production signals help the agent find prerequisites before white matrices exist. They are not an alternate final objective. Legal ordinary gameplay, human pause/stop, and truthful evidence are hard constraints, not costs that can be traded for more throughput.

The policy ranks completed episodes lexicographically: verified white-matrix throughput first, net progress points second, and fewer elapsed game ticks third. This ordering makes any verified positive white throughput outrank a strategy that only farms early components. Before white matrices exist, the score rewards new, retained production capabilities. Progress points are the change in a bounded potential: the sum of configured signal points at the end minus the sum at the start. An already-running iron line earns no new points for producing another ingot. A stalled line loses its sustained-output signal. The point values in [`reward-policy.json`](../data/reward-policy.json) are policy parameters, not observed game quantities or recipe costs.

This uses the idea of [potential-based reward shaping](https://people.eecs.berkeley.edu/~russell/papers/icml99-shaping.pdf) to avoid endlessly paying for cycles. The formal policy-invariance theorem does not automatically apply to this partially observed, lexicographically ranked agent. The policy must be tested for reward gaming; [DeepMind's specification-gaming review](https://deepmind.google/blog/specification-gaming-the-flip-side-of-ai-ingenuity/) explains why a plausible score can still favor the wrong behavior.

## Evidence contract

`src/Agent/dsp_agent/reward.py` accepts only named proofs. A sustained-output proof needs at least two positive game-time windows attributed to an entity counter or a clean-save counter that can be attributed to the new line. A planet aggregate from an existing factory, inventory growth, a placed building, and a model assertion are not accepted as production evidence. White throughput must match its sustained-output proof. Nonproduction signals require a visible-game observation reference. A scoring adapter must establish session, item, save-copy, and entity identity before constructing these proofs. Evidence IDs point to private episode records; raw episodes stay outside Git.

The current bridge exposes only planet-wide ore and ingot totals. Those totals are useful context but cannot feed an attributed production proof on a mature save. There is no live reward feed yet, and no white-matrix game observation has been made. The two-ore manual mining test produces no reward signal for an automated iron line.

## Learning loop

1. Freeze an ordinary checkpoint and record its game version and starting state. Propose a versioned strategy change while retaining the active baseline.
2. Run baseline and candidate on separate copies of the same checkpoint. Pair trials by an exact caller-supplied trial key. Record game actions, observations, time, and proof references.
3. Score each completed episode. `RewardPolicy.compare` requires the configured minimum paired trials, identical trial keys and game version, no candidate regression, and at least one improvement.
4. `StrategyMemory` stores comparison evidence in a local SQLite database and promotes the candidate strategy ID only if the paired comparison passes. Repeating the same experiment ID is idempotent; conflicting reuse is rejected. A losing candidate remains unpromoted.
5. Keep counterexamples and test the promoted strategy on another suitable checkpoint before calling it broadly general. Revert the active strategy if later real-game evidence shows a regression.

This is strategy selection from measured episodes, not fine-tuning model weights. The code does not generate candidate strategies, control the game, or automatically run trials. Those integrations follow a verified stage C iron line and a live evidence adapter. The currently configured trial count and point values are initial policy choices to evaluate, not measured optimum values.

## Integration sequence

First finish the deterministic iron line and verify a production counter attributable to it. Then connect the existing `ProductionVerifier` to fresh game snapshots and persist private episode records. Add an adapter from verified episode records to `SignalProof` and `WhiteThroughput`, retaining session and entity identity. Run a baseline/candidate comparison on copied saves, inspect every score component, and check that repeating early mining cannot beat actual downstream progress. Only after this can model-proposed strategy variants be evaluated and promoted automatically. The agent must still obey the bounded action and pause contracts.
