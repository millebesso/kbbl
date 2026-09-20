# 03 — Make a bloc betrayal cost something

**What to build:** Two fixes to one failure. KD and L waved through a government containing a
Party both of them exclude, and neither the data nor the briefings gave them a reason not to.
Re-price the right bloc so a left Platform cannot buy it by accident, and give the Referee a
third report — what a Proposal does to a Party's own Exclusions — shown at the Vote beside the
Gap report.

## What happened

The recorded Run in `cassettes/riksdag-2026/` (replay it: `uv run kbbl run
scenarios/riksdag-2026 --replay`) ended with a left minority government formed on Abstentions:

```
Yes      151    S 99 + V 30 + MP 22
Abstain   66    C 25 + KD 22 + L 19
No       132    M 70 + SD 62
```

**C's Abstention is correct and is not part of this ticket.** §9 is built on exactly that
possibility — *"Centerpartiet's abstention alone decides who governs"* — and C charged for it,
naming `environment >= +1` and *"SD has no influence over government policy"*, both of which
this Platform pays. That is the mechanism working.

**KD's and L's Abstentions are the failure.** Both are right-bloc parties, both list **V** as an
Exclusion, and V sits in the Government of the Proposal they let through. Neither would do this.

## Why they did it — two different causes

**KD was bought for one Axis.** Its entire Supporting price is `law_and_order >= +2`. The
Platform sits at exactly +2, so the Referee reported the whole price met, and KD honoured it:

> *"Law_and_order at +2 meets exactly what I asked for abstention. The rest is far from our
> mandate on economic and social, but we named our price and it's been met — I won't renege on
> that."*

The Agent did nothing wrong. A Supporting price of one Axis that a left Platform can satisfy in
passing is a price this repo wrote, in `scenarios/riksdag-2026/KD.json`.

**L was not bought at all — its price was unmet.** `education >= +2` against a Platform at −1.
It abstained on `willingness_to_re_elect: 1`:

> *"This platform betrays nearly everything L campaigned on — economic, health, and education
> gaps are unacceptable, and none of our asks were met. We won't own this by voting Yes, but we
> also won't be the ones forcing another election."*

That is §3's lever doing precisely its job: Willingness to re-elect is the only outside option
in the model and the reason a refusal costs anything. Set to 1 it makes almost any deal better
than an election, so L cannot refuse anything. The 1 was editorially defensible — L polled
5.34% against a 4% threshold — but the model gives L nothing to weigh against it.

## The design finding underneath both

**Nothing joins a Party's Exclusions to who is in the Government, at the moment it votes.**
Verified against the recorded requests: KD's and L's Vote briefings both show `Government: S,
V` and neither mentions an Exclusion anywhere. The information exists in two places and is
never put together — the Persona says *"V. That is a preference, not a veto"*, and the Proposal
names V, and no report stands between them.

§5.4 exists because *"an Agent asked abstractly to hold its ground drifts; the same Agent shown
the number it is abandoning behaves differently."* That argument was made about policy distance
and a whole feedback mechanism was built for it. It applies unchanged to a coalition betrayal,
and there is no equivalent report. §12.1 names agreeableness as the largest unmitigated risk
and says *"the only thing between this design and a grand coalition every run is §5.4"* — this
is that risk arriving in the one form §5.4 does not cover.

The new report is feedback and never a constraint, exactly like the other two (§2): a Party
remains free to wave through a government full of Parties it excludes. It just has to do so
knowing that is what it is doing.

**Not an n=1 argument.** One Run is not evidence (§12.3), but neither cause is inferred from
the outcome: KD's price is one line of JSON, and the missing report is visible in
`agents._the_vote` without running anything.

## Cost note

Changing a Persona, a briefing or a schema re-keys every Cassette, so the report half of this
re-records **both** drawers — `cassettes/four-party/` and `cassettes/riksdag-2026/`, about
$0.50 each. `riksdag-2026/02` changes briefings too. Land them together, or pay twice.

**Blocked by:** None. Independent of `riksdag-2026/02`, but see the cost note.

**Status:** done

