# 2. OpenFlightMaps

Reviewed: 2026-09-29. Decision: **supplementary aviation-data candidate**.

## Verified source characteristics

The official [downloads index](https://openflightmaps.org/downloads/) includes
[Germany (ED)](https://openflightmaps.org/downloads/ed/). The
[FAQ](https://openflightmaps.org/faq/) describes CUP/OpenAir exports, the AIXM-based
model, and links to OFMX documentation. It also states that the data is not
certified and is supplementary rather than a primary navigation source.
The provider's [OFMX repository](https://github.com/openflightmaps/ofmx) identifies
OFMX as an AIXM 4.5-derived format and points to its successor on GitLab.

| Requested field | Assessment |
| --- | --- |
| Access | Regional file downloads and map products. Current German payload/URL must be inspected; a stable public REST API is not established here. |
| Format | OFMX structured XML is the preferred candidate for semantic data; provider also describes OpenAir/CUP and PDF/PNG map products. Verify which exports the selected cycle actually offers. |
| Update frequency | AIRAC cycle, nominally 28 days; confirm validity and publication delay on each package. |
| Spatial resolution | Vector geometry has no fixed grid spacing. Published 1:500,000 chart scale is not metre-level accuracy. No universal positional accuracy was verified. |
| Automatic use | Likely suitable for file ingestion after format/version, current distribution and license checks; no parser or package has been tested. |

The provider documents the 28-day cadence and 1:500,000 chart products in its
[AIRAC/chart explanation](https://openflightmaps.org/2016/08/18/rocketroute-installation-instructions/).
This is an older official description, not proof of a current download's freshness.
The [OFMA overview](https://openflightmaps.org/) allows use under the OFMA General
Users' License; preserve the exact [license](https://www.openflightmaps.org/live/downloads/20150306-GUL.pdf)
with the selected distribution. Do not treat it as OSM's license.

## Proposed use in this project

Engineering proposal: parse aviation objects into a separate vector layer with
source identity, airspace category, vertical limits and validity where available.
Display airspace outlines separately from OSM costs and DIPUL zones.

For route evaluation, intersect the planned operating volume with relevant
airspace and interpret its conditions. A map footprint alone must not make every
airspace a ground-to-infinity obstacle. Preserve feet/metres and AGL/MSL/flight
level distinctions; unresolved altitude references should yield unresolved checks.

Avoid counting a restriction twice when DIPUL and OFM describe related airspace.
Their provenance and purposes should remain visible. Do not substitute rendered
chart pixels for source geometry.

## Next validation

Obtain one current German vector package from the official distribution, record
its cycle/schema/license/checksum, parse an airspace boundary and vertical limits,
then compare it visually with the provider's chart. The new regional page was
located, but this payload validation is still open. No fixed download URL is
invented in this assessment.
