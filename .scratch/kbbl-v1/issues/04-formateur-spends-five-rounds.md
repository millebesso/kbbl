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
