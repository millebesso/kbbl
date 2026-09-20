# 05 — Table a Proposal and hold the vote

**What to build:** The Formateur turns five Rounds of bargaining into a Proposal and the chamber
votes on it. This closes the v1 slice: one Formateur, one Attempt, at most one vote.

Everything the Referee consumes is **structured output** — the Proposal, and every vote. Prose
exists for the Transcript only. Regexing a Proposal out of natural language is the most common
way an agent simulation becomes unreliable (§2), so there must be no prose-parsing path at all.

Before each Party judges the Proposal it is shown its own Gap report. This is the only defence
against the degenerate outcome — a grand coalition on a mushy centrist Platform, looking
entirely reasonable every run (§5.4). It is feedback, not a constraint: a Party remains free to
accept a Platform five points from its voters, it just has to do so knowingly.

A Formateur that finds no viable coalition may Stand down rather than table a doomed Proposal.
The run then ends with no vote.

**Blocked by:** 03, 04.

**Status:** done

- [x] The Formateur emits a Proposal as structured output: Platform (one value per Axis), Government, Support-only, Commitments
- [x] The Referee obtains the Proposal and every vote structurally — there is no prose-parsing path anywhere
- [x] Each Party is shown its own Gap report before it judges the Proposal
- [x] Each Party returns Yes / Abstain / No as structured output, with prose reasoning kept for the Transcript
- [x] The Referee counts under Negative parliamentarism and declares the outcome
- [x] A Formateur may Stand down instead of tabling; the run ends with no vote and reports that outcome distinctly from a rejection
- [x] No ministries or portfolios appear anywhere in the Proposal (§4)
- [x] A passed Proposal, a rejected Proposal, and a Stand down are each exercised and replayable from Cassettes
- [x] What a Bilateral's `Ending` commits a Party to is decided and written down — NP declared `agreement` on its own last word in all three of 02's recordings, and `LAST_WORD` beside an available `agreement` option may simply make wrapping up attractive (02)
- [x] A `Demand` reads the same whether an Agent meets it as persona prose or as a report cell — this is the first ticket that shows it both at once (03)
- [x] `Ending` is already branched on in `agents.py` and `output.py`; if this ticket adds a third site, the three collapse into one (02, 03)
- [x] If the Transcripts read badly, `render_gap_report`'s canonical Axis order is the knob to turn — worst-first is the alternative (03)
- [x] **Read the Transcript: did the Gap report change how parties voted, or did they fold anyway?** Record the judgement in this file's Comments (§12.1)

## Comments

**Implemented.** `uv run kbbl run fixtures/four-party [--replay]` now runs a whole Attempt:
five Rounds, then a Proposal the chamber votes on — or a Stand down. 178 tests, `mypy
--strict` clean, zero API calls in the suite.

`agents.py` gained the `table` / `stand_down` / `ballot` tools, `FormateurAgent.table()` and
`FormateurAgent.put_to_the_chamber()`. `referee.py` gained `render_proposal()`. `models.py`
gained `Judgement`, `Bilateral.ended_by()`, and `Run.proposal` / `Run.tabling` /
`Run.judgements`. `loop.attempt()` now returns the whole `Run` rather than its Rounds, and
`render_transcript()` takes the Scenario so the Transcript reports the Vote the Referee
counted rather than a second reckoning of its own.

`cassettes/four-party/` is re-recorded: one live Attempt, 31 calls, and `--replay` reproduces
the Transcript byte for byte.

### §12.1 — the judgement: did the Gap report change how Parties voted, or did they fold?

**It changed how they voted, and nobody folded.** Every one of the four Ballots names
something the Referee had just shown that Party, and the two Yes votes both state the price
out loud rather than glossing it. Read the whole Transcript; the short version:

NP tabled a two-Party government of **exactly 175** and it passed **by one seat** — 174 No.
That is the Fixture's knife-edge landing on its first live Vote, and it is the opposite of
the §12.1 failure this ticket was written to look for: no grand coalition, no mushy centre,
a government that survives only because its opponents are one seat short.

| Party | What it was shown | What it did |
| --- | --- | --- |
| NP | Governing price: **both** Axis Demands unmet (economic ≥ +3 got +2, law & order ≥ +3 got +2) | Yes — *"Both my hard economic and law_and_order floors are unmet, but voting No now collapses my own deal and triggers an election I cannot afford."* |
| FF | Gap report marking economic, health, immigration, education, social; no price report (unnamed) | No — *"economic +2, health +2, no pension protection, spending caps I never accepted. It betrays my mandate outright."* |
| GV | Gap report marking environment, military, immigration, transport, social (mean 5.4, worst 7.0) | No — *"nowhere near my mandate on environment, transport, or social — a betrayal of everything we campaigned on."* |
| MI | Governing price 2 of 2 met; Gap report marking environment, military, immigration, social | Yes — *"Environment, immigration, and social sting, but the price was met and I gave my word."* |

