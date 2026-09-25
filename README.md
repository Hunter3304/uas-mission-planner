# UAS Mission Planner

A local Python geospatial research prototype for an internship and subsequent bachelor's thesis. Acquire a small area, save and verify its data, explore layers and statistics, and download results.

**Stage version: v0.3.0.** See [CHANGELOG](CHANGELOG.md), [Iteration 003 plan](doc/plan/iteration-003.md), and [feedback](doc/iteration/iteration-003/feedback.md). Read [HANDOFF](HANDOFF.md) before work and update it afterward.

## Quick start: offline demonstration

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

This is a local small-area prototype that loads datasets into memory and revalidates API reads. Browser-triggered acquisition, background jobs, large-area performance, risk models, mission routing and public deployment require future planned work. No next sprint is approved automatically by this release.
