# Hanoi Crossing

Two players solve their own Tower of Hanoi. They share the middle peg.

That one sentence is the whole game, and everything interesting about it follows
from the sharing. Pole 2 is the spare peg you need to solve your own puzzle, and
it is also the one place your opponent can reach — so it is simultaneously your
workspace and the place they can leave a rock in your path.

This repository is a game engine plus two frontends: a replay CLI that runs a
recorded game, and a random-play mode where two agents make uniformly random
legal moves. The rules are in [`docs/ASSIGNMENT.md`](docs/ASSIGNMENT.md); the
places where those rules were open to interpretation are decided, one paragraph
each, in [`DECISIONS.md`](DECISIONS.md).

## Install and run

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```
uv sync
uv run pytest                       # 154 tests, under a second
```

Replay a recorded game:

```
uv run hanoi-replay examples/blockade.json
uv run hanoi-replay examples/smuggle.json --json
```

Watch two random agents play:

```
uv run hanoi-random --n 3 --seed 42
uv run hanoi-random --n 2 --seed 4 --max-steps 40 --json
```

`hanoi-random` takes `--n` (disks per player, default 3), `--seed` (omit it and
one is drawn and printed, so any run can be reproduced), `--max-steps` (turns to
schedule before giving up, default 200) and `--json`.

## Input format

A replay file is a JSON object with three keys:

```json
{
  "n": 1,
  "turn_order": ["A", "B", "A"],
  "moves": ["LIFT_SOURCE", "LIFT_SOURCE", "PLACE_TARGET"]
}
```

`n` is the number of disks *per player*. `turn_order` is the external schedule —
who acts on each step, with no pattern assumed; `["A", "A", "B", "A"]` is
perfectly valid. `moves` are player-relative action names, applied in order
against that schedule.

Moves and turn order are separate lists rather than a list of pairs because the
schedule is not the player's to choose. You are handed the turn order; you only
decide what to do with your turns.

Malformed input is rejected with a message and exit code 2, never a traceback:

```
$ uv run hanoi-replay my-replay.json
hanoi-replay: moves[0]: unknown action 'JUMP' (expected: LIFT_SOURCE, LIFT_SHARED, ...)
```

Three examples ship in `examples/`: the assignment's own N=1 walkthrough, a
blockade, and a cooperative smuggle.

## Output format

Both frontends print the same thing, from the same code, because a log format
that drifts between tools is worse than useless:

```
$ uv run hanoi-replay examples/blockade.json
step  player  action         status    reason
   0  A       LIFT_SOURCE    OK        -
   1  A       PLACE_SHARED   OK        -
   2  B       LIFT_SOURCE    OK        -
   3  B       PLACE_TARGET   OK        -
   4  A       LIFT_SHARED    OK        -

final board (bottom to top)
  1a: -
   2: -
  3a: -
  1b: -
  3b: 2
  hands: A=1  B=-

stopped after 5 step(s): game ended
outcome: B_WINS
```

`status` describes the action: `OK`, `SKIPPED` or `ILLEGAL`, with `reason` set
only for the last of those. (The engine has a fourth, `GAME_OVER`, for actions
submitted after the game is decided; neither frontend can produce one, because
both stop at that point.) The game's result is a different thing entirely and
lives on the last line: `A_WINS`, `B_WINS`, `DRAW` or `UNFINISHED`.

`--json` emits the same data for machines — `n`, the step log, the final state,
why the run stopped, and the outcome:

```json
{
  "n": 1,
  "steps": [
    {"step": 0, "player": "A", "action": "LIFT_SOURCE",  "status": "OK", "reason": null},
    {"step": 1, "player": "B", "action": "LIFT_SOURCE",  "status": "OK", "reason": null},
    {"step": 2, "player": "A", "action": "PLACE_TARGET", "status": "OK", "reason": null}
  ],
  "final_state": {
    "pole_1a": [], "pole_1b": [], "pole_2": [], "pole_3a": [1], "pole_3b": [],
    "hand_a": null, "hand_b": 2, "step": 3, "outcome": "A_WINS"
  },
  "ended": "game ended",
  "outcome": "A_WINS"
}
```

That is the assignment's N=1 example: A wins on step 2 while B is still holding
disk 2, which is why `hand_b` is not null in a won position.

Note that the printed board is a god view — it shows both players' poles. That
is a property of the *replay tool*, not of the game. What a player is allowed to
see is a different type entirely; see below.

