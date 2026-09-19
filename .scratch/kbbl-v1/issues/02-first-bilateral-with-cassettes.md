# 02 — First Bilateral against a live model, recorded to Cassettes

**What to build:** One Formateur meets one Party privately and they bargain. Up to three
Exchanges each way, with either side free to exit early by agreeing or declaring impasse. The
conversation prints as a readable Transcript. Every request and response is written to a
Cassette keyed by a hash of the request, so `--replay` reruns the meeting for free.

**This is the ~$0.02 test the rest of v1 is built outward from** (§10). The riskiest assumption
in the project is not the arithmetic — it is whether LLM Party agents produce a negotiation
worth reading, or agree in round one. This ticket answers that, and the answer should be
written down before ticket 04 builds more machinery on top of it.

Cassettes land here rather than later because §8 is explicit: retrofitting record/replay means
re-plumbing every call site, so it goes in with the first call that is ever made.

**Blocked by:** 01.

**Status:** done

- [x] A Formateur and one other Party hold a private Bilateral of up to three Exchanges each way
- [x] Either side may exit early by agreeing or declaring impasse, and the Transcript shows which happened
- [x] Persona is built from the mandate: Positions, Governing price, Supporting price, Exclusions, Willingness to re-elect
- [x] Willingness to re-elect reaches the Agent as a disposition it may conceal or overstate — never as a number the Referee reads (§3)
- [x] Exclusions reach the Agent as soft preferences carrying a price, never as hard constraints (§3)
- [x] Every request/response is written to a Cassette keyed by a hash of the request
- [x] `--replay` reruns the Bilateral from Cassettes with zero API calls and an identical Transcript
- [x] Live is the default; `--replay` opts out (§11.5)
- [x] Model is `claude-sonnet-5`, with prompt caching on the stable persona prefix (§6)
- [x] Exchanges accumulate into an in-memory run record for ticket 06 to serialise — not printed and discarded
- [x] **Read the Transcript closely and record the judgement in this file's Comments: do the parties bargain, or fold immediately?** This is the deliverable, not a formality (§12.1)

## Comments

**Implemented.** `uv run kbbl run fixtures/four-party [--meet PARTY] [--replay]` holds one
Bilateral and prints the Transcript. 72 tests, `mypy --strict` clean. Three Bilaterals are
recorded under `cassettes/four-party/` — NP↔FF, NP↔MI, NP↔GV — and all three replay for free.
The test suite itself makes zero API calls.

New modules: `cassettes.py` (the single seam through which a Run reaches the model,
content-addressed by a sha256 of the canonical request), `agents.py` (`persona()` and
`bilateral()`), `output.py` (`render_transcript()`). `models.py` gained `AXIS_POLES`, `Ending`,
`Declaration`, `Exchange`, `Bilateral` and `Run`.

### §12.1 — the judgement: do the parties bargain, or fold?

**They bargain, and the two price lists are what makes them.** This is the answer the rest of
v1 was waiting on, and it is a yes. Read all three Transcripts; the short version:

- **NP↔FF is the real test, and neither side folded.** NP opened at its stated price (economic
  ≥ +3, law & order ≥ +3, a binding spending cap). FF counter-anchored at economic ≤ −2 for
  cabinet and refused to move. Both sides then did the thing the model exists to make possible:
  they concluded the *cabinet* gap was unbridgeable, said so explicitly, and moved to the
  cheaper Supporting price instead. FF held at exactly 0 and refused +1 — *"I'm not going to be
  the party that let a market-lean platform through by a single point and then have to explain
  that gap to my own voters"* — and NP paid it, conceding three points from its opening
  economic number in exchange for abstention rather than support. **That is §3's claim about two
  price lists doing real work, confirmed on a live run.**
- **NP↔MI shows the price lists sorting correctly in the other direction.** MI's Positions were
  already close to NP's on economic and law & order, so there was nothing to fight about there
  and MI did not manufacture a fight. It charged on its *own* axes instead — international ≥ +3
  and the rural broadband programme funded in full — and, because the platform was cheap for it,
  bid *up* to cabinet rather than settling for support. Cheap agreement on shared ground bought
  a higher-priced arrangement, which is exactly the right shape.
- **NP↔GV prices an Exclusion, which is the §3 requirement that was most at risk.** NP lists GV
  as an Exclusion. Nothing behaved like a veto. GV set its Governing price deliberately out of
  reach (environment ≥ +4, transport ≥ +3, no new motorways) and *said* it was doing so — *"I
  doubt that's a place you want to be, and honestly it's not obviously where mine want me
  either"* — then sold abstention at environment ≥ +2 and held that number against two rounds of
  push-back. NP paid a four-point swing on an axis it had campaigned on. **A soft preference
  carrying a price is what actually happened.**

**Willingness to re-elect reached the Agents as disposition and never as a number** — but the
Fixture cannot show much more than that, and an earlier draft of this judgement overstated it.
`_DISPOSITIONS` bands 0..10 at ceilings 1/3/6/8/10, and the Fixture's values land like this:

