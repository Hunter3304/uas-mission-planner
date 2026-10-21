# Iteration 012 Part 3 - Regional OSM map integration

Date: 2026-10-21 (Europe/Berlin). The user requested Part 3 completion and later
confirmed continuing the same task. Assigned Issue #108 in verified Milestone 11
was created before `feature/108-regional-osm-map` from `iteration/012` at `d5002c3`.
Part 3 implementation and local acceptance are complete at `b826f9d`.
[PR #109](https://github.com/Hunter3304/uas-mission-planner/pull/109) publishes
the feature to `iteration/012`; successful remote CI/integration and Part 4
remain separate gates at this record. Main is unchanged.

## Result

- Initial study fit displays the labelled bounded OSM aggregate grid and all eight
  sites. Zoom 15+ uses individual-object queries with a 10% buffered viewport,
  clamped to retained coverage; over-budget detail is discarded for an explicitly
  aggregate overview. No old full-regional feature request is issued.
- Four independent category switches, shared category precedence and category/cost
  palettes, independent selected-category costs and a representation-aware legend
  replace the uniform brown overlay. Unknown/default/unscored gray dashes and
  historical obstruction outlines retain demo semantics without changing rules.
- Canvas clicks and a bounded accessible object list fetch original-object tags,
  classifications and diagnostics on demand. Nondrawable diagnostic samples remain
  inspectable. Selection clears on viewport/style changes; late details cannot
  restore a closed selection. Source tags are text, including markup-like values.
- 180 ms settled-event debounce, AbortController cancellation and generation/source
  identity checks reject obsolete work. The four-entry / 8 MiB serialized-payload
  LRU rechecks readiness even when reusing a response. Loading, errors, empty,
  outside coverage, unavailable preparation and hidden categories are explicit.
- OSM, reference/boundary, route and external overlays use independent group
  lifecycles. Interactive paths share Canvas hit testing; the boundary is
  noninteractive and the route uses noninteractive SVG above it. This avoids an
  upper transparent canvas swallowing source clicks. Route changes preserve OSM
  selection and do not reload unchanged OSM data. OSM changes preserve the route.
- Focus origin/destination and fit-study controls support local detail navigation.
  Street tiles remain optional. Corrected tile cleanup to retain Leaflet's own
  remove listeners, preventing zoom errors after disabling the street basemap.
  Existing planning rules, source geometries and acquisition behavior are unchanged.

## Validation

- Backend regression: **313 passed / one existing Windows permission skip**,
  103.86 s; Ruff lint/format pass. No backend implementation changed.
- Frontend lint, TypeScript and production build pass. **22 browser tests** include
  five new Part 3 scenarios: actual Canvas clicks before/after route display,
  original tags, route/export preservation, bounded overview fallback, diagnostic
  inspection, readiness/capacity errors, snapshot mismatch, obsolete requests,
  empty/outside views, cached readiness and late detail cancellation.
- Existing **14 real-stack browser smoke tests** pass, preserving Braunschweig
  independent costs, population/DIPUL/terrain, OFM, planner controls and exports.
  Tests use installed Chrome because bundled Chromium is absent locally.
- Real retained Hannover functional evidence and screenshots are saved locally
  under `.cache/iteration012-part3-ui-final/`; reproduction is documented in
  `doc/experiments/iteration-012/README.md` and `verify-part3-ui.mjs`.
- The full overview contains 1,580 aggregate cells. Real MHH category detail
  contains 1,978 objects; all four category switches and four cost categories are
  exercised. Original object `relation/181180` is inspected, and the historical
  rheuma-podbi -> mhh research route retains length 3,715.5915279316932 m and exact
  catalog endpoints with OSM enabled. Route updates cause zero OSM requests and
  retain the current object selection. Desktop and 390 px mobile show no page
  errors or horizontal overflow; source SHA-256 remains unchanged.

The final route/export observation took **50.047 s** in this local browser run;
it includes source/model preparation and is not an off/on overhead benchmark.
The largest observed category-detail response was **713,165 bytes / 1,978 objects**;
the complete overview was **591,368 bytes / 1,580 cells**. All observed responses
remain within backend limits. These are functional-run observations rather than
Part 4 latency, heap or peak-memory acceptance.

## Remaining gates and limits

This is Part 3 functional acceptance. A serialized cache cap is not a measured
JavaScript heap cap. Part 4 still requires the 20-view browser latency campaign,
50-cycle state/resource measurements, actual browser/backend memory peaks and
three-run OSM off/on route-overhead comparison, plus complete iteration/main gates.
The existing conservative endpoint conflicts and strict unresolved inputs retain
their meanings; the tested route uses explicit historical research assumptions.
Mission-duration enforcement, new acquisition, expanded coverage, OFM planner
integration, 3D/flight phases and new permission rules remain outside this scope.

Original data, private profiles and user-owned services remain intact. Temporary
verification services are isolated on unused ports and stopped after acceptance.
