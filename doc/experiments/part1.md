# Part 1: reproduce and inspect external source layers

Scope and mission: [approved plan](../plan/iteration-005.md) and
[machine-readable configuration](braunschweig-part1.json). The area is
9.230371747 km², not the earlier tiny demonstration. No grid or route search is
implemented. OSM costs, population observations, source zones and terrain remain
independent.

## Acquire a new snapshot

Install the locked backend/frontend dependencies as described in the README.
From the repository root, choose new output names:

```powershell
uv run --project backend --locked uas-planner experiment-fetch --config doc/experiments/braunschweig-part1.json --output data/braunschweig-experiment
uv run --project backend --locked uas-planner fetch --west 10.5 --south 52.25 --east 10.545 --north 52.277 --output data/braunschweig-experiment/osm --cache .cache/osmnx
uv run --project backend --locked uas-planner experiment-inspect data/braunschweig-experiment
uv run --project backend --locked uas-planner experiment-inspect data/braunschweig-experiment --longitude 10.505 --latitude 52.254
```

Alternatively, attach an already saved OSM dataset with exactly matching bounds:

```powershell
uv run --project backend --locked uas-planner experiment-add-osm data/braunschweig-experiment --dataset data/my-matching-osm
```

Attachment copies and verifies the original OSM files into a new `osm/` folder;
it does not alter the source dataset. Reattaching or overwriting completed output
is refused. External collection and OSM acquisition are separate, explicit steps.
Until both are present, the explorer reports the dataset as needing attention.

Acquisition is limited to the configured area (maximum 25 km²) and this adapter's
validated Braunschweig region. GHSL is distributed as an indivisible archive:
retain the 41 MB native tile ZIP, but derive only an aligned native-pixel window
for inspection. No population resampling occurs. Source geometries intersecting
the area are retained whole and can extend beyond the query rectangle.

External requests have 15 s connect/45 s read timeouts, a 150 MiB response cap,
and a checked 180 s transfer budget (a blocking read can extend that budget by
its timeout). No automatic retry loop is used. An incomplete acquisition is kept
for diagnosis. To explicitly continue it, use the same command with `--resume`;
saved response checksums and request URLs must match. Completed snapshots cannot
be resumed, and a partial response without a completed receipt is not overwritten.
Choose a new output directory if such a response exists. This does not resume
any earlier canceled OSM acquisition.

## Offline reload and UI

Keep the complete experiment folder:

```text
experiment.json              source/configuration/integrity manifest
acquisition-progress.json    receipts for explicit interrupted-acquisition recovery
population.tif              native GHSL window, without resampling
raw/ghsl.zip                 exact publisher archive
raw/terrain.tif              exact bounded DGM1 WCS response
raw/*-capabilities.xml       source capabilities
raw/*-schema.xml             selected DIPUL schemas
raw/dgm-description.xml      original terrain coverage description
raw/*.geojson                exact bounded DIPUL responses
osm/features.gpkg           independently verified OSM snapshot
osm/metadata.json           OSM metadata and checksum
```

`experiment-inspect` uses only local files and checks every recorded payload's
SHA-256, raster metadata/coverage and vector identity/geometry/completeness.
Changing mission assumptions requires a new experiment. Copying the whole folder
preserves its inspection results; reacquiring later can legitimately change OSM,
DIPUL or terrain source versions. Checksums establish snapshot integrity, not
independent proof of geographic accuracy.

Start the normal API and frontend, select the experiment, and disable Basemap
for offline use. GHSL and DIPUL checkboxes operate independently of the four OSM
layers and cost modes. Click a native population cell/zone for source values,
or any location inside the boundary for ground elevation and aircraft altitude.
**Inspect start/end** provides reproducible reference locations. Source details
show identity, epoch, attribution, license, unknown status and metadata exceptions.
The ordinary download buttons continue to export OSM only; external originals
remain local, including DIPUL material under CC BY-ND 4.0.

Population colors use display bins only; the underlying floating-point count is
unchanged. Zero is known zero, while NoData is null/unknown. A count of 20 in a
100 m equal-area cell corresponds to 2,000 people/km²; clipping a displayed cell
or using a finer future planning grid must not duplicate or redistribute that
count without an explicit model. Footprint overlap alone is not an area-weighted
population total for the experiment.

