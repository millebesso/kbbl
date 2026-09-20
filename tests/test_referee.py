"""Seat arithmetic and the Blocking minority. Costs nothing to test, so it is tested hard."""

from __future__ import annotations

from collections import Counter
from itertools import product
from pathlib import Path

import pytest
from pydantic import ValidationError

from conftest import COMMITTED_SCENARIOS, mandate, platform, two_party, write_scenario
from kbbl.models import (
    TOTAL_SEATS,
    Axis,
    AxisDemand,
    ExclusionReport,
    Party,
    Platform,
    Proposal,
    Role,
    Scenario,
    TextDemand,
    Ballot,
)
from kbbl.referee import (
    BLOCKING_MINORITY,
    Price,
    Satisfaction,
    blocking_groupings,
    count_vote,
    exclusion_report,
    gap_report,
    price_report,
    render_blocking_groupings,
    render_exclusion_report,
    render_gap_report,
    render_price_report,
    render_proposal,
    render_seat_table,
    render_vote,
)
from kbbl.scenario import load_scenario


def test_the_blocking_minority_is_an_absolute_majority_of_349() -> None:
    assert BLOCKING_MINORITY == 175
    assert BLOCKING_MINORITY * 2 > 349


def test_the_fixtures_groupings_put_every_party_in_at_least_one(
    four_party: Scenario,
) -> None:
    """No Party in this Fixture is a null player — each one is pivotal somewhere."""
    groupings = blocking_groupings(four_party)

    assert [(g.parties, g.seats) for g in groupings] == [
        (("NP", "FF"), 272),
        (("NP", "GV"), 182),
        (("NP", "MI"), 175),
        (("FF", "GV", "MI"), 209),
    ]
    assert {name for g in groupings for name in g.parties} == {"NP", "FF", "GV", "MI"}


def test_only_minimal_groupings_are_reported(four_party: Scenario) -> None:
    """NP+MI+GV clears 175, but NP+MI already does — the third Party is not load-bearing."""
    groupings = blocking_groupings(four_party)

    assert ("NP", "MI", "GV") not in [g.parties for g in groupings]
    for grouping in groupings:
        for name in grouping.parties:
            assert grouping.seats - four_party.party(name).seats < BLOCKING_MINORITY


def test_a_party_above_the_blocking_minority_is_a_grouping_of_one(tmp_path: Path) -> None:
    write_scenario(tmp_path, mandate("AA", 200), mandate("BB", 100), mandate("CC", 49))

    groupings = blocking_groupings(load_scenario(tmp_path))

    assert [g.parties for g in groupings] == [("AA",)]


def test_a_chamber_can_have_no_grouping_short_of_a_pair(tmp_path: Path) -> None:
    """Three near-equal thirds: every pair clears 175, so no single Party does."""
    write_scenario(tmp_path, mandate("AA", 117), mandate("BB", 116), mandate("CC", 116))

    assert [g.parties for g in blocking_groupings(load_scenario(tmp_path))] == [
        ("AA", "BB"),
        ("AA", "CC"),
        ("BB", "CC"),
    ]


def test_the_seat_table_lists_every_party_largest_first(four_party: Scenario) -> None:
    table = render_seat_table(four_party)

    names = [line.split()[0] for line in table.splitlines()]
    assert names == ["Party", "-----", "NP", "FF", "GV", "MI", "-----", "Total"]
    assert table.splitlines()[-1].split() == ["Total", "349", "100.0%"]


def test_the_grouping_report_names_the_blocking_minority(four_party: Scenario) -> None:
    report = render_blocking_groupings(four_party)

    assert "Blocking minority: 175 of 349 seats." in report
    assert "NP + MI" in report


def test_a_gap_is_measured_between_a_position_and_the_platform(
    four_party: Scenario,
) -> None:
    """GV stands at environment +5 and transport +5; a Platform at +1 and +5 betrays one."""
    report = gap_report(four_party.party("GV"), platform(environment=1, transport=5))

    assert report.on(Axis.ENVIRONMENT).gap == 4
    assert report.on(Axis.TRANSPORT).gap == 0


def test_a_gap_has_no_direction(four_party: Scenario) -> None:
    """Three points to the left of a Party is the same betrayal as three to the right."""
    mi = four_party.party("MI")
    assert mi.positions.on(Axis.TRANSPORT) == 0

    left = gap_report(mi, platform(transport=-3))
    right = gap_report(mi, platform(transport=3))

    assert left.on(Axis.TRANSPORT).gap == right.on(Axis.TRANSPORT).gap == 3


