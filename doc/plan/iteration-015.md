# Iteration 015 - Ramke fused-risk regional planning

Original plan date: 2026-10-27 (Europe/Berlin).
Status: implementation authorized on 2026-10-27 after the user reviewed the plan.
The user requested replacing regional `risk` directly, fixed weight information,
background score 0 and a research planning-mode default. No extra objective is added.
The user subsequently authorized a 300-second total request limit if preparation
needs it. Adopt 300 s for regional backend requests, with 310 s browser waiting
to allow response transfer; search budgets remain separate.
Inspected baseline: clean local `main` at `2b3efce`.
Local implementation and validation are recorded in the
[iteration outcome](../iteration/iteration-015/outcome.md). The historical local
checks below are not evidence of a new release run.

Publication update, 2026-11-02: the user authorized pushing the latest
`iteration/015` feature work and merging it into `main`. Fresh local release checks
have completed as recorded in the outcome; remote CI and integration are tracked
separately by the publication PR and GitHub checks. Datasets and `data.zip` are excluded.
The existing 30 s per-graph preparation cap remains independent from the selected
search budget and the 300 s total request ceiling. No macOS OMPL build or successful
macOS route has been verified; the README instructs Mac users to select A*/Dijkstra.

## Intended outcome

Replace the regional risk objective with Ramke's documented hierarchy
of OSM/population fusion and risk/distance optimization. Reuse the existing
Hannover page, source snapshots, constraint engine and planner selector. Change
only the controls and result descriptions necessary to select and explain the
updated objective. Preserve distance as the comparison baseline. Small-area
building-risk experiments remain separate and retain their existing contract.

This is a reproduction of the paper's documented method using the project's
retained modern data and explicit spatial policies. It is not a claim to
reproduce the original author's source code, historical data or numeric results.

## Paper evidence and current implementation

Source: Carsten Ramke (2020), *Development of advanced informed planning
techniques for BVLOS UAS operations*, retained locally under
`praxis/masterarbeit/MA_Ramke_Development of advanced informed planning techniques for BVLOS UAS operations.pdf`.
Page references below distinguish printed pages from PDF page numbers.

- Printed pp. 31-33 / PDF pp. 43-45: separate feasibility from soft cost;
  classify OSM objects; use `natural` to enrich `landuse` and fill gaps.
- Printed pp. 38-39 / PDF pp. 50-51: choose a common cost grid (150 m in the
  described example), classify population into five classes, fuse `building`,
  `landuse` and `highway` equally, then fuse OSM and population equally.
- Printed p. 41 / PDF p. 53: combine the custom fused-map objective with path
  length using weights 0.9 and 0.1, respectively.
- Printed pp. 45-46 / PDF pp. 57-58: compare OMPL planners and select ABIT.
- Printed p. 44 / PDF p. 56: explain the bias caused by unclassified zero-cost
  areas and the use of a medium uncertainty cost for those areas.

At the inspected baseline, regional `risk` was building-only, optionally plus a separately weighted
250 m population term. `landuse`, `highway` and `natural` are independently
classified for inspection but are not route costs. A*, Dijkstra and native OMPL
ABIT* already share hard constraints and independently checked final results.

## Objective contract

Keep `objective="risk"` and `objective="distance"`; regional `risk` now means
the fused paper method rather than the former building-only method.
For a location x on the common cost grid:

```text
C_osm(x) = (C_building(x) + C_landuse(x) + C_highway(x)) / 3
C_fused(x) = 0.5 * C_osm(x) + 0.5 * C_population(x)

F(route) = sum(length_m(segment inside fused cell) * C_fused(cell))
J(route) = 0.9 * F(route) + 0.1 * L(route)
```

Equivalently, after integration on the same common grid:

```text
J = 0.15 * B + 0.15 * LU + 0.15 * H + 0.45 * P + 0.1 * L
```

`B`, `LU`, `H` and `P` are separate score-metre totals; `F` is the fused
score-metre total and `L` is horizontal metres. These are ordinal research
preferences, not probabilities. Count the complete centreline, exact endpoint
connectors and repeated traversal. Safety clearance affects hard checks, not
the width used for soft-cost integration. A zero-length path still requires
valid endpoints and known population support.

The paper objective has fixed documented weights. Population is mandatory for
this objective, independent of a retained legacy checkbox or hidden weight.
Legacy building/distance/population controls must not change its coefficients
or add population a second time. Effective controls and weights are returned
explicitly. Regional risk requests, including requests omitting the objective,
use the new versioned fusion contract. Old adjustable weight arguments are
deprecated and ignored in risk mode; distance-plus-population remains supported.

## Spatial policies to implement and disclose

The paper does not specify all rasterization and tie-breaking details. The
following are proposed project policies, which must be versioned and described
as such rather than attributed verbatim to Ramke.

### Common cost grid and population

1. Use a fixed 150 m cost lattice in EPSG:25832, clipped to the entire saved
   study boundary. Snap its origin to 150 m multiples and retain stable IDs.
   This is distinct from the A*/Dijkstra search grid and from the existing
   250 m population display; no new map layout or overlay is required.
