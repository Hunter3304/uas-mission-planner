# Iteration 008 Part 3 — Regional weighted algorithm integration

Date: 2026-10-06 (Europe/Berlin).

Integration update, 2026-10-07: PR #73 merged into iteration/008 at `e7544d5`
after Windows/Linux backend and frontend CI passed in run `37663352235`.
All 10 mocked browser tests also passed with clean Windows exit (6.2 s).
Main integration is authorized and has its own successful-CI gate; final main
merge facts are reported in the delivery response. Earlier local-only status
records the implementation stage. Parts 4/5 remain deferred.
Tracking: Milestone 7 / [Issue #72](https://github.com/Hunter3304/uas-mission-planner/issues/72).
Branch: `feature/72-regional-routing`, based on `iteration/008` fast-forwarded to
main's Part 2 merge `848763a`. Implementation authorized; no publication or merge
performed. Parts 4/5 remain deferred.

## Behavior

`RegionalPlanner` verifies the retained source study and native terrain, selects
exact catalog endpoints and delegates graph search to existing A*/Dijkstra or
continuous search to official native ABIT*. A private checker hook in the shared
routing core applies `RegionalConstraints` to points, complete motions, connectors
and final routes. It cannot be serialized as a prepared source model. Existing
Braunschweig/synthetic entry points retain their existing behavior.

Weighted building routing defaults to risk/distance weights 0.9/0.1. Risk uses
the existing unbuffered centerline integration, max-overlap policy and explicit
background assessment. GHSL is not a routing objective. Distance mode uses the
same regional checker. Clearance and altitude belong to the supplied scenario;
speed changes mission time estimates, never geometry or edge cost.

Preflight distinguishes blocked exact endpoints from unresolved inputs before
grid or native setup. Unknown height, source geometry, terrain and applicability
remain conservative in research mode. Native unavailability, zero-budget timeout,
no graph path and resource failures retain the shared planner outcomes.

Full-region grids are capped at 10,000 candidate cells and 30 seconds of cooperative
grid preparation. Default spacing is 250 m, explicitly recorded; there is no silent
coarsening or region cropping. ABIT* does not construct the discrete graph. Each
complete motion is subdivided into metric segments of at most 500 m before native
terrain queries; all pieces and their safety envelopes are checked. The 10,000-piece
limit and terrain pixel/NoData limits retain unresolved outcomes. Larger clearance
can still exceed native query limits.

The per-solve motion cache holds at most 50,000 point/segment entries and never
crosses a model or mode. Prepared identity records source/terrain/rule provenance,
scenario, grid, objective, weights, background and endpoints. No cross-request
model cache bypasses source checksum verification. The identity conservatively
includes speed and budget; these do not affect geometric cost. Regional source
verification remains an in-memory, request-scoped operation.

Success receives a fresh full-route constraint check, exact endpoint verification
and independent metric length/objective recomputation. Injected cost corruption is
rejected as computational failure. Exports include mission, source/rule signatures,
assumptions, diagnostics, costs and timings. Source preparation, grid preparation,
search and total time are separate; cruise time is L/v with range [L/35, L/25].

## Interfaces

CLI `study-route` and POST `/api/datasets/{id}/study/route` share
`plan_regional_route`. The API accepts a contained terrain dataset ID, never an
arbitrary filesystem path. CLI output is JSON; optional GeoJSON output never
overwrites an existing file. API `export: true` returns GeoJSON metadata and only
successful route geometry.

The explorer identifies regional studies and presents basic regional planning
controls. Scenario start/end must be explicitly supplied with offsets; no saved
engineering date is automatically treated as the user's flight schedule. Parameters
invalidate results and cancel obsolete client requests. Export uses the displayed
snapshot without another solve. Location IDs are typed at this stage; named endpoint
selectors, regional route rendering and independent map layers remain Part 4.

## Validation and limits

Final integration review, 2026-10-07: user authorized commit, push and PR delivery
through iteration/008 into main, gated by successful CI. Full backend regression
on the reviewed source: **221 passed / one existing Windows permission skip**
(83.40 s). Ruff lint/format and frontend lint/build pass. Source datasets remain
excluded from Git. The earlier local-only status is historical.
All **12 real API/browser smoke tests passed with exit code 0 (31.5 s)** when
executed with normal Windows process permissions. This confirms the earlier
teardown stall belongs to sandbox process cleanup: Playwright's Windows server
shutdown uses taskkill, then waits for process/pipe closure. No application source
or test dependency change was needed. Local API, map, planning and export operate;
retained real Hannover source uncertainty still yields unresolved_input.

Initial full backend regression: 219 passed / one existing Windows permission skip
(81.33 s), including ten new regional cases. Subsequent checks additionally cover
cooperative preparation deadlines and native unavailability/zero budgets.
Final regional suite: 12 passed (20.12 s). All 50 Python files pass Ruff formatting.
Ruff lint/format, frontend lint/production build pass. Browser checks cover default
weights, shared request semantics, result invalidation and export without solving.
All 10 mocked browser tests pass (6.4 s), including regional controls and a
390-pixel mobile overflow check; `.cache/part3-mobile.png` was visually inspected.
All 12 real API/browser checks individually passed with one worker. An initial
six-worker run exceeded the existing grid assertion's five-second wait; the
single-worker rerun passed that assertion in 1.5 s. The Windows smoke runner then
stalled during auxiliary-server teardown and was interrupted after every test
passed; no successful runner exit is claimed. A writable offline uv cache was used
because the sandbox could not initialize the account's default cache.
Native OMPL is exercised on the installed Windows runtime; tests skip successful
native solves on hosts without the optional dependency. Remote CI and Linux
runtime validation have not been run for this local implementation.

Offline real-source verification tested 24 combinations: 100/120 m, strict/research,
three algorithms and risk/distance objectives for rheuma-podbi → mhh. All correctly
returned `unresolved_input` without searching. Source preparation took approximately
37 seconds per altitude. Retained geometry and zone uncertainty, including incompatible
vertical references, remain reported. No real route or flight permission is claimed.
See [compact evidence](part3-evidence.json); the checksummed full local report is
`.cache/hannover-part3-evidence.json`. This is integration preflight, not Part 5's
multi-pair flight experiment matrix.

Synthetic integration tests independently demonstrate graph objective agreement,
lower-risk detours versus the distance baseline, successful native ABIT*, exact
endpoints, speed-only timing changes, same-site routes, resource limits and CLI/API
agreement. Full-region successful-search performance remains unestablished while
the retained real model is unresolved. Budgets are cooperative; a single source
read/check can exceed a deadline. No original data or dependencies were changed.
