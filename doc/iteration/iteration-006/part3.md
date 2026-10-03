# Iteration 006 Part 3 — Planner controls and reproducible comparisons

Status: local implementation authorized on 2026-10-01. Issue [#60](https://github.com/Hunter3304/uas-mission-planner/issues/60)
is assigned to Hunter3304 in Milestone 6. Branch: `feature/60-planner-controls`.
Feature-branch publication was authorized on 2026-10-02; integration remains
pending. The local validation state recorded below predates publication.

The branch preserves all uncommitted Part 2 work from `feature/59-ompl-abitstar`
on the existing iteration/006 base. No commit, push, PR or integration merge
has been performed for these local Part 2/3 changes.

## Public operation

`core/planning.py` is the shared CLI/API entry point. `astar`, `dijkstra` and
`abitstar` support `distance` and `risk`. Default requests retain distance-only
A*, exact endpoints and the existing conservative constraint policy. Distance
does not require an assessed building-risk surface; weighted risk never silently
turns an empty background into score zero.

Weighted objective: `J = risk_weight * risk_length_cost + distance_weight * length_m`.
Defaults are 0.9 and 0.1. Weights are nonnegative finite coefficients, not risk
probabilities or normalized percentages. Risk integrates building scores along
the centreline; population is separate. Clearance is measured in the same metric
CRS as the path costs. Exact results retain full source/rule/model provenance.

Run from the repository root, using **new** output names:

```powershell
uv run --project backend --locked uas-planner route-demo --low-risk --output data/synthetic-risk-demo
uv run --project backend --locked --extra ompl-windows uas-planner experiment-route data/synthetic-risk-demo --algorithm abitstar --objective risk --background-cost 0 --cell-m 25 --time-budget-s 3 --output risk-route.geojson
uv run --project backend --locked --extra ompl-windows uas-planner route-compare data/synthetic-risk-demo --background-cost 0 --cell-m 25 --repetitions 3 --time-budget-s 2 --output risk-comparison.json
```

`--start LON LAT`, `--end LON LAT`, `--risk-weight`, `--distance-weight` and
`--safety-distance-m` work for both routes and comparisons. Omit the optional
native extra when only using graph planners. ABIT* without a compatible patched
package returns `planner_unavailable`. CLI stdout is JSON; native warning/error
logging uses stderr. CLI route and comparison output files are never overwritten.

API endpoints:

- `/api/datasets/{id}/experiment/route`: `algorithm`, `objective`, `cell_m`,
  `risk_weight`, `distance_weight`, `background_cost`, `safety_distance_m`,
  `time_budget_s`, optional `start_lon/start_lat/end_lon/end_lat` and `export=true`.
- `/api/datasets/{id}/experiment/compare`: the same cost/constraint/endpoints
  and `repetitions`. Comparisons always use the fixed four-planner lineup;
  individual algorithm/objective selection applies to the route endpoint.

In the map, select the synthetic dataset, grid 25 m and background score 0.
Choose **Weighted building risk**, select an algorithm, and generate or compare.
Results show algorithm, solution kind, exact status, length, risk cost, objective,
runtime, optimality limits and assumptions. Parameter changes invalidate results.
The comparison table scrolls internally on mobile; long report text wraps.

UI exports serialize the **displayed result**, avoiding another stochastic solve.
An API GET export describes that request's solve; it is not a lookup of a prior
request. Failed/approximate results export diagnostic metadata and zero successful
route features. Approximate candidates never appear as exact flight routes.

## Comparison and budgets

The lineup is distance A*, weighted A*, weighted Dijkstra and repeated weighted
ABIT*, with identical endpoints, surface, weights and hard constraints. Re-score
the distance baseline under the weighted model before comparing objectives;
its search objective is still physical distance. Independently check returned
endpoints and full constraints, recompute segment costs and compare with returned
values. Failed verification cannot contribute to the verified exact-solution rate.

Budgets are at most 60 s per ABIT* run, with 1–10 repetitions and at most 60 s
total ABIT* budgets per comparison. Input snapshot verification precedes the
planning timer. Individual route grid preparation, risk preparation and native
setup consume the requested budget. Comparisons separately prepare the shared
grid/model before per-run timers. Cooperative callbacks and final validation
can add overhead; this is not a hard process-kill deadline. Aborting a browser
request does not forcibly cancel a backend task, which remains bounded by its
planner limits. Timeouts do not establish continuous-space infeasibility.

The bindings do not expose per-task planner/sampler seeding. Reports explicitly
record `seed_supported=false`, null seeds, budgets, repetitions, environment
versions, verified exact-solution rate and objective distributions. The global
RNG is not reset during concurrent tasks. Regeneration reproduces the scenario
and deterministic graph results; timestamps/checksums, native paths and timings
need not repeat byte for byte. Grid and continuous-space candidates differ;
minimum graph objective and finite-budget continuous optimality are separate.

## Measured evidence

[Synthetic report](part3-synthetic-comparison.json): background 0, weights 0.9/0.1,
clearance 0, grid 25 m, three ABIT* runs at 2 s each. All six routes were exact
and independently verified; ABIT* verified exact-solution rate was 3/3.

| Planner | Length (m) | Risk cost (score-m) | Comparable weighted objective |
| --- | ---: | ---: | ---: |
| Distance A* | 192.182 | 163.824 | 166.660 |
| Weighted A* | 233.603 | 0 | 23.360 |
| Weighted Dijkstra | 233.603 | 0 | 23.360 |
| ABIT* run 1 | 194.672 | 0 | 19.467 |
| ABIT* run 2 | 193.982 | 0 | 19.398 |
| ABIT* run 3 | 195.999 | 0 | 19.600 |

The longer graph detour avoids the high-score building band. The continuous
routes use different candidates; these measurements do not prove interchangeable
optimality. The scenario has synthetic zero-background support and no real-flight
applicability.

[Real-data report](part3-real-unresolved.json): existing `braunschweig-part1-v2`
snapshots, grid 100 m, explicit background 0 and one 1 s ABIT* run. Three graph
results remain `unresolved_input`; ABIT* exhausted its budget during preparation
and returned `timeout`. No successful real route was exported. The dataset was
not acquired or modified for Part 3. Unknown legal/temporary restriction coverage
remains unresolved even with a building background assumption.

## Validation and remaining delivery limits

Backend coverage includes compatible defaults, weighted detours/A*-Dijkstra cost
agreement, API parameters/validation, immutable output files, real uncertainty,
unavailable native planner, bounded comparison requests, endpoint selection,
actual repeated native ABIT*, distance ABIT* without risk assessment, native
callback lifetime and subprocess JSON output without native leak diagnostics.
Browser checks exercise real API controls, displayed-result export without a
second solve, result invalidation, zero-budget failures, comparison/report export,
mobile layout and prior route/grid/source workflows.

Native callbacks use weak owner references to remove cross-language cycles while
retaining OMPL's own distance arithmetic. A diagnostic Python `hypot` substitution
produced different floating-point lower bounds and stalled direct distance solves;
it was reverted to OMPL distance through weak ownership. The regression includes
a time-bounded native CLI subprocess. No binding/global RNG workaround was added.

Local checks: full backend regression 158 passed / 1 existing Windows permission
skip; after the final requested-endpoint/corruption check, 8 planner-control tests
passed. Ruff check/format, frontend ESLint/build, 9 mocked Chrome checks and
9 real API Chrome smoke checks passed. See [validation record](part3-validation.md). Remote CI, Linux ABIT* and a
second clean Windows host remain unverified. Publication/integration and reviewed
cleanup of feature branches remain pending. Historical Part 2 records retain
their original delivery state; this document describes the later local Part 3.
