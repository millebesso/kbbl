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

**Status:** ready-for-agent

- [ ] KD's Supporting price names at least one term a left Platform cannot pay in passing — an Axis the blocs actually divide on, or a free-text term against the statutory profit ban
- [ ] L's Supporting price and `willingness_to_re_elect` are re-set so that its fear of an election is a real pressure rather than an override; the 5.34% reading is kept, and what changes is that L has something to weigh against it
- [ ] C is left alone, and `scenarios/README.md` says why its Abstention is the one that is supposed to happen (§9)
- [ ] The Referee reports, to each Party before it votes, what the Proposal does to its own Exclusions — who it would rather not deal with, and whether they are in the Government, Support-only, or not named
- [ ] That report is feedback and never a constraint: a Party can still wave through a government full of Parties it excludes (§2)
- [ ] It is a data structure before it is a rendering, and it reaches `run.json` the way `Run.gap_reports` does — §7 wants every report a Party was shown to survive the Run (`kbbl-v1/06`)
- [ ] The report computed is the one shown, built once and passed in, the way `_judge` already does it for the Gap report
- [ ] `CONTEXT.md` gains the noun, beside **Gap report** and **Price report**
- [ ] A Party with no Exclusions is shown nothing, the way `_who_you_would_rather_not_deal_with` already omits its section rather than saying "none"
- [ ] Both Cassette drawers are re-recorded, not patched, and both replay byte-identical afterwards
- [ ] **Re-run `scenarios/riksdag-2026` and read it: do KD and L still stand aside?** Record the judgement in this file's Comments. C abstaining again is the expected result, not a regression
- [ ] §12.1's question is asked again of the new Run, since this ticket changes the one defence that section names
