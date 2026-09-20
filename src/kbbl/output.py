"""What a Run leaves behind: a Transcript to read, and a record to count.

Every Run writes one directory holding all three (§7). They answer different questions and
neither substitutes for the other — the Transcript is read closely and never counted, and
`run.json` is counted in batches and read by nobody. `result.json` is the one-line answer
with the date on it, because KBBL predicts an open question rather than settling one (§9).

All three are rendered from the run record rather than printed as the Run goes along, so
they cannot drift from it or from each other.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from textwrap import fill

from pydantic import BaseModel

from kbbl.models import Bilateral, Judgement, Record, Result, Round, Run, Scenario
from kbbl.referee import ROUNDS, count_vote, record, render_proposal, render_vote

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

    A Run that stopped is a third thing and reads as a third thing. It holds no Proposal,
    exactly as a Stand down does, and telling the reader that the Formateur conceded would be
    the Transcript inventing a decision nobody made.
    """
    if not run.finished:
        return _stopped(scenario, run)

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


def _stopped(scenario: Scenario, run: Run) -> str:
    """A Run that broke: everything it got to, and then the fact that it stopped there.

    Whatever it reached is printed first — a Proposal it managed to table, the Ballots cast
    before it broke — because `run.json` holds them and the two artifacts must not disagree.
    The Vote is not counted, because there is nothing to count: `count_vote` is handed the
    whole Chamber and a Run that stopped mid-Vote has polled part of one.
    """
    parts = []
    if run.proposal is not None:
        parts.append(
            _under("The Proposal", f"{_said_by(run)}{render_proposal(scenario, run.proposal)}")
        )
    if run.judgements:
        parts.append(
            _under(
                "The Vote, as far as it got",
                "\n\n".join(_ballot(cast) for cast in run.judgements),
            )
        )
    parts.append(
        _under(
            f"{run.formateur}'s Attempt stopped",
            f"This Run did not reach an end of its own. Everything above is what it paid "
            f"for before it stopped, and {_as_far_as(run)}",
        )
    )
    return "\n\n\n".join(parts)


def _as_far_as(run: Run) -> str:
    """How far a Run that stopped got — said exactly, because the record says it exactly."""
    if run.proposal is None:
        return "no Proposal was tabled and the chamber held no Vote."
    cast = len(run.judgements)
    if not cast:
        return "the chamber had not begun voting on the Proposal above."
    plural = "Party" if cast == 1 else "Parties"
    return (
        f"the chamber was voting: {cast} {plural} had cast a Ballot and the Vote was never "
        f"counted."
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


# --- the artifacts one Run leaves behind ---------------------------------------------------


TRANSCRIPT = "transcript.md"
"""Read closely, never counted (§8)."""

RECORD = "run.json"
"""Counted in batches, read by nobody. The complete Record (§7)."""

RESULT = "result.json"
"""The one-line answer, with the date it was answered on (§9)."""


def write_run(
    directory: Path | str, scenario: Scenario, run: Run, *, at: datetime | None = None
) -> Path:
    """Write one Run's three artifacts into a fresh timestamped directory, and return it.

    Handed the record rather than asked to produce one, so that a Run which stopped writes
    exactly what it paid for. That is the whole reason the record accumulates: an Attempt
    that breaks in its fourth Bilateral has bought three meetings and part of a fourth, and
    those cost real money (§6).

    `at` is the Run's timestamp. It reaches `result.json` and names this directory, and it
    is deliberately the only thing here that a second replay of the same Cassettes would
    write differently.
    """
    stamped = at if at is not None else datetime.now(UTC)
    written = _fresh(Path(directory), stamped)
    recorded = record(scenario, run)
    (written / TRANSCRIPT).write_text(
        render_transcript(scenario, run) + "\n", encoding="utf-8"
    )
    (written / RECORD).write_text(_json(recorded), encoding="utf-8")
    (written / RESULT).write_text(_json(_result(recorded, stamped)), encoding="utf-8")
    return written


def _result(recorded: Record, at: datetime) -> Result:
    """`result.json` from `run.json`: the same outcome, said in one breath and dated.

    Read off the Record rather than off the Run, so the two files cannot disagree about how
    the same Run came out.
    """
    proposal = recorded.run.proposal
    return Result(
        scenario=recorded.scenario,
        formateur=recorded.run.formateur,
        outcome=recorded.outcome,
        at=at,
        government=() if proposal is None else proposal.government,
        support_only=() if proposal is None else proposal.support_only,
        count=recorded.count,
    )


def _json(model: BaseModel) -> str:
    """One artifact, indented to be diffed by eye and newline-terminated like a text file."""
    return model.model_dump_json(indent=2) + "\n"


def _fresh(directory: Path, at: datetime) -> Path:
    """`run-<timestamp>/`, and never a directory that already holds a Run.

    Two Runs started within the same second would otherwise write over one another, and a
    Run costs about $1.56 (§6) — overwriting one to save a suffix is the wrong trade. The
    directory is claimed by creating it rather than by looking first, so two Runs racing for
    the same name cannot both win it.
    """
    stamp = at.astimezone(UTC).strftime("%Y%m%d-%H%M%S")
    index = 1
    while True:
        written = directory / f"run-{stamp}{'' if index == 1 else f'-{index}'}"
        try:
            written.mkdir(parents=True)
        except FileExistsError:
            index += 1
            continue
        return written
