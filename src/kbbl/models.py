"""The nouns a Run is made of: the party mandate, and the record of what was said.

Both arrive from outside the program — mandates as hand-written JSON (`docs/kbbl.md` §3),
Exchanges as an Agent's structured output (§2) — so every model here forbids unknown fields
and refuses type coercion: a typo or a malformed reply must fail loudly rather than reach an
Agent, or a Transcript, as a plausible value.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    Tag,
    computed_field,
    model_validator,
)

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
    reasoning: str = ""
    """Why this Party, in the Formateur's own words — empty when its Agent gave the call and
    no sentence beside it. Nobody in the Run reads a reasoning, so an absent one is a Round
    the record is silent about rather than a Round that did not happen."""


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

    def ended_by(self, reader: str | None = None) -> str:
        """How this meeting finished, said to whoever is reading it.

        The only place `Ending` is branched on to make prose. Three sites wanted it by this
        ticket — the Transcript, the Formateur hearing a meeting close, and the same
        Formateur seeing its spent Rounds recapped before it tables — and three copies of a
        three-way branch is three places for the vocabulary to drift.

        `reader` is the Party the sentence is being shown to: it is named "you". The second
        person is the reason the three sites looked different rather than a reason to keep
        them apart, so it is a parameter here instead of a fourth branch out there.
        """
        if self.ending is Ending.EXHAUSTED:
            return (
                "the messages ran out with neither of you agreeing or declaring impasse"
                if reader is not None
                else "neither side agreed or declared impasse"
            )
        who = "you" if self.closed_by == reader else self.closed_by
        verb = "agreed" if self.ending is Ending.AGREEMENT else "declared impasse"
        return f"{who} {verb}"


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


class Role(StrEnum):
    """What a Proposal makes of one Party: cabinet, backing from outside, or nothing at all.

    Not being named is a role rather than the absence of one, and saying so in the type is
    what stops the third case being spelled differently everywhere it comes up. It is also
    the role the cheapest thing on offer is bought from: a Party a Proposal asks for nothing
    still decides whether to abstain or block, and an Abstention is what a Formateur short of
    a majority actually needs (§5.2).
    """

    GOVERNMENT = "in the Government"
    SUPPORT_ONLY = "Support-only"
    UNNAMED = "not named"


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

    def role_of(self, name: str) -> Role:
        """What this Proposal makes of one Party.

        One answer in one place: three sites asked this question by branching on the two
        tuples themselves — what a Party is told it is being asked for, which of its two
        price lists it is charging on, and where a Proposal puts a Party somebody would
        rather not deal with — and three copies of the same branch is three chances for the
        third case to be forgotten.
        """
        if name in self.government:
            return Role.GOVERNMENT
        if name in self.support_only:
            return Role.SUPPORT_ONLY
        return Role.UNNAMED


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


class Gap(Strict):
    """The distance on one Axis between a Party's Position and a Proposal's Platform."""

    axis: Axis
    position: int
    platform: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def gap(self) -> int:
        """How far apart they are. Unsigned: a betrayal to the left is a betrayal.

        Computed here and written out all the same. An aggregation over a batch of
        `run.json` should be a loop and a `Counter` (§7), and one that had to subtract two
        columns to learn what a Party gave up would be re-deriving the Referee's own
        arithmetic from the record of it.
        """
        return abs(self.position - self.platform)


class GapReport(Strict):
    """Every Gap between one Party's Positions and one Platform, and the summaries over them.

    Held as data rather than rendered on the spot because §7 wants every Gap report a Party
    was shown to survive into `run.json`, where a later batch aggregation can count them.
    That is also why the summaries below are written out rather than left as properties: a
    Gap report is §5.4's whole defence, and whether Agents drift is a question asked of many
    Runs at once.
    """

    party: str = Field(min_length=1)
    gaps: tuple[Gap, ...] = Field(min_length=1)

    def on(self, axis: Axis) -> Gap:
        """This report's Gap on one Axis."""
        return next(gap for gap in self.gaps if gap.axis is axis)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def mean_gap(self) -> float:
        """The mean Gap over all ten Axes."""
        return sum(gap.gap for gap in self.gaps) / len(self.gaps)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def worst_gap(self) -> int:
        """The largest Gap in the report."""
        return max(gap.gap for gap in self.gaps)

    @property
    def worst(self) -> tuple[Gap, ...]:
        """Every Axis at the worst Gap. A tie is reported, never broken."""
        return tuple(gap for gap in self.gaps if gap.gap == self.worst_gap)


class Placement(Strict):
    """One Party somebody would rather not deal with, and what a Proposal makes of it."""

    party: str = Field(min_length=1)
    role: Role


