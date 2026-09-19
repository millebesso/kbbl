"""The party mandate, validated at the boundary (`docs/kbbl.md` §3).

Mandates are hand-written JSON, so every model here forbids unknown fields and refuses
type coercion: a typo must fail loudly rather than reach an Agent as a plausible value.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag, model_validator

TOTAL_SEATS = 349
"""Seats in the chamber. A Scenario's Parties must sum to exactly this."""


class Axis(StrEnum):
    """One of the ten policy dimensions, each scored -5..+5."""

    ECONOMIC = "economic"
    ENVIRONMENT = "environment"
    MILITARY = "military"
    HEALTH = "health"
    IMMIGRATION = "immigration"
    LAW_AND_ORDER = "law_and_order"
    EDUCATION = "education"
    TRANSPORT = "transport"
    SOCIAL = "social"
    INTERNATIONAL = "international"


Score = Annotated[int, Field(ge=-5, le=5)]
"""A value on an Axis: -5..+5, for both a Party's Positions and a Proposal's Platform."""


class MandateModel(BaseModel):
    """Shared strictness for every model built out of hand-written mandate JSON."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Positions(MandateModel):
    """A Party's own value on each of the ten Axes. All ten are required."""

    economic: Score
    environment: Score
    military: Score
    health: Score
    immigration: Score
    law_and_order: Score
    education: Score
    transport: Score
    social: Score
    international: Score


class AxisDemand(MandateModel):
    """A price the Referee can check: a constraint on one Axis of a Platform."""

    axis: Axis
    op: Literal[">=", "<=", "=="]
    value: Score


class TextDemand(MandateModel):
    """A price only an Agent can interpret. The Referee never reads it."""

    text: str = Field(min_length=1)


def _demand_kind(value: Any) -> str | None:
    """Which kind of Demand this is, decided before either shape is validated.

    Without this, a Demand with one field wrong is reported twice over — once as a broken
    AxisDemand and once as a broken TextDemand. Classifying first buys one honest error.
    """
    if isinstance(value, AxisDemand) or (isinstance(value, dict) and "axis" in value):
        return "axis"
    if isinstance(value, TextDemand) or (isinstance(value, dict) and "text" in value):
        return "text"
    return None


Demand = Annotated[
    Annotated[AxisDemand, Tag("axis")] | Annotated[TextDemand, Tag("text")],
    Discriminator(_demand_kind),
]
"""A price a Party names. The two forms mix freely within either price list."""


class Party(MandateModel):
    """One parliamentary party, as defined by its hand-written mandate."""

    name: str = Field(min_length=1)
    seats: int = Field(ge=0, le=TOTAL_SEATS)
    positions: Positions
    prefer_not: tuple[str, ...] = ()
    to_govern: tuple[Demand, ...] = ()
    to_support: tuple[Demand, ...] = ()
    willingness_to_re_elect: int = Field(ge=0, le=10)


class Scenario(MandateModel):
    """A complete set of Party mandates whose seats sum to 349. The input to a Run."""

    name: str = Field(min_length=1)
    parties: tuple[Party, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_chamber(self) -> Self:
        names = [party.name for party in self.parties]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f"two Parties share a name: {', '.join(duplicates)}")

        if self.seats != TOTAL_SEATS:
            raise ValueError(f"seats sum to {self.seats}, not {TOTAL_SEATS}")

        known = set(names)
        for party in self.parties:
            for excluded in party.prefer_not:
                if excluded not in known:
                    raise ValueError(
                        f"{party.name} excludes {excluded!r}, which is not a Party "
                        f"in this Scenario"
                    )
        return self

    @property
    def seats(self) -> int:
        return sum(party.seats for party in self.parties)

    def party(self, name: str) -> Party:
        for party in self.parties:
            if party.name == name:
                return party
        raise KeyError(f"no Party named {name!r} in Scenario {self.name!r}")
