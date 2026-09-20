# KBBL

KBBL simulates the negotiation that follows a Swedish general election: LLM party agents
bargain over a government while a deterministic referee owns all arithmetic and procedure.
This file is the glossary that negotiation is described in — nothing else. Design lives in
`docs/kbbl.md`.

## Language

### Actors

**Referee**:
The deterministic code that computes and reports — seat arithmetic, Gaps, demand
satisfaction, vote counting, procedure. It never constrains an Agent's choice, and it never
parses prose.
_Avoid_: engine, orchestrator, judge, arbiter, simulator

**Agent**:
The LLM instance negotiating on behalf of one Party for the length of a Run. Agents hold
judgement; the Referee holds certainty.
_Avoid_: bot, player, model, LLM

**Persona**:
A Party's Mandate as its Agent receives it: everything true of the Party for the length of a
Run, written as prose it can act on. The Referee never reads a Persona, and nobody an Agent
meets has seen it.
_Avoid_: prompt, system prompt, character, briefing

**Party**:
One of the parliamentary parties, defined by a hand-written Mandate: seats, Positions,
Exclusions and its two price lists.
_Avoid_: faction, actor, participant

**Formateur**:
The Party currently trying to form a government. It alone chooses whom to meet, and it alone
tables a Proposal.
_Avoid_: leader, PM candidate, convener, initiator

### The party mandate

**Mandate**:
Everything one Party is defined by — its seats, Positions, Exclusions and two price lists —
hand-written before a Run and never changed by one. Two neighbouring senses are not this one:
a single seat is a *seat*, and a Formateur's commission to try is an *Attempt*.
_Avoid_: profile, config, party file, spec, definition

**Positions**:
A Party's own value on each of the ten Axes — what it went to the election on. Distinct from
a Platform, which is what a Proposal offers.
_Avoid_: manifesto, stance, views, preferences

**Axis**:
One of the ten policy dimensions (economic, environment, military, health, immigration,
law & order, education, transport, social, international), each scored -5..+5.
_Avoid_: issue, dimension, topic, policy area

**Demand**:
A price a Party names for joining or backing a government. Either an Axis constraint, which
the Referee can check, or free text, which only Agents can interpret.
_Avoid_: condition, requirement, ask, term

**Governing price** (`to_govern`) and **Supporting price** (`to_support`):
The two lists of Demands — what a Party charges to sit in cabinet, and the normally lower
price of backing a government from outside. Two price lists, never one.
_Avoid_: conditions, terms, asking price

**Exclusion** (`prefer_not`):
A Party this one would rather not deal with. Always soft — every Exclusion has a price.
_Avoid_: veto, blocklist, red line, hard no

**Willingness to re-elect**:
A Party's stated appetite for facing the voters again rather than taking a deal. It is the
only outside option in the model and the reason a refusal costs anything. Persona only: the
Referee never reads it, and the Agent may conceal or overstate it.
_Avoid_: stubbornness, resolve, BATNA

### The negotiation

**Run**:
One complete simulation, from the first Formateur to either a formed government or a
Re-election.
_Avoid_: game, session, simulation, episode

**Attempt**:
One Formateur's entire effort — its Rounds and the single Proposal they lead to. An Attempt
ends when its Proposal is voted down, or when the Formateur Stands down without tabling one;
either way the role passes to the next-largest Party that has not yet had an Attempt.
_Avoid_: turn, try, mandate, go

**Standing down**:
A Formateur conceding at the end of its Rounds without tabling a Proposal. It ends the
Attempt without spending one of the Chamber's four Votes, so Attempts and Votes are not
one-to-one.
_Avoid_: giving up, conceding, forfeiting, passing

**Round**:
One unit of a Formateur's budget, spent on exactly one Bilateral. Five per Attempt — so the
Formateur cannot meet everyone, and choosing whom to court is the central strategic act.
_Avoid_: turn, step, iteration

**Bilateral**:
The private meeting with one other Party that a Round buys. *Private* is load-bearing: the
Formateur accumulates what it hears across every Bilateral, while each other Party knows only
its own. That asymmetry is the game.
_Avoid_: meeting, talks, session, negotiation

**Counterparty**:
The Party a Formateur meets in a Bilateral. It sees only its own Bilateral and is never told
the others happened — the half of the asymmetry that is easy to break by accident, since it is
kept by what a Party is never shown rather than by anything it is told.
_Avoid_: the other party, opponent, partner, invitee

