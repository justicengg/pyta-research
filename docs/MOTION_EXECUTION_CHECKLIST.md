# Motion Execution Checklist

## Goal
- Keep the `Precision Glass × Quantum Topology` feel.
- Remove always-on motion that reads as lag.
- Convert the canvas into a state-driven motion system.

## Principles
1. Motion should be event-driven, not ambient-only.
2. Idle state should feel stable and readable.
3. Running state can carry more energy, but only in focused zones.
4. Converged and degraded states should settle down, not continue to perform.

## Execution Items

### 1. Background layer
- [x] Remove default infinite grid drift.
- [x] Remove default infinite ring spin.
- [x] Remove default infinite trace sweep.
- [x] Keep the topology atmosphere as static presence in idle state.
- [x] Re-enable only the lighter background signals during `running`.

### 2. Center core
- [x] Remove the always-on breathing / orbit effect from the center core.
- [x] Keep hover/edit feedback only.
- [x] Add one short `run-start` pulse instead of continuous motion.

### 3. Agent nodes
- [x] Keep entrance animation.
- [x] Keep hover/focus lift.
- [x] Move live/reused status pulse to `running` only.
- [x] Add result-arrival pulse for the updated node only.

### 4. Result cards
- [x] Keep reveal animation.
- [x] Keep loading shimmer only while running.
- [x] Keep confidence-bar breathing only while running.
- [x] Reveal animation now emphasizes newly updated cards.

### 5. Edges
- [x] Remove always-on edge drift in idle state.
- [x] Keep softer static presence in idle state.
- [x] Re-enable edge motion only during `running`.
- [ ] Later map edge emphasis to propagation events instead of whole-canvas running state.

### 6. Toolbar
- [x] Remove always-on float in idle state.
- [x] Re-enable float only during `running`.

## Next Recommended Pass
1. Keep Prompt Orb variants configurable, but treat `ai_native` as the leading candidate for future refinement.
2. Continue reducing asset heaviness before removing more motion; prefer smaller transparent assets and CSS glow over large bitmap haze.
3. Add `complete / degraded / partial` settling refinements only if they improve clarity more than they add visual noise.
4. If performance still feels heavy, reduce blur radius before removing more motion.
