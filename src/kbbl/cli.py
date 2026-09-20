"""`kbbl run <scenario>` — load a Scenario, print the chamber, and run one Formateur's Attempt.

Live is the default and `--replay` opts out (§11.5): a Run that negotiates is a Run that
calls the model, and the free path is the recorded one.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from kbbl.agents import AgentError
from kbbl.cassettes import CassetteMiss, Cassettes
from kbbl.ledger import Ledger
from kbbl.loop import attempt
from kbbl.models import Scenario
from kbbl.output import render_transcript, write_run
from kbbl.referee import render_blocking_groupings, render_seat_table
from kbbl.scenario import ScenarioError, load_scenario

CASSETTES = Path("cassettes")
"""Where recordings live. Each Scenario gets its own drawer under it, so two Scenarios cannot
collide on a request that happens to hash the same."""

OUT = Path("out")
"""Where a Run's artifacts go (§11.5). Each Run gets its own timestamped directory under it,
because a Run is never written twice and never written over."""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kbbl", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="load a Scenario and negotiate")
    run.add_argument("scenario", help="directory of Party mandates")
    run.add_argument(
        "--replay",
        action="store_true",
        help="replay from Cassettes, making no API calls",
    )
    run.add_argument(
        "--out",
        type=Path,
        default=OUT,
        metavar="DIR",
        help=(
            "where to write this Run's artifacts; each Run gets its own timestamped "
            f"directory under it (default: {OUT})"
        ),
    )
    run.add_argument(
        "--cassettes",
        type=Path,
        default=CASSETTES,
        metavar="DIR",
        help=(
            "root directory of Cassettes; each Scenario gets its own drawer under it "
            f"(default: {CASSETTES})"
        ),
    )
    arguments = parser.parse_args(argv)

    try:
        scenario = load_scenario(arguments.scenario)
    except ScenarioError as error:
        print(error, file=sys.stderr)
        return 1

    formateur, *others = scenario.parties
    if not others:
        print(
            f"{scenario.name} has only one Party, so there is nobody for "
            f"{formateur.name} to meet",
            file=sys.stderr,
        )
        return 1

    print(f"Scenario: {scenario.name} ({len(scenario.parties)} Parties, {scenario.seats} seats)")
    print()
    print(render_seat_table(scenario))
    print()
    print(render_blocking_groupings(scenario))
    print()

    ledger = Ledger(scenario=scenario.name, formateur=formateur.name)
    broke: Exception | None = None
    try:
        attempt(
            scenario,
            formateur=formateur,
            cassettes=Cassettes(arguments.cassettes / scenario.name, replay=arguments.replay),
            ledger=ledger,
        )
    except (AgentError, CassetteMiss) as error:
        broke = error
    except BaseException:
        # A network error, or a Ctrl-C twenty minutes into a live Run. Not this command's
        # to explain, and the traceback is the honest answer — but the Exchanges it
        # interrupted were paid for all the same, so they are kept on the way out.
        _keep(arguments.out, scenario, ledger)
        raise

    negotiated = ledger.run
    if broke is not None and not negotiated.usage:
        # Nothing was paid for, so there is nothing to keep. A Run that never reached the
        # model has no Exchanges, no Ballots and no bill — writing a directory for it would
        # leave a reader an artifact of an Attempt that never started.
        print(broke, file=sys.stderr)
        return 1

    print(render_transcript(scenario, negotiated))
    print()
    _keep(arguments.out, scenario, ledger)
    if broke is not None:
        print(broke, file=sys.stderr)
        return 1
    return 0


def _keep(out: Path, scenario: Scenario, ledger: Ledger) -> Path | None:
    """Write what this Run paid for, and say where. None if it paid for nothing.

    Called on every way out of an Attempt, including the ways that do not return. A Run at
    §6's ~130 calls is a dollar and a half of transcript, and losing it to an exception on
    the way out is the one failure the record accumulates in order to prevent.
    """
    if not ledger.run.usage:
        return None
    written = write_run(out, scenario, ledger.run)
    print(f"Written to {written}")
    return written