def test_the_mean_gap_is_taken_over_all_ten_axes(four_party: Scenario) -> None:
    report = gap_report(four_party.party("MI"), platform())

    assert [gap.gap for gap in report.gaps] == [2, 2, 1, 0, 1, 1, 1, 0, 2, 4]
    assert report.mean_gap == 1.4


def test_the_worst_gap_names_every_axis_that_reaches_it(four_party: Scenario) -> None:
    """A Party betrayed equally on two Axes is told about both — the tie is not broken."""
    gv = four_party.party("GV")
    conceded = gv.positions.model_dump() | {"environment": 0, "immigration": -1}

    report = gap_report(gv, Platform(**conceded))

    assert report.worst_gap == 5
    assert [gap.axis for gap in report.worst] == [Axis.ENVIRONMENT, Axis.IMMIGRATION]


def test_the_gap_report_marks_the_axes_a_party_is_furthest_from(four_party: Scenario) -> None:
    """§5.4: the report's job is to name the betrayals, not to total them up."""
    gv = four_party.party("GV")
    conceded = gv.positions.model_dump() | {"environment": 0, "transport": 0}

    report = render_gap_report(gap_report(gv, Platform(**conceded)))

    marked = {line.split()[0] for line in report.splitlines() if line.endswith("<<")}
    assert marked == {"environment", "transport"}
    assert "worst Gap: environment, transport (5.0)" in report
    assert "mean Gap: 1.0" in report


def test_the_gap_report_shows_every_axis_and_both_numbers(four_party: Scenario) -> None:
    report = render_gap_report(gap_report(four_party.party("NP"), platform(economic=1)))

    assert all(axis.value in report for axis in Axis)
    assert "  economic        +5        +1   4.0  <<" in report
    assert "  international   +1         0   1.0" in report


def test_a_party_that_concedes_evenly_has_no_standout_betrayal(four_party: Scenario) -> None:
    """Every Axis at the mean, so nothing is marked — and the report says so by saying nothing."""
    report = render_gap_report(gap_report(four_party.party("MI"), platform(**{
        axis: value - 2 for axis, value in four_party.party("MI").positions.model_dump().items()
    })))

    assert "<<" not in report
    assert "mean Gap: 2.0" in report


def test_an_axis_demand_is_checked_against_the_platform(four_party: Scenario) -> None:
    """FF charges economic <= -2 and health <= -3 to govern. One is paid, one is not."""
    report = price_report(four_party.party("FF"), platform(economic=-2), Price.GOVERNING)

    assert [check.satisfaction for check in report.checks] == [
        Satisfaction.MET,
        Satisfaction.UNMET,
        Satisfaction.UNEVALUATED,
    ]


def test_every_comparison_is_honoured(tmp_path: Path) -> None:
    demands = [
        {"axis": "economic", "op": ">=", "value": 2},
        {"axis": "environment", "op": "<=", "value": -2},
        {"axis": "military", "op": "==", "value": 0},
    ]
    write_scenario(tmp_path, mandate("AA", 200, to_govern=demands), mandate("BB", 149))
    aa = load_scenario(tmp_path).party("AA")

    exact = price_report(aa, platform(economic=2, environment=-2, military=0), Price.GOVERNING)
    over = price_report(aa, platform(economic=5, environment=-5, military=1), Price.GOVERNING)

    assert [check.satisfaction for check in exact.checks] == [Satisfaction.MET] * 3
    assert [check.satisfaction for check in over.checks] == [
        Satisfaction.MET,
        Satisfaction.MET,
        Satisfaction.UNMET,
    ]


def test_the_two_price_lists_are_reported_separately(four_party: Scenario) -> None:
    """The point of two lists: this Platform buys FF's support and not its cabinet."""
    ff = four_party.party("FF")
    offered = platform(economic=0)

    assert price_report(ff, offered, Price.SUPPORTING).unmet == ()
    assert len(price_report(ff, offered, Price.GOVERNING).unmet) == 2


def test_a_free_text_demand_is_reported_unevaluated_never_guessed_at(
    four_party: Scenario,
) -> None:
    """The Referee does not read prose (§2) — it says so and leaves the Demand to the Agents."""
    gv = four_party.party("GV")

    report = price_report(gv, platform(environment=5, transport=5), Price.GOVERNING)

    assert report.unmet == ()
    assert [check.demand for check in report.unevaluated] == [
        TextDemand(text="no new motorway starts this term")
    ]


