# 06 — Write the run artifacts

**What to build:** Every Run writes a timestamped directory containing a readable Transcript and
a complete structured record.

The bar for `run.json` is set in §7: complete enough that aggregating a batch of Runs later is a
loop and a `Counter`, not a re-instrumentation. Anything an Agent said, was shown, or decided
belongs in it. Getting this wrong is only discovered much later, when the aggregation that
should have been trivial requires going back and re-plumbing every call site — the same failure
Cassettes were pulled forward to avoid.

`result.json` carries a timestamp because KBBL is a prediction of an open question, not a
retrodiction of a settled one (§9): a later comparison against the real outcome should be a
lookup.

**Blocked by:** 05.

**Status:** done

- [x] `out/run-<timestamp>/` contains `transcript.md`, `run.json` and `result.json`
- [x] `transcript.md` reads start to finish: every Bilateral, the Proposal, the vote
- [x] `run.json` records every Exchange, the Proposal, every vote with its reasoning, and every Gap report shown
- [x] `run.json` records which Party the Formateur chose each Round, and why
- [x] `result.json` carries the outcome — formed, rejected, or stood down — plus a timestamp
- [x] Demonstrated: counting outcomes across many Runs is a loop and a `Counter` over `run.json`, with no re-instrumentation
- [x] Artifacts are identical under `--replay`
- [x] `--out` controls the destination directory (§11.5)
- [x] The `Run` record accumulates as the Run happens rather than being assembled after it — a Run that aborts mid-Bilateral keeps every Exchange already paid for (02)
- [x] `run.json` carries token and cache usage and the Cassette key for every request, which §7 needs present if aggregation is to be a `Counter` rather than a re-instrumentation (02)

## Comments

**Implemented.** `uv run kbbl run fixtures/four-party [--replay] [--out DIR]` now writes
`out/run-<timestamp>/` holding `transcript.md`, `run.json` and `result.json`. 200 tests,
`mypy --strict` clean, zero API calls in the suite.

`ledger.py` is new: the Run record as it is written, one paid-for thing at a time. `models.py`
gained `Gap` and `GapReport` (moved out of `referee.py` and made serialisable), `Usage`,
`Outcome`, `Count`, `Record` and `Result`, and `Run` gained `gap_reports`, `usage` and
`finished`. `referee.py` gained `record()`, `count()` and `outcome()`. `output.py` gained
`write_run()`. `CONTEXT.md` gained Ledger, Outcome, Record and Result.

Replaying the committed Cassettes writes a `run.json` of 31 requests, 59,634 input tokens
and 44,503 read from cache — which is the first time §6's claim about caching the Persona
prefix has been visible rather than asserted.

### Judgement calls

- **Gap reports are stored, not recomputed.** Ticket 05 handed this forward the other way:
  they are a pure function of Positions and the Platform, both of which the record holds, so
  06 *could* recompute. The checklist here asks for "every Gap report shown", and shown is
  the operative word — recomputing gives the report a Party *would* be shown by today's
  code, which is a different claim from the one an aggregation over old Runs needs. The
  report is now computed once in `_judge` and both shown and recorded, so the two cannot
  drift. `mean_gap` and `worst_gap` are serialised alongside for the same reason: §5.4 is
  read across a batch, and a `Counter` should not have to redo the Referee's arithmetic.

- **`Run.finished` is a new field, and it is what makes an aborted Run honest.** Without it a
  Run that stopped and a Formateur that Stood down are the same record — one holding no
  Proposal — and only one of them is a decision somebody made. `stood_down` now means
  *finished and holding no Proposal*, the Transcript has a third branch, and `Outcome` has a
  fourth word (`unfinished`). The `Run` validator's "tabled a Proposal and nobody voted"
  check is now conditional on `finished`, because between tabling and the first Ballot that
  is exactly what the record legitimately looks like.

- **`run.json` nests the Run under a `Record` rather than flattening it.** `Record` is the
  Run plus the Referee's arithmetic — outcome, chamber, count — so the file stands alone and
  a batch aggregation never loads a Scenario. Flattening would have meant a second model
  repeating every field of `Run`, which is a second place for the record's shape to drift.

- **The Cassette key is computed at the call site, not returned by `Cassettes`.** `key()` is
  already a pure function of the request, so `_Side.reply` calls it. `Cassettes.respond` is
  untouched and so are its tests.