class ExclusionReport(Strict):
    """Where a Proposal puts every Party one Party would rather not deal with (§5.4).

    The information exists in two places and was never put together: a Persona says "V. That
    is a preference, not a veto" and a Proposal names V in its Government, and nothing stood
    between them at the moment a Ballot was cast. §5.4's argument — that an Agent asked
    abstractly to hold its ground drifts, and the same Agent shown the number it is
    abandoning does not — is about policy distance only because that is the form the risk
    was first met in. It applies unchanged to a coalition betrayal.

    Held as data rather than rendered on the spot for the reason `GapReport` is: §7 wants
    every report a Party was shown to survive into `run.json`, where a batch can count how
    often a Party waved one of these through.

    A Party with no Exclusions has no report at all rather than an empty one — which is why
    `placements` is never empty, and why `referee.exclusion_report` answers None.
    """

    party: str = Field(min_length=1)
    placements: tuple[Placement, ...] = Field(min_length=1)

    @property
    def in_the_base(self) -> tuple[Placement, ...]:
        """The ones this Proposal is actually built on, in cabinet or backing it outside.

        One tuple because the Base has one arithmetic (`Proposal.base`): a Party that would
        rather not deal with V is being asked to wave V's seats through either way.
        """
        return tuple(
            placed for placed in self.placements if placed.role is not Role.UNNAMED
        )


class Usage(Strict):
    """What one request to the model cost, and the Cassette holding the whole of it.

    §6 budgets a Run at roughly 130 calls, and cost is the first thing anybody aggregates
    over a batch of them. Recomputing it afterwards from a Transcript is not possible at
    all — the Transcript holds what was said, never what it was billed at — so the numbers
    are taken as each reply arrives.

    The Cassette key is here because it is the one handle on what was actually *sent*. No
    artifact repeats a Persona or a briefing in full, and the request behind this key holds
    every word the Agent was shown.

    Nothing here says whether this request was replayed or paid for live. That is a fact
    about the process rather than about the Run, and a record carrying it could not be
    identical under `--replay`.
    """

    party: str = Field(min_length=1)
    cassette: str = Field(min_length=1)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0


class Judgement(Strict):
    """One Party's Ballot on a Proposal, and what it said as it cast it.

    The Ballot is the enumerated field the Referee counts; the reasoning is prose and exists
    for the Transcript alone (§2). They are one record because reading a Ballot without the
    sentence beside it is exactly what §8 says a full Run is *not* for — the Ballots are read
    closely, never counted, and the count is the Referee's job from the enum.
    """

    party: str = Field(min_length=1)
    ballot: Ballot
    reasoning: str = ""
    """Why, in the Party's own words. Empty when its Agent cast the Ballot and said nothing
    beside it: the Ballot is what the Referee counts, and it is there either way."""