def test_the_price_report_names_the_list_and_the_state_of_every_demand(
    four_party: Scenario,
) -> None:
    rendered = render_price_report(
        price_report(four_party.party("GV"), platform(environment=2), Price.GOVERNING)
    )

    assert "Governing price" in rendered
    assert "environment" in rendered and "transport" in rendered
    assert "no new motorway starts this term" in rendered
    assert "unevaluated" in rendered


def test_a_party_that_names_no_price_still_gets_a_report(tmp_path: Path) -> None:
    """Naming no price does not mean the Platform is free, and an empty table would imply it."""
    two_party(tmp_path)

    rendered = render_price_report(
        price_report(load_scenario(tmp_path).party("AA"), platform(), Price.SUPPORTING)
    )

    assert "no price" in rendered


def proposed(*government: str, support_only: tuple[str, ...] = ()) -> Proposal:
    """A Proposal from the first-named Party, on a Platform nobody is being asked about."""
    return Proposal(
        formateur=government[0],
        platform=platform(),
        government=government,
        support_only=support_only,
    )


def test_the_proposal_report_shows_the_platform_the_roles_and_the_arithmetic(
    four_party: Scenario,
) -> None:
    """One rendering, shown to every Party before it votes and printed afterwards."""
    rendered = render_proposal(
        four_party,
        Proposal(
            formateur="NP",
            platform=platform(economic=3, environment=-2),
            government=("NP", "MI"),
            support_only=("GV",),
            commitments=("a binding cap on public spending growth",),
        ),
    )

    assert "NP's Proposal." in rendered
    assert "economic        +3" in rendered
    assert "environment     -2" in rendered
    assert "military         0" in rendered
    assert "Government:    NP, MI" in rendered
    assert "Support-only:  GV" in rendered
    assert "217 seats are behind it" in rendered
    assert f"{BLOCKING_MINORITY} voting No" in rendered
    assert "a binding cap on public spending growth" in rendered


def test_a_proposal_with_nobody_outside_cabinet_says_so_rather_than_showing_a_blank(
    four_party: Scenario,
) -> None:
    rendered = render_proposal(four_party, proposed("NP"))

    assert "Support-only:  nobody" in rendered
    assert "commits the government to" not in rendered


def test_no_ministry_or_portfolio_is_reported_because_none_is_modelled(
    four_party: Scenario,
) -> None:
    """§4: modelling portfolios needs a ministry list and a per-Party valuation of each
    post, which is a second preference model this project does not have."""
    rendered = render_proposal(four_party, proposed("NP", support_only=("MI",)))

    for word in ("ministr", "portfolio", "department"):
        assert word not in rendered.lower()


def test_a_proposal_passes_unless_the_blocking_minority_votes_no(
    four_party: Scenario,
) -> None:
    """NP governs alone on 140. The other three hold 209 — enough, but only together."""
    against = count_vote(
        four_party,
        proposed("NP"),
        {"NP": Ballot.YES, "FF": Ballot.NO, "GV": Ballot.NO, "MI": Ballot.NO},
    )
    abstained = count_vote(
        four_party,
        proposed("NP"),
        {"NP": Ballot.YES, "FF": Ballot.NO, "GV": Ballot.NO, "MI": Ballot.ABSTAIN},
    )

    assert against.no == 209 and not against.passed
    assert abstained.no == 174 and abstained.passed


def test_an_abstention_is_worth_exactly_its_seats(four_party: Scenario) -> None:
    """MI's 35 seats are the single seat of margin the Fixture is built around."""
    vote = count_vote(
        four_party,
        proposed("FF", support_only=("GV",)),
        {"FF": Ballot.YES, "GV": Ballot.YES, "NP": Ballot.NO, "MI": Ballot.NO},
    )

    assert vote.no == BLOCKING_MINORITY
    assert not vote.passed


def test_support_only_seats_count_exactly_as_government_seats_do(
    four_party: Scenario,
) -> None:
    """§4: without this, the Government/Support-only distinction is decorative."""
    ballots = {"FF": Ballot.YES, "GV": Ballot.YES, "NP": Ballot.NO, "MI": Ballot.ABSTAIN}

    in_cabinet = count_vote(four_party, proposed("FF", "GV"), ballots)
    outside = count_vote(four_party, proposed("FF", support_only=("GV",)), ballots)

    assert in_cabinet.base_seats == outside.base_seats == 174
    assert in_cabinet.no == outside.no == 140
    assert in_cabinet.passed and outside.passed


