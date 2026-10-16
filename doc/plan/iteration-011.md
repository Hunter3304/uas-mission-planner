# Iteration 011 - Independent OpenFlightMaps layer and visualization

Date: 2026-10-15 (Europe/Berlin).
Status: **approved for implementation on 2026-10-16**.
The user requested implementation under the standard project workflow, authorizing
tracking, feature development, validation and CI-gated integration to main.
The earlier documentation-only authorization is superseded. The six steps below
form one visualization delivery; no five-Part split has been agreed.

## Objective and scope interpretation

Deliver an independent OpenFlightMaps (OFM) dataset for the existing Hannover
eight-site study region, document its information and access interfaces, and make
the selected layers inspectable in a standalone visualization preview.

Interpret "do not integrate into the map yet" as deferring integration into the
existing main explorer map. A separate offline preview of the independent layers
provides the requested visualization. It may display the study boundary and the
eight reference sites without requiring street tiles or another online basemap.
The preview does not create routes, make permission decisions or change the
existing DIPUL/OSM/GHSL/terrain controls.

## Standing default region

The user explicitly confirmed this as the default scope for subsequent project
maps and data-layer work, unless a later instruction selects a different region.
The source of truth is
[`hannover-study.json`](../experiments/iteration-008/hannover-study.json),
`region_id: hannover-lehrte-5km`, matching retained `hannover-part1-v4`.

| WGS84 bound | Value |
|---|---:|
| West | 9.650495867959657 |
| South | 52.32042221571155 |
| East | 10.068841103123809 |
| North | 52.45032927853548 |

Retain the existing 5,000 m study margin; reuse these saved bounds rather than
recomputing a new box from the site points. The eight reference site IDs are:

- `mhh` - Medizinische Hochschule Hannover.
- `henriettenstift` - DIAKOVERE Henriettenstift.
- `rheuma-lister` - Rheumapraxis Hannover, Lister Meile.
- `rheuma-podbi` - Rheumapraxis Hannover, Podbielskistrasse.
- `limbach-lehrte` - MVZ Labor Limbach Lehrte.
- `amedes-georg` - amedes MVZ wagnerstibbe, Georgstrasse.
- `amedes-schiffgraben` - amedes MVZ genetics, Schiffgraben.
- `friederikenstift` - DIAKOVERE Friederikenstift.

Default visualization fits this study boundary and keeps all eight sites visible.
Panning/zooming does not fetch new data or expand source coverage. This is a
default view and processing extent, not a request to lock all map interaction.
An airport or airspace outside this region is not a reason to enlarge it silently.
Historical Braunschweig datasets remain selectable explicitly and unchanged.
This documentation establishes the standing default; runtime default changes are
implemented only when work on the applicable visualization is authorized.

## Information inventory and first-delivery priorities

The inspected Germany archive uses OFMX 0.1. The inventory below describes source
information, not a guarantee that every field exists on every regional object.

| Source information | Example fields | First delivery |
|---|---|---|
| Airspace semantics (`Ase`) | Stable source identifier, name, type such as CTR/TMA/R/D/TMZ/RMZ, class | Required independent polygon layer and object details |
| Airspace boundaries (`Abd`, optional shape extension, derived/shared geometry) | Geographic coordinates, arcs/frontier references, source links | Required supported visualization geometry with provenance/quality diagnostics |
| Vertical limits | Lower/upper values, FT/M/FL units, HEI/ALT/STD reference | Required original-value display and qualified numeric conversions; no automatic applicability |
| Operational schedules and remarks | Timetable records, H24/TIMSH where present, free-text conditions | Preserve and display; do not infer active/inactive status from unsupported schedules |
| Aerodromes (`Ahp`) | Identity/name/type, coordinates, elevation and original units | Separate point sublayer if objects lie in the default region; a verified empty result is valid |
| Runways (`Rwy`, `Rdn`, related records) | Dimensions, surface, direction/bearing, endpoints where supplied | Inventory and airport details where linked; drawing runway geometry is optional and explicitly qualified |
| Aviation communications/services (`Fqy`, `Sae`, related records) | Frequency, unit, service/callsign and associations | Preserve/display linked attributes where available; not a radio-operation recommendation |
| Navigation aids/points (`Vor`, `Ndb`, `Dme`, `Dpn`, etc.) | Name, type, location, frequency/channel where present | Document available categories and counts; optional later drawable sublayers |
| Source metadata | Region, AIRAC cycle, snapshot effective/created time, retrieval time, schema, checksum/license evidence | Required snapshot panel, API metadata and export provenance |

The eight hospitals/practices/labs are existing project reference sites, not OFM
aerodrome records. Label and style them separately.

## Interfaces: provider access versus proposed project API

### Verified provider file interfaces

These are official HTTP file resources, not evidence of a supported public REST
or spatial-query API. Resolve URLs from the publication index where possible.

| Interface | Purpose |
|---|---|
| `https://openflightmaps.org/downloads/ed/` | Human-facing Germany download entry |
| `https://snapshots.openflightmaps.org/publicationServices/ED_{AIRAC}.xml` | Publication catalog, cycle validity, product links and publication timestamps |
| `https://snapshots.openflightmaps.org/live/2610/ofmx/ed/latest/ofmx_ed.zip` | Verified OFMX example; pin the received revision by checksum, not the mutable `latest` URL |
| OpenAir/CUP links in the publication catalog | Alternative airspace/point exports; inventory only, no parallel importer required in this scope |
| Referenced OFMX schema/documentation | Field/association definitions and version checks; select the schema matching the actual package |

