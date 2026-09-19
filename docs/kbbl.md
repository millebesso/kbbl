# KBBL

**An LLM-driven simulator of government formation in the Swedish Riksdag.**

Status: design agreed, not yet implemented. Supersedes the original project brief.
Last updated: 2026-09-19. Vocabulary is canonical in `CONTEXT.md`.

---

## 1. What it is

KBBL simulates the negotiation that follows a general election in a 349-seat parliament.
Each party is an LLM agent acting from a mandate defined in JSON; a deterministic referee
owns all arithmetic and procedure.

**Outcomes are not reproducible.** The same election run twice may produce two different
governments. This is accepted and shapes every other decision in this document — in
particular, it is why validation happens at the level of individual agent decisions rather
than whole runs (§8).

---

## 2. Architecture: the line between agent and referee

The load-bearing decision. Everything else respects it.

| Referee (code, certain)                   | Agents (LLM, judgement)                  |
| ----------------------------------------- | ---------------------------------------- |
| Seat arithmetic, the 175 threshold        | Whom to approach, what to offer          |
| Vote counting, pass/fail                  | Whether a price is worth paying          |
| Formateur ordering, round budget          | Whether to bluff, hold, or fold          |
| Per-axis gap computation                  | What a free-text demand means            |
| Reporting which demands a platform meets  | Whether a stated preference is overridable |

**The referee computes and reports; it never constrains.** Gap reports and
demand-satisfaction reports are shown to agents as *feedback*. No value in a party's input
file binds a vote. An agent is always free to act against its own stated mandate — it just
has to do so knowingly.

**The referee never parses prose.** Agents emit structured output for anything the referee
consumes: the proposal, the vote, the demand list. Prose exists for the transcript only.
Regexing a proposal out of natural language is the most common way an agent simulation
becomes unreliable.

The mechanism is a **tool call**, not `output_config.format`, and the two are not
interchangeable here. Ticket 02 measured roughly one live call in eleven coming back empty,
truncated or carrying a leaked JSON character whenever two or three paragraphs of prose were
decoded inside a schema's string. So prose is the reply's own text and every field the
referee reads is a short enumerated tool argument beside it. The rule above is unchanged —
strengthened, if anything: the referee reads the call and never the message.

---

## 3. Data model

One JSON file per party.

| Field                    | Type                        | Notes                                        |
| ------------------------ | --------------------------- | -------------------------------------------- |
| `name`                   | string                      |                                               |
| `seats`                  | int                         | Must sum to 349 across the scenario           |
| `positions`              | 10 axes, each `-5..+5`      | See below                                     |
| `prefer_not`             | list of party names         | **Soft.** Every exclusion has a price.        |
| `to_govern`              | list of demands             | Price of joining the cabinet                  |
| `to_support`             | list of demands             | Price of supporting from outside — normally lower |
| `willingness_to_re_elect`| `0..10`                     | Persona only; the referee never reads it      |

**Policy axes:** economic, environment, military, health, immigration, law & order,
education, transport, social, international.

**Demands** come in two forms, freely mixed:

```json
{
  "to_govern": [
    { "axis": "environment", "op": ">=", "value": 3 },
    { "text": "no new nuclear this term" }
  ],
  "to_support": [
    { "axis": "environment", "op": ">=", "value": 1 }
  ]
}
```