2. Aggregate the retained native 100 m GHSL counts directly onto this common
   grid using native-plane intersection fractions and actual supported area.
   Do not average the existing 250 m class labels to derive a 150 m class.
3. Normalize supported cell density by one complete-study maximum and apply
   exact fifths of [0,1] to obtain classes 0-4. Keep all-zero and NoData cases
   distinct. Changing route corridor, algorithm, search spacing or viewport
   must not change this reference.
4. This uses modern GHSL and count-conserving transfer. The original paper's
   population product, example grid dimensions and figure bin edges differ;
   record those differences. Preserve the existing 250 m population product,
   identities and distance-plus-population routing behavior.

### OSM rasterization and missing data

1. Reuse the existing versioned tag classifications. Preserve original tags,
   provisional unknown-value score 2 and source identities.
2. For each common cell, use the maximum numeric score of intersecting objects
   within each category, with no addition of overlapping duplicates. Polygon
   contributions require positive-area overlap; line contributions require
   positive-length overlap within the cell. A point contributes to its
   containing cell, using stable cell IDs to resolve a shared boundary.
3. Rasterize highway lines directly onto touched cells. Do not invent a road
   width, buffer or a conversion from `lanes` to measured width. This makes
   roads visible to the cost model without pretending they have area data.
4. Use `natural` as a fallback where a cell has no numeric `landuse` coverage.
   It is not a fourth equal-weight OSM layer. Cell-level fallback is an explicit
   approximation; partial-cell land-use/natural blending is outside this version.
5. Cells without numeric category support use the user-selected background
   assumption, default 0. Prefill the existing input with 0. Record its use as
   an explicit assumption, never observed zero risk. The paper discusses medium
   uncertainty cost; the user's default 0 deliberately differs from that suggestion.
6. An obstruction-only classification has no invented numeric score. It does
   not create a new legal prohibition; the cell's remaining numeric support or
   declared background determines soft cost. Record obstruction-only/default
   coverage findings separately from hard constraint decisions.
7. Reuse already declared derived building geometries only where the selected
   planning mode permits them. Retain invalid non-building geometry diagnostics
   and treat affected, localizable cost cells as unresolved; an unlocalizable
   invalid extent prevents model acceptance. Do not silently discard such data
   or turn a geometry failure into background support.
8. GHSL NoData/outside support never becomes medium OSM background or zero.
   Any unknown-population contact makes that route portion unresolved.

### Motion integration and boundaries

Prepare the fused cost surface before route search. The planner evaluates
centreline lengths against that surface, rather than repeatedly fusing all
source objects for each motion. Cache/index the common cells; merge adjacent
equal-cost cells where it is demonstrably useful and preserves component totals.

Partition each motion to count each length once. On shared cell edges, use
the higher fused cell cost, with a stable cell-ID tie break; component totals
must come from that same selected cell, not independent maxima that violate
the fusion identity. Keep unknown-cell contact unresolved. Reuse a documented
small numerical contact tolerance without presenting it as flight clearance.

## Search, constraints and time

- Reuse native OMPL ABIT* for the paper's continuous-space planning approach.
  It remains stochastic and budget-limited; no finite run proves optimality.
  A*/Dijkstra remain selectable for deterministic graph comparisons.
- All planners use exactly the same fused evaluator, endpoint connector costs
  and independent final scoring. A* uses `0.1 * straight_line_distance` as its
  admissible lower bound because all additional costs are nonnegative.
- Preserve the strict/conservative/research constraint engine, source checks,
  full-segment checks, obstacle contact, altitude, terrain and evidence rules.
  Do not copy historical 2020 legal exclusions or fixed legal buffers into the
  present engine. A paper objective cannot make a blocked endpoint valid.
- Preserve automatic arrival from actual route length/speed and complete-flight
  interval revalidation. Reuse one static cost surface across corridor expansion
  and duration passes. A time/profile/altitude change still refreshes constraints.
- Retain current route-grid and request bounds. Bound cost preparation, geometry
  work and integration cooperatively, including cache hits and cancellation.
  Resource failure returns no accepted route, costs or ETA.
- Key a small bounded immutable cost cache by OSM/GHSL checksums, study boundary,
  grid origin/size, classification and fusion versions, background and geometry
  policy. Verify saved sources on retrieval. Measure cold and warm full-study
  preparation; if 150 m preparation exceeds the existing request deadline,
  optimize preparation and reuse cached surfaces rather than changing resolution
  or normalization scope. The user-authorized regional request limit is 300 s,
  with 10 s frontend response grace; other endpoints retain their current timeout.

## Minimal frontend changes

Keep the map, panel arrangement, layer controls, inspectors, endpoint selection,
time input, permission profiles and export button in their current positions.
No CSS redesign or new dashboard is planned.

1. Replace the meaning and label of existing `risk` with fused risk; keep only
   the existing risk/distance values and initial risk selection.
