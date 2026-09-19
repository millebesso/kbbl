# 03 — Referee: Gaps, demand satisfaction, and the Blocking minority

**What to build:** The deterministic core — the part of the system allowed to be certain, and
so the part tested ruthlessly (§8). It computes and reports; it never constrains an Agent and
never parses prose (§2).

Three capabilities: the Gap between a Party's Positions and a Platform, per Axis and
summarised; axis-Demand satisfaction of a Platform against either price list; and vote counting
under Negative parliamentarism. Ships the Fixtures whose right answers are obvious.

Costs $0 to test, so there is no excuse for thin coverage here.

**Blocked by:** 01. Runs in parallel with 02 — it needs the models, not the model.

**Status:** ready-for-agent

- [ ] Gap computed per Axis between a Party's Positions and a Platform; mean Gap and worst Gap derived
- [ ] The Gap report renders a Party's worst Gaps, naming the Axes (§5.4)
- [ ] Axis-Demand satisfaction reported against a Platform, for the Governing price and the Supporting price separately
- [ ] Free-text Demands are reported as unevaluated, never guessed at — they are for Agents to interpret
- [ ] Vote counting: a Proposal passes unless 175 or more seats vote No
- [ ] Support-only seats count toward defeating the Blocking minority exactly as Government seats do (§4)
- [ ] Invariant tested: a Proposal never passes with 175 or more seats against it
- [ ] Invariant tested: a Party listed Support-only never appears in Government
- [ ] Invariant tested: seats always sum to 349
- [ ] Landslide, knife-edge-kingmaker and forced-deadlock Fixtures are committed and covered
- [ ] This ticket's test suite makes zero API calls
