# Iteration 014 - Optional population costs on a 250 m grid

Date: 2026-10-25 (Europe/Berlin).
Status: Part 1 implementation authorized on 2026-10-25, including colored grid
visualization brought forward from Part 3. The user additionally requested replacing
the old green native-count overlay with this grid. Part 2 was authorized after
Part 1 publication and is implemented locally; Parts 3-4 remain planned.
Part 1 is delivered to iteration/014 through PR #123 at `d3b0154`, following
exact-head remote checks and the user's explicit integration approval;
Issue #122 is closed. See [Part 1 outcome](../iteration/iteration-014/part1.md)
for numerical/browser/real-data results and delivery evidence. Part 2 is tracked by
Issue #124 / Milestone 13; see [Part 2 outcome](../iteration/iteration-014/part2.md).
Baseline inspected: local `iteration/013`, with the completed Iteration 013 Parts.
This plan does not claim Iteration 013 delivery to main or create remote tracking.

## Requested result and confirmed scope

The user selected aggregation to 250 m population cells before classification.
Retain 250 m as the default route search spacing. Add population to route costs
only when explicitly selected beside the existing distance/risk objective control.
Show the population weight input only while that selection is enabled.

For a route, accumulate population cost as:

`P(route) = sum(length_m(route segment inside population cell) * cell score)`

Use Ramke's five ordinal classes, 0 through 4, after aggregation. Document the
implemented classification, aggregation and new routing objective in `doc/rules`.
The work targets Hannover regional planning first, consistent with Iteration 013.
Existing small-area pages and historical requests retain their existing behavior.
Repository documents and application labels remain English; the plan is reported
to the user in Chinese.

## Current implementation and paper evidence

- GHSL is GHS-POP R2023A V1.0, using 2020 estimates on native 100 m
  ESRI:54009 cells. Values are floating-point estimated people per native cell.
- `core/regional.py:PopulationInspector` exposes native cells and area-weighted
  inspection totals, with `routing_cost: false`. Native zero and NoData differ.
- `frontend/src/external.ts:populationColor` uses display bins: zero, positive
  below 25, 25 to below 100, and 100 or more. These are not paper risk classes.
- `core/regional_routing.py` defaults to `cell_m=250`. A*/Dijkstra construct a
  bounded graph; ABIT* samples continuous space instead of building that graph.
- `core/risk.py:RiskModel` currently integrates building scores by line length.
  The risk objective is `risk_weight * building score-metres + distance_weight * metres`.
  Population is not currently part of this objective.
- Carsten Ramke (2020), *Development of advanced informed planning techniques
  for BVLOS UAS operations*, printed p. 38 / PDF p. 50, describes normalization
  by the population maximum and five equal-width classes assigned 0-4. Figure
  3-9 has example boundaries around 0.12, 0.29, 0.47, 0.64, 0.82 and 0.99.
  Consequently the text and figure do not establish exact universal 0.2 cutoffs
  or fixed thresholds of 25/100 people. Printed p. 39 / PDF p. 51 describes
  weighted population/OSM fusion, with half allocated to each layer in that example.

The source paper used an older population product and different grid resolutions.
The 250 m aggregation, fixed normalization domain, exact interval boundaries and
optional additive objective below are explicit project policies inspired by its
method. Do not describe this iteration as an exact reproduction of its experiment.

## Population counts, density and the 100-to-625 example

For ideal complete square cells under the same area convention:

```text
100 m cell area = 10,000 m2 = 0.01 km2
250 m cell area = 62,500 m2 = 0.0625 km2
area ratio = (250 / 100)^2 = 6.25

100 people / 100 m cell = 10,000 people/km2
10,000 people/km2 * 0.0625 km2 = 625 people / 250 m cell
```

Thus a boundary of 100 people per complete 100 m cell corresponds to 625 people
per complete 250 m cell at the same density. This applies to either an upper or
lower class boundary, provided its inclusion convention is preserved. It does not
mean every aggregate cell has 6.25 times one particular source cell's population.
Neighbouring source cells can have different values, and 250/100 is not an integer.

