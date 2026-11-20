# Iteration 016 Phase 1 — Hannover–Lehrte pedestrian layer

Implemented on 18 November 2026 against the saved `hannover-part1-v4` study.
The [approved Phase 1 plan](../../plan/iteration-016.md),
[preparation guide](../../experiments/iteration-016.md) and
[source inventory](../../data-sources/07-mid-2023.md) record the scope,
commands, source definitions and citations. The implementation is on
`feature/134-public-pedestrian-map` from `iteration/016`. The existing Phase 1
[issue #134](https://github.com/Hunter3304/uas-mission-planner/issues/134) is in
[Milestone 14](https://github.com/Hunter3304/uas-mission-planner/milestone/14).

## Real-input acceptance run

- The 10 BKG municipalities with positive-area intersections had published MiD
  SAE rows. They covered all 411.447 km² of the original metric footprint.
  The GHSL layer had full valid coverage. The municipality intersection
  reconciled approximately 666,835 residential people from the 2020 grid.
  It split 421 populated 150 m cells at municipal boundaries. The sum of the
  absolute native-area correction to preserve cell counts was below 0.001
  resident.
- The saved OSM network had 211,509 vertices and 233,953 eligible walkable
  edges, with outdoor edges intersecting 14,547 study cells. There were 19,840
  OSM destination features, including 11,903 supplemental features from the
  existing PBF, and 13,380 snapped destination nodes.
- The map represents the full footprint with 18,574 cells in each window.
  17,431 cells have a model estimate, including 5,760 modelled zeros, covering
  93.87% of the area. 1,143 cells are marked unavailable over 25.222 km².
  Of those, 627 lack a nearby mapped connection, 514 lack a reachable mapped
  destination, and two intersect a segment with uncertain shelter. These
  model-coverage limits remain visible in the map and API.
- The modal split and daily rates give approximately 533,175 modelled walking
  departures per representative day. The chosen grouped-duration assumptions
  imply an average of 31.13 minutes per departure. The walking-minute ledger
  reconciles approximately 16,599,348 total person-minutes, including
  15,827,154 outdoors in the study area, 149,290 covered, 13,070 outside the
  study area and 609,834 unallocated. Unallocated is about 3.67% of the budget.

| Europe/Berlin window | Mean estimated concurrent outdoor pedestrians in cells with usable model coverage |
| --- | ---: |
| 05:00–08:00 | 6,540 |
| 08:00–10:00 | 14,035 |
| 10:00–13:00 | 18,223 |
| 13:00–16:00 | 21,529 |
| 16:00–19:00 | 20,469 |
| 19:00–22:00 | 9,228 |
| 22:00–05:00 (next day) | 1,107 |

The column reports a modelled concurrent mean across the known cells. The
Niedersachsen timing profile represents all survey days pooled. The model
uses fixed spatial allocations, so the surfaces have the same relative
pattern and different intensities. For 08:00–10:00, assigning 60 or 120 minutes
to the open duration group gives approximately 12,488 and 15,281 pedestrians.
Using a 750 m instead of 500 m destination decay changes the morning total by
about one pedestrian and redistributes walking across cells. The separate
coverage sensitivity reduces the totals by about 1.52%. These sensitivity
cases describe model assumptions. They are separate from sampling uncertainty
and from comparison with local street counts.

## Evidence and receipts

- The served local snapshot is `data/.pedestrian-exposure/hannover-part1-v4.json`.
  SHA-256 `58803d3af5e038b37aa4b712ff8bc3edb03a71a06f25834ea2096cb4e246886f`.
- The local public workbook has SHA-256
  `036acf4cd3cf3993a8e8f0547130500fcc245087519180487bc3902a5b40462f`.
  The WFS response has SHA-256
  `1c328f829cbf465c147c028ab291e713a8cf917c1c3de85701c6e6376eec208a`.
  The snapshot preserves the OSM, GHSL and study-manifest receipts and both
  public MiT query definitions with unrounded percentages.
- An independent midpoint integration at 15-second steps matched all seven
  time-window budgets. Independent product checks verified the total number of
  departures, grid area, coverage states, person-minute partitions and common
  spatial pattern across windows. The live local API returned all seven
  full-footprint layers on the same colour scale. A second offline preparation
  produced the same SHA-256 in about 204 seconds on the Windows host.
- The real browser loaded and inspected a cell in all seven windows. The
  legend stayed fixed and the 390 px viewport had no horizontal overflow.
  All 68 mocked browser regression tests passed, as did frontend lint and build.
- The backend regression suite passed 394 tests with one existing skip.
  Ruff lint and formatting checks passed for all changed Python files.

See the [Phase 2 outcome](phase-2.md) for route planning on these surfaces.
