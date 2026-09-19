# 03 — Referee: Gaps, demand satisfaction, and the Blocking minority

**What to build:** The deterministic core — the part of the system allowed to be certain, and
so the part tested ruthlessly (§8). It computes and reports; it never constrains an Agent and
never parses prose (§2).

Three capabilities: the Gap between a Party's Positions and a Platform, per Axis and
summarised; axis-Demand satisfaction of a Platform against either price list; and vote counting
under Negative parliamentarism. Ships the Fixtures whose right answers are obvious.

Costs $0 to test, so there is no excuse for thin coverage here.

**Blocked by:** 01. Runs in parallel with 02 — it needs the models, not the model.

**Status:** done

- [x] Gap computed per Axis between a Party's Positions and a Platform; mean Gap and worst Gap derived
- [x] The Gap report renders a Party's worst Gaps, naming the Axes (§5.4)
- [x] Axis-Demand satisfaction reported against a Platform, for the Governing price and the Supporting price separately
- [x] Free-text Demands are reported as unevaluated, never guessed at — they are for Agents to interpret
- [x] Vote counting: a Proposal passes unless 175 or more seats vote No
- [x] Support-only seats count toward defeating the Blocking minority exactly as Government seats do (§4)
- [x] Invariant tested: a Proposal never passes with 175 or more seats against it
- [x] Invariant tested: a Party listed Support-only never appears in Government
- [x] Invariant tested: seats always sum to 349
- [x] Landslide, knife-edge-kingmaker and forced-deadlock Fixtures are committed and covered
- [x] This ticket's test suite makes zero API calls

## Comments

**Implemented.** 111 tests, `mypy --strict` clean, and this ticket's suite makes zero API
calls — it never constructs a `Cassettes` at all, so there is no path from it to the model.
`referee.py` grew three capabilities, each with its computation and its report beside it:
`gap_report()`/`render_gap_report()`, `price_report()`/`render_price_report()`, and
`count_vote()`/`render_vote()`. `models.py` gained `Axes`, `Platform`, `Proposal`, `Vote` and
`signed()`.

Three Fixtures are committed — `fixtures/landslide/`, `fixtures/knife-edge/` and
`fixtures/deadlock/` — and documented in `fixtures/README.md`.

### Decisions worth knowing about

- **Positions and a Platform are one shape, two nouns.** Both are the ten Axes in the same
  units and differ only in who owns them (`CONTEXT.md`, Platform), so they share an `Axes`
  base. A Gap is only meaningful because they are commensurable; giving them two independent
  definitions would have been two places to drift.
- **The Gap report marks the Axes above the Party's own mean**, rather than everything past
  some fixed size. That reproduces §5.4's sample exactly with no magic number in it, and it
  scales to the Party rather than to the scale: one that held nine Axes and surrendered the
  tenth sees exactly that one marked, and one that conceded evenly everywhere has no standout
  to flag, which is the truth about it.
- **A tie for the worst Gap is reported, never broken.** `worst` returns every Axis at the
  worst Gap. Picking one arbitrarily would hide half of a Party's worst betrayal.
- **Free text is `UNEVALUATED`, which is a third answer and not a missing one.** A tri-state
  enum rather than `bool | None` so the report can say *why* the Referee is silent: it is not
  the Referee's to read (§2), and a guess would be the Referee inventing a fact for an Agent
  to act on.
- **`Tally.passed` is the whole vote rule and nothing else** — `no < 175`. Seats behind the
  Proposal are reported beside the count rather than used in it, because §2 forbids the
  Referee constraining an Agent: a Party named in a Government may vote against it, and the
  Referee reports that rather than correcting it. There is a test for exactly that case.
- **Support-only needs no separate arithmetic to count (§4)** — `Proposal.backers` is
  `government + support_only` and the count is over Ballots regardless of role. The test
  moves GV from cabinet to Support-only and asserts every number is unchanged; if the two
  ever diverge, that test is what fails.
- **The invariants are exhaustive, because they cost nothing.** Every possible way each
  chamber could vote is enumerated (3^n) and asserted against "never passes with 175 or more
  against", with a check that both outcomes actually occurred so the loop cannot pass
  vacuously. The invariants run over every Fixture directory *found on disk* rather than a
  list, so a Fixture added later is covered the moment it lands.
