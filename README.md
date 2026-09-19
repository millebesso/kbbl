# kbbl

An LLM-driven simulator of government formation in the Swedish Riksdag: LLM Party agents
bargain over a government while a deterministic Referee owns all arithmetic and procedure.

Design lives in [`docs/kbbl.md`](docs/kbbl.md). The vocabulary it is described in is canonical
in [`CONTEXT.md`](CONTEXT.md).

## Getting started

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run kbbl run fixtures/four-party --replay
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

Then the Formateur — the largest Party — meets one other Party in private and they bargain,
up to three Exchanges each way, and the meeting prints as a Transcript:

```
Bilateral: NP meets FF
----------------------

NP:
    Here's my opening position: any government I lead needs a credible economic platform
    — firmly market-oriented, not the muddled centre. I'll also want a binding cap on
    spending growth written into the programme; that's non-negotiable for me sitting in
    cabinet.

FF:
    A 'firmly market-oriented' economic platform with a binding spending cap is not
    something I can sell to my people as a compromise; it's a surrender, and they would
    see it as one within a week.

    ...

Ended: NP agreed, after 5 Exchanges.
```

That is an excerpt from the committed Cassettes — `--replay` prints the whole of it.

A Fixture is a Scenario in every respect, so `kbbl run` takes either. See
[`fixtures/README.md`](fixtures/README.md).

## Live and replay

**A Run calls the model, and live is the default.** Every request and response is written to a
Cassette under `cassettes/<scenario>/`, keyed by a hash of the request:

```sh
uv run kbbl run fixtures/four-party                 # live — calls claude-sonnet-5, records
uv run kbbl run fixtures/four-party --replay        # free — replays, identical Transcript
uv run kbbl run fixtures/four-party --meet MI       # the Formateur meets MI instead of FF
```

Replay needs no credentials at all: the API client is only built on the live path. Editing a
persona, a briefing or the model changes the request, so `--replay` will miss and say so — a
miss is the honest answer, not a bug.

`--meet` is a placeholder. Ticket 04 gives the Formateur that choice for itself.

## Development

```sh
uv run pytest
uv run mypy
```

The test suite makes zero API calls. Tests that need a Bilateral record one against a scripted
stand-in and replay it; the committed Cassettes under `cassettes/` are replayed too.