**Exchange**:
One message from one side of a Bilateral. Each side may send up to three, and either side may
end the meeting early by carrying a Declaration on one of them.
_Avoid_: message, turn, reply

**Ending**:
How a Bilateral finished: by *agreement*, by *impasse*, or *exhausted* — three Exchanges each
way spent with neither. Exactly one per Bilateral, and it belongs to the meeting rather than to
either side. An Ending of agreement settles nothing: it says the bargaining stopped, not that a
deal exists. Only a Proposal binds anything, and only the Formateur tables one.
_Avoid_: close, verdict — and *Outcome* or *Result*, which name how a whole Run came out and
never how one meeting finished.

**Declaration**:
A side's announcement, carried on an Exchange, that the Bilateral is over — agreement or
impasse, the two Endings a side can reach for. It closes the meeting at once and the other side
gets no reply, so a Declaration is one Party's act even when the word is "agreement".
Exhaustion is never declared: it is what is left when nobody declares anything.
_Avoid_: exit, signal, flag, resolution

### The proposal

**Proposal**:
What a Formateur tables for a vote: a Platform, who governs, who supports, and any
Commitments. One per Attempt, and tabling it ends the Attempt.
_Avoid_: bid, deal, offer, package

**Platform**:
The single agreed value on each Axis that a Proposal commits its government to. Same units as
Positions, different owner.
_Avoid_: programme, policy, agreement, positions

**Government**:
The Parties taking cabinet seats under a Proposal. Cabinet portfolios are deliberately not
modelled.
_Avoid_: cabinet, coalition, ministry

**Support-only**:
The Parties backing a Proposal from outside cabinet. Their seats count against the Blocking
minority exactly as Government seats do — without that, the distinction is decorative.
_Avoid_: confidence & supply, backers, partners, supporters

**Base**:
Every Party behind a Proposal — Government and Support-only together — and the seats they hold
between them. One noun because they have one arithmetic: both count against the Blocking
minority alike. A Proposal assigns the role; nobody accepts it. A Party in the Base is free
to cast a No Ballot on the very Proposal it is named as governing under.
_Avoid_: backers, bloc, coalition, support base, underlag

**Commitment**:
A free-text side deal a Proposal carries — a free-text Demand that has been granted. Agents
interpret Commitments; the Referee never reads them. An Axis Demand is never a Commitment: it
is granted by the Platform itself.
_Avoid_: pledge, promise, concession, side letter

### What the Referee reports

**Gap**:
The distance on one Axis between a Party's Position and a Proposal's Platform. Also used of
the summaries over all ten — *mean Gap*, *worst Gap*.
_Avoid_: distance, delta, divergence, drift

**Gap report**:
The table the Referee shows a Party before it judges a Proposal, naming its own worst Gaps.
It is feedback, never a constraint — the sole defence against Agents drifting into a mushy
grand coalition.
_Avoid_: distance table, scorecard, diff

**Price report**:
The table the Referee shows of one price list against a Platform: which Demands it pays, which
it leaves outstanding, and which are not the Referee's to read. Like a Gap report it is a
report and never a verdict — a Party may waive a Demand it named, or walk away over one the
Referee has just called met.
_Avoid_: demand check, satisfaction report, price check, scorecard

**Unevaluated**:
What the Referee says about a free-text Demand. Not unknown for want of trying: it is not the
Referee's to read, and the only alternative is the Referee inventing a fact for an Agent to
act on.
_Avoid_: unknown, unchecked, pending, n/a

### The vote

**Chamber**:
The 349 seats a Scenario divides between its Parties, and the body that votes on a Proposal.
It owns the four Votes a Run may spend — the budget is the Chamber's, never any one
Formateur's.
_Avoid_: parliament, house, assembly, legislature

**Negative parliamentarism**:
The Riksdag's rule that the Chamber votes on whether to *reject* a government, not to install
one. A Proposal passes unless a Blocking minority votes against it.
_Avoid_: the vote rule, investiture, confidence vote

**Blocking minority**:
The 175 seats — an absolute majority of the Chamber — that must vote No to defeat a Proposal.
Anything short of it lets the Proposal through.
_Avoid_: majority, threshold, quorum, 175 rule

