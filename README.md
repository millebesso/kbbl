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
Round 3 of 5 — NP meets GV
--------------------------

Why NP chose GV
    MI deal secures NP+MI at exactly 175, mathematically safe against any No coalition.
    Now I want insurance — test whether GV will abstain or offer outside support
    cheaply, padding my margin without touching my core platform.

NP:
    I'm gauging the field before committing to a shape. Would GV consider abstaining on
    a government led by NP, rather than voting it down? What would make that worthwhile
    for you, without asking you to join cabinet or back us outright?

GV:
    Abstention is on the table if the platform sets environment at +2 or higher — that's
    my floor for staying out of your way without owning your programme. Below that, I've
    no reason not to vote you down.

    ...

Ended: NP declared impasse, after 5 Exchanges.
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
Platform sits from what it campaigned on, its worst betrayals marked by name. Parties in the
Proposal also see what it pays of their own price list. Both are feedback and neither binds —
a Party may vote down a government it is named as sitting in, and one the Proposal ignores
entirely may wave it through. That report is the only thing standing between this design and
a mushy grand coalition every run (§5.4), so the first live Attempt was read for exactly it:

```
GV votes No:
    This platform is nowhere near my mandate on environment, transport, or social — a
    betrayal of everything we campaigned on. NP offered nothing for our cooperation.
    We're not obligated to spare them the consequences of that. Voting No.

...

Yes        175
Abstain      0
No         174

174 seats voted No, and it takes 175 to defeat a Proposal. It passes.
```

Nobody folded, and a government of exactly 175 survived by a single seat.

A Fixture is a Scenario in every respect, so `kbbl run` takes either. See
[`fixtures/README.md`](fixtures/README.md).

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

A whole Attempt is around 30 calls, and `cassettes/four-party/` holds one of 31. Changing a
persona, a briefing or the schema re-keys every one of them, so the recording is replaced
rather than patched: delete the drawer and run live again.

## Development

```sh
uv run pytest
uv run mypy
```

The test suite makes zero API calls. Tests that need a Bilateral record one against a scripted
stand-in and replay it. Two replay the committed Cassettes instead, one of them auditing the
requests of a real Run for whether any Party was ever shown a Bilateral it was not in; both
skip, saying so, if the drawer is empty.
