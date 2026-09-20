# Scenarios

A Scenario is a directory of Party Mandates whose seats sum to 349 (`docs/kbbl.md` §9). A
Fixture **is** a Scenario — same shape, same loader, same validation — so everything in
`fixtures/` loads through the path these do. Only the directory and the intent differ: what is
here is meant to be a reading of a real parliament, and what is there is invented to make a
negotiation legible.

## ⚠️ What is fact here, and what is not

**The seats are fact.** They are the allocation of the 349 Riksdag seats after the election of
13 September 2026 and they are checkable against the source below.

**Everything else is the author's editorial judgement.** The ten Axis Positions, both price
lists, the Exclusions and the Willingness to re-elect are one person's reading of where these
parties stand, expressed on a scale invented by this repo. They are not sourced, not
peer-reviewed, and not the parties' own words. No party has been consulted.

**A Run is not an authority on Swedish politics.** It is eight language models negotiating from
a set of numbers somebody made up, refereed by code that is certain only about arithmetic. A
Transcript that reads persuasively is a Transcript that reads persuasively; it is not evidence
about what any real party would do, and the fact that the model recognises these names does not
make its output reporting. Read it as fiction constrained by real seat arithmetic (§12.4).

## `riksdag-2026/` — the real parliament

Election of 13 September 2026, turnout 84.89%.

| Party | Seats | Vote share | Name                       |
| ----- | ----: | ---------: | -------------------------- |
| S     |    99 |     28.02% | Socialdemokraterna         |
| M     |    70 |     19.85% | Moderaterna                |
| SD    |    62 |     17.48% | Sverigedemokraterna        |
| V     |    30 |      8.40% | Vänsterpartiet             |
| C     |    25 |      7.03% | Centerpartiet              |
| KD    |    22 |      6.17% | Kristdemokraterna          |
| MP    |    22 |      6.12% | Miljöpartiet de gröna      |
| L     |    19 |      5.34% | Liberalerna                |

Parties are named by their abbreviation rather than in full because a Grouping label is built
by joining names: `S + M + SD` is 38 columns at the widest and
`Socialdemokraterna (S) + Moderaterna (M) + …` is 151, against a Transcript width of 88. The
full names are in the table above, which is the only place they are needed.

The Referee invariants in `tests/test_referee.py` are run over every Scenario in the repo —
both this directory and `fixtures/` — found rather than listed, so a Scenario added here is
covered by them the moment it lands (§8).

