# Iteration 013 Part 1 - Grouped controls and cached scenario layers

Date: 2026-10-22 (Europe/Berlin). Approved plan:
[Iteration 013](../../plan/iteration-013.md).
Tracking: assigned [Issue #114](https://github.com/Hunter3304/uas-mission-planner/issues/114)
in verified Milestone 12, created before `feature/114-hannover-map-controls`
from `iteration/013` at `4ed0023`.

Status: implementation, regression and final real-data acceptance complete.
Remote feature delivery remains pending. Parts 2-4 remain planned; main is unchanged.

## Result

- One independently collapsible source-grouped control area, with OSM building,
  DIPUL decision and notice/coverage derivatives correctly separated. GHSL legend
  matches zero/NoData colors; loaded cells show actual epoch/native resolution.
- Original DIPUL raw-overlay control and its fetching branch removed from the
  regional UI. Other source APIs and retained originals remain available. Bounded
  OSM is the only regional object renderer; duplicate fit control removed.
- No manual scenario-load button. Valid enabled layers prepare automatically,
  with explicit pending/loading/empty/error states and contextual retry.
- Successful shared scenario collections (including hidden/empty ones) are cached
  independently of display state. Hiding all layers or collapsing groups preserves
  them. Relevant scenario changes replace the current identity, with a 300 ms
  debounce, one browser job in flight and stale-response isolation. Backend
  admission separately limits actual preparation to one active job per app process.
- Dedicated endpoint section: default eight-site mode, or exact-coordinate mode
  with source-derived WGS84 bounds, field validation and retained full precision.
  The old override checkbox is removed. Actual endpoints drive markers/focus,
  request overrides and export metadata. Switching modes invalidates route results.

## Regression evidence

- Backend: **316 passed / one existing Windows permission skip**, 100.03 s.
  Includes two new tests of actual concurrent preparation admission and slot/
  terrain cleanup on success, validation failure and exception paths.
- Frontend: **28 browser tests passed**, 19.9 s, including six Part 1 cases:
  ten cached visibility/fold cycles, shared-source grouping, latest-scenario
  isolation, hidden completion/empty caches, failure/retry, GHSL reuse and exact
  endpoint validation/focus/export/mobile behavior.
- **14 real-stack smoke checks passed**, 34.4 s, preserving the small-area,
  native ABIT*, OFM, panel and export workflows.
- ESLint, TypeScript/production build and Ruff lint/format pass. Windows full
  backend/browser checks use isolated host processes because the sandbox blocks
  TestClient/native handles/local browser sockets. Existing nonfatal Starlette/
  Rasterio warnings remain.

## Real retained Hannover evidence

Operation/reproduction: [guide and isolated harness](../../experiments/iteration-013/README.md).
Final evidence is retained under `.cache/iteration013-part1-final/` against
the completed implementation, with `passed: true`, matching implementation hashes
and desktop/mobile screenshots visually inspected. Initial scenario loading is
**79.940 s**, the research route **50.982 s**. Ten visibility/fold cycles generate
**zero additional requests**, and GHSL loads once across visibility changes.
There are no page errors/mobile overflow; exact input/export endpoints agree.
OSM/study source hashes are unchanged and `services.json` verifies owned service
cleanup. No application code changed after this campaign.

Each conservative/research scenario response is about **85.75 MB** and includes
162,011 original building findings plus 324 DIPUL findings. This is the existing
whole-study constraint response, not the bounded OSM display API. Large first
preparation/transfer and retained memory remain explicit limits; no process-memory
ceiling or preparation-speed improvement is claimed. Subsequent matching display
toggles reuse those data without new requests or model preparation.

Earlier successful functional evidence is retained in
`.cache/iteration013-part1-real-v2/`: ten cache cycles with **zero additional
requests**, GHSL served once across off/on, 162,011 cached OSM building findings
and 324 DIPUL findings grouped separately, exact catalog-coordinate research route
approximately **3,715.6 m**, matching export endpoints and no mobile overflow/page
errors. Source OSM/study hashes are unchanged and owned services stopped.
Initial scenario load was **87.848 s**, route **50.774 s**. The final campaign above
supersedes those preliminary timings; these are local observations, not new targets.

The diagnostic v1 run did not complete: its extra DevTools response-body read
exceeded Chrome inspector retention. The harness now records headers and UI
facts without duplicating the large response body through DevTools. This was
an acceptance-harness failure and is not counted as a passed campaign.

## Remaining scope and limits

The page still requires the existing explicit scenario start/end interval. Part 4
will add departure-only automatic duration and reassessment; no guessed hidden
end-time is introduced here. Shared black selection outlines, the left inspector
and readable feature popups belong to Parts 2-3 and are not claimed delivered.

The cache is per page/dataset session, not persisted across browser reloads. Use
sidebar Refresh after replacing sources on disk. Initial full model preparation,
large uncertain-building constraint payloads and long route preparation remain
existing costs; this Part removes repeat loading on visibility changes. The
separate OSM viewport limits are preserved, not presented as a total-memory cap.
No source, permission rule, objective, source acquisition or private profile changes.

Feature publication, Linux/Windows/frontend CI, merge to `iteration/013` and
verified branch cleanup remain pending. Do not close Issue #114 or remove its
unmerged branch before actual delivery. Keep the iteration milestone/branch for
Parts 2-4; full iteration/main integration is outside this Part 1 delivery.