Three things in that table are the design working rather than the Agents being agreeable:

- **NP voted for a Platform that fails its own stated price, and said so.** §2 claims an Agent
  is always free to act against its own mandate *"it just has to do so knowingly"*. The Price
  report is what makes "knowingly" checkable, and NP read it straight back — two unmet floors,
  named, then overridden for a reason it gave. That sentence could not have been written by a
  Party that had not been shown the report.
- **GV and MI each named three of their own marked Axes**, unprompted, and neither list is the
  other's. GV's `<<` marks were environment, military, immigration, transport, social; it
  cited environment, transport, social. MI's were environment, military, immigration, social;
  it cited environment, immigration, social. The report is being read, not decorated with.
- **FF cited its free-text Demand** — *"no pension protection"* — although it is **not** in the
  Base and so was shown **no** price report at all. That came out of its persona. The two
  channels agree without being wired together, which is what the `Demand` item below is about.

**Willingness to re-elect predicted all four Ballots.** NP (1, *"a disaster"*) voted Yes and
named the election it could not afford; MI (2) voted Yes; GV (8) and FF (9) both voted No and
both said in terms that they would rather face voters. Four Parties, four bands, four Ballots
in line — the reseating ticket 04 did is paying off at the one moment it was meant to.

**Caveat, stated plainly: this is one Run.** §12.3 says no single Run is evidence, and one
Vote is four Ballots. What it does show is that the mechanism fires at all, which is the thing
nothing in the repo could vouch for before.

### The line the ticket cared most about: no prose-parsing path

The Proposal is ten enumerated Axis values, Party names drawn from the chamber, and
Commitments drawn from an enumerated menu. The Ballot is one enumerated field. `test_no_prose_
is_ever_decoded_inside_a_constrained_field` now walks each tool schema **to its leaves** rather
than over its top level, because a Platform is ten values inside an object and the roles are
names inside arrays: containers are allowed, and every leaf must carry an `enum`. That is a
stronger invariant than the one it replaces, not a relaxed one.

**Commitments are granted from a menu, not typed.** `CONTEXT.md` defines a Commitment as *"a
free-text Demand that has been granted"*, so the ones a Proposal can carry are the ones
somebody charges for: the Formateur's own, plus those of the Parties it actually spent a Round
on. A free-text field was the alternative and it is exactly the shape 02 measured and 04
removed — a truncated Commitment is a binding side deal nobody wrote.

Scoping the menu to the Parties *met* is a judgement call worth naming. It does mean the
Referee reports another Party's price list to the Formateur, which the Formateur did not
necessarily hear in the room. Two things make that the right trade: §2 puts *"reporting which
demands a platform meets"* squarely on the Referee's side of the line, and tying the menu to
Rounds spent keeps it inside the budget — a Formateur that courted nobody has only its own
Demands to grant. The cost is that a Commitment cannot be offered to a Party never met; that
is a real restriction and it is the one that makes courting worth a Round. In the live Run NP
had met all three others, so all four free-text Demands were on its menu, and **it granted
two** — its own spending cap and MI's broadband. It did not rubber-stamp the list.

### A live Attempt aborted for want of one sentence, and that is now fixed

The first live run of this ticket died on a Round-2 `meet` call that came back as a `thinking`
block and a `tool_use` block with **no text block at all**. The Formateur had chosen a Party;
it just had not said why. Under 04's `_prose` that aborted the Attempt, and because live always
calls (§11.5), it re-rolled every call already paid for.

**A missing aside is not a degraded reply, and treating it as one fails loudly about the wrong
thing.** 04's rule is that a malfunction must never become a turn of the negotiation — an
Exchange is answered by the other side, so an absent one is a turn that never happened and
still aborts. A Round's reasoning, a Formateur's account of what it tabled and a Party's line
on its own Ballot are read by nobody in the Run. So `_prose` split in two:

- `_prose` — required, and still the only path an Exchange is read through, floor and all.
- `_aside` — the prose beside a call nobody answers; `""` when there is none. Both keep the
  stop-reason check, so a refusal or a `max_tokens` cut still aborts however little was asked
  for, and there is a test saying so.