| Party | Willingness | Band prose actually sent |
| --- | ---: | --- |
| MI | 2 | *"You would much rather take a deal than face the voters again so soon."* |
| NP | 4 | *"You could live with another election. You would rather not have one."* |
| FF | 6 | *"You could live with another election. You would rather not have one."* |
| GV | 8 | *"You are comfortable going back to the voters, and a bad deal is worse to you than an election."* |

**NP and FF are sent identical prose**, because 4 and 5 and 6 share the middle band. Two of the
five bands are unused by this Fixture. So of the three Bilaterals only GV's and MI's say
anything about the disposition prose steering behaviour — and both are consistent with it: GV
twice threatened an election and used it as leverage, MI never threatened one and moved fastest
to terms.

The NP/FF pair turns out to be the more interesting result precisely *because* the prose was
identical. Given the same disposition, NP conceded three points on economic and FF held its
number and extracted them. **Whatever separated those two, it was their Positions and price
lists, not their appetite for an election** — which is a cleaner demonstration of §3's claim
than the disposition prose could have given.

The number itself never reaches an Agent: `_another_election` renders only the band prose, and
nothing in the request or the Referee reads the integer.

**Two things to fix before this evidence is reused.** The bands are too coarse in the middle to
distinguish the Fixture's two largest Parties, and the Fixture picks no value in the outer two
bands, so three of five are exercised. Either reband or reseat before ticket 04 leans on
willingness-to-re-elect as a behavioural lever.

**Nobody agreed in round one.** Every Bilateral ran to five Exchanges. The shortest path to
terms was still three rounds of genuine price discovery.

**What to watch, on three samples.** NP declared `agreement` on its own last word in all three
Bilaterals. Because that is NP's third Exchange, the counterparty never replies — so the
recorded Ending is one side's declaration, not a mutual one. In each case the counterparty had
effectively converged the turn before, so nothing here is wrong; but `LAST_WORD` plus an
available `agreement` option may simply make wrapping up attractive, and ticket 05 needs to
decide what a Bilateral's Ending actually commits a Party to. Earlier recordings (since
re-recorded) ended on the *counterparty* agreeing, at four and six Exchanges, so the endings do
vary.

**The chamber briefing reads correctly.** An earlier run had a Party invert Negative
parliamentarism (treating 175 as the threshold to *install*). It did not recur: NP reasoned
*"together we hold exactly the seats needed to stop any no-confidence motion from reaching
175"*, which is right, and matches the seat table's `NP + MI 175 (+0)`. No change needed to
`_the_chamber`.

### The finding that matters for ticket 04: structured outputs degrade under this prompt shape

**`minLength` is not enforced by structured outputs, and a schema that carries it is lying.**
The API drops string constraints (`minLength`/`maxLength`) from a `output_config.format` schema
— documented, and confirmed the hard way: an Agent returned an empty `message` from a schema
asking for 200 characters. An earlier session added `minLength: 1` to stop empty messages and
recorded it as a fix; **it was a no-op**, and the empty messages had merely stopped by chance.
The floor is now enforced in `_read` on the way back in (`MIN_MESSAGE`), which is the only
place it can be, and a regression test asserts the schema does *not* carry a `minLength`.

**Roughly one live call in eleven came back degraded** — four distinct malfunctions across the
session's ~45 live calls, every one with `stop_reason: "end_turn"` and hundreds of thinking
tokens spent:

| Manifestation | Example |
| --- | --- |
| Empty string | `""` |
| Truncated stub | `"Let's be clear on what "` (23 chars) |
| Leaked JSON structural character | `", let me just write.}"` (21 chars) |
| Token-seam corruption + leaked escape | `"Cab inet ... is n't a price , it 's ... work .\" to be precise"` |

The common thread is that the model is being asked to emit two or three paragraphs of free
prose *inside a constrained JSON string*, and the constrained decoder is what breaks: leaked
structural characters, premature string termination, and detokenization seams. The 200-character
floor catches the first three; the fourth is long enough to pass it and was only caught by
reading. **This is a shape problem, not a prompt problem, and ticket 04 should not build a
five-Round Attempt on top of it without addressing it.** The obvious alternative is to let the
message be the assistant's ordinary text and take only the Ending through a tool call — which
still honours "the Referee never parses prose", because it would read the tool call, not the
message. Sharpening the `message` description to demand a whole, written-out reply did
measurably help (three clean Bilaterals on first attempt afterwards), but it is mitigation, not
a fix.

**A malfunction now aborts the Run rather than becoming a turn of the negotiation.** That is
deliberate. In the worst observed case the other side read a 23-character fragment as the
opening of a sentence and *wrote the rest of it*, so a decoding artifact silently became a
bargaining position. Failing loudly is worth the aborted Run. The cost is that recording is
flaky: because live always calls, a Run that dies on its fifth Exchange re-rolls all five when
re-run. A retry policy inside `Cassettes` would fix that, but it muddies "a recording is what
happened" and is a ticket-04 decision, not this one.

### Other decisions worth knowing about

