# Iteration 007 — Real-area research routing and explicit readiness

Date: 2026-10-03 (Europe/Berlin).
Status: Plan and implementation of Parts 1 and 2 authorized by the user.

## Problem and objective

On braunschweig-part1-v2, ABIT* can exhaust a three-second budget during data
preparation before reporting unresolved source applicability. Enable explicit,
reproducible research routes on real geography while preserving strict defaults.

## Part 1 — Readiness and timing

Validate endpoints and constraint readiness before native planner setup. Return
structured global and local reasons instead of hiding them behind a timeout.
Report preparation, planner and total durations separately. ABIT* budget denotes
search time, excluding data preparation; maximum remains 60 seconds per run.
Preparation remains bounded by the existing 10,000-cell grid limit and frontend
120-second request timeout (not a hard server deadline).

## Part 2 — Explicit research mode

Add strict (default) and research modes to shared core, CLI, API and UI. Research
mode explicitly assumes unresolved DIPUL applicability does not exclude travel;
it is not legal validation. Preserve source diagnostics, known blocked geometries,
terrain unknowns, boundaries and clearance. Do not alter cached strict grids or
saved source snapshots. Rebuild graph eligibility consistently, retaining diagonal
corner checks. Export mode, assumptions, crossed uncertain zones and mission dates.
Keep strict grid colours and source polygons available for inspection.

Research success means a computationally validated route under stated assumptions,
not permission, terrain-following 3D clearance or population risk certification.
Real-source inspection also found four non-polygon building objects causing global
risk uncertainty. Research explicitly uses polygon footprints only, retaining omitted
object diagnostics and recording this assumption; strict risk keeps blocking them.
Building costs retain their existing meaning; blank background stays unassessed
unless the user supplies a score. Comparison must use the selected mode consistently.

## Acceptance

- All three strict algorithms explain the real snapshot's global blocker before search.
- Invalid endpoints take precedence over readiness and timeout.
- Research mode preserves known obstacles and missing-terrain exclusions.
- A*, Dijkstra and ABIT* use the same selected research constraints and provenance.
- Real Braunschweig A*/Dijkstra routes agree in objective and preserve exact endpoints;
  ABIT* is validated if it finds an exact solution, otherwise reports bounded failure.
- UI mode changes invalidate results; research labels and timing survive GeoJSON export.
- Backend regression, lint, frontend build and browser checks pass.

## Deferred Part 3

No new source acquisition, updated mission scheduling, legal applicability rules,
NOTAM verification, population fusion, full-city planning or full 3D avoidance.
Existing 2026-10-01 mission dates are historical and must remain visible in provenance.

## Delivery

Local implementation, tests, real-source evidence and README/HANDOFF updates.
Remote publication and integration are not included in this request.