## Internal model

Five modules, 278 lines, no dependencies outside the standard library.

**A disk is its integer size.** Sizes are globally unique and parity encodes
ownership: A has the odd disks, B the even ones. So there is no `Disk` class and
no owner field — a pole is a `tuple[int, ...]`, bottom disk first. Ownership is
`size % 2`, which is also why nothing in the engine needs to track it.

**State is frozen and transitions are pure.** `apply(state, player, action)`
returns an `ActionResult`, never mutating its input:

```python
State(pole_1a, pole_1b, pole_2, pole_3a, pole_3b, hand_a, hand_b, step, outcome)
```

Five tuples, two `int | None` hands, a step index, an outcome. It round-trips
through JSON, and a property test checks that round-trip at every state reachable
by random play, not just at the start position. Immutability is not decoration:
it is what makes replay, snapshotting, cheap rollouts and thread-safety fall out
for free, which is what the assignment asks for when it says the engine must
later serve an RL loop or a many-game service unchanged.

**Actions are player-relative and there are exactly seven of them**, whatever N
is: `LIFT_SOURCE`, `LIFT_SHARED`, `LIFT_TARGET`, `PLACE_SOURCE`, `PLACE_SHARED`,
`PLACE_TARGET`, `SKIP`. `SOURCE` is your pole 1, `TARGET` your pole 3, `SHARED`
is pole 2. One policy can play either side without knowing which side it is on,
and the action space does not grow with the board.

**Illegal actions are values, not exceptions.** `apply` is total: it never
raises. An illegal action returns `status=ILLEGAL` with a typed `reason` and
burns the turn, exactly as the rules require. Legal moves are *not* masked inside
`apply` — `legal_actions(state, player)` is exposed separately, for agents that
want a mask.

**`observe(state, player)` is the whole of what a player may see**: their own
three poles, their own hand, their own disk count, and a bool for whether the
opponent is holding something — never which disk. The hiding is structural
rather than filtered: an `Observation` has no field in which the opponent's poles
could be stored, so a policy cannot cheat by accident.

The legality rules live in exactly one function, and that function takes an
`Observation`, not a `State`. `legal_actions(state, player)` is a three-line
wrapper that calls `observe` and delegates. This is not tidiness for its own
sake — it is a proof obligation discharged: whether a move is legal never depends
on anything the acting player cannot see, and the random agent playing from
observations alone is provably playing by the same rules the engine enforces.

**Turn order lives behind a `Schedule` protocol** with a single method,
`player_at(step) -> Player`. `SequenceSchedule` wraps an explicit list and raises
`IndexError` past the end; callers turn that into `UNFINISHED`. The engine is
never told whose turn it is — it is told who is acting, which is not the same
thing, and is why an irregular schedule like `[A, A, B, A, A, A]` needs no
special handling anywhere.

The engine does no I/O at all: no printing, no logging, no files, no clock, no
randomness, no globals. The frontends own every bit of that. A test asserts the
five core modules import nothing outside the standard library, and another
asserts they stay under 500 lines (currently 278).

## Rules analysis

### The shared pole is both a spare peg and a weapon

Textbook Hanoi needs three pegs: source, target, and a spare to shuffle through.
Here your spare peg is the one thing your opponent can also touch. Every disk you
park on pole 2 is a disk you had to put somewhere — and every disk *anyone* parks
there is a disk that stops *both* players from winning, because the win condition
requires that among your visible poles only pole 3 has disks, and pole 2 is
visible to both.

So parking a disk on the shared pole is a legal, deliberate blockade. It is not
free: the disk is on your critical path too, you spent a turn placing it, and
you will spend another lifting it back. But if your opponent is one move from
winning, a rock on the shared peg is the only move on the board that stops them.
This is the whole game. The Hanoi part is a solved exercise; the interesting part
is that the spare peg has another mind on it.

### You can win on your opponent's turn

The win condition is checked for **both** players after **every** action. That
follows from reading the rule as a property of a position rather than as
something you achieve on your own turn, and it produces the most striking
behaviour in the game. `examples/blockade.json` is exactly this:

```
   3  B       PLACE_TARGET   OK      B is now fully set up — but pole 2 is occupied
   4  A       LIFT_SHARED    OK      A lifts their own disk off pole 2 — and B wins
```