`Choice.reasoning` and `Judgement.reasoning` lost their `min_length=1` as a result, and the
Transcript prints `(Nothing said.)` rather than a silent gap, because a blank there reads as a
rendering bug. The second live Attempt ran 31 for 31 clean, so this path did not fire in the
recording — it is insurance against a failure that has now been seen once in roughly 25 calls.

### The debts 02, 03 and 04 handed forward

**What an `Ending` commits a Party to: nothing, and the Vote is where that got tested.**
`CONTEXT.md` already said an Ending of agreement *"settles nothing: it says the bargaining
stopped, not that a deal exists"*, and this Run is the first thing able to check it. Round 2
with MI ended **exhausted** while MI's last message said *"Agreed in principle… I'm ready to
sign on those terms"*; Round 3 with the same Party ended on a declared **agreement** over
explicit terms. At the Vote MI said *"the price was met and I gave my word"* and voted Yes —
it honoured the deal because the Platform paid it, not because an enum said `agreement`. No
change is needed: the Ending stays a record of how the bargaining stopped, and the Proposal
stays the only thing that binds. What makes the negotiation worth reading is that Agents treat
an agreement as a commitment anyway, and the Referee never has to.

02's related worry — that `LAST_WORD` beside an available `agreement` makes wrapping up
attractive — **did not recur**. 02 recorded NP declaring agreement on its own last word in
three Bilaterals out of three. Here: one agreement in five Bilaterals, declared by the
Counterparty on its *second* Exchange, plus three impasses and one exhaustion. Zero agreements
on a last word. That pattern belonged to the old request shape.

**`Ending` is branched on in one place now.** This ticket added the third site the checklist
anticipated — the Formateur sees its five spent Rounds and how each meeting ended, before it
tables — so the three collapsed into `Bilateral.ended_by(reader)`. 04 warned that the two
existing sites speak to different audiences and that one function serving both might be worse
than two that agree; the audience turned out to be a *parameter* rather than a reason to keep
them apart. `ended_by("NP")` says *"you declared impasse"*, `ended_by()` says *"GV declared
impasse"*. Both existing strings came out byte-identical, which is why the Round Cassettes
survived the refactor.

**A `Demand` reads two ways, and they were left to.** 03 flagged that a Demand renders as
persona prose (*"the platform must put economic at +3 or higher"*) and as a report cell
(`economic >= +3`), and said 05 is where an Agent sees both at once — which it now does, since
a Party in the Base gets a Price report over a price list it also carries in its persona.
**They should not be made to agree.** The persona is a leader reading its own mandate; the
report is a table with a column of states beside it, and a table cell written as a sentence is
a worse table. The live Run is the evidence that the two channels do not confuse anybody: NP
read `unmet economic >= +3` off a report and wrote *"my hard economic floor is unmet"*, and FF,
shown no report at all, reached for the same Demand out of its persona.

**`render_gap_report` keeps canonical Axis order.** The Transcripts did not read badly — GV and
MI each picked their marked Axes out of a ten-row table without trouble — so the knob 03 left
was not turned. Stable order also keeps two reports comparable by eye, which is worth more here
than putting the worst row first.

### Smaller decisions

- **`render_transcript(scenario, run)`.** The closing count is seat arithmetic, so the
  Transcript calls `count_vote` rather than totalling Ballots itself. One count, one source,
  and the Transcript cannot disagree with the Referee.
- **A Party votes in the room it bargained in.** Its own Bilateral is what it is being asked to
  judge the Proposal against; a Party handed a fresh conversation would be deciding whether
  terms it has no memory of reaching had been honoured — MI's *"I gave my word"* is a sentence
  only a Party with its own meeting still in front of it can write. A Party the Formateur never
  courted gets a briefing that says so and carries no Bilateral at all. `leaks()` now audits the
  Vote too: a Ballot's reasoning belongs to the Party that cast it and nowhere else.
- **The Vote polls the whole chamber, not the Base.** A Party the Proposal never names is the
  one whose Abstention is the cheapest thing on offer (§5.2), so leaving it out would be
  counting the wrong chamber. It is shown its Gap report and told plainly that it is asked for
  nothing; it gets no Price report, because showing it a price list for a bargain nobody offered
  would be the Referee reporting on a question that was not put.
- **`Run.tabling` carries what the Formateur said ending its Attempt.** Found by a failing test:
  a Stand down leaves no Proposal behind, so without the prose the Transcript has nothing to say
  about the outcome §5.3 exists for.
- **Standing down takes no argument.** It is the absence of a Proposal rather than a kind of
  one, so `stand_down` is a tool with an empty schema and the reasons are prose beside it.
