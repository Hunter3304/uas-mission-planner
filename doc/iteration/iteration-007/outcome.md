# Iteration 007 — Parts 1 and 2

Date: 2026-10-03. Feature-branch publication authorized on 2026-10-04.

## Behavior

Strict remains the default. Readiness checks precede native setup and timeout,
with global source reasons and local endpoint/connector reasons. Invalid endpoints
remain distinct. ABIT* search budgets exclude grid/risk preparation; results report
preparation_ms, planner_ms and total runtime_ms. Native setup, callbacks and final
validation remain cooperative; the browser timeout is not a hard server deadline.

Research explicitly assumes unresolved DIPUL coverage and applicability do not
exclude travel. The real OSM snapshot also contains four point building objects;
research integrates polygon footprints only, retaining their unsupported geometry
IDs and an explicit policy in risk provenance. Strict risk behavior is unchanged.
Unscored polygon risk is still unknown even with background zero. Known blocked
geometry, unknown terrain regions, boundaries, clearance and graph corner checks
remain enforced. Original source payloads and cached strict grids are unchanged.

The UI shows mode, historical mission interval, incomplete verification, crossed
uncertain-zone count and timing. Export and comparison retain mode and assumptions;
parameter/mode changes clear displayed results. Source overlays and grid continue
showing the strict assessment, explained beside the mode controls.

## Real-source results

Dataset: braunschweig-part1-v2; 50 m cells; weighted building risk; background 0;
weights 0.9/0.1; safety distance 0; ABIT* search budget 3 s. Source checksums verified.

Screenshot endpoints (10.505, 52.254) to (10.54, 52.255):
- All three strict planners: unresolved_input, no native search.
- Research ABIT*: exact computational route, length 3,426.855 m, objective 677.194.
- Research grid planners: start connector crosses unscored polygon way/49170599.
  Final implementation reports this local reason before graph search.

Nearby connected grid-centre endpoints:
- Start: (10.504709863937636, 52.2537613755198).
- End: (10.539918336772804, 52.25510557964907).
- Research A* and Dijkstra: success, length 2,997.056 m, objective 316.333;
  integrated score-length 18.474. Costs agree within floating-point tolerance.
- Research ABIT*: success, length 3,489.754 m, objective 680.693 in this run.
  Native finite-budget results are stochastic and are not guaranteed to outperform
  a grid route or find an exact path on every run.

Compact measurements: real-validation.json and connected-real-validation.json.
Independent endpoint, segment constraint and cost rechecks: independent-verification.json.
Full local route/provenance exports are under .cache/iteration007-*.geojson (ignored).
The measurement files contain the successful runtime evidence and original graph
failure; independent-verification.json records the refined connector explanation.

## Verification

- Complete backend regression after research risk policy: 167 passed, one existing
  Windows symlink-permission skip. After connector readiness refinement, affected
  routing/risk/native/planner tests: 71 passed; research suite with the added
  connector regression: 9 passed.
- Ruff lint/format, frontend ESLint and production build passed.
- Chrome mocked UI: 9 passed. Actual API Chrome smoke: 12 passed, including mode,
  readiness, export and comparison. Run with --workers=1 alongside large real-data
  experiments; six-worker run showed preparation timing contention. Test server
  shutdown stalled in this Windows sandbox; only the identified test servers were
  stopped, after which both Playwright commands finished with exit code 0.

## Deferred

No current source acquisition, temporary-restriction/NOTAM verification, legal
rules, new mission date, population fusion, full 3D clearance or flight permission.
The saved 2026-10-01 mission interval remains explicit historical scenario data.

## Authorized cleanup (2026-10-04)

Removed obsolete small OSM demo, incomplete first acquisition, duplicate OSM-only
dataset (identical GeoPackage SHA-256 to v2/osm), and superseded Iteration 005 draft.
Kept real v2, offline-sample, synthetic-route-demo and synthetic-risk-demo because
the three fixtures exercise distinct functionality. Local datasets are ignored by
Git; their deletion cleans the local explorer, not a remote data repository.