## Real payload validation, 2026-09-29

Local completed snapshot: `data/braunschweig-part1-v2`. The first failed terrain
validation remains separately under `data/braunschweig-part1`; original
`braunschweig-demo` and `offline-sample` were not modified.

| Source | Observed payload |
| --- | --- |
| OSM | 31,496 objects; same geographic query bounds |
| GHSL | GHS_POP_E2020_GLOBE_R2023A_54009_100_V1_0_R3_C19; Float64, ESRI:54009, 100 m, NoData -200 |
| Population display | 961 native cells intersect the query; 11 true zeros, no NoData cells; range 0–194.769439697 people/cell |
| Terrain | LGLN ni_dgm1; EPSG:25832; Float32; 3,135 × 3,068 native 1 m cells; observed range 66.521–87.198 m |
| DIPUL | WFS 2.0.0 GeoJSON; 2 control-zone features, 1 railway feature; 0 federal-road and 0 nature-reserve features |

The 37 × 28 population window includes a margin around the transformed geographic
rectangle; only intersecting cell footprints are rendered. CRS transformations
always use longitude/easting as x, never the WFS EPSG axis order implicitly.
DIPUL requests explicitly use CRS84 bbox order and validate returned coordinates.
Feature IDs and all properties are preserved, including MSL/feet fields in the
control zones. Native WFS IDs are scoped to this snapshot; stable IDs across
future publications are not assumed.

| Point (longitude, latitude) | Terrain m NHN | AGL m | Aircraft m NHN | People/native cell |
| --- | ---: | ---: | ---: | ---: |
| Start (10.505, 52.254) | 74.744003296 | 60 | 134.744003296 | 30.697637558 |
| End (10.54, 52.273) | 74.338996887 | 60 | 134.338996887 | 106.301925659 |

Heights use the containing terrain cell, without interpolation. The arithmetic
was checked at both endpoints; population values were independently read back
from the retained publisher ZIP and match the saved window exactly. Height display
is `aircraft = terrain + AGL`, consistently in metres NHN/DHHN2016 (EPSG:7837).
The numeric precision above identifies the stored float, not survey accuracy.
No conversion between this datum and a DIPUL MSL reference is asserted.

### Terrain metadata contradictions and resolution

The current WCS `DescribeCoverage` returns `W.m-2.Sr-1` as the band unit and no
nil values; the actual TIFF also omits its NoData tag. Both original responses
are saved. The [official LGLN product notice](https://www.lgln.niedersachsen.de/download/207140/Kundeninformation_1_2024.pdf)
identifies the DGM as a 1 m terrain raster, ETRS89/UTM32, DHHN2016 normal height,
with NoData -9999. This adapter uses that documented product contract and records
the override separately (`effective_nodata`), leaving response bytes untouched.
The inspected crop contains plausible positive terrain values and no -9999 values;
synthetic tests verify -9999 remains unknown despite the missing TIFF tag. No
radiance conversion or replacement of missing values with zero is performed.
The survey epoch is unknown, not inferred from download time. This resolution is
adequate for source inspection; terrain accuracy and datum compatibility require
further assessment before altitude-dependent constraint interpretation.

### DIPUL coverage and semantics

The selected static layers are deliberately partial. Empty responses are valid
only when their declared match counts are zero; they do not imply all-source
coverage or permission to fly. Temporarily restricted areas were not queried.
Validity periods were not supplied in these static feature properties; response
timestamps are retrieval evidence only. All applicability remains unresolved.
Source polygons are retained without adding buffers. Whether any particular
source geometry includes its complete regulatory buffer remains unverified;
Part 2 must resolve this per category before geometric constraint interpretation.
WMS is not used as geometry. See the [DIPUL assessment](../data-sources/04-dipul.md).

The terrain source is bare-earth DGM, not a surface/building model. Neither the
height display nor the zone overlay establishes clearance, a validated route or
operational legal applicability. Those interpretations remain outside Part 1.
