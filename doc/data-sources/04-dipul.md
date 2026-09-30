# 4. DIPUL

Reviewed: 2026-09-29. Decision: **first geographical-zone integration candidate**.

## Current access evidence

The official [announcement](https://www.dipul.de/homepage/en/aktuelle-meldungen/vector-data-for-geographical-zones-is-available/)
is dated 9 July 2026. Older WMS-only descriptions do not represent the current
documented offering.

| Requested field | Assessment |
| --- | --- |
| Access | Static downloads via Mobilithek; WFS 2.0.0; WMS 1.3.0; Map Tool export; ED-318 API/pub-sub with identity verification. |
| Format | Static GeoJSON and ED-318-extended GeoJSON; WFS generally GML; WMS rendered images. API documentation is offered as OpenAPI/AsyncAPI/Arazzo YAML. |
| Update frequency | Static package every 28 days with validity dates. Exact WFS/WMS and dynamic API refresh/latency commitments were not verified. |
| Spatial resolution | Vector objects with heterogeneous provenance, not a fixed-resolution grid. No universal metre accuracy confirmed. WMS output pixels are not source accuracy. |
| Automatic use | Strong technical candidate via WFS or versioned static downloads. Payload, quotas and semantics need validation; registered API access is a separate step. |

Source: [official download/access documentation](https://www.dipul.de/homepage/en/information/geographical-zones/download/).
The static distribution excludes dynamic information; it cannot stand in for
current temporary restrictions. The documented fields include legal references,
object identifiers and altitude units/references. Preserve these during import.

The [WFS/WMS documentation](https://www.dipul.de/homepage/en/information/geographical-zones/wfs-wms/)
lists individual layers, including control zones and active/inactive temporary
operational restrictions, and reserves rate/bandwidth limits.

- [WFS GetCapabilities](https://uas-betrieb.de/geoservices/dipul/ows?service=WFS&version=2.0.0&request=GetCapabilities)
- [WMS GetCapabilities](https://uas-betrieb.de/geoservices/dipul/ows?service=WMS&version=1.3.0&request=GetCapabilities)

Both requests failed in the research browser. They are provider-documented
endpoints, not successfully validated endpoints. Do not assume GeoJSON WFS output
until the actual capabilities confirm it. Mobilithek requires JavaScript in the
available research browser; its package workflow remains untested.

## License and derived results

The provider specifies CC BY-ND 4.0 and attribution to dipul. The
[license text](https://creativecommons.org/licenses/by-nd/4.0/legalcode.en)
permits producing/reproducing adapted material but does not grant sharing it.
Thus ND is not a blanket prohibition on local analysis. Whether a particular
exported fused dataset or map is adapted material needs review before sharing.
Keep source layers and attribution separate, and record intended output use.

## Proposed use in this project

Engineering proposal: show source zone categories independently; use vector
intersections to produce a route-condition report. Resolve applicability from
operation type, altitude, time and permissions before deriving a blocking mask.
A zone is not automatically an unconditional no-fly area.

Store source geometry and relevant legal/validity attributes. Determine whether
geometry already includes a regulatory buffer before applying additional distance
rules. Keep unknown applicability distinct from permitted passage. Prefer WMS
for visual comparison, not pixel-based extraction of route constraints.

## Next validation

Read capabilities, inspect a bounded feature response or one static package,
verify geometry/CRS/identifiers/validity/vertical fields, and compare a feature
against Map Tool. Confirm temporary-zone timing separately. Resolve license
handling for the planned demo output before publishing derived layers.
