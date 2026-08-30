# Decisions

The assignment says: where the rules are open to interpretation, be creative,
make a decision, document it. These are the eleven places we found, what we
chose, and what we turned down.

They are listed in the order they appear in `CLAUDE.md` §3, which is where they
were written down — before any of the engine existed, so that the code could be
held to them rather than the other way round.

---

## 1. The win condition is checked for both players after every action

After every action we evaluate the win predicate for A and for B, not just for
whoever moved. This is the central non-obvious reading in the whole project, and
everything interesting downstream depends on it.

The consequence is that you can win on your opponent's turn. B finishes setting
up but is blocked by a disk sitting on the shared pole; the instant A lifts that
disk — for their own reasons, on their own turn — the position satisfies B's win
condition and B wins. `examples/blockade.json` plays this out in five steps.

**Rejected:** checking only the acting player. It reads naturally, but it makes
winning a matter of noticing. B, already in a won position, would have to spend a
turn on a `SKIP` to claim it, and would lose if the schedule never came back
round to them. That turns the win condition from a fact about the board into an
administrative formality, and it quietly makes the turn order — which the
assignment insists is external and patternless — part of who wins.

## 2. The shared pole must be empty for either player to win

Pole 2 is visible to both players, so "among their visible poles, only pole 3 has
disks" includes it for both of them. A disk on the shared pole therefore blocks
*both* players from winning, whoever put it there and whoever owns it.

This is the decision that gives the game its shape. Parking a disk on pole 2 is a
legal, deliberate blockade — the only defensive move in the game. It costs you a
turn to place and a turn to retrieve, and the disk is in your own way too, so it
is a real trade rather than a free spoiler.

**Rejected:** treating pole 2 as neutral ground that only its owner's win
condition cares about, or not at all. Both readings need you to add a notion of
ownership to a pole the rules describe as shared, and both delete the only
interaction between the two players that the board actually supports. Without
this, two players simply solve two separate puzzles next to each other.

## 3. The win condition is positional, not ownership-based

"Only pole 3 has disks" says nothing about whose disks. So a foreign disk resting
on your pole 3 does not block your win, and you do not need all N of your own
disks there — you need pole 1 clear, pole 2 clear, hand empty, and pole 3 not
empty.

The goal is *clear your side*, not *collect your disks*. We prefer this because
it is what the sentence says, and because the alternative requires the engine to
track ownership for a purpose the rules never state.

**Rejected:** requiring all N of your own disks on your pole 3. That is the
tidier, more Hanoi-shaped goal, and it is a defensible reading of the spirit. But
it contradicts the letter of the rule, it makes a disk your opponent hands you
into a permanent loss condition rather than a nuisance, and it would force a
`Disk` type with an owner field into a state model that otherwise gets ownership
for free from parity.

## 4. Cooperative smuggling is legal

This is not an independent decision so much as a consequence of (2) and (3) that
we chose to accept rather than patch out. A places disk 1 on pole 2; B lifts it
and buries it on 3b, which is legal as long as 3b's top disk is larger. Disk 1 is
now out of A's way for good, and A has one fewer disk to solve.
`examples/smuggle.json` shows A winning at N=2 in four of their own turns instead
of the six an uncontested solo solve costs.

It is a real communication channel between two players who cannot see each
other's boards or exchange messages: the only thing you can say to your opponent
is what you leave on the shared pole, and the only thing they can say back is
whether they take it.

