"""The nouns a Run is made of: the party mandate, and the record of what was said.

Both arrive from outside the program — mandates as hand-written JSON (`docs/kbbl.md` §3),
Exchanges as an Agent's structured output (§2) — so every model here forbids unknown fields
and refuses type coercion: a typo or a malformed reply must fail loudly rather than reach an
Agent, or a Transcript, as a plausible value.
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


AXIS_POLES: dict[Axis, tuple[str, str]] = {
    Axis.ECONOMIC: ("state-led redistribution", "free market, low tax"),
    Axis.ENVIRONMENT: ("growth before climate", "climate before growth"),
    Axis.MILITARY: ("disarmament, non-alignment", "heavy defence, alliance"),
    Axis.HEALTH: ("fully public provision", "market provision"),
    Axis.IMMIGRATION: ("restrictive", "open, generous"),
    Axis.LAW_AND_ORDER: ("rehabilitation, liberties", "punitive, tough"),
    Axis.EDUCATION: ("comprehensive, public", "school choice, private"),
    Axis.TRANSPORT: ("roads and cars", "rail and public transit"),
    Axis.SOCIAL: ("traditional values", "progressive, liberal values"),
    Axis.INTERNATIONAL: ("sovereigntist, EU-sceptic", "internationalist, pro-EU"),
}
"""What -5 and +5 mean on each Axis.

A bare `economic: +5` says nothing to an Agent, so the poles have to travel with the number.
They are a convention of this repo rather than a fact about politics — `fixtures/README.md`
states the same table in prose, and this is the copy the Personas are built from.
"""


class Strict(BaseModel):
    """Shared strictness for every model in KBBL. Nothing here is coerced, guessed or ignored."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Positions(Strict):
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


class AxisDemand(Strict):
    """A price the Referee can check: a constraint on one Axis of a Platform."""

    axis: Axis
    op: Literal[">=", "<=", "=="]
    value: Score


class TextDemand(Strict):
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


class Party(Strict):
    """One parliamentary party, as defined by its hand-written mandate."""

    name: str = Field(min_length=1)
    seats: int = Field(ge=0, le=TOTAL_SEATS)
    positions: Positions
    prefer_not: tuple[str, ...] = ()
    to_govern: tuple[Demand, ...] = ()
    to_support: tuple[Demand, ...] = ()
    willingness_to_re_elect: int = Field(ge=0, le=10)


class Scenario(Strict):
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


class Ending(StrEnum):
    """How a Bilateral finished."""

    AGREEMENT = "agreement"
    IMPASSE = "impasse"
    EXHAUSTED = "exhausted"
    """Three Exchanges each way spent without either side exiting. Only a Bilateral ends this
    way — an Exchange can declare the other two, but no side can declare exhaustion."""


Declaration = Literal[Ending.AGREEMENT, Ending.IMPASSE]
"""The two Endings a side may declare, exiting the Bilateral early."""


class Exchange(Strict):
    """One message from one side of a Bilateral, and whether it ends the meeting."""

    speaker: str = Field(min_length=1)
    message: str = Field(min_length=1)
    declares: Declaration | None = None


class Bilateral(Strict):
    """The private meeting a Round buys: who met, what was said, and how it finished."""

    formateur: str = Field(min_length=1)
    counterparty: str = Field(min_length=1)
    exchanges: tuple[Exchange, ...] = Field(min_length=1)

    @property
    def ending(self) -> Ending:
        declared = self.exchanges[-1].declares
        return declared if declared is not None else Ending.EXHAUSTED

    @property
    def closed_by(self) -> str | None:
        """The side that exited early, or None if the meeting simply ran out of Exchanges."""
        return self.exchanges[-1].speaker if self.exchanges[-1].declares is not None else None


class Run(Strict):
    """The record of one Run, accumulated in memory as it happens.

    Everything an Agent said belongs here rather than only in the Transcript: ticket 06
    serialises this, and §7 asks that aggregating a batch of Runs later be a loop and a
    `Counter` rather than a re-instrumentation.
    """

    scenario: str = Field(min_length=1)
    formateur: str = Field(min_length=1)
    bilaterals: tuple[Bilateral, ...] = ()
