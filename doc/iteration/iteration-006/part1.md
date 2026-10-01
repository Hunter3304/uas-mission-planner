# Iteration 006 Part 1 — Metric building-risk weighted graph routing

User approved Part 1 on 2026-09-30 and requested the calculation rules under
`doc/rules/`. Milestone 6 / [Issue #56](https://github.com/Hunter3304/uas-mission-planner/issues/56)
were created before `feature/56-risk-weighted-routing`, based on `iteration/006`
from main `42db227`. Parts 2 and 3 remain deferred.

## Delivered behavior

The Python core reuses saved OSM classification and EPSG:25832, computes
centreline length times building score, takes maximum score in overlaps, and
optimizes `0.9 * risk_length_cost + 0.1 * length_m`. A*/Dijkstra share the same
assessed graph, constraints and endpoint costs. Output separates physical
length from objective, records assessment flags and source/config/rule identity,
and rechecks final segments. Verified snapshots are checked before cache use.

Point and complete segment checks share optional metric clearance, reject
partial overlap/boundary contact and preserve unresolved constraints. Invalid
building polygons cause explicit errors; non-polygon footprints and missing
numeric scores remain unresolved rather than being silently inferred.

Current API/CLI/UI retain distance-only defaults. Use the offline Python
`plan_risk_route` entry point documented in the
[calculation rules](../../rules/risk-weighted-routing.md).
Background 0 in the example is an explicit research assumption, not observed
zero risk in all uncovered space. Rule version: `building-length-risk-v1`;
distance collision policy version: `distance-grid-v2`.

## Validation and practical limits

Local gate: 139 Python tests passed, one Windows symlink-permission skip;
Ruff lint/format, frontend ESLint and production build passed. Analytical tests
cover 100 m with 20 m at score 4 (R=80, J=82), subdivision invariance, overlapping
and duplicate regions, missing support, zero-length routes, exact connectors,
positive point/motion clearance (including conservative circular approximation),
weighted A* versus Dijkstra, source/cache
invalidation, result provenance isolation, cost overflow and unchanged
conservative real-data outcomes. Six real-stack browser checks passed. Windows
test-server teardown required stopping the servers started by this test run;
Playwright subsequently exited successfully with all six cases passing.

Real saved Braunschweig snapshot at 100 m remains `unresolved_input`. Its OSM
checksum is `060bc0e7ea5f206e8e1099125bcf3b154c2a632dbb7fa1e5295a9042fa5ef4c9`;
four in-boundary building-tagged objects have unsupported non-polygon geometry.
This is recorded separately from unresolved real restriction coverage. There
is no validated real route or inferred building footprint.

The existing synthetic snapshot at 100 m returns `no_path_on_grid`; this is a
resolution-limited graph result, not proven continuous-space infeasibility.
Its OSM checksum is `28b1e015e85760c64d99154756978775aef4ca87fa6c199b7faba9a669fa0248`.

At 50 m the saved synthetic snapshot succeeds with both A* and Dijkstra:
length 276.22166570077525 m, risk-length cost 71.90458069004399,
objective 92.33628919111712. Both retain the explicit background assumption;
the contributing building ID is `way/3`. This sample verifies consistent scoring;
the separate analytical high-risk-crossing fixture verifies lower-risk detouring.

Part 1 is implemented and locally validated. On 2026-10-01 the user explicitly
authorized pushing and merging to `Hunter3304/uas-mission-planner`, resolving
the previous publication approval block. Implementation commit `9dac74d` is
pushed and [feature PR #57](https://github.com/Hunter3304/uas-mission-planner/pull/57)
targets `iteration/006`. CI, integration and verified feature-branch cleanup
are in progress.

The pre-existing 51-line real-route HANDOFF addition is retained locally and
excluded from this task's commit. Local changes are confined to Part 1 core,
tests, calculation rules and delivery/planning documentation.
No OMPL install, new real acquisition, population optimization or weighted UI
controls are included in this part.
