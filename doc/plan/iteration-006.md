# Iteration 006 — Risk-weighted routing and ABIT* integration

Status: Plan approved; Part 1 implementation authorized on 2026-09-30.
Part 2 implementation authorized on 2026-10-01 and resumed after the native
Windows dependency gate passed. Local implementation and validation are complete;
publication and integration remain pending.
Native Python reimplementation is deferred; no Linux runtime is selected.
Part 3 implementation authorized on 2026-10-01; local controls, comparisons and
documentation implemented on `feature/60-planner-controls` (Issue #60, Milestone 6).
Part 2/3 feature-branch publication authorized on 2026-10-02; integration remains pending.
Date: 2026-09-30 (Europe/Berlin).

## Objective

Reuse the project's saved OSM data and explainable tag classifications to
choose routes using travelled distance and accumulated ground-risk score.
Add the reference archive's ABIT* planner behind the same cost and constraint
interfaces as the existing graph planners. Preserve explicit unresolved inputs
and distinguish graph optimality from continuous-space planning results.

## Confirmed user decisions

- Use metric coordinates for distances, intersections and safety buffers.
- Risk cost is intersected route length multiplied by the area's risk value.
- Point collision uses intersection of the buffered point with obstacles;
  partial overlap and boundary contact are invalid. Validate complete motions too.
- Initially retain reference weights: risk 0.9, horizontal length 0.1.
- Prepare this plan first; begin implementation only after user approval.

## Verified baseline

- `acquisition/osm.py` fetches building, highway, landuse and natural tags through
  OSMnx/Overpass, retaining source geometries and attributes.
- `core/costs.py` and `core/cost_rules.json` already classify independent tag
  layers with ordinal costs 0–4. Unknown classified values default to 2 with
  an explicit flag; unassessed map space is not an established zero-risk area.
- `core/grid.py` already uses EPSG:25832 for the Braunschweig study region.
- `core/routing.py` implements distance-only A*/Dijkstra and final vector checks.
  Its metric-displacement check and full-distance heuristic must be adapted
  when objective weights become distinct from physical lengths.
- Python baseline is 3.13 on Windows and Linux. OMPL is not a current dependency.
- The reference ZIP contains 10 Python files, but not its scenario datasets or
  the production process for `merged15.shp`. Do not assume that fusion model
  has been reproduced or that its risk values equal the project's categories.
- Real Braunschweig constraint coverage/applicability remains unresolved.
  Risk optimization cannot resolve those existing data limitations.

## Approved scope and modelling policies

First delivery uses building polygon scores only. Reuse existing independent
road/landuse/natural analysis without adding those layers to the routing objective.
Population objective remains disabled. Other-layer fusion is a later extension.

For each metric segment e, compute R(e) = sum(length(e intersect A_i) * r_i)
over a non-overlapping effective risk map, and J(e) = 0.9 * R(e) + 0.1 * length(e).
Intersections use the unbuffered route centreline, never buffered polygon perimeter.
The full path sums these values, including exact endpoint connectors.

Proposed overlap policy: maximum building score at each location, avoiding
duplicate OSM objects artificially adding costs. Preserve contributing object IDs.
Unknown classifications keep the existing provisional score 2 and its flag.
Obstruction-only entries have no invented numeric score; their handling is
explicit in the scenario's constraint model.

Proposed background policy: a complete, explicitly configured research cost
surface is required. For synthetic fixtures, outside-building background is
known and set explicitly. Real unassessed space must remain flagged; an optional
background assumption may be recorded as such, never presented as observed zero.
Do not produce a validated result when the selected policy requires inputs that
remain unresolved. Handle non-polygon building geometry explicitly: do not invent
footprints or silently buffer them into scored buildings.

High scores remain soft costs. Historical paper obstruction flags are not
automatically promoted to current legal prohibitions. Existing explicit hard
constraints remain authoritative.

Expose a nonnegative `safety_distance_m`. Use the same value for point and motion
checks in all planners. Proposed compatibility default is 0 m; positive-buffer
fixtures demonstrate the clearance behavior. A 0 m check must use Point/LineString
directly because Point.buffer(0) is empty. With positive clearance, the entire
buffered geometry must be covered by the allowed boundary and must not intersect
blocked geometry. Boundary contact with obstacles is blocked.

## Delivery parts

### Part 1 — Shared risk and geometry core; weighted graph baseline

1. Build a reusable metric model from saved snapshots and existing classifications.
   Transform all contributing layers/endpoints consistently to EPSG:25832.
2. Separate tag classification, effective risk surface, segment evaluation and
   constraint checking. Use spatial indexes to limit intersection candidates.
3. Return physical length, risk-length cost, weighted objective and assessment
   flags separately. Validate finite, nonnegative scores and configuration.
4. Apply J to existing A*/Dijkstra edges and endpoint connectors. Use
   h = 0.1 * straight-line metric distance for A* with nonnegative risk;
   Dijkstra uses zero heuristic. Keep the existing distance-only mode available.
5. Include risk rules, source checksums, background/overlap policies, weights,
   safety distance and CRS in prepared-model cache identity and route provenance.

Acceptance: analytically known segment costs match; A* and Dijkstra return equal
objective values on controlled graphs; reported physical length is independent
of objective value; unknown inputs stay explicit; existing distance mode works.

### Part 2 — Official OMPL/ABIT* adapter and bounded execution

Windows dependency gate passed on 2026-10-01: official OMPL 2.0.1 plus recorded
binding/portability patches compiled into a Python 3.13 x64 wheel. Fresh isolated
wheel installation, actual ABIT* solve, all custom callbacks, conservative
last-valid semantics, deadline/cancellation and independent path/cost checks
passed. See [verification](../iteration/iteration-006/part2-windows-verification.md)
and README dependencies. Part 2 local adapter acceptance now passed (Issue #59);
Linux execution and distribution to a second Windows machine are unverified.

1. Verify a reproducible native Windows source build of official OMPL and its
   Python 3.13 bindings in an isolated directory/environment before changing
   project dependencies. Check MSVC/CMake/Ninja, Boost/Eigen and Nanobind; pin
   the source revision and record any portability/binding patches. Compilation
   or import alone is insufficient: instantiate ABITstar, exercise custom
   objective/state/motion callbacks (including motion-validator overloads), and
   solve and independently validate a controlled fixture. Preserve Linux support
   with a separately tested installation path; do not install WSL or Docker.
2. Integrate official ABITstar through a named planner contract with independent
   instances per task. Use `initialize()` and `simple_setup` rather than a
   method/attribute named `setup`. Keep native Python reimplementation deferred.
3. Share Part 1's metric state/motion checks and segment costs. Verify admissible
   cost-to-go behavior for the custom objective; start with a conservative lower
   bound rather than copying the reference heuristic blindly.
4. Replace unlimited experiment loops with an explicit total planning budget,
   bounded solve slices where useful, cancellation checks and measured runtime.
   Document cooperative cancellation granularity and setup time separately.
5. Return structured results before optional persistence. No fixed global
   `path.txt` or `graph.graphml`; optional diagnostics have task-specific paths.
   Remove graph_tool from the required path; diagnostics cannot affect success.
6. Distinguish exact solution, approximate solution, timeout without exact path,
   invalid endpoints, unresolved input, cancellation and computation failure.
   A time limit does not prove continuous-space infeasibility. Revalidate and
   recompute final route costs before returning an exact successful result.

Acceptance: bounded ABIT* run returns a fully validated exact path on controlled
fixtures; approximate results do not masquerade as exact; cancellation/timeouts
are explicit; simultaneous tasks do not overwrite outputs or share search state.

Dependency decision gate: missing Windows wheels do not prove source-build
failure. The user requested plan revision followed by actual native Windows
verification on 2026-10-01, superseding the native Python decision. Record tested
failures and concrete remedies if compilation/bindings cannot pass the gate;
do not silently change algorithms, Python baseline or operating system. Part 1
remains independently deliverable. Part 2 is not complete until actual custom
callbacks and final validated ABIT* paths run successfully.

### Part 3 — API/CLI/UI, comparisons and delivery

1. Add planner/objective selection, weights, safety distance and ABIT* time budget
   to CLI/API with compatible defaults for existing distance-only requests.
2. Show algorithm, exact/approximate status, length_m, risk_length_cost,
   objective_cost, runtime and model assumptions; export the same provenance.
3. Add a clearly synthetic low-risk-detour demonstration and compare distance-only
   A*, weighted A*, weighted Dijkstra and ABIT* under identical cost/constraint
   settings. Grid and continuous spaces have different candidate routes:
   objective values are comparable but optimality claims are not interchangeable.
4. For ABIT*, record seeds where supported, budgets, repeated runs, exact-solution
   rate and objective distributions. Independently recompute all final costs.
5. Retain real-data unresolved outcomes and report them separately from successful
   synthetic experiments. Document operation, reproducibility and limitations.

## Validation

- Metric known-length segments and mixed-score intersections; subdivision
  invariance; zero-length routes; no buffered-perimeter contribution.
- Overlapping/duplicate polygons, unknown tags, missing background assessment,
  invalid geometry and non-polygon building cases.
- Buffered point partially crossing an obstacle, point inside obstacle, boundary
  contact, safe point, segment crossing an obstacle between valid endpoints,
  positive clearance and zero-buffer behavior.
- Weighted A* heuristic versus Dijkstra; exact endpoint costs; graph failure
  distinguished from unknown continuous-space feasibility.
- ABIT* final checks, approximate outcomes, resource budget/cancellation and
  independent task output; graceful unavailable-planner diagnostics.
- Relevant backend tests, lint/format, frontend checks/build and end-to-end route
  controls/export checks. Preserve current Windows/Linux regression coverage.

## Excluded from this iteration

Population optimization, multi-layer risk fusion, 3D/kinodynamic planning,
altitude/time optimization, dynamic obstacles, flight execution, and resolving
the outstanding DIPUL/NOTAM coverage investigation. No new real-data acquisition
is required for the initial algorithm integration.

## Workflow after approval

Create Milestone 6 and `iteration/006` according to the existing project workflow.
Create and assign issues for the three delivery parts before their feature
branches. Deliver Part 1, then Part 2, then Part 3 with validation and reviewed
integration. Update README, CHANGELOG, iteration feedback and HANDOFF; retain
iteration history and follow verified post-merge feature-branch cleanup.

Part 1 is tracked by Milestone 6 and Issue #56, with implementation branch
`feature/56-risk-weighted-routing` based on `iteration/006`. The user also
requested that the implemented calculation rules be recorded under `doc/rules/`.
Part 2 implementation was authorized on 2026-10-01 after the official Windows
source-build gate. Issue #59 in Milestone 6 precedes branch
`feature/59-ompl-abitstar`, based on `iteration/006` synchronized to main e54e245.
Local adapter/tests/README and lock are implemented; see Part 2 feedback.
The runtime-gate and Python-candidate survey remain historical
evidence; neither WSL nor native Python reimplementation is the current route.
Part 3 implementation authorized on 2026-10-01. The user explicitly approved
Issue #60 creation/assignment in Milestone 6 before `feature/60-planner-controls`.
The branch preserves uncommitted Part 2 work on the same iteration/006 base.
See `doc/iteration/iteration-006/part3.md` for local outcome and validation;
commit/push/integration and remote CI remain pending.
