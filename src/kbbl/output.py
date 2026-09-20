"""Rendering a Run for people to read — for now, the Transcript.

Read closely, never counted. It is rendered from the run record rather than printed as the
Run goes along — the record is the artifact ticket 06 serialises, and a Transcript that could
drift from it would not be worth reading.
"""

from __future__ import annotations

from textwrap import fill

from kbbl.models import Bilateral, Judgement, Round, Run, Scenario
from kbbl.referee import ROUNDS, count_vote, render_proposal, render_vote

WIDTH = 88
"""Where a message wraps. Transcripts are read, so lines have to be a readable length."""

_INDENT = "    "
"""Exchanges are indented under the speaker so the Transcript reads as a conversation rather
than as a wall of paragraphs."""


def render_transcript(scenario: Scenario, run: Run) -> str:
    """Everything that happened in a Run, start to finish.

    The Scenario comes in beside the record because the closing count is seat arithmetic and
    seat arithmetic is the Referee's (§2). The Transcript therefore reports the very Vote
    `count_vote` computes rather than a second reckoning of its own, and cannot disagree
    with it.
    """
    parts = [f"Run: {run.scenario}\nFormateur: {run.formateur}"]
    parts.extend(render_round(spent) for spent in run.rounds)
    parts.append(_how_it_ended(scenario, run))
    return "\n\n\n".join(parts)


def _how_it_ended(scenario: Scenario, run: Run) -> str:
    """The end of an Attempt: a Proposal and the Vote on it, or a Formateur Standing down.

    The two are reported apart on purpose. A Proposal voted down and a Formateur that never
    tabled one both end an Attempt, but only the first spends one of the Chamber's four Votes
    (§5.3) — and a Transcript that let them read alike would be the one place a reader could
    not tell which had happened.
    """
    if run.proposal is None:
        return _under(
            f"{run.formateur} stands down",
            f"{_said_by(run)}{run.formateur} tabled no Proposal. Its Attempt is over, the "
            f"chamber held no Vote, and it has spent none of the four it has.",
        )

    vote = count_vote(scenario, run.proposal, run.ballots)
    return "\n\n\n".join(
        [
            _under(
                "The Proposal",
                f"{_said_by(run)}{render_proposal(scenario, run.proposal)}",
            ),
            _under("The Vote", "\n\n".join(_ballot(cast) for cast in run.judgements)),
            render_vote(vote),
        ]
    )


def _said_by(run: Run) -> str:
    """What the Formateur said ending its Attempt, above what it did. Given before the
    outcome because that is when it was given, the way a Round's reasoning is."""
    return f"{_wrap(run.reasoning)}\n\n" if run.reasoning else ""


def _under(title: str, body: str) -> str:
    """A section of the Transcript, under a heading ruled the same way a Round's is."""
    return f"{title}\n{'-' * len(title)}\n\n{body}"


def _ballot(judgement: Judgement) -> str:
    """One Party's Ballot with the sentence it cast it in. Read closely, never counted (§8)."""
    return f"{judgement.party} votes {judgement.ballot.value}:\n{_wrap(judgement.reasoning)}"


def render_round(spent: Round) -> str:
    """One Round: whom the Formateur chose, why, and the private meeting it bought.

    `spent` rather than `round`: a Round is a unit of budget, and naming it for the builtin
    it would shadow reads worse than naming it for what spending one means.

    The reasoning is printed before the meeting rather than after it, because that is when it
    was given — a choice explained after the fact is a different claim from one explained
    before, and only the second one can be read against what followed.
    """
    heading = f"Round {spent.number} of {ROUNDS} — {spent.formateur} meets {spent.counterparty}"
    lines = [
        heading,
        "-" * len(heading),
        "",
        f"Why {spent.formateur} chose {spent.counterparty}",
        _wrap(spent.choice.reasoning),
    ]
    lines.extend(_conversation(spent.bilateral))
    return "\n".join(lines)


def _conversation(bilateral: Bilateral) -> list[str]:
    """Every Exchange in order, and how the meeting finished."""
    lines: list[str] = []
    for exchange in bilateral.exchanges:
        lines.append("")
        lines.append(f"{exchange.speaker}:")
        lines.append(_wrap(exchange.message))
    lines.append("")
    lines.append(_ending(bilateral))
    return lines


def _ending(bilateral: Bilateral) -> str:
    count = len(bilateral.exchanges)
    plural = "Exchange" if count == 1 else "Exchanges"
    return f"Ended: {bilateral.ended_by()}, after {count} {plural}."


def _wrap(message: str) -> str:
    """One Agent's prose, wrapped — or a line saying there was none.

    An Agent that gives a tool call and no sentence beside it leaves a gap in the Transcript,
    and a silent gap reads as a rendering bug. Naming it is the honest version: the Run went
    on, and this is the part of it nobody explained.
    """
    paragraphs = [
        fill(paragraph.strip(), width=WIDTH, initial_indent=_INDENT, subsequent_indent=_INDENT)
        for paragraph in message.split("\n\n")
        if paragraph.strip()
    ]
    return "\n\n".join(paragraphs) if paragraphs else f"{_INDENT}(Nothing said.)"
