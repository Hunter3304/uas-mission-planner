# UAS Mission Planner — Handoff

## Current status

- Local project directory: `D:\Aostfalia\develop\uas-mission-planner`.
- GitHub repository: https://github.com/Hunter3304/uas-mission-planner (public).
- Iteration 001: https://github.com/Hunter3304/uas-mission-planner/milestone/1.
- Approved scope: specify an area -> acquire OSM data -> save -> reload.
- Implementation Issues #1-#4 are closed. Feature PRs #5-#8 merged into `iteration/001`; their feature branches were deleted.
- Sprint PR #9 merged into `main` at commit `4c16cc9ce1f3e6ec10c10e5987f5d29b90b15774` on 2026-09-25. Iteration 001 Milestone is closed.
- This post-merge documentation update records completed delivery; no application changes are included.
- Python and frontend dependencies are installed and locked. The Python command-line core is implemented. React application screens and HTTP endpoints are deferred.
- Local validation: 20 offline tests pass; Ruff passes; a real Braunschweig acquisition saved and reloaded 91 features.
- Remote validation passed on Windows and Linux, plus frontend dependency installation. The sprint PR checks are successful.
- Next step: demonstrate the saved dataset and discuss the next sprint with the user. No next sprint or implementation scope is approved.

## Local commands and demonstration

- Install dependencies: `uv sync --project backend --locked` and `npm ci --prefix frontend`.
- Run tests: `uv run --project backend --locked pytest backend/tests -q`.
- Command help: `uv run --project backend --locked uas-planner --help`.
- Reload live sample: `uv run --project backend --locked uas-planner inspect data/braunschweig-demo`.
- Sample files: `data/braunschweig-demo/features.gpkg` and `metadata.json` (excluded from Git).
- GitHub CLI: `D:\Aostfalia\app\GitHubCLI\bin\gh.exe`, version 2.101.0, authenticated as Hunter3304. It is invoked by absolute path; no global PATH change was made.
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

- `doc/plan/`: agreed sprint plans.
- `doc/iteration/`: sprint outcomes and retrospectives.
- `doc/decisions/`: architecture and technical decisions.
- `doc/research/`: literature notes and experiment methodology.

## Open questions and pending decisions

- No new sprint is approved. Discuss subsequent scope with the user before creating it.
- Runtime baseline is approved and validated: Python 3.13.13, Node.js 24.14.1, npm 11.11.0, uv 0.11.6. Git is 2.45.1.windows.1.
- OSMnx may retry after service backoff without an overall deadline; Ctrl+C cancels acquisition. HTTP timeout is not a total execution limit.
- Geometries are complete source features, not clipped. Invalid geometries are retained and counted. Unknown tags are preserved as JSON-compatible values.
- Acquisition timestamps may describe a cache read, not the original source download/edit. Source snapshots require preserving the local dataset.
- Frontend dependencies are ready, but there is no frontend app/build yet; CI only validates its dependency installation.

## Session outcome

- Rechecked branch cleanup at the user's request: actual local and remote branches were only `main` and `iteration/001`; no feature branches remained.
- Clarified mandatory local/remote deletion and verification for all merged feature and temporary documentation/fix branches.

- Installed and verified locked dependencies and checksum-verified GitHub CLI; user completed browser authorization.
- Created the public repository, Milestone, and Issues before their feature branches.
- Implemented acquisition, GeoPackage persistence, manifest validation, and command-line fetch/inspect.
- Live testing exposed OSMnx index names `element/id`; normalized both these and the older `element_type/osmid` schema and added regression coverage.
- A temporary-directory sandbox restriction affected the first environment smoke test; rerunning within the workspace passed. No application defect remained from that check.
- Final validation passed: 20 local tests, Ruff, the 91-feature real-data round trip, Windows/Linux CI, and frontend dependency checks.
- Merged the complete iteration through PR #9 and closed its Milestone. README and retrospective now describe delivered functionality and actual merge evidence.