class Run(Strict):
    """The record of one Run, accumulated in memory as it happens.

    Everything an Agent said belongs here rather than only in the Transcript: ticket 06
    serialises this, and §7 asks that aggregating a batch of Runs later be a loop and a
    `Counter` rather than a re-instrumentation.

    v1 is one Formateur and one Attempt (§10), so this record is both. When there are several
    Attempts, the Proposal and the Judgements belong to one of them and this splits in two.

    Nothing here is assembled at the end. A `Ledger` fills this in as the Run happens, so a
    Run that breaks mid-Bilateral still holds every Exchange it paid for — which is what
    `finished` below is for, and the reason it is the only field an unfinished record is
    dishonest without.
    """

    scenario: str = Field(min_length=1)
    formateur: str = Field(min_length=1)
    rounds: tuple[Round, ...] = ()
    proposal: Proposal | None = None
    """What the Formateur tabled, or None if it Stood down. A finished Attempt has one or the
    other, and the two outcomes are not the same thing: a Proposal voted down spends one of
    the Chamber's four Votes and Standing down spends none (§5.3)."""
    reasoning: str = ""
    """The Formateur's own account of how it ended its Attempt — the Proposal above, or
    Standing down instead of tabling one. Named for the prose rather than for either act,
    because Standing down is by definition the one where nothing was tabled. It is the only
    account there is of why an Attempt ended the way it did: a Stand down leaves no Proposal
    behind to read it off."""
    judgements: tuple[Judgement, ...] = ()
    gap_reports: tuple[GapReport, ...] = ()
    """Every Gap report the Referee put in front of a Party before it voted (§5.4).

    Beside the Judgements rather than inside one, because a Gap report is something a Party
    was *shown* and a Judgement is what it then did. Each report names its own Party, so
    reading the two together is a join on a name.
    """
    exclusion_reports: tuple[ExclusionReport, ...] = ()
    """Every Exclusion report the Referee put in front of a Party before it voted.

    Beside the Gap reports rather than inside them: they answer different questions about
    the same moment — one what the Platform costs this Party's voters, the other who the
    Proposal would have it govern beside — and a Party that named nobody has one and not the
    other. Reading either against a Judgement is a join on a name.
    """
    usage: tuple[Usage, ...] = ()
    """What every request in this Run cost, in the order they were made."""
    finished: bool = False
    """Whether the Attempt reached an end of its own — a Proposal put to the Chamber, or the
    Formateur Standing down without tabling one.

    False is a Run that *stopped*: an Agent returned something unreadable, a Cassette was
    missing, the process died. That is not a third way for an Attempt to end and it is not a
    Stand down either, which is exactly why it has to be written down — the two are
    otherwise the same record, a Run holding no Proposal, and only one of them is a decision
    somebody made."""

    @model_validator(mode="after")
    def _check_the_record_agrees_with_itself(self) -> Self:
        """A tabled Proposal was voted on, and a Stand down was not. Whether *every* Party
        voted is `count_vote`'s to say, because only it is handed the Chamber."""
        if self.judgements and self.proposal is None:
            raise ValueError(
                f"{self.formateur} tabled no Proposal, and "
                f"{len(self.judgements)} Ballots were cast on it"
            )
        if self.finished and self.proposal is not None and not self.judgements:
            raise ValueError(
                f"{self.formateur} tabled a Proposal and no Ballot was cast on it. Tabling "
                f"one spends a Vote, and Standing down is the end of an Attempt that does not"
            )
        voted = [judgement.party for judgement in self.judgements]
        twice = sorted({name for name in voted if voted.count(name) > 1})
        if twice:
            raise ValueError(f"a Party cast more than one Ballot: {', '.join(twice)}")
        return self

    @property
    def ballots(self) -> dict[str, Ballot]:
        """Every Party's Ballot, in the shape `count_vote` counts. The record owns this: three
        callers were reshaping it for themselves, which is three places to get it wrong."""
        return {judgement.party: judgement.ballot for judgement in self.judgements}

    @property
    def stood_down(self) -> bool:
        """Whether the Formateur conceded without tabling (§5.3).

        A finished Attempt holding no Proposal, and finished is half of it: a Run that
        stopped holds no Proposal either, and calling that a Stand down would credit an
        Agent with a decision it never got to make.
        """
        return self.finished and self.proposal is None


class Outcome(StrEnum):
    """How a Run came out, in the one word a batch aggregation counts (§7).

    Three of these are ends an Attempt reached: a government formed, a Proposal the Chamber
    threw out, a Formateur that Stood down rather than table one. The fourth is a Run that
    stopped, and it is named here rather than left as a gap so that counting a batch never
    silently reads a broken Run as a Stand down.
    """

    FORMED = "formed"
    REJECTED = "rejected"
    STOOD_DOWN = "stood down"
    UNFINISHED = "unfinished"


class Count(Strict):
    """A Vote's arithmetic as an artifact carries it: the seats each way, and what they did.

    Not a second name for the Vote. The Vote is the Chamber's single decision and
    `referee.count_vote` is the only place it is reckoned; this is that reckoning written
    down, so that reading a Run back needs neither the Scenario's seats nor a second pass
    over the Ballots.
    """

    yes: int
    abstain: int
    no: int
    base_seats: int
    """The seats in the Proposal's Base, carried over from the Vote that reckoned it and
    reported for the same reason `referee.Vote.base_seats` gives."""
    passed: bool


class Record(Strict):
    """`run.json`: one whole Run, and the Referee's arithmetic over it.

    Self-contained on purpose. §7 asks that aggregating a batch of Runs later be a loop and
    a `Counter`, and an aggregation that had to re-load a Scenario to learn who held what
    seats — or re-count a Vote to learn whether a government formed — is precisely the
    re-instrumentation that section exists to prevent. So the outcome, the chamber and the
    count sit beside the record rather than being derivable from it.

    It carries no timestamp. `result.json` does (§9), and keeping the two apart is what lets
    this file come out byte-identical when a Run is replayed.
    """

    scenario: str = Field(min_length=1)
    outcome: Outcome
    chamber: dict[str, int]
    """Every Party in the Scenario and the seats it holds, largest first."""
    count: Count | None = None
    """The Vote, or None when the Chamber held none — a Stand down, or a Run that stopped."""
    run: Run


class Result(Strict):
    """`result.json`: how a Run came out, and when.

    The timestamp is the whole reason this is its own file. KBBL is a prediction of an open
    question rather than a retrodiction of a settled one (§9), so a later comparison against
    the real government should be a lookup: what was predicted, and as of when.
    """

    scenario: str = Field(min_length=1)
    formateur: str = Field(min_length=1)
    outcome: Outcome
    at: datetime
    government: tuple[str, ...] = ()
    """Who governs under the Proposal that was tabled. Empty when none was."""
    support_only: tuple[str, ...] = ()
    count: Count | None = None