**Rejected:** forbidding a player from placing a disk they do not own, or from
lifting a disk they do not own off the shared pole. The second is explicitly
contradicted by the rules ("either player may lift any top disk from the shared
pole"), and the first would need the ownership machinery that (3) already
rejected. We document this as emergent strategy, not as a defect.

## 5. Pole 3 must be non-empty to win

"Only pole 3 has disks" implies there are some. A player with an entirely empty
side has not won.

Without this, total giveaway is the fastest strategy in the game: hand every disk
you own to the shared pole, let your opponent bury them, and win with nothing on
your side at all. That is a degenerate line that trivialises the puzzle, and it
turns (3) from an interesting loosening into an exploit.

**Rejected:** reading "only pole 3 has disks" as satisfied vacuously when no pole
has disks. It is a legitimate parse of the English, and it is why the rule needs
stating explicitly rather than being left to whoever writes the predicate.

## 6. Placing onto your own pole 1 is legal

Nothing in the rules forbids it. Pole 1 is one of your visible poles, and place
says "onto any visible pole".

It also has to be legal for the game to work: real Hanoi maneuvering needs to put
disks back on the source peg constantly, and the random agent does it routinely.
Forbidding it would make many positions unsolvable for no stated reason.

**Rejected:** treating pole 1 as a one-way source, on the intuition that disks
should flow left to right. The intuition is aesthetic, the rules say otherwise,
and the aesthetic version breaks the puzzle.

## 7. A simultaneous win is a draw

If both players satisfy the win condition after the same action, the outcome is
`DRAW`. This exists so that the transition function is total: every position maps
to exactly one outcome, and no input can put the engine in a state it has no
answer for.

We believe it is unreachable from a standard start, but we state that as a
conjecture rather than a proof. The argument: a `PLACE` cannot change the
opponent's poles, so it cannot complete their side; and a `LIFT` that empties the
shared pole necessarily fills the lifting player's hand, which disqualifies them
under their own win condition. That covers the ways an action can newly satisfy
two win predicates at once, but we have not enumerated the state space to check
it. If you can construct a reachable draw, we would like to see it.

**Rejected:** raising, asserting, or awarding the win to the acting player.
Raising makes a pure function partial for a case that may not exist. Awarding it
to the mover invents a tiebreak the rules do not mention, and quietly makes the
schedule decide the game.

## 8. Illegal actions are typed values, not exceptions

`apply` never raises. It returns `ActionResult(state, status, reason)` where
`status` is `OK`, `SKIPPED` or `ILLEGAL`, and `reason` is one of `EMPTY_POLE`,
`HAND_FULL`, `HAND_EMPTY`, `SIZE_VIOLATION`, `POLE_NOT_VISIBLE`, set only when
the status is `ILLEGAL`.

An illegal action is not an error. It is an ordinary, rule-sanctioned outcome —
the rules say so explicitly, in that it wastes the turn — and it will be roughly
half of everything a learning agent does early in training. Exceptions for that
would mean every caller wraps every step in a `try`, and the cost of a wasted
turn would be paid in stack unwinding. `SKIP` stays distinct from `ILLEGAL` in
the log, because "I chose to do nothing" and "I tried something impossible" are
different facts about a player, even though they have the same effect on the
board.

We also keep the action's status and the game's result strictly separate:
`status` describes what happened to this action, `State.outcome` describes the
game. Conflating them is how you end up unable to say "that move was illegal and
also your opponent just won".

`POLE_NOT_VISIBLE` is unreachable through the seven-action enum, which can only
name poles the acting player can see. We keep it because the reason enum
describes the rules, and invisibility is one of the rules; it would become
reachable the moment anyone added an absolute-pole action space.

**Rejected:** raising `IllegalMoveError`, or returning a bare `bool`. The first
is discussed above. The second throws away the reason, which is the part that
makes a log worth reading and a training signal worth having.

## 9. You can see that your opponent holds a disk, but not which

An `Observation` carries a bool for whether the opponent's hand is full, and
nothing about its contents. A player also knows their own disk count, and not
their opponent's.

Hiding the fact of holding entirely would be a lie the board contradicts: a disk
you were watching on the shared pole vanishes, and there is only one place it can
have gone. Revealing which disk would leak the opponent's private poles by
elimination over time. The bool is the honest middle.

**Rejected:** exposing the held disk's size (the opponent's board becomes
inferable), and hiding the hand entirely (the observation contradicts what a
player can plainly deduce).

The mechanism matters as much as the choice: `Observation` has no field for the
opponent's poles or hand contents. The hiding is structural rather than a filter
applied on the way out, so a policy cannot reach around it, and a test asserts
the field set to keep it that way.

## 10. Running out of schedule ends the game as `UNFINISHED`

Turn order is an external, finite sequence. If it runs out with no winner, the
game ends in a fifth terminal outcome, `UNFINISHED`. The engine never crashes and
never loops forever.

`UNFINISHED` is deliberately not a draw. A draw is a statement about the
position; `UNFINISHED` is a statement about the schedule, and the position is
usually nowhere near decided. Collapsing them would make "we ran out of budget"
and "you both won at once" the same event in a log.

**Rejected:** looping until somebody wins (unbounded, and random play can stall),
raising on exhaustion (a normal end to a finite schedule is not an error), and
reusing `DRAW`.

## 11. The step counter always advances

Every action increments the step, including skips and illegal actions. The rules
say an illegal action wastes the turn, and a wasted turn is one that happened.

Practically, this is what stops any driver looping forever on an agent that keeps
proposing the same illegal move, and it makes the step counter mean "how many
turns have been consumed" — which is the quantity a schedule is indexed by, so
the two stay in step by construction.

**Rejected:** advancing only on actions that change the board. That makes the
step index disagree with the schedule position, and it makes an agent's illegal
moves free, which is exactly backwards from what the rules say.
