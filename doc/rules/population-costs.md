# Population classes on a 250 m grid

Implemented in Iteration 014 Part 1: aggregation, classification, inspection API
and colored Hannover map cells. Route weighting is deferred to Part 2.
Rule version: `ramke-population-250m-v1`.

## Source and interpretation

Carsten Ramke (2020), *Development of advanced informed planning techniques for
BVLOS UAS operations*, printed pp. 38-39 (PDF pp. 50-51), describes population
normalization by the maximum, five equal-width classes with costs 0-4, and weighted
fusion with OSM. Figure 3-9's example intervals differ from exact fifths of [0,1].
The exact fifths, 250 m lattice and complete-study reference below are project
policies, not claims of exact reproduction of that experiment.

Use retained GHS-POP R2023A counts on their native 100 m ESRI:54009 cells.
The configured 2020 estimate or 2025 projection epoch is retained in provenance.
Values are estimated residential people per cell, not exact people present,
accident probabilities or exposed-person counts. Class 4 is a soft research
preference category, not an obstacle or flight prohibition. Class 0 can contain
people; NoData is separate from all numeric classes.

## Fixed lattice and count transfer

Build the complete saved study boundary in EPSG:25832. Snap its minimum x/y down
to multiples of 250 m to define a stable lattice origin. Clip the 250 m square
cells to this boundary. Cell IDs are `population250:row:col`, relative to this
fixed origin. A map viewport or route corridor never changes the lattice.
The population lattice is independent of the route graph's corridor-based origin.

For each clipped cell, densify metric polygon edges at at most 25 m before
transforming into the native raster CRS. Read only the intersecting raster
window. Transfer each native count by its intersected fraction:

`N(c) = sum(N(i) * native_area(c intersect i) / 10,000)`

This assumes uniform population density inside each native pixel. It preserves
fractional counts instead of duplicating an entire pixel into each touched cell,
sampling only cell centres or averaging previously assigned class labels.

Track observed counts, known area, declared NoData area and outside-raster area
separately in the native Mollweide plane. Declared NoData is masked; negative or
nonfinite unmasked values cause preparation to fail. Non-north-up, non-native
rasters are rejected. Source metadata and checksums must match their receipts.

Support is complete only with positive observed area and no more than `1e-6 m2`
total NoData/outside area per target cell. That tolerance handles numerical
projection slivers only. Material missing support makes estimated total, density
and class null, while retaining the observed partial count and missing areas.

For complete support:

`D(c) = N(c) / known_native_area(c) * 1,000,000` people/km2.

The tolerance means known area and transformed polygon area can differ by at most
`1e-6 m2` for a complete cell. Count transfer/density never mix native planar
areas with geodesic or nominal UTM areas. Export both actual metric cell area and
native support area; boundary cells are not assumed to be full 250 m squares.

## Five classes and exact boundaries

Compute `M`, the maximum density over all completely supported 250 m cells in
the full saved study. Unknown cells do not contribute. Use this same reference
for every display subset and later route request on this source/rule identity.

| Class | Density interval, M > 0 | Color |
|---|---|---|
| 0 - Very low | `[0, 0.2 M)` | Green `#26866c` |
| 1 - Low | `[0.2 M, 0.4 M)` | Yellow-green `#80a944` |
| 2 - Medium | `[0.4 M, 0.6 M)` | Amber `#d4a326` |
| 3 - High | `[0.6 M, 0.8 M)` | Orange `#d77732` |
| 4 - Very high | `[0.8 M, M]` | Red `#bd3849` |
| Unknown | No complete support | Gray `#78838e`, dashed outline |

Compute stored cutoffs as `M * (i / 5)` for i=1..4 and classify with a
right-inserting binary search. A value exactly on a stored cutoff enters the
higher class. Do not round values, use quantiles, or apply a fuzzy comparison
that moves neighbouring floating-point values across a boundary.

