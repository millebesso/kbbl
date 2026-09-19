# Fixtures

A Fixture **is** a Scenario — same shape, same loader, same 349-seat validation (`docs/kbbl.md`
§9). Only the directory and the intent differ. Everything here is fictional.

## `four-party/` — the Scenario v1 negotiates on

Four Parties, 349 seats, and a deliberate knife-edge:

| Party | Seats | Character              |
| ----- | ----- | ---------------------- |
| NP    | 140   | Market right           |
| FF    | 132   | Social-democratic left |
| GV    | 42    | Greens                 |
| MI    | 35    | Centrists              |

```
NP                        = 140
FF 132 + GV 42            = 174   <- one seat short of blocking
MI                        =  35
```

No Party reaches 175 alone, and the two seats that decide everything are the ones nobody holds:
**NP + MI is exactly 175, and FF + GV is exactly 174.**

Largest-first makes NP the Formateur, and under Negative parliamentarism its cheapest route to
power is an Abstention rather than a partner. An NP minority government of 140 faces 209 seats
that could vote No — enough to block it — but that total collapses below 175 the moment any one
of the three abstains, and by only a single seat when it is MI. The competing government, an
FF+GV minority of 174, is blocked by NP + MI at precisely 175, so it too lives or dies on
whether MI steps out of the way. MI's low Willingness to re-elect (2) is what makes that
Abstention purchasable; GV's high value (8) makes it the expensive sell.

This is the shape of the real 2026 parliament (§9) — no bloc at 175, a small centre Party's
Abstention deciding who governs — in a chamber small enough to read the whole Transcript of.

**Every Party is pivotal.** The groupings that reach the Blocking minority without a spare seat
are NP+FF, NP+GV, NP+MI and FF+GV+MI: each Party appears in at least one, so no Party can be
safely ignored by the Formateur. That is deliberate. An earlier draft of this Fixture gave GV
28 seats, which made it a null player — pivotal in no configuration at all, and therefore
worthless to court. A Party the arithmetic lets the Formateur ignore is a Party the negotiation
never has to bargain with, and a quarter of the chamber stops being part of the game.

Note that NP+GV is arithmetically one of those groupings while NP lists GV as an Exclusion.
Exclusions are soft and every one has a price (§3) — this Fixture is built so that the price is
sometimes worth paying.

## The Referee Fixtures

Three more Fixtures exist so the deterministic core can be tested against answers that are
obvious by inspection (§8, §9). Nothing negotiates on them — they have no Cassettes — and the
invariants in `tests/test_referee.py` are run over every Fixture in this directory, found
rather than listed, so a Fixture added later is covered by them the moment it lands.

### `landslide/` — one Party above the Blocking minority

| Party | Seats | Character           |
| ----- | ----- | ------------------- |
| MJ    | 200   | Broad governing left |
| OP    | 100   | Market right        |
| RS    | 49    | Greens              |

MJ alone clears 175, so it is the only minimal Grouping there is and nothing the rest of the
chamber does can defeat a Proposal it tables: OP + RS is 149, and 149 No votes are 26 short.
The right answer is that the negotiation is over before it starts.

### `knife-edge/` — a kingmaker holds the balance

| Party | Seats | Character    |
| ----- | ----- | ------------ |
| RB    | 173   | Right bloc   |
| LB    | 151   | Left bloc    |
| KM    | 25    | Centre       |

This is §9's real 2026 arithmetic with the blocs collapsed into one Party each. Neither bloc
reaches 175, and **KM's Abstention alone decides who governs**: an LB minority of 151 survives
if KM steps out of the way, because RB's 173 is two seats short of blocking it, and dies the
moment KM votes with RB. The mirror holds for an RB minority. Neither bloc can do anything
about it, which is the point — under Negative parliamentarism the thing worth buying is an
Abstention, and KM's low Willingness to re-elect (2) is what makes it purchasable.

### `deadlock/` — no Platform pays any two prices

| Party | Seats | Character       |
| ----- | ----- | --------------- |
| RF    | 120   | Market reform   |
| SK    | 115   | Socialist left  |
| TN    | 114   | Traditionalist  |

Every Party is short of 175 and every pair clears it, so nobody governs without somebody else
stepping aside. The Supporting prices make that impossible to buy with policy: RF charges
`economic >= +4`, SK charges `economic <= -4`, and TN charges `economic == 0`. Those three
name one Axis between them and contradict each other pairwise, so **no Platform in the whole
-5..+5 range pays more than one of them** — the test ranges over all eleven values and says so.
Any Abstention bought here is bought against a Party's own stated price, which is exactly the
judgement the Referee is not allowed to make for it.

## Axis conventions

Positions are scored −5..+5 on ten Axes. The poles used by every Fixture here:

| Axis            | −5                          | +5                             |
| --------------- | --------------------------- | ------------------------------ |
| `economic`      | State-led redistribution    | Free market, low tax           |
| `environment`   | Growth before climate       | Climate before growth          |
| `military`      | Disarmament, non-alignment  | Heavy defence, alliance        |
| `health`        | Fully public provision      | Market provision               |
| `immigration`   | Restrictive                 | Open, generous                 |
| `law_and_order` | Rehabilitation, liberties   | Punitive, tough                |
| `education`     | Comprehensive, public       | School choice, private         |
| `transport`     | Roads and cars              | Rail and public transit        |
| `social`        | Traditional values          | Progressive, liberal values    |
| `international` | Sovereigntist, EU-sceptic   | Internationalist, pro-EU       |

These poles are a convention of this repo, not a fact about politics. Fixture Positions are
invented to produce a legible negotiation, nothing more.

The same table lives in `AXIS_POLES` in `src/kbbl/models.py`, because a bare `economic: +5`
says nothing to an Agent — the poles have to travel with the number into every Persona. Change
one copy and change the other.
