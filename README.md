# UAS Mission Planner

A local Python geospatial research prototype for an internship and subsequent bachelor's thesis. Acquire a small area, save and verify its data, explore layers and statistics, and download results.

**Stage version: [v0.3.0](https://github.com/Hunter3304/uas-mission-planner/releases/tag/v0.3.0).** See [CHANGELOG](CHANGELOG.md), [Iteration 003 plan](doc/plan/iteration-003.md), and [feedback](doc/iteration/iteration-003/feedback.md). Read [HANDOFF](HANDOFF.md) before work and update it afterward.

Main includes the completed [Iteration 004](doc/plan/iteration-004.md) independent tag costs; these additions are not part of the fixed v0.3.0 release. See [iteration feedback](doc/iteration/iteration-004/feedback.md).

Iteration 005 Part 1 adds independent **GHSL population, DIPUL zones and terrain
height inspection**. Use the [experiment guide](doc/experiments/part1.md) to acquire
or reload a checksummed snapshot and inspect 60 m AGL plus ground/aircraft height.
The saved local demonstration is `braunschweig-part1-v2` (9.23 km²). Select it in
the explorer after restarting the backend and refreshing the page.

Iteration 005 [Part 2](doc/iteration/iteration-005/part2.md) was delivered to main
on 2026-09-30 through [PR #48](https://github.com/Hunter3304/uas-mission-planner/pull/48).
It adds a configurable
EPSG:25832 preparation grid (default 50 m, maximum 10,000 cells). Enable
**Constraint grid**, change **Grid cell (m)**, and click a cell to inspect
population estimates, unknown support, altitude diagnostics and adjacent
candidate connections. Endpoint connectors preserve the exact mission points.
The read-only endpoint is `/api/datasets/{id}/experiment/grid?cell_m=50`.
Temporary restriction coverage and legal applicability remain unresolved;
`block_unresolved` excludes every candidate from traversal. Part 3 preserves
this policy and reports `unresolved_input` for the real snapshot. This
preparation graph does not establish flight permission.
Validated locally with 96 Python passes (one Windows permission skip), 9 mocked
and 5 real-stack browser passes, lint/format/build, and real Braunschweig grid
inspection. Windows/Linux Python and frontend CI passed before and after merge.
The real 50 m grid has 3,809 cells and 14,867 candidate edges; initial preparation
took about 35 seconds locally, so allow it to finish before inspecting cells.

## Part 3: constrained shortest route

Part 3 was delivered to main on 2026-09-30 through
[PR #53](https://github.com/Hunter3304/uas-mission-planner/pull/53), after
Windows/Linux Python and frontend CI passed. It adds deterministic distance-only
A*, verified against Dijkstra, exact
endpoint selection, full segment checks, explicit failures and route GeoJSON
with mission/source/rule metadata. See [Part 3 outcome](doc/iteration/iteration-005/part3.md).
Local verification: 110 Python passes (one Windows permission skip), 9 mocked
and 6 real-stack browser passes, Ruff, ESLint and production build.
Real Braunschweig inputs remain unresolved; use this synthetic obstacle model
for a successful offline demonstration:

```powershell
uv run --project backend --locked uas-planner route-demo --output data/synthetic-route-demo
uv run --project backend --locked uas-planner experiment-route data/synthetic-route-demo --output .cache/demo-route.geojson
```

Output paths must be new. Restart the backend, refresh the explorer and select
`synthetic-route-demo`. Choose **Select start/end on map** or edit longitude and
latitude, then **Generate shortest route**. The green route displays horizontal
length and runtime. **Export route GeoJSON** includes provenance and assumptions;
failures export empty features with their explicit outcome. The optional dashed
**Straight-line reference** has no constraint validation. Changing endpoints,
dataset or cell size clears the old route. Grid colors: green permitted, red
blocked, amber unresolved. Population and OSM scores are independent of routing.

The API is `/api/datasets/{id}/experiment/route?cell_m=50` with optional
`start_lon`, `start_lat`, `end_lon`, `end_lat`; add `export=true` for GeoJSON.
Results distinguish `success`, `invalid_endpoint`, `unresolved_input`,
`no_path_on_grid`, `resource_limit` and `computational_failure`. Malformed
coordinates or unsupported preparation sizes return HTTP 422. CLI exit codes
are 0 success, 2 explicit route failure, 1 invalid input/storage failure.
The shortest-distance guarantee applies to the constructed graph only; no
flight permission, continuous-space optimality, 3D clearance or SORA claim.

## Quick start: offline demonstration

Iteration 006 Part 1 adds **building-risk weighted A*/Dijkstra in the Python
core**, with metric centreline length times score, overlap maximum, explicit
background assumptions and risk/length weights 0.9/0.1. See the
[calculation rules and offline example](doc/rules/risk-weighted-routing.md) and
[Part 1 feedback](doc/iteration/iteration-006/part1.md). Current route controls
continue to optimize distance; OMPL and weighted route controls are later parts.
Real unresolved constraints retain their existing behavior.
Feature [PR #57](https://github.com/Hunter3304/uas-mission-planner/pull/57) passed
Windows/Linux Python and frontend CI and merged into `iteration/006`;
[PR #58](https://github.com/Hunter3304/uas-mission-planner/pull/58) is the main
integration record. Local verification: 139 Python passes, one Windows permission
skip, six real-stack browser passes, Ruff, ESLint and production build.

Prerequisites: Git, Python 3.13, uv, and Node.js 24/npm 11. Validated baseline: Python 3.13.13, uv 0.11.6, Node 24.14.1, npm 11.11.0. Open the repository folder in VS Code. Run these PowerShell commands from its root:

```powershell
# New checkout only; skip if the repository already exists locally.
git clone https://github.com/Hunter3304/uas-mission-planner.git
cd uas-mission-planner

# First installation (requires internet).
uv sync --project backend --locked
npm ci --prefix frontend

# Generate a tiny sample; no map-service access is needed.
uv run --project backend --locked uas-planner sample --output data/offline-sample
uv run --project backend --locked uas-planner inspect data/offline-sample
```

The sample contains **3 synthetic objects: 1 point, 1 line, 1 polygon**. Each semantic layer has one object; the building also has a land-use tag, so layer counts total four but unique objects total three. It is illustrative data, not surveyed OSM data. Feature content is fixed; timestamps and GeoPackage checksums can differ between saves. If `data/offline-sample` already exists, inspect it or choose another output name. Never overwrite a dataset silently.

Open **two terminals** at the repository root and keep both running:

```powershell
# Terminal 1: backend
uv run --project backend --locked uvicorn uas_planner.api.app:app --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2: frontend
npm --prefix frontend run dev
```

Open **http://127.0.0.1:5173**. Select `offline-sample`; switch off **Basemap** for offline use. Toggle layers, select a feature in the map/table, and download GeoJSON, GeoPackage, or metadata. Downloads always contain the complete dataset, including hidden layers. Click **Refresh** after saving another dataset. Stop each service with **Ctrl+C** in its terminal.

| Address | Purpose |
| --- | --- |
| http://127.0.0.1:5173 | User interface |
| http://127.0.0.1:8000/docs | API documentation |
| http://127.0.0.1:8000/api/health | Backend health; returns `{"status":"ok"}` |
| http://127.0.0.1:8000/ | No page is registered; `Not Found` is expected |

## Optional OMPL / ABIT* on native Windows

Iteration 006 Part 2's dependency probe passed on Windows x64 / Python 3.13.13.
The route uses the official OMPL 2.0.1 C++ ABIT* algorithm with local Python
binding and packaging fixes. Part 2 adds an offline Python adapter; the
normal quick start above does not require OMPL. No Linux/WSL setup is needed
for this verified Windows route.

| Dependency | Verified version / purpose |
| --- | --- |
| Visual Studio 2022 Build Tools | 17.14.37710.0; MSVC x64/x86 14.44.35207, native source builds |
| Windows SDK | 10.0.26100.0, native source builds |
| CMake / Ninja | 4.4.3 / 1.13.2 |
| vcpkg | Pinned checkout; Boost 1.92.0 serialization, program-options, math, graph and odeint; Eigen 5.0.1 |
| scikit-build-core | 1.1.0, Python wheel packaging |
| Nanobind | Pinned OMPL source submodule, Python bindings |
| OMPL wheel | Patched `2.0.1+uas.1`, included under `backend/vendor`, Python 3.13 x64 only |

The compiler/SDK are build prerequisites. The wheel includes its Boost runtime
DLL; a plain PyPI `ompl` installation is not the verified Windows package.
The wheel was tested on the build host, not a separate clean Windows machine.
See the [source pins, patches, build commands and runtime evidence](doc/iteration/iteration-006/part2-windows-verification.md).
Install the optional planner and run its tests from the repository root:

```powershell
uv sync --project backend --locked --extra ompl-windows
uv run --project backend --locked --extra ompl-windows pytest tests/test_abitstar.py -q
```

The lock pins the repository wheel's SHA-256. Compiler tools are unnecessary for
installing it on a compatible Windows x64 Python 3.13 environment; the Windows
MSVC runtime must be available. Use `--extra ompl-windows` on subsequent `uv run`
or `uv sync` commands to retain the optional planner. Other platforms retain
graph routing and receive `planner_unavailable` for ABIT* unless a compatible
patched native build is separately installed. Linux ABIT* is not runtime-verified.

The Python entry point is `plan_risk_route(..., algorithm="abitstar",
background_cost=0, time_budget_s=3, cancel=event.is_set)`. Background 0 is an
explicit research assumption. Results distinguish exact success, approximate
candidate, timeout, cancellation, invalid endpoint, unresolved input, unavailable
planner and computation failure. Returned exact paths are rechecked against the
full vector constraints and their costs are recomputed. Budget/cancellation are
cooperative; preparation and final validation can add overhead. CLI/API/UI controls and independently scored comparisons are available in Part 3. See [Part 2 usage and limits](doc/iteration/iteration-006/part2.md)
and [binary source/build provenance](backend/vendor/README.md).

## Iteration 006 Part 3: controls and comparison

CLI/API/UI now select A*, Dijkstra or ABIT*, distance or weighted building risk,
weights, an explicit background score, safety distance and ABIT* time budget.
Existing requests default to distance-only A*. Blank background remains
unassessed; background 0 is an explicit research assumption. Population is separate.

Create a **new** synthetic low-risk-detour dataset and compare offline:

```powershell
uv run --project backend --locked uas-planner route-demo --low-risk --output data/synthetic-risk-demo
uv run --project backend --locked --extra ompl-windows uas-planner experiment-route data/synthetic-risk-demo --algorithm abitstar --objective risk --background-cost 0 --cell-m 25 --time-budget-s 3 --output risk-route.geojson
uv run --project backend --locked --extra ompl-windows uas-planner route-compare data/synthetic-risk-demo --background-cost 0 --cell-m 25 --repetitions 3 --time-budget-s 2 --output risk-comparison.json
```

Use new output names if they already exist. In the map, choose the synthetic
dataset, set grid 25 m and background 0, and generate or **Compare algorithms**.
The UI exports the displayed result without another solve. Status, costs,
assumptions and provenance are retained; approximate/failed results do not export
a successful route feature. Parameter changes invalidate displayed results.

`/api/datasets/{id}/experiment/route` accepts algorithm/objective/weights,
background/clearance/budget and optional endpoints; `/experiment/compare` runs
the fixed four-planner lineup with bounded repetitions and independent cost checks.
Per-task native seeds are unsupported and recorded as such. Grid and continuous
optimality claims remain separate. Real-data unresolved results stay explicit.
See [operation, budgets, measurements and verification](doc/iteration/iteration-006/part3.md).

## Acquire real map data

With dependencies installed, run from the repository root:

```powershell
uv run --project backend --locked uas-planner fetch --west 10.519 --south 52.269 --east 10.521 --north 52.271 --output data/braunschweig-demo --cache .cache/osmnx
uv run --project backend --locked uas-planner inspect data/braunschweig-demo
```

`fetch` needs internet and retrieves building, highway, landuse, and natural features through OSMnx/Overpass. It saves `features.gpkg` and `metadata.json`, then reloads and verifies them. `inspect` reads only local data. The output directory must be new. A previous live demonstration contained 91 features; current OSM results may change.

Coordinates use EPSG:4326 longitude/latitude. Queries are limited to 25 km², a maximum one-degree span per axis, and no polar or dateline-crossing area. Features retain complete geometries and can extend beyond the query rectangle. Layers match by union. Empty results are valid; source-invalid geometries are retained and counted.

OSMnx enables caching and service backoff. Individual HTTP requests time out after 60 seconds; retries/backoff are not bounded by an overall deadline. Use Ctrl+C to cancel. Acquisition times are operation times, not source edit times or proof of a fresh download. A failed save may leave an incomplete folder for diagnosis; it will not pass verification. Preserve it for investigation and retry with a new output name.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `WinError 10048` / address already in use | A service already owns backend port 8000. Check `/api/health`; reuse it if it is this project, or stop the original terminal with Ctrl+C before restarting. |
| `Port 5173 is already in use` | Check the existing frontend URL. Stop the original frontend terminal before starting another instance. |
| Backend root shows `Not Found` | Open port **5173** for the UI, or `/docs` on port 8000 for API docs. |
| Cannot reach data service / error 500 or 502 | Start the backend and check its terminal. Restart Vite after changing branches or proxy configuration. |
| Invalid response / unexpected download type | Check both addresses above. An HTML page may be served instead of the API; restart the services with the correct configuration. |
| No saved datasets | Run the sample/fetch command, then Refresh. Check the data root and folder name. |
| Dataset cannot be verified | Inspect it with the CLI for details. Check that both files are present; do not edit checksums to bypass corruption. |
| Basemap unavailable | Disable Basemap. Saved vector layers, statistics, and downloads still work locally. |
| uv hardlink warning | Installation falls back to copying; this is not failure. Optionally set `$env:UV_LINK_MODE='copy'` in that terminal. |
| Sample output already exists | Use `inspect`, or choose a new directory such as `data/offline-sample-02`. |

Identify the owner of a busy port in PowerShell:

```powershell
Get-NetTCPConnection -LocalPort 8000,5173 -State Listen |
    Select-Object LocalAddress, LocalPort, OwningProcess
# Replace 12345 with an actual PID from the output:
Get-Process -Id 12345
```

Stop a process only after confirming it belongs to your project. Prefer Ctrl+C in its original terminal. If that terminal is unavailable, `Stop-Process -Id 12345` stops the confirmed process. Do not copy an old PID from another session.

## Configuration and data

The API reads direct subdirectories of `data/`, containing `features.gpkg` and `metadata.json`. Names must start with an ASCII letter/digit, use only letters, digits, underscores or hyphens, and be at most 100 characters. To use another data root, set `$env:UAS_DATA_DIR='D:/path/to/datasets'` in the **backend terminal before startup**.

Vite proxies `/api` to `http://127.0.0.1:8000`. To use another backend port, start uvicorn with that port and set `$env:UAS_API_URL='http://127.0.0.1:8001'` in the **frontend terminal before startup**. Servers bind to loopback for local development.

Generated datasets and caches are excluded from Git. Metadata records the source, query, versions, geometry policy, count, and GeoPackage SHA-256. Verification checks storage consistency, not geographic accuracy. Synthetic samples are explicitly marked in metadata and UI. Dataset schema remains version 1, compatible with valid earlier datasets.

## Verify the delivery

From the repository root:

```powershell
uv run --project backend --locked uas-planner --version
uv run --project backend --locked pytest backend/tests -q
uv run --project backend --locked ruff check backend/src backend/tests
uv run --project backend --locked ruff format --check backend/src backend/tests
npm --prefix frontend run lint
npm --prefix frontend run build

# One-time browser installation requires internet.
cd frontend
npx playwright install chromium
npm run test:e2e
npm run test:smoke
cd ..
```

Alternatively, with Chrome installed on Windows, set `$env:PLAYWRIGHT_CHANNEL='chrome'` before the browser tests and skip installing Chromium. The mocked UI suite uses port 5174. The **real-stack smoke test** creates a temporary sample, launches the actual API on 8011 and Vite on 5175, checks map/statistics/tags and all downloads, verifies the GeoPackage checksum, and stops its servers. Keep these test ports free. Basemap requests are blocked in tests; map-service access is unnecessary after dependencies and browser installation.

CI runs Python checks on Windows/Linux and frontend lint, build, mocked browser tests and real-stack smoke on Linux. Windows may skip the symlink-containment test when symlink permission is unavailable; Linux runs it. A dependency currently emits a Starlette/httpx deprecation warning; it does not fail the checks.

## Architecture and stack

### Independent tag cost analysis

Saved datasets are analyzed using versioned rules from Ramke (2020). Choose
**Cost category**: Buildings, Roads & paths, Land use, or Natural features.
Enable the corresponding **cost map** checkbox to color that category by its
tag cost (0-4). Roads, land use and natural features are analyzed independently,
including objects with no building tag. Select a feature to inspect each tag, its cost or unscored status,
the matched rule, source and any historical paper obstruction flag. Search
supports tag keys/values as well as names and OSM identities.
Read [Cost rules](doc/rules/README.md) and the
[independent-layer guide](doc/rules/independent-costs.md). The executable rules
live in [cost_rules.json](backend/src/uas_planner/core/cost_rules.json).
Unknown classifications use provisional cost 2 with a distinct gray
style; blank areas are unassessed. Other tag costs are shown independently,
not added to the selected category's cost. Statistics cover all saved objects in
that category, including hidden ones. Switching categories updates the map,
table and statistics and clears the prior selection. Active layer switches still
use union visibility for objects carrying multiple tags.
Paper obstruction flags do not establish current flight restrictions.

Restart the backend after updating rules/code, then Refresh the dataset.
Original datasets and downloads are unchanged; analysis is calculated on read.
This feature does not yet create a fused cost grid or plan a flight route.

One public monorepo, separately running frontend/backend. React communicates through HTTP. **The Python core must never depend on React or FastAPI**; CLI, API and future experiments reuse the core. Code, UI and project documentation default to English.

| Area | Stack |
| --- | --- |
| Core/API | Python 3.13, FastAPI, uvicorn |
| Frontend | React 19.3.0, TypeScript 6.0.3, Vite 8.3.1, Leaflet |
| Geospatial | OSMnx/Overpass, GeoPandas, Shapely, pyproj, pyogrio |
| Storage/export | GeoPackage, GeoJSON, JSON metadata |
| Environments | uv + backend/uv.lock; npm + frontend/package-lock.json |
| Quality | pytest, Ruff, ESLint, TypeScript, Playwright, GitHub Actions |
| Development | Local VS Code; Python 3.13 and Node.js 24 runtime lines |

Use locked installs. Upgrade dependencies deliberately through a tested issue/PR, not as part of ordinary startup.

```text
backend/src/uas_planner/   Independent core, acquisition, storage, CLI and API adapters
backend/tests/            Unit/API tests and isolated smoke-test server
frontend/src/             React interface and map
frontend/tests/           Mocked browser regression tests
frontend/smoke/           Real API/browser sample test
data/                     Local generated datasets (ignored)
doc/plan/                 Agreed sprint plans
doc/iteration/            Results and retrospectives
doc/decisions/            Architecture decisions
doc/research/             Literature and methodology
.github/                  Issues and CI
HANDOFF.md                Current state, workflow and pending work
CHANGELOG.md              Stage release history
```

## Workflow and stage versions

Read HANDOFF, discuss each sprint, and record its plan before creating the Milestone. Create Issues in that Milestone **before** feature branches. Branch from `iteration/NNN`, validate and merge PRs back into it, close Issues, and immediately delete merged branches **locally and remotely**, pruning and verifying both. Merge the tested iteration into main; retain iteration branches as history. Update README, feedback and HANDOFF, including post-merge facts.

The v0.3.0 stage release is a tagged prototype baseline. Backend, frontend, CLI and API versions agree; a regression test checks this. Only tag a main commit with successful CI. Release notes record capabilities, validation and limits. Do not move a published tag; fixes get a new version. GitHub source archives plus committed lockfiles and the sample command reproduce the release environment without publishing local map datasets.

## Current limits

The [external data and methodology assessment](doc/data-sources/README.md)
reviews Droniq/TraX, OpenFlightMaps, GHSL, DIPUL, SORA 2.5 and EGRED 2 as of
2026-09-29, with access evidence, limitations and proposed routing uses.
GHSL, selected DIPUL WFS layers and LGLN DGM1 are integrated for local independent
inspection in Part 1. The other assessed sources remain documentation-only.

This is a local small-area prototype that loads datasets into memory and revalidates API reads. Building tag costs are ordinal research classifications. Browser-triggered acquisition, background jobs, large-area performance, population/cost fusion, mission routing and public deployment require future planned work. No next sprint is approved automatically by this release.

## Explorer panel controls

Use **Collapse / Expand** on the cost analysis, independent source layers, route
planning, location/source inspection, feature browser and feature details panels.
The map stays visible and folding preserves planner inputs and results. Feature
browser/details start collapsed, can be opened manually, and both open when any
feature is selected. Clearing selection collapses both.

**Distance** hides Risk weight, Distance weight and Background score assumption;
**Weighted building risk** shows them and restores their values. Safety distance
and ABIT* budget remain available. Distance objective cost is horizontal route
length in metres. Weighted objective cost is `risk_weight * integrated_building_score_length
+ distance_weight * horizontal_length`; background must be explicitly assessed.
See [UI validation](doc/iteration/iteration-006/ui-panels.md).


Iteration 006 Part 2/3 and explorer panel controls were accepted on 2026-10-03.
Delivered to main through [PR #64](https://github.com/Hunter3304/uas-mission-planner/pull/64)
after successful Windows/Linux Python and frontend CI. See HANDOFF for integration records.
