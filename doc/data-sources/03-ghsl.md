# 3. GHSL

Reviewed: 2026-09-29. Decision: **first population-data integration candidate**.

## Product selection and evidence

GHSL is a product family. Select **GHS-POP R2023A** explicitly for the first
experiment, rather than referring ambiguously to “GHSL data”. The current
[product catalogue](https://human-settlement.emergency.copernicus.eu/datasets.php)
also lists GHS-WUP R2025A long-range projections; R2023A is a deliberate baseline,
not a claim that all GHSL products are still on a 2023 release.

| Requested field | Assessment |
| --- | --- |
| Access | Anonymous HTTP file download, by product/epoch/resolution and tile; no account required in the catalogue. |
| Format | ZIP archives containing georeferenced TIFF rasters and documentation; floating-point people per cell. |
| Update frequency | Catalogue says irregular. Epochs at five-year intervals describe modeled years, not publication cadence. |
| Spatial resolution | 100 m / 1 km in World Mollweide; 3 / 30 arcseconds in WGS84. |
| Automatic use | High feasibility: download, verify, crop, read raster and calculate derived metrics locally. Actual tile validation remains pending. |

The selected product describes residential population, with 1975–2020 estimates
and projections for 2025/2030. Catalogue terms permit reuse with source
acknowledgment. Sources: [JRC dataset record](https://data.jrc.ec.europa.eu/dataset/2ff68a52-5b5b-4a22-8f40-c41da8332cfe),
[product description](https://human-settlement.emergency.copernicus.eu/ghs_pop2023.php).

The public [file index](https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/)
was readable. Use the [download wizard](https://human-settlement.emergency.copernicus.eu/downloadWizard.php)
to identify the tile and retain the resulting versioned URL. No tile was downloaded.

## Proposed use in this project

Engineering proposal: begin with 100 m equal-area population data and keep its
native values, CRS and NoData mask. Display a distinct population layer, not a
new Ramke tag score. Select 2020 estimates or 2025 projections explicitly in the
experiment configuration and label that choice.

Convert count to density using cell area before comparing density thresholds.
A native 100 m square has area 0.01 km², so a count of 20 corresponds to
2,000 people/km². Do not apply that formula to a geographic-degree grid without
calculating its area. The publisher labels Mollweide as EPSG:54009; verify its
actual CRS definition with the raster/library, where ESRI:54009 may be the
recognized identifier.

Regridding must preserve the meaning of population counts. Upsampling does not
create finer population knowledge, and summing duplicated fine-grid values would
inflate totals. Keep visualization resampling separate from analytical aggregation.

Potential routing outputs are a population-based preference cost and population
statistics within a defined route corridor. A line alone has no exposure area.
Neither metric is automatically a SORA result or an expected casualty count.

## Project-specific limitations and next validation

The existing query area is approximately 0.0304 km²: roughly three native
100 m cell areas, although the actual intersected-cell count depends on alignment.
It may be too small for informative population-driven detours. Select a larger
bounded test region only after checking data variation.

Inspect tile metadata, CRS, pixel size, NoData and a small crop; verify units and
aggregation with a hand-checkable example. Add raster support alongside existing
OSM vectors. Residential estimates do not establish current crowds or daytime
occupancy; record this limitation in route results.
