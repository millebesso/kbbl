"""`kbbl run <scenario>` — load a Scenario, print the chamber, and spend a Formateur's Rounds.

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
from kbbl.loop import attempt
from kbbl.models import Run
from kbbl.output import render_transcript
from kbbl.referee import render_blocking_groupings, render_seat_table
from kbbl.scenario import ScenarioError, load_scenario

CASSETTES = Path("cassettes")
"""Where recordings live. Each Scenario gets its own drawer under it, so two Scenarios cannot
collide on a request that happens to hash the same."""


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

    try:
        rounds = attempt(
            scenario,
            formateur=formateur,
            cassettes=Cassettes(arguments.cassettes / scenario.name, replay=arguments.replay),
        )
    except (AgentError, CassetteMiss) as error:
        print(error, file=sys.stderr)
        return 1

    record = Run(scenario=scenario.name, formateur=formateur.name, rounds=rounds)
    print(render_transcript(record))
    return 0