- **The forced deadlock is a deadlock of prices, not of seats.** No chamber can be
  arithmetically deadlocked against every coalition — the coalition of everyone always holds
  349 — so `deadlock/` is forced the only way it can be: RF charges `economic >= +4`, SK
  `economic <= -4` and TN `economic == 0`, which name one Axis between them and contradict
  each other pairwise. The test ranges over all eleven values of that Axis and asserts no
  Platform ever pays two of them, and asserts first that the three Supporting prices really
  do name one Axis, which is what makes ranging over it exhaustive rather than suggestive.
- **`knife-edge/` is §9's real arithmetic with each bloc collapsed into one Party.** KM's
  Abstention alone decides who governs, in both directions, and the test asserts all three of
  KM's options against both possible governments.
- **Nothing is wired into the CLI.** The ticket asks for computation and reporting; who is
  *shown* a Gap report and when is ticket 05, and putting a Platform on the command line
  before there is a Proposal to carry it would be inventing an interface twice.
- **`Proposal` and `Vote` land here rather than in 05** because vote counting cannot be
  written without them. What is deliberately *not* here is their structured-output schema and
  anything that asks an Agent for one — that is 05's, and building it now would have fixed
  the shape before the Agent side had an opinion.
- **`signed()` moved into `models.py`.** `agents.py` and `referee.py` had identical copies.
  It is Axis vocabulary rather than either module's business, and both a persona and a
  Referee report print these in columns where a bare `3` reads as a magnitude.

### New nouns with no `CONTEXT.md` entry

Per `docs/agents/domain.md`, noted rather than unilaterally added: **`Tally`** (the chamber's
verdict on one Proposal), **`Ballot`** (how one Party voted and the seats it carries),
**`Satisfaction`** (met / unmet / unevaluated), **`Price`** (which of the two price lists is
being checked — the two values themselves are glossary terms), and **`Axes`** (the ten values
Positions and a Platform are both made of). `Grouping`, `Ending` and `Declaration` are still
outstanding from tickets 01 and 02, so a `/domain-modeling` pass now has seven terms waiting.

### Review findings

`/code-review` could not run: both sub-agents died on a session rate limit (HTTP 429) before
reading anything. The two axes were run by hand instead, against `CONTEXT.md`,
`docs/agents/domain.md`, the ticket, and the smell baseline. Seven findings, all applied:

- **A Party handed its own Positions back was told its worst Gap was all ten Axes at 0.0** —
  read as a complaint about a Platform it had written itself. `_worst` now says so plainly.
- **The vote table's totals fell out of its own columns** whenever the longest Party name was
  shorter than "Abstain". The column is now wide enough for both.
- **`Tally.seats(vote)`** took an argument, while `seats` is a plain number on `Grouping`,
  `Scenario`, `Party` and `Ballot`. Renamed `seats_voting`.
- **"free-text Demand(s)"** in prose an Agent reads, and "0 of 0 Axis Demands met" for a price
  list naming none. `_counted` now writes only the sentences it has something to say in.
- **`Tally.yes` and `Tally.abstain` had no caller and no test** — dead by the baseline's
  Speculative Generality. Both are now asserted, along with the Ballots coming back in chamber
  order.
- **A test name used "distance"**, which `CONTEXT.md` lists under Gap's *Avoid*, and
  `docs/agents/domain.md` binds test names to the glossary.
- **Two stray blank lines** left where `signed()` was lifted out.

### Left for later tickets

- **`Ending` is still branched on in two modules** (ticket 02's note). This ticket added no
  third site, so it stands as it was.
- **`Demand` is rendered twice**, as persona prose in `agents.py` (*"the platform must put
  economic at +3 or higher"*) and as a table cell here (`economic >= +3`). Both are private
  and the two readings suit their two places, but ticket 05 shows an Agent both at once —
  that is the moment to decide whether they should agree.
- **`render_gap_report` puts the Axes in canonical order, not worst-first.** Stable order
  makes two reports comparable by eye, and the marks and the summary line do the naming. If
  05's Transcripts read badly, this is the knob.
