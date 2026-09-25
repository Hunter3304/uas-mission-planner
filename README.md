# UAS Mission Planner

A Python-based geospatial data and UAS mission-planning research project, developed for an internship and a subsequent bachelor's thesis.

## Project status

Iteration 002 adds a local dataset explorer: view saved OSM layers, inspect statistics and feature tags, and download GeoJSON, GeoPackage, or metadata. Iteration 001 provides the acquisition/save/reload core. See the [Iteration 002 plan](doc/plan/iteration-002.md) and [feedback](doc/iteration/iteration-002/feedback.md).

Read [HANDOFF.md](HANDOFF.md) before starting work and update it at the end of each work session.

## Architecture

- One public GitHub repository, intended name: `Hunter3304/uas-mission-planner`.
- Separate frontend and backend code, running as separate local processes.
- The React frontend communicates with the Python backend through HTTP APIs.
- The Python research core is independent of React and FastAPI. API handlers and experiment scripts call the same core.
- Default project language: English.

## Technology stack

The architecture and runtime baselines are agreed. Dependency versions are recorded in `backend/uv.lock` and `frontend/package-lock.json`.

| Area | Technology | Status |
| --- | --- | --- |
| Research core | Python 3.13.13 | Installed and verified |
| HTTP API | FastAPI | Read-only dataset API implemented |
| Frontend | React 19.3.0, TypeScript 6.0.3, Vite 8.3.1 | Dataset explorer implemented |
| Map interface | Leaflet | Interactive vector map implemented |
| Frontend runtime/tooling | Node.js 24.14.1 LTS, npm 11.11.0 | Installed and verified |
| Map data | OpenStreetMap through OSMnx/Overpass | Agreed |
| Geospatial processing | GeoPandas, Shapely, pyproj | Agreed |
| Storage and export | GeoPackage, GeoJSON, JSON metadata | Agreed |
| Python environment and dependency management | uv 0.11.6, project-local virtual environment, uv.lock | Installed and verified |
| Frontend dependency management | npm, package-lock.json | Installed and locked |
| Python quality checks | Ruff, pytest | Installed |
| Frontend quality checks | ESLint, TypeScript, Playwright | Lint, build, and browser checks enabled |
| Development | Local Windows environment, VS Code | Agreed |
| Version control and automation | Git, GitHub, GitHub Actions | CI runs offline Python tests on Windows/Linux and runs frontend lint, build, and browser tests |

### Runtime and dependency policy

- Agreed runtime lines: Python 3.13 and Node.js 24 LTS.
- Runtime pins are recorded in `.python-version` and `.node-version`; npm is pinned in `frontend/package.json`.
- The geospatial stack has been installed and verified on Windows with Python 3.13.13.
- Select mutually compatible stable package releases during scaffolding; do not select prereleases by default.
- Backend and frontend dependency lockfiles are committed. Use the same locked dependencies in local development and CI.
- Upgrade dependencies deliberately, verify affected functionality, and record changes through the project workflow.
- Evaluate future planning-library compatibility when introducing those libraries; it has not been tested yet.

### Local environment observed during planning

| Tool | Observed version |
| --- | --- |
| Python | 3.13.13 |
| Node.js | 24.14.1 |
| npm | 11.11.0 |
| Git | 2.45.1.windows.1 |
| uv | 0.11.6 |

Dependencies are installed. Python imports, frontend dependency resolution, GeoPackage mixed-geometry persistence, and coordinate projection have passed environment checks. See `doc/iteration/iteration-001/` for workflow validation and live acquisition evidence.

### Install locked dependencies

From the repository root, install Python dependencies with `uv sync --project backend --locked` and frontend dependencies with `npm ci --prefix frontend`. Use the project environment rather than installing packages into system Python.

## Repository layout

`frontend/`, `backend/`, `data/`, `doc/plan/`, and `.github/` are established. Experiment and research directories will be added when their work begins.

```text
frontend/          React application and frontend tests
backend/           Python package, API, and backend tests
experiments/       Reproducible experiment configurations and runners
data/              Local datasets; large generated files excluded from Git
doc/plan/          Agreed sprint plans
doc/iteration/     Sprint outcomes and retrospectives
doc/decisions/     Architecture and technical decision records
doc/research/      Literature and research-methodology notes
.github/           Issue templates and automated checks
HANDOFF.md         Current state, workflow, open questions, and next steps
```

## Workflow

1. Read the handoff and verify the actual state.
2. Discuss each sprint with the user and write the agreed plan in `doc/plan/`.
3. Create a GitHub Milestone for the sprint and an `iteration/NNN` branch.
4. Create Issues assigned to that Milestone before creating corresponding feature branches.
5. Branch from the iteration branch, implement, validate, and merge through a pull request into that iteration branch.
6. Close the completed Issue and delete the merged feature branch. Keep Issue history.
7. Prepare the sprint retrospective and README update, validate the whole sprint, and merge into `main` through a pull request.
8. Record post-merge facts as needed and update the handoff at the end of the session.

