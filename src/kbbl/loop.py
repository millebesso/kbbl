"""One Formateur's Attempt: the Rounds it spends, one Bilateral at a time.

The budget is the Referee's (§2), so it is counted here rather than left to the Formateur to
observe — an Agent asked to keep track of how many meetings it has left is an Agent that can
be wrong about it. Everything inside a Round is the Formateur's own: whom to meet, what to
say, and when to walk out.
"""

from __future__ import annotations

from kbbl.agents import FormateurAgent
from kbbl.cassettes import Cassettes
from kbbl.models import Party, Round, Scenario
from kbbl.referee import ROUNDS


def attempt(scenario: Scenario, *, formateur: Party, cassettes: Cassettes) -> tuple[Round, ...]:
    """The Rounds of one Attempt, in the order they were spent.

    As far as v1 has built it: ticket 05 adds the Proposal they lead to, which is the other
    half of what `CONTEXT.md` calls an Attempt.
    """
    agent = FormateurAgent(scenario, formateur)
    return tuple(agent.spend(cassettes) for _ in range(ROUNDS))