def test_the_referee_counts_a_proposal_its_own_base_voted_down(
    four_party: Scenario,
) -> None:
    """§2: the Referee never constrains an Agent. A Party may vote against a Proposal it is
    named in, and the Referee reports what happened rather than correcting it."""
    vote = count_vote(
        four_party,
        proposed("NP", support_only=("FF",)),
        {"NP": Ballot.YES, "FF": Ballot.NO, "GV": Ballot.NO, "MI": Ballot.NO},
    )

    assert vote.base_seats == 272
    assert vote.no == 209 and not vote.passed


def test_every_party_in_the_chamber_must_cast_exactly_one_vote(
    four_party: Scenario,
) -> None:
    with pytest.raises(ValueError, match="MI"):
        count_vote(four_party, proposed("NP"), {"NP": Ballot.YES, "FF": Ballot.NO, "GV": Ballot.NO})

    with pytest.raises(ValueError, match="ZZ"):
        count_vote(
            four_party,
            proposed("NP"),
            {"NP": Ballot.YES, "FF": Ballot.NO, "GV": Ballot.NO, "MI": Ballot.NO, "ZZ": Ballot.NO},
        )


def test_a_proposal_may_only_name_parties_in_the_chamber(four_party: Scenario) -> None:
    with pytest.raises(ValueError, match="ZZ"):
        count_vote(
            four_party,
            proposed("NP", support_only=("ZZ",)),
            {"NP": Ballot.YES, "FF": Ballot.NO, "GV": Ballot.NO, "MI": Ballot.NO},
        )


def test_the_vote_report_gives_the_count_and_the_outcome(four_party: Scenario) -> None:
    rendered = render_vote(
        count_vote(
            four_party,
            proposed("NP", support_only=("MI",)),
            {"NP": Ballot.YES, "MI": Ballot.YES, "FF": Ballot.NO, "GV": Ballot.ABSTAIN},
        )
    )

    assert "175" in rendered
    assert "132" in rendered
    assert "passes" in rendered


@pytest.mark.parametrize("directory", COMMITTED_SCENARIOS, ids=lambda path: path.name)
def test_every_committed_scenario_seats_the_whole_chamber(directory: Path) -> None:
    """§8's first invariant, over every Scenario in the repo rather than the ones remembered."""
    assert load_scenario(directory).seats == TOTAL_SEATS


@pytest.mark.parametrize("directory", COMMITTED_SCENARIOS, ids=lambda path: path.name)
def test_a_proposal_never_passes_with_the_blocking_minority_against_it(
    directory: Path,
) -> None:
    """Exhaustive over every way the chamber could vote — it costs nothing, so it is."""
    scenario = load_scenario(directory)
    names = [party.name for party in scenario.parties]
    outcomes = Counter[bool]()

    for ballots in product(Ballot, repeat=len(names)):
        vote = count_vote(scenario, proposed(names[0]), dict(zip(names, ballots, strict=True)))
        assert not (vote.passed and vote.no >= BLOCKING_MINORITY)
        outcomes[vote.passed] += 1

    assert outcomes[True] and outcomes[False], "this Fixture never exercised both outcomes"


def test_a_party_listed_support_only_never_appears_in_government() -> None:
    """§8's third invariant. Support-only is backing from outside cabinet; both is nonsense."""
    with pytest.raises(ValidationError, match="both Government and Support-only"):
        Proposal(
            formateur="NP",
            platform=platform(),
            government=("NP", "MI"),
            support_only=("MI",),
        )


def test_a_proposal_never_names_the_same_party_twice() -> None:
    """Otherwise its seats would be counted twice over in what stands behind it."""
    with pytest.raises(ValidationError, match="same Party twice"):
        Proposal(formateur="NP", platform=platform(), government=("NP", "NP"))


def test_nothing_the_chamber_does_defeats_a_landslide(landslide: Scenario) -> None:
    """MJ holds 200. The other two hold 149 between them and cannot reach 175 however
    they vote, so the Fixture's right answer is obvious: MJ governs alone."""
    others = [party.name for party in landslide.parties if party.name != "MJ"]

    for ballots in product(Ballot, repeat=len(others)):
        vote = count_vote(
            landslide,
            proposed("MJ"),
            {"MJ": Ballot.YES} | dict(zip(others, ballots, strict=True)),
        )
        assert vote.passed

    assert [grouping.parties for grouping in blocking_groupings(landslide)] == [("MJ",)]


