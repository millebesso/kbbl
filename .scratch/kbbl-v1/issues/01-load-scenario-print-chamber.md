# 01 — Load a Scenario and print the chamber

**What to build:** `uv run kbbl run <scenario>` reads a directory of Party mandates, validates
them at the boundary, prints the seat table and which groupings clear the Blocking minority,
and exits. Nothing negotiates yet — this is the spine every later ticket extends. Ships the
four-Party Fixture that v1 negotiates on, and stands up the project: uv, pydantic, pytest.

A mandate is hand-written JSON (§3), so validation is the whole point: it must fail loudly and
usefully rather than letting a typo reach an Agent.

**Blocked by:** None — can start immediately.

**Status:** done

- [x] `uv run kbbl run <scenario>` loads a Scenario directory of Party mandates and prints a seat table
- [x] Mandates validate at the boundary: all ten Axes present, each −5..+5; seats sum to 349
- [x] Both price lists parse, with axis Demands and free-text Demands freely mixed in either
- [x] Exclusions and Willingness to re-elect parse and round-trip
- [x] A malformed mandate fails with a message naming the Party and the offending field, not a stack trace
- [x] The four-Party Fixture v1 negotiates on is committed and loads clean
- [x] Fixtures load through the same path as Scenarios — one loader, never two
- [x] `out/` is gitignored
- [x] Tests cover: a valid Fixture loads; seats ≠ 349 rejected; an Axis out of range rejected; a missing Axis rejected

## Comments

**Implemented.** `uv run kbbl run fixtures/four-party` loads, validates and prints the chamber.
30 tests, `mypy --strict` clean, zero API calls.

Modules: `models.py` (Party, Positions, Demand, Scenario — all `extra="forbid"` and
`strict=True`, validated from raw JSON so a hand-written typo cannot coerce into a plausible
value), `scenario.py` (the one load path, and `ScenarioError` — every message names the Party
and the offending field), `referee.py` (seat table, minimal groupings reaching the Blocking
minority), `cli.py`.

Decisions worth knowing about:

- **Minimal groupings, not all of them.** "Which groupings clear the Blocking minority" is
  rendered as the *minimal* ones — those where no member can be dropped. Listing every grouping
  buries the interesting ones under their own supersets; the minimal ones name each kingmaker
  exactly once. NP+MI+GV therefore never appears, because NP+MI already clears it.
- **Two validations beyond §3.** A `prefer_not` naming a Party outside the Scenario is rejected,
  and so are two Parties sharing a name. §3 asks for neither, but a silently-ignored Exclusion
  typo is exactly the failure this ticket exists to prevent, and duplicate names would break
  Party lookup and vote counting downstream.
- **Rendering lives in `referee.py`, not `output.py`.** §2 says the Referee computes *and
  reports*; the seat table is chamber arithmetic, not a Transcript. Ticket 06 should revisit the
  seam when `output.py` arrives.
- **`Grouping` is a new noun** carried by the CLI output and this ticket's own wording, with no
  `CONTEXT.md` entry yet. Worth a glossary pass.
- **mypy** was added alongside pytest. The ticket says uv/pydantic/pytest; strict typing on a
  pydantic boundary earns its keep, but it is one dependency more than was asked for.

**The Fixture was reseated after review.** The first draft was NP 137 / FF 140 / GV 28 / MI 44,
and in it **GV was a null player** — 28 seats that were pivotal in no configuration whatsoever,
so the Formateur had no arithmetic reason ever to court it and a quarter of the chamber dropped
out of the game. Final seats are NP 140 / FF 132 / GV 42 / MI 35, which puts every Party in at
least one minimal grouping and produces an exact knife-edge: NP+MI is 175, FF+GV is 174. The
Formateur (NP, largest) can pass a minority government if any one of the other three abstains,
by a single seat when it is MI; the rival FF+GV minority is blocked by NP+MI at precisely 175
unless MI steps aside. See `fixtures/README.md`.
