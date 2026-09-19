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
