# UAS Mission Planner — Handoff

## Current status

### Iteration 008 Part 2 integration authorized (2026-10-06)

- User accepted Part 2 and authorized final review, commit/push and integration
  through feature -> iteration/008 -> main PRs after successful CI.
- Final review fixed native GHSL point/line queries on cell edges to include both
  neighbouring cells; added an independent boundary regression. Area-weighted region
  and corridor results remain unchanged. Required checks run on the reviewed source.
- Final reviewed backend regression: 209 passed / one existing Windows permission
  skip (63.38 s); Ruff lint/format pass. Previous frontend lint/build and offline
  source evidence remain applicable. Remote Windows/Linux/frontend CI gates both PRs.
- Keep original study/terrain data local and excluded from Git. Deliver Part 2 only;
  Parts 3–5 remain deferred. Retain iteration/008 and clean the merged feature branch
  after confirming integration/synchronization. Earlier local-only notes are history.

### Iteration 008 Part 2 local delivery (2026-10-06)

- User authorized Part 2 implementation. Milestone 7 / Issue #69 was created
  before `feature/69-regional-constraints`, based on existing `iteration/008`.
  Part 1 main delivery is confirmed locally at PR #68 merge `cea5b0e`.
- Implemented offline indexed fixed-AGL constraints, explicit timed scenario,
  building-height/clearance policies, original geometry diagnostics, compatible
  vertical-reference checks and source-signature/evidence-scoped zone decisions.
  Point, full motion, polyline and endpoint connectors share the same checks.
- Native terrain: bounded 2 km requests, up to three workers, checksummed WCS
  originals/metadata, explicit verified resume and complete-marker gating. Full
  `data/hannover-part2-terrain-v1` completed 120/120 tiles (1,314,968,709 TIFF bytes),
  covering the complete study region. A server 502 after 86 tiles was recovered
  with two-worker resume. Earlier MHH one-kilometre probe remains separate evidence.
- Complete conservative terrain windows retain NoData and 4,000,000-pixel query
  limits; NHN is not implicitly MSL. Known terrain does not establish 3D clearance.
- GHSL native region/corridor/crossed-cell queries and SVG/cell-GeoJSON inspection
  are independent of routing cost. Existing soft building max-overlap/background
  semantics and risk/distance weights 0.9/0.1 are preserved through `RiskModel`.
- CLI: `terrain-fetch`, `study-prepare`, `study-check`, `study-population`.
  Read-only API: `/api/datasets/{id}/study` and `/study/population`. Frontend
  selectors/layer controls and regional algorithm integration remain Parts 3/4.
- 208 backend passes / one existing Windows permission skip; 21 new cases also
  passed after final bounds checks. Ruff, ESLint and frontend build passed. Native
  SVG rendered/inspected in installed Chrome without adding a dependency.
- Offline real verification forbade network access: 100/120 m scenarios (~37.66 /
  37.59 s), all eight addresses and three representative motions have known complete
  terrain support. All remain unresolved due to retained building/source uncertainty.
  Source reports one 282 m building, 162,010 polygon buildings without usable height,
  13 invalid geometries, 10 collections and 67 non-polygon building diagnostics.
- Regional population estimate ~666,980 (2020, uniform native-cell weighting);
  41,725 intersecting native cells, 20,415 known zeros, no missing support. Counts
  and native-plane area are distinct from full crop/geodesic study-area totals.
- Rules: `doc/rules/regional-constraints.md`; outcome/evidence:
  `doc/iteration/iteration-008/part2.md` / `part2-evidence.json`; operating guide
  and offline verification script in `doc/experiments/iteration-008/`.
- Part 2 is implemented locally, with no commit/push/PR/merge requested here.
  Issue #69 remains open for delivery. Original Part 1 study, terrain files and
  caches remain local and excluded from Git. Parts 3–5 remain deferred. Earlier
  Part 2 deferred notes below are historical.

### Iteration 008 Part 1 integration delivery (2026-10-06)

- PR #67 merged Part 1 into `iteration/008` at `f270ed7` after Windows/Linux
  backend and frontend CI all passed (run `37450930456`). Issue #66 is closed.
- Initial Linux CI exposed a few-ULP coordinate comparison; the regression now
  uses 1e-10 degree absolute tolerance while retaining independent coverage checks.
  Production code and saved coordinates were unchanged by this fix.
- Merged feature branch `feature/66-hannover-acquisition` deleted locally/remotely;
  fetch/prune, branch -a and ls-remote verified cleanup. Retain `iteration/008`.
- Main delivery is tracked by PR #68 and requires all integration checks to pass.
  The final main merge commit and CI results are reported in the final chat response.
- Part 1 is complete; Parts 2–5 remain deferred. Local source snapshots remain
  unchanged and excluded from Git. Earlier authorization/pending notes are history.


### Iteration 008 Part 1 integration authorized (2026-10-06)

- User authorized review and merging the published Part 1 into main through the
  existing feature -> iteration -> main PR workflow. Parts 2–5 remain deferred.
- Feature head before integration documentation: `e791783`.
- CI must pass on each PR before merge. Retain `iteration/008` as history and
  remove the feature branch only after confirming its merge and synchronization.
- Final PR/merge commits and cleanup checks are reported in the final chat response.
  Earlier publication-only restrictions below are historical.


### Iteration 008 Part 1 publication authorized (2026-10-06)

- User accepted Part 1 and explicitly authorized its commit and remote push.
- Publication branch: `feature/66-hannover-acquisition`; include implementation,
  tests, English plan, workflow guide and recorded validation evidence.