If 100 instead means people/km2, the density threshold stays 100 people/km2; it
must not be multiplied by 6.25. A normalized score or class label is not scaled.

Implementation uses actual intersection/support areas. A study-boundary cell
may be clipped, and a UTM 250 m square transformed into the native Mollweide
plane is not exactly 62,500 native square metres. Its corresponding count
threshold is `density_threshold * actual_support_area_m2 / 1,000,000`.
625 is the nominal full-cell conversion, not a replacement for area calculations.

This iteration does not introduce a fixed 100-person threshold. Actual cutoffs
are derived after aggregation and exported in density units, with nominal
100 m/250 m count equivalents for explanation. Aggregation can change the maximum
density, so the new normalized boundaries cannot simply be copied from the native
100 m raster and multiplied by 6.25.

## Part 1 - Stable 250 m aggregation and versioned classification

Introduce a reusable population cost surface, provisionally in
`backend/src/uas_planner/core/population_costs.py`, independent of HTTP and map
visibility. Read verified saved GHSL only; no source acquisition is needed.

### Grid geometry and count conservation

1. Define a fixed 250 m population lattice in EPSG:25832, with its origin snapped
   down to 250 m multiples from the complete study boundary's minimum coordinates.
   Retain the lattice identity across requests and corridor expansion.
2. Clip lattice cells to the study boundary. Keep stable cell IDs, uncut grid
   coordinates, clipped geometry and actual support area. This cost lattice is
   independent of the corridor-relative route graph origin and any later edits
   to search spacing. Both default to 250 m; they need not have identical origins.
3. Transform each clipped cell into native GHSL coordinates for overlap work.
   Read bounded raster windows and transfer counts by intersected area:
   `N(c) = sum(N(native_i) * area(c intersect native_i) / 10,000)`.
4. Track known area, NoData area and outside-raster area separately. A cell with
   material unknown support has no complete population count, density or score.
   Keep its observed partial count for diagnostics only. Define and version a
   small area tolerance for projection roundoff; do not hide real missing area.
5. For complete support, compute
   `D(c) = N(c) / native_support_area_m2 * 1,000,000` in people/km2.
   Source-plane area is used consistently for count transfer and density.
6. Record the within-native-cell uniform-density assumption. Do not round source
   values or derived counts before classification. Rounded UI values are display only.

Conservation is checked against the native area-weighted population total over
the same study geometry. Do not duplicate full native counts into every touched
250 m cell, use nearest-neighbour sampling, or average already assigned classes.

### Exact classification policy proposed for v1

Use one fixed normalization reference for the complete saved study, computed
from all completely supported 250 m cells. Never recompute it for the viewport,
current route, initial corridor, expanded corridor or automatic-duration pass.

Let `M = max(D(c))` over these eligible cells. For `M > 0`, normalize
`u(c) = D(c) / M` and define five equal-width intervals over the full [0, 1] domain:

| Score | Normalized interval | Density interval |
|---|---|---|
| 0 | `[0, 0.2)` | `[0, 0.2 M)` |
| 1 | `[0.2, 0.4)` | `[0.2 M, 0.4 M)` |
| 2 | `[0.4, 0.6)` | `[0.4 M, 0.6 M)` |
| 3 | `[0.6, 0.8)` | `[0.6 M, 0.8 M)` |
| 4 | `[0.8, 1]` | `[0.8 M, M]` |

Equivalent mathematical definition: `score = min(4, floor(5 * D / M))`.
The implementation must specify stable floating-point threshold comparisons and
test exact boundaries. These intervals make the project policy deterministic;
they are not claimed to be the exact bin edges used by Figure 3-9.

