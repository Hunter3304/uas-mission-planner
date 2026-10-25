# Iteration 014 Part 2 - Optional population route objective

Date: 2026-10-25 (Europe/Berlin). Status: implemented and locally accepted.
User authorized Part 2 after publishing Part 1.
Implementation: `feature/124-population-routing`, assigned Issue #124 in
[Milestone 13](https://github.com/Hunter3304/uas-mission-planner/milestone/13).
Plan: [Iteration 014](../../plan/iteration-014.md).
Rules: [Population routing](../../rules/population-costs.md).

## Part 1 publication

Part 1 was committed as `e7459c6d81c1b37e0b1217e035d6332fffbce382` and pushed
to `origin/feature/122-population-surface` before Part 2 application edits.
[PR #123](https://github.com/Hunter3304/uas-mission-planner/pull/123) targets
`iteration/014`. Checks run `40189193801` passed on that exact head: Linux Python,
Windows Python and frontend, including their test steps. Issue #122 remains open
until integration. The remote iteration branch is the verified `d0782d3` baseline.

Automatic approval rejected merging PR #123 because the explicit user request
authorized pushing Part 1, but did not authorize remote iteration integration.
The user was asked for that specific approval. Do not bypass the rejection or
merge into iteration/014/main without the requested authorization. Part 2 work
continues independently on Part 1's published head; its local feature is stacked
until Part 1 integration is authorized. No Part 2 publication is claimed here.

## Implemented behavior

- New shared `PopulationEvaluator` indexes immutable metric cell footprints from
  the accepted 250 m surface. It integrates centreline length times class, counts
  shared edges once using the maximum class, retains repeated traversal and uses
  the documented `1e-7 m` numerical contact policy. Unknown touches/outside support
  remain unresolved, including endpoints and zero-length routes.
- `PopulationRiskModel` adapts that evaluator to graph/native planners while
  preserving building support/background semantics. Optional regional controls
  are `include_population` (false by default) and `population_weight` (1 when
  enabled). Inactive/zero-weight population has no preparation/support requirement.
  An invalid hidden weight is ignored when population is disabled.
- Risk base: `J = w_building * B + w_distance * L + w_population * P`.
  Distance base: `J = L + w_population * P`, with effective building/distance
  weights 0/1. A positive population weight also permits a population-only risk
  objective with building/distance coefficients both zero.
- A*, Dijkstra and native ABIT* share the evaluator, connector costs and independent
  final costs. Graph/native heuristics remain admissible. Approximate native paths
  remain diagnostics; unsuccessful exports contain no successful geometry.
- Regional API/CLI expose separate building score-metres, population score-metres,
  physical length, effective weights/objective, population model/reference identity,
  endpoint support and successful-route population cell IDs. Exports preserve the
  same quantities. Building cost is null in distance mode.
- Request-local population preparation/reference is reused across corridor and
  automatic interval retries. Context-local preparation limits preserve shared
  cache identity while enforcing remaining request time, including cache hits.
  Search cost preparation observes its deadline. Final validation, timeouts and
  automatic nonconvergence clear accepted geometry/costs/ETA and retain diagnostics.
- No Part 3 routing checkbox/weight UI was added. Existing colored map controls
  only inspect population; API/CLI opt in independently. Original source files
  and the classification reference remain unchanged.

## Validation and real-data results

Final complete backend regression: **372 passed / one existing Windows skip**
(133.09 s). Focused final routing/CLI/API/automatic-duration checks: **58 passed**
(63.29 s). Twenty-two new cases cover hand-computed P, diagonal/reversed/repeated
segments, shared boundaries/corner touches, zero/unknown data, overflow, inactive
weights, exact connectors, route choices, cost corruption, API/export/native budget,
corridor reuse, automatic retries and preparation cancellation/deadlines.

The controlled two-route fixture has alternatives L=350/P=900 and L=450/P=100.
Their crossover is population weight 0.125. At 0.1 both A*/Dijkstra choose cost 440
on the shorter route; at 0.2 both choose cost 470 on the lower-population detour.
Native OMPL tests pass against the same population evaluator and independently
recomputed final objective. No finite-budget continuous optimum is claimed.

Real-backend browser smoke: 14 passed (35.8 s). Frontend application sources are
unchanged from accepted Part 1; ESLint/build pass. Ruff/format and diff checks pass.

Run the offline real-data campaign with the project Python environment:

```powershell
backend/.venv/Scripts/python.exe doc/experiments/iteration-014/verify-part2.py --output .cache/iteration014-part2-real-new
```

It uses the established frozen 2026-10-07 research scenario, verified existing
Hannover sources/terrain, 250 m graph spacing, 20 s search budget, exact endpoint
coordinates and automatic arrival. It does not acquire data or launch services.
Evidence is in `.cache/iteration014-part2-real-v1/` and is not tracked in Git.

| Real run | Length m | Building score-metres | Population score-metres | Objective |
|---|---:|---:|---:|---:|
| Building-risk baseline, no population | 3715.591528 | 1202.148740 | Not evaluated | 1453.493018 |
| Building risk + population weight 1 | 3715.591528 | 1256.815787 | 1512.315622 | 3015.008983 |
| Distance + population weight 1 | 2840.878100 | Not evaluated | 1487.690116 | 4328.568216 |

All runs succeed and independently validate automatic arrival/constraints. Risk
plus population chooses different geometry from the baseline, with the same
physical length. The two active runs retain the exact Part 1 population identity
`79d339b9671be83654c8e6b1237b085878eccddad55258177fffcb61cdbc011e`.
Independent unbuffered-cell recomputation differs from each active P by less than
`0.000001` score-metres. Population raster, study manifest and original OSM
GeoPackage hashes match before/after the campaign.

Re-scoring the baseline on the same population surface gives P=1865.8690114843
and combined J=3319.3620298647. The selected population-weighted risk route has
P=1512.3156215565 and J=3015.0089830114: approximately 19% less ordinal population
cost at the same physical length. This is not a claim about accident probabilities
or fewer actual people exposed. The baseline still reports null P in its original
population-inactive result; this comparison is a separate diagnostic re-score.

Observed core request runtimes are 59.78 s baseline, 62.40 s risk+population and
50.29 s distance+population. Source preparation accounts for 39-49 s. These runs
have different cache/source-preparation conditions and do not establish relative
speedups. Actual real-data algorithm here is A*; Dijkstra/native compatibility is
verified separately on numerical/synthetic scenarios. Memory and broader combined
UI acceptance remain later work.

## Using Part 2

Add `"include_population": true, "population_weight": 1` to an otherwise valid
regional route request. Keep `objective` as `risk` or `distance`; the response's
`effective_objective` identifies the added population term. Omit the flag or use
weight zero to preserve the existing objective and skip population requirements.

CLI adds `--include-population --population-weight 1` to `uas-planner study-route`.
It retains the existing explicit scenario/terrain/endpoints and interval contract.
The UI routing toggle and conditional input remain Part 3.
