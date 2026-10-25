# Iteration 013 - Hannover UI and cruise arrival outcome

Date: 2026-10-22. Scope: Hannover regional explorer/planning UI and consistent
automatic cruise intervals. Plan: [Iteration 013](../../plan/iteration-013.md).

All four Parts are delivered to iteration/013 through PRs #115, #117, #119 and
#121. Part 4 merged at `81ec028` after Checks run `39947203136` passed on final
head `500d496`: Windows 339 passes; Linux 329 passes / 10 skips; frontend lint/
build, 55 browser and 14 real-stack smoke passes. Issue #120 is closed and
local/remote merged-feature cleanup is verified. Explicit user publication
approval on 2026-10-23 superseded the earlier automatic block. Full iteration/main
CI/integration remains pending. Main is `4ed0023`; Milestone 12 remains open.

## Delivered behavior

- One collapsible source-grouped control area: base/references, OSM, GHSL, DIPUL
  and scenario coverage. Legacy uniform OSM/raw DIPUL controls, manual layer-load
  button and coordinate override checkbox are removed. Current category-colored
  buildings are intentional, not the removed legacy renderer.
- Enabled scenario overlays load automatically and retain all response collections
  for same-identity visibility toggles. GHSL has its own cached load. Errors,
  source refresh and stale preparation remain explicit. No toggle triggers routing.
- Endpoints occupy a separate section, defaulting to the eight saved sites.
  Exact-coordinate mode alone exposes longitude/latitude inputs and study bounds.
- OSM/DIPUL/GHSL/derived areas share one selection, actual black geometry outline
  with white halo, left inspector and short map summary. Mobile uses one collapsible
  sheet. Hiding/changing sources and stale collections clear selection; ordinary
  group/popup closure does not. Aggregate/diagnostic objects stay distinguished.
- Readable source cards show facts, units, scoped decisions and uncertainty.
  Original/nested attributes, matched rules and provenance expand separately;
  JSON is advanced only. Color-mode help explains type/category precedence and
  independent 0-4 scores. GHSL zero/NoData labels match its existing palette.
- Part 4 adds departure-only planning, actual-route L/v arrival, complete-interval
  restriction/evidence rechecks, provisional/final overlay identity and matching
  exports. UTC arithmetic handles DST/midnight/fractional time. Failed/stale routes
  show no ETA. Historical explicit interval API/CLI semantics remain available.

## Evidence and remaining limits

See [Part 1](part1.md), [Part 2](part2.md), [Part 3](part3.md), [Part 4](part4.md)
and the [operation guide](../../experiments/iteration-013/README.md) for individual
tracking, validation and actual delivery status. Final local Part 4 regression is
338 backend passes / one existing Windows skip, 55 browser and 14 smoke passes.
Final integrated Hannover acceptance passes with all 21 application hashes matched,
unchanged original hashes and owned services stopped. The actual 3715.592 m route
at 30 m/s takes 123.853 s; automatic and explicit baseline geometry/cost agree.
Initial/final layers take 74.268/74.498 s; automatic/baseline requests take
50.185/50.595 s. Conservative invalid-endpoint failure has no ETA. Export,
completed assessment scope, desktop/mobile, Parts 1-3 interaction and zero-request
cached toggles pass. The feature CI gate passed; the independent complete-iteration
gate remains before claiming main delivery. All 21 application hashes still match
after integration with no logical source change.

Unchanged limits: full scenario preparation/payload costs, bounded OSM queries,
current-page cache lifetime and request-local source preparation. Data completeness,
source heights/units, terrain support, evidence scope and permission are not
invented by UI formatting or successful research planning. Cruise estimates omit
takeoff/landing/wind/dynamics. There is no source acquisition expansion, scoring/
objective revision, broad planner cache redesign, other-page UI migration or OFM
integration into planning. Originals, private profiles and user services remain.
