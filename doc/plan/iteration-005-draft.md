# Iteration 005 discussion draft: external data and constrained shortest-path routing

Status: **DRAFT — not approved for implementation**. Updated 2026-09-29.
No milestone, issue or branch is created by this document. The numbered delivery
steps below describe sequencing, not completed work. After discussion, record the
agreed scope in `iteration-005.md` before starting the normal sprint workflow.

## User-confirmed direction

- First sources: **GHSL and DIPUL** (the repeated DIPUL name was clarified).
- Do not integrate sources or implement routing yet; discuss and agree the plan.
- Flight altitude and time belong to the eventual planning problem. Initially
  hold them fixed; later consider optimizing departure time and altitude.
- User confirmed altitude is AGL. Display local ground elevation and the
  corresponding aircraft altitude above the agreed sea-level datum as well.
- User confirmed a user-configurable square grid with an initial/default side
  length of **50 m**; replace the earlier 25 m proposal.
- First routing milestone is start/end plus applicable constraints, optimizing
  distance only. Population-sensitive routing remains a later proposed extension.
- SORA assessment, algorithms and integration are excluded from this iteration.
- Split delivery into three independently reviewable parts; do not implement all
  parts in one batch. A* for planning and Dijkstra for verification are user-confirmed.
- Use Ramke's supplied master's thesis as methodological background.
- Produce a Chinese report on all six sources in `D:/Aostfalia/praxis/datasource/`.
  This report is a documentation deliverable, not an integration milestone.

## Proposed outcome

For one defined small area, show independent OSM, GHSL population and DIPUL zone
layers, then produce a distance-minimizing route under **explicitly modeled
constraints** and fixed mission altitude/time assumptions. A population-sensitive
comparison is a proposed follow-up, not a prerequisite of the first routing
milestone. Preserve input versions and explain constraints and no-route results.

This is a research model. It does not establish complete legal applicability,
three-dimensional clearance, physical flight feasibility or SORA compliance.

## Relationship to Ramke (2020)

Reference: *Development of advanced informed planning techniques for BVLOS UAS
operations*, supplied locally under `D:/Aostfalia/praxis/masterarbeit/`.

- Section 3.1.1, printed p. 24 (PDF p. 36): continuous 2D, time-invariant state
  space; altitude is omitted under that thesis's assumptions.
- Sections 3.2.4 and 3.3, printed pp. 31–34: separate feasibility/obstruction
  information from optimization costs and discuss when to fuse layers.
- Section 3.4.2, printed pp. 37–39: grid-based preprocessing and weighted fusion,
  eventually represented by equal-cost polygons. Its 150 m grid and weights are
  experiment choices, not parameters automatically appropriate to our project.
- Section 3.4.3, printed pp. 39–41: sampling-based OMPL planning and custom
  continuous segment checks against vector obstacles. Our proposed A* baseline
  is a deliberate implementation difference, not a claim to reproduce its planner.
- Section 4.4, printed pp. 47–49: coarse five-class cost quantization loses useful
  detail; distinguish numeric precision from spatial grid resolution.
- Chapter 6, printed pp. 59–60: dynamic planning includes updating a reusable
  roadmap and searching it after an artificial dynamic obstruction.

Retain the separation of feasibility and cost. Do not copy historical legal
assumptions, universal buffers, area-relative normalization or numeric weights
without justification. An altitude/time-independent assumption in the thesis
does not establish that those variables are irrelevant in general.

## Proposed spatial model

Use a **layered 2D model conditioned on fixed mission parameters**, with both
grid and vector representations. It is not a 3D occupancy model.

| Component | Representation and purpose |
| --- | --- |
| Raw observations | Keep original OSM vectors, GHSL rasters and DIPUL vector payloads plus provenance |
| Mission parameters | Area, exact start/end, fixed altitude and reference, departure time/time zone, validity interval and scenario assumptions |
| Preference fields | Aligned floating-point analytical arrays; retain separate source contributions |
| Applicability/constraints | Separate permitted/blocked/unresolved states under the chosen research policy; retain vector zone boundaries |
| Quality/coverage | Separate NoData, unknown tags, unresolved altitude/time and coverage masks |
| Planner | Grid graph with metric edge lengths; exact start/end connectors and segment checks |

For Braunschweig, evaluate ETRS89 / UTM zone 32N as a metric analysis CRS; verify
transformations with source metadata. Geographic coordinates remain suitable
for exchange and display. Raster pixel area and units must remain explicit.

Use a **50 m default grid**, with cell side length editable by the user. Validate
positive finite values and a practical maximum cell count; changing resolution
must rebuild the grid and invalidate dependent routes/caches. This is a graph
sampling choice, not a claim of 50 m population accuracy. GHSL's native 100 m information
must retain its support and count/density semantics. Narrow relevant passages
may need a finer grid; continuous edge checks prevent obstacle crossings but do
not make coarse-grid search complete in continuous space.

