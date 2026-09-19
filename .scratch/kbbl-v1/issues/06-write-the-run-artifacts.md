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

**Status:** ready-for-agent

- [ ] `out/run-<timestamp>/` contains `transcript.md`, `run.json` and `result.json`
- [ ] `transcript.md` reads start to finish: every Bilateral, the Proposal, the vote
- [ ] `run.json` records every Exchange, the Proposal, every vote with its reasoning, and every Gap report shown
- [ ] `run.json` records which Party the Formateur chose each Round, and why
- [ ] `result.json` carries the outcome — formed, rejected, or stood down — plus a timestamp
- [ ] Demonstrated: counting outcomes across many Runs is a loop and a `Counter` over `run.json`, with no re-instrumentation
- [ ] Artifacts are identical under `--replay`
- [ ] `--out` controls the destination directory (§11.5)
