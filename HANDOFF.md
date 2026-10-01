# UAS Mission Planner — Handoff

## Current status

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
  model and unresolved decisions in `doc/plan/iteration-005-draft.md`. This is not
  an approved iteration plan; no milestone/issues/branches were created.
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
