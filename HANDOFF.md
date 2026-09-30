# UAS Mission Planner — Handoff

## Current status

- Iteration 005 Part 1 is delivered to `main` through sprint PR #39 at
  `1469af7ded55782cf1c67fded3b2c7b8c60e50e9`. Feature PR #38 merged into
  `iteration/005` at `89796b130f6d31ed7efcdfa0200427fafa3b1a6d`.
  Issue #37 is closed in Milestone #5. Parts 2/3 remain deferred.
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

- Follow-up Issue #42 addresses the Part 1 UI timeout on the 31,496-feature
  local snapshot: the tag-analysis response is ~85.5 MB and measured 26.2 seconds.
  Frontend request timeout raised from 30 to 120 seconds; no backend or data
  contract change. Maintenance branch/PR and merge evidence will be recorded here.
  Local checks: ESLint and production build passed. The response duration and
  size were measured against the saved experiment API. Automated CI will run on
  the pull request; its result and merge commit will be appended after delivery.
