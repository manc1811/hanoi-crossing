# CLAUDE.md — Hanoi Crossing

Project instructions. These decisions are **locked**. If you think one is wrong,
say so and stop — do not silently implement a different semantics.

---

## 1. What this is

A Python game engine for "Hanoi Crossing" plus two
frontends: a replay CLI and a random-play mode. Scope discipline matters more than 
feature count.

## 2. The rules (restated)

Authoritative source: `docs/ASSIGNMENT.md`. The restatement below is a working
summary — if the two disagree, the assignment wins.

Two players, A and B. Each has three poles. Pole 2 is **shared** and visible to
both. A sees `1a – 2 – 3a`. B sees `1b – 2 – 3b`. Neither can see the other's
poles 1 and 3, nor what the other holds.

- A starts with odd-sized disks (1, 3, 5, …) stacked on `1a`, largest at bottom.
- B starts with even-sized disks (2, 4, 6, …) stacked on `1b`.
- Placement rule: a disk may go only on an empty pole or on a **strictly
  larger** disk.
- One action per turn: `LIFT` (top disk of a visible pole → hand), `PLACE`
  (held disk → visible pole), or `SKIP`.
- At most one disk in hand.
- Either player may lift from the shared pole.
- An illegal action leaves state unchanged but **consumes the turn**.
- Turn order is an external sequence. The engine must assume **no pattern**.

**Win:** a player wins when their hand is empty and, among their visible poles,
only pole 3 has disks.

## 3. Locked rule interpretations

These are the "be creative, make a decision" points. Implement exactly these and
mirror each one in `DECISIONS.md` with its rationale.

1. **Win is checked for BOTH players after EVERY action**, not just the acting
   player. Consequence: a player can win on the opponent's turn — e.g. B is
   fully set up but blocked by a disk on pole 2; the instant A lifts that disk,
   B wins. This is the central non-obvious reading of the spec.
2. **The shared pole must be empty for either player to win.** Therefore parking
   a disk on pole 2 is a legal, deliberate blockade. This is the core tension:
   pole 2 is both your spare peg and your weapon.
3. **The win condition is positional, not ownership-based.** "Only pole 3 has
   disks" — so a foreign disk resting on your pole 3 does not block your win,
   and you do not need all N of your own disks there.
4. **Consequence of (3): cooperative smuggling is legal.** A places disk 1 on
   pole 2; B lifts it and buries it on 3b (legal — 1 sits on 2). A now has one
   fewer disk to solve. Document this as an emergent strategy the rules permit,
   not as a bug.
5. **Pole 3 must be non-empty to win.** "Only pole 3 has disks" implies at least
   one. Makes total giveaway a losing line.
6. **Placing onto your own pole 1 is legal.** Nothing forbids it and real Hanoi
   maneuvering needs it.
7. **Simultaneous win → `DRAW`.** Define it for totality. Note in DECISIONS.md
   that we believe it is unreachable from a standard start (a `PLACE` cannot
   change the opponent's poles, and a `LIFT` that empties pole 2 fills the
   lifter's hand), and invite the reader to disprove it. State it as a
   conjecture, not a proof.
8. **Illegal actions are typed, not exceptions.** Return an
   `ActionResult(state, status, reason)` where `status: ActionStatus` is `OK`,
   `SKIPPED` or `ILLEGAL`, and `reason` is set only when `ILLEGAL`, from the enum
   `EMPTY_POLE`, `HAND_FULL`, `HAND_EMPTY`, `SIZE_VIOLATION`, `POLE_NOT_VISIBLE`.
   `SKIP` is distinct from an illegal action in the log. `status` describes the
   action; the game result is separate and lives on `State.outcome`.
9. **Hidden information:** a player can see *that* the opponent holds a disk but
   not *which*. Rationale: you can observe a disk vanish from the shared pole
   anyway. A player knows their own disk count, not the opponent's.
10. **Schedule exhaustion:** if the turn sequence runs out with no winner, the
    game ends in terminal state `UNFINISHED`. Never crash, never loop forever.
11. **Step counter always advances**, including on illegal actions and skips.

## 4. Architecture — non-negotiable

The spec says the engine must serve **unchanged** as (a) the environment core of
an RL loop and (b) a service holding many concurrent games. Do not build either.
Do make these true:

- **Immutable state, pure transition.** `apply(state, player, action) ->
  ActionResult`. Frozen dataclasses, no mutation. This buys replay, snapshotting,
  cheap rollouts and thread-safety for free.
- **Zero I/O in the engine.** No printing, no logging, no file access, no
  globals, no clock, no randomness. Frontends own all of that.
- **A disk is its integer size.** Sizes are globally unique; parity encodes
  ownership. No owner field. State = five int-tuples + two optional ints + a step
  index. Must round-trip through JSON.
- **Player-relative action space.** Seven actions, identical for both players and
  fixed regardless of N: `LIFT_SOURCE`, `LIFT_SHARED`, `LIFT_TARGET`,
  `PLACE_SOURCE`, `PLACE_SHARED`, `PLACE_TARGET`, `SKIP`. One policy can play
  either side.
- **Do not mask illegal actions inside `apply`.** Every action is representable;
  illegal ones burn a turn. Expose `legal_actions(state, player)` separately for
  agents that want masking.
- **`observe(state, player) -> Observation`** returns only visible poles and own
  hand. The random player must consume **only** this — never the full state. The
  spec explicitly asks for this; a random player reading god-state fails the brief.
- **Turn order behind a `Schedule` protocol** with `player_at(step) -> Player`,
  backed by an explicit sequence. Supports `[A, A, B, A, A, A]`.

## 5. Layout

```
pyproject.toml                       # uv; [project.scripts] hanoi-replay, hanoi-random
src/hanoi_crossing/
  state.py          # frozen State, Pole, Player
  actions.py        # 7-action enum
  engine.py         # apply(), legality, both-player win check
  schedule.py
  observation.py
  frontends/replay.py
  frontends/random_play.py
tests/
examples/n1_spec_example.json        # the assignment's own N=1 example
examples/blockade.json               # B wins when A lifts off pole 2
examples/smuggle.json                # cooperative handoff
README.md  DECISIONS.md  AI_USAGE.md
```

## 6. Code conventions

- Python 3.11+. Full type hints. `from __future__ import annotations`.
- Core engine (`state.py + actions.py + engine.py + observation.py + schedule.py`)
  **under 500 lines total**, excluding blank lines and comments. A test asserts this.
- No classes that aren't carrying state or a protocol. No abstract base class
  hierarchies. No plugin registries. No dependency injection framework.
- Standard library only in the engine. `pytest` for tests. `hypothesis` only if
  it earns its place in under 20 lines.
- Docstrings on public functions, terse. No commented-out code.


## 8. Working protocol

- Follow `PLAN.md` milestone by milestone. One milestone, one commit.
- **Stop after each milestone and wait for review.** Do not run ahead.
- For milestones 3 and 4, write the test first, show it failing, then implement.
- Never `git push`, never rewrite history, never squash, never amend. Commit only
  when explicitly asked. **Do not propose a commit message** — the human writes it
  after reviewing the diff.
- If a rule in section 3 conflicts with something you want to do, raise it.
