# UAS Mission Planner — Handoff

## Current status

- Local project directory: `D:\Aostfalia\develop\uas-mission-planner`.
- Intended GitHub repository: `Hunter3304/uas-mission-planner`, public.
- The local directory, this handoff file, and README.md have been created.
- Git initialization and remote repository creation have not yet been performed.
- No sprint, milestone, issue, branch, or application code has been created.
- Next step: discuss and agree on Iteration 001 scope and acceptance criteria with the user, then record the agreed plan before creating the sprint.

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
7. Validate changes and merge feature pull requests into the iteration branch. Close the corresponding Issue explicitly if necessary; retain its history. Delete the merged feature branch.
8. Validate the complete sprint and merge the iteration branch into `main` through a pull request.
9. Prepare sprint feedback in `doc/iteration/iteration-NNN/` and update README before the sprint merge. Record post-merge facts or further feedback through a documentation update as needed.
10. Update this file at the end of every work session, including incomplete or blocked sessions.

## Documentation locations

- `doc/plan/`: agreed sprint plans.
- `doc/iteration/`: sprint outcomes and retrospectives.
- `doc/decisions/`: architecture and technical decisions.
- `doc/research/`: literature notes and experiment methodology.

## Open questions and pending decisions

- Iteration 001 scope and acceptance criteria require discussion. Candidate scope: foundational environment and map-data acquisition prototype.
- Dependency versions, exact module layout, and development commands will be determined during implementation.
- README.md records the agreed stack and proposes Python 3.13.x, Node.js 24 LTS, npm 11, and uv. These version/tooling proposals await user confirmation and compatibility validation.
- Local environment observed: Python 3.13.13, Node.js 24.14.1, npm 11.11.0, Git 2.45.1.windows.1. uv was not found on PATH. These are observations, not validated project pins.
- No application tests have run because application code does not exist yet.

## Session outcome

- Read the handoff and checked local runtime versions.
- Consulted official Python, Node.js, Vite, and OSMnx documentation.
- Added an English README documenting architecture, stack, proposed runtime baselines, version-locking policy, workflow, and pending setup.
- No runtime changes or dependency installations were performed; application compatibility remains untested.
