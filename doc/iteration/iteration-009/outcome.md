# Iteration 009 — Real Hannover research route recovery

Date: 2026-10-08 (Europe/Berlin). Milestone 8 / Issue #79.
Approved plan: `doc/plan/iteration-009.md`. Local implementation and acceptance
complete. Feature PR #80 merged into `iteration/009` at `4b3c278` after Linux,
Windows and frontend CI passed in run `37809752912`. Issue #79 is closed and its
verified merged feature branch was deleted locally/remotely. Main PR #81 merged
at `329ca6c` after its separate CI gate passed. Merged-main run `37810854105` also
passed Linux Python, Windows Python and frontend. `iteration/009` and all
historical source/experiment work are retained.

## Supplemental closeout and known limitations (2026-10-11)

The user authorized publishing the previously retained local street-basemap
change and updated diagnostics through the same milestone/iteration workflow.
Assigned Issue #82 precedes `feature/iteration009-basemap-handoff`, based on
`iteration/009` fast-forwarded to main `329ca6c`. The regional map now supports
optional online OpenStreetMap street tiles, a tile-failure explanation and an
offline display of retained boundaries/locations/loaded overlays. The browser
test checks tile requests, toggling, errors and the existing canvas renderer.
No backend or original source data is changed by this supplemental delivery.
Fresh local validation passes frontend lint/build, 13 mocked browser cases
(8.8 s) and 12 isolated real-stack smoke cases (30.4 s), with clean runner exits.
Supplemental feature and main PRs require successful Linux/Windows/frontend CI.

User inspection found a large-layer problem not covered by the earlier real-route
browser acceptance. Regional `/features` still fills all 1,481 tag keys for each
of 326,334 objects: 483,300,654 property positions. A read-only 256-object sample
estimates about 11 GiB of properties JSON alone, before geometry. A running user
backend occupied about 18 GiB working-set memory while the OSM overlay was loading,
and route requests reached the frontend's 120-second timeout. The sample is not a
completed full-response benchmark. Sparse regional serialization, viewport-based
payloads/rendering, preparation reuse and cooperative request cancellation remain
follow-up work. Avoid the full OSM overlay when reproducing route acceptance.

OSM/DIPUL/GHSL study files (0.674 decimal GB) and complete native terrain
(1.315 GB) are already local, totaling about 1.99 GB. DIPUL is integrated, with
31 saved layers and 324 original features; applicability/completeness remain
explicitly uncertain. Online street tiles are independent of these local sources.
Terrain-only directories are incorrectly marked `needs attention` by the generic
OSM dataset catalog; select `hannover-part1-v4` in Saved dataset and the complete
terrain in the dedicated Terrain dataset selector.

The user explicitly deferred mission-end automation and duration feasibility
enforcement. Current interval validation only requires positive duration, at most
24 hours, and a valid Berlin offset. Cruise duration is computed separately and
is not compared with the selected interval. A successful route may exceed that
window; takeoff/landing/waiting are also outside the cruise-only estimate.

## Problem and resulting behavior

Empty required scenario fields prevented browser submission. After submission,
76 unsupported/invalid building extents blocked every regional point globally,
including research mode. Whole-region risk preparation also consumed much of
the request timeout, and a single containing-cell connector could cross unscored
support even when the exact endpoint was usable.

Research mode now explicitly opts into a derived geometry model, a configurable
missing-height estimate (UI default 30 m), and the existing zone/temporary-source
assumptions. Original sources and strict validation remain intact. Recoverable
polygon parts use `make_valid`; non-polygon or residual extents are excluded with
a configured uncertainty buffer (UI 20 m). Unlocatable geometry remains an explicit
region-wide incomplete-verification assumption, not silently discarded evidence.
Known tall buildings, missing terrain, known zone prohibitions, boundaries,
clearance and unscored polygon costs still exclude travel.

Search begins within a catalog-pair corridor (default 1,000 m margin), expands on
graph failure, and remains within retained regional coverage. Cost preparation
uses the same declared corridor. Nearby connectors undergo full constraint and
cost checks and retain exact endpoint coordinates. Explicit launch/landing
overrides preserve catalog coordinates separately and appear in exports.
The graph's 10,000-cell and 30-second preparation limits remain in effect.
An eight-reader request-scoped terrain cache reduces repeated TIFF opens;
undecodable native pixels become unknown support rather than a server traceback.
API route preparation closes its native readers on both success and failure.

