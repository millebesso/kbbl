"""The Referee: seat arithmetic, Gaps, demand satisfaction, and the vote.

This is the part of the system allowed to be certain (§8), and everything in it computes and
reports. Nothing here constrains an Agent's choice — a Gap report is shown to a Party as
feedback and it remains free to accept a Platform five points from its voters, a Demand the
Referee reports unmet may still be waived by the Party that named it, and a Party may vote
against a Proposal it is named in. Nothing here reads prose either: a free-text Demand is
reported as unevaluated rather than guessed at (§2).
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from itertools import combinations
from typing import NamedTuple

from kbbl.models import (
    TOTAL_SEATS,
    Axis,
    AxisDemand,
    Demand,
    Ballot,
    Party,
    Platform,
    Proposal,
    Scenario,
    TextDemand,
    signed,
)

BLOCKING_MINORITY = 175
"""The seats that must vote No to defeat a Proposal — an absolute majority of 349."""

ROUNDS = 5
"""The Rounds one Formateur's Attempt is worth (§5.3).

The budget is the Referee's to hold rather than the Formateur's to feel (§2), and it is the
whole reason whom to court is a decision at all: five Rounds do not reach eight Parties, so a
Formateur that spends them badly fails (§5.1).
"""


class Grouping(NamedTuple):
    """A set of Parties and the seats they hold between them."""

    parties: tuple[str, ...]
    seats: int


def blocking_groupings(scenario: Scenario) -> list[Grouping]:
    """Every *minimal* grouping that reaches the Blocking minority.

    Minimal means no member can be dropped and still reach it. Listing every grouping
    instead would bury the interesting ones under their own supersets; listing the minimal
    ones names each kingmaker exactly once.
    """
    by_seats = {party.name: party.seats for party in scenario.parties}
    found: list[Grouping] = []
    for size in range(1, len(by_seats) + 1):
        for names in combinations(by_seats, size):
            seats = sum(by_seats[name] for name in names)
            if seats < BLOCKING_MINORITY:
                continue
            if any(seats - by_seats[name] >= BLOCKING_MINORITY for name in names):
                continue
            found.append(Grouping(names, seats))
    found.sort(key=lambda grouping: (len(grouping.parties), -grouping.seats, grouping.parties))
    return found


def render_seat_table(scenario: Scenario) -> str:
    """The chamber, largest Party first."""
    width = max(5, *(len(party.name) for party in scenario.parties))
    rule = f"{'-' * width}  -----  ------"
    lines = [f"{'Party':<{width}}  Seats   Share", rule]
    for party in scenario.parties:
        share = 100 * party.seats / scenario.seats
        lines.append(f"{party.name:<{width}}  {party.seats:>5}  {share:>5.1f}%")
    lines.append(rule)
    lines.append(f"{'Total':<{width}}  {scenario.seats:>5}  {100.0:>5.1f}%")
    return "\n".join(lines)


def render_blocking_groupings(scenario: Scenario) -> str:
    """Which groupings clear the Blocking minority, and by how much."""
    groupings = blocking_groupings(scenario)
    lines = [
        f"Blocking minority: {BLOCKING_MINORITY} of {TOTAL_SEATS} seats.",
        "Minimal groupings that reach it:",
    ]
    if not groupings:
        lines.append("  none")
        return "\n".join(lines)

    labels = [" + ".join(grouping.parties) for grouping in groupings]
    width = max(len(label) for label in labels)
    for label, grouping in zip(labels, groupings, strict=True):
        margin = grouping.seats - BLOCKING_MINORITY
        lines.append(f"  {label:<{width}}  {grouping.seats:>3}  (+{margin})")
    return "\n".join(lines)


class Gap(NamedTuple):
    """The distance on one Axis between a Party's Position and a Proposal's Platform."""

    axis: Axis
    position: int
    platform: int

    @property
    def gap(self) -> int:
        """How far apart they are. Unsigned: a betrayal to the left is a betrayal."""
        return abs(self.position - self.platform)


class GapReport(NamedTuple):
    """Every Gap between one Party's Positions and one Platform, and the summaries over them.

    Held as data rather than rendered on the spot because §7 wants every Gap report a Party
    was shown to survive into `run.json`, where a later batch aggregation can count them.
    """

    party: str
    gaps: tuple[Gap, ...]

    def on(self, axis: Axis) -> Gap:
        """This report's Gap on one Axis."""
        return next(gap for gap in self.gaps if gap.axis is axis)

    @property
    def mean_gap(self) -> float:
        """The mean Gap over all ten Axes."""
        return sum(gap.gap for gap in self.gaps) / len(self.gaps)

    @property
    def worst_gap(self) -> int:
        """The largest Gap in the report."""
        return max(gap.gap for gap in self.gaps)

    @property
    def worst(self) -> tuple[Gap, ...]:
        """Every Axis at the worst Gap. A tie is reported, never broken."""
        return tuple(gap for gap in self.gaps if gap.gap == self.worst_gap)