Use vector segment checks in addition to grid constraints so endpoints alone
cannot hide crossings. If an operational clearance corridor is modeled, check
that corridor rather than an infinitesimal line. A geometric clearance allowance
is distinct from a SORA ground-risk buffer and from a source's existing buffer.

Do not immediately force all costs into five bins. UI colors may use categories
without quantizing the underlying population or fused cost calculation.

## Fixed altitude and time: decisions needed

1. AGL is confirmed; the numeric height remains to be chosen. Display ground
   elevation and aircraft altitude using `aircraft_altitude = ground_elevation
   + AGL`, with a consistent documented vertical datum and units. This adds a
   terrain-elevation source requirement (DTM/DEM), not satisfied by the existing
   OSM tag extraction or GHSL population raster. Select/assess that source before
   implementation; distinguish bare-earth terrain from surface/building height
   and ellipsoidal height from sea-level-referenced height. Missing elevation
   must remain unknown. Constant AGL implies changing aircraft altitude over
   varying terrain, even though the search remains horizontal in this milestone.
2. Choose departure time with time zone and a bounded mission interval. A source
   download timestamp is not the mission time or source validity date.
3. First implementation can conservatively retain any applicable restriction
   active during that interval. It must not claim dynamic route timing analysis.
   If using static packages only, explicitly leave temporary-zone coverage unverified.
4. Use a research point-mass cruise-path model initially. Terrain elevation is
   used for height display/applicability; executable terrain-following control,
   take-off/landing, obstacle heights, kinematics and energy are outside this proposal.
   Buildings are not automatically obstacles merely because their tag cost is high.
5. For unresolved zones/coverage, propose no claim of a validated route; use an
   explicit unresolved status or a documented conservative blocking policy.

Later, compare candidate departure times or altitude scenarios only if the data
and objectives actually vary with those choices. Joint space-time search and
live-traffic avoidance are separate future work. Static resident population alone
does not establish a best time to fly.

## Algorithm selection (user-confirmed 2026-09-29)

A* is selected for planning and Dijkstra for verification. See the
[routing algorithm rules](../rules/routing-algorithms.md) for the detailed contract.
The other algorithms below remain future alternatives.

Constraints define valid states and edges before search; high costs are not a
substitute for excluding forbidden traversal. Population values do not change
edge weights in this distance-only iteration.

| Algorithm | Fit and tradeoff | Proposed role |
| --- | --- | --- |
| Dijkstra | Shortest path on a nonnegative weighted graph; no goal heuristic and potentially more exploration | Small-case correctness reference |
| A* | Shortest graph path with appropriate search handling and an admissible heuristic; a consistent Euclidean heuristic fits metric edge lengths | Recommended first production planner |
| Theta* | Any-angle grid planning reduces heading artifacts; needs continuous line-of-sight checks and does not guarantee the exact continuous shortest path | Later comparison |
| PRM* / RRT* | Sampling-based continuous-space planning; asymptotic optimality is not finite-run exact optimality; adds sampling and termination choices | Later thesis-oriented or higher-dimensional research |
| D* Lite | Reuses search work after graph changes; useful for repeated replanning | Later dynamic-data phase |

Recommended first configuration: 8-neighbor A*, metric edge length only, Euclidean
straight-line heuristic, and vector validation of every traversed segment.
At 50 m spacing, cardinal edges cost 50 m and diagonal edges cost 50*sqrt(2) m.
Validate exact endpoint connectors; never silently relocate a selected endpoint.
Disallow diagonal corner cutting. Report optimality for the constructed graph,
not for continuous space. Length means horizontal length, not terrain-following
3D length, energy or flight time. Dijkstra is a verification oracle, not a second
mandatory user-facing planner. Smoothing is deferred.

