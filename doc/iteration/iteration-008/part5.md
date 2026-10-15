# Iteration 008 Part 5 — Static experiments and evidence

Current verification: 2026-10-15 (Europe/Berlin). Tracking:
[Issue #78](https://github.com/Hunter3304/uas-mission-planner/issues/78), closed on
2026-10-15 at the user's explicit request. The user authorized merging the retained
feature and updating README/HANDOFF. Feature and main integration use separate CI
checks; final publication facts are recorded after execution.

## Current implementation and reproduction

The original Part 5 feature `51e1508` is reconciled with main `633b16e`, retaining
Iterations 009/010. Its synthetic risk adapter now accepts the current metric
search boundary. The runner closes native terrain readers after each altitude.
Production planners, restriction policies and original source snapshots are unchanged.

Run from the repository root using the locked backend environment:

```powershell
backend/.venv/Scripts/python.exe doc/experiments/iteration-008/run-part5.py --output .cache/part5-new
backend/.venv/Scripts/python.exe doc/experiments/iteration-008/report-part5.py --input .cache/part5-new --output .cache/part5-new-evidence.json
```

Both commands refuse existing outputs. `--synthetic-only` runs without real source
snapshots. Optional `--study`, `--terrain` and `--scenario` paths must match between
the runner and reporter. Requests are forbidden during the run; original inputs
are read without modification. `summary.json` is written last and checksums
`runs.json`; a directory without a summary is interrupted work, not complete evidence.
The reporter rechecks original manifest hashes, record integrity, grouped algorithm
results, failure geometry, mission/provenance speed and graph invariance.

The primary [evidence](part5-evidence.json) is the fresh 2026-10-15 run on the
current engine. Full local records: `.cache/part5-current-20261015/runs.json`.
The unchanged [2026-10-08 evidence](part5-evidence-20261008.json) and original
`.cache/part5-full-v2/` remain historical; original checksums were reverified.
Historical results are not substituted for current acceptance.

## Matrix and real Hannover outcomes

The latest run contains **600 matrix records**: 360 real and 240 synthetic, plus
six separate real research preflights. Wall time: 144.41 s. Source
preparation: 45.35 s at 100 m and
42.15 s at 120 m. Backend regression
and frontend checks overlapped part of this run; these are observations, not
isolated performance benchmarks.

| Exact catalog pair | Matrix records | Current outcome |
|---|---:|---|
| rheuma-podbi -> mhh | 120 | unresolved_input |
| amedes-georg -> mhh | 120 | unresolved_input |
| limbach-lehrte -> mhh | 120 | unresolved_input |

All 360 real records and six research checks fail preflight with no route geometry
and zero search duration. The matrix explicitly uses strict mode, unresolved
building-height/geometry policies, the retained 2026-10-07 engineering interval,
100/120 m AGL, 100/250/500 m grids, 25/30/35 m/s speeds and fresh/reused prepared
models. Exact endpoints are retained. No lengths, costs or cruise times are invented.
Real ABIT* preflight failures are not counted as stochastic searched-path samples.

Separate research preflights do not enable the derived geometry, estimated 30 m
building height and assessed background used by Iteration 009's successful research
routes. Current unresolved outcomes therefore do not contradict those results.
Iteration 010 conservative policies and evidence profiles remain available, but
this matrix does not invent permission profiles or claim conservative route success.

## Synthetic objective and algorithm comparisons

Fixtures are explicitly artificial EPSG:25832 regions with exact artificial
endpoints, a hospital-score polygon, assessed zero background and known low
building heights. A boundary-detour fixture adds a hard wall. They use the shared
regional planner; their constraint provider never replaces a real Hannover source.

All **170 successful records** pass core validation and independent metric segment/
polygon intersections, endpoint/boundary/obstacle, length, objective and L/v checks.
The remaining synthetic outcomes are **28 graph no-path results** and **42 native
timeouts**. Successful A*/Dijkstra pairs agree on the same graph objective.

| Fixture, 50 m graph | Weighted length m | Distance length m | Weighted risk | Distance-route risk | Weighted J | Distance-route J at 0.9/0.1 |
|---|---:|---:|---:|---:|---:|---:|
| Risk detour | 432.84 | 350.00 | 1.9e-09 | 800.00 | 43.28 | 755.00 |
| Diagonal | 612.13 | 494.97 | 0 | 1131.37 | 61.21 | 1067.73 |
| Hard wall, expanded | 574.26 | 574.26 | 0 | 0.00 | 57.43 | 57.43 |

Risk is ordinal score times metres, not a probability. Small transform residuals
are retained in JSON. Scoring a distance route for comparison does not change its
optimization objective.

Weighted native ABIT*, three fresh-batch runs per baseline, 0.25 s budget:

| Fixture | Successes | Length range m | Objective range | Search time range ms |
|---|---:|---:|---:|---:|
| risk-detour-base | 3/3 | 427.14-498.55 | 43.67-49.86 | 253.24-256.42 |
| diagonal-base | 3/3 | 591.98-594.67 | 59.20-59.47 | 253.39-260.75 |
| boundary-detour-base | 0/3 | - | - | - |
| boundary-detour-expanded | 3/3 | 542.68-668.94 | 54.27-66.89 | 252.40-261.52 |

All variants retain native budgets, attempts, search-start flags, success rates,
length/objective/runtime distributions and wall times. Finite stochastic runs have
no exposed seed; timeouts do not establish infeasibility. Continuous routes need
not match graph lengths and do not establish global optimality.

## Sensitivity, caches and remaining limits

- Twelve deterministic graph/objective groups preserve route geometry and costs
  across 100/120 m altitude and 25/30/35 m/s. Cruise time is checked as L/v and
  the range [L/35, L/25]. Speed changes do not change geometric cost.
- Grids at 25/50/100 m create non-nested graphs/connectors. Finer grids do not
  guarantee a monotonically better objective; per-variant results remain in JSON.
- The synthetic full-height wall prevents an initial-boundary graph route. Adding
  100 m around the boundary permits a checked detour with identical endpoints
  and obstacle geometry. Native timeouts alone are not a proof of no path.
- A real 10 km detour margin is not covered by the retained study/terrain. Larger
  OSM extract coverage does not extend DIPUL/GHSL/terrain. The recorded outcome
  is `missing_source_coverage`; no expanded real routing is claimed.
- The 10,000-cell cap remains. Original-region upper bounds at 100/250/500 m are
  42,476/6,900/1,740; expanded bounds are 97,639/15,756/3,978. These are estimates,
  not successful graph preparation measurements; endpoint preflight runs first.
- Source preparation is shared within each fresh/reused prepared-model batch.
  `cold_equivalent_total_ms` is source cost plus a solve, not repeated measured
  preparation. OS caches are uncontrolled; no solved route is reused.

Fixed-AGL 2D is not a 3D terrain-following or flight-dynamics model. Takeoff/landing,
wind and turns remain unmodelled. GHSL is inspection-only, with no population cost
in the objective. Real permissions, complete NOTAM access, unsupported applicability
and datum uncertainties remain separate needs. OSM overlay performance and mission
end-time feasibility remain deferred.

## Current validation and integration

- Full backend: **261 passed / one existing Windows permission skip** (100.12 s).
- Six experiment tests pass, including cost/endpoint corruption detection,
  no-path boundary expansion, graph agreement and speed/provenance isolation.
- Ruff lint/format, frontend lint/TypeScript/production build pass.
- **14 mocked browser and 12 real-stack smoke tests pass**, with clean exits.
- Fresh 600-record report, all successful synthetic checks, twelve invariance
  groups, six research preflights and unchanged input manifests verified.
- Historical 600-record report reverified; original data/evidence remain local.
- Final feature/main CI and merge facts follow in HANDOFF after verification.