def gap_report(party: Party, platform: Platform) -> GapReport:
    """What one Party gives up on each Axis to accept this Platform (§5.4).

    Feedback, never a constraint. It exists because an Agent asked abstractly to hold its
    ground drifts, and the same Agent shown the number it is abandoning on its signature Axis
    behaves differently — which is the only defence this design has against every Run ending
    in a mushy grand coalition.
    """
    return GapReport(
        party=party.name,
        gaps=tuple(
            Gap(axis=axis, position=party.positions.on(axis), platform=platform.on(axis))
            for axis in Axis
        ),
    )


def render_gap_report(report: GapReport) -> str:
    """A Party's own Gaps, with the ones above its mean marked (§5.4).

    Marking above the mean rather than at some fixed size is what names *this* Party's worst
    betrayals: a Party that conceded evenly everywhere has no standouts to flag, and one that
    held nine Axes and surrendered the tenth sees exactly that one marked.

    Gaps are whole numbers shown to one decimal, because the mean beside them is not, and a
    column mixing `4` with `2.1` reads as two different quantities.
    """
    width = max(len(axis.value) for axis in Axis)
    lines = [
        f"{report.party}: its Positions against this Platform.",
        "",
        f"  {'axis':<{width}}  you  platform   gap",
    ]
    for gap in report.gaps:
        mark = "  <<" if gap.gap > report.mean_gap else ""
        lines.append(
            f"  {gap.axis.value:<{width}}  {signed(gap.position):>3}  "
            f"{signed(gap.platform):>8}  {gap.gap:>4.1f}{mark}"
        )
    lines.append("")
    lines.append(f"  mean Gap: {report.mean_gap:.1f}   worst Gap: {_worst(report)}")
    return "\n".join(lines)


def _worst(report: GapReport) -> str:
    """The Axes at the worst Gap — or the honest answer when there is no betrayal to name.

    Without this a Party handed its own Positions back is told its worst Gap is all ten Axes,
    which reads as a complaint about a Platform it wrote itself.
    """
    if not report.worst_gap:
        return "none — this Platform is your Positions"
    named = ", ".join(gap.axis.value for gap in report.worst)
    return f"{named} ({report.worst_gap:.1f})"


def render_proposal(scenario: Scenario, proposal: Proposal) -> str:
    """What is on the table, and the seat arithmetic behind it.

    One rendering, shown to every Party before it votes and printed in the Transcript
    afterwards — a chamber reading one Proposal and a reader reading another would make the
    Transcript evidence of nothing.

    **No ministries.** There is no portfolio column here because there is no portfolio
    anywhere: modelling who gets which department needs a ministry list *and* a per-Party
    valuation of each post, which is a second preference model this project does not have
    (§4).

    The Base's seats are stated because they are arithmetic and arithmetic is the Referee's
    (§2). They are not a prediction: the Parties named have agreed to nothing, and one of them
    voting No is a thing this Proposal cannot stop.
    """
    width = max(len(axis.value) for axis in Axis)
    lines = [f"{proposal.formateur}'s Proposal.", "", "  Platform:"]
    lines.extend(
        f"    {axis.value:<{width}}  {signed(proposal.platform.on(axis)):>3}" for axis in Axis
    )

    base = sum(scenario.party(name).seats for name in proposal.base)
    lines.extend(
        [
            "",
            f"  Government:    {', '.join(proposal.government)}",
            f"  Support-only:  {', '.join(proposal.support_only) or 'nobody'}",
            "",
            f"  {base} seats are behind it, in cabinet or outside it. It takes "
            f"{BLOCKING_MINORITY} voting No to defeat it.",
        ]
    )

    if proposal.commitments:
        lines.append("")
        lines.append("  It also commits the government to:")
        lines.extend(f"    - {commitment}" for commitment in proposal.commitments)
    return "\n".join(lines)