## Initial delivery direction

The agreed first iteration establishes the development foundation and a command-line map acquisition prototype: specify an area, retrieve OSM features, save and reload the dataset, and record acquisition metadata. Iteration 002 adds interactive display and API endpoints. Acceptance criteria are recorded in the iteration plan.

## Run the core workflow

Run these commands from the repository root after installing locked dependencies:

```powershell
uv run --project backend --locked uas-planner fetch --west 10.519 --south 52.269 --east 10.521 --north 52.271 --output data/braunschweig-demo --cache .cache/osmnx
uv run --project backend --locked uas-planner inspect data/braunschweig-demo
```

`fetch` downloads OSM building, highway, landuse, and natural features, creates `features.gpkg` and `metadata.json`, and immediately reloads and verifies the output. `inspect` only reads local files and checks integrity. It needs no network connection when the locked environment is already installed. For direct offline use, run `backend/.venv/Scripts/uas-planner.exe inspect data/braunschweig-demo` on Windows.

The output directory must be new; an existing dataset is never silently overwritten. To repeat the demonstration, choose a different output directory or inspect the saved dataset. Coordinates are EPSG:4326 longitude/latitude with explicit west/south/east/north flags. Query area is limited to 25 km², each coordinate span to one degree, and polar/dateline-crossing queries are unsupported.

Returned features retain their complete geometry, so their bounds may extend beyond the query. Tags match by union, not intersection. Empty matches are valid datasets with zero features; service failures return a nonzero exit code. Source-invalid geometries are retained and counted in metadata.

Acquisition uses OSMnx's cache and service backoff. HTTP requests have a 60-second timeout, but repeated service backoff can make total execution longer; use Ctrl+C to cancel. Acquisition timestamps record the request operation, not the edit date of source data or a guaranteed fresh download. Data files remain local and are excluded from Git.

## Verify

```powershell
uv run --project backend --locked pytest backend/tests -q
uv run --project backend --locked ruff check backend/src backend/tests
uv run --project backend --locked ruff format --check backend/src backend/tests
npm run lint --prefix frontend
npm run build --prefix frontend
# First install the test browser:
cd frontend
npx playwright install chromium
npm run test:e2e
cd ..
```

Automated tests use synthetic data and mocked acquisition. They check input validation, request errors, mixed-geometry/tag persistence, empty datasets, checksum corruption, and offline CLI reload. Live acquisition is a separate manual demonstration, not a CI network dependency.

## Technical references

- [Python version lifecycle](https://devguide.python.org/versions/)
- [Node.js release lifecycle](https://nodejs.org/en/about/previous-releases)
- [Vite setup requirements](https://vite.dev/guide/)
- [OSMnx installation](https://osmnx.readthedocs.io/en/stable/installation.html)
- [uv project management](https://docs.astral.sh/uv/guides/projects/)

## Run the demonstration interface

From the repository root, open two terminals:

```powershell
# Terminal 1: Python API
uv run --project backend --locked uvicorn uas_planner.api.app:app --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2: React interface
npm --prefix frontend run dev
```

Open http://127.0.0.1:5173. The development server proxies `/api` to port 8000. API documentation is at http://127.0.0.1:8000/docs.

1. Select a saved dataset. Use the CLI acquisition command above if none exists, then click **Refresh**.
2. Toggle Buildings, Roads & paths, Land use, and Natural features. Overlapping layers count each object only once in the visible total.
3. Select an object on the map or in the searchable table to inspect its tags. **Fit dataset** restores the complete extent; the dashed rectangle marks the query boundary.
4. Download GeoJSON, GeoPackage, or metadata. Downloads contain the entire dataset, including hidden layers, and verify stored integrity before returning data.

The API reads direct subdirectories of `data/`, each containing `features.gpkg` and `metadata.json`. Dataset folder names must start with an ASCII letter or digit, contain only letters, digits, underscores, or hyphens, and be at most 100 characters. Set `UAS_DATA_DIR` before starting the API to use another data root.

Saved vectors and statistics work without internet; the optional OpenStreetMap basemap needs network access. Turn off **Basemap** for an offline demonstration. Source features retain their full geometry outside the query boundary. Integrity verification checks storage consistency, not geographic accuracy. This local prototype loads datasets into memory; browser acquisition, large-area streaming, route planning, and public deployment are future scope.

Browser regression tests mock API responses and tile failures. Backend tests verify actual export bytes separately. On Windows, an existing Chrome installation can be used for tests with `$env:PLAYWRIGHT_CHANNEL='chrome'` instead of downloading Chromium.
