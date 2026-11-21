# Iteration 017 — Weighted outdoor pedestrian exposure routing

The [approved plan](../../plan/iteration-017.md) is tracked by
[Issue #137](https://github.com/Hunter3304/uas-mission-planner/issues/137)
under [Milestone 15](https://github.com/Hunter3304/uas-mission-planner/milestone/15).

## Implementation

The website prefers the saved Hannover Part 1 v4 dataset and opens its route
panel in **Outdoor pedestrian exposure** mode. The mode offers A*, Dijkstra
and native ABIT*, with ABIT* selected at 30 seconds and an editable limit of
120 seconds. The native budget is shared across automatic flight-interval
passes and bounded by the regional request deadline.

Users can choose any of the eight saved sites for either endpoint or enter
two WGS84 longitude/latitude pairs. The exact points feed the map, constraint
preview, solver, complete-flight assessment and export. The 150 m exposure
surface still uses the Berlin departure window throughout the route.

The weighted objective is J = distance weight × L + exposure weight × E,
with defaults 0.1 and 0.9. The route search and independent scoring use the
same weights, and the geographic results record both. The map places
**Outdoor pedestrians** beside **DIPUL restrictions** on wide screens and
stacks the panels on narrow screens.

## Real Hannover comparison

Use the POST endpoint `/api/datasets/hannover-part1-v4/study/route` with the
same retained Hannover files used in [Iteration 016](../iteration-016/phase-2.md)
and terrain `hannover-part2-terrain-v1`. The exposure snapshot SHA-256 is
`58803d3af5e038b37aa4b712ff8bc3edb03a71a06f25834ea2096cb4e246886f`.
Set `objective` to
`pedestrian_exposure`, `duration_mode` to `automatic` and `planning_mode` to
`research`. Set `distance_weight` to 0.1, `exposure_weight` to 0.9,
`time_budget_s` to 30, `corridor_margin_m` to 1000 and `cell_m` to 500.
The scenario uses Europe/Berlin, 100 m AGL, 30 m/s, zero horizontal
and vertical clearances, derived building geometry with a 20 m uncertainty
buffer, a 30 m missing-height estimate and the NHN plus AGL assumption with
zero offset and uncertainty. Use `civil`, unresolved unknown building heights,
and an empty zone assessment.

| Case | Origin | Destination | Departure timestamp | Exposure window |
| --- | --- | --- | --- | --- |
| Short | `rheuma-podbi` | `mhh` | 2026-11-18T14:07:23+01:00 | 13:00–16:00 |
| Long | `mhh` | `limbach-lehrte` | 2026-10-07T12:55:00+02:00 | 10:00–13:00 |

Run A* and Dijkstra once and ABIT* three times per case. These are retained
research scenarios. The request independently validates geometry and scoring,
then assesses the full cruise interval.

| Case | Planner | L (m) | E (m) | J (m) | Preparation (s) | Planner (s) | Total request (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Short | A* | 2999.75 | 3281.64 | 3253.45 | 64.00 | 0.10 | 66.21 |
| Short | Dijkstra | 2999.75 | 3281.64 | 3253.45 | 52.79 | 0.11 | 55.01 |
| Short | ABIT* 1 | 3404.88 | 2209.65 | 2329.17 | 49.31 | 30.01 | 80.62 |
| Short | ABIT* 2 | 3288.10 | 2296.37 | 2395.55 | 36.97 | 30.02 | 68.33 |
| Short | ABIT* 3 | 3132.60 | 2274.32 | 2360.14 | 36.48 | 30.01 | 68.03 |
| Long | A* | 18817.36 | 3180.03 | 4743.77 | 48.60 | 0.43 | 51.85 |
| Long | Dijkstra | 18817.36 | 3180.03 | 4743.77 | 48.85 | 0.49 | 52.27 |
| Long | ABIT* 1 | 16645.40 | 2530.22 | 3941.74 | 38.36 | 30.03 | 71.17 |
| Long | ABIT* 2 | 17347.12 | 3021.21 | 4453.80 | 42.19 | 30.07 | 75.39 |
| Long | ABIT* 3 | 18825.04 | 2374.95 | 4019.96 | 42.86 | 30.07 | 76.15 |

All ten requests returned validated routes. Each passed independent score and
geometry checks and the complete flight-interval assessment on its first
planning pass. A* and Dijkstra matched in both cases. ABIT* succeeded in three
out of three runs per case, with a lower observed objective on each run and
about 30 seconds in the planner. Its continuous search space differs from the
500 m graph, and these finite-budget trials establish performance for the two
recorded scenarios. The complete request timings include source verification,
preparation, search, validation and serialization, with local test load
varying during the comparison.

An additional short-case request used manual coordinates
`[9.7967865, 52.4044919]` and `[9.8044306, 52.3834806]`, weights 0.25 and
0.75, the 120-second ABIT* budget and `export: true`. It passed independent
scoring and full-interval validation. GeoJSON retained both input coordinates
and both weights. The result was L = 2979.37 m, E = 2052.13 m and J =
2283.94 m. Planner time was 120.02 seconds and backend request time was
164.59 seconds.

## Regression verification

- Backend on the Windows host with native OMPL installed. 412 tests passed
  and one test was skipped. The tests cover exact coordinates across all
  three planners, weight-dependent graph choices, missing exposure coverage
  and the shared 120-second automatic request budget.
- The final 12-case pedestrian routing run also passed. It checks each
  planner with both weights positive, distance weight zero and exposure
  weight zero, plus invalid weight inputs.
- Frontend lint and production build passed. All 69 Chrome regression tests
  passed, including the first-load defaults, missing OMPL fallback controls,
  custom 120-second request, coordinate entry and GeoJSON, and desktop and
  mobile panel layout. Vite emitted its bundle-size advisory for the
  500.44 kB main JavaScript chunk.
