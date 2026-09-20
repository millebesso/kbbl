# 01 — The 2026 Riksdag as a Scenario

**What to build:** `scenarios/riksdag-2026/` — eight hand-written Party mandates for the real
parliament elected on 13 September 2026, and one Run against them, read closely.

**No new code.** A Fixture is a Scenario in every respect — same shape, same loader, same
349-seat validation (§9, §11.6) — so this ticket is data, documentation, and the first honest
look at whether eight Personas negotiate as well as four did. If anything here needs a change
to `scenario.py`, that is a finding worth writing down rather than a change worth making
quietly: it would mean the one load path was never one.

**This is the whole point of the project.** §9 frames KBBL as a *prediction of an open
question*, not a retrodiction of a settled one, and ticket 06 dated `result.json` so that a
later comparison against the real government is a lookup. Until this Scenario exists, that
timestamp is dated evidence about four invented parties.

Neither bloc reached 175, and that is why this parliament is worth simulating:

```
Left    S 99 + V 30 + MP 22            = 151
Right   M 70 + SD 62 + KD 22 + L 19    = 173
C                                      =  25   <- holds the balance
```

Under Negative parliamentarism a left minority government of 151 survives **if C abstains** —
the entire right bloc is two seats short of the 175 needed to block it. Centerpartiet's
Abstention alone decides who governs, which is exactly the thing §5.2 says the negotiation is
really for.

**Positions are editorial judgement, not fact.** §9 and §12.4 both insist on this, and it is a
publishing obligation rather than a nicety: a Run is not an authority on Swedish politics, and
the data must say so in the same directory a reader finds it in. The seats are sourced and
checkable; the ten Axis values, the two price lists and the Willingness to re-elect are the
author's reading and must be labelled as such.

**Blocked by:** None — v1 is complete and the loader already takes this.

**Status:** ready-for-agent

**Remaining:** the data, the documentation and the tests are done and committed. The four
unticked boxes all need one live Run, which spends real API credit and was deliberately
deferred — see the Comments. Do not redo the work above.

- [x] `scenarios/riksdag-2026/` holds eight mandates whose seats match §9 exactly: S 99, M 70, SD 62, V 30, C 25, KD 22, MP 22, L 19
- [x] They load through `load_scenario` unchanged — one load path, never two (§9, §11.6)
- [x] `scenarios/README.md` states, in the directory a reader finds the data in, that Positions, both price lists and Willingness to re-elect are the author's editorial judgement and that a Run is not an authority on Swedish politics (§9, §12.4)
- [x] The seat source is recorded with its date — Valmyndigheten, marked final on 19 September; the 17 September release still said preliminary, so a levelling-seat adjustment is possible (§12.5)
- [x] Every Exclusion is soft and priced; no mandate encodes a veto (§3, decision 7)
- [x] `uv run kbbl run scenarios/riksdag-2026` prints the chamber, and the Referee's own Blocking-minority output shows the §9 arithmetic — that the right bloc alone does not reach 175 — rather than this ticket asserting it in prose
- [x] Formateur order under largest-first is S → M → SD → V, and §5.3's known divergence from the Speaker's real discretion is documented where a reader of the Scenario will meet it (§12.2)
- [x] The Formateur is told it cannot meet everybody — seven other Parties and five Rounds is the case `_what_the_budget_buys` was written for, and this is the first Scenario where it fires (§5.1)
- [ ] One live Run is recorded to Cassettes and replays byte-identical
- [ ] **What the Run actually cost is measured and recorded**, not assumed: §6's ~130 calls / ~$1.56 is a design-time estimate, and v1's four-Party Attempt was 31. Eight Parties means more Exchanges per Round and eight Ballots per Vote
- [ ] **Read the Transcript: do eight Personas still hold their ground, or does the extra room to manoeuvre produce the grand coalition §12.1 warns about?** Record the judgement in this file's Comments
- [ ] `transcript.md` is still readable at this length — §10 flags eight Parties as "a lot of transcript to read", and `kbbl-v1/06` left the four-space indent question open because four Parties never made it hurt

