# UAS Mission Planner

A Python-based geospatial data and UAS mission-planning research project, developed for an internship and a subsequent bachelor's thesis.

## Project status

Iteration 001 is in progress: specify an area, acquire OSM features, save, and reload. The public repository is [Hunter3304/uas-mission-planner](https://github.com/Hunter3304/uas-mission-planner). See the [iteration plan](doc/plan/iteration-001.md).

Read [HANDOFF.md](HANDOFF.md) before starting work and update it at the end of each work session.

## Architecture

- One public GitHub repository, intended name: `Hunter3304/uas-mission-planner`.
- Separate frontend and backend code, running as separate local processes.
- The React frontend communicates with the Python backend through HTTP APIs.
- The Python research core is independent of React and FastAPI. API handlers and experiment scripts call the same core.
- Default project language: English.

## Technology stack

The architecture and runtime baselines are agreed. Dependency versions are recorded in `backend/uv.lock` and `frontend/package-lock.json`; the frontend application is deferred beyond the initial core round trip.

| Area | Technology | Status |
| --- | --- | --- |
| Research core | Python 3.13.13 | Installed and verified |
| HTTP API | FastAPI | Agreed |
| Frontend | React 19.3.0, TypeScript 6.0.3, Vite 8.3.1 | Dependencies installed; application deferred |
| Map interface | Leaflet | Agreed |
| Frontend runtime/tooling | Node.js 24.14.1 LTS, npm 11.11.0 | Installed and verified |
| Map data | OpenStreetMap through OSMnx/Overpass | Agreed |
| Geospatial processing | GeoPandas, Shapely, pyproj | Agreed |
| Storage and export | GeoPackage, GeoJSON, JSON metadata | Agreed |
| Python environment and dependency management | uv 0.11.6, project-local virtual environment, uv.lock | Installed and verified |
| Frontend dependency management | npm, package-lock.json | Installed and locked |
| Python quality checks | Ruff, pytest | Installed |
| Frontend quality checks | ESLint, TypeScript checks, relevant component tests | Proposed; test tooling selected when needed |
| Development | Local Windows environment, VS Code | Agreed |
| Version control and automation | Git, GitHub, GitHub Actions | GitHub agreed; CI configuration pending |

### Runtime and dependency policy

- Agreed runtime lines: Python 3.13 and Node.js 24 LTS.
- Select and record exact runtime patch versions after compatibility validation. Locally observed versions are not automatically project requirements.
- Validate installation and import of the geospatial stack on Windows before finalizing the Python baseline.
- Select mutually compatible stable package releases during scaffolding; do not select prereleases by default.
- Commit backend and frontend dependency lockfiles once generated. Use the same locked dependencies in local development and CI.
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

Dependencies are installed. Python imports, frontend dependency resolution, GeoPackage mixed-geometry persistence, and coordinate projection have passed environment checks. These checks do not yet demonstrate live OSM acquisition.

### Install locked dependencies

From the repository root, install Python dependencies with `uv sync --project backend --locked` and frontend dependencies with `npm ci --prefix frontend`. Use the project environment rather than installing packages into system Python. The frontend has no application or development-server script in this iteration.

## Planned repository layout

These directories describe the intended layout; they have not yet been created.

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

The agreed first iteration establishes the development foundation and a command-line map acquisition prototype: specify an area, retrieve OSM features, save and reload the dataset, and record acquisition metadata. Interactive display and API endpoints are deferred. Acceptance criteria are recorded in the iteration plan.

## Technical references

- [Python version lifecycle](https://devguide.python.org/versions/)
- [Node.js release lifecycle](https://nodejs.org/en/about/previous-releases)
- [Vite setup requirements](https://vite.dev/guide/)
- [OSMnx installation](https://osmnx.readthedocs.io/en/stable/installation.html)
- [uv project management](https://docs.astral.sh/uv/guides/projects/)
