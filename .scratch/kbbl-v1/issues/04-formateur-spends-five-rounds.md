# 04 — A Formateur spends five Rounds

**What to build:** The Formateur works through its budget of five Rounds, choosing which single
Party to meet in each one and saying why before it does. Choosing whom to court is the central
strategic act of the game (§5.1) — with more parties than Rounds, a Formateur that spends its
budget badly should visibly fail.

The information asymmetry is the other half of this ticket: the Formateur accumulates
everything it hears across every Bilateral, while each other Party knows only what happened in
its own. That asymmetry is the game, and it is easy to leak by accident.

**Blocked by:** 02.

**Status:** ready-for-agent

- [ ] The Formateur chooses one Party per Round and states its reasoning before the Bilateral opens
- [ ] Five Rounds per Attempt, and the budget is enforced
- [ ] The Formateur carries what it learned in earlier Bilaterals into later ones
- [ ] No Party other than the Formateur sees any Bilateral but its own — verifiable from the run record, not just from reading
- [ ] The Transcript reads as five distinct private meetings
- [ ] `--replay` replays the whole five-Round sequence with zero API calls
- [ ] A Party may be met more than once if the Formateur chooses to spend two Rounds on it
- [ ] Willingness to re-elect is rebanded, or the Fixture reseated, before the Formateur leans on it — `_DISPOSITIONS` sends NP and FF identical prose today and two of its five bands go unused, so the lever this ticket wants does not yet distinguish the two largest Parties (02, §12.1)
- [ ] `--meet` is withdrawn — it stood in for a choice the Formateur now makes for itself (02)
- [ ] Each Round's chosen Party and the reasoning given for it land in the `Run` record, not only in the Transcript — ticket 06 serialises what this ticket accumulates (§7)

**Sequencing note (02).** Cassettes are content-addressed by a hash of the request, so rebanding
willingness invalidates all fifteen committed recordings, and carrying earlier Bilaterals into
later ones invalidates every Round-2+ request regardless. Reband first, then record the full
five-Round run once — recording before the reband pays for the sequence twice.