@pytest.mark.parametrize(
    ("governs", "blocks"), [("LB", "RB"), ("RB", "LB")]
)
def test_the_kingmaker_alone_decides_who_governs(
    knife_edge: Scenario, governs: str, blocks: str
) -> None:
    """§9's arithmetic in miniature: a minority government lives if KM steps out of the way,
    and dies if KM joins the opposition. Neither bloc can do anything about it."""
    outcomes = {
        vote: count_vote(
            knife_edge,
            proposed(governs),
            {governs: Ballot.YES, blocks: Ballot.NO, "KM": vote},
        ).passed
        for vote in Ballot
    }

    assert outcomes == {Ballot.YES: True, Ballot.ABSTAIN: True, Ballot.NO: False}


def test_no_platform_pays_two_parties_in_the_deadlock_fixture(deadlock: Scenario) -> None:
    """The Fixture is forced: the three Supporting prices contradict each other pairwise, so
    there is no Platform any two of them would both back."""
    prices = [
        price_report(party, platform(), Price.SUPPORTING) for party in deadlock.parties
    ]
    assert [len(price.checks) for price in prices] == [1, 1, 1]
    assert all(
        isinstance(check.demand, AxisDemand) and check.demand.axis is Axis.ECONOMIC
        for price in prices
        for check in price.checks
    ), "the Supporting prices name one Axis between them, which is what makes this exhaustive"

    for value in range(-5, 6):
        offered = platform(economic=value)
        paid = [
            party.name
            for party in deadlock.parties
            if not price_report(party, offered, Price.SUPPORTING).unmet
        ]
        assert len(paid) <= 1, f"economic {value:+d} pays {paid}"


def test_no_minority_government_survives_the_deadlock_fixture(deadlock: Scenario) -> None:
    """Every Party is short of 175, and the other two together always reach it."""
    for party in deadlock.parties:
        others = [other.name for other in deadlock.parties if other.name != party.name]
        vote = count_vote(
            deadlock,
            proposed(party.name),
            {party.name: Ballot.YES} | dict.fromkeys(others, Ballot.NO),
        )

        assert not vote.passed


def test_the_vote_reports_all_three_ways_the_chamber_voted(four_party: Scenario) -> None:
    """Only No defeats a Proposal, but the other two are what the Transcript is read for."""
    vote = count_vote(
        four_party,
        proposed("NP", support_only=("MI",)),
        {"NP": Ballot.YES, "MI": Ballot.YES, "FF": Ballot.NO, "GV": Ballot.ABSTAIN},
    )

    assert (vote.yes, vote.abstain, vote.no) == (175, 42, 132)
    assert vote.yes + vote.abstain + vote.no == TOTAL_SEATS


def test_the_casts_come_back_in_chamber_order(four_party: Scenario) -> None:
    """Largest Party first, as the seat table shows them — one order, read twice."""
    vote = count_vote(
        four_party,
        proposed("NP"),
        dict.fromkeys(["NP", "FF", "GV", "MI"], Ballot.ABSTAIN),
    )

    assert [cast.party for cast in vote.casts] == ["NP", "FF", "GV", "MI"]
    assert [cast.seats for cast in vote.casts] == [140, 132, 42, 35]


def test_a_party_handed_its_own_positions_back_is_told_it_gave_up_nothing(
    four_party: Scenario,
) -> None:
    """Naming all ten Axes as the worst Gap would read as a complaint about its own Platform."""
    gv = four_party.party("GV")

    rendered = render_gap_report(gap_report(gv, Platform(**gv.positions.model_dump())))

    assert "worst Gap: none" in rendered
    assert "environment" not in rendered.splitlines()[-1]
    assert "mean Gap: 0.0" in rendered


def test_the_price_report_counts_free_text_demands_without_judging_them(
    four_party: Scenario,
) -> None:
    ff = four_party.party("FF")

    paid = render_price_report(price_report(ff, platform(economic=-4, health=-4), Price.GOVERNING))

    assert "2 of 2 Axis Demands met." in paid
    assert "1 free-text Demand is not the Referee's to read" in paid