If every eligible cell is known zero, assign all those cells score 0 and record
the all-zero case without division. If there are no complete cells, preparation
is unresolved. Unknown cells never enter `M` and never become score 0.
Score 0 means the lowest ordinal class; positive populations can also receive 0.
It does not mean zero population. All-zero and NoData have distinct UI details.

Record a separate version, provisionally `ramke-population-250m-v1`, including
the source checksum/product/epoch, both CRSs, study boundary, lattice origin,
aggregation method, actual area basis, support tolerance, normalization domain,
`M`, exact density boundaries, count equivalents and class distribution.
Do not modify the existing OSM classification table or its version.

## Part 2 - Shared route objective and algorithm integration

Keep existing building cost `B`, physical length `L`, and population cost `P`
separate. When selected, use the same population evaluator in A*, Dijkstra,
ABIT*, exact endpoint connectors and independent final route validation.

```text
L(route) = sum(segment length in EPSG:25832 metres)
B(route) = existing integrated building score-metres
P(route) = sum(segment length inside each 250 m population cell * its 0-4 score)

risk base objective, population selected:
J = risk_weight * B + distance_weight * L + population_weight * P

distance base objective, population selected:
J = L + population_weight * P
```

Unchecked requests preserve the current risk/distance objectives. The proposed
checkbox is available beside either base objective; the UI explicitly identifies
distance plus population as a combined objective rather than pure shortest path.
In distance mode, effective building weight is 0 and distance weight is 1,
regardless of retained hidden risk-mode inputs.

Add `include_population` (default false) and `population_weight` (proposed initial
value 1 while enabled). Weights are finite and nonnegative and do not need to sum
to 1. The initial value is a research control, not a calibrated safety parameter
or the paper's population/OSM 50:50 fusion. A zero effective population weight
skips population preparation/support requirements and records that it was inactive.
Unknown population cannot affect requests where population is inactive.

### Segment evaluation and uncertainty

- Query a spatial index of 250 m cell footprints in the metric analysis CRS.
  Partition each complete centreline; use intersection lengths, not cell-centre
  samples, endpoint averages, cell counts or corridor areas.
- Count shared-boundary segments once. Proposed tie rule: use the maximum
  adjacent numeric class along an exact grid boundary; if an adjacent touched
  cell is unknown, conservatively leave the support unresolved. Document this
  tie policy, including point touches, and test it consistently in all planners.
- Sum segment evaluations without losing repeated traversals. Exact endpoint
  connectors contribute both their length and population cost.
- A zero-length route has cost 0, but still requires supported population at its
  point when population is active, plus the existing constraint validation.
- Any required unknown/outside population support leaves the segment unassessed;
  do not use building background cost or research planning mode to fill it.
  Missing endpoint support returns unresolved input. Distinguish exclusion of
  unassessed edges from a proven no-path result, using the existing outcome model.
- Population is a soft preference. Even score 4 is not automatically an obstacle.
  Existing DIPUL/building/terrain/clearance checks keep their separate roles.

Reuse/extend the model interface expected by the planners, including
`evaluate`, `distance_weight`, `crs`, `boundary` and `safety_distance_m`, rather
than implementing three different cost calculations. Preserve the building
overlap/background policy. Nonnegative population cost keeps
`effective_distance_weight * Euclidean_distance` an admissible heuristic;
use the same lower bound in the native objective, or zero where appropriate.

Independently recompute `L`, `B`, `P` and `J` after solving. Preserve active
population identity and cutoffs across corridor retries and automatic flight
interval expansion. Recheck actual-route arrival and constraints as today.

### API, result and export contracts

- Extend the regional route POST allowlist and core entry points with the two
  controls. Historical requests without them remain population-inactive.
- Return `population_length_cost`, effective weights/objective, active population
  model identity, source/aggregation/classification provenance and support findings.
  Inactive population cost is null/not evaluated rather than a measured zero.
- Keep `risk_length_cost` as the existing building quantity. Do not silently rename
  its meaning to building plus population. `objective_cost` is the combined scalar.