- **`run.json` carries no timestamp, and that is what makes it byte-identical under
  `--replay`.** The date lives in `result.json` alone, which §9 is the reason for anyway.
  Nothing records whether a request was replayed or paid for live: that is a fact about the
  process, not about the Run, and a record carrying it could not be identical either.

- **The CLI writes artifacts on the way out of a failure, not inside `attempt()`.** A Run
  that raises never returns, so the caller holds the Ledger. A Run that paid for nothing
  writes no directory — there is nothing to keep, and a directory for an Attempt that never
  started is an artifact of nothing.

### Found in review, and fixed

- **A Run that stopped mid-Vote said nothing had been tabled.** `_how_it_ended` tested
  `finished` first, so a Run holding a Proposal and half its Ballots printed *"no Proposal
  was tabled, and the chamber held no Vote"* — while `run.json` carried both. The Transcript
  now prints whatever the Run reached and then says how far it got, so the two artifacts
  cannot contradict each other. The Vote is still not *counted* there, because `count_vote`
  is handed the whole Chamber and a Run that stopped mid-Vote polled part of one.

- **A dropped Round renumbered the ones after it.** The Ledger numbered Rounds by their
  place in the list, so a Round whose meeting produced no Exchange relabelled Round 4 as
  Round 3. It now numbers by when a Round was opened: a dropped Round leaves a gap, which is
  the truth, rather than a wrong label, which is not.

- **Two `meet()` calls on the same Party ran into one Bilateral.** The Ledger reused an open
  Round whenever the counterparty matched. It now reuses one only while it is still empty —
  a Formateur spending two Rounds on one Party is the normal case (§5.1), and the record was
  turning two meetings of three into one of six.

- **The CLI lost everything on any error but the two it named.** It caught `AgentError` and
  `CassetteMiss` only, so a network error or a Ctrl-C twenty minutes into a live Run — the
  likeliest mid-Run abort at §6's ~130 calls — took the artifacts with it. It now keeps what
  was paid for on the way out of any exception and re-raises, so the traceback is still the
  answer to what went wrong.

- **Naming**: `Count` and `Usage` were missing from `CONTEXT.md`; `output.RUN` was a filename
  spelled like the `Run` model; `record` in `cli.py` named a `Run`; `Ledger.finished()` read
  as a query beside the `Run.finished` it sets, and is now `finish()`. `attempt()` no longer
  duplicates the build-a-default-Ledger ternary — it passes the caller's through to
  `FormateurAgent`, which is the only place a default is built.

Handed to the next ticket:

- **`FormateurAgent` now writes to a Ledger as well as negotiating.** It is the only object
  the whole Attempt passes through, and the private rooms are the reason it cannot be split
  (argued in 05). The Ledger is a field rather than a parameter on every method, and a
  default one is built when no caller supplies it, so tests that only want an Attempt run
  are unchanged.

- **`out/` is not pruned.** Every Run writes a new directory and nothing ever deletes one,
  which is correct for something that costs $1.56 and wrong for something run in a loop. A
  batch mode (deferred, §10) is where that becomes a question.

- **`transcript.md` is Markdown by extension and by its setext headings, but its wrapped
  prose is indented four spaces**, which a Markdown renderer reads as a code block. It reads
  correctly in a terminal, which is where Transcripts have been read so far. Changing it is a
  Transcript-format decision, not an artifact one, and was left alone here.

- **A Round that bought a Choice and no Exchange is still dropped from the record**, losing
  the Formateur's reasoning for the Round it was spending when the Run broke. Keeping it
  means a `Bilateral` with no Exchanges, which costs `Ending` its meaning and needs a
  "nobody spoke" branch at every site that reads one. The reasoning is not gone — the Choice
  was a paid request, so its Cassette key is in `usage` and the request behind it holds the
  prose — but recoverable is not the same as recorded. Reachable only by a Run that stops in
  the instant between booking a meeting and its first word. Argued, not overlooked.

- **§7 names "exchanges, offers, votes, gap reports" and an *offer* is not a noun anywhere in
  KBBL.** Offers survive as prose inside `Exchange.message` and are not countable. Making
  them countable means the Referee reading prose, which §2 forbids, or an Agent emitting a
  structured offer per Exchange, which is a negotiation-model change rather than an artifact
  one.
