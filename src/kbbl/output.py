"""Rendering a Run for people to read — for now, the Transcript.

Read closely, never counted. It is rendered from the run record rather than printed as the
Run goes along — the record is the artifact ticket 06 serialises, and a Transcript that could
drift from it would not be worth reading.
"""

from __future__ import annotations

from textwrap import fill

from kbbl.models import Bilateral, Ending, Run

WIDTH = 88
"""Where a message wraps. Transcripts are read, so lines have to be a readable length."""

_INDENT = "    "
"""Exchanges are indented under the speaker so the Transcript reads as a conversation rather
than as a wall of paragraphs."""


def render_transcript(run: Run) -> str:
    """Everything that happened in a Run, start to finish."""
    parts = [f"Run: {run.scenario}\nFormateur: {run.formateur}"]
    parts.extend(render_bilateral(bilateral) for bilateral in run.bilaterals)
    return "\n\n\n".join(parts)


def render_bilateral(bilateral: Bilateral) -> str:
    """One private meeting: who met, every Exchange in order, and how it ended."""
    heading = f"Bilateral: {bilateral.formateur} meets {bilateral.counterparty}"
    lines = [heading, "-" * len(heading)]
    for exchange in bilateral.exchanges:
        lines.append("")
        lines.append(f"{exchange.speaker}:")
        lines.append(_wrap(exchange.message))
    lines.append("")
    lines.append(_ending(bilateral))
    return "\n".join(lines)


def _ending(bilateral: Bilateral) -> str:
    spent = len(bilateral.exchanges)
    plural = "Exchange" if spent == 1 else "Exchanges"
    if bilateral.ending is Ending.EXHAUSTED:
        return (
            f"Ended: {spent} {plural} spent, and neither side agreed or declared impasse."
        )
    verb = "agreed" if bilateral.ending is Ending.AGREEMENT else "declared impasse"
    return f"Ended: {bilateral.closed_by} {verb}, after {spent} {plural}."


def _wrap(message: str) -> str:
    paragraphs = [
        fill(paragraph.strip(), width=WIDTH, initial_indent=_INDENT, subsequent_indent=_INDENT)
        for paragraph in message.split("\n\n")
        if paragraph.strip()
    ]
    return "\n\n".join(paragraphs)
