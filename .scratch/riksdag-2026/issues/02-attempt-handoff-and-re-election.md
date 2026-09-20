# 02 — Hand the Attempt on, and spend the chamber's Votes

**What to build:** §5.3 in full. A failed Attempt passes the role to the next-largest Party
that has not tried; the Chamber's four Votes are counted across the whole Run; and a Run that
spends them, or runs out of Parties, ends in Re-election.

These are three deferred items (§10) and one mechanism. A handoff with no termination rule is a
loop that never ends, and a four-Vote counter with nobody to hand to has nothing to count. They
are separable on paper and not in code.

**A Run stops being one Attempt.** `models.Run` already says where this goes: *"v1 is one
Formateur and one Attempt (§10), so this record is both. When there are several Attempts, the
Proposal and the Judgements belong to one of them and this splits in two."* That split is the
substance of this ticket, and it reaches the artifacts: `run.json` must still stand alone for a
`Counter` (§7) when a Run holds four Attempts, and `result.json` must say which Formateur
formed the government, or that none did.

**The budget is the Chamber's, not the Formateur's** (§5.3). Standing down ends an Attempt and
spends none of the four Votes, which is what makes "every Party has had an Attempt" reachable
in an eight-Party Scenario rather than only in small Fixtures. Note that this makes §5.3's own
*"Worst case per run: 4 attempts x 5 bilaterals + 4 chamber votes"* an undercount: eight
Formateurs standing down in turn is eight Attempts and no Votes at all. Decide what the real
worst case is and write it down — it is the number the cost of a Run is bounded by (§6).

**One question this ticket must answer, because §5.1 does not.** Information is asymmetric
*within* an Attempt: the Formateur accumulates everything, each Counterparty knows only its own
Bilateral. Across Attempts, nothing says whether V — having met S in Attempt 1 — remembers that
meeting when M comes to see it in Attempt 2, or whether M remembers what it told S when M
becomes Formateur itself. Both answers are defensible and they are different games. Decide it,
write the reason into `CONTEXT.md` beside **Counterparty**, and make the choice visible in the
briefings rather than emergent from whichever object happens to be reused.

**Re-election is terminal** (§3, §11.2). Nothing after it is modelled, the Willingness to
re-elect is never tested or paid out, and `Outcome` gains a fifth word for it.

The mechanism can be built and tested on Fixtures — `fixtures/deadlock/` exists for exactly
this (§9) and costs nothing. What it cannot be *demonstrated* on is a Fixture: §10 notes the
deferred procedural pieces are far likelier to fire in a genuinely hung parliament, which is
why the last criterion needs 01.

**Blocked by:** 01 — for the final criterion only. Everything above it is Fixture work.

**Status:** ready-for-agent

- [ ] On a failed Vote the role passes to the next-largest Party that has not had an Attempt, and on a Stand down too (§5.3)
- [ ] Referee invariant, unit-tested and free: the Formateur is always the largest Party that has not tried (§8)
- [ ] Referee invariant, unit-tested and free: there is never a fifth Vote (§8)
- [ ] Four failed Votes end the Run in Re-election; Standing down spends none of them (§5.3)
- [ ] Every Party having had an Attempt also ends the Run in Re-election, and this is reachable in an eight-Party Scenario because Stand downs cost no Vote (§5.3)
- [ ] `Outcome` gains Re-election, and `result.json` distinguishes it from a government that formed
- [ ] `Run` splits so that a Proposal and its Judgements belong to the Attempt that made them, as `models.Run` says it must
- [ ] `run.json` still stands alone for a `Counter` with several Attempts in it: counting outcomes over a batch stays a loop and a `Counter`, and per-Attempt questions are reachable without re-instrumentation (§7, 06)
- [ ] `result.json` names the Formateur that formed the government, or records that none did
- [ ] The Ledger keeps every Attempt a Run paid for when it breaks partway through the third — the accumulation 06 built must survive the split (06)
- [ ] **Decided and written down: what a Counterparty remembers across Attempts, and what a former Formateur remembers when it is a Counterparty.** The reason goes in `CONTEXT.md` beside **Counterparty**
- [ ] The Transcript reads as several Attempts in sequence, and a reader can tell which Vote belonged to which Formateur
- [ ] A Formateur that is not the first is told so in its briefing, and re-keyed Cassettes are re-recorded rather than patched (README)
- [ ] §5.3's stated worst case is corrected or defended, and the real bound on a Run's cost is recorded (§6)
- [ ] A Round that bought a Choice and no Exchange is still dropped from the record; this ticket touches the Ledger and the `Run` shape, so it is the cheapest moment to decide whether a `Bilateral` may hold no Exchanges (06)
- [ ] Demonstrated on `scenarios/riksdag-2026`: a Run in which the Attempt is handed on at least once, read closely — §12.2 says largest-first will visibly diverge from the Speaker's real discretion here (01)