If M=0, every supported cell has known zero and receives class 0, with the
degenerate interval [0,0] explicitly inclusive. Other classes are empty. If no
complete cells exist, the surface state is unresolved, M is null and there are
no numeric bins. The API still exposes unknown geometries and support findings.

Export rule version, complete-study boundary/origin, source checksum and raster
metadata, epoch, area convention/tolerance, normalization scope, M, exact bins,
class counts and a stable model identity. Bin definitions are shared once in
response metadata, keyed by score; map properties do not duplicate these tables.
Returned metadata/features are copied so callers cannot mutate cached classes.

## Why 100 people becomes 625 people

For nominal full cells under one common area convention:

`(250 / 100)^2 = 6.25`

`100 people / 0.01 km2 = 10,000 people/km2`

`10,000 people/km2 * 0.0625 km2 = 625 people`

Thus 100 people per complete 100 m cell and 625 per complete 250 m cell express
the same density. Density thresholds themselves and ordinal class labels are
not multiplied by 6.25. A clipped/transformed cell uses its actual area instead.
Nominal 100 m/250 m count equivalents accompany each density bin; actual cell
equivalents are derived using that cell's native support area. These are
explanations, not fixed paper population thresholds. The maximum is calculated
after aggregation, so the new cutoffs need not equal native-grid cutoffs scaled
by 6.25.

## API, verification, caching and map behavior

`GET /api/datasets/{id}/study/population-costs`

Optional `bbox=west,south,east,north` filters displayed cells in EPSG:4326.
It never changes the study-wide M, bin definitions, lattice or identity.
The API returns source/classification metadata, display completeness/counts and
a cell GeoJSON layer. Each cell includes score, density, complete/observed
population count, support status/areas, grid size, native resolution and epoch.
An empty display subset is distinct from an unresolved full-study surface.

Population-only source verification reads the study schema/bounds/epoch, checks
the GHSL file against its unique manifest receipt and declared raster metadata,
and checks its checksum again after preparation/retrieval. This does not load or
attest unrelated OSM/DIPUL/terrain sources. Every core preparation call verifies
the source, even on a cache hit; no new data is acquired or original rewritten.

Cache at most two immutable study surfaces by source, bounds, epoch and rule
identity. Bound preparation to 100,000 candidate target cells, 10,000 pixels per
native window and 90 seconds, with per-cell/per-row deadline/cancellation checks.
Serialize at most 10,000 display features and a bounded 5 MiB response, reserving
64 KiB for metadata. A geographic STRtree bounds viewport selection. One API
population preparation runs at a time; concurrent requests receive 409/retry.
Resource exhaustion returns a structured `resource_limit`, never a coarser grid
or corridor-local normalization.

The Hannover GHSL control now shows only `population risk (250 m)` with the five
colors above, replacing the former green native-count display bins. Click a grid
cell to inspect it in the shared left inspector. Details include its actual
population/density/support and the fixed reference/thresholds. Hiding a layer
clears its selection; folding a group retains its state. Cached show/hide does
not repeat the request. Hiding during preparation retains that request/result;
initial map positioning does not start an overlapping viewport request.
For a complete full-study response, panning also reuses
the response; bounded/incomplete displays reload the viewport after movement,
with at most two cached responses and an explicit truncation notice.

Native population inspection remains available through `/study/population`, CLI
and the existing small-area experiment page. Its 100 m raw counts are not relabelled
as risk classes. The original source raster remains unchanged.

## Route contract reserved for Part 2

The approved next-part formula is:

`P(route) = sum(length_m(segment intersect population_cell) * class(population_cell))`

Intersection lengths will be measured in EPSG:25832, including endpoint connectors
and repeated traversals, with shared-edge/unknown-support policies documented
when implemented. Building score-metres, population score-metres and physical
distance will remain separate quantities. Part 1 exposes `routing_cost: false`:
these classes currently do not alter A*, Dijkstra, ABIT* or their constraints.

See the [implementation plan](../plan/iteration-014.md) for later objective/UI work.
