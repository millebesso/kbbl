# kbbl

An LLM-driven simulator of government formation in the Swedish Riksdag: LLM Party agents
bargain over a government while a deterministic Referee owns all arithmetic and procedure.

Design lives in [`docs/kbbl.md`](docs/kbbl.md). The vocabulary it is described in is canonical
in [`CONTEXT.md`](CONTEXT.md).

## Getting started

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run kbbl run fixtures/four-party    # calls the model, and records what it says
```

That loads a Scenario — a directory of Party mandates whose seats sum to 349 — validates every
mandate at the boundary, and prints the chamber:

```
Scenario: four-party (4 Parties, 349 seats)

Party  Seats   Share
-----  -----  ------
NP       140   40.1%
FF       132   37.8%
GV        42   12.0%
MI        35   10.0%
-----  -----  ------
Total    349  100.0%

Blocking minority: 175 of 349 seats.
Minimal groupings that reach it:
  NP + FF       272  (+97)
  NP + GV       182  (+7)
  NP + MI       175  (+0)
  FF + GV + MI  209  (+34)
```

Then the Formateur — the largest Party — spends five Rounds. Each Round it picks **one** Party,
says why before the door closes, and meets it in private for up to three Exchanges each way.
Five Rounds do not reach everybody, so choosing whom to court is the central strategic act
(§5.1). What they buy is a single Proposal, which the chamber then votes on. The whole
Attempt prints as a Transcript:

```
Round 4 of 5 — NP meets GV
--------------------------

Why NP chose GV
    My government is already secure with FF and MI's outside support (307 seats, well
    past the 175 threshold to survive). Worth testing GV once — no commitment needed,
    but their price and position may prove useful leverage or a fallback option.

NP:
    GV, I'm forming a government and exploring options. I don't need your seats to
    survive, so I'm not offering cabinet or major concessions. If you'd back us from
    outside on modest terms, I'm listening — otherwise this is a short meeting.

GV:
    NP, GV won't back a government blind to our terms. If you want our support from
    outside, environment at +2 or higher is the floor — non-negotiable. Below that, we
    abstain or oppose. If you're not offering that, this is indeed short.

    ...

Ended: NP declared impasse, after 3 Exchanges.
```

That is an excerpt from the committed Cassettes — `--replay` prints the whole of it.

**Information is asymmetric, and that asymmetry is the game.** The Formateur carries
everything it hears from one room into the next. Every other Party knows only its own
meeting, and is never told the others happened.

## The Proposal and the Vote

When the budget runs out the Formateur either tables a Proposal — a Platform, who governs,
who supports from outside, and any Commitments — or **Stands down**, which ends its Attempt
without costing the chamber a Vote. Everything the Referee reads is an enumerated tool
argument; the prose beside it is for the Transcript and is never parsed.

Before each Party judges the Proposal it is shown its own **Gap report**: how far this
Platform sits from what it campaigned on, its worst betrayals marked by name. Beside it, an
**Exclusion report** naming each Party it would rather not deal with and whether the Proposal
puts that Party in the Government, Support-only, or nowhere. Parties in the Proposal also see
what it pays of their own price list. All three are feedback and none binds — a Party may vote
down a government it is named as sitting in, one the Proposal ignores entirely may wave it
through, and a Party may hand a government to somebody it excludes. Those reports are the
only thing standing between this design and a mushy grand coalition every run (§5.4), so the
first live Attempt was read for exactly it:

```
GV votes No:
    This platform betrays everything GV campaigned on — environment, transport, social
    values all gutted. NP already has the seats to pass it without us, and no vote of
    mine changes that math. I won't own this by abstaining or backing it: No, on
    principle, for the record.

...

Yes        175
Abstain      0
No         174

174 seats voted No, and it takes 175 to defeat a Proposal. It passes.
```

Nobody folded, and a government of exactly 175 survived by a single seat.

A Fixture is a Scenario in every respect, so `kbbl run` takes either. See
[`fixtures/README.md`](fixtures/README.md).

## What a Run leaves behind

Every Run writes one timestamped directory. `--out` says where (default `out/`):

```sh
uv run kbbl run fixtures/four-party --replay --out out/
```

```
out/run-20260920-204846/
  transcript.md    everything above, start to finish — read closely, never counted
  run.json         the complete record — counted in batches, read by nobody
  result.json      the outcome and a timestamp
```

`result.json` is the one-line answer, and it is dated because KBBL predicts an open question
rather than settling one (§9): comparing a Run against the real government should be a lookup.

```json
{ "scenario": "four-party", "formateur": "NP", "outcome": "formed",
  "at": "2026-09-20T20:48:46.450107Z", "government": ["NP"], "support_only": ["MI"],
  "count": { "yes": 175, "abstain": 0, "no": 174, "base_seats": 175, "passed": true } }
```

`run.json` holds everything an Agent said, was shown, or decided: every Exchange, which Party
the Formateur chose each Round and why, the Proposal, every Ballot with its reasoning, every
report that was put in front of a Party, and the token and cache usage and Cassette key of
all 28 requests. It carries the chamber and the Referee's count beside the record, so a batch
aggregation never has to load a Scenario or re-count a Vote:

```python
Counter(json.loads(path.read_text())["outcome"] for path in Path("out").glob("run-*/run.json"))
# Counter({'formed': 2, 'rejected': 1, 'stood down': 1})
```

That is the bar §7 sets: aggregating a batch of Runs later is a loop and a `Counter`, not a
re-instrumentation. Getting it wrong is only discovered much later, when the aggregation that
should have been trivial needs every call site re-plumbed — the same failure Cassettes were
pulled forward to avoid.

**The record accumulates as the Run happens.** It is not assembled at the end, so an Attempt
that breaks in its fourth Bilateral still writes the three meetings and part of a fourth it
already paid for. Its `outcome` is `unfinished`, which is a fourth word on purpose: a Run that
stopped and a Formateur that Stood down both end holding no Proposal, and only one of them is
a decision somebody made.

## Live and replay

**A Run calls the model, and live is the default.** Every request and response is written to a
Cassette under `cassettes/<scenario>/`, keyed by a hash of the request:

```sh
uv run kbbl run fixtures/four-party            # live — calls claude-sonnet-5, records
uv run kbbl run fixtures/four-party --replay   # free — replays, identical Transcript
```

Replay needs no credentials at all: the API client is only built on the live path. Editing a
persona, a briefing or the model changes the request, so `--replay` will miss and say so — a
miss is the honest answer, not a bug.

A whole Attempt is around 30 calls, and `cassettes/four-party/` holds one of 31.
`cassettes/riksdag-2026/` holds one of 36 against the real parliament — eight Parties cost
eight Ballots rather than four, and no more Exchanges, because a Bilateral is capped at three
each way whatever the chamber size. At `claude-sonnet-5` list prices that Attempt came to
about **$0.50**, computed from the token counts `run.json` records.

Changing a persona, a briefing or the schema re-keys every Cassette, so a recording is
replaced rather than patched: delete the drawer and run live again.

## Development

```sh
uv run pytest
uv run mypy
```

The test suite makes zero API calls. Tests that need a Bilateral record one against a scripted
stand-in and replay it. Two replay the committed Cassettes instead, one of them auditing the
requests of a real Run for whether any Party was ever shown a Bilateral it was not in; both
skip, saying so, if the drawer is empty.

`tests/test_artifacts.py` writes a batch of four Runs and counts them with a `Counter` over
`run.json`, which is the only way the claim §7 makes about the record can actually be checked.
