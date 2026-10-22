# Iteration 012 - Hannover OSM display performance and category colors

Date: 2026-10-21; Part 4 acceptance updated 2026-10-22 (Europe/Berlin).
Status: **Parts 1-3 delivered to iteration/012 on 2026-10-21;
Part 4 locally accepted and delivered to iteration/012 through PR #111 on
2026-10-22; independent main integration pending**.
The user reviewed the plan and requested completion of Part 1. Tracking: Milestone
11 / Issue #104; integration `iteration/012`; feature
`feature/104-osm-display-access` (merged and cleaned up). Part 1 PR #105 merged at
`64fff6a` after all three CI jobs passed in run `39628187365` attempt 2; Issue #104
is closed. This supersedes the earlier planning-only status for Part 1. Full sprint
integration to main awaits the remaining scope. See
[Part 1 implementation and acceptance](../iteration/iteration-012/part1.md).

The user requested review of Part 1 followed by Part 2 if it passed. Review
passed 47 focused tests and all 20 independently selected Hannover viewports.
Part 2 is tracked by assigned Issue #106 in Milestone 11 and
`feature/106-osm-classification-details` from `iteration/012`. Shared compact
classification, original-object details and demo style helpers are implemented;
PR #107 merged at `70ef8f4` after Linux/Windows/frontend Checks run `39648870309`
passed on reviewed head `c67ea50`. Issue #106 is closed and its merged feature
branch was removed locally/remotely after verification. See
[Part 2 acceptance](../iteration/iteration-012/part2.md).