- [x] KD's Supporting price names at least one term a left Platform cannot pay in passing — an Axis the blocs actually divide on, or a free-text term against the statutory profit ban
- [x] L's Supporting price and `willingness_to_re_elect` are re-set so that its fear of an election is a real pressure rather than an override; the 5.34% reading is kept, and what changes is that L has something to weigh against it
- [x] C is left alone, and `scenarios/README.md` says why its Abstention is the one that is supposed to happen (§9)
- [x] The Referee reports, to each Party before it votes, what the Proposal does to its own Exclusions — who it would rather not deal with, and whether they are in the Government, Support-only, or not named
- [x] That report is feedback and never a constraint: a Party can still wave through a government full of Parties it excludes (§2)
- [x] It is a data structure before it is a rendering, and it reaches `run.json` the way `Run.gap_reports` does — §7 wants every report a Party was shown to survive the Run (`kbbl-v1/06`)
- [x] The report computed is the one shown, built once and passed in, the way `_judge` already does it for the Gap report
- [x] `CONTEXT.md` gains the noun, beside **Gap report** and **Price report**
- [x] A Party with no Exclusions is shown nothing, the way `_who_you_would_rather_not_deal_with` already omits its section rather than saying "none"
- [x] Both Cassette drawers are re-recorded, not patched, and both replay byte-identical afterwards
- [x] **Re-run `scenarios/riksdag-2026` and read it: do KD and L still stand aside?** Record the judgement in this file's Comments. C abstaining again is the expected result, not a regression
- [x] §12.1's question is asked again of the new Run, since this ticket changes the one defence that section names

## Comments

**Both halves landed, both drawers were re-recorded, and the failure this ticket was written
about does not recur.** 222 tests, `mypy --strict` clean, and both recordings replay
byte-identical — `transcript.md` and `run.json` compare equal, `result.json` differs only in
its timestamp.

```
Yes        151      S 99 + V 30 + MP 22
Abstain     70      M 70
No         128      SD 62 + C 25 + KD 22 + L 19
```

**KD and L both voted No**, where both abstained before, and each said why in the terms this
ticket gave it:

- **KD**: *"economic, environment, health, education, transport, social all far off, plus
  statutory profit bans I'd never accept. I owe S nothing and it asked me nothing."* The
  clause after "plus" is the free-text Demand added here — the one V charges for in the
  other direction, so no Platform can pay both. The Platform did pay `law_and_order >= +2`,
  exactly as before; it is no longer the whole price.
- **L**: *"A 7-point education gap and a redistributive-climate platform I never signed onto
  isn't something I'll wave through for nothing."* **"for nothing" is the finding.** At a
  Willingness to re-elect of 1 L was told almost any deal beat an election and could refuse
  nothing; at 3 it still much prefers a deal, and now has something to weigh against that.

### The Exclusion report did the thing §5.4 is for, on a Party this ticket never touched

**M abstained with V in its Government, and named the price it had been paid for it**:
*"The deal held: law_and_order at +2, income tax cuts in the first budget, and economic held
at -3 as negotiated. It's not my platform, but I gave my word to stand aside on those terms,
and I'll honor it."*

That is the report working as designed rather than failing. M excludes V, was shown V in the
Government in its own Exclusion report, and waved it through anyway — knowingly, and having
been *bought*. Feedback and never a constraint (§2). The contrast with the first Run is the
whole point: KD stood aside for nothing and said the price had been met; M stood aside for a
Commitment it had negotiated in a Bilateral.

### C voted No, and C is not what changed

`scenarios/riksdag-2026/C.json` is byte-identical to before, and §9's arithmetic is
untouched. What differed is the bargaining: S spent Round 1 on C, the meeting exhausted its
Exchanges with nothing agreed, and the Proposal then named C nowhere and offered it nothing.
*"I extract no price for silence"*, C said, and blocked what it could not bill for.

This ticket predicted C would abstain again. It did not, and that is not a regression in the
data: **C's Abstention has become purchasable rather than free**, which is what §9 always
described. The Formateur's cheapest route to power moved from three right-bloc Parties
standing aside for prices a left Platform paid in passing, to one Party — M, 70 seats — being
paid for its Abstention in a Bilateral. One Run is not evidence either way (§12.3).

