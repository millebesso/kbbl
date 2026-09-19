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
(§5.1), and the whole Attempt prints as a Transcript:

```
Round 3 of 5 — NP meets GV
--------------------------

Why NP chose GV
    FF will not move on economic and MI is already close enough to wait. GV is the only
    abstention left that I can still afford, and I would rather find out what it costs
    now than in the last round.

NP:
    Here's my opening position: any government I lead needs a credible economic platform
    — firmly market-oriented, not the muddled centre. ...

GV:
    A 'firmly market-oriented' economic platform is not something I can sell to my people
    as a compromise; it's a surrender, and they would see it as one within a week. ...

Ended: NP agreed, after 5 Exchanges.
```

That block is the shape of a Round rather than a recording of one — `cassettes/` is empty
until a Run is recorded, and what the Agents actually say is theirs, not this README's.

**Information is asymmetric, and that asymmetry is the game.** The Formateur carries
everything it hears from one room into the next. Every other Party knows only its own
meeting, and is never told the others happened.

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

That is also why `cassettes/` is currently empty: giving the Formateur its own choice of whom
to meet re-keyed every recording ticket 02 made, and a Cassette that cannot replay is not
worth keeping. Record a fresh Attempt with the live command above — one Run is about 35 calls
— and `--replay` is free from then on.

## Development

```sh
uv run pytest
uv run mypy
```

The test suite makes zero API calls. Tests that need a Bilateral record one against a scripted
stand-in and replay it. Two tests replay the committed Cassettes instead — including one that
audits a real Run for whether any Party was ever shown a Bilateral it was not in — and they
skip, saying so, while none are recorded.