**Grouping**:
A set of Parties counted together, and the seats they hold between them. Pure arithmetic — a
Grouping is Parties the Referee has added up, never Parties that have agreed to anything. The
ones worth naming are the *minimal* Groupings reaching the Blocking minority, where no member
can be dropped: they name each kingmaker exactly once, and one of them pairing two Parties that
would rather not deal with each other is the normal case, not a bug.
_Avoid_: bloc, coalition, alliance, set

**Vote**:
The Chamber's single decision on one Proposal. A Run may hold four, and only a tabled Proposal
spends one — which is why Standing down costs the Chamber nothing, and why Attempts and Votes
are not one-to-one.
_Avoid_: division, ballot, round of voting, investiture

**Ballot**:
One Party's Yes, Abstain or No in a Vote. It carries every seat the Party holds — a Party's
seats are never split — and every Party casts one, including the Parties a Proposal never
names. It is exactly those Parties whose Abstention is the Formateur's cheapest route to
power.
_Avoid_: vote, choice, verdict, position

**Count**:
A Vote's arithmetic written down: the seats cast each way, the Base's seats, and whether the
Proposal passed. Not a second name for the Vote — the Vote is the Chamber's decision and the
Referee reckons it once; a Count is that reckoning recorded, so reading a Run back needs
neither the Scenario's seats nor a second pass over the Ballots.
_Avoid_: tally, result, score, totals

**Abstention**:
A Ballot that is neither Yes nor No. Under Negative parliamentarism it is the cheapest thing a
Formateur can buy: a Party that will neither join nor support can still be paid to step out of
the way.
_Avoid_: pass, neutral, absence, non-vote

**Re-election**:
The terminal state a Run reaches when the Chamber's four Votes are spent, or every Party has
had an Attempt. Nothing after it is modelled.
_Avoid_: new election, snap election, do-over, failure

### Running and validating

**Scenario**:
A complete set of Party Mandates whose seats sum to the Chamber's 349. The input to a Run.
_Avoid_: setup, config, dataset, world

**Fixture**:
A Scenario in every respect — same shape, same loader, same 349 seats — that happens to be
small, fictional, and built so the right answer is obvious: a landslide, a knife-edge
kingmaker, a forced deadlock. Used to test the Referee.
_Avoid_: test case, sample, dummy

**Probe**:
A single question put to one Agent in isolation to test its judgement, with no negotiation
around it — typically an offer it plainly ought to refuse.
_Avoid_: eval, benchmark, test, assay

**Cassette**:
A recorded request/response pair on disk, keyed by a hash of the request, letting a Run replay
without calling the model.
_Avoid_: fixture, mock, snapshot, tape, VCR

**Ledger**:
The Run record as it is written — the one place an Exchange, a Ballot, a Gap report or a
request's cost is entered, at the moment it happens rather than when the Attempt ends. A Run
that breaks mid-Bilateral keeps everything it has already paid for.
_Avoid_: recorder, logger, collector, accumulator, buffer

**Outcome**:
How a Run came out, in the one word a batch of Runs is counted by: *formed*, *rejected*,
*stood down* — or *unfinished*, a Run that stopped rather than ending. The fourth is named
rather than left as a gap, so that counting a batch never reads a broken Run as a Stand down.
_Avoid_: status, verdict, state, ending

**Usage**:
What one request to the model cost — its tokens in and out, what was written to and read from
the cache — and the key of the Cassette holding it. Recorded as each reply arrives, because
the reply is the only place the numbers exist and no Transcript can be asked what it was
billed. The Cassette key beside them is the one handle on what was actually sent.
_Avoid_: cost, tokens, metrics, telemetry, billing

**Transcript**:
The human-readable record of a Run — every Bilateral, the Proposal, the Vote. Read closely,
never counted. Written as `transcript.md`.
_Avoid_: log, output, report

**Record**:
The complete structured record of one Run, written as `run.json`: every Exchange, every
Choice and its reasoning, the Proposal, every Ballot, every Gap report shown, and what each
request cost. Counted in batches, read by nobody — the Transcript is the one that is read. It
carries the Referee's arithmetic beside it and stands alone: aggregating a batch is a loop and
a `Counter`, never a re-instrumentation.
_Avoid_: dump, log, trace, export

**Result**:
The one-line answer with a date on it, written as `result.json`: the Outcome, who governs, and
when it was predicted. KBBL predicts an open question rather than settling one, so comparing a
Run against the real government should be a lookup.
_Avoid_: summary, verdict, conclusion
