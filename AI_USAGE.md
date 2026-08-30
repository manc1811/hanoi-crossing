# AI usage

The assignment allows unrestricted use of AI tools and asks for disclosure.

**Tool:** Claude Code (Opus 5), driven interactively from the terminal, used to
write most of the Python here — engine, frontends and tests.

**What was decided by hand, before any code existed:** the interpretation of the
rules. `CLAUDE.md` §3 fixes the eleven calls that `DECISIONS.md` explains — that
the win condition is checked for both players after every action, that the shared
pole blocks everyone, that the goal is positional rather than ownership-based,
that smuggling therefore stands. Those came from reading an ambiguous spec and
choosing, and they were written down as constraints the model was then held to
and told to challenge rather than quietly reinterpret. The architecture
constraints, the code conventions, the 500-line ceiling, and the nine milestones
in `PLAN.md` are the same — human, and prior. Plan mode was used to draft the
plan; the milestones and their ordering are a person's.

**The tests that pin the rules were written from the assignment, not from the
code.** `tests/test_spec_example.py` encodes the brief's own N=1 walkthrough and
was committed before any engine existed (`55c6a67`). `tests/test_win.py` states
the four win-detection cases by hand, before win detection. Tests written from
the spec can falsify an implementation; tests written from the implementation can
only agree with it.

**How it was run:** one milestone at a time, reviewed before the next began, one
commit each, commit messages written by the human after reading the diff. Two
designs were sent back at review — output formatting that had been duplicated
across the two frontends, and a legality check that read the full state, which
made "an `Observation` is enough to play from" a claim in prose rather than a
fact enforced by the code. Both are now the other way round.

The model wrote the code. The decisions in `DECISIONS.md` are the work, and they
are not its.
