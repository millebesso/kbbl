"""Helpers for building Scenario directories on disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from kbbl.models import Axis, Scenario
from kbbl.scenario import load_scenario

AXES = tuple(axis.value for axis in Axis)

FOUR_PARTY = Path(__file__).resolve().parents[1] / "fixtures" / "four-party"


@pytest.fixture
def four_party() -> Scenario:
    """The committed four-Party Fixture, loaded through the one and only load path."""
    return load_scenario(FOUR_PARTY)


def positions(**overrides: int) -> dict[str, int]:
    """A neutral Position on every Axis, with named Axes overridden."""
    return {axis: 0 for axis in AXES} | overrides


def mandate(name: str, seats: int, **overrides: Any) -> dict[str, Any]:
    """A minimal valid mandate, with named fields overridden."""
    base: dict[str, Any] = {
        "name": name,
        "seats": seats,
        "positions": positions(),
        "prefer_not": [],
        "to_govern": [],
        "to_support": [],
        "willingness_to_re_elect": 5,
    }
    return base | overrides


def write_scenario(directory: Path, *mandates: dict[str, Any]) -> Path:
    """Write one JSON file per mandate into `directory`, as a Scenario would be laid out."""
    directory.mkdir(parents=True, exist_ok=True)
    for entry in mandates:
        name = entry.get("name", "unnamed")
        (directory / f"{name}.json").write_text(json.dumps(entry), encoding="utf-8")
    return directory


def two_party(directory: Path, **overrides: Any) -> Path:
    """A two-Party Scenario summing to 349, with fields of the first mandate overridden."""
    return write_scenario(directory, mandate("AA", 200) | overrides, mandate("BB", 149))