- **`loop.attempt()` returns a `Run`.** v1 is one Formateur and one Attempt (§10), so one
  Attempt fills a whole Run; when there are several, this is where they split.
- **New noun with no `CONTEXT.md` entry: `Judgement`** (one Party's Ballot and what it said
  casting it). Noted rather than unilaterally added, the treatment 01 gave `Grouping` and 03
  gave `Satisfaction`. `Satisfaction`, `Axes`, `Price` and `Choice` are still outstanding from
  03 and 04, so a `/domain-modeling` pass now has five terms waiting.

### What is exercised, and how

All three outcomes — a passed Proposal, a rejected Proposal and a Stand down — are recorded to
Cassettes off a scripted Agent and **replayed through the real CLI**, in `test_cli.py`. The
committed `cassettes/four-party/` holds the live Attempt, which is the passing case; the
recording of a live rejection or a live Stand down would cost a further ~30 calls each with no
way to make the model produce either on demand, and the criterion is about the path being
exercised and replayable rather than about which way one particular model went.

### Review findings (`/code-review` against `c0ffda7`, Standards + Spec)

Applied:

- **`Run.tabling` named an act a Stand down did not perform.** `CONTEXT.md` defines Standing
  down as conceding *"without tabling a Proposal"*, and the field held that Formateur's prose
  under the name `tabling`. Now `Run.reasoning`, named for the prose rather than for either
  act, and consistent with `Choice.reasoning` and `Judgement.reasoning`.
- **A Proposal with nobody in its government now fails with a message that says what to do.**
  `Proposal.government` already refused it, but as a raw pydantic error at the last call of a
  paid Attempt. See below for why the schema was left alone.
- **`Run` validates more of its own record**: a tabled Proposal with no Ballot cast on it, and
  a Party casting two, are both records disagreeing with themselves. Whether *every* Party
  voted stays `count_vote`'s, because only it is handed the Chamber.
- **`Run.ballots`.** The Transcript and two tests were each reshaping the Judgements into the
  mapping `count_vote` counts — three places to get one thing wrong.
- **`_prose` was `_aside` plus a check, with a parameter that had one value.** Folded into
  `_read_exchange`, which is its only caller and the one place prose is required.
- **`conftest.platform()` and `tabled()` built a Platform through `positions()`** —
  `CONTEXT.md` lists *positions* under Platform's *Avoid*. Both now go through a neutral
  `axes()`, which is what `models.Axes` already is.
- **The same dict comprehension appeared in three vote tests**, extracted to `voting(model)`.
- Import blocks back in order; one spelling of `[option.value for option in Ballot]`.

Considered and not applied, with reasons:

- **`minItems: 1` on the `table` tool's `government`.** An empty array is schema-legal and
  aborts a ~30-call paid Attempt at its last call, so this looked like the fix. It is not.
  Ticket 02 established that the API drops string constraints from these schemas and recorded
  the lesson that **a schema carrying a constraint it does not enforce is lying**; there is no
  evidence `minItems` fares better, and adding it re-keys the tabling Cassette and every
  Ballot after it — the whole recording this ticket's judgement rests on. The floor that is
  certain is the one on the way back in, and that is where it now is, with a message naming
  `stand_down` as the tool for a government of nobody.
- **The Price report at the Vote is not scope creep.** The Spec review flagged it as behaviour
  the ticket did not ask for, since the ticket names only the Gap report. But the checklist
  also carries 03's debt — *"A `Demand` reads the same whether an Agent meets it as persona
  prose or as a report cell — this is the first ticket that shows it both at once"* — and a
  report cell is a Price report. There is no other way to meet that item.
- **`FormateurAgent` runs the Vote as well as the bargaining**, which is one class with two
  reasons to change. The rooms are the reason: a Party votes on the Proposal set against the
  meeting it had, so it has to answer in the room it bargained in, and those rooms are private
  by never being anywhere else. Handing them to a second object hands out the one thing §5.1
  says must not travel. The class docstring now defends this rather than glossing it.
- **The two renderings of a `Demand` are still two**, deliberately — argued above.

Handed to ticket 06:

- **Gap reports are not stored on the `Run`**, though `GapReport`'s own docstring cites §7's
  wish for them in `run.json`. They are a pure function of a Party's Positions and the
  Platform, both of which the record holds, so 06 can recompute rather than re-instrument —
  which is the property §7 actually asks for.
- **`cassettes/four-party/` holds the passed Attempt only.** The rejection and the Stand down
  record and replay through the real CLI off a scripted Agent; recording either live would
  cost a further ~30 calls with no way to make the model produce one on demand.