**Source:** [Valmyndigheten](https://www.val.se/english/election-results/elections-to-the-riksdag-and-regional-and-municipal-councils/election-results-2026),
cross-checked against [Riksdagsvalet i Sverige 2026](https://sv.wikipedia.org/wiki/Riksdagsvalet_i_Sverige_2026).
The English results page marked these **final on 19 September 2026**; the press release of
**17 September still called them preliminary**, so a levelling-seat adjustment is not
impossible (§12.5). If the allocation is revised, the blast radius is wider than these eight
files: §9's table, the arithmetic quoted below, the tests that pin it, and every Cassette
recorded against the old seats — which are re-keyed by the change and have to be re-recorded
rather than patched.

### Why this parliament

Neither bloc reached 175:

```
Left    S 99 + V 30 + MP 22            = 151
Right   M 70 + SD 62 + KD 22 + L 19    = 173
C                                      =  25   <- holds the balance
```

The seats in that sum are fact. **Which Party belongs to which bloc is not** — it is the
conventional Swedish reading, and placing C outside both is the whole of what makes it the
kingmaker. Nothing in the data encodes a bloc: the Referee knows only seats, and it adds up
any set of Parties you like without asking whether they would sit together.

Under Negative parliamentarism a left minority government of 151 **survives if C abstains** —
the entire right bloc is two seats short of the 175 needed to block it. Under the positive rule
the original brief specified, that government is impossible. Centerpartiet's Abstention alone
decides who governs.

You do not have to take that on trust, and it is not asserted anywhere in the data. Run
`uv run kbbl run scenarios/riksdag-2026` and read the Referee's own list of minimal Groupings:
**`M + SD + KD + L` does not appear in it**, because 173 does not reach 175. The entire right
bloc cannot block a left minority government.

What the list does show is that **no minimal Grouping is drawn from one bloc alone** — neither
151 nor 173 reaches 175, so every way of blocking anything needs somebody from the other side
of the chamber. Four Groupings clear the line by a single seat, and `M + SD + C + L` at 176 is
one of them.

Note what the arithmetic does *not* say: `M + SD + KD + MP` is also 176, so C is not the only
Party that can complete a blocking Grouping. A Grouping is Parties the Referee has added up,
never Parties that have agreed to anything (`CONTEXT.md`), and the reason C rather than MP is
the one to watch is political judgement, not arithmetic. §9's claim is the narrower one above:
the right bloc is two seats short.

### Who tries first

Largest-first makes the Formateur order **S → M → SD → V**, and then C, KD, MP, L.

The Chamber holds four Votes, but that is not a cap of four Attempts: Standing down ends an
Attempt and spends no Vote (§5.3), so in an eight-Party chamber every Party can have a turn
before the Votes run out. A Re-election is reached either way — four failed Votes, or every
Party having tried.

**This is a known divergence from reality.** In the real Riksdag the Speaker nominates and has
discretion over who is asked to try; largest-first is a simplification, and this is the
parliament where it shows (§5.3, §12.2). A hung chamber is exactly where a Speaker's judgement
would matter most, so where KBBL's order and the Speaker's differ, KBBL is wrong about the
procedure rather than the arithmetic.

v1 runs one Attempt and stops (§10). The handoff, the four-Vote counter and Re-election are
`riksdag-2026/02`.

### The recorded Run

`cassettes/riksdag-2026/` holds one live Attempt — 36 requests, about $0.50 — so
`uv run kbbl run scenarios/riksdag-2026 --replay` reproduces it for nothing.

In it **a left minority government formed on Abstentions**, which is §9's prediction reached
by §5.2's mechanism: S and V in cabinet, MP, C and KD named as Support-only, 151 Yes against
132 No, and C, KD and L standing aside. S never met M or SD.

Read it for what the prices did rather than for who won. Two of the three Parties named
Support-only abstained rather than backing it — a Proposal assigns the role and nobody accepts
it — and L abstained with its own price unmet, on nothing but its Willingness to re-elect of 1.

**A caveat on the calibration.** The Supporting prices of C, KD and L are single Axis Demands
that a left Platform pays almost by accident, so the cheapest route to power is cheaper here
than it should be. KD standing aside for an S+V government because `law_and_order >= +2` is
met is mechanically correct and politically absurd, and it is this file's fault rather than
the Agents'. One Run is not evidence (§12.3); this one is a demonstration that the machine
runs, not a forecast.

### The Positions, and why they are what they are

Editorial, as above. The shape they are built to have:

- **No Platform pays everyone.** SD sits at `international −4` and L at `+5`; L charges
  `international >= +3` to govern. The right bloc's arithmetic works and its price lists fight
  each other, which is the real difficulty of that bloc rather than an artefact.
- **C is pivotal and not cheap.** The Axis half of its Supporting price is `environment >= +1`,
  which a left Platform pays easily — but its own `economic +2` against a left Platform near
  `−3` is a Gap of five on the Axis it would have to defend, and the free-text half below is
  the term that decides which bloc it can deal with at all. Being purchasable is not the same as being willing,
  and its Willingness to re-elect of 3 is what makes the Abstention worth asking for.
- **Free-text Demands carry what no Axis can.** C charges *"SD has no influence over government
  policy"* on both lists, which is the one term that decides which bloc it can deal with and
  which the Referee reports as Unevaluated because reading it is not the Referee's job (§2).
  MP charges *"no new nuclear this term"*, which is §3's own worked example.
- **Every Exclusion is soft, and all eight Parties name somebody.** Ten pairs in total: S→SD,
  M→V, SD→V and MP, V→SD and M, C→SD, KD→V, MP→SD, L→V. Each reaches its Agent as "a
  preference, not a veto: there is a price at which you would deal with them anyway". Nothing
  in these files can stop a Party voting any way it likes (§2).

## Axis conventions

The poles are the same ten in `fixtures/README.md` and in `AXIS_POLES` in
`src/kbbl/models.py` — a convention of this repo, not a fact about politics. A Position here is
a reading of a real party placed on an invented scale, which is two layers of judgement, not
none.