The user requested Part 3 completion on 2026-10-21. Assigned Issue #108 in
Milestone 11 precedes `feature/108-regional-osm-map`, based on `iteration/012`
at `d5002c3`. Regional viewport/overview integration, category/cost controls,
original-object details and independent overlay lifecycles are implemented.
See [Part 3 acceptance](../iteration/iteration-012/part3.md) and merged
[PR #109](https://github.com/Hunter3304/uas-mission-planner/pull/109).
PR #109 merged at `cf23506` after Checks run `39670301509` explicitly passed
Linux Python, Windows Python and frontend on reviewed head `d33763a`. Issue #108
is closed; its merged feature was removed locally/remotely after ancestry and
expected-head verification, followed by fetch/prune and branch/remote checks.
Part 4's full acceptance and main integration remain pending; main is unchanged.
That Part 3-era acceptance note is superseded by
[Part 4 outcome](../iteration/iteration-012/outcome.md): assigned Issue #110 in
Milestone 11 precedes `feature/110-osm-real-acceptance` from `aba6a4e`. Local
acceptance passes unchanged warm API/browser/route gates, with actual process/
browser memory, 50-cycle state, exact exports and remaining startup/route costs
recorded. A bounded metadata-only catalog query fixes the observed map-label
full-source-loading bottleneck; full inspection/planner verification is intact.
PR #111 merged at `db7427f` after Linux/Windows/frontend run `39766913176`
passed on `af80714`; Issue #110 is explicitly closed, and feature cleanup is
verified locally/remotely. Independent main integration remains pending.

## Objective

Display retained Hannover OSM objects with the same category and independent
tag-cost color meanings as the Braunschweig demo, while keeping map interaction
and regional route planning usable. Deliver bounded viewport queries, compact
display attributes, object details on demand and explicit overview/detail states.

Use the saved `hannover-part1-v4` study and the exact `hannover-lehrte-5km` bounds
from [hannover-study.json](../experiments/iteration-008/hannover-study.json), with
its 5,000 m margin and all eight reference sites. Initial fit remains the complete
study boundary. Panning and zooming query retained local data only; they neither
acquire new OSM data nor expand the study. Braunschweig remains selectable.

## Confirmed baseline and causes

Read-only code and metadata inspection on 2026-10-21, local main `a034bc0`:

| Saved source | Objects | Distinct tag fields | Area |
|---|---:|---:|---:|
| `braunschweig-part1-v2` | 31,496 | 657 | 9.23 km2 |
| `hannover-part1-v4` | 326,334 | 1,481 | 411.74 km2 |

1. `/features` omits absent tags only when `experiment.json` exists. Regional
   `study.json` snapshots take the null-filling branch, creating 483,300,654
   attribute positions for Hannover before geometry and analysis. This is a code
   and metadata calculation, not a fresh full-response benchmark.
2. `RegionalMap.tsx` requests the complete `/features` collection without cost
   analysis and gives all OSM objects the same brown style. Successful loading
   alone would not reproduce the demo's category or cost colors.
3. The regional map already uses Leaflet Canvas. It still constructs all returned
   feature layers and property popups together, and its shared effect rebuilds
   OSM layers when route/constraint/selection state changes.
4. `load_dataset(compact=True)` still verifies and reads the complete dataset.
   Adding bbox filtering after this call would retain substantial request cost.
5. Existing full tag analysis builds detailed per-tag explanations and copies
   collections. Reusing that full-response form for every map feature would add
   avoidable payload and memory costs even after sparse serialization is fixed.

Historical high-memory/timeout observations are retained in
[Iteration 009 outcome](../iteration/iteration-009/outcome.md). This planning pass
does not repeat the known unbounded request or claim new timing/RAM measurements.

## User-visible result

- Four independently switchable OSM categories: buildings, roads/paths, land use
  and natural features, with the existing demo palette and a visible legend.
- A category view and a cost view. Cost view selects one of the four categories
  and uses its own 0-4 cost classification; categories are not added together.
- A click selects a stable OSM object and loads its original tags, category costs,
  classification explanations, rule version and geometry/source diagnostics.
- A full-study overview on initial fit, with all eight sites and explicit detail
  availability. Zooming in reveals individual colored objects; moving the map
  loads the newly visible part of the retained study.
- Loading, retry, empty viewport, outside coverage, overview, incomplete display
  and source-verification failures are distinguishable. A bounded or aggregated
  result is never labelled a complete set of individual source objects.
- OSM changes do not clear an existing route or reset the map position. Route
  updates do not rebuild an unchanged OSM layer.

## Display and classification contract

Reuse `core/costs.py`, `core/cost_rules.json`, `frontend/src/types.ts` and the
palette/unknown behavior in `BuildingCosts.tsx`. Extract shared helpers if needed;
do not introduce a second classification table in the regional UI.

| View | Meaning |
|---|---|
| Category | Buildings brown; roads blue; land use ochre; natural features green |
| Cost | Existing green-to-red palette for known costs 0 through 4 |
| Unknown/default/unscored | Existing gray treatment, including provisional numeric defaults |
| Paper obstruction flag | Existing qualified outline/detail meaning; not a current prohibition |

Objects can belong to several categories. Category-view precedence must match the
existing demo and be documented; toggles filter membership rather than changing
source tags. Cost view renders the selected category once per object. Whole-study
category counts may overlap and must not be summed as unique object totals.

The compact response includes identity, category membership and only the selected
style's score/status/default/flag fields. Full per-tag explanations are returned
by the detail interface. Preserve point, line, polygon and multipart identity;
points use bounded circle-marker rendering rather than per-object DOM icons.

Display simplification/clipping is a derived visualization operation. Record the
display mode and tolerance; calculate costs from original tags. Unsupported or
invalid geometries remain counted and inspectable through diagnostics. Do not
silently repair source originals or feed display geometry into route checks.

## Proposed architecture and interfaces

Part 1 implements summary, category-only features and overview; Part 2 adds cost
styles and original-object classification details. See the
[actual API guide](../experiments/iteration-012/README.md). Validate bounding boxes,
zoom, category/style enums and IDs, intersect requests with saved study coverage,
and reject malformed requests before expensive reads.

| Proposed endpoint | Purpose |
|---|---|
| `GET /api/datasets/{id}/study/osm/summary` | Source/rule identity, whole-study category counts, diagnostics and display readiness |
| `GET /api/datasets/{id}/study/osm/features?bbox=west,south,east,north&zoom=...&categories=...&style=category` | Bounded detail features; cost style also supplies `cost_category` |
| `GET /api/datasets/{id}/study/osm/overview?bbox=...` | Bounded, explicitly aggregated overview for views too dense for detail |
| `GET /api/datasets/{id}/study/osm/features/{element_type}/{osm_id}` | Original object tags/geometry and full existing classification explanations |

Responses identify the dataset checksum, rule version, requested/effective bounds,
representation, returned count, applicable limits and completeness. Distinguish
whole-study counts from viewport-returned counts; do not invent exact viewport
totals where a bounded probe only establishes that the limit was exceeded.

### Local query and cache design

- Verify the source once when preparing a display snapshot, then query an indexed
  GeoPackage or a separately generated spatial display cache directly by bbox.
  Verify the retained spatial index and representative query behavior first.
  Do not load the full GeoDataFrame or hash the complete source on every pan.
- Retain sparse `tags_json` for source/detail access. A derived display cache may
  store compact category/cost fields to avoid rescoring every object on every pan.
  Build it in bounded batches, with a manifest written after successful completion.
- Key derived products by verified source checksum, rule version, display schema
  and simplification settings. Define source-file/manifest change detection and
  explicit refresh/reverification; a filename or mtime alone is not integrity proof.
  Changed/corrupt inputs invalidate readiness and cached products rather than
  returning stale data under a verified label. Incomplete cache builds are unusable.
- Expose preparation progress/readiness separately from fast viewport queries.
  Coalesce preparation per dataset and bound query concurrency and cache memory.
  Do not let a browser request start an unbounded background preparation loop.
- The existing regional `/features` path must stop filling absent tags and must
  not remain an unbounded route to browser memory exhaustion. For oversized
  regional interactive responses, return a clear bounded-interface instruction.
  Retain small-area behavior and existing source-export semantics separately.
  Audit catalog/metadata reads too, so source selection does not repeatedly perform
  the full expensive verification while viewing the region.

### Browser loading and level of detail

- Keep Leaflet and the existing map. On settled move/zoom events, request the
  viewport plus a small bounded margin, clamped to study coverage.
- Debounce interactions, cancel obsolete fetches, reject late responses by request
  generation and snapshot identity, and use a bounded cache for nearby views.
  Browser cancellation alone does not cancel backend work: bound queries and
  cooperate with disconnect/cancellation where the execution model permits.
- Use separate persistent layer groups for OSM, route, sites and other overlays.
  Bind lightweight click handlers; create details/popups only for selected objects.
- Start with a proposed ceiling of 5,000 detail objects and 5 MiB uncompressed
  GeoJSON per viewport response, with a coordinate/geometry budget as well.
  Enforce bounds during query/serialization, not after constructing a huge result.
  Tune and document these provisional values from real dense-city measurements.
- If the viewport exceeds a budget, show an explicitly aggregated category
  overview (bounded grid, up to 2,000 cells) and a zoom-for-detail message. Counts
  follow a documented unique-object assignment rule and are not an inferred
  continuous risk surface. Cost coloring is individual-object detail; overview
  must not fabricate a fused cost score. A simple notice-only blank map does not
  satisfy the initial-view overview requirement.
- Full multizoom vector/raster tile generation and a WebGL map migration are
  deferred. Reconsider them from measurements if bounded queries and overview
  cannot meet this iteration's usability targets.

## Implementation sequence

The four Parts below form one coherent display delivery. Part 1 is tracked by
closed Issue #104 and Part 2 by closed Issue #106. Part 3 is delivered under
closed Issue #108; Part 4 is delivered through PR #111 / closed Issue #110.
Independent main integration is pending. Earlier unstarted scope is retained
below as the planned sequence.

1. **Part 1 - Bounded data access and preparation.** Confirm spatial index and
   safe sample baselines; define schemas, verification lifecycle and limits;
   implement compact indexed querying, display preparation, summary/overview and
   the regional legacy-endpoint guard. Verify count/identity and source changes.
2. **Part 2 - Shared classification and details.** Reuse existing classification
   rules and colors, expose compact styles plus on-demand details, define overlap
   semantics and geometry diagnostics, and check agreement with demo behavior.
3. **Part 3 - Regional map integration.** Add category/cost controls and legends,
   viewport/overview loading, request race handling, independent layer lifecycles,
   selected-object details and explicit coverage/limit feedback.
4. **Part 4 - Real-data acceptance and delivery records.** Exercise Hannover and
   Braunschweig, check route interaction, measure the agreed resource/performance
   budgets, and write reproducible evidence, operating notes and actual outcomes.

## Acceptance and measurement

### Correctness and compatibility

1. Real Hannover initial fit shows the saved boundary, eight sites and a labelled
   OSM overview; dense-city and Lehrte detail views show category-colored objects.
2. Each category toggle and selected cost category work. Existing demo and regional
   styles agree for identical tags, including multi-tag/multi-value objects,
   unknown/default values, costless obstruction flags and unscored values.
3. Spatial-query fixtures cover crossing lines/polygons, points, multipart shapes,
   boundary contact, empty/outside views and dense queries. Within-budget results
   agree with an independent spatial selection; over-budget results are explicit.
4. Clicking a rendered object resolves its original identity/tags and explanations.
   No absent tag is synthesized into a confirmed classification. Unsupported
   geometry diagnostics account for records excluded from rendering.
5. Rapid pan/zoom, layer/style changes and dataset refresh do not apply stale
   results. Selection is cleared or explicitly retained when its object leaves
   the view; loading/errors cannot masquerade as a verified empty result.
6. Source/rule changes invalidate prepared data. Partial/corrupt caches, malformed
   requests and invalid IDs fail clearly. Original file checksums remain unchanged.
7. With OSM enabled, route planning still returns its correct result/diagnostics.
   Compare a documented deterministic real research A* case with OSM off/on;
   retain the conservative endpoint rejection and exact displayed-route export.
   Map colors never change planning costs, permissions or source geometry.
8. Existing Braunschweig category/cost inspection, DIPUL/GHSL/terrain controls and
   independent OFM preview retain their behavior. Test desktop and 390 px mobile;
   saved OSM remains usable with the online street basemap disabled.

### Performance evidence and proposed gates

Use the retained full Hannover dataset on the same local machine/browser, with
hardware, runtime versions, source hashes, viewport dimensions and query sequence
recorded. Keep preparation, cold requests and warm requests separate. Measure
backend private/working-set memory and browser memory where instrumentation allows;
unavailable measurements must be identified, not replaced with estimates.

- Record first preparation time/peak memory, cold viewport latency, response bytes,
  returned object/coordinate counts, API latency and time until the map is usable.
- Use at least 20 fixed warm queries spanning MHH/Podbi, dense central Hannover,
  Lehrte and boundary views. Proposed targets: warm API p95 <= 2 s and settled
  viewport-to-interactive p95 <= 3 s, excluding initial cache preparation.
- Verify every response against the adopted object/byte/geometry ceilings. Test
  50 pan/zoom/style cycles with bounded cache occupancy and no accumulating stale
  layers/requests; record memory peaks and retained state after the sequence.
- Run a controlled route case with OSM off and on, at least three runs each.
  Proposed target: median route completion overhead <= 20%, no frontend timeout,
  and identical deterministic route meaning/output. Report preparation versus
  solving time so cache differences do not create a misleading comparison.
- These numbers are draft acceptance targets, not observed performance. Confirm
  or explicitly revise them with measured baseline evidence before closeout;
  missed targets remain documented gaps rather than an unqualified pass.

Run targeted backend/API classification and spatial tests, frontend lint/build,
mocked browser interaction tests and real-stack smoke tests. Before any authorized
delivery, run repository backend/Linux/Windows/frontend integration gates. Real
Hannover evidence is mandatory; small synthetic fixtures alone are insufficient.
The initial documentation-only plan needed no application tests. Part 1 requires
the relevant implementation gates and real-data checks recorded in its outcome.

## Boundaries, artifacts and workflow

This iteration changes OSM viewing and its bounded local access path. New source
acquisition, region expansion, planner objectives, DIPUL permission rules, OFM
integration, 3D/flight phases and mission-duration enforcement are outside scope.
Original snapshots and private profiles remain intact. Display caches stay local
and rebuildable; detailed source data are not added to Git as implementation assets.

Expected implementation documentation: `doc/iteration/iteration-012/outcome.md`
and a reproducible guide under `doc/experiments/iteration-012/`; measurements,
screenshots and derived cache artifacts stay in new local `.cache/` locations.
Update README/HANDOFF with verified behavior and remaining limits at delivery.

When implementation is requested, follow the established milestone ->
`iteration/012` -> assigned issue before feature branch workflow. Record actual
tracking IDs and authorized scope then; do not infer a GitHub milestone number
from the iteration number. Apply the existing feature CI/merge/cleanup and
independent main integration gate within the user's authorized delivery scope.

## Technical references

- [Pyogrio spatial filtering and selected-column reads](https://pyogrio.readthedocs.io/en/latest/introduction.html#filter-records-by-spatial-extent)
  support the proposed local bbox queries; actual retained index behavior needs
  measurement during Part 1.
- [Leaflet 1.9.4 API](https://leafletjs.com/reference.html) documents Canvas,
  move/zoom events, GeoJSON styles and independent layers used by the existing app.
- [Existing independent tag-cost rules](../rules/tag-cost-tables.md) remain the
  source of classification semantics for both regional and small-area displays.
