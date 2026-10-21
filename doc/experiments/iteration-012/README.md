# Iteration 012 Part 1 - Bounded regional OSM data access

This guide describes the implemented Part 1 interfaces. Regional category/cost
controls, individual-object classification details and viewport loading in the
browser are delivered in later Parts. The current regional browser must not use
the old unbounded OSM switch to obtain the full Hannover collection.

## Prepare the retained source explicitly

From the repository root:

```powershell
uv run --project backend --locked uas-planner study-osm-prepare data/hannover-part1-v4
```

The command verifies original OSM bytes against their manifest, validates source
identity/count/CRS and study coverage, streams objects into a spatial display
database and publishes its manifest last. It writes only derived cache files at
`data/.osm-display/{identity-hash}/`, with progress on stderr and a JSON result on
stdout. Original OSM, study, terrain and private-profile files are preserved.

Repeat the same command to verify/reuse an existing complete cache. Explicitly
rebuild after cache corruption, or for a new display implementation, with:

```powershell
uv run --project backend --locked uas-planner study-osm-prepare data/hannover-part1-v4 --refresh
```

`--cache-root` can override the parent cache directory. To serve the cache through
the API, it must match the selected API data root's `.osm-display` directory.
No HTTP request starts preparation. A per-snapshot exclusive lock prevents
simultaneous builds across processes; incomplete generations have no usable
manifest. Failed/older generations remain available for diagnosis and are not
automatically deleted. If a process was forcibly terminated, verify that no
preparation is still running before removing its stale `prepare.lock` and retrying.

The source SHA-256, metadata/study hashes, cost-rule hash/version, display schema,
grid definition and simplification policy identify the cache. Each new API process
verifies the source and derived database before trusting an existing snapshot.
Warm reads check file identity, size and modification/change times plus parsed
metadata/study identity; they do not reread/hash the entire source. Windows uses
native file ChangeTime, since creation time cannot detect restored-mtime edits.
Change tokens invalidate trust; complete checksums establish integrity. Changes
during a query reject the result. Explicit preparation/refresh is the recovery
path for changed manifests or corrupt source/cache data.

## Read-only API

The backend's existing data-root selection applies. Example dataset:
`hannover-part1-v4`.

| Request | Behavior |
|---|---|
| `GET /api/datasets/{id}/study/osm/summary` | Readiness, source/rule identity, complete source/category counts, geometry diagnostics and limits |
| `GET /api/datasets/{id}/study/osm/features?bbox=9.800,52.381,9.808,52.386&zoom=16` | Compact original-geometry objects intersecting the effective viewport |
| `GET /api/datasets/{id}/study/osm/overview?bbox=9.650495867959657,52.32042221571155,10.068841103123809,52.45032927853548` | Bounded labelled aggregate cells for the complete study |

Both collection endpoints accept `categories`, a comma-separated selection of
`building,highway,landuse,natural`. Membership means a non-null saved category
tag, matching the demo's layer membership. An object with multiple categories
appears once in a detail response. Category counts may overlap.

Part 1 supports `style=category` only. Cost coloring and object-detail endpoints
are Part 2; unsupported styles return 422 rather than inventing classifications.

`bbox` is west,south,east,north in WGS84; finite ordered bounds are required.
`zoom` is an integer 0-22. Requests are intersected with the saved study boundary.
An outside-coverage response is explicitly labelled and empty; a verified empty
viewport inside coverage is distinguishable from it.

Detail responses are GeoJSON with a `display` member containing identity,
requested/effective/coverage bounds, category selection, representation,
returned count, completeness, limits and any limit reason. Properties contain
only `element_type`, `osm_id` and category membership. There are no null-filled
tag columns or per-tag explanation copies. Feature IDs retain `node/ID`, `way/ID`
or `relation/ID`. Geometry is complete original geometry, selected by exact
intersection after an R-tree candidate query; no source clipping/repair or
simplification is applied in this Part. Complete objects can extend beyond the
viewport/study. Rendering clips at the map viewport in the future integration.

Adopted detail ceilings:

- 5,000 returned objects, 5 MiB uncompressed response and 100,000 coordinates.
- At most 10,000 examined candidates; a two-second cooperative query budget.
- At most two active display queries per API process; eight source-verification
  memo entries. Connections close after each query.

Geometry size/count is checked before loading/mapping the object, and encoded
feature bytes are counted incrementally with reserved metadata space. A capped
response has `complete: false`, `limit_reason` and `overview_recommended: true`.
The returned count is not an invented total viewport count. A SQLite deadline
interrupt can instead produce a 503 retry response. Cooperative time limits do
not preempt a geometry operation already in progress.

Overview uses a fixed 40-by-40 grid in saved study coordinates, up to 1,600 cells.
Each valid supported source object is assigned exactly once using a representative
point of its intersection with study coverage. Cell properties include total
assigned objects and independent category counts. These are whole-cell counts,
including when only part of a cell intersects the requested viewport; they are
not footprint-intersection totals, exact viewport totals or a fused risk score.
Invalid or unsupported objects are excluded from drawing, counted by reason and
retained with identity/diagnostic in the cache. Summary samples are bounded and
explicitly indicate whether the sample is complete.

## Errors and legacy compatibility

- Before preparation, summary returns `not_prepared` and `verified: false`.
  A locked initial build reports `preparing`. Metadata-only regional catalog
  entries also retain `verified: false`; the explorer badge respects that flag.
- Detail/overview reads without a completed snapshot return 409; transient busy
  or verification states return 503 with `Retry-After`. Invalid query parameters
  and failed source/cache verification return 422. Errors do not expose local paths.
- Oversized regional `/features` requests return 413 before the full loader runs.
  The legacy regional endpoint also guards source bytes and rejects the detailed
  analysis response. Small regional raw responses omit absent tags and have a
  final byte limit. Regular small-area/demo source and analysis APIs remain.
- Regional catalog/detail requests use metadata and the prepared summary instead
  of repeatedly loading a full GeoDataFrame. Without a prepared cache, geometry
  and layer summaries are unavailable, rather than reported as verified counts.
- Existing original-source download and route/constraint APIs keep their contracts.
  A bounded display response must not be substituted for a full source export.

## Reproduce real Part 1 acceptance

With a prepared cache, use a new evidence directory:

```powershell
backend/.venv/Scripts/python.exe doc/experiments/iteration-012/verify-part1.py --output .cache/iteration012-part1-new
```

Add `--prepare` to explicitly rebuild and measure preparation before the query
run. The script tests 20 viewports across MHH, Podbi, central Hannover, Lehrte and
the study boundary, checks returned identities independently through GDAL/Pyogrio
source spatial reads, verifies complete overview totals, exercises the legacy
guard and confirms unchanged source bytes. It records cold verification separately
from warm API timings, response sizes, source-index query plan and Windows process
memory counters. It uses an in-process ASGI TestClient; local event-loop sockets
are required, but no HTTP server, external network or browser is started. API
latencies include serialization and exclude TCP/browser rendering.

See [Part 1 outcome](../../iteration/iteration-012/part1.md) for actual results and
[the plan](../../plan/iteration-012.md) for the remaining integration acceptance.