class Price(StrEnum):
    """Which of a Party's two price lists a Platform is being checked against.

    Two lists, never one (§3): a Party asked what a Platform buys has two answers, and
    collapsing them loses the Formateur its cheapest route to power.
    """

    GOVERNING = "Governing price"
    SUPPORTING = "Supporting price"


class Satisfaction(StrEnum):
    """What the Referee can say about one Demand against one Platform."""

    MET = "met"
    UNMET = "unmet"
    UNEVALUATED = "unevaluated"
    """A free-text Demand. Not unknown for want of trying — it is not the Referee's to read
    (§2), and a guess here would be the Referee inventing a fact for an Agent to act on."""


class DemandCheck(NamedTuple):
    """One Demand, and what the Referee can say about it."""

    demand: Demand
    satisfaction: Satisfaction


class PriceReport(NamedTuple):
    """One Party's price list, checked Demand by Demand against one Platform."""

    party: str
    price: Price
    checks: tuple[DemandCheck, ...]

    @property
    def met(self) -> tuple[DemandCheck, ...]:
        return self._with(Satisfaction.MET)

    @property
    def unmet(self) -> tuple[DemandCheck, ...]:
        return self._with(Satisfaction.UNMET)

    @property
    def unevaluated(self) -> tuple[DemandCheck, ...]:
        return self._with(Satisfaction.UNEVALUATED)

    def _with(self, satisfaction: Satisfaction) -> tuple[DemandCheck, ...]:
        return tuple(check for check in self.checks if check.satisfaction is satisfaction)


def price_report(party: Party, platform: Platform, price: Price) -> PriceReport:
    """Which of a Party's Demands this Platform pays, on one of its two price lists.

    A report, not a verdict: a Party is free to waive a Demand it named and free to walk away
    over one the Referee has just called met.
    """
    demands = party.to_govern if price is Price.GOVERNING else party.to_support
    return PriceReport(
        party=party.name,
        price=price,
        checks=tuple(
            DemandCheck(demand=demand, satisfaction=_satisfaction(demand, platform))
            for demand in demands
        ),
    )


def _satisfaction(demand: Demand, platform: Platform) -> Satisfaction:
    if isinstance(demand, TextDemand):
        return Satisfaction.UNEVALUATED
    return Satisfaction.MET if _holds(demand, platform) else Satisfaction.UNMET


def _holds(demand: AxisDemand, platform: Platform) -> bool:
    offered = platform.on(demand.axis)
    if demand.op == ">=":
        return offered >= demand.value
    if demand.op == "<=":
        return offered <= demand.value
    return offered == demand.value


def render_price_report(report: PriceReport) -> str:
    """What this Platform pays of one price list, and what it leaves outstanding."""
    lines = [f"{report.party}, {report.price.value}, against this Platform:", ""]
    if not report.checks:
        lines.append("  It named no price. That does not mean this Platform is free to it.")
        return "\n".join(lines)

    width = max(len(check.satisfaction.value) for check in report.checks)
    for check in report.checks:
        lines.append(f"  {check.satisfaction.value:<{width}}  {_demand(check.demand)}")
    lines.append("")
    lines.append(f"  {_counted(report)}")
    return "\n".join(lines)


def _counted(report: PriceReport) -> str:
    """The one-line summary under a price list, saying only what the Referee can say."""
    checkable = len(report.met) + len(report.unmet)
    sentences = []
    if checkable:
        sentences.append(f"{len(report.met)} of {checkable} Axis Demands met.")
    free_text = len(report.unevaluated)
    if free_text:
        plural = "Demand is" if free_text == 1 else "Demands are"
        sentences.append(
            f"{free_text} free-text {plural} not the Referee's to read: judge those yourself."
        )
    return " ".join(sentences)