- Retain local source datasets and download caches outside Git. No application
  changes since the verified 187-pass delivery; only publication records updated.
- Push result and remote-head verification are reported in the final chat response.
  Pull request creation and integration merges are not included in this request.
- Earlier local-only statements below are historical delivery records.


### Iteration 008 Part 1 local delivery (2026-10-05)

- User authorized Part 1 implementation only. Milestone 7 / Issue #66 precede
  `iteration/008` and `feature/66-hannover-acquisition`; no commit/push/PR/merge.
- Completed `data/hannover-part1-v4`: eight verified address points, a 5 km detour
  allowance and 411.74 km² Hannover/Lehrte region. Default configuration and guide
  are in `doc/experiments/iteration-008/`; evidence in
  `doc/iteration/iteration-008/part1.md` and `part1-evidence.json`.
- `study-fetch/inspect/rebuild/configure` acquire, verify, rebuild offline and
  regenerate boundaries. Regional scope is explicit; legacy 25 km² queries remain.
- Overpass partial acquisition encountered repeated 504/timeouts. Optional bounded
  requests, recorded subdivisions and verified resume remain supported. Default
  OSM input is dated Geofabrik Niedersachsen PBF, with publisher MD5, SHA-256,
  original extract polygon and local GDAL selection; no new runtime dependency.
- Regional OSM tags are sparse JSON objects, not a wide null-filled dataframe.
  Real snapshot: 326,334 objects, 1,481 tag keys; 13 invalid geometries and 10
  GeometryCollections remain explicitly recorded for Part 2 treatment.
- DIPUL: all 31 advertised layers, 324 features; temporary layer returned zero,
  without claiming temporal/legal/NOTAM completeness. GHSL crop: 43,605 native
  cells, 21,935 known zeros, no NoData; values/masks match original ZIP exactly.
- Offline inspection verifies all 70 files. Raw-receipt offline rebuild succeeded.
  Regression: 187 passed / one existing Windows permission skip; Ruff, ESLint and
  frontend build passed. Evidence is local; source payloads remain excluded from Git.
- Part 2 must prepare constraints and bounded terrain/vertical-reference support.
  The source study is not yet a flight experiment or route-ready UI dataset.
  Parts 2–5 remain deferred; preserve inherited building risk/distance weights
  0.9/0.1. Configured altitude/speed: 100 m AGL / 30 m/s, ranges 100–120 / 25–35.
- All version-controlled iteration/project documentation is English.

### Iteration 008 planning draft (2026-10-05)

- Draft: `doc/plan/iteration-008.md`; pending user review, implementation not started.
- Scope: predefined Hannover/Lehrte region covering all eight supplied sites plus
  detour space; reproducible OSM/DIPUL/GHSL snapshots; fixed-altitude 2D routing
  at 100–120 m and constant cruise speed 25–35 m/s; listed origins/destinations.
- Retain the approved building risk/distance objective (0.9/0.1) in A*, Dijkstra
  and ABIT*. Distance-only is a comparison baseline. GHSL inspection is included;
  population costs/fusion remain deferred.
- User reaffirmed that all version-controlled iteration/project documents must
  be English. Draft translated accordingly; Chinese review text stays in chat.
- Iteration 007 historical plan preserved. No acquisition, application changes,
  GitHub objects, commit, push or merge performed during this planning session.

### Iteration 007 Parts 1/2 local delivery (2026-10-03)

- User authorized writing the Iteration 007 plan and implementing Parts 1/2 only.
- Shared planner adds explicit strict/research mode, readiness before native setup,
  separate preparation/planner timing and full ABIT* search budget after preparation.
- Research retains strict source data/cache integrity, obstacles, unknown terrain,
  boundaries, clearance and unscored polygon support. It explicitly assumes unresolved
  DIPUL applicability and polygon-only building risk; omitted non-polygon IDs remain
  in risk provenance. CLI/API/UI/comparisons/export carry the selected mode.
- Real 50 m Braunschweig weighted A*/Dijkstra demonstration succeeded (~2,997 m,
  objective ~316.333). Original screenshot endpoints also succeeded with native ABIT*
  at 3 s; their graph start connector crosses unscored way/49170599 and is explained.
- Strict real inputs remain unresolved. Source acquisition/legal applicability,
  updated mission scheduling and Part 3 are deferred. Saved dates are historical.
- Plan: doc/plan/iteration-007.md; evidence: doc/iteration/iteration-007/outcome.md.
- Remote feature-branch publication authorized on 2026-10-04. Local obsolete datasets
  braunschweig-demo, incomplete braunschweig-part1 and duplicated braunschweig-part1-osm
  removed; the latter GeoPackage matched v2/osm SHA-256 exactly. Kept v2 and the three
  independently useful synthetic/offline fixtures. Superseded Iteration 005 draft removed.
  Publication result is recorded in the final chat response. No PR or merge requested.


### Main delivery completed (2026-10-03)

- Accepted native planning, Part 3 controls and collapsible UI delivered through
  PR #62 -> PR #63 -> PR #64. Main merge commit: 31f4930.
- PR #63 and #64 Windows/Linux Python and frontend CI passed before merge.
- Issues #59, #60 and #61 verified closed as completed after main merge.
- feature/59-ompl-abitstar, feature/60-planner-controls and
  feature/61-collapsible-panels removed locally; the published feature/60 and
  feature/61 branches removed remotely. Remote refs pruned. iteration/006 retained.
