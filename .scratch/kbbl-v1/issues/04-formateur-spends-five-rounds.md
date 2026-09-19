# 04 — A Formateur spends five Rounds

**What to build:** The Formateur works through its budget of five Rounds, choosing which single
Party to meet in each one and saying why before it does. Choosing whom to court is the central
strategic act of the game (§5.1) — with more parties than Rounds, a Formateur that spends its
budget badly should visibly fail.

The information asymmetry is the other half of this ticket: the Formateur accumulates
everything it hears across every Bilateral, while each other Party knows only what happened in
its own. That asymmetry is the game, and it is easy to leak by accident.

**Blocked by:** 02.

**Status:** ready-for-human — everything below is built and tested; the one remaining box
is a live recording, which needs an API key this agent did not have.

- [x] The Formateur chooses one Party per Round and states its reasoning before the Bilateral opens
- [x] Five Rounds per Attempt, and the budget is enforced
- [x] The Formateur carries what it learned in earlier Bilaterals into later ones
- [x] No Party other than the Formateur sees any Bilateral but its own — verifiable from the run record, not just from reading
- [x] The Transcript reads as five distinct private meetings
- [~] `--replay` replays the whole five-Round sequence with zero API calls — the path is
      built and tested against a scripted Agent; the committed recording is not made (below)
- [x] A Party may be met more than once if the Formateur chooses to spend two Rounds on it
- [x] Willingness to re-elect is rebanded, or the Fixture reseated, before the Formateur leans on it — `_DISPOSITIONS` sends NP and FF identical prose today and two of its five bands go unused, so the lever this ticket wants does not yet distinguish the two largest Parties (02, §12.1)
- [x] `--meet` is withdrawn — it stood in for a choice the Formateur now makes for itself (02)
- [x] Each Round's chosen Party and the reasoning given for it land in the `Run` record, not only in the Transcript — ticket 06 serialises what this ticket accumulates (§7)

**Sequencing note (02).** Cassettes are content-addressed by a hash of the request, so rebanding
willingness invalidates all fifteen committed recordings, and carrying earlier Bilaterals into
later ones invalidates every Round-2+ request regardless. Reband first, then record the full
five-Round run once — recording before the reband pays for the sequence twice.

## Comments

**Implemented.** `uv run kbbl run fixtures/four-party [--replay]` now spends a Formateur's five
Rounds. 132 tests, `mypy --strict` clean, zero API calls in the suite.

New module: `loop.py` (`attempt()` — the Rounds of one Attempt, the budget counted by the
Referee). `agents.py` gained `FormateurAgent`, which is one conversation for the length of an
Attempt. `models.py` gained `Choice` and `Round`, and `Run.bilaterals` became `Run.rounds`.
`referee.py` gained `ROUNDS`, since §2 puts the round budget on the Referee's side of the line.

### The one box left open: nothing is recorded

Every committed Cassette is gone. The sequencing note above said rebanding would orphan all
fifteen, and carrying earlier Bilaterals forward would orphan every Round-2+ request anyway;
changing the reply shape (below) orphaned the rest. They could not replay, so keeping them
would have meant a red suite and a README promising a `--replay` that misses.

**To finish this ticket: `uv run kbbl run fixtures/four-party` once, with `ANTHROPIC_API_KEY`
set, then commit `cassettes/four-party/`.** About 35 calls, on the order of $0.40. Two tests
skip until then, saying so: `test_the_committed_cassettes_replay_a_real_attempt` and
`test_the_recorded_run_shows_no_party_a_bilateral_it_was_not_in`. Both go green with no code
change. §12.1's judgement — read the five-Round Transcript and record whether a Formateur with
a budget spends it like one — also waits on that recording, and belongs here when it exists.

### Structured output is gone: prose is never decoded inside a constrained field

02's finding was that roughly one live call in eleven came back empty, truncated, or carrying a
leaked JSON character, always while two or three paragraphs were being decoded inside a schema
string — and that ticket 04 should not build a five-Round Attempt on top of it. A Round is up
to seven calls, so an Attempt is ~35, and at that rate an abort mid-Attempt was close to
certain. Live always calls (§11.5), so each abort re-rolls everything already paid for.

So the shape 02 proposed is the shape now: **the message is the reply's ordinary text, and the
only things the Referee reads are short enumerated tool arguments beside it** — `end_meeting`
carrying an `ending`, `meet` carrying a `party`. §2's rule is unchanged and slightly stronger;
`docs/kbbl.md` §2 is updated to name the mechanism, because it named `output_config.format`
specifically. `test_no_prose_is_ever_decoded_inside_a_constrained_field` holds the line: every
tool field in every request must be an enum.