def _demand(demand: Demand) -> str:
    if isinstance(demand, TextDemand):
        return demand.text
    return f"{demand.axis.value} {demand.op} {signed(demand.value)}"


class Cast(NamedTuple):
    """One Party's Ballot, and the seats it carries."""

    party: str
    seats: int
    ballot: Ballot


class Vote(NamedTuple):
    """The chamber's verdict on one Proposal, under Negative parliamentarism."""

    proposal: Proposal
    casts: tuple[Cast, ...]
    base_seats: int
    """The seats in the Proposal's Base — Government and Support-only together (§4). Reported
    beside the count rather than used in it: what defeats a Proposal is the No seats, and a
    Party named in a Proposal is still free to cast a No Ballot on it."""

    def seats_casting(self, ballot: Ballot) -> int:
        """The seats cast one way. Named for the question because `seats` is a number
        everywhere else in the Referee, and a `Vote.seats` taking an argument would not be."""
        return sum(cast.seats for cast in self.casts if cast.ballot is ballot)

    @property
    def yes(self) -> int:
        return self.seats_casting(Ballot.YES)

    @property
    def abstain(self) -> int:
        return self.seats_casting(Ballot.ABSTAIN)

    @property
    def no(self) -> int:
        return self.seats_casting(Ballot.NO)

    @property
    def passed(self) -> bool:
        """The whole of the vote rule: a Proposal passes unless a Blocking minority votes No.

        Nothing else can defeat it. A Proposal with 140 seats for it and 174 against passes;
        one with no seats for it at all passes if fewer than 175 turn up to say No.
        """
        return self.no < BLOCKING_MINORITY


def count_vote(scenario: Scenario, proposal: Proposal, ballots: Mapping[str, Ballot]) -> Vote:
    """Count one Vote — the Chamber's single decision on one Proposal (§5.2).

    Every Party casts a Ballot, because every Party holds seats and the count is over seats. A
    Party the Proposal never mentions still decides whether to abstain or block, which is the
    whole of the Formateur's cheapest route to power.
    """
    by_seats = {party.name: party.seats for party in scenario.parties}

    unknown = sorted(set(proposal.base) - set(by_seats))
    if unknown:
        raise ValueError(
            f"the Proposal names {', '.join(unknown)}, which is not a Party in "
            f"Scenario {scenario.name!r}"
        )

    missing = sorted(set(by_seats) - set(ballots))
    if missing:
        raise ValueError(f"no Ballot was cast by {', '.join(missing)}")
    strangers = sorted(set(ballots) - set(by_seats))
    if strangers:
        raise ValueError(
            f"{', '.join(strangers)} cast a Ballot, and holds no seat in "
            f"Scenario {scenario.name!r}"
        )

    return Vote(
        proposal=proposal,
        casts=tuple(
            Cast(party=name, seats=seats, ballot=ballots[name])
            for name, seats in by_seats.items()
        ),
        base_seats=sum(by_seats[name] for name in proposal.base),
    )


def render_vote(vote: Vote) -> str:
    """The count, and what it did to the Proposal."""
    proposal = vote.proposal
    width = max(len("Abstain"), *(len(cast.party) for cast in vote.casts))
    rule = f"{'-' * width}  -----  -------"
    lines = [
        f"Vote on {proposal.formateur}'s Proposal.",
        "",
        f"{'Party':<{width}}  Seats  Vote",
        rule,
    ]
    for cast in vote.casts:
        lines.append(f"{cast.party:<{width}}  {cast.seats:>5}  {cast.ballot.value}")
    lines.append(rule)
    for ballot in Ballot:
        lines.append(f"{ballot.value:<{width}}  {vote.seats_casting(ballot):>5}")

    support = ", ".join(proposal.support_only) or "nobody"
    outcome = "passes" if vote.passed else "is defeated"
    lines.extend(
        [
            "",
            f"Government: {', '.join(proposal.government)}. Support-only: {support}. "
            f"{vote.base_seats} seats behind it.",
            f"{vote.no} seats voted No, and it takes {BLOCKING_MINORITY} to defeat a "
            f"Proposal. It {outcome}.",
        ]
    )
    return "\n".join(lines)