- Local workspace synchronized to main, with no application changes during
  integration. Earlier pending-state sections below are historical.


### Accepted delivery integration (2026-10-03)

- User accepted the implementation and explicitly authorized remote merge.
- PR #62 merged UI into the planner branch at 65c7580; its Windows/Linux Python
  and frontend CI passed. UI feature branch deleted locally/remotely.
- PR #63 integrates native Part 2, Part 3 controls and accepted UI into
  iteration/006 before the final main delivery PR. Earlier pending/uncommitted
  statements below are historical snapshots.
- No runtime behavior changed during integration; validation is recorded in
  part3-validation.md and ui-panels.md. Retain iteration branches as history.


### Explorer panel refinement (2026-10-02)

- Issue #61, assigned to Hunter3304 in Milestone 6, tracks the user-requested UI
  refinement. Branch `feature/61-collapsible-panels` builds on the published
  `feature/60-planner-controls`; parent integration is still pending.
- Six panels fold independently while the map remains available. Feature panels
  are always present, initially collapsed, manually expandable and both open on
  selection of any feature. Clearing selection collapses them.
- Distance hides only the three risk inputs; switching objectives restores
  values. Folding preserves inputs/results.
- ESLint and production build passed; 9 mocked browser tests and all 11 real API
  smoke tests passed. Mobile screenshot reviewed with no horizontal overflow.
- Evidence and operation: `doc/iteration/iteration-006/ui-panels.md`.
- UI changes are prepared for a separate PR into the parent planner branch; no
  integration merge or branch deletion has been performed.


### Feature-branch publication authorized (2026-10-02)

- User requested commit and remote push of the reviewed local implementation.
  Publication branch: `feature/60-planner-controls`, including the retained Part 2
  native dependency/adapter and Part 3 controls, comparisons, tests and evidence.
- PR creation and integration merges are not part of this push request. Earlier
  local/uncommitted statements below describe the 2026-10-01 validation state.

### Iteration 006 Part 3 local implementation (2026-10-01, latest)

- User authorized Part 3 and explicitly approved Issue #60 creation/assignment
  to Hunter3304 in Milestone 6. `feature/60-planner-controls` preserves all
  uncommitted Part 2 changes on the existing iteration/006 base.
- Shared planner controls power compatible CLI/API distance/risk requests and
  map controls/status/assumptions. UI exports the displayed snapshot without
  another solve; changing parameters invalidates results. Mobile reports wrap.
- Synthetic low-risk demo and four-planner comparisons independently verify
  endpoints/constraints/costs; report bounded native repeats, distributions,
  environment versions and unsupported per-task seeds.
- Native callback cycles fixed with weak ownership while retaining OMPL metric
  arithmetic. CLI native stdout is JSON, tested in a bounded subprocess.
- Measurements and separate real unresolved/timeout evidence are under
  `doc/iteration/iteration-006/`; see `part3.md` for operation and limitations.
- Validation: full backend regression 158 passed / 1 existing Windows symlink
  permission skip (44.16 s); after independent requested-endpoint verification
  tightening, all 8 planner-control tests passed (21.24 s), including injected
  cost/endpoint corruption. Ruff check/format passed. Frontend ESLint/build,
  9 mocked Chrome checks and 9 real API Chrome smoke checks passed (30.5 s).
  Detailed commands/evidence: `doc/iteration/iteration-006/part3-validation.md`.
- Changes remain local/uncommitted. No push, PR, integration merge, acquisition
  or branch deletion performed. Remote CI, Linux native runtime and a clean
  second Windows host remain unverified. Earlier sections preserve history.

### Iteration 006 Part 2 implementation (2026-10-01, latest)

- User resumed Part 2 after the verified native Windows route and requested
  README dependency instructions. Issue #59 created in Milestone 6 before
  `feature/59-ompl-abitstar`; iteration/006 fast-forwarded to main e54e245.
- Implemented `core/abitstar.py`: official C++ ABIT*, per-task native setup and
  callbacks, shared metric geometry/risk costs and admissible heuristics,
  cooperative budget/cancellation, explicit exact/approximate/timeout/unresolved/
  unavailable/failure outcomes, full final revalidation and cost recomputation.
  Saved-data entry point: `plan_risk_route(..., algorithm="abitstar")`.
- Optional `ompl-windows` extra now pins repository wheel `2.0.1+uas.1` by hash
  in uv.lock. Installed into backend venv. Wheel is ~4.7 MB, includes Boost DLL
  and licenses; vendor build-info and complete source patch record provenance.
  README records dependencies and `--extra ompl-windows` installation/use.
- Local validation: 151 backend passes and one existing Windows permission skip;
  Ruff check/format, frontend ESLint/build and nine mocked Chrome checks passed.
  Twelve new tests exercise actual native ABIT* and failure/concurrency contracts.
  Detailed validation/status in doc/iteration/iteration-006/part2.md.
  CI configured to exercise native Windows tests while retaining Linux baseline;
  remote CI, Linux ABIT* and a second clean Windows host remain unverified.
- Local changes are not committed/pushed/merged. Preserve all earlier unrelated
  HANDOFF additions. No Part 3 controls or real-data acquisition implemented.

### Official OMPL native Windows route (2026-10-01, latest decision)

- User explicitly deferred native Python ABIT* and requested plan revision first,
  then native Windows verification of official OMPL. The revised iteration-006
  plan supersedes both the Python route and earlier WSL proposal below.
