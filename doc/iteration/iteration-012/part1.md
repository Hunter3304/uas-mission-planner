# Iteration 012 Part 1 - Bounded Hannover OSM display access

Date: 2026-10-21 (Europe/Berlin).
User-authorized Part 1; Milestone 11 / Issue #104. Integration branch
`iteration/012`; feature `feature/104-osm-display-access` from main `a034bc0`.
Local implementation and acceptance are complete at `ccfcd31`. Parts 2-4 and
full main integration remain pending.

## Delivery state

Milestone 11 and Issue #104 exist on GitHub. On 2026-10-21 the user explicitly
authorized pushing `iteration/012` and `feature/104-osm-display-access` to
`https://github.com/Hunter3304/uas-mission-planner`, creating a PR, and merging
Part 1 into `iteration/012` after successful CI. Repository identity/push permission
and the remote main base `a034bc0` were verified before publication. This supersedes
the earlier automatic-approval rejection; that rejected push was not executed.

Implementation and local acceptance are complete. Publication and the independent
Linux/Windows/frontend feature gate proceed under this explicit authorization;
actual PR/run/merge and cleanup facts are recorded after verification. Issue #104
remains open until the Part 1 merge is verified. Milestone 11 remains open for
Parts 2-4. No main merge is included in this delivery.

## Result

The regional OSM display path now uses explicitly prepared, indexed SQLite
snapshots, bounded viewport queries and an aggregate overview instead of a
null-expanded full-source response. Implemented endpoints:

- `/api/datasets/{id}/study/osm/summary`.
- `/api/datasets/{id}/study/osm/features?bbox=west,south,east,north&zoom=16`.
- `/api/datasets/{id}/study/osm/overview?bbox=west,south,east,north`.

Preparation is CLI-only: `study-osm-prepare`. Builds stream source objects with
periodic commits, use an exclusive filesystem lock and publish the manifest last.
Source/cache checksums establish initial trust; source/rule identity and file
change detection invalidate it. Warm reads neither hash/read the full source nor
construct full GeoDataFrames. Windows native ChangeTime also detects same-size
edits with restored modification timestamps. Query connections and concurrency
are bounded; source and cache changes during queries reject the result.

Category membership and stable OSM identity are available in compact properties.
Detail ceilings are 5,000 objects, 5 MiB, 100,000 coordinates, 10,000 candidates
and a two-second cooperative budget. Limits produce incomplete/overview feedback
or an explicit retry response, never a false complete viewport. The overview
assigns each valid supported object to one of up to 1,600 cells, with separate
category counts and no inferred cost surface.

Legacy oversized regional `/features` requests are rejected before full loading;
source-byte and analysis guards plus sparse/raw-response limits cover smaller
regional cases. Regional catalog/details use metadata and prepared statistics;
metadata-only entries remain unverified, and the explorer respects that flag.
Existing small-area APIs and original-source export contracts are retained.

## Real retained Hannover acceptance

Final reproducible evidence: `.cache/iteration012-part1-real-final/evidence.json`
and `overview.geojson`. Initial exploratory evidence is retained separately at
`.cache/iteration012-part1-real-v1/`.

| Observation | Final result |
|---|---:|
| Original source objects / source R-tree entries | 326,334 / 326,334 |
| Drawable supported valid objects | 326,311 |
| Invalid source geometries, retained as diagnostics | 13 |
| Unsupported GeometryCollection records, retained as diagnostics | 10 |
| Building / highway memberships | 175,367 / 110,706 |
| Land use / natural memberships | 9,549 / 30,837 |
| Explicit preparation including final verification | 68.90 s |
| Separate cold source/cache verification | 0.615 s |
| Separate first API snapshot verification | 0.594 s |
| Warm API viewport queries | 20 |
| Warm API p95 / maximum | 0.191 s / 0.322 s |
| Complete queries agreeing with independent source selection | 20 / 20 |
| Returned objects per tested viewport | 8-3,594 |
| Maximum tested detail payload | 1,123,187 bytes |
| Full-region overview | 1,580 cells / 591,227 bytes |
| Legacy full-source guard latency | 0.008 s |
| Warm regional dataset-details latency | 0.023 s |

GDAL/Pyogrio independently selects original source geometries for MHH, Podbi,
central Hannover, Lehrte and study-boundary views at four sizes each. Returned
IDs agree with those spatial selections. The overview's total assignment equals
the drawable count; independent category counts retain overlaps. The source
R-tree is confirmed by SQLite query-plan evidence. Original OSM SHA-256 remains
`6678ed0b55cb58dbfc23b570dda5474d42da78f984563cae910cde673e65e8a6`.

Windows process counters after preparation: peak working set 132,775,936 bytes,
current working set 131,301,376 bytes, private usage 462,495,744 bytes. Peak working
set over the complete validation process: 153,370,624 bytes. These are whole-process
counters including imported geospatial libraries, not isolated cache allocations.
Some other verification work ran on the same host; this is reproducible acceptance
evidence, not an isolated performance benchmark or browser-memory measurement.

API timing uses an in-process ASGI TestClient including response serialization.
It excludes real TCP, browser parsing and rendering. The proposed warm API p95
target of two seconds passes for these viewports; browser interaction and route
overhead targets belong to later map integration acceptance.

## Validation

- Full local backend: **299 passed / one existing Windows permission skip**,
  95.57 s. Twenty-five new cases cover independent intersections, cross-boundary
  lines/polygons, multipart/point geometry, category membership, bounds, resource
  ceilings, cache reuse/restart/corruption, partial preparation/locks, rule/source
  changes including restored timestamps, empty data, API guards and CLI reuse.
- Targeted final API/display checks: 33 passed / one existing skip.
- Ruff lint and format checks pass for backend and the reproduction script.
- Frontend lint/TypeScript/production build pass; 14 mocked browser tests and
  14 real-stack smoke tests pass using installed Chrome. The default Playwright
  bundled Chromium is absent locally; using the configured Chrome channel avoids
  installing or changing browser dependencies. Smoke runners exit cleanly.
- Real sources and private profiles remain intact. Tests use their own data and
  services; no user-owned running service is stopped or restarted.

## Remaining scope

Part 1 provides data access, not the completed colored regional map. Part 2 adds
shared cost styles and on-demand classification details; Part 3 connects viewport
requests, category/cost controls and separate map-layer lifecycles. The existing
regional OSM switch still uses the legacy path and receives the explicit large-
response guard until that integration. Invalid/unsupported geometries remain
diagnosed rather than repaired into display or planner geometry.

Part 4 still needs browser resource/interaction sequences, OSM-on route comparison
and complete iteration delivery gates. Full multizoom tiles, WebGL, new source
acquisition, planner/permission changes and study expansion remain outside this
Part. See [operation and API guide](../../experiments/iteration-012/README.md) and
[the iteration plan](../../plan/iteration-012.md).
