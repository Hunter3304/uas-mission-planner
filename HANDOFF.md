# UAS Mission Planner — Handoff

## Current status

- Public repository: https://github.com/Hunter3304/uas-mission-planner.
- Local directory: `D:/Aostfalia/develop/uas-mission-planner`.
- Iterations 001–003 are delivered. Iteration 003 completes the user-requested error handling, small-example tests, README and stage version.
- Sprint PR #29 merged into main at `6d33ceae8d227eba48ee2c08d716fc37448edd5e`. Main CI run 36174938461 passed Windows/Linux Python and frontend checks, including the real-stack smoke test.
- Published release: https://github.com/Hunter3304/uas-mission-planner/releases/tag/v0.3.0. Annotated tag v0.3.0 points to that tested sprint commit; publication date 2026-09-25.
- Milestone #3 is closed. Implementation issues #23–#25 are closed; PRs #26–#28 merged and their branches were deleted locally/remotely, pruned and verified.
- This final post-merge documentation is tracked by #30. Its temporary branch follows the mandatory cleanup policy below. Subsequent main documentation commits do not move the published tag.
- Validation: 42 local Python tests passed (one Windows symlink-permission skip), nine mocked browser tests and one real-stack browser test passed; Ruff, ESLint and production build passed.
- Existing data/braunschweig-demo remains verified with 91 features. data/offline-sample contains three synthetic features. Both are local and excluded from Git.
- No further implementation or next sprint is approved. Discuss the next plan with the user.

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

- Iteration 003 is complete. Discuss subsequent scope before creating another sprint.
- Runtime baseline is approved and validated: Python 3.13.13, Node.js 24.14.1, npm 11.11.0, uv 0.11.6. Git is 2.45.1.windows.1.
- OSMnx may retry after service backoff without an overall deadline; Ctrl+C cancels acquisition. HTTP timeout is not a total execution limit.
- Geometries are complete source features, not clipped. Invalid geometries are retained and counted. Unknown tags are preserved as JSON-compatible values.
- Acquisition timestamps may describe a cache read, not the original source download/edit. Source snapshots require preserving the local dataset.
- Frontend and read-only API are implemented. Acquisition remains a CLI operation; refresh the UI after saving new data.
- The current API loads and verifies complete small datasets per request; large-data performance remains future scope.

## Session outcome

- Hardened shared dataset validation, CLI cancellation and frontend error/download handling.
- Added an offline synthetic point/line/polygon sample and a real API/browser round-trip test.
- Unified stage versions, prepared changelog, rewrote README quick start and startup troubleshooting.
- Do not leave agent-owned demonstration servers running. Test servers use 8011/5175 and terminate after testing; do not stop user-owned 8000/5173 services.
- Completed main integration and published v0.3.0 after successful main CI. Implementation branches were removed and verified.
- Test ports 8011/5174/5175 were confirmed free after tests. No demonstration server was left running by this session. User-owned development services were not stopped.
- Restart both development terminals after updating to load the latest Python code and Vite configuration.
- Known non-blocking dependency warning: Starlette deprecates its current httpx test-client integration. CI also reports older action runtime deprecation notices; schedule deliberate tooling updates in future work.

## Start the interface

Run from the repository root in two terminals:

```powershell
uv run --project backend --locked uvicorn uas_planner.api.app:app --host 127.0.0.1 --port 8000
npm --prefix frontend run dev
```

Open http://127.0.0.1:5173. Dataset files are local and excluded from Git. See README for acquisition and verification commands.

For a network-free example after installing dependencies: `uv run --project backend --locked uas-planner sample --output data/offline-sample`. Existing directories are not overwritten. Test with `npm --prefix frontend run test:smoke`.
