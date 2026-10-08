# Hannover regional source workflow — Iteration 008 Part 1

Part 5 now provides offline multi-pair experiments. Run
`backend/.venv/Scripts/python.exe doc/experiments/iteration-008/run-part5.py --output .cache/part5-new`
then
`backend/.venv/Scripts/python.exe doc/experiments/iteration-008/report-part5.py --input .cache/part5-new --output .cache/part5-new-evidence.json`.
Use new outputs; add `--synthetic-only` to the first command when real snapshots
are unavailable. See [Part 5 results](../../iteration/iteration-008/part5.md) for
the matrix, metadata, cache interpretation and unresolved real/expanded inputs.

This delivery prepares OSM, DIPUL and GHSL sources. Constraint interpretation,
planner preparation and the endpoint-selection UI belong to later parts of
[the plan](../../plan/iteration-008.md). A complete source snapshot is not a
validated route or flight authorization.

## Sites and region

[locations.json](locations.json) records all eight supplied sites, the attachment
checksum, operator address references, OSM coordinate identities and verification
status. [location-evidence/](location-evidence/) retains the original one-time
address lookup responses. Coordinates are representative facility/address points,
not surveyed launch or landing positions. Rheumatology practices retain their
actual type even though the attachment groups them with laboratories.

Addresses were cross-checked against operator contact pages on 2026-10-05:
[MHH](https://www.mhh.de/die-mhh/anfahrt-lageplan),
[DIAKOVERE](https://www.diakovere.de/gesund-werden/fuer-patienten/kontakt-und-anfahrt/),
[Rheumapraxis](https://www.rheumapraxis-hannover.de/kontakt),
[Limbach](https://www.labor-limbach-lehrte.de/datenschutz/), and
[amedes](https://www.amedes-genetics.de/ueber-uns/standorte-labor.html).

The cached, one-time OSM Nominatim lookup used one machine and sequential requests
spaced by more than one second, with an identifying User-Agent. It is not an
application geocoding service. Any future lookup must follow the
[Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/):
at most one request per second, identifying client headers, attribution and
cached results; no autocomplete or systematic scraping.

[hannover-study.json](hannover-study.json) contains the authoritative bounds and
all locations. Bounds envelope the EPSG:25832 site extent plus a 5,000 m allowance,
then transform that envelope to a geographic rectangle. The resulting area is
approximately 411.74 km², including Hannover and Lehrte. This allowance does not
guarantee a feasible detour. The optional Overpass workflow partitions the
rectangle into 32 requests, each under the existing 25 km² small-query limit.

Transiently failing OSM chunks can subdivide into four children, to a maximum of
two subdivision levels. Decisions are preserved in progress and final manifests.
The resulting leaf requests still partition the entire original region without
gaps; no failed chunk is silently omitted. The final count can exceed 32.

Parameters are 100 m AGL and 30 m/s by default, with accepted ranges of 100–120 m
and 25–35 m/s. The configuration retains the building-risk objective and 0.9/0.1
risk/distance weights. These parameters are recorded here; Part 1 does not execute
route optimization, altitude restrictions or flight-time estimation.

## Acquire and inspect

Run from the repository root with the locked backend environment installed:

```powershell
uv run --project backend --locked uas-planner study-fetch --config doc/experiments/iteration-008/hannover-study.json --output data/hannover-part1-new --cache .cache/source-downloads
uv run --project backend --locked uas-planner study-inspect data/hannover-part1-new
```

Use a new output name. Downloads are explicit; inspection is offline. A cache hit
retains the original retrieval timestamp and records its reuse timestamp. Cache
reuse is not a fresh source check. For a fresh acquisition, use a new cache
directory as well as a new snapshot directory.

The study adapter supports the configured Hannover/Lehrte/Braunschweig geographic
envelope, up to 2,000 km². This limit is separate from the 25 km² legacy small-area
workflow, which remains unchanged. It is not a planner resource-limit increase.

The default OSM configuration downloads a dated
[Geofabrik Niedersachsen extract](https://download.geofabrik.de/europe/germany/niedersachsen.html)
(`niedersachsen-261003.osm.pbf`) and its publisher checksum, then selects complete
intersecting building/highway/landuse/natural features locally using the existing
GDAL OSM driver. Original IDs and common columns plus `other_tags` are retained;
computed fields such as `z_order` are not introduced as source tags. Polygon
representations take precedence when GDAL represents a closed way in two layers.
The publisher extract polygon is preserved and must cover the whole study region.
This boundary file has its own retrieval date; it is not presented as a historical
boundary extracted from the dated PBF. No new runtime dependency is required.

The original PBF is about 483 MiB and contains a broader area than the study.
This is deliberate: one stable source artifact enables offline regional extraction
and later margin changes. It is not a manually selected small map download. Its
explicit dated URL, response headers, publisher MD5 and snapshot SHA-256 are retained.
PBF transfers have a 650 MiB size cap and checked 900 s transfer budget. Future
larger publisher artifacts require an explicit adapter-limit adjustment.

[hannover-overpass.json](hannover-overpass.json) retains the alternative bounded
query configuration. It uses sequential Overpass requests for building/highway/landuse/natural
tags, preserving full source geometry and dependencies. Original JSON is stored
per request. Duplicate identities are merged deterministically; tagged objects
take precedence over skeleton dependencies. Conflicting tagged versions retain
the first and are counted, with both original observations preserved. Source base
timestamps can differ across chunks; this is not a transactional global snapshot.

DIPUL acquires all currently advertised layers, or an explicit configured layer
list. Capabilities and per-layer schemas are preserved. WFS pages use CRS84 bounds,
explicit start indices and a 2,000-feature page size. Matched/returned counts,
geometry and identities are checked. Unknown totals, duplicate IDs, changing
totals and incomplete pages prevent completion. Current acquisition includes
temporary restrictions but does not establish date/height/legal applicability or
NOTAM completeness. An unavailable inactive/future layer is not assumed covered.
Original DIPUL bytes remain local; derived restriction exports are not introduced.

GHSL uses [GHS-POP R2023A](https://human-settlement.emergency.copernicus.eu/ghs_pop2023.php),
2020 population estimates, native 100 m Mollweide cells and the explicitly selected
R3_C19 publisher tile. The adapter checks that this tile covers the full region;
it rejects incomplete coverage rather than silently clipping. Multi-tile GHSL
mosaicking is not implemented. Original ZIP, native aligned crop, product identity,
units and NoData metadata are retained. No population resampling occurs and NoData
is not zero. GHSL built-up products are not bundled into this population product.

The regional source-study manifest is `study.json`, separate from the existing
small-area `experiment.json`. This separation prevents source acquisition from
claiming flight-model readiness. Full-region native DGM1 terrain acquisition is
not performed here; Part 2 must determine bounded terrain support for existing
vertical-reference diagnostics before integrating these sources into planning.

## Resume and rebuild

```powershell
uv run --project backend --locked uas-planner study-fetch --config doc/experiments/iteration-008/hannover-study.json --output data/hannover-part1-new --cache .cache/source-downloads --resume
uv run --project backend --locked uas-planner study-rebuild data/hannover-part1-new --output data/hannover-part1-rebuilt
```

Resume requires exactly matching configuration and verified original receipts.
Completed snapshots cannot be resumed or overwritten. Receipted files are reused;
only missing requests are downloaded. HTTP requests have 15 s connection/60 s read
timeouts, a checked 240 s transfer budget and a 150 MiB cap. There are at most three
attempts for transient network errors and HTTP 429/502/503/504. A blocking read may
extend the checked budget by its timeout. Transfers use named `.part` files, and
the final study completion marker is written only after validation.

For the default primary Overpass endpoint, transient failure retries may use the
server-specific Lambert endpoint announced by the primary service's status API.
The primary service is listed in the
[OSM public-instance documentation](https://wiki.openstreetmap.org/wiki/Overpass_API).
Receipts preserve the configured request, actual response URL and transfer endpoint.
Custom configured services are not redirected. A mirror does not guarantee the
same replication timestamp; original source timestamps remain visible.

Rebuild reads originals only and writes a new directory. It works if derivatives
have been lost, and also if all original requests completed but derivation failed
before `study.json` was written. It never downloads missing originals; resume the
acquisition first if the original set is incomplete. Keep `study-progress.json`
for interrupted-acquisition recovery. Corrupted originals are rejected.

```text
study.json                     completed study manifest and provenance
study-progress.json            acquisition configuration and original receipts
raw/ghsl.zip                   original publisher archive
raw/dipul-capabilities.xml     advertised WFS layers
raw/dipul-*-schema.xml          original per-layer schemas
raw/dipul-*-NNN.geojson         original WFS pages
raw/osm-NNN.json               original bounded Overpass responses
raw/osm-source.osm.pbf         original dated PBF (PBF mode)
raw/osm-source.md5             publisher checksum (PBF mode)
raw/osm-source.poly            publisher extract coverage (PBF mode)
population.tif                 aligned native population crop
osm/features.gpkg              deduplicated OSM features
osm/metadata.json              OSM integrity and region metadata
```

## Change the detour margin

```powershell
uv run --project backend --locked uas-planner study-configure --config doc/experiments/iteration-008/hannover-study.json --margin-m 10000 --output .cache/hannover-expanded.json
uv run --project backend --locked uas-planner study-fetch --config .cache/hannover-expanded.json --output data/hannover-expanded --cache .cache/source-downloads
```

The configuration command is offline and refuses to overwrite existing output.
Every location must remain strictly inside the region. A new region needs its own
snapshot; matching immutable source requests may reuse the download cache.

See [Part 1 delivery evidence](../../iteration/iteration-008/part1.md) for the real
snapshot counts and validation results.

## Part 2: regional constraints and native population inspection

Part 2 adds offline source-to-constraint preparation, separate native terrain
snapshots and population queries. It does not produce routes or replace the
Braunschweig `experiment.json` workflow. Rules and uncertainty policies are in
[regional constraints](../../rules/regional-constraints.md).

`hannover-scenario.json` is an explicit engineering inspection interval on
2026-10-07, not a flight authorization or user flight schedule. Select your actual
interval before interpreting applicability. The example retains 100 m AGL,
30 m/s, zero additional clearance and unresolved missing building heights.

```powershell
uv run --project backend --locked uas-planner study-prepare data/hannover-part1-v4 --scenario doc/experiments/iteration-008/hannover-scenario.json --terrain data/hannover-part2-terrain-v1 --output .cache/hannover-prepared.json
uv run --project backend --locked uas-planner study-population data/hannover-part1-v4 --svg .cache/hannover-population.svg --output .cache/hannover-population.json
```

Output paths must be new. `study-prepare` verifies the original study and terrain
payloads, records model/rule/source identity, building/zone state counts, source
geometry diagnostics, exact address conflicts and native population statistics.
Omit `--terrain` to inspect explicit unknown terrain support; this does not create
observed elevation or permission. Read the `blocked`, `unresolved`, `assumptions`
and `terrain` fields, not just the summary state.

For a WGS84 GeoJSON Point or LineString **geometry** file:

```powershell
uv run --project backend --locked uas-planner study-check data/hannover-part1-v4 --scenario doc/experiments/iteration-008/hannover-scenario.json --terrain data/hannover-part2-terrain-v1 --query .cache/motion.json --mode strict --output .cache/motion-check.json
uv run --project backend --locked uas-planner study-population data/hannover-part1-v4 --query .cache/motion.json --corridor-m 100 --cells --output .cache/corridor-population.json
```

`--corridor-m` is total corridor width; half is buffered on each side in metric
coordinates. `--cells` includes native-cell GeoJSON, not a resampled grid. The SVG
shows the complete aligned population crop including its edge margin; it does not
show statutory constraints or flight risk. Missing support makes complete totals
null and retains observed partial totals.

Read-only API:

- `/api/datasets/{id}/study`: verified regional manifest.
- `/api/datasets/{id}/study/population`: full-region native population statistics.
- Optional `geometry_json` is a URL-encoded WGS84 GeoJSON geometry; `corridor_m`
  and `cells=true` request a corridor and native display layer respectively.

The population API and CLI share `PopulationInspector`. Endpoint selectors,
regional layer switches and route display remain Part 4.

### Separate bounded native terrain acquisition

Use the exact study bounds, in west/south/east/north order, to reproduce the
full-region terrain snapshot. `terrain-fetch` permits at most 144 native 2 km
requests, with up to three workers. Hannover's region requires 120 tiles. This
is a large separate download; existing original study files remain untouched.

```powershell
$studyConfig = Get-Content doc/experiments/iteration-008/hannover-study.json -Raw | ConvertFrom-Json
uv run --project backend --locked uas-planner terrain-fetch --bounds $studyConfig.bounds.west $studyConfig.bounds.south $studyConfig.bounds.east $studyConfig.bounds.north --output data/hannover-part2-terrain-v1 --workers 3
```

On interruption, use the identical command with `--resume`. Receipted payloads
are verified and reused; unreceipted files are preserved under archive names before
fresh acquisition. Completion requires every planned tile and valid native grids.
Changing bounds requires a new output directory. DGM1 retains its native 1 m
grid and NHN reference. Incomplete support, NoData and a conservative query budget
remain explicit; no center sample stands in for full-motion terrain coverage.

`data/hannover-part2-terrain-mhh` is the earlier one-kilometre native acquisition
probe around MHH. Its coverage is only local; it is not the full-region snapshot.

### Reproduce offline Part 2 evidence

With retained study and completed full-region terrain snapshots:

```powershell
uv run --project backend --locked python doc/experiments/iteration-008/verify-part2.py --output .cache/hannover-part2-evidence.json
```

The script explicitly forbids HTTP requests, verifies both snapshots and records
100/120 m scenarios, all eight address diagnostics and three representative complete
motions with independent 100 m-wide population corridors. Its motion checks are
inspection evidence, not searched routes or Part 5 flight experiments. Pixel-budget
failures, unknown applicability and address conflicts are retained in the output.
# Part 3 regional routing

From the repository root, using the existing backend environment:

```powershell
backend/.venv/Scripts/python.exe -m uas_planner.cli study-route data/hannover-part1-v4 --scenario doc/experiments/iteration-008/hannover-scenario.json --terrain data/hannover-part2-terrain-v1 --start-id rheuma-podbi --end-id mhh --algorithm astar --objective risk --cell-m 250 --output .cache/hannover-route.geojson
backend/.venv/Scripts/python.exe doc/experiments/iteration-008/verify-part3.py --output .cache/hannover-part3-new-evidence.json
```

Use `--algorithm dijkstra` or `abitstar`, `--objective distance`, and explicit
`--planning-mode research` to compare contracts. Background remains unassessed
unless `--background-cost` is explicitly supplied. The example scenario is dated
engineering evidence, not a flight schedule. Real retained inputs remain unresolved.

API: POST `/api/datasets/hannover-part1-v4/study/route`, JSON:

```json
{
  "start_id": "rheuma-podbi",
  "end_id": "mhh",
  "terrain_id": "hannover-part2-terrain-v1",
  "algorithm": "astar",
  "objective": "risk",
  "cell_m": 250,
  "scenario": {
    "agl_m": 100,
    "speed_m_s": 30,
    "scenario": "civil",
    "mission_start": "2026-10-07T10:00:00+02:00",
    "mission_end": "2026-10-07T10:15:00+02:00",
    "clearance_m": 0,
    "vertical_clearance_m": 0,
    "building_unknown_height": "unresolved"
  }
}
```

Other shared controls: `planning_mode`, `background_cost`, `risk_weight`,
`distance_weight`, `time_budget_s` (0–60). `export: true` returns GeoJSON.
Refresh/restart the explorer and select the regional dataset to see the basic
regional controls. Enter explicit offset-aware scenario times. Changing a control
clears old results; export saves the displayed result including failure diagnostics.
Named selectors and map layers are Part 4. See the Part 3 delivery for limits.
