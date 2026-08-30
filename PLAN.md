# PLAN.md — Hanoi Crossing

Nine milestones. Stop after each and wait for review.

---

### M1 — Skeleton + the spec's own example as a failing test

- `uv init`, `pyproject.toml` with `[project.scripts]` for `hanoi-replay` and
  `hanoi-random`, package under `src/hanoi_crossing/`.
- `tests/test_spec_example.py` encoding the assignment's N=1 walkthrough:
  turn order `[A, B, A]`, A lifts 1 from 1a, B lifts 2 from 1b, A places 1 on
  3a → A wins. It must fail for the right reason (nothing implemented yet).


---

### M2 — State and actions

- Frozen `State`: `pole_1a`, `pole_1b`, `pole_2`, `pole_3a`, `pole_3b` as
  `tuple[int, ...]` (index 0 = bottom), `hand_a`/`hand_b` as `int | None`,
  `step: int`, `outcome: Outcome` (`IN_PROGRESS` at the start).
- `Outcome` enum in `state.py`: the game result. Distinct from `ActionStatus`
  (M3), which describes a single action.
- `initial_state(n)` — odds on 1a, evens on 1b, largest at bottom.
- Seven-member player-relative `Action` enum.
- `to_dict` / `from_dict` round-trip.

Test: round-trip is identity; `initial_state(3)` has 1a = (5, 3, 1).


---

### M3 — Legality and `apply` (test-first)

- `legal_actions(state, player) -> frozenset[Action]`.
- `apply(state, player, action) -> ActionResult` — pure, returns new state.
- `ActionResult(state, status, reason)`, `ActionStatus` (`OK`, `SKIPPED`,
  `ILLEGAL`) and `IllegalReason` live in `engine.py`.
- Illegal actions: state unchanged **except** `step` advances; typed `reason`.

Tests (write these first): each of the five illegal reasons; strictly-larger
placement enforced both ways; placing on your own pole 1 allowed; lifting from
your own pole 3 allowed; illegal action does not mutate the input state object.


---

### M4 — Win detection (test-first — this is the differentiator)

- After every action, evaluate the win predicate for **both** players.
- Predicate: hand empty ∧ pole 1 empty ∧ pole 2 empty ∧ pole 3 non-empty.
- `State.outcome` values: `IN_PROGRESS`, `A_WINS`, `B_WINS`, `DRAW`,
  `UNFINISHED`.

Tests (write these first, by hand):
- **B wins on A's turn**: B has 1b empty, 3b loaded, empty hand; a disk sits on
  pole 2; A lifts it; B wins on A's action.
- Occupied shared pole blocks both players' wins.
- A foreign disk on your pole 3 does not block your win.
- Empty pole 3 with everything else clear is not a win.


---

### M5 — Schedule and observation

- `Schedule` protocol, `SequenceSchedule` backed by an explicit list.
- `observe(state, player) -> Observation`: visible poles, own hand, whether the
  opponent is holding something (not what), own disk count. Nothing else.

Test: `Observation` for A contains no reference to 1b, 3b, or B's disk identity.

---

### M6 — Replay CLI

- Reads a JSON file: `{"n": 3, "turn_order": ["A","B",...], "moves": [...]}`.
- Applies moves against the schedule, prints final state + per-step log
  (`step, player, action, status, reason`). `--json` for machine output.
- Handles: moves list shorter than schedule, illegal moves, early win.


---

### M7 — Random-play mode

- Both players sample uniformly from `legal_actions`, seeded (`--seed`).
- **Consumes `observe()` only** — assert this in review; the agent function must
  take an `Observation`, not a `State`.
- `--max-steps` guard; ends `UNFINISHED` if the schedule runs out.


---

### M8 — Property tests and the line-count guard

- Disk conservation: the multiset of all disks across poles and hands is
  invariant under `apply`.
- Stack ordering: every pole is strictly decreasing bottom-to-top, always.
- Determinism: same seed → same trace.
- Line-count guard: core engine modules under 500 non-blank, non-comment lines.


---

### M9 — Documentation

- `README.md`: install/run, input and output formats, internal model, and a
  **rules analysis** section — the shared peg as both spare and weapon, winning
  on the opponent's turn, positional win condition, cooperative smuggling.
  State that A alone is textbook Hanoi (2^N−1 moves, ×2 turns since lift and
  place are separate actions) and that the game is what happens when the spare
  peg has another mind on it.
- `DECISIONS.md`: each of the 11 locked interpretations, one paragraph each,
  with the alternative that was rejected and why.
- `AI_USAGE.md`: specific and unembarrassed — which tool, that the human wrote
  CLAUDE.md and the rule decisions, that plan mode was used, which tests were
  hand-written, where the model's output was rejected.


---