References: [A* documentation](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.shortest_paths.astar.astar_path.html),
[Theta* original paper](https://arxiv.org/abs/1401.3843),
[OMPL planners](https://ompl.kavrakilab.org/planners.html), and
[D* Lite author's research overview](https://idm-lab.org/project-a-content.html).

## Three-part delivery plan

These are delivery parts within this discussion draft, not three approved sprints
or newly allocated iteration numbers. Finish and review each part independently
before continuing to the next under the subsequently agreed workflow.

### Part 1 — Reproducible data and independent layer inspection

Purpose: establish what data actually exists for the chosen experiment.

- Agree civil/BOS scenario, bounded area, endpoints, numeric AGL, mission interval
  and coverage expectations. Preserve the existing tiny sample and stay within
  the 25 km² acquisition limit. Do not resume canceled acquisition implicitly.
- Validate GHSL product/epoch, CRS, units, native support and NoData; explicitly
  choose a 2020 estimate or 2025 projection. Save original payload and checksum.
- Validate one bounded DIPUL vector response/package: schema, geometry, IDs,
  validity, vertical reference, existing buffers and license. WMS is display
  context, not routing geometry. Record temporary-restriction coverage limits.
- Select and assess a terrain source, including vertical datum, units, coverage
  and NoData. This prerequisite follows from the agreed height-display feature.
- Add independent GHSL/DIPUL visualization alongside existing OSM layers, with
  legends, inspectable values, source/version and unknown status. Display AGL,
  terrain elevation and corresponding aircraft altitude for inspected locations.
- Store external data using source-native identities, not synthetic OSM IDs.

Deliverable: a repeatable local experiment dataset and independently inspectable
layers with provenance. No route-search implementation in this part.

Acceptance: matching bounds/CRS; checked sample values and height conversion;
missing data distinct from zero; repeatable reload; existing OSM behavior retained.
If real payloads contradict documentation, resolve the discrepancy before Part 2.

### Part 2 — Configurable grid and explicit constraint model

Purpose: transform source data into a graph the planner can safely interpret.
Depends on Part 1 payload validation and agreed mission assumptions.

- Implement reusable pure-Python preparation outside FastAPI/React.
- Build a metric square grid, default 50 m with validated user configuration and
  a cell-count cap. Changing size invalidates dependent products/routes.
- Transfer GHSL information with explicit count/density and native-resolution
  semantics; retain it as an inspectable field, not a route penalty this iteration.
- Interpret relevant DIPUL attributes for the fixed altitude/time/scenario.
  Zones may be conditional; do not treat every zone as universally forbidden.
  Track permitted, blocked and unresolved states with a reason and source.
- Agree a conservative or unresolved-result policy for unknown inputs. A missing
  rule/coverage/elevation is not proof that traversal is allowed.
- Build candidate graph connections and exact endpoint connectors; check full
  segments against vector constraints, including diagonal corner crossings.
  Cache results by source versions and model configuration.
- Visualize cell state and allow inspection of why a cell/connection is excluded.
  Existing OSM risk classes do not automatically become obstacles.

Deliverable: an inspectable grid/constraint graph plus valid endpoint connections.
No route-search feature is required to accept this part.

Acceptance: hand-checkable fixtures cover resolution changes, NoData versus zero,
count/density handling, height/time applicability, conditional/unresolved zones,
and narrow obstacles crossed by an edge whose endpoints appear free.

### Part 3 — Constrained shortest route and demo integration

Purpose: complete the end-to-end routing objective using the Part 2 graph.
Use the confirmed A* / Dijkstra roles and routing algorithm rules.

- Implement the selected algorithm (A*) with distance-only weights.
- Let the user select start/end and generate a route with length, runtime and
  mission/source assumptions. Show an optional straight-line reference clearly
  distinguished from a constraint-validated route.
- Preserve exact endpoint positions. Return clear invalid-endpoint,
  unresolved-input and no-path-on-this-grid outcomes. A grid failure does not
  establish that no continuous-space path exists.
- Validate every output segment and compare small fixtures against Dijkstra.
  Cover detours, full blockage, diagonal corner cutting and endpoint connectors.
- Export route GeoJSON and experiment metadata with source/rule versions;
  respect source-derived export licensing. Document reproducible demo steps,
  limitations and results; update README, feedback and HANDOFF.

Deliverable: start/end → modeled constraints → shortest graph route → map and
reproducible result, for one defined area. GHSL is connected to the analytical
model but is not claimed to influence distance-only route selection.

Acceptance: deterministic optimal length on reference graph cases, no forbidden
crossings, explicit failures, and a usable end-to-end local demo. Application
checks are scoped to each part; perform integration checks for final delivery.

## Out of scope for this proposed iteration

Automatic departure-time selection, height optimization, 3D obstacle clearance,
live Droniq traffic, OFM integration, all SORA assessment/integration, EGRED rule
engines, population-weighted routing, OSM–population cost fusion, public
deployment, actual flight execution and a complete physical risk model.

## Pending agreement

- Finalize scenario-dependent settings before implementation. A* planning and
  Dijkstra verification are confirmed; delivery remains split into three parts.
- Select civil/BOS scenario, area, endpoints, numeric AGL and mission interval.
- Select the terrain elevation source and its vertical datum for height display.
- Agree whether temporary-zone data is required in this first implementation.
- Agree unresolved-data policy and practical limits on the configurable 50 m
  default grid; population objective settings are deferred.

Supporting material: [six-source assessment](../data-sources/README.md),
[integration recommendation](../data-sources/integration-recommendation.md), and
[OMPL validity-checking design](https://ompl.kavrakilab.org/core/stateValidation.html)
for the separation of state and motion checks.
