# 2. OpenFlightMaps

Implementation update, **2026-10-16**: the approved independent snapshot/layer/API
and standalone preview have passed local acceptance under Iteration 011. See
[operation](../experiments/iteration-011.md) and
[current outcome](../iteration/iteration-011/outcome.md). The feasibility assessment
below remains the dated pre-implementation research; routing/legal integration
and full license archival remain outside the completed display functionality.

Reviewed: **2026-10-15**, against current project main `16720a0`.
Decision: **technically feasible for a bounded Hannover aviation-context layer**.
A first weekly delivery can cover verified acquisition, offline import, separate
map display and object inspection. Automatic route restrictions require a further
explicit semantic adapter and validation scope. This is feasibility research, not
an approved implementation iteration.

## Verified live distribution

The [official German page](https://openflightmaps.org/downloads/ed/) loads its
publication catalog through the provider's
[download script](https://openflightmaps.org/js/ofmTemplate.js). This review followed
that script to the [ED 2610 publication index](https://snapshots.openflightmaps.org/publicationServices/ED_2610.xml)
and downloaded the listed [German OFMX archive](https://snapshots.openflightmaps.org/live/2610/ofmx/ed/latest/ofmx_ed.zip)
without authentication. OFMX, OpenAir and CUP products are advertised in that index.
This verifies public file access; it does not establish a maintained public REST API
or an availability guarantee. The older GitHub OFMX repository is archived and
[points to GitLab](https://github.com/openflightmaps/ofmx); use the current
[provider documentation](https://gitlab.com/openflightmaps/ofmx/-/wikis/home).

| Item | Observed value |
|---|---|
| Cycle | AIRAC 2610, 2026-10-01 00:00 UTC to 2026-10-29 00:00 UTC |
| OFMX publication timestamp | 2026-10-12 12:07:00 UTC |
| Download | HTTP 200; 7,709,535 compressed bytes; no account/token |
| Isolated XML | 20,646,534 bytes; OFMX-Snapshot version 0.1 |
| Isolated effective/created | 2026-10-12 12:02:34 UTC |
| Germany objects | 1,056 Ase airspaces; 1,048 Abd boundaries; 1,360 Ahp aerodromes |
| Embedded XML | 38,450,011 bytes; 3,683 airspaces; includes surrounding-region records |
| Original evidence | `.cache/ofm-feasibility-20261015/ofmx_ed.zip` and `probe.json`, outside Git |

Archive SHA-256:
`e87c100883ea10dd196fb5a8ce200d8dbf6644ec5857f57f310ce57dd40280e1`.
The `latest` URL is mutable, including within one AIRAC cycle. Persist the original
ZIP, publication index, response timestamps and checksum in an immutable snapshot.
Do not identify the dataset solely by `2610`, and do not replace original studies.
The downloaded snapshot becomes effective after the project's 2026-10-07 historical
scenario; its cycle label alone cannot establish historical applicability. Select
an appropriate retained revision or a new explicit scenario for later experiments.

The [referenced 0.1 snapshot XSD](https://schema.openflightmaps.org/0.1/OFMX-Snapshot.xsd)
and the current provider Airspace wiki were also accessible. XML parsing and object
inspection succeeded; full schema validation, dependency resolution and a complete
production importer have **not** been performed.

## Hannover sample and geometry limits

Joining the isolated shape extension by `AseUid/@mid` to the semantic Ase objects
produced 1,048 numeric polygon candidates. A simple Shapely validity check found
1,022 valid and 26 invalid candidates. Five valid candidates intersect the retained
Hannover study boundary: Hannover CTR, two Hannover TMAs, a Hannover AGL band and
Langen FIS-DV. Five additional invalid candidates have bounding boxes overlapping
the study (FIR/UIR and a TMA); these are unresolved diagnostics, not five verified
intersections or grounds for silently discarding those objects.

These results describe the provider's supplied shape-extension interpretation.
They are not independent validation of all raw OFMX geometry or a claim of universal
source errors. Raw boundaries include great-circle segments, clockwise/counterclockwise
arcs, referenced frontiers and derived/shared geometry. Parsing an XML coordinate
list does not implement these semantics. Reconstruct/compare supported geometry,
retain tolerances and source identity, and diagnose unsupported cases explicitly.
Do not silently repair geometry and promote it to a confirmed restriction.

Hannover CTR sample: `mid=dd8fc890-28a3-46dd-c070-c8707b74b4e9`, `codeId=ED6D0F9`,
class D, lower `HEI 0 FT`, upper `ALT 2500 FT`. The provider documentation defines
HEI as above ground, ALT as above MSL and STD as standard-atmosphere altitude.
The upper value is 762 m MSL, not 762 m AGL. Current site-point checks using the
supplied shape put MHH, rheuma-lister and rheuma-podbi inside that footprint.
This is spatial evidence only; no route or legal applicability was decided.

The sampled Hannover TMAs include `ALT 2500 FT -> STD FL65` and `STD FL65 -> FL100`.
The whole German data mixes HEI/ALT/STD with FT/FL, with some missing limits.
The sample also contains TIMSH schedules and free-text operational conditions.
A high-level TMA, information sector or CTR label must not automatically become
a ground-to-infinity legal prohibition. Preserve type/class, original units,
references, schedules, remarks and evidence requirements. FL is not directly
convertible to project MSL without an explicit supported atmospheric model/policy.

## Fit to the current project

The project already has immutable source receipts/checksums, Shapely/pyproj,
EPSG:25832 motion checks, separate regional layers, restriction evidence profiles,
result invalidation and three shared planners. These provide useful integration
points, but current `RegionalConstraints` and its restriction decisions are
DIPUL-specific. A new source adapter is required; renaming OFM objects as DIPUL
features would lose provenance and misapply rule semantics.

Recommended pipeline:

1. Resolve the publication index; acquire a bounded ZIP and preserve receipts,
   metadata, license evidence and original bytes. Work offline thereafter.
2. Import isolated Germany semantic objects and geometries separately, join stable
   IDs, select by intersection with the Hannover boundary and keep full extents.
   Record rejected/unsupported objects rather than reporting complete coverage.
3. Expose a separate, bounded OFM API/map layer with type/class, original vertical
   limits, effective/publication times, operational text and source identity.
   Avoid sending full Germany or expanding arbitrary property keys in each feature.
4. Add read-only endpoint/route intersection diagnostics. Relate overlaps to DIPUL
   using explicit source links/geometry matching; retain both provenances and avoid
   charging a duplicate risk cost or interpreting duplicates as independent consent.
5. Only after a separately agreed scope, normalize supported height/time decisions
   into shared point/motion/connector checks for A*, Dijkstra and ABIT*. Retain
   strict/conservative/research behavior and the original building 0.9/0.1 objective.

## License and scope qualification

The [provider homepage](https://openflightmaps.org/) describes a royalty-free
license including commercial use, conditional on the OFMA General Users' License.
The [FAQ](https://openflightmaps.org/faq/) permits complementary information use
and states that the data is uncertified and must not be primary navigation data.
This is a promising basis for local research, not a completed redistribution review.

The bundled two-page `readme.pdf` refers to the OFM Data User License but does not
include the full text. The historical GUL URL used in the 2026-09-29 assessment
returned HTTP 404 on this review; the tested snapshots-host alternative also
returned 404. Obtain and archive the applicable full license and verify attribution,
produced-work/derivative-database and sharing requirements before public data or
map distribution. Do not assume CC0, OSM licensing or permission to redistribute
all rendered products. No provider was contacted and no account was created.

OFM does not supply observed real-time traffic, a complete NOTAM feed, drone
operator consent or the missing DIPUL legal evidence. It can supplement the current
aviation picture; acquiring it alone will not resolve the conservative endpoint
conflicts or certify route clearance.

## Proposed weekly delivery and acceptance

Engineering estimate, assuming the bounded first scope and existing dependencies:
roughly 3-5 development days; a complete nationwide all-format legal constraint
engine is outside that estimate. This is an effort estimate, not a deadline promise.

- Days 1-2: acquire/inspect/import one pinned German snapshot, join semantic and
  geometric objects, clip the selection to Hannover, report validity/unknowns.
- Day 3: separate map toggle, legend, feature details and source/cycle diagnostics.
- Days 4-5: endpoint/route intersection report, regression checks, a reproducible
  eight-site demonstration, README/HANDOFF and CI. Use permission/source decisions
  only where their semantics are explicitly supported; unresolved cases remain so.

Accept when a fresh checkout can reproduce the selected snapshot metadata and
Hannover overlay offline, inspect CTR/TMA/height references, report invalid/missing
geometry and stale/revised snapshots, export source provenance, and run existing
planners without changing their constraint or risk contracts. Full license archival
is a sharing prerequisite; raw curve validation and FL/time/legal automation remain
explicit follow-up items if not completed in the first scope.

## Historical assessment: 2026-09-29

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