def test_neither_bloc_in_the_2026_riksdag_reaches_the_blocking_minority(
    riksdag_2026: Scenario,
) -> None:
    """The whole reason §9 is worth simulating, computed rather than asserted in prose.

    The right bloc is two seats short of blocking a left minority government, so a left
    government of 151 survives if C abstains. Both blocs being short of 175 is the same fact
    twice: no minimal Grouping is drawn from one bloc alone, because neither bloc has the
    seats. What the arithmetic does *not* say is that C is the only Party that can complete
    one — `M + SD + KD + MP` reaches 176 without it. A Grouping is Parties the Referee has
    added up, never Parties that have agreed to anything.
    """
    seats = {party.name: party.seats for party in riksdag_2026.parties}
    left, right = {"S", "V", "MP"}, {"M", "SD", "KD", "L"}

    assert sum(seats[name] for name in left) == 151
    assert sum(seats[name] for name in right) == 173
    assert seats["C"] == 25
    assert BLOCKING_MINORITY - sum(seats[name] for name in right) == 2

    reaching = [grouping.parties for grouping in blocking_groupings(riksdag_2026)]
    assert ("M", "SD", "KD", "L") not in reaching, "the right bloc alone must not reach 175"
    assert not [
        named for named in reaching if set(named) <= left or set(named) <= right
    ], "no minimal Grouping is drawn from one bloc alone"
    assert ("M", "SD", "KD", "MP") in reaching, "C is not the only Party that completes one"


def test_the_exclusion_report_says_where_the_proposal_puts_each_one(
    four_party: Scenario,
) -> None:
    """§5.4's argument, applied to the coalition rather than to the Platform: the Party is
    shown who is in the government it is about to wave through, not asked to remember."""
    report = exclusion_report(four_party.party("GV"), proposed("NP", support_only=("MI",)))

    assert report is not None
    assert report.party == "GV"
    assert [(placed.party, placed.role) for placed in report.placements] == [
        ("NP", Role.GOVERNMENT)
    ]


def reported(party: Party, proposal: Proposal) -> ExclusionReport:
    """The Exclusion report of a Party that has one. `exclusion_report` answers None for a
    Party that named nobody, and a test about the rendering is not a test about that."""
    report = exclusion_report(party, proposal)
    assert report is not None, f"{party.name} names somebody, so it has a report"
    return report


def test_the_exclusion_report_tells_the_three_roles_apart(four_party: Scenario) -> None:
    """Not being named is a role, not the absence of one: a Party the Proposal ignores is
    still one whose seats are not behind it (§5.2)."""
    governs = reported(four_party.party("GV"), proposed("NP", support_only=("MI",)))
    supports = reported(four_party.party("NP"), proposed("FF", support_only=("GV",)))
    ignored = reported(four_party.party("FF"), proposed("GV", support_only=("MI",)))

    assert governs.placements[0].role is Role.GOVERNMENT
    assert supports.placements[0].role is Role.SUPPORT_ONLY
    assert ignored.placements[0].role is Role.UNNAMED
    assert [placed.party for placed in governs.in_the_base] == ["NP"]
    assert [placed.party for placed in supports.in_the_base] == ["GV"]
    assert [placed.party for placed in ignored.in_the_base] == []


def test_a_party_that_would_deal_with_anybody_is_shown_nothing(four_party: Scenario) -> None:
    """MI names nobody, so there is no report — the way the Persona omits its section
    rather than saying "none"."""
    assert four_party.party("MI").prefer_not == ()

    assert exclusion_report(four_party.party("MI"), proposed("NP")) is None


def test_the_exclusion_report_names_who_is_in_the_base(four_party: Scenario) -> None:
    rendered = render_exclusion_report(
        reported(four_party.party("GV"), proposed("NP", support_only=("MI",)))
    )

    assert "GV: the Parties it would rather not deal with" in rendered
    assert "  NP  in the Government" in rendered
    assert "NP is in the Base" in rendered


def test_an_exclusion_the_proposal_leaves_out_is_reported_as_left_out(
    four_party: Scenario,
) -> None:
    """The report is feedback and never a constraint (§2), so the honest answer when a
    Proposal is built on nobody this Party objects to is that it is built on nobody."""
    rendered = render_exclusion_report(
        reported(four_party.party("FF"), proposed("GV", support_only=("MI",)))
    )

    assert "  NP  not named" in rendered
    assert "None of them is in the Base" in rendered


def test_a_partys_role_and_the_base_are_the_same_answer(four_party: Scenario) -> None:
    """`Proposal.base` and `Proposal.role_of` say who is behind a Proposal in two ways, and
    `ExclusionReport.in_the_base` trusts that they agree. This is what says they do."""
    proposal = proposed("NP", support_only=("MI",))

    named = {name for name in proposal.base}
    by_role = {
        party.name
        for party in four_party.parties
        if proposal.role_of(party.name) is not Role.UNNAMED
    }

    assert named == by_role == {"NP", "MI"}
    report = reported(four_party.party("FF"), proposal)
    assert all(placed.party in named for placed in report.in_the_base)
