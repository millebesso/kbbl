"""One Formateur's Attempt: five Rounds, then a Proposal the chamber votes on — or neither.

The budget is the Referee's (§2), so it is counted here rather than left to the Formateur to
observe — an Agent asked to keep track of how many meetings it has left is an Agent that can
be wrong about it. Everything inside a Round is the Formateur's own: whom to meet, what to
say, when to walk out, and at the end of them whether there is a government here worth putting
to a vote at all.
"""

from __future__ import annotations

from kbbl.agents import FormateurAgent
from kbbl.cassettes import Cassettes
from kbbl.models import Party, Run, Scenario
from kbbl.referee import ROUNDS


def attempt(scenario: Scenario, *, formateur: Party, cassettes: Cassettes) -> Run:
    """One whole Attempt: the Rounds, what they led to, and how the chamber answered.

    Returns the record rather than the outcome, because the outcome is the Referee's to
    compute from it and computing it twice is two places for it to differ. A Run holding no
    Proposal is a Formateur that Stood down, which is not a Proposal that lost: it spends
    none of the Chamber's four Votes (§5.3).

    v1 is one Formateur and one Attempt (§10), so one Attempt fills a whole `Run`. The
    handoff to the next-largest Party is deferred, and so is the four-Vote counter.
    """
    agent = FormateurAgent(scenario, formateur)
    rounds = tuple(agent.spend(cassettes) for _ in range(ROUNDS))
    proposal, reasoning = agent.table(cassettes)
    return Run(
        scenario=scenario.name,
        formateur=formateur.name,
        rounds=rounds,
        proposal=proposal,
        reasoning=reasoning,
        judgements=(
            () if proposal is None else agent.put_to_the_chamber(proposal, cassettes)
        ),
    )
