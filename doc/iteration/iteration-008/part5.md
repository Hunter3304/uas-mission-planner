# Iteration 008 Part 5 — Static experiments and evidence

Date: 2026-10-08 (Europe/Berlin).
Implementation authorized; local delivery on `feature/iteration008-part5-experiments`,
based on `iteration/008` fast-forwarded to main `17d9b27` (Part 4 / PR #77).
Tracking: Milestone 7 / [Issue #78](https://github.com/Hunter3304/uas-mission-planner/issues/78),
created and assigned to Hunter3304 after explicit user authorization on 2026-10-08.
The earlier issue-creation attempt was rejected by automatic approval review;
authorization resolved that tracking limitation. The user subsequently authorized
committing and pushing Part 5 on 2026-10-08. Publication targets this feature branch;
PR integration into iteration/008 or main remains a separate delivery step.

## Reproduction and record contracts

Run from the repository root with the existing locked backend environment:

```powershell
backend/.venv/Scripts/python.exe doc/experiments/iteration-008/run-part5.py --output .cache/part5-new
backend/.venv/Scripts/python.exe doc/experiments/iteration-008/report-part5.py --input .cache/part5-new --output .cache/part5-new-evidence.json
```

Both commands refuse existing outputs. `--synthetic-only` runs without real source
datasets. Optional `--study`, `--terrain` and `--scenario` paths must match between
the runner and reporter. The runner forbids HTTP requests, reads original snapshots
without modification, and writes finite JSON. A directory with no `summary.json`
is an interrupted experiment, not complete evidence; rerun in a new directory.
No original dataset, legal decision, coordinate or dependency is changed.

The existing scenario is retained as an explicit **2026-10-07 engineering interval**,
not a current flight schedule. Baseline altitude/speed are 100 m AGL / 30 m/s;
altitude 120 m and speeds 25/35 m/s are separate sweeps. Building weights remain
0.9/0.1, clearance remains zero, missing heights remain unresolved, strict mode
remains the matrix default, and GHSL remains inspection-only. Six separate
research-mode preflight reports preserve the same real failure findings.

`runs.json` retains exact endpoints, geometry or failure diagnostics, mission and
planner controls, source/rule signatures, assumptions, length, building risk,
objective, cruise estimate/range, independent checks and preparation/search/total
timings. Each objective runs A*, Dijkstra and three independent native ABIT*
invocations. Native budgets are 1 s for real inputs and 0.25 s for fixtures;
preflight can prevent any search from starting. Finite native runs have no exposed
seed and do not establish continuous global optimality.

`summary.json` is written last and checksums `runs.json`. The reporter verifies
that checksum and unchanged input-manifest hashes, recomputes grouped summaries,
checks graph agreement, failure geometry and speed/provenance consistency, and
checks deterministic synthetic speed/altitude invariance. Saved final evidence:
[part5-evidence.json](part5-evidence.json). Full local records are retained at
`.cache/part5-full-v2/runs.json`; six research reports are checksummed in the evidence.
The initial development runs are not the reviewed evidence.

## Real Hannover results

The reviewed run contains **600 matrix records**: 360 real and 240 synthetic,
plus six separate research preflight reports. Whole-run wall time was 138.98 s.
Initial source preparation took 46.15 s at 100 m and 44.31 s at 120 m on this
Windows environment, while another backend regression was running. These are
observations, not isolated performance benchmarks.

| Exact catalog pair | Scenario | Matrix result | Additional endpoint findings |
|---|---|---|---|
| rheuma-podbi → mhh | Local | 120 unresolved records | Residential zone and control-zone applicability at origin |
| amedes-georg → mhh | Urban | 120 unresolved records | Authority-zone applicability at origin |
| limbach-lehrte → mhh | Cross-city | 120 unresolved records | Missing height on `way/486442105` at origin |

All three pairs share unresolved OSM source geometry (76 invalid/unsupported
constraint extents), temporary/NOTAM completeness and scenario applicability.
MHH additionally retains hospital/airfield applicability and an incompatible
vertical-reference question: native terrain uses NHN and is not silently treated
as MSL. The full source dataset also retains extensive missing building heights.
Selected point diagnostics do not stand in for full-route support.

All **360 real matrix records and six research checks return `unresolved_input`**
with no geometry and zero search duration. Sweeping 100/120 m, 100/250/500 m grid
spacing, 25/30/35 m/s and prepared-model reuse does not bypass endpoint preflight.
No real length, risk, objective or cruise time is invented. Real ABIT* invocations
are reported as preflight failures, not searched paths or stochastic performance
samples. No successful real regional search or flight permission is established.

## Synthetic algorithm and objective comparison

Fixtures use a complete, explicitly artificial EPSG:25832 region, exact artificial
endpoints, one scored hospital polygon, known low building height and assessed
zero background. A third fixture adds a hard wall spanning the initial boundary.
No real Hannover input is replaced or relaxed. The same regional planner and
algorithm implementations are used; only the synthetic constraint provider differs.

Every successful route is independently recomputed using direct segment/polygon
intersections, metric length, exact endpoints, boundary/obstacle checks and L/v;
the experiment validator does not call `RiskModel.evaluate` or the core checker.
All **170 successful records pass both core and experiment checks**. The other
records are 28 graph `no_path_on_grid` outcomes and 42 finite-budget native
timeouts. Every successful A*/Dijkstra pair agrees on the same graph objective.

| Fixture, 50 m graph | Weighted length (m) | Distance-only length (m) | Weighted-route risk | Distance-route risk | Weighted J | Distance-route J under 0.9/0.1 |
|---|---:|---:|---:|---:|---:|---:|
| Risk detour | 432.84 | 350.00 | ≈0 | 800.00 | 43.28 | 755.00 |
| Diagonal | 612.13 | 494.97 | ≈0 | 1131.37 | 61.21 | 1067.73 |
| Hard wall, expanded boundary | 574.26 | 574.26 | 0 | 0 | 57.43 | 57.43 |

Risk costs are ordinal score × metres, not probabilities. Tiny residuals near
1e-8 arise from coordinate transforms and are retained in JSON rather than rounded
to observed zero. Distance-only routes are independently scored for comparison;
this does not change the distance planner's objective.

Native weighted ABIT*, three fresh-batch runs per baseline:

| Fixture | Successful searches | Length range (m) | Objective range | Search time range (ms) |
|---|---:|---:|---:|---:|
| Risk detour | 3/3 | 437.04–453.77 | 43.70–45.38 | 253.90–255.28 |
| Diagonal | 3/3 | 588.00–616.92 | 58.80–61.69 | 254.92–261.12 |
| Hard wall, initial boundary | 0/3 | — | — | All runs time out |
| Hard wall, expanded boundary | 3/3 | 549.02–591.43 | 54.90–59.14 | 252.33–265.82 |

All objectives/variants also retain three native invocations and their outcomes,
budget, success rate, successful length/objective/runtime min/max/mean and wall
times in evidence. Continuous ABIT* may outperform a discretized graph; equality
of graph and continuous route lengths is not an acceptance requirement.

## Sensitivity, cache interpretation and limits

- **Altitude/speed:** deterministic fixture routes and objectives remain identical
  at 100/120 m and 25/30/35 m/s. Twelve graph/objective invariance groups pass;
  cruise times are independently checked as L/v with [L/35, L/25]. Native runs
  vary stochastically; speed is not interpreted as changing geometric cost.
- **Grid:** the risk-detour weighted lengths at 25/50/100 m are
  482.84/432.84/453.55 m; diagonal lengths are 647.49/612.13/612.13 m.
  Different resolutions construct non-nested graphs and endpoint connectors,
  so finer spacing is not assumed to produce a monotonically better objective.
- **Boundary:** the synthetic hard wall yields no graph path within the initial
  boundary and a validated detour after adding 100 m around it, with unchanged
  exact endpoints and obstacle. Native timeouts alone do not prove infeasibility.
- **Real expansion:** a 10,000 m detour allowance is computed for all eight sites.
  The retained study/terrain do not cover it. Original DIPUL pages, GHSL crop and
  terrain cannot be promoted to larger coverage just because the OSM PBF is larger.
  The result is `missing_source_coverage`, not a search failure or feasible detour.
  A separately acquired complete expanded snapshot is needed for real expanded
  routing; that route comparison remains unavailable.
- **Resources:** original-region candidate-cell upper bounds are 42,476 / 6,900 /
  1,740 at 100/250/500 m; expanded bounds are 97,639 / 15,756 / 3,978.
  The 10,000-cell limit remains unchanged. These are geometric estimates, not
  measured successful grid preparations; real endpoint preflight currently wins.
- **Caches:** baseline fresh/reused prepared-model batches are separate. Source
  preparation is measured once per altitude, then shared within a batch.
  `cold_equivalent_total_ms` is source cost + one solve, not a new source preparation
  measured on every row. OS caches are uncontrolled; every solve has a fresh motion
  cache and builds its graph again. No cached route is reused or claimed.

Fixed-AGL 2D planning does not establish terrain following or 3D clearance.
Takeoff, landing, wind, acceleration and turn dynamics remain unmodelled. GHSL
uses the retained 2020 population product at native resolution and never enters
the objective. Coverage, missing heights, geometry and time/vertical applicability
remain unresolved where unsupported. Successful fixtures cannot establish
full-region real runtime, legality or flight permission.

## Validation

- Full backend regression: **228 passed / one existing Windows permission skip**
  (100.85 s), including the first five new experiment checks.
- Final focused suite: **6 passed** (1.86 s), including the added speed metadata
  isolation test; Ruff lint and format checks pass for backend and both scripts.
- Reviewed offline matrix/report checks: 600 records, 170 independently validated
  successes, no successful-looking failure geometry, graph agreement and twelve
  deterministic speed/altitude groups pass; input manifest hashes unchanged.
- Frontend is unchanged; existing Part 4 browser evidence remains applicable.
  No frontend rerun or remote CI is claimed for this local experiment delivery.
