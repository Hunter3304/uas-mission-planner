# Part 3 local validation — 2026-10-01

Environment: native Windows x64 Python 3.13.13, repository backend venv,
patched official OMPL 2.0.1+uas.1, installed Chrome. Comparison reports also
record Python/platform and geometry/native package versions. No real-data
acquisition was performed.

## Backend

Executed from `backend/`, with task-specific writable pytest directories:

```powershell
.venv/Scripts/python.exe -m ruff check src tests
.venv/Scripts/python.exe -m ruff format --check src tests
.venv/Scripts/python.exe -X utf8 -m pytest -q --basetemp D:/Aostfalia/tmp/part3-final-verification-02 -o cache_dir=D:/Aostfalia/tmp/part3-final-cache-02 --tb=short --durations=5
```

Result: **158 passed, 1 skipped in 44.16 s**. The skip is the existing Windows
symlink-creation permission check. Other warnings are upstream FastAPI test-client
and Rasterio/Affine deprecations, not test failures.

The final comparison tightening checks endpoints against the requested mission,
not merely returned metadata. Added injected wrong-cost/wrong-endpoint coverage,
then ran the complete affected suite:

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest tests/test_planning_controls.py -q --basetemp D:/Aostfalia/tmp/part3-controls-final-02 -o cache_dir=D:/Aostfalia/tmp/part3-final-cache-02 --tb=short
```

Result: **8 passed in 21.24 s**. Ruff check and format check subsequently passed.
The subprocess regression verifies native CLI JSON stdout and absence of native
leak diagnostics; the native owner-lifetime regression requires prompt release.
Repeated native comparison checks obtain independently verified exact paths.

## Frontend and real API

Executed from `frontend/`:

```powershell
npm run lint
npm run build
$env:PLAYWRIGHT_CHANNEL='chrome'
$env:UV_CACHE_DIR='D:/Aostfalia/tmp/part3-uv-cache'
$env:PYTHONUTF8='1'
npm run test:e2e
npm run test:smoke -- --workers=1
```

ESLint and TypeScript/Vite build passed. Mocked Chrome suite: **9 passed**.
Final real API Chrome smoke suite: **9 passed in 30.5 s**. It uses freshly
generated isolated sample/source/routing/risk datasets and a local test API.
Basemap network requests are blocked in the browser checks.

New browser assertions verify parameter propagation, displayed-result export
without another request, exact geometry/provenance retention, invalidation,
zero-budget failure with zero exported features, independently scored comparison
tables, JSON report download and 390 px mobile layout. Prior route/grid/source
and download workflows remain covered. The smoke config retains the optional
native extra on Windows; Linux can report the unavailable planner explicitly.

Restricted Windows process teardown stalled a first browser run after assertions;
the final runs used process permissions for test-owned teardown. Initial uv/pytest
cache directories were inaccessible, so verification used task-specific workspace
directories. No compiler/runtime installation or dependency upgrade was needed.

## Measurements and delivery state

- [Synthetic comparison](part3-synthetic-comparison.json): six exact verified
  paths; weighted A* and Dijkstra agree; ABIT* verified exact rate 3/3 at 2 s/run.
- [Saved real-data comparison](part3-real-unresolved.json): three graph
  `unresolved_input` results and one preparation-budget `timeout`; no exact route.
- `git diff --check` passed. Existing Part 2 edits and historical records remain.
- All implementation is local on `feature/60-planner-controls`. No commit, push,
  PR, merge or branch cleanup was performed. Remote CI, Linux native ABIT* and
  a second clean Windows host remain unverified.