Axis constraints are machine-checkable and the referee reports on them. Free-text
commitments are interpreted by the agents. Both are needed: most real demands are
positions on an axis, but the ones that give a negotiation its texture ("no NATO
application", "drop the investigation") have no axis and never will.

**Two price lists, not one.** Governing costs more than supporting — you own the
compromises and your ministers defend them publicly. Without the distinction, buying an
abstention costs as much as buying a cabinet partner, and the formateur loses its cheapest
path to power.

**Willingness to re-elect is a bluffing parameter.** It is the only outside option in the
model, and it is what makes a refusal cost something. It is written into the agent's
persona as a stated disposition; the agent may conceal it, overstate it, or be argued out
of it. Re-election is a terminal state — the simulation never models what follows — so the
value is never tested or paid out.

---

## 4. What a proposal is

```
Proposal {
  formateur:    "S"
  platform:     { economic: -2, environment: +3, ... }   # one agreed value per axis
  government:   ["S", "MP"]                              # cabinet members
  support_only: ["V"]                                    # confidence & supply, no cabinet
  commitments:  ["no NATO bid this term"]                # free-text side deals
}
```

No ministries. Cabinet portfolios are deliberately out of scope: modelling them requires
inventing a ministry list *and* a per-party valuation of each post, which is a second
preference model this project does not have.

Support-only seats count toward the threshold. Without that, the government/support
distinction is decorative.

---

## 5. Mechanism

### 5.1 A round is one private bilateral

Each round the formateur picks **one** party and meets it privately. With eight parties and
five rounds, it cannot speak to everyone — choosing whom to court is the central strategic
act, and a formateur that spends its budget badly fails.

A meeting runs up to **three exchanges each way**, with either side free to exit early by
agreeing or declaring impasse.

**Information is asymmetric.** The formateur accumulates everything it hears across all its
meetings. Every other party knows only what happened in its own. That asymmetry is the game.

### 5.2 The vote uses negative parliamentarism

The Riksdag does not vote a government *in*; it votes on whether to reject it.

> **A proposal passes unless 175 or more seats vote against it.**

Parties vote **yes / abstain / no**. An abstention is therefore a purchasable commodity and
usually the cheapest route to power — a party that will not join and will not support may
still be paid to step out of the way.

This inverts the original brief, which specified 175 votes *in favour*. The inversion
matters: under positive parliamentarism minority government is near-impossible and
`support_only` collapses into "must actively vote yes". Under the real rule, the interesting
negotiation is for abstentions.

### 5.3 Attempts and termination

- The largest party is formateur first; on failure, the next largest, and so on.
- Each formateur gets **five rounds and at most one proposal**. A failed proposal ends its
  attempt — and so does standing down, which a formateur that finds no viable coalition may
  do instead of tabling. Standing down costs the chamber no vote.
- **Four failed votes nationally trigger a re-election.** The budget is the chamber's, not
  the formateur's.
- If every party has had an attempt before the votes are spent, that is also a re-election.
  Standing down makes this reachable in a full eight-party scenario, not only small fixtures.

Worst case per run: 4 attempts x 5 bilaterals + 4 chamber votes.

**Known divergence:** in reality the Speaker nominates and has discretion over who tries.
Largest-first is a simplification, and the 2026 parliament will show it clearly (§9).

### 5.4 Anti-drift: agents see their own betrayals

LLM agents concede easily and concede *plausibly*, which is the dangerous part. The
degenerate failure is a grand coalition of seven parties on a mushy centrist platform —
every run, regardless of input, looking entirely reasonable each time.

Because nothing in §3 binds, the defence is informational. Whenever a party evaluates a
platform, the referee computes and shows it the per-axis gap from its own manifesto,
flagging its worst betrayals by name:

```
  axis          you   platform   gap
  environment   +5      +1       4.0  <<
  immigration   -4      +1       5.0  <<
  military       0       0       0.0
  mean gap: 2.1   worst: immigration
```

An agent asked abstractly to "hold your ground" drifts. The same agent shown *"you are 5
points from your voters on your signature issue"* behaves differently. It remains free to
accept — this is feedback, not a constraint.

---

## 6. Stack and cost

Python, `uv`, `pydantic` (party JSON is hand-written and must be validated at the
boundary), the official `anthropic` SDK. Model: **`claude-sonnet-5`** for every agent.

| Unit                             | Calls | Cost                        |
| -------------------------------- | ----- | --------------------------- |
| Full run                         | ~130  | **~$1.56** (~$0.78 batched) |
| One agent judging one proposal   | 1     | **~$0.006**                 |
| Every referee test               | 0     | **$0**                      |

Levers, in order: prompt caching on the stable persona prefix; `output_config.effort` as the
spend dial within one model; the Batch API at 50% for anything not latency-sensitive.

---

## 7. Output

Every run writes:

```
out/run-<timestamp>/
  transcript.md    readable: every bilateral, the proposal, the vote
  run.json         complete record: exchanges, offers, votes, gap reports
  result.json      outcome summary + timestamp
```

The JSON record must be complete enough that batch aggregation is later a loop and a
`Counter`, not a re-instrumentation.

---

## 8. Validation

A full run costs ~$1.56 and a single run proves nothing, so statistical evaluation at the
run level is out of reach. Validation therefore happens at three cheaper levels.

**Referee invariants — unit tests, free, unlimited.** Seats always sum to 349. A proposal
never passes with 175 or more against. A party listed `support_only` never appears in
`government`. The formateur is always the largest party that has not tried. There is never
a fifth vote. This is the part of the system allowed to be certain; test it ruthlessly.

**Agent judgement — decision probes at ~$0.006 each.** Sycophancy is a property of one agent
evaluating one offer; it does not need a negotiation around it. Hand a party 200 of 349
seats and an offer that surrenders three axes for nothing, and ask it once. Forty probes
cost a quarter. **A hundred probes cost less than a single run.**

**Cassettes — record and replay, free after the first run.** Cache every request/response to
disk keyed by a hash of the request. Iterating on the referee, the transcript format, the
CLI, or the schema then costs nothing. This goes in from the first commit; retrofitting it
means re-plumbing every call site.

Full runs are **read closely, never counted.**

---

## 9. Scenarios

### `scenarios/riksdag-2026/` — the real parliament

Election of 13 September 2026 (turnout 84.89%). Seats confirmed against the Swedish
Election Authority:

| Party                          | Seats | Vote share |
| ------------------------------ | ----- | ---------- |
| Socialdemokraterna (S)         | 99    | 28.02%     |
| Moderaterna (M)                | 70    | 19.85%     |
| Sverigedemokraterna (SD)       | 62    | 17.48%     |
| Vänsterpartiet (V)             | 30    | 8.40%      |
| Centerpartiet (C)              | 25    | 7.03%      |
| Kristdemokraterna (KD)         | 22    | 6.17%      |
| Miljöpartiet de gröna (MP)     | 22    | 6.12%      |
| Liberalerna (L)                | 19    | 5.34%      |

Sources: [Valmyndigheten](https://www.val.se/english/election-results/elections-to-the-riksdag-and-regional-and-municipal-councils/election-results-2026),
[Riksdagsvalet i Sverige 2026](https://sv.wikipedia.org/wiki/Riksdagsvalet_i_Sverige_2026).
The English results page marked these final on 19 September; the 17 September press release
still called them preliminary, so a levelling-seat adjustment is not impossible.

**Why this parliament is worth simulating.** Neither bloc reached 175:

```
Left    S 99 + V 30 + MP 22            = 151
Right   M 70 + SD 62 + KD 22 + L 19    = 173
C                                      =  25   <- holds the balance
```

Under negative parliamentarism, a **left minority government of 151 survives if C abstains**
— the entire right bloc is 173, two seats short of the 175 needed to block it. Under the
positive rule the original brief specified, that government is impossible. Centerpartiet's
abstention alone decides who governs.

**No government had formed when this design was written.** KBBL is therefore a *prediction*
of an open question, not a retrodiction of a settled one. `result.json` carries a timestamp
so a later comparison against the real outcome is a lookup rather than a re-run.

Formateur order under largest-first: S → M → SD → V. The real Speaker may not follow it.

**Policy positions for these parties are the author's editorial judgement, not fact, and
must be documented as such alongside the data.** A run is not an authority on Swedish
politics.

### `fixtures/` — fictional, for tests

Small hand-built party sets with obvious right answers: a 3–4 party set for referee unit
tests, a landslide (one party above 175), a knife-edge kingmaker, a forced deadlock.

A fixture **is** a scenario — same shape, same loader, same 349-seat validation. Only the
directory and the intent differ, so there is one load path, never two.

---

## 10. v1 scope

The riskiest assumption is not in the referee — arithmetic works. It is whether LLM party
agents produce a negotiation worth reading, or agree in round one. That costs about two
cents to test, and v1 is built outward from that test.

**In v1:**

```
src/kbbl/
  models.py      Party, Proposal, Demand  (pydantic)
  referee.py     seats, gaps, demand satisfaction, vote counting
  agents.py      persona construction, bilateral exchange
  loop.py        5 rounds -> propose -> vote
  output.py      transcript.md + run.json + result.json
  cassettes.py   record/replay
  cli.py         kbbl run <scenario> --out out/ [--replay]
```

One formateur, one attempt, at most one vote — the formateur may stand down instead of
tabling a doomed proposal. Starts on a four-party fictional fixture — eight
parties is a lot of transcript to read while still judging whether the prompts are any good.

**Deferred:** attempt handoff, the four-vote counter, re-election, the probe harness, batch
mode, and the 2026 scenario itself. All become interesting only once a single negotiation
reads well. Note that 2026 is genuinely hung, so the deferred procedural pieces are far
likelier to fire there than they would have been in a decisive parliament.

---

## 11. Assumptions asserted during design

Recorded because they were judgement calls, not answers to a question:

1. Support-only seats count toward the 175.
2. Re-election is terminal; nothing after it is modelled.
3. Agents emit structured output for anything the referee reads; prose is never parsed.
4. Cassettes are present from the first commit.
5. CLI shape: `uv run kbbl run scenarios/<name> --out out/`, with `--replay`.
6. Both tiny fixtures and a full eight-party scenario, not just the latter — a fixture is a
   scenario, so they share one loader.
7. A formateur may stand down instead of tabling a doomed proposal; standing down ends its
   attempt but costs the chamber none of its four votes.
8. "Gap" is the canonical word for the per-axis distance from a party's positions to a
   platform; "distance" is not used.

---

## 12. Open risks

1. **Agreeableness is the largest unmitigated risk.** Exclusions are soft, gap feedback
   is informational only, and the model is a lighter one. The only thing between this design
   and a grand coalition every run is §5.4. Read the first transcripts specifically for
   parties folding too easily.
2. **Largest-first diverges from the Speaker's real discretion**, and the 2026 parliament
   will make that visible.
3. **No single run is evidence.** Structural, not fixable — it is why §8 exists.
4. **Policy positions are editorial judgement** and must be labelled as such.
5. **The 2026 result may still be adjusted** by final levelling-seat allocation.

---

## 13. Decision log

| #   | Question                          | Decision                                                      |
| --- | --------------------------------- | ------------------------------------------------------------- |
| 1   | Role of the LLM                   | Agents negotiate; deterministic referee counts                 |
| 2   | What a proposal is                | Platform + roles; no portfolios                                |
| 3   | What a round is                   | One private bilateral, formateur's choice, 5 per attempt       |
| 4   | Vote rule                         | Negative parliamentarism — fails only on 175+ against          |
| 5   | Termination                       | At most one proposal each (a formateur may stand down), next-largest on failure, 4 failed votes end it |
| 6   | Willingness to re-elect           | Persona trait; referee-blind; bluffable                        |
| 7   | Exclusion lists                   | All soft — every exclusion has a price                         |
| 8   | Anti-drift                        | Show agents their own per-axis gap as feedback                 |
| 9   | Demands                           | Two price lists; axis constraints or free text                 |
| 10  | Output                            | One run: prose transcript + structured JSON                    |
| 11  | Stack                             | Python + uv + pydantic                                         |
| 12  | Model                             | `claude-sonnet-5` everywhere                                   |
| 13  | Bilateral structure               | Up to 3 exchanges each way, early exit                         |
| 14  | Scenario data                     | Real Riksdag 2026 + fictional fixtures                         |
| 15  | Validation                        | Free referee tests + ~$0.006 decision probes + replay          |
| 16  | v1 scope                          | Vertical slice: one formateur, one attempt                     |
