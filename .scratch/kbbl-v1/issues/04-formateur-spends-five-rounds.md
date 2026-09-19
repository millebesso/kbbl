# 04 — A Formateur spends five Rounds

**What to build:** The Formateur works through its budget of five Rounds, choosing which single
Party to meet in each one and saying why before it does. Choosing whom to court is the central
strategic act of the game (§5.1) — with more parties than Rounds, a Formateur that spends its
budget badly should visibly fail.

The information asymmetry is the other half of this ticket: the Formateur accumulates
everything it hears across every Bilateral, while each other Party knows only what happened in
its own. That asymmetry is the game, and it is easy to leak by accident.

**Blocked by:** 02.

**Status:** done

- [x] The Formateur chooses one Party per Round and states its reasoning before the Bilateral opens
- [x] Five Rounds per Attempt, and the budget is enforced
- [x] The Formateur carries what it learned in earlier Bilaterals into later ones
- [x] No Party other than the Formateur sees any Bilateral but its own — verifiable from the run record, not just from reading
- [x] The Transcript reads as five distinct private meetings
- [x] `--replay` replays the whole five-Round sequence with zero API calls
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

### The recording

All fifteen of 02's Cassettes are gone — the sequencing note above said rebanding would orphan
them and carrying Bilaterals forward would orphan every Round-2+ request anyway; the reply
shape did for the rest. `cassettes/four-party/` now holds one whole five-Round Attempt, 24
calls, and `--replay` reproduces the Transcript byte for byte.

**The new request shape worked on the first live call**, which is the thing nothing in the
repo could vouch for: text plus a tool call, adaptive thinking, both tools, 24 calls without a
single malformed reply. 02 measured roughly one in eleven degrading under the old shape; this
Attempt is a clean 24 for 24, which is weak evidence on its own and exactly the direction the
change predicted.

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

It runs over the scripted stand-in's requests, and over the committed Cassettes — the actual
traffic of the live Run. Both are clean.

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

### §12.1 — the judgement: does a Formateur with a budget spend it like one?

**Yes, and the two Rounds it spent on MI are the evidence.** NP met FF, then MI, then GV, then
MI again, then FF again — three Parties over five Rounds, twice going back to somebody it had
already seen. Read the whole Transcript; the short version:

- **It reasoned about the budget in the language of the arithmetic.** Round 1: *"FF is the
  obvious anchor partner — together we'd command a commanding majority. I want to test their
  price on economic and law_and_order before dealing with anyone else."* Round 3, after MI had
  named its price: *"MI deal secures NP+MI at exactly 175, mathematically safe against any No
  coalition. Now I want insurance."* That is the seat table being used, correctly, to decide
  whom a Round is worth spending on.
- **Round 4 is the ticket's own criterion doing work.** NP went back to MI to close — *"Rather
  than reopen incompatible terms with FF, I'll use this round to firm up remaining details"* —
  and **MI remembered**: it answered *"This meets my terms in full"* and agreed in two
  Exchanges rather than five. A Party met twice that had been handed a fresh conversation
  would have reopened the whole negotiation, and the Round would have been wasted. The bug
  found in review was not academic.
- **Round 5 is a Formateur spending its last Round on a long shot and losing it.** Holding
  MI's 175, NP went back to FF for a cushion, found FF had not moved, and declared impasse in
  one Exchange. That is a budget being spent, not consumed.
- **Nobody folded.** FF held economic at 0 across six Exchanges against a Formateur opening at
  +3 and closing at +1, and NP walked rather than pay. GV held environment +2 for an
  abstention and NP refused it — *"more than I'll trade for an abstention I may not need"* —
  which is a Formateur pricing an Abstention against its own arithmetic, the §5.2 claim
  working.

**The reseated Willingness to re-elect shows up in behaviour on its first run.** FF, moved to
9 (*"would welcome another election"*), ended Round 1 with *"anything harder on economic and I
walk and take my chances at the polls."* NP, moved to 1 (*"another election would be a
disaster"*), never once reached for the threat. Under the old seating those two Parties were
sent identical prose; they are now the two ends of the scale and they played it.

**The Transcript is readable, which took two attempts.** Asked for "two or three short
paragraphs" the Agents wrote a median of 80 words per Exchange; asked for "three or four
sentences" they wrote the same 80 words in longer sentences. A word count (`WORDS = 40`) is
what actually moved it, to a median of 47. §8 asks that full runs be read closely, and a
Transcript nobody finishes is a Transcript that fails that on its own.

**One thing to watch, still.** Four of the five Bilaterals here ended on a Declaration, three
of them NP's. 05 still owns what an Ending commits a Party to — and Round 2 ending in
*"agreement"* while Round 4 re-opened and agreed again is the sharpest version of that
question yet: an Ending of agreement plainly settled nothing, which is exactly what
`CONTEXT.md` says it should not be read as settling.