`MIN_MESSAGE` stays anyway. It costs nothing, the failure it catches is silent rather than
loud, and a run of clean Exchanges is not evidence that a decoder cannot slip again.

**This is the one thing here no test can vouch for.** Nothing in this repo has yet sent the new
request shape to the API, because nothing could. Read the first live run for that as much as
for the negotiation.

### The retry policy 02 handed forward: no

02 left it open whether `Cassettes` should retry a degraded reply, noting it "muddies 'a
recording is what happened'". **It should not, and this ticket does not add one.** A retry
records the second thing the model said as though it were the first, and the whole reason a
malfunction aborts the Run is that a degraded reply must never become a turn of the
negotiation — a retry inside the recording seam is that same failure, moved somewhere harder to
see. The right fix for the cost was to remove the shape that was degrading, which is what the
section above does. If Attempts still abort often once there is live evidence, the honest
lever is resuming from Cassettes already on disk, not re-rolling quietly.

### Two bugs that only existed once a Formateur had a memory

Both were invisible while a Bilateral was a thing that happened once and was thrown away.

- **The Formateur never heard the Counterparty's last word.** The meeting loop broke out before
  delivering the closing message, so a Bilateral ending on the Counterparty's turn was carried
  into the next Round missing the very message it ended on. A Declaration buys the declarer no
  *reply*; it does not unsay what it was carried on.
- **The Formateur's conversation had two consecutive `user` turns** at every Round boundary — a
  meeting closing and a Round opening, with nothing said in between. The Messages API takes
  alternating roles, so the first live Round 2 would have failed. `_Side.hear` now merges into
  the open turn, and a test asserts strict alternation across every request in an Attempt.

### A Party met twice keeps its own first meeting

Found in review, and it is the criterion's real content rather than a detail: a second meeting
was opening a fresh conversation, so the Formateur could say "as we agreed" to a Party that
remembered agreeing nothing. `CONTEXT.md` gives a Counterparty "only what happened in its own"
— an earlier Bilateral with this same Formateur **is** its own. `FormateurAgent` now keeps one
room per Party and reopens it, telling the Party that time has passed and that what it knows is
still only its own side. The other half is tested too: reopening a room carries nothing from
the meetings in between.

### Verifiable from the record, not from reading

`leaks(requests, run)` in `tests/conftest.py` reads every request a Run made back against the
record of who said what in which Bilateral, and reports anything a Party was shown that was
said somewhere it was not. It is the only way to check the asymmetry that does not come down to
trusting the code that builds the briefings. A second test tampers with a Run to prove the
audit fails when there is something to find.

It runs over the scripted stand-in's requests today. It runs over the committed Cassettes — the
actual traffic of a live Run — the moment one is recorded.

### The Fixture was reseated rather than the bands rebanded

NP 4 → 1 and FF 6 → 9. Rebanding could not have fixed it: eleven values across five bands means
one band spans three, so any pair can still collide — the values were the problem, not the
banding. Four Parties now sit in four bands and no two are sent the same prose. The pairing is
deliberate: the largest Party dreads the campaign it would fight after failing to form a
government, and the second largest, nine seats behind, fancies its chances in one.
`fixtures/README.md` carries the table and the reasoning.

### Smaller decisions

- **`FormateurAgent`, not `Formateur`.** `CONTEXT.md` gives *Formateur* to the Party; this class
  is the LLM instance negotiating on its behalf, which that glossary calls an Agent. It also
  stops `loop.py` reading `Formateur(scenario, formateur)`.
- **`Round` stores the Choice and the Bilateral, and refuses to hold both if they disagree.**
  The chosen Party is not stored twice: `Bilateral.counterparty` is who was actually met, and a
  Round naming somebody else is a record disagreeing with itself.
- **The Formateur is told the truth about its own budget.** `_your_attempt` said five Rounds do
  not stretch to a tour of the chamber, which is false of every Fixture in the repo (three or
  four Parties). It is now conditional on the arithmetic. §5.1's premise — more Parties than
  Rounds — is only true of the eight-Party `scenarios/riksdag-2026/`, which §10 defers.
- **New noun with no `CONTEXT.md` entry: `Choice`** (the Formateur's decision about how to spend
  one Round — whom, and why). Noted rather than unilaterally added, the treatment 01 gave
  `Grouping` and 02 gave `Ending` and `Declaration`. All four want a `/domain-modeling` pass.
- **`Ending` is now branched on at a third site** (`agents._that_meeting_is_over`, beside
  `output._ending` and `agents._declaration`), which makes 05's checklist item live. Worth
  noting before collapsing them: the two rendering sites speak to different audiences — one
  second-person to the Formateur mid-Attempt, one third-person in the Transcript — so one
  function serving both may be worse than two that agree.