- Populate controls and available diagnostics on failures as well as successes.
  On failed final validation, clear all accepted route costs, geometry and ETA.
- Include the same information in displayed-result GeoJSON exports and prepared
  identity. Distinguish user-requested controls from their effective values.

## Part 3 - Optional UI control and inspectable 250 m population classes

In `RegionalRouting.tsx`, place `Include population` beside the distance/risk
objective selection, default unchecked. Render `Population weight` only while
checked. Retain existing risk/distance weight behavior for the base objective.
Unchecking removes the active population contribution even if a previous weight
value is retained locally. Invalid hidden values cannot break an inactive request.

Changing the checkbox or active weight invalidates the displayed route/ETA and
cancels obsolete requests. It does not automatically trigger another solve.
Show physical length, building cost when active, population cost when active,
combined objective and effective weights as distinct result values.

Within the existing GHSL source group, provide the derived
`250 m population risk` layer, replacing the old green native-count overlay in
the Hannover UI, as clarified by the user on 2026-10-25. Its display
toggle does not enable route weighting, and route weighting does not require
loading/rendering its GeoJSON. Use a bounded cached display response and the
existing inspector; avoid adding a second independent selection system.

Details and legend show: score 0-4, estimated people in the actual clipped cell,
density, corresponding bin boundaries, normalization scope/reference, 250 m
aggregation and native 100 m support, epoch and known/unknown status. The lowest
class may contain people. NoData must remain visibly different from class 0.
Preserve native GHSL inspection APIs/CLI and other pages, with their original units.

Part 1 now includes the derived inspection API, colors and grid inspector;
the route checkbox/weight remain Part 3. Preserve mobile layout, cached layer toggles, the left
inspector, exact endpoint selection and departure-only planning from Iteration 013.

## Performance and resource policy

- Default route search stays at 250 m. There is no 6.25-fold search-node increase
  merely from adding the population layer. Aggregation and segment evaluation
  still add work and must be measured; unchanged total latency is not promised.
- Build the fixed study population surface and classification reference once per
  verified source/study/policy identity. Use bounded raster reads and an indexed
  in-memory surface. Do not open/read the raster on every motion-cost callback.
- Use the same verified immutable surface within a request, including retries.
  Reuse across requests only through a bounded cache whose identity includes the
  GHSL checksum, study bounds, lattice geometry, area policy and rule version.
  Validate source identity before cache reuse. Record invalidation and memory use.
- Full-study classification is independent of the 10,000-cell search-graph cap.
  Apply a separate bounded aggregation budget, provisionally 100,000 target
  cells, with explicit cancellation/deadline checks. Report resource limits;
  do not silently coarsen the surface or switch normalization to a corridor.
- Population preparation counts toward the existing request deadline. Preserve
  graph preparation/search limits and automatic-duration/browser timeout contracts.
- Viewing native/derived population layers is not a prerequisite for route costs.
  Checking the routing option must not fetch the full native-cell display layer.
- Measure cold aggregation, warm reuse, constraint preparation, search, final
  validation, display payload/rendering and peak memory separately. Compare
  population on/off on the same existing route inputs and source snapshots.

## Part 4 - Acceptance, rules and delivery

### Numerical and routing acceptance

1. Uniform-density fixture: nominal native 100 m cells each containing 100 people
   produce 625 people in a complete 250 m square under a common equal-area test
   geometry. Density remains 10,000 people/km2. Separately verify production CRS
   transformations against actual support area rather than forcing exactly 625.
2. Nonuniform source cells, fractional overlaps, non-aligned grids, clipped study
   edges and source margins conserve the area-weighted source count. Prove why a
   clipped cell uses its own support area for threshold conversion.
3. Verify each class boundary and neighbours, known zero, small positive class 0,
   all-zero study, no complete support, partial NoData and out-of-support areas.
