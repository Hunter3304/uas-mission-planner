# Local datasets

Generated datasets and caches are excluded from Git. A successful acquisition creates a new directory containing `features.gpkg` and `metadata.json`. Keep both files together. The metadata is written last and includes a checksum of the GeoPackage.

The prototype preserves complete source geometries intersecting the requested area, so feature bounds can exceed query bounds. OSM tags are stored losslessly as JSON-compatible values in the `tags_json` GeoPackage column, then expanded on reload. Missing values are normalized to JSON null; pandas column dtypes are not guaranteed to be identical after reload.

Invalid source geometries are counted in metadata and retained rather than silently repaired. A failed write may leave an incomplete directory; inspection fails if the manifest is missing. Choose a new output directory for a retry.

Map data attribution: © OpenStreetMap contributors. See https://www.openstreetmap.org/copyright for source licensing. These datasets are geographic features, not an authoritative aviation restriction database.

Part 1 experiments use a separate `experiment.json` manifest, native raster
window and `raw/` source responses. Their OSM snapshot resides under `osm/` with
its original schema. Copy the entire experiment folder for offline reproduction.
The API accepts this layout and the legacy flat OSM layout. See
[external experiment instructions](../doc/experiments/part1.md). External data is
never assigned synthetic OSM IDs and is not included in OSM download buttons.
