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


def signed(value: int) -> str:
    """An Axis value as it is written everywhere: `+3`, `-3`, `0`.

    A bare `3` on a scale that runs -5..+5 reads as a magnitude rather than a position, and
    both the Referee's reports and an Agent's persona show these side by side in columns.
    """
    return f"{value:+d}" if value else "0"


class Strict(BaseModel):
    """Shared strictness for every model in KBBL. Nothing here is coerced, guessed or ignored."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Axes(Strict):
    """A value on each of the ten Axes. All ten are required.

    Positions and a Platform are the same ten numbers in the same units and differ only in
    who owns them, so they are one shape here and two nouns everywhere else (§5.4 compares
    them Axis by Axis, which only means anything if they are commensurable).
    """

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

    def on(self, axis: Axis) -> int:
        """The value on one Axis, reached by Axis rather than by attribute name."""
        value: int = getattr(self, axis.value)
        return value


class Positions(Axes):
    """A Party's own value on each of the ten Axes — what it went to the election on."""


class Platform(Axes):
    """The single agreed value on each Axis that a Proposal commits its government to."""


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


class Choice(Strict):
    """A Formateur's decision about how to spend one Round: whom to meet, and why.

    The reasoning is prose, and nobody but the record ever reads it. The name is the only part
    the Referee acts on, which is why it arrives as a short enumerated field rather than as
    something read out of the prose (§2).
    """

    counterparty: str = Field(min_length=1)
    reasoning: str = Field(min_length=1)


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


class Round(Strict):
    """One unit of a Formateur's budget: the Choice it made, and the Bilateral that bought.

    The chosen Party is not stored twice. `Bilateral.counterparty` is who was actually met,
    and a Round whose Choice names somebody else is a record disagreeing with itself — so it
    is refused here rather than serialised for ticket 06 to puzzle over.
    """

    number: int = Field(ge=1)
    choice: Choice
    bilateral: Bilateral

    @model_validator(mode="after")
    def _check_it_met_who_it_chose(self) -> Self:
        if self.bilateral.counterparty != self.choice.counterparty:
            raise ValueError(
                f"Round {self.number} chose {self.choice.counterparty} and met "
                f"{self.bilateral.counterparty}"
            )
        return self

    @property
    def formateur(self) -> str:
        """The Party whose Round this was."""
        return self.bilateral.formateur

    @property
    def counterparty(self) -> str:
        """The Party this Round was spent on."""
        return self.bilateral.counterparty


class Proposal(Strict):
    """What a Formateur tables for a vote. One per Attempt, and tabling it ends the Attempt.

    No ministries: cabinet portfolios are deliberately out of scope (§4), because modelling
    them needs a ministry list *and* a per-Party valuation of each post — a second preference
    model this project does not have.
    """

    formateur: str = Field(min_length=1)
    platform: Platform
    government: tuple[str, ...] = Field(min_length=1)
    support_only: tuple[str, ...] = ()
    commitments: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _check_roles(self) -> Self:
        for role, named in (("Government", self.government), ("Support-only", self.support_only)):
            repeated = sorted({name for name in named if named.count(name) > 1})
            if repeated:
                raise ValueError(f"{role} names the same Party twice: {', '.join(repeated)}")

        both = sorted(set(self.government) & set(self.support_only))
        if both:
            raise ValueError(
                f"a Party is in both Government and Support-only: {', '.join(both)}. "
                f"Support-only is backing from outside cabinet, so the two are exclusive"
            )
        return self

    @property
    def base(self) -> tuple[str, ...]:
        """This Proposal's Base: every Party behind it, in cabinet or backing it from outside.

        They are one list here because §4 gives them one arithmetic: Support-only seats
        count toward the Blocking minority exactly as Government seats do, and without that
        the distinction between the two is decorative. One list is not one promise, though —
        a Party in the Base is still free to cast a No Ballot on the Proposal it governs under.
        """
        return self.government + self.support_only


class Ballot(StrEnum):
    """One Party's Yes, Abstain or No in a Vote.

    A Ballot is one Party's; the Vote is the Chamber's single decision on a Proposal, and a
    Run may hold four of those. Only No is load-bearing under Negative parliamentarism, which
    is what makes an Abstention purchasable: a Party that will neither join nor support can
    still be paid to step out of the way (§5.2).
    """

    YES = "Yes"
    ABSTAIN = "Abstain"
    NO = "No"


class Run(Strict):
    """The record of one Run, accumulated in memory as it happens.

    Everything an Agent said belongs here rather than only in the Transcript: ticket 06
    serialises this, and §7 asks that aggregating a batch of Runs later be a loop and a
    `Counter` rather than a re-instrumentation.
    """

    scenario: str = Field(min_length=1)
    formateur: str = Field(min_length=1)
    rounds: tuple[Round, ...] = ()