4. Prove that viewport changes, endpoint changes, corridor expansion and automatic
   flight interval changes leave the population grid/reference/cutoffs unchanged.
   Source, study or rule changes must invalidate the identity.
5. Hand-computed line: 50 m in score 1 and 100 m in score 3 gives
   `P = 50 * 1 + 100 * 3 = 350 score-metres`. Test diagonals, shared grid edges,
   corner touches, connectors, repeated traversal and zero-length routes.
6. Synthetic two-corridor graph: population weighting changes the chosen path at
   a calculable weight threshold; A*/Dijkstra agree on total objective, including
   connectors. Weight 0/unchecked recover the existing objective and requirements.
7. When native OMPL is available, verify that ABIT* uses the same `P`/`J` evaluator
   and final validation. Preserve explicit unavailable/time-budget outcomes and
   distinguish finite-budget continuous results from graph optimality.
8. Test API defaults/invalid controls, active/inactive missing population, building
   background independence, overflow, resource limits, failed final validation,
   automatic duration and exported/displayed cost/provenance agreement.

### UI and real-data acceptance

- Checkbox placement/default, conditional weight visibility, active/inactive
  requests, both base objectives, stale-route/ETA clearing and exact export.
- Native counts versus derived class legend/details; no confusion between zero,
  lowest class and NoData. Desktop and 390 px mobile inspector/map layout.
- Derived layer cached show/hide causes no repeated preparation; route weighting
  works with all population displays off. No weight edit refetches raw OSM/GHSL.
- Hannover with verified existing sites: population off/on under identical hard
  constraints, 250 m search spacing and automatic flight interval behavior.
  Record route length, separate costs, active cutoffs, timing, support and memory.
  A real successful solve need not change geometry, but synthetic acceptance must
  demonstrate an actual route-choice effect. Report all unsuccessful outcomes.
- Run focused numerical/API/browser checks, then required backend/frontend and
  real-stack regression. Record actual benchmark results, not estimated speedups.

### Required rule and operating-document updates during implementation

Create `doc/rules/population-costs.md` containing the exact aggregation, units,
250 m lattice, density normalization scope, five intervals, 100-to-625 example,
boundary/support rules, route formula, objective modes, weights, limits and
provenance. Distinguish paper evidence from project-specific choices.

Update `doc/rules/risk-weighted-routing.md`, `regional-constraints.md`,
`routing-algorithms.md` and `doc/rules/README.md` to describe optional population
routing and link the new rule. Update current population inspection-only claims
in affected UI/README/operating notes with their precise remaining scope; native
inspection itself stays an independent product. Do not rewrite historical
iteration reports to imply population routing existed earlier.

Deliver an operating guide and `doc/iteration/iteration-014/outcome.md` with
actual validation/performance evidence and deviations from this plan. Update
HANDOFF/README when implementation is delivered. Keep generated caches and
screenshots outside tracked source files and preserve original data/checksums.

Suggested delivery order is Part 1 surface/classification/rules, Part 2 shared
objective/API/all planners, Part 3 UI/derived inspection, then Part 4 integrated
acceptance and documentation completion. Follow the existing milestone ->
iteration branch -> assigned issue -> feature branch workflow when implementation
is requested, recording actual IDs and respecting Iteration 013 integration state.
This documentation-only task creates no remote milestone, issue, PR or publication.

## Proposed defaults to review with implementation

The user has confirmed 250 m aggregation, length-times-class cost, optional
population weight input and rule documentation. This plan proposes the remaining
precise defaults: complete-study maximum, intervals over [0,1], stable UTM
population lattice, population available with either base objective, initial
population weight 1, and conservative shared-boundary support handling. These
are explicit reviewable project decisions, not pre-existing implemented behavior.

Outside scope: changing OSM tag tables or fusing additional OSM categories,
switching the default route grid to 100 m, source downloads/study expansion,
legal-permission changes, casualty probabilities, SORA calculation, 3D/energy/wind
models, a general planner redesign or migration of other pages to the new UI.