## Comments

**Data, documentation and tests are done. The live Run is deferred by decision, not oversight.**
`uv run kbbl run scenarios/riksdag-2026` loads the real parliament, validates it and prints the
chamber. 208 tests, `mypy --strict` clean, zero API calls. **No change to `src/` at all** — the
ticket's "no new code" held, which is the evidence that a Fixture really is a Scenario and there
really is one load path.

The four unticked boxes need one live Run against `claude-sonnet-5` (~44 calls, and measuring
the real cost is itself one of them). That spends real credit, so it was put to the user, who
chose to commit the data and leave the Run. Nothing about it is blocked except the decision to
spend.

### Judgement calls

- **Parties are named `S`, `M`, `SD`, … rather than in full.** A Grouping label is built by
  joining names, and the widest line goes from 38 columns to 151 against a Transcript width of
  88 — measured, not guessed, on all 25 minimal Groupings. The full names live in the README
  table, which is the only place they are needed.

- **`COMMITTED_FIXTURES` became `COMMITTED_SCENARIOS` and now sweeps both directories.** The
  Referee invariants were found-not-listed over `fixtures/` for the reason the conftest gives:
  a Scenario added without them run over it is the one that would have caught something. Two
  lists would have been the second load path §9 exists to prevent, arriving in the tests
  instead of the code. The real Scenario makes the exhaustive vote invariant 3^8 rather than
  3^4, which still costs nothing.

- **The editorial obligation is discharged in `scenarios/README.md`, not in the mandates.**
  JSON has nowhere to put a disclaimer a reader will actually meet, and §9 asks for it
  "alongside the data" rather than inside it.

### Found in review, and fixed

Two of these were factual errors in the README about its own data — the worst failure available
to this ticket, since the whole point is that the data be honestly described.

- **"C is what completes it" was false.** Four minimal Groupings reach exactly 176, not one, and
  `M + SD + KD + MP` blocks without C at all. What is true and checkable is narrower: the right
  bloc is 173 and absent from the table, and no minimal Grouping is drawn from one bloc alone.
  The README now says that, and says out loud that C rather than MP being the Party to watch is
  political judgement rather than arithmetic.

- **"the Chamber's four Votes run out after the fourth" contradicted §5.3.** Standing down ends
  an Attempt and spends no Vote, so all eight Parties can have a turn. Both the README and a
  test docstring repeated the error.

- **The bloc table sat unmarked under "the seats are fact".** Which Party belongs to which bloc
  is the conventional reading, not fact, and nothing in the data encodes a bloc — the Referee
  knows only seats. Now labelled.

- **The Exclusions bullet listed four of ten pairs and read as exhaustive**; C's Supporting
  price was called "only `environment >= +1`" two paragraphs above the bullet noting its
  free-text Demand sits on both lists.

- **A test assertion could not fail.** `all(other in named …)` is guaranteed by
  `Scenario._check_chamber`, which refuses a dangling Exclusion before the fixture exists — and
  the docstring claimed it was "the only thing that could go wrong". It now checks the softness,
  which is the part nothing else covers, and cites the test that really pins the other half.

- **Two tests were in the wrong module and one reached a private name.** The bloc arithmetic
  moved to `test_referee.py`; the budget briefing moved to `test_agents.py` and is now read off
  the request that was actually sent rather than by importing `_what_the_budget_buys`. The
  renamed sweep had also left `test_every_committed_fixture_seats_the_whole_chamber` calling the
  real parliament a Fixture.

Handed forward:

- **The bloc arithmetic now appears in §9, in `scenarios/README.md` and in a test.** That is
  spec → documentation → check rather than duplication, and the test is what would catch a
  drift — but a levelling-seat revision (§12.5) touches all three plus every Cassette. The
  README's revision warning now says so.

- **Nothing yet reads a Transcript of eight Parties**, so §10's worry that eight is "a lot of
  transcript to read" and `kbbl-v1/06`'s open question about the four-space indent are both
  still untested. They need the live Run.