Acquisition remains a bounded CLI/file operation, separate from read-only viewing.
Keep the publication response and archive, response headers/retrieval time,
checksums, original metadata and available license evidence. Refresh creates a new
snapshot. Regional selection happens locally; full Germany may be downloaded but
must not be sent to the preview as though it were the selected local layer.

### Local interface contract

| Proposed endpoint | Response |
|---|---|
| `GET /api/ofm/snapshots` | Available local OFM snapshots and their study/cycle identities |
| `GET /api/ofm/snapshots/{id}` | Snapshot metadata, region, inventory, quality counts and supported layer names |
| `GET /api/ofm/snapshots/{id}/features?layer=airspaces` | Bounded GeoJSON for the saved default region; allow the aerodrome layer when available |
| `GET /api/ofm/snapshots/{id}/features/{feature_id}` | Complete selected-object attributes, relationships, provenance and geometry quality |
| `GET /api/ofm/snapshots/{id}/diagnostics` | Invalid/missing/unsupported geometry, missing fields, snapshot/reference/coverage diagnostics |

These names describe the planned contract and can be aligned with existing API
conventions during implementation. No browser-triggered acquisition or external
write is included. A proposed CLI supplies fetch/import/inspect/preview operations;
exact command names follow the approved implementation design.

## Implementation sequence

1. **Define the layer contract and snapshot storage.** Separate OFM identity from
   OSM and DIPUL IDs. Preserve semantic records, original geometry/attributes,
   selected-region metadata, receipts and explicit unsupported states.
2. **Acquire and import one pinned German revision.** Parse matching-version OFMX,
   join `AseUid` references, retain data needed by the selected airspaces and
   aerodromes, and compare the selected objects with the saved study boundary.
3. **Prepare independent display geometry.** Select objects intersecting the
   region; retain complete original extents. Display may be clipped at the
   viewport, but derived/clipped geometry must never replace source originals.
   Track unsupported curves, references and invalid shapes explicitly. Provider
   shape-extension geometry is a display derivative, with its origin recorded.
4. **Expose the read-only local layer and diagnostic APIs.** Return sparse,
   bounded properties; provide feature details separately. Missing geometry must
   remain inspectable through metadata/diagnostics, with no silent omission.
5. **Build the standalone preview.** Show the boundary, all eight project sites,
   independently switchable airspaces/aerodromes, type/class legend, a selectable
   feature list/details, original height limits and snapshot/quality status.
   Include pan/zoom or equivalent region inspection and GeoJSON/metadata export.
   Work from retained files without online basemap tiles.
6. **Verify and document.** Record reproducible commands, layer counts, known
   failures, preview evidence, operating instructions and README/HANDOFF status.
   Run relevant parser/storage/API checks and preview smoke checks; run repository
   integration gates before publication and main integration.

## Data interpretation and known research findings

- HEI, ALT and STD mean different height references. Preserve FT/M/FL and original
  values; arithmetic feet-to-metres conversion is not an altitude-datum transform.
  FL stays a flight level unless a supported conversion policy is separately agreed.
- Do not turn all airspace polygons into prohibitions. The first delivery displays
  source information without an OFM legal-decision or routing-constraint adapter.
- Prior numeric shape-extension probing found 1,022 valid and 26 invalid Germany
  polygon candidates; five valid intersections and five additional invalid
  overlapping bounding boxes concern the existing study. These are feasibility
  observations, not fixed expected counts or a complete geometry validation.
- Keep original schedules/remarks and missing fields. Unknown categories and
  unsupported relationships need visible diagnostics and qualified coverage.
- AIRAC validity, revision effective time and retrieval time are distinct. The
  inspected revision is effective on 2026-10-12, after the historical 2026-10-07
  mission; do not imply that it reconstructs that historical flight scenario.
- Preserve license evidence and attribution. The historical full GUL link returned
  404 during research; public redistribution requires the applicable complete
  license to be obtained/reviewed. Do not upload original data by default.

## Acceptance

1. Importing/reading a saved snapshot reproduces its checksums, metadata and
   selected-region inventory offline, with no overwrite of original datasets.
2. Default extent exactly matches `hannover-lehrte-5km`; all eight reference sites
   are visible. Sparse/empty source sublayers do not expand the study boundary.
3. Supported OFM airspaces are independently visible and inspectable. Aerodrome
   points, where present, have their own toggle and distinguishable reference sites.
4. Selected objects show name/ID/type/class, original lower/upper reference/units,
   available schedule/remarks, source revision and geometry/field diagnostics.
5. Preview and APIs expose excluded or unsupported records and do not portray
   incomplete coverage as complete. Layer exports retain OFM provenance.
6. The preview runs independently of the existing main map and route controls;
   route algorithms, costs and restriction decisions keep their current behavior.
7. README/HANDOFF describe actual results, reproducible operation and the standing
   eight-site default. No implementation completion is claimed from this plan.

## Deferred scope

Existing main-map integration, basemap changes, route-intersection analysis,
automatic height/time/legal decisions, DIPUL/OFM constraint fusion, route avoidance,
population/risk changes, real-time traffic/NOTAM integration, nationwide map
rendering and region expansion are outside this visualization delivery.

## Tracking and evidence

On explicit implementation authorization, follow the current HANDOFF workflow:
create the iteration milestone/issues before feature branches, implement and
validate, then perform any separately authorized CI-gated remote integration.
Implementation is authorized on 2026-10-16; record verified tracking and delivery facts in HANDOFF.

See [feasibility research](../data-sources/02-openflightmaps.md) and the existing
[eight-site catalog](../experiments/iteration-008/locations.json). Existing raw
research samples remain under `.cache/ofm-feasibility-20261015/`, outside Git.
