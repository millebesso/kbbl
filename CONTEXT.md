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

**Party**:
One of the parliamentary parties, defined by a hand-written mandate: seats, Positions,
Exclusions and its two price lists.
_Avoid_: faction, actor, participant

**Formateur**:
The Party currently trying to form a government. It alone chooses whom to meet, and it alone
tables a Proposal.
_Avoid_: leader, PM candidate, convener, initiator

### The party mandate

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
Attempt without spending one of the chamber's four votes, so Attempts and failed votes are
not one-to-one.
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

**Exchange**:
One message from one side of a Bilateral. Each side may send up to three, and either side may
exit early by agreeing or declaring impasse.
_Avoid_: message, turn, reply

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

**Commitment**:
A free-text side deal a Proposal carries — a free-text Demand that has been granted. Agents
interpret Commitments; the Referee never reads them. An Axis Demand is never a Commitment: it
is granted by the Platform itself.
_Avoid_: pledge, promise, concession, side letter

### Distance

**Gap**:
The distance on one Axis between a Party's Position and a Proposal's Platform. Also used of
the summaries over all ten — *mean Gap*, *worst Gap*.
_Avoid_: distance, delta, divergence, drift

**Gap report**:
The table the Referee shows a Party before it judges a Proposal, naming its own worst Gaps.
It is feedback, never a constraint — the sole defence against Agents drifting into a mushy
grand coalition.
_Avoid_: distance table, scorecard, diff

### The vote

**Negative parliamentarism**:
The Riksdag's rule that the chamber votes on whether to *reject* a government, not to install
one. A Proposal passes unless a Blocking minority votes against it.
_Avoid_: the vote rule, investiture, confidence vote

**Blocking minority**:
The 175 seats — an absolute majority of 349 — that must vote No to defeat a Proposal.
Anything short of it lets the Proposal through.
_Avoid_: majority, threshold, quorum, 175 rule

**Abstention**:
A vote that is neither Yes nor No. Under Negative parliamentarism it is the cheapest thing a
Formateur can buy: a Party that will neither join nor support can still be paid to step out of
the way.
_Avoid_: pass, neutral, absence, non-vote

**Re-election**:
The terminal state a Run reaches when the chamber's four votes are spent, or every Party has
had an Attempt. Nothing after it is modelled.
_Avoid_: new election, snap election, do-over, failure

### Running and validating

**Scenario**:
A complete set of Party mandates whose seats sum to 349. The input to a Run.
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

**Transcript**:
The human-readable record of a Run — every Bilateral, the Proposal, the vote. Read closely,
never counted.
_Avoid_: log, output, report