Date/time selectors use Europe/Berlin offsets, reject reversed/overlong intervals
and ambiguous or missing DST-transition wall times. Terrain selection lists saved
complete manifests; selected bytes are still fully verified during preparation.
Research assumptions, failures and displayed-result exports remain visible.
Scenario layer colors retain strict inspection semantics; they are not the
research route's permissibility classification or a flight authorization.

## Verified real results

All results use original `hannover-part1-v4` / `hannover-part2-terrain-v1`, the
retained engineering interval 2026-10-07 10:00–10:15 +02:00, 100 m AGL, 30 m/s,
zero clearance, background assumption 0 and weights 0.9/0.1. These historical
times reproduce engineering evidence, not a current flight schedule.

| Exact catalog pair | Algorithm/grid | Length (m) | Objective | Cruise (s) |
|---|---|---:|---:|---:|
| rheuma-podbi → mhh | A*, 250 m | 3,715.59 | 1,453.49 | 123.9 |
| amedes-georg → mhh | A*, 500 m | 8,431.17 | 3,843.11 | 281.0 |
| limbach-lehrte → mhh | A*, 500 m | 18,096.34 | 2,703.61 | 603.2 |

The eight-case final run has seven independently accepted successes and one
expected strict `unresolved_input`. Primary weighted A*/Dijkstra agree exactly
on length/objective. Primary distance-only A* returns 2,840.88 m. The final
3-second ABIT* run succeeds at 3,453.39 m / objective 1,776.29; finite-budget
native paths vary and do not establish global optimality. Coarser grids can
produce longer/more costly paths; the primary 500 m run is 4,747.25 m.

The separate validator never calls `RegionalPlanner.check`, `plan_route` or
`RiskModel.evaluate`. It recomputes metric length, exact endpoints, complete
boundary support, intersections with known obstacles/uncertain extents, native
terrain support, max-overlap building costs and cruise estimates. Every successful
case passes all eight checks. Models still depend on explicit research assumptions.

Retained local evidence: `.cache/iteration009-final-v2/evidence.json` and its eight
checksummed GeoJSON files. All source snapshots and historical Part 5 evidence are
preserved outside Git. Initial diagnostic attempts remain separate from final evidence.
Source verification/preparation took 43.25 s while other checks were running;
subsequent prepared-model solves took approximately 6–24 s. These are observations,
not isolated performance benchmarks.

## Validation and operation

- Backend: 229 passed / one existing Windows permission skip, 85.89 s.
- Mocked browser: 13 passed, including DST, interval validation, research request
  fields, explicit endpoint selection, result invalidation and exports.
- Real-stack browser smoke: 12 passed with clean runner exit, 30.1 s.
- Real Hannover browser: success, exact endpoints and displayed export verified;
  mobile fits 390 px, no page errors, planning/export wall time 53.15 s. Screenshots,
  export and evidence: `.cache/iteration009-ui-v1/`.
- Ruff lint/format, frontend ESLint/TypeScript/production build pass.

Restart the backend and refresh the frontend. Select `hannover-part1-v4`, terrain
`hannover-part2-terrain-v1`, `research`, A*, `risk`, background 0, height estimate
30 m and grid 250 m for the primary pair (500 m for the other pairs). Enter explicit
scenario dates using the date selectors. Review the visible assumptions before
planning. Original addresses remain exact unless the override checkbox is selected.

Reproduce core evidence in a new output directory:

```powershell
backend/.venv/Scripts/python.exe doc/experiments/iteration-009/verify-real-routes.py --output .cache/iteration009-new
```

For real UI verification, start an isolated backend on port 8012 and a frontend
on 5176 with `UAS_API_URL=http://127.0.0.1:8012`, then run:

```powershell
node doc/experiments/iteration-009/verify-real-ui.mjs .cache/iteration009-ui-new
```

Strict mode still stops on unresolved source geometry/applicability; research
success does not make those questions resolved. Height estimates are not measured
building heights. NHN is never equated with MSL. Population remains inspection-only.
No new source acquisition, physical launch-site verification, flight permission,
terrain-following/3D feasibility or guaranteed ABIT* success is claimed.