### §12.1, asked again of the new Run

**No grand coalition, and no mush.** The Platform is unmistakably left — `economic −3`,
`health −4`, `education −3`, `environment +4` — and **four of eight Parties voted No**. Every
Ballot traces to its own Mandate: SD naming `immigration −1` against its red line, V weighing
`economic` falling short against the profit ban it won, MP naming its three met asks, L and
KD and C refusing what they were not paid for. The one Party that was bought said what it
was bought with.

§12.1 names §5.4 as the only thing between this design and a grand coalition every Run. This
ticket widened §5.4 from the Platform to the coalition, and the Run after it is less
agreeable than the Run before it, not more.

### What it cost

**riksdag-2026: 37 requests, $0.39. four-party: 28 requests, $0.38.** Computed from the
`usage` in `run.json` at `claude-sonnet-5` list prices as of 2026-09-20 — $2.00/MTok input,
$10.00/MTok output, cache write at 1.25× input and cache read at 0.1× — not read off a bill.

| | riksdag-2026 | four-party |
| --- | ---: | ---: |
| input | 70,768 | 52,370 |
| output | 16,586 | 21,618 |
| cache write | 31,501 | 19,481 |
| cache read | 39,956 | 33,385 |

**`riksdag-2026/01`'s $0.50 is not comparable to this $0.39.** Its token counts reproduce
that figure only at $3.00/$15.00 per MTok, so the two numbers are the same size of Run priced
differently rather than a Run that got cheaper. Token counts are the durable part of both
records; the dollars are a reading of a price list on a date.

### Judgement calls

- **`Role` and `Proposal.role_of` were extracted rather than a fourth branch written.** Three
  places asked "what does this Proposal make of this Party" by branching on the two tuples —
  what a Party is told it is being asked for, which price list it charges on, and now this
  report. Not being named is the case a fourth copy would have got wrong, so it is a member
  of the enum rather than the `else`.

- **`Ledger.shown` takes either report and files it by type.** One verb for one act. Two
  methods would have let a caller put a report under the wrong heading, which is the only way
  these can go wrong — a Ledger never reads either list back.

- **KD's Supporting price gained two terms, not one.** `social <= 0` is an Axis the blocs
  really do divide on (KD −3, SD −4 against MP +5, V +4, S +2), and the free-text term is
  the one that collides head-on with V's Governing price. Either alone would satisfy the
  criterion; together they give the Supporting price the same shape as the Governing price it
  is the cheaper version of.

- **L's free-text term mirrors C's exactly.** *"V has no influence over government policy"*
  is the same shape as C's *"SD has no influence over government policy"*, which is precedent
  already in this Scenario. It is a price rather than a veto — the Referee reports it
  Unevaluated and L remains free to waive it.

- **The report is shown at the Vote and is not in the Transcript.** Neither is the Gap report:
  what a Party was shown lives in `run.json`, and the Transcript is what was said.

### Handed forward

- **Nothing checks that a Proposal's Commitments are consistent with each other.** S's
  Proposal carries both *"profit in tax-funded welfare banned in law this term"* (V's) and
  *"income tax cuts in the first budget"* (M's). The Referee never reads a Commitment (§2),
  so this is an Agent's judgement rather than a bug — but a Proposal granting two Commitments
  that contradict is a thing no report names, and it is how a Formateur could buy two Parties
  with one breath. The same §5.4 argument would apply.

- **`render_proposal`'s seat sentence is still not wrapped** — exactly one line of
  `transcript.md` exceeds the 88-column width, at 89 characters, unchanged from
  `riksdag-2026/01`.

- **Whether the cheapest route to power is now M's Abstention every time is not answerable
  from one Run** (§12.3). It is the question batch mode (§6) and the probe harness (§8) exist
  for, and both are still deferred.

- **`transcript.md` is 286 lines and 11,638 bytes** against the first Run's 280 and 11,137.
  Still readable at eight Parties; §10's worry remains untested for four Attempts
  (`riksdag-2026/02`).
