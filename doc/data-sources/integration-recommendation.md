# Integration recommendation for the existing prototype

Date: 2026-09-29. These are **engineering proposals**, not completed work or an
approved iteration plan. Source evidence is in the six linked assessments.

## Current implementation and the missing connection

The current code acquires OSM vectors, saves GeoPackage plus metadata, and
classifies building/highway/landuse/natural tags independently. The explorer
displays those results. There is no fused grid, route search or mission model.

Relevant implementation points:

- [OSM adapter](../../backend/src/uas_planner/acquisition/osm.py)
- [OSM-specific storage](../../backend/src/uas_planner/storage/dataset.py)
- [Independent classification](../../backend/src/uas_planner/core/costs.py)
- [Read-only API](../../backend/src/uas_planner/api/app.py)
- [Current analysis policy](../rules/independent-costs.md)

Storage currently requires `element_type` and `osm_id`, and assumes EPSG:4326
vectors and OSM source metadata. A raster or traffic feed should not be forced
into that structure. Preserve this working pipeline and add source-specific
adapters with a small shared provenance record when implementing integration.

## Recommended sequence

| Stage | Work | Evidence needed to complete it |
| --- | --- | --- |
| 1 | Resolve mission assumptions and validate GHSL/DIPUL access | Defined scenario, sample metadata/payloads, units, coverage and access conditions |
| 2 | Display OSM, population and zones separately | Correct alignment and source/epoch/validity labels; unknown data visibly distinct |
| 3 | Define analytical layers | Explicit metric CRS, spatial support, overlap rules, NoData policy and conditional zone handling |
| 4 | Add a simple baseline planner | Route or explicit no-route result; start/end and edge traversal respect defined constraints |
| 5 | Compare routes with incremental data | Same mission/endpoints; quantified length, population metric, zone intersections and unknown coverage |
| Later | OFM supplementation and conditional Droniq feed | Parsed airspace semantics; separately authorized and documented time-dependent traffic input |

Read the SORA methodology while defining stage 1 inputs. Apply EGRED if the
mission is a BOS scenario. This does not require implementing all of either
document before a research route can be demonstrated.

## Test area

The existing `braunschweig-demo` metadata records bounds
`(10.519, 52.269, 10.521, 52.271)` in longitude/latitude and an area of
approximately 0.0304 km². It is useful for ingestion regression checks, but may
not contain enough population variation or meaningful detour options.

Propose a separate bounded area around Braunschweig with residential and less
populated land, selected after looking at source coverage. A 2–4 km-wide area
is a candidate scale, not a finalized boundary. Stay within the current 25 km²
query limit and preserve the original dataset. The previously canceled expanded
OSM acquisition has not been resumed.

## Minimum analytical contract

Keep the following separate even if the renderer shows them on one map:

- **Preference costs:** existing ordinal tags and a separately defined population
  transformation. Do not add incompatible units or treat ordinal levels as measured risk.
- **Constraints:** only those restrictions established to apply to the specific
  altitude, time and operation; retain unresolved conditions explicitly.
- **Data quality:** missing coverage, unknown classes, age, invalid geometries
  and source resolution. Absence of a feature is not proof of zero risk.
- **Methodology checks:** versioned SORA/EGRED inputs and outcomes, including
  items requiring human judgment.

Choose grid size after source resolution and operating assumptions are known.
Use a suitable projected metric CRS for distances. Define physical support for
points/lines explicitly; UI line widths are not buffers. Specify treatment of
complete source features extending beyond the query boundary.

A* is one possible first planner once this contract exists. Its cost function,
connectivity, diagonal collision behavior and heuristic must match the model.
Algorithm selection is secondary to valid spatial inputs at this stage.

## Proposed comparison

Use identical endpoints and applicable constraints for:

1. A distance-only feasible baseline.
2. A route adding explicitly modeled OSM preference costs.
3. A route additionally using the selected population product.

Show source layers separately before showing routes together. Report route
length, the defined population metric, applicable zone intersections, unknown
coverage, input versions and runtime. Do not label a lower weighted score as
proof of safety or completed SORA compliance. If no valid route exists, preserve
that result instead of silently ignoring a restriction.

## Open items for the next implementation plan

| Item | Why it matters |
| --- | --- |
| Civil or BOS mission; aircraft, height and timing | Determines applicable rules and the spatial/temporal model |
| Actual GHSL tile and epoch | Enables raster/NoData/unit verification and reproducibility |
| DIPUL WFS or static package payload | Confirms schema, validity, vertical fields and source-buffer meaning |
| DIPUL derived-output license handling | Determines what can be shared with the demo or results |
| Current German OFM vector distribution | Confirms importer scope and package freshness |
| Droniq research interface agreement | Determines whether live integration is available at all for this project |
| Current EGRED edition/change log | Prevents encoding a superseded procedure |

For every imported source, retain source ID/URL, download time, source epoch or
validity interval, schema/product version, CRS, units, native resolution, coverage,
NoData meaning, license and checksum. Save analytical rules separately from raw
data so experiments can be reproduced.
