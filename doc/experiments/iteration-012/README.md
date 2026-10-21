# Iteration 012 Parts 1-2 - Bounded regional OSM data and classification

This guide describes bounded category/cost interfaces and on-demand original-object
classification details. Regional controls and viewport loading in the browser
remain Part 3. The current regional browser must not use
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
Part 2 uses display schema **2**, adding precomputed independent primary-category
scores. A schema-1 cache is not reused as a verified schema-2 snapshot; the ordinary
prepare command builds the new identity in a separate directory. Retained old
generations are preserved. Restart a backend running older code after updating;
preparation alone does not change that running process's implementation.

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
| `GET /api/datasets/{id}/study/osm/features?bbox=9.800,52.381,9.808,52.386&zoom=16&style=cost&cost_category=building` | The selected category's compact independent cost/flags |
| `GET /api/datasets/{id}/study/osm/features/{element_type}/{osm_id}` | Original sparse tags/geometry, complete per-category explanations and geometry diagnostics |
| `GET /api/datasets/{id}/study/osm/overview?bbox=9.650495867959657,52.32042221571155,10.068841103123809,52.45032927853548` | Bounded labelled aggregate cells for the complete study |

Both collection endpoints accept `categories`, a comma-separated selection of
`building,highway,landuse,natural`. Membership means a non-null saved category
tag, matching the demo's layer membership. An object with multiple categories
appears once in a detail response. Category counts may overlap.

`style=category` is the default. `style=cost` requires `cost_category` to be one
of the selected `categories`; supplying it for category style is invalid (422).
Cost mode includes an object only when the existing demo's `analyze_feature`
returns an analysis for the selected category. Absent/null/empty/`no` values do
not become confirmed scores. Present but excluded values such as `highway=corridor`
retain a gray, nonnumeric result. Category membership remains a non-null saved
tag, independently of whether that value can be scored.

An object appears once. In category view the first enabled membership wins in
demo order: **building, highway, landuse, natural**. Hiding buildings on a shared
building/landuse object exposes its landuse color. In cost view only the selected
category supplies the score and historical paper obstruction flag; other tag
costs/flags are not fused. Counts overlap and must not be added as unique totals.
Shared frontend helpers in `osmStyles.ts` preserve the demo palette, gray/dashed
unknown/default/unscored appearance and qualified dark obstruction outline.

`bbox` is west,south,east,north in WGS84; finite ordered bounds are required.
`zoom` is an integer 0-22. Requests are intersected with the saved study boundary.
An outside-coverage response is explicitly labelled and empty; a verified empty
viewport inside coverage is distinguishable from it.

Detail responses are GeoJSON with a `display` member containing identity,
requested/effective/coverage bounds, category selection, representation,
returned count, completeness, limits and any limit reason. Properties contain
only `element_type`, `osm_id` and category membership. Cost style adds a foreign
feature member `cost_analysis` with only `cost`, `status`, `has_default` and
`obstruction`. The collection's `display.cost_category` and `display.identity`
provide category/rule/source identity. There are no null-filled tag columns or
per-tag explanation copies. Feature IDs retain `node/ID`, `way/ID`
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

### On-demand object detail

Use a returned feature's string ID (or a summary diagnostic ID) to request its
details. IDs must use `node`, `way` or `relation` and a canonical nonnegative
signed-64-bit integer without leading zeros. Invalid IDs fail before snapshot
verification; a valid absent ID returns 404.

The GeoJSON Feature includes original sparse `properties`, original geometry
and `layer_analyses` for all four categories using the same existing demo
classification engine. Each non-null analysis includes rule version, numeric
cost/label/status/default/flag and full per-tag matches, reasons and sources.
Absent categories are null; absent source tags are not synthesized. Source/rule
checksums are in `display.identity`. Detail reads first resolve the indexed cache
identity, then read the original GeoPackage **by fid primary key**. Warm clicks
do not load a complete GeoDataFrame or rehash the full source.

`display` identifies `object_detail`, membership, coverage, original geometry
type/coordinate count, `diagnostic` and whether it is drawable. Invalid original
geometry and unsupported GeometryCollections remain available for inspection;
they are not repaired or added to viewport drawing. Original geometry can extend
outside coverage. Costs always use original tags, including when geometry is
omitted from a bounded response.

Details share the 5 MiB response, 100,000-coordinate and two-second cooperative
budgets. Geometry reads are capped at 16 MiB source bytes, and encoded geometry
has a half-response budget. Oversized, missing or nonfinite geometry is returned
as null with an explicit `geometry_omitted` reason and `geometry_complete: false`;
tags/analyses remain inspectable where their own budget permits. Full explanations
allow at most 512 original tag keys and 4,096 value tokens (including semicolon/list
values), with a 1 MiB source-tag limit. Expansion/response overflow returns 413
with a source-export instruction rather than a partial explanation labelled full.
`tags_complete` and `classification_complete` are true on successful responses.

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

## Reproduce real Part 2 acceptance

After preparing schema 2, use a new output directory:

```powershell
backend/.venv/Scripts/python.exe doc/experiments/iteration-012/verify-part2.py --output .cache/iteration012-part2-new
```

The script checks 20 independent original-source spatial selections, 80 selected-
category cost responses, sampled original-object tags/geometry/explanations and
all bounded summary diagnostic samples. It compares costs with the existing demo
classifier and records timings, bytes/coordinates, source-primary-key query-plan
evidence, process memory and unchanged original SHA-256. It uses ASGI TestClient
and requires local event-loop sockets. It measures neither browser rendering nor
OSM-on route overhead; those remain later integration acceptance. See
[Part 2 outcome](../../iteration/iteration-012/part2.md).