2. Keep the algorithm dropdown in place. Make native ABIT* the initial algorithm
   for this new default, while leaving explicit A*/Dijkstra selection available.
   Do not silently replace a user-selected algorithm on subsequent changes.
3. Remove old adjustable risk/distance weights and their explanations. In risk
   mode show only the fixed fusion explanation; population is always included.
   Keep optional population controls only for distance mode. Prefill background
   with 0 and select research planning mode by default in the regional UI/CLI.
   Core/API retain an explicit strict policy default for unspecified callers.
4. Explain that the fixed 150 m cost grid differs from the existing configurable
   graph spacing and the unchanged 250 m population display. Graph spacing is
   inactive for continuous ABIT* search; do not imply it controls fusion resolution.
5. Add compact result lines for B/LU/H/P, fused risk F, physical length L and
   total objective J. Show returned effective weights/model identity in the
   existing details/export flow. Do not label F as building-only risk.
6. Objective changes cancel stale requests and clear route/ETA/export. Toggling
   source display layers never changes the objective or triggers a route solve.

## Work packages and deliverables

### Part 1 - Fused cost surface and numerical rules

- Add a reusable `core/paper_risk.py` surface/evaluator, separate from HTTP/UI.
- Extend population aggregation internally for a separately identified 150 m
  surface, preserving the public 250 m contract.
- Feed all four supported OSM categories from verified regional sources into
  the new preparer; preserve existing hard-constraint preparation.
- Add `doc/rules/paper-risk-routing.md` with formulas, paper page references,
  spatial policies, model identity, missing data and reproduction differences.
- Validate common-grid counts, classification, rasterization, natural fallback,
  overlap and boundary integration with hand-computable geometry fixtures.

### Part 2 - Shared planner API CLI and exports

- Replace regional `risk` semantics consistently in core, POST API and `study-route`.
- Integrate A*, Dijkstra, native ABIT*, connector checks and final validation.
- Preserve separate component/fused costs and source identities in normal and
  automatic-duration results and GeoJSON exports. Clear them on all failures.
- Preserve distance, distance-plus-population and small-area experiments. Migrate
  regional risk expectations to the new contract and add corruption-detection tests.
- Measure bounded preparation and define offline reuse if required by real data.

### Part 3 - Small frontend integration

- Apply only the dropdown/default, contextual-control and result-text changes
  listed above, within the existing page structure.
- Add browser coverage for risk/research/background defaults, request payload,
  fixed weights, distance controls, stale cancellation and displayed-result export.
- Check the existing desktop/mobile layout and map interactions.

### Part 4 - Integrated real-data acceptance

- Run the required backend checks, frontend lint/build and browser/smoke suites.
- Exercise the retained Hannover sources with explicit valid research endpoints
  for successful model/algorithm comparisons. Independently recompute B/LU/H/P,
  F/J, exact endpoints, hard constraints and automatic ETA from the accepted path.
- Verify A*/Dijkstra objective agreement on the same graph. Run bounded native
  ABIT* and record success, approximation or timeout honestly; do not infer an
  algorithm ranking from different search spaces or one stochastic run.
- Separately test catalog-address conservative failures. Retain their original
  coordinates and report blocked endpoints rather than moving them implicitly.
- Record cold/warm runtime, peak worker memory, cache bounds and source hashes.
  No fixed latency improvement is promised by this plan.
- Update README, rules, iteration outcome and HANDOFF with actual results.

## Acceptance criteria

1. A uniform 100 m path with cell scores B=4, LU=2, H=0, P=3 has
   `B=400, LU=200, H=0, P=300, F=250, L=100, J=235`.
2. An isolated highway change and an isolated land-use change can each change
   route choice with building/population held fixed. This demonstrates that
   the implementation adds actual routing inputs, not just metadata or weights.
3. Natural fallback fills an otherwise unscored land-use cell without becoming
   a separate fusion term or overriding numeric land-use coverage.
4. Unknown OSM background, provisional classifications, obstruction-only entries,
   GHSL NoData, all-zero population and invalid geometry have distinct outcomes.
5. Endpoints, repeated traversal, shared edges/corners and thin roads are covered
   without duplicate length or broken component/fused objective identities.
6. All planners and independent final validation agree on the same scoring
   contract. Deliberately corrupted component or total costs are rejected.
7. API, CLI, UI and export show the actual selected objective and coefficients;
   hidden legacy controls cannot affect paper-mode results.
8. Distance/small-area objectives and the 250 m population display retain behavior;
   desktop/mobile page organization is preserved.
9. Invalid endpoints, unresolved support and time/resource failures contain no
   accepted route geometry, cost totals or ETA. No success claims flight permission.

## Approval and delivery sequence

The user approved implementation, with direct replacement of risk, fixed weight
information, background 0 and research as the regional UI default. Other proposed
policies remain in scope: 150 m fusion, cell-maximum rasterization, cell-level
natural fallback and native ABIT* as the initial regional algorithm.
Implementation and historical local verification are recorded in the outcome.
Publication and merge were authorized on 2026-11-02; complete the fresh release
checks and applicable CI gates, then record actual delivery facts.