- Verification record: `doc/iteration/iteration-006/part2-windows-verification.md`.
  Official 2.0.1 source pinned to `c509861210a63ec962bbec72c52823abc16b102e`;
  Nanobind submodules and build helpers prepared only under
  `D:/Aostfalia/tmp/ompl-windows-probe`. Project dependencies/venv unchanged.
- Actual CMake preflight failed for both VS 2022 (no Visual Studio instance)
  and Ninja (no C++ compiler). This is missing tooling, not demonstrated
  incompatibility of OMPL with Windows.
- Source audit confirms official C++ ABITstar exists but Python ABITstar is not
  registered in 2.0.1. The motion-validator last-valid overload also needs
  verification/repair. Binding patches are now compiled and runtime-tested.
- User explicitly approved MSVC/SDK installation. Microsoft-signed Build Tools
  installer returned 0 through UAC elevation; VS 2022 17.14.37710.0, MSVC
  14.44.35207 and SDK 10.0.26100.0 installed. No automatic reboot. Isolated
  vcpkg dependencies built successfully. Official C++ core and patched Python
  3.13 x64 extension compiled; wheel built and installed offline into a new
  isolated environment. ABIT* exact obstacle-detour solve passed in 3.0003 s,
  with custom geometry/cost/heuristic callbacks, last-valid checks, independent
  path/cost validation and immediate cancellation (0.000084 s).
- Patches, build/probe scripts, result and artifact SHA256 saved under
  `doc/iteration/iteration-006/windows-probe`; README now documents the added
  native build/runtime dependencies. Application venv and lock remain unchanged.
  Linux runtime and a second clean Windows machine remain unverified.
- Part 2 remains incomplete; no application adapter, new OS runtime, commit,
  push or merge. Preserve historical investigation notes and unrelated edits.

### Native Python ABIT* decision and survey (2026-10-01)

- User declined Linux runtime setup and explicitly authorized native Python
  ABIT*, requesting discovery of validated reusable implementations first.
  This supersedes the pending WSL proposal below; no runtime approval is needed
  for the selected native Python implementation. Part 3 remains deferred.
- Survey: `doc/iteration/iteration-006/part2-python-survey.md`. Reviewed three
  public Python candidates and academic Python baseline evidence. No reviewed
  candidate establishes a validated drop-in risk-weighted ABIT* implementation.
- Reproduced robotics-study/navigation_basic's six ABIT* tests on Windows Python
  3.13.13: 6 passed in 1.20 s with `-X utf8`; default GBK decoding fails before
  algorithm execution. Isolated checkout at `D:/Aostfalia/tmp/abit-research-navigation`,
  revision `a98698104edf66329a1fa5c4d6b4e07dc4397903`. No package installed.
- That candidate has simplified scheduling, distance-only objective, no time
  budget/cancellation and no identified redistribution license. Do not vendor it
  or claim formal correctness from six tests. Implement independently from the
  original ABIT* specification and reuse Part 1 cost/constraint functions.
- Plan updated for the explicit native Python decision. Application implementation
  remains outstanding; issue assignment must precede the Part 2 feature branch.

### Iteration 006 Part 2 dependency gate (2026-10-01)

- User authorized Part 2 implementation. Local main is `e54e245`, including
  merged Part 1 integration PR #58. Part 3 remains deferred.
- Actual native Windows CPython 3.13.13 OMPL 2.0.1 binary-install dry-run failed:
  no matching `win_amd64` wheel. Linux x86-64 cross-platform dry-run resolves,
  but actual Linux imports/ABIT* callbacks/solving have not been executed.
- No Docker executable found; WSL reports that it is not installed. No new
  runtime, package dependency, lockfile change or algorithm adapter was installed.
- Per the approved plan's dependency gate, prepared concrete WSL 2 / Ubuntu
  24.04 / Python 3.13.13 / OMPL 2.0.1 proposal for review in
  `doc/iteration/iteration-006/part2-runtime-gate.md`. Await runtime approval
  before host installation; Part 2 is not complete. Create/assign its issue
  before creating a feature branch when implementation resumes.
- Preserved pre-existing HANDOFF edits; this investigation is local documentation
  only, with no commit, push, PR or merge. Application code is unchanged.

### Open work — Real Braunschweig route validation (2026-09-30)

Part 3's search/UI/export implementation is delivered, but a validated route on
the real `braunschweig-part1-v2` data has **not** been achieved. The user requested
that this unfinished real-data status be recorded for continuation.

- The saved DIPUL snapshot contains only control zones, railway facilities,
  federal roads and nature reserves. It does not contain the temporary operating
  restriction layer. The existing global "Temporary restriction coverage
  unverified" reason is a preparation-policy uncertainty, not an observed ban
  across Braunschweig. Changing endpoints alone cannot bypass it: all real
  connections remain excluded by `block_unresolved`.
- Mission interval: 2026-10-01 10:00–10:15 Europe/Berlin, equivalent to
  08:00–08:15 UTC, civil scenario, 60 m AGL. No finding of "no applicable
  temporary restrictions" has been established for this interval and area.
- Next: verify current DIPUL capabilities/schema, query bounded temporary
  restriction geometry and inspect effective dates, activation schedules,
  vertical limits and applicability. Official documentation lists
  `dipul:temporaere_betriebseinschraenkungen` and
  `dipul:inaktive_temporaere_betriebseinschraenkungen`; the saved capabilities
  confirmed the former only. Verify the latter's actual availability and semantics
  before claiming coverage of inactive/future restrictions. Include all relevant
  published restrictions overlapping the mission interval, not merely those
  active at download time.
