"""Rendering a Run for people to read — for now, the Transcript.

Read closely, never counted. It is rendered from the run record rather than printed as the
Run goes along — the record is the artifact ticket 06 serialises, and a Transcript that could
drift from it would not be worth reading.
"""

from __future__ import annotations

from textwrap import fill

from kbbl.models import Bilateral, Ending, Round, Run
from kbbl.referee import ROUNDS

WIDTH = 88
"""Where a message wraps. Transcripts are read, so lines have to be a readable length."""

_INDENT = "    "
"""Exchanges are indented under the speaker so the Transcript reads as a conversation rather
than as a wall of paragraphs."""


def render_transcript(run: Run) -> str:
    """Everything that happened in a Run, start to finish."""
    parts = [f"Run: {run.scenario}\nFormateur: {run.formateur}"]
    parts.extend(render_round(spent) for spent in run.rounds)
    return "\n\n\n".join(parts)


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
    if bilateral.ending is Ending.EXHAUSTED:
        return f"Ended: {count} {plural} spent, and neither side agreed or declared impasse."
    verb = "agreed" if bilateral.ending is Ending.AGREEMENT else "declared impasse"
    return f"Ended: {bilateral.closed_by} {verb}, after {count} {plural}."


def _wrap(message: str) -> str:
    paragraphs = [
        fill(paragraph.strip(), width=WIDTH, initial_indent=_INDENT, subsequent_indent=_INDENT)
        for paragraph in message.split("\n\n")
        if paragraph.strip()
    ]
    return "\n\n".join(paragraphs)
