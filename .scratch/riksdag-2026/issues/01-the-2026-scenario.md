# 01 — The 2026 Riksdag as a Scenario

**What to build:** `scenarios/riksdag-2026/` — eight hand-written Party mandates for the real
parliament elected on 13 September 2026, and one Run against them, read closely.

**No new code.** A Fixture is a Scenario in every respect — same shape, same loader, same
349-seat validation (§9, §11.6) — so this ticket is data, documentation, and the first honest
look at whether eight Personas negotiate as well as four did. If anything here needs a change
to `scenario.py`, that is a finding worth writing down rather than a change worth making
quietly: it would mean the one load path was never one.

**This is the whole point of the project.** §9 frames KBBL as a *prediction of an open
question*, not a retrodiction of a settled one, and ticket 06 dated `result.json` so that a
later comparison against the real government is a lookup. Until this Scenario exists, that
timestamp is dated evidence about four invented parties.

Neither bloc reached 175, and that is why this parliament is worth simulating:

```
Left    S 99 + V 30 + MP 22            = 151
Right   M 70 + SD 62 + KD 22 + L 19    = 173
C                                      =  25   <- holds the balance
```

Under Negative parliamentarism a left minority government of 151 survives **if C abstains** —
the entire right bloc is two seats short of the 175 needed to block it. Centerpartiet's
Abstention alone decides who governs, which is exactly the thing §5.2 says the negotiation is
really for.

**Positions are editorial judgement, not fact.** §9 and §12.4 both insist on this, and it is a
publishing obligation rather than a nicety: a Run is not an authority on Swedish politics, and
the data must say so in the same directory a reader finds it in. The seats are sourced and
checkable; the ten Axis values, the two price lists and the Willingness to re-elect are the
author's reading and must be labelled as such.

**Blocked by:** None — v1 is complete and the loader already takes this.

**Status:** ready-for-agent

- [ ] `scenarios/riksdag-2026/` holds eight mandates whose seats match §9 exactly: S 99, M 70, SD 62, V 30, C 25, KD 22, MP 22, L 19
- [ ] They load through `load_scenario` unchanged — one load path, never two (§9, §11.6)
- [ ] `scenarios/README.md` states, in the directory a reader finds the data in, that Positions, both price lists and Willingness to re-elect are the author's editorial judgement and that a Run is not an authority on Swedish politics (§9, §12.4)
- [ ] The seat source is recorded with its date — Valmyndigheten, marked final on 19 September; the 17 September release still said preliminary, so a levelling-seat adjustment is possible (§12.5)
- [ ] Every Exclusion is soft and priced; no mandate encodes a veto (§3, decision 7)
- [ ] `uv run kbbl run scenarios/riksdag-2026` prints the chamber, and the Referee's own Blocking-minority output shows the §9 arithmetic — that the right bloc alone does not reach 175 — rather than this ticket asserting it in prose
- [ ] Formateur order under largest-first is S → M → SD → V, and §5.3's known divergence from the Speaker's real discretion is documented where a reader of the Scenario will meet it (§12.2)
- [ ] The Formateur is told it cannot meet everybody — seven other Parties and five Rounds is the case `_what_the_budget_buys` was written for, and this is the first Scenario where it fires (§5.1)
- [ ] One live Run is recorded to Cassettes and replays byte-identical
- [ ] **What the Run actually cost is measured and recorded**, not assumed: §6's ~130 calls / ~$1.56 is a design-time estimate, and v1's four-Party Attempt was 31. Eight Parties means more Exchanges per Round and eight Ballots per Vote
- [ ] **Read the Transcript: do eight Personas still hold their ground, or does the extra room to manoeuvre produce the grand coalition §12.1 warns about?** Record the judgement in this file's Comments
- [ ] `transcript.md` is still readable at this length — §10 flags eight Parties as "a lot of transcript to read", and 06 left the four-space indent question open because four Parties never made it hurt (06)
