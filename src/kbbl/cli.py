"""`kbbl run <scenario>` — load a Scenario, print the chamber, exit."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from kbbl.referee import render_blocking_groupings, render_seat_table
from kbbl.scenario import ScenarioError, load_scenario


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kbbl", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="load a Scenario and print the chamber")
    run.add_argument("scenario", help="directory of Party mandates")
    arguments = parser.parse_args(argv)

    try:
        scenario = load_scenario(arguments.scenario)
    except ScenarioError as error:
        print(error, file=sys.stderr)
        return 1

    print(
        f"Scenario: {scenario.name} "
        f"({len(scenario.parties)} Parties, {scenario.seats} seats)"
    )
    print()
    print(render_seat_table(scenario))
    print()
    print(render_blocking_groupings(scenario))
    return 0