A had a disk parked on pole 2. B finished arranging their own side and could do
nothing more. The moment A picked their own disk back up — a move A needed to
make, since that disk had to come home eventually — the position satisfied B's
win condition and B won on A's turn. A never made a mistake in any local sense.
The blockade was load-bearing, and lifting it was fatal.

The alternative reading (check only the acting player) would mean B has to
*notice* and spend a turn skipping to claim a win they already have, which turns
the rule into a formality about attention rather than a fact about the board.

### The win condition is positional, not ownership-based

"Only pole 3 has disks" says nothing about whose disks. So a foreign disk resting
on your pole 3 does not block your win, and you do not need all N of your own
disks on it — you need your pole 1 and the shared pole clear, your hand empty,
and at least one disk on pole 3.

This makes the goal *clear your side*, not *collect your disks*, which is a
sharper and stranger objective than the ownership reading. It also means your
opponent can hand you a disk you then have to deal with, and that a disk of
yours which ends up buried on their pole 3 is simply gone from your problem.

### Therefore smuggling is legal, and it is cooperative

Put the two previous readings together and something the rules never mention
falls out. A places disk 1 on pole 2. B lifts it and buries it on 3b — legal,
since 1 was the top disk of the shared pole and 3b's top disk is larger. Disk 1
is now permanently out of A's way, and A has one fewer disk to solve.

`examples/smuggle.json` runs this at N=2. A wins using **four** of their own
turns instead of the six an uncontested solo solve would need. B gave up two
turns to do it and got nothing back, so it is not obviously good play — but it is
unambiguously legal, and it is a genuine cooperative channel between two players
who cannot otherwise communicate or see each other's boards. Two poles, one
shared, no messages: the only thing you can say to your opponent is what you
leave on pole 2.

We treat this as an emergent strategy the rules permit, not a bug to be patched.

### The solo baseline

One player alone, unbothered, is textbook Tower of Hanoi: **2^N − 1** moves to
get N disks from pole 1 to pole 3 using pole 2 as the spare. But a move here is
two actions — a lift and a place are separate turns — so an uncontested solve
costs **2(2^N − 1)** turns:

| N | Hanoi moves | turns |
|---|---|---|
| 1 | 1 | 2 |
| 2 | 3 | 6 |
| 3 | 7 | 14 |
| 4 | 15 | 30 |

Conveniently, the textbook solution ends with the spare peg empty, which is
exactly what the win condition demands. That baseline is the thing everything
else is measured against: the blockade makes it longer, smuggling makes it
shorter, and the whole game is the fight over which.

For what it's worth, two uniformly random agents do finish. Over 200 seeds at
N=3 with a 2000-turn budget, every game was decided, A winning about 58% — the
edge presumably coming from moving first.

## Tests

```
uv run pytest
```

154 tests. Beyond the unit tests for each rule and each illegal reason, the
suite includes property tests over seeded random play — disk conservation, strict
decreasing order on every pole, step-counter monotonicity, JSON round-tripping,
and determinism — driven two ways. One walk plays masked, through
`legal_actions_from`, like the random frontend. The other samples all seven
actions uniformly, so roughly half its turns are illegal, because invariants that
only hold on the happy path are not invariants. Together they check about 17,000
transitions and hit every reachable illegal reason.

The property suite was itself checked by mutation: breaking `LIFT` so it drops
the disk, removing the placement size check, and making illegal actions free
each produce failures in the tests that should catch them.

## Layout

```
src/hanoi_crossing/
  state.py          frozen State, Player, Outcome, initial_state
  actions.py        the seven-action enum
  engine.py         apply(), legality, both-player win check
  observation.py    observe() and the Observation type
  schedule.py       Schedule protocol, SequenceSchedule
  frontends/
    replay.py       hanoi-replay
    random_play.py  hanoi-random
    report.py       the step log and board format, shared by both
tests/
examples/
docs/ASSIGNMENT.md  the original brief
DECISIONS.md        the eleven interpretation calls, and what was rejected
AI_USAGE.md         what the AI tooling did, and what it did not decide
```

## What is deliberately not here

No RL environment wrapper, no server, no persistence layer, no strategy beyond
uniform random. The assignment asks that the engine be *able* to serve those
unchanged, and explicitly asks that they not be built. Purity, immutability, the
observation boundary and the schedule protocol are what make them possible; a
`gym.Env` subclass would just be a different frontend, and writing it now would
be guessing at an API nobody has asked for yet.