- **Live always calls; a recording is not a cache.** `--replay` is the only free path (§11.5).
  Re-running live overwrites the Cassette for an identical request.
- **Cassettes are content-addressed and chain naturally.** Each request embeds the prior
  Exchanges verbatim, so replaying turn *n* reproduces the exact request for turn *n+1*. The
  "identical Transcript" criterion falls out of that rather than being engineered. The flip side:
  any change to a persona, briefing or the schema re-keys every Cassette downstream of it, and
  the old ones are orphans that must be deleted by hand.
- **Two system blocks, `cache_control` on the first only.** Block 1 is persona + chamber (stable
  for the whole Run, cached); block 2 is this meeting. Measured: ~1,750 tokens written to cache
  and read back on every subsequent turn, comfortably over Sonnet 5's documented 1,024-token
  minimum, so caching genuinely fires. The seam exists so ticket 04's accumulated Formateur
  knowledge can go in block 2 without breaking the cached prefix.
- **`AXIS_POLES` moved into `models.py`.** A bare `economic: +5` is meaningless to an Agent, so
  the poles travel with the number. Duplicated in prose in `fixtures/README.md`; both copies
  cross-reference each other.
- **`--meet` is an explicit placeholder** for the choice ticket 04 hands the Formateur. Defaults
  to the largest other Party, and is flagged as a placeholder in `--help` and the README.
- **Ticket 01's CLI tests were rewritten.** `kbbl run` now negotiates, so the old tests would
  cost money per run. They record a Bilateral against a scripted stand-in and replay it through
  the real CLI; the behaviour under test is unchanged.
- **The test stand-in obeys the same floor the Referee enforces.** `spoken()` in `conftest.py`
  pads a scripted one-line message up to `MIN_MESSAGE`, and `said()` names what it becomes, so
  tests stay readable without bypassing the contract the live path is held to.
- **New nouns with no `CONTEXT.md` entry: `Ending` and `Declaration`.** Per `docs/agents/domain.md`
  these are noted, not unilaterally added to the glossary — the same treatment ticket 01 gave
  `Grouping`. All three are worth a `/domain-modeling` pass.

### Review findings (`/code-review` against `71e1f58`, Standards + Spec)

Applied:

- **`_Side.speak` no longer mutates stored history** to add the last-word nudge. It built the
  nudge into `_messages` permanently, which made a Cassette's key depend on how many times a
  side had been asked to speak rather than on what was said. Harmless today — a side never
  speaks again after its last word — but a trap for ticket 04, which reuses a `_Side` across
  Rounds. The nudge is now added to a per-request copy (`_asked`), and the committed Cassettes
  re-key identically, which is the proof it was equivalent.
- **Glossary compliance on identifiers** (`CONTEXT.md`, Bilateral: *Avoid: meeting*):
  `_this_meeting` → `_this_bilateral`, `meeting` → `met` in `cli.py`, and the `test_agents.py`
  helper → `hold_bilateral`. The Agent-facing prose still says "THIS MEETING" deliberately —
  `CONTEXT.md` defines a Bilateral *as* "the private meeting", and Agents should not be taught
  project jargon.
- **Constant docstrings** on `CASSETTES` and `_INDENT`, matching the convention `referee.py`
  set with `BLOCKING_MINORITY`.
- **The README excerpt** quoted Agent prose containing "stance" (*Avoid* for Positions);
  swapped for a different clause of the same Exchange.

Considered and not applied, with reasons:

- **`output.py` is not renamed to `transcript.py`.** The glossary bans "output" as a synonym
  for Transcript and the module docstring did read as though the module *were* the Transcript
  — that part is fixed. But `docs/kbbl.md` assigns `output.py` three artifacts
  (`transcript.md + run.json + result.json`), so the module is correctly named for the scope
  ticket 06 gives it, and renaming it to one of its three outputs would be worse. Ticket 01's
  Comments already flag this seam; it belongs to ticket 06.
- **`--meet` and `--cassettes` are scope creep, knowingly.** `--meet` is what made the §12.1
  judgement possible at all — one pairing is not evidence about whether Parties bargain, and
  NP↔GV (the Exclusion) is the pairing that tests §3 hardest. `--cassettes` exists so the test
  suite can record into `tmp_path` instead of the repo. Both are cheap to withdraw; `--meet`
  should be withdrawn by ticket 04 when the Formateur makes the choice itself.
- **Three Bilaterals and 15 Cassettes committed** where the ticket says "one Formateur meets
  one Party". The extra two are evidence for the deliverable, not extra product surface.

Left for later tickets:

- **The `Run` record is assembled after `bilateral()` returns** (`cli.py`), so a Run that
  aborts mid-Bilateral discards every Exchange already paid for. That matters more now that a
  malfunctioning reply aborts the Run. It also carries no token/cache usage and no Cassette
  keys, which §7 wants present so that aggregation is "a loop and a `Counter`". Ticket 06 owns
  the run record; this should land with it.
- **`Ending` is branched on in two modules** (`agents.py::_read` and `output.py::_ending`).
  Fine at two; worth collapsing if ticket 05 adds a third.