- Cross-check with an official DFS NOTAM briefing and relevant AIP supplements
  for the area/time/height. Preserve original responses, briefing references,
  retrieval time, query scope, source versions and checksums. Any coverage finding
  is limited to information published at the time of checking; refresh near the
  mission. This session inspected documentation and existing payloads only;
  temporary-layer acquisition, NOTAM verification and time-applicability
  implementation remain unfinished.
- Resolve the independent static-zone legal/scenario conditions and MSL terrain
  profile limitations as well. Verifying temporary coverage alone does not make
  every zone or connection permitted. Extend the explicit constraint model,
  test time/height interpretations, then select connected real endpoints and
  revalidate the final route. Do not silently mark unknown inputs permitted or
  promote a synthetic route to a real-source validated result.
- Official references: [DIPUL WFS/WMS layers](https://www.dipul.de/homepage/de/informationen/geografische-gebiete/wfs-wms/),
  [temporary restrictions](https://www.dipul.de/homepage/de/temporaere-betriebseinschraenkungen/),
  [DFS NOTAM guide](https://www.dfs.de/homepage/de/medien/ifr-vfr-informationen/vfr-informationen/21-10-2022-notam-von-a-bis-z/2823-notam-heftchen-neu-2022-web-ds.pdf?cid=hmg).

`synthetic-route-demo` occupies the geographic rectangle west 10.519, south
52.269, east 10.522, north 52.272 (EPSG:4326) in Braunschweig: approximately
205 m east–west by 334 m north–south, geodesic area 0.06836 km² (6.84 hectares).
Its OSM-like
features, population raster, terrain and restriction wall are generated test
data, not acquired observations. The optional OSM basemap is real map context
only. See `backend/src/uas_planner/route_demo.py` and `sample.py`.

### Delivered implementation and historical evidence

- Part 3 was authorized on 2026-09-30. Issue #51 in existing Milestone #5 was
  created before `feature/51-constrained-routing`, based on iteration/005
  synchronized to main. Implementation adds deterministic distance-only A*,
  Dijkstra verification, exact endpoint selection, final vector segment checks,
  explicit route outcomes and GeoJSON provenance export through core/CLI/API/UI.
  `route-demo` creates a separate synthetic experiment for successful search.
  Real Braunschweig inputs retain conservative `unresolved_input` behavior.
  See `doc/iteration/iteration-005/part3.md` for reproducible operations and limits.
  Local gate: 110 Python passes, one Windows symlink-permission skip; 9 mocked
  browser checks and 6 real-stack checks passed; Ruff check/format, ESLint, build
  and diff whitespace checks passed. Real 100 m CLI returns unresolved_input;
  synthetic 50 m detour is 276.222 m and 200 m gives no_path_on_grid.
  Feature PR #52 passed all three CI jobs in run `36747282565` and merged into
  iteration/005 at `dc04c01cdd6a60b87c9203eccc664398dad14693`. Issue #51 is closed.
  Feature ancestry was confirmed in synchronized iteration/005 before deleting
  the local/remote feature branch; fetch/prune, branch -a and ls-remote verified
  cleanup. Main integration PR #53 delivered Part 3 at
  `a097e4b7c1233a38399ffefe0e819b4cfe05df4c` on 2026-09-30. PR run
  `36747782585` and iteration push run `36747776576` passed all three jobs.
  Main merge run `36748035762` also passed all three jobs.
  Final delivery documentation is tracked by Issue #54. Retain iteration branches
  and v0.3.0. Restart backend, refresh frontend and select `synthetic-route-demo`
  for successful routing, or `braunschweig-part1-v2` for explicit unresolved data.

- Iteration 005 Part 2 is delivered to `main` through PR #48 at
  `8815f8c10f787b38fc8644691855851b7a5d344d` on 2026-09-30.
  PR CI run `36737388087` and iteration push run `36737380659` passed all
  Windows/Linux Python and frontend checks. Issue #46 is closed in Milestone #5;
  documentation follow-up is tracked by Issue #49.
  Main merge CI run `36737709390` also passed all three jobs. README records
  the delivered Part 2 scope, operation, validation and cold preparation time.
  Feature branch `feature/46-grid-constraints` was created from `iteration/005`
  after issue assignment and synchronization to main's Part 1 maintenance.
  Implementation had already been prepared locally. The user authorized the
  Part 2 handoff workflow on 2026-09-30; Part 3 was deferred at that delivery.
- Part 2 adds configurable EPSG:25832 cells (50 m default, 10,000 maximum),
  area-weighted native GHSL estimates, conservative DIPUL diagnostics, candidate
  connections and exact endpoint connectors. No routing or flight permission.
  MSL checks across cells/segments remain unresolved because center terrain
  samples cannot bound the profile. Temporary coverage/legal applicability
  remains unresolved and `block_unresolved` excludes every connection.
- Part 2 validation covers population conservation, missing support, exact
  endpoints, metric lengths, source/config cache invalidation, integrity rechecks
  and a zone crossed between centers. Browser tests cover grid rebuilding,
  cell/connection inspection, invalid input and real-snapshot mobile layout.
- Restart the backend and refresh the frontend, select `braunschweig-part1-v2`,
  enable Constraint grid and click a cell. Real 50 m preparation: 3,809 cells,
  14,867 candidate edges, all unresolved; cold preparation about 35 seconds
  locally. At 100 m: 978 cells, 3,726 edges, about 10 seconds. Endpoint coordinates
  remain [10.505, 52.254] and [10.54, 52.273]. Source snapshots are unchanged.
- Feature PR #47 merged into `iteration/005` at
  `b5be7732ee6df183fb58646b9c0e76555c233dfa`. CI run `36736745505` passed
  Windows/Linux Python and frontend checks. Issue #46 was explicitly closed.
  Its feature branch was deleted locally/remotely after confirming ancestry in
  the synchronized target; fetch/prune, branch -a and ls-remote confirmed cleanup.
  Local validation: 96 Python tests passed, one symlink-permission skip; 9 mocked
  and 5 real-stack browser tests, Ruff lint/format, ESLint and build passed.
  Retain iteration branches and v0.3.0. Part 3 route search was deferred at that delivery.

- Iteration 005 Part 1 is delivered to `main` through sprint PR #39 at
  `1469af7ded55782cf1c67fded3b2c7b8c60e50e9`. Feature PR #38 merged into
  `iteration/005` at `89796b130f6d31ed7efcdfa0200427fafa3b1a6d`.
  Issue #37 is closed in Milestone #5. Part 2 was subsequently authorized;
  Part 3 remains deferred.
- Post-merge feature branch cleanup is complete: the user explicitly authorized
  deletion, the exact commit was confirmed in `iteration/005`, and local/remote
  references were pruned and checked after removal.
- Approved experiment: civil, bounds (10.50, 52.25, 10.545, 52.277), 60 m AGL,
  2026-10-01 10:00–10:15 Europe/Berlin, GHSL 2020 estimate. Full details and
  reproduction commands: `doc/experiments/part1.md`.
- Real snapshot: `data/braunschweig-part1-v2`, with a matching OSM snapshot under
  `osm/`. Original tiny samples remain unchanged. First failed terrain snapshot
  remains in `data/braunschweig-part1` for diagnosis; do not use it for the demo.
- GHSL original ZIP/native window, bounded DIPUL WFS responses/schemas and LGLN
  DGM1 terrain are preserved with checksums. Independent UI layers and location
  height inspection are implemented; no routing or constraint evaluation.
- Terrain response omits NoData and its WCS metadata gives an incorrect unit.
  Explicitly use the official product's -9999 NoData and metres NHN/DHHN2016;
  preserve and document the original metadata. DIPUL coverage is partial and
  temporary restrictions, validity, buffers/applicability remain unresolved.
- Large-area UI verification exposed excessive empty OSM tag expansion. API
  reads now use compact tag dictionaries; experiment display omits absent tags,
  while legacy responses and all original downloads retain their prior contract.
- Local validation: 85 Python tests passed, one Windows symlink-permission skip;
  9 mocked browser tests and 12 repeated real-stack smoke runs passed; Ruff,
  ESLint and production build passed. PRs #38 and #39 passed Windows/Linux
  Python and frontend CI; the main merge commit also passed all three jobs.
  Real-data Chrome inspection succeeded with no page errors, and original GHSL
  ZIP values equal saved-window values at both endpoints.
- Known non-failing dependency warnings: Starlette/httpx and Rasterio/Affine.
- Restart the backend and refresh the frontend; select `braunschweig-part1-v2`.
  Use GHSL/DIPUL switches and Inspect start/end. External originals are local-only;
  existing download buttons continue to export OSM only.

### Historical planning and previous iteration notes

- Latest scope update (2026-09-29): user excluded SORA from this iteration and
  requested algorithm options plus three delivery parts. Draft now separates
  (1) data/independent layers, (2) grid/constraints, (3) shortest-route demo.
  A* for planning and Dijkstra for verification are now user-confirmed.
  Their planned contract is recorded in `doc/rules/routing-algorithms.md`;
  implementation remains deferred.
  Planning-only changes; no adapters, routing code or remote objects created.

- Latest planning decisions (2026-09-29): AGL height, with ground elevation and
  corresponding aircraft altitude displayed; user-configurable 2D grid default
  50 m; first planner optimizes distance under constraints. Draft updated.
- Height display requires an additional terrain-elevation source and verified
  vertical datum. Source choice and numeric AGL/time remain unresolved. Population
  optimization is a later extension; implementation is still deferred.

- Follow-up on 2026-09-29: user confirmed GHSL + DIPUL as first sources, with
  altitude/time fixed initially and potentially optimized later. Implementation
  remains explicitly deferred pending discussion.
- Read relevant Ramke thesis sections and recorded proposed sequencing, spatial
  model and unresolved decisions in the former Iteration 005 draft (removed on
  2026-10-04 after being superseded by `doc/plan/iteration-005.md`). At that time
  no milestone/issues/branches were created.
- Created the Chinese six-source PDF report at
  `D:/Aostfalia/praxis/datasource/六项数据源评估报告_2026-09-29.pdf`.
- PDF validation: 9 pages, embedded Chinese fonts, 17 external reference links;
  rendered pages inspected, text bounds checked. Documentation diff whitespace
  checks passed. No application tests run because application code is unchanged.

- 2026-09-29: user requested assessment of six external sources and a dedicated
  documentation folder. Added `doc/data-sources/` with overview, six source notes
  and an integration recommendation based on current official web material.
- This session is documentation-only: no new sprint, GitHub objects, acquisition,
  source adapter or routing implementation. Changes remain local and uncommitted.
- Key finding: current DIPUL documentation includes vector downloads, WFS and
  registered ED-318 API access. GHSL and DIPUL are first validation candidates;
  Droniq access remains conditional; SORA/EGRED are methodological inputs.
- Live payload validation remains pending. See assessment verification limits,
  including failed capabilities fetches and unverified latest EGRED revision.

- Iteration 004 implements independent explainable costs for building, highway,
  landuse and natural tags. User approved implementation and GitHub integration.
- Delivered to main through sprint PR #34 at
  `7d516065a05e807e26092db1c1c7e969e0211c90` on 2026-09-28.
- Feature PR #33 merged into iteration/004; implementation Issue #32 is closed.
  Feature branch was deleted locally/remotely, pruned and verified. Retain
  iteration/001 through iteration/004 as history.
- Feature PR CI run 36446412570, iteration push run 36446647516 and sprint PR
  run 36446678245 passed all Windows/Linux Python and frontend checks.
- Main push CI run 36446895517 also passed for the sprint merge commit.
- Final delivery documentation is tracked by Issue #35 in Milestone #4.
- Local validation: 66 Python tests passed, one Windows symlink-permission skip;
  9 mocked and 3 real-stack browser tests passed; Ruff, ESLint and build passed.
- Published release remains v0.3.0; Iteration 004 does not move its tag or create
  a new release. CHANGELOG records these capabilities under Unreleased.
- Existing saved datasets are unchanged. Analysis requires no new acquisition.
- See `doc/plan/iteration-004.md`, `doc/iteration/iteration-004/feedback.md`,
  and `doc/rules/independent-costs.md` for scope, verification and rules.

## Local commands and demonstration

- Install dependencies: `uv sync --project backend --locked` and `npm ci --prefix frontend`.
- Run tests: `uv run --project backend --locked pytest backend/tests -q`.
- Command help: `uv run --project backend --locked uas-planner --help`.
- Reload live sample: `uv run --project backend --locked uas-planner inspect data/braunschweig-demo`.
- Sample files: `data/braunschweig-demo/features.gpkg` and `metadata.json` (excluded from Git).
- GitHub CLI: `D:\Aostfalia\app\GitHubCLI\bin\gh.exe`, version 2.101.0, not logged in directly. Git's credential provider supplies authenticated access when required; never print or persist credential values. No global PATH change was made.
- See README and `doc/iteration/iteration-001/feedback.md` for commands and limitations.

## Agreed architecture

- One repository with clearly separated `frontend/` and `backend/` directories.
- Frontend: React, TypeScript, Vite, and Leaflet.
- Backend: Python, FastAPI, and a reusable Python research core.
- Frontend and backend run separately. The frontend calls the backend through HTTP APIs.
- The Python core must not depend on the frontend or FastAPI; experiments can call it directly.
- Initial geospatial stack: OpenStreetMap, OSMnx/Overpass, GeoPandas, Shapely, and pyproj.
- Initial storage: GeoPackage, GeoJSON exports, and JSON metadata.
- Local development with VS Code; GitHub provides version control and automated checks.
- Default language for code, project documents, issues, and pull requests: English.

## Required workflow

1. Read this file before starting work and verify it against the actual repository state.
2. Discuss each new sprint plan with the user before creating the sprint.
3. Record the agreed plan in `doc/plan/iteration-NNN.md`.
4. Represent each sprint with a GitHub Milestone and an `iteration/NNN` integration branch.
5. Create each Issue and assign it to its Milestone before creating its feature branch.
6. Create feature branches from the corresponding iteration branch.
7. Validate changes and merge feature pull requests into the iteration branch. Close the corresponding Issue explicitly if necessary; retain its history. Immediately delete the merged feature branch both locally and on GitHub, following the mandatory cleanup procedure below.
8. Validate the complete sprint and merge the iteration branch into `main` through a pull request.
9. Prepare sprint feedback in `doc/iteration/iteration-NNN/` and update README before the sprint merge. Record post-merge facts or further feedback through a documentation update as needed.
10. Update this file at the end of every work session, including incomplete or blocked sessions.

### Mandatory post-merge branch cleanup

- Applies to every merged feature branch and temporary documentation/fix branch, including the branch used to change this document.
- Verify that the intended PR is merged before deleting its source branch. Never delete a branch with unmerged work merely to make the branch list shorter.
- Switch to the target branch and synchronize it, delete the source branch on GitHub, and delete the corresponding local branch.
- Run `git fetch --prune origin` to remove stale remote-tracking references.
- Verify both `git branch -a` and `git ls-remote --heads origin`. Do not report cleanup as complete based only on a PR merge or the local branch list.
- Keep `main`. Iteration integration branches such as `iteration/001` are separate from feature branches and remain historical references under the current convention; changing their retention requires an explicit user decision.
- For squash merges, Git ancestry alone may not mark the local feature branch merged. Confirm the merged PR and synchronized changes before deleting that local branch.

## Documentation locations

- `doc/data-sources/`: external data/methodology assessments and integration options.
- `doc/plan/`: agreed sprint plans.
- `doc/iteration/`: sprint outcomes and retrospectives.
- `doc/decisions/`: architecture and technical decisions.
- `doc/research/`: literature notes and experiment methodology.

## Open questions and pending decisions

- Iteration 004 implementation is delivered. Further feature work requires a subsequent agreed plan.
- Runtime baseline is approved and validated: Python 3.13.13, Node.js 24.14.1, npm 11.11.0, uv 0.11.6. Git is 2.45.1.windows.1.
- OSMnx may retry after service backoff without an overall deadline; Ctrl+C cancels acquisition. HTTP timeout is not a total execution limit.
- Geometries are complete source features, not clipped. Invalid geometries are retained and counted. Unknown tags are preserved as JSON-compatible values.
- Acquisition timestamps may describe a cache read, not the original source download/edit. Source snapshots require preserving the local dataset.
- Frontend and read-only API are implemented. Acquisition remains a CLI operation; refresh the UI after saving new data.
- The current API loads and verifies complete small datasets per request; large-data performance remains future scope.

## Session outcome

- Added independent tag-cost core/API and category switching in the explorer.
- Original features/downloads and dataset schema remain compatible. Historical
  paper obstruction flags are distinct from numeric costs and current regulation.
- Unknown values use explicitly marked provisional cost 2. No undocumented rule
  was added to classify natural=tree as natural=wood.
- Expanded-area acquisition was canceled at the user's request and not resumed.
  Basemap imagery is context; moving the map does not acquire analysis features.
- All current changes were prepared locally before remote tracking was established;
  Issue #32 was created before the feature branch. The plan records this sequence.
- Do not stop user-owned development services. Browser tests use 8011/5174/5175.
- Restart the backend after updating, then refresh the browser. In Cost category,
  select Buildings, Roads & paths, Land use or Natural features and enable its map.
- Known dependency warning: Starlette deprecates the current httpx TestClient
  integration. It does not fail the verified tests.

## Start the interface

Run from the repository root in two terminals:

```powershell
uv run --project backend --locked uvicorn uas_planner.api.app:app --host 127.0.0.1 --port 8000
npm --prefix frontend run dev
```

Open http://127.0.0.1:5173. Dataset files are local and excluded from Git. See README for acquisition and verification commands.

For a network-free example after installing dependencies: `uv run --project backend --locked uas-planner sample --output data/offline-sample`. Existing directories are not overwritten. Test with `npm --prefix frontend run test:smoke`.

- Follow-up Issue #42 addressed the Part 1 UI timeout on the 31,496-feature
  local snapshot: the tag-analysis response is ~85.5 MB and measured 26.2 seconds.
  Frontend request timeout was raised from 30 to 120 seconds with no backend or
  data contract change. ESLint and the production build passed locally; the
  response duration and size were measured against the saved experiment API.
- PR #43 merged to `main` at `063905eed8254ea9816686696b3ec5453be34301`.
  GitHub Actions run `36693434334` passed. Issue #42 closed with the merge.
  Branch `fix/42-large-dataset-timeout` was deleted locally and remotely, then
  pruned; `git branch -a` and `git ls-remote --heads origin` confirmed cleanup.

## Iteration 006 Part 1 (2026-09-30)

- User approved `doc/plan/iteration-006.md`, authorized Part 1, and requested calculation rules under `doc/rules/`. Parts 2 and 3 remain deferred.
- Milestone 6 / Issue #56 precede `iteration/006` and `feature/56-risk-weighted-routing`, based on main `42db227`.
- Confirmed: metric units; centreline intersection length times risk; buffered point/motion intersection collision checks; initial risk/length weights 0.9/0.1.
- Verified existing OSM acquisition, 0–4 building/tag classifications, EPSG:25832 grid and distance-only A*/Dijkstra. Reuse them rather than importing the archive wholesale.
- Approved: building-only first objective, maximum score in overlaps, explicit background assessment policy, safety-distance default 0 m with configurable positive clearance. Population and cross-layer fusion deferred.
- OMPL Python 3.13 Windows/Linux compatibility remains unverified and is an implementation dependency gate. Real-data constraint uncertainty remains unchanged.
- Implemented core: `risk.py`, `risk_routing.py`, weighted A*/Dijkstra in `routing.py`; documented calculations in `doc/rules/risk-weighted-routing.md`. Existing CLI/API/UI remain distance-only defaults; Python entry point is `plan_risk_route`.
- Prepared risk models verify saved OSM before cache access; signatures include source/rules/manifest/grid/CRS/weights/background/clearance. Final route costs and full geometry are rechecked.
- Local validation: 139 Python tests passed, one Windows permission skip; Ruff, ESLint and frontend build passed. Six real-stack browser cases passed and Playwright exited successfully after stopping its test servers during Windows teardown.
- Saved real `braunschweig-part1-v2` at 100 m remains `unresolved_input`; four in-boundary building objects have unsupported non-polygon geometry, explicitly recorded without invented footprints. Synthetic 100 m returns `no_path_on_grid`; use finer cells for successful demos.
- Saved synthetic 50 m succeeds for weighted A* and Dijkstra: 276.22166570077525 m, risk-length 71.90458069004399, objective 92.33628919111712, explicit background 0 assumption.
- Part 1 implementation and local validation are complete. On 2026-10-01 the user explicitly authorized publication and merges to `Hunter3304/uas-mission-planner`. Feature PR #57 merged into `iteration/006` at `02ef32a5c0035b83749e996b78f8d63273ac4093` after all three CI jobs passed in run `36836063414`. Issue #56 is closed; the merged feature branch was deleted locally/remotely after verified ancestry, followed by fetch/prune, branch -a and ls-remote checks.
- Main integration is tracked by PR #58. Its initial CI run `36836528007` and iteration push run `36836402950` passed all three jobs. This delivery record follows the same existing iteration/PR; no additional documentation issue or branch is created.
- Existing 51-line real-route handoff addition predates this task and is preserved unstaged; it is excluded from this task's commit. No OMPL dependency, population objective, new acquisition or weighted UI controls implemented.
