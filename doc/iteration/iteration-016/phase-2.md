# Iteration 016 Phase 2 — Plan with outdoor pedestrian exposure

Implemented on 19 November 2026 on `feature/134-public-pedestrian-map` with
the [Phase 1 data and map](outcome.md). The approval and methodology are recorded
in the [Iteration 016 plan](../../plan/iteration-016.md). The default **Existing
planning** mode retains its route objectives and controls.

## Planner and time settings

The new mode uses saved sites, a terrain dataset, a Europe/Berlin departure,
altitude, speed and flight clearances. The preset runs A* with 500 m search
spacing, a 1,000 m starting corridor margin and 30 seconds for graph costs and
search. It uses the existing Research feasibility assessment with derived
building geometry, a 30 m missing-height estimate and the stated NHN plus AGL
engineering assumption with zero datum offset and uncertainty. The existing
full flight-interval assessment still checks the actual route and arrival.
The map and results retain the departure exposure window, including when the
estimated arrival crosses a window boundary.

Search spacing is independent of the 150 m exposure grid. The route integrates
density along its centreline and uses `E = sum(length_in_cell × density / 100)`
and `J = L + E`. The fixed reference of 100 people/km² gives a common density
scale across all windows. The configured exposure coefficient is 1. At the
reference density, one metre adds one metre to `E` and two metres to `J`
including the distance. The scale and coefficient are experimental choices.
When a segment follows a shared cell boundary, the maximum adjacent density
is counted once. Missing support along a positive-length part beyond numerical
tolerance makes the edge unavailable to the optimizer. The route has to keep
complete scored support and pass independent path and feasibility checks.

The API uses `objective: "pedestrian_exposure"` on the existing regional route
endpoint. It reports `length_m`, `pedestrian_exposure_m`, `objective_cost`,
the departure and arrival window, coverage assessment, model version and
layer identity. The existing API defaults still select the previous objective
when callers omit it. In the new mode, the same identity is checked when the map
loads the saved departure layer accompanying a successful result.

## Real-input acceptance

Both runs use exact saved MHH and MVZ Labor Limbach Lehrte endpoints with the
same terrain, 100 m AGL, 30 m/s and existing Research assumptions. The date is
7 October 2026, the saved historical research scenario. Both runs completed
on the initial 240-cell graph and passed the complete-flight-interval check.

| Departure in Europe/Berlin | Exposure window | L (m) | E (m) | J (m) | Arrival |
| --- | --- | ---: | ---: | ---: | --- |
| 08:00 | 08:00–10:00 | 15,281.83 | 3,343.98 | 18,625.81 | 08:08:29.394 |
| 12:55 | 10:00–13:00 | 15,281.83 | 4,341.76 | 19,623.59 | 13:03:29.394 |

The two runs selected the same 30-vertex geometry. The 12:55 run retained the
10:00–13:00 exposure surface and checked feasibility through the 13:03 arrival.
An external calculation intersected each saved route segment with the Phase 1
cell polygons, confirmed complete scored coverage and matched all three
reported components to within 0.000001 m. The separate controlled A* test
selects the direct route at a low density and a detour at a high density.

The 500 m default was selected after an initial 250 m run reached the existing
30-second grid-preparation cap. With 500 m, both reference runs finished in
about 52–53 seconds end to end on the development Windows host. This includes
source preparation and the complete flight-interval check.

The full backend suite passed 402 tests with one existing skip. Ruff lint and
formatting, frontend lint/build and all 69 browser regression tests passed.
The controlled tests cover local time boundaries, unavailable exposure, scoring,
mode switching and restoration of the existing planner controls.
The real Chrome workflow reproduced the 12:55 case, showed the arrival-window
notice, retained the departure overlay and exported the same `E` in GeoJSON.
