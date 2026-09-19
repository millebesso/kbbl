# 05 — Table a Proposal and hold the vote

**What to build:** The Formateur turns five Rounds of bargaining into a Proposal and the chamber
votes on it. This closes the v1 slice: one Formateur, one Attempt, at most one vote.

Everything the Referee consumes is **structured output** — the Proposal, and every vote. Prose
exists for the Transcript only. Regexing a Proposal out of natural language is the most common
way an agent simulation becomes unreliable (§2), so there must be no prose-parsing path at all.

Before each Party judges the Proposal it is shown its own Gap report. This is the only defence
against the degenerate outcome — a grand coalition on a mushy centrist Platform, looking
entirely reasonable every run (§5.4). It is feedback, not a constraint: a Party remains free to
accept a Platform five points from its voters, it just has to do so knowingly.

A Formateur that finds no viable coalition may Stand down rather than table a doomed Proposal.
The run then ends with no vote.

**Blocked by:** 03, 04.

**Status:** ready-for-agent

- [ ] The Formateur emits a Proposal as structured output: Platform (one value per Axis), Government, Support-only, Commitments
- [ ] The Referee obtains the Proposal and every vote structurally — there is no prose-parsing path anywhere
- [ ] Each Party is shown its own Gap report before it judges the Proposal
- [ ] Each Party returns Yes / Abstain / No as structured output, with prose reasoning kept for the Transcript
- [ ] The Referee counts under Negative parliamentarism and declares the outcome
- [ ] A Formateur may Stand down instead of tabling; the run ends with no vote and reports that outcome distinctly from a rejection
- [ ] No ministries or portfolios appear anywhere in the Proposal (§4)
- [ ] A passed Proposal, a rejected Proposal, and a Stand down are each exercised and replayable from Cassettes
- [ ] What a Bilateral's `Ending` commits a Party to is decided and written down — NP declared `agreement` on its own last word in all three of 02's recordings, and `LAST_WORD` beside an available `agreement` option may simply make wrapping up attractive (02)
- [ ] A `Demand` reads the same whether an Agent meets it as persona prose or as a report cell — this is the first ticket that shows it both at once (03)
- [ ] `Ending` is already branched on in `agents.py` and `output.py`; if this ticket adds a third site, the three collapse into one (02, 03)
- [ ] If the Transcripts read badly, `render_gap_report`'s canonical Axis order is the knob to turn — worst-first is the alternative (03)
- [ ] **Read the Transcript: did the Gap report change how parties voted, or did they fold anyway?** Record the judgement in this file's Comments (§12.1)
