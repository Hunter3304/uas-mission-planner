# Iteration 008 Part 1 — Hannover source preparation

Date: 2026-10-05 (Europe/Berlin).
Tracking: Milestone 7, [Issue #66](https://github.com/Hunter3304/uas-mission-planner/issues/66).
Branch: `feature/66-hannover-acquisition`, based on `iteration/008`.

## Scope and behavior

The former external adapter only accepted Braunschweig and at most 25 km².
The new regional workflow configures an approximately 411.74 km² Hannover/Lehrte
area containing all eight supplied hospital/laboratory/practice sites and a
5 km margin around their projected extent. Legacy small-area acquisition remains
available with its original limit; regional scope is explicit in stored metadata.

The delivery adds:

- A verified address catalog with operator references, original OSM lookup
  responses, selected coordinates and an explicit unverified-landing-site status.
- Offline region regeneration from the site list and a configurable metric margin.
- OSM acquisition using either an immutable dated Geofabrik extract or bounded
  Overpass requests, with original bytes and provenance preserved.
- DIPUL capabilities, per-layer schemas and paginated original responses with
  matched counts, source IDs, geometry, CRS and request-scope checks.
- GHSL publisher ZIP preservation and a native aligned population crop without
  resampling, retaining known zero and NoData separately.
- SHA-256 manifests, download caches, verified explicit resume and offline rebuild
  into a new output directory. A completion marker is written only after validation.
- Sparse tag-object storage for regional OSM features, avoiding a mostly empty
  dataframe with thousands of tag columns while preserving original tag values.

Commands and data contracts are documented in the
[workflow guide](../../experiments/iteration-008/README.md).

## Acquisition decisions

The initial Overpass run successfully preserved 18 original full-size chunks and
one subdivided child, but further requests repeatedly returned HTTP 504 or timed
out, including public alternatives. The pipeline retains bounded retry and
subdivision support; it does not omit failed parts of the region or label the
incomplete run as complete.

The default configuration therefore uses the dated official Geofabrik
`niedersachsen-261003.osm.pbf` (506,819,877 bytes). Its publisher MD5 is checked,
and the original publisher polygon must cover the complete study rectangle.
The optional Overpass configuration remains separately documented.

The installed GDAL OSM driver is reused; no dependency or host runtime is added.
Its source tag handling is verified with actual native driver fixtures, including
building heights, original way IDs, polygon geometry, road tags, quotes and
multiline tag values. Closed-way duplicate representations prefer polygons.
Native source parsing can report non-closed rings; source quality findings remain
visible in dataset metadata and are not presented as flight clearance.

The GHSL ZIP is reused from the previously verified publisher archive. It is the
same R2023A 2020 product and R3_C19 tile; original retrieval timestamps are retained,
with cache reuse recorded independently. DIPUL payloads retain their own retrieval
timestamps. Acquisition timestamps are not mission validity.

## Verification

Completed local snapshot: `data/hannover-part1-v4`. It was built offline from
preserved raw receipts, without contacting source services. Independent inspection
forbade network requests and verified all 70 manifest payloads.

| Item | Observed result |
|---|---|
| Region | 411.74130068017575 km²; all 8 sites inside; 5 km metric margin |
| OSM source | dated Geofabrik PBF; publisher checksum and extract coverage verified |
| OSM objects | 326,334 unique node/way/relation identities |
| Buildings | 175,367 tagged objects |
| Roads | 110,706 tagged objects |
| Land use | 9,549 tagged objects |
| Natural | 30,837 tagged objects |
| Tag vocabulary | 1,481 keys, preserved as sparse per-object dictionaries |
| Geometry | 187,713 MultiPolygons; 91,736 LineStrings; 46,875 Points; 10 GeometryCollections |
| Invalid geometry | 13 objects retained with diagnostics; no silent repair |
| DIPUL | 31 advertised layers; 324 returned features; complete bounded response counts |
| DIPUL temporary layer | query completed, zero returned features; applicability/NOTAM coverage unresolved |
| GHSL | native 100 m R2023A 2020 crop, 135 × 323 cells |
| GHSL values | 43,605 native crop cells; 21,935 known-zero cells; zero NoData cells |
| Original/crop equality | values and masks equal the retained ZIP's aligned native window |

Tag-layer counts overlap and therefore do not sum to the total. Population counts
above describe the entire aligned native crop, including its small edge margin;
they are not an area-weighted population total for the geographic rectangle.

Machine-readable [evidence](part1-evidence.json) includes per-layer DIPUL counts
and IDs/reasons for invalid geometries and GeometryCollections. Those quality
findings require explicit treatment in Part 2; source integrity does not make
invalid geometry or unresolved constraints suitable for planning.

Final validation: **187 backend tests passed, one existing Windows symlink-permission
skip** (80.80 s); Ruff lint and format checks passed; frontend ESLint and production
build passed. The 18 new regional-source tests and sparse-storage regression cover
actual GDAL parsing and pipeline contracts. Dependency deprecation warnings remain
non-failing. No frontend source was changed.

Backend fixtures cover region/site containment and gap-free request partitioning,
parameter bounds, incomplete/error responses, cache/resume integrity, offline
rebuild after derivative loss, interrupted derivation recovery, DIPUL pagination
and duplicate IDs, request-scope consistency, publisher-source loading, sparse
tag preservation, native raster coverage, and transport interruption/mirror receipts.

The full backend regression, Ruff, frontend lint and production build are run for
this delivery. No new UI workflow is claimed; endpoint selection and independent
regional source-layer display belong to Part 4.

## Remaining scope

This is a source study (`study.json`), not a flight experiment (`experiment.json`).
Part 2 must prepare hard constraints and bounded terrain/vertical-reference support;
Part 3 must integrate A*/Dijkstra/ABIT*. The inherited building-risk/distance
objective remains 0.9/0.1. GHSL population costs and cross-layer fusion are deferred.
The configured altitude is 100 m AGL and speed is 30 m/s, with the requested
100–120 m and 25–35 m/s ranges validated but no route or dynamic flight simulated.

DIPUL acquisition includes available temporary restriction geometry, not a finding
of complete legal, temporal, NOTAM or altitude applicability. An address coordinate
does not establish an authorized launch/landing position. The 5 km region margin
requires later route and boundary-sensitivity experiments.

The initial Part 1 implementation was delivered locally on 2026-10-05. The user
authorized commit and feature-branch publication on 2026-10-06. Source datasets
remain local and excluded from Git; pull request creation and integration merges
remain outside this publication request.

On 2026-10-06 the user authorized feature-to-iteration and iteration-to-main PR
integration after successful remote CI. This delivers Part 1 only; Parts 2–5 remain
deferred. The iteration is not declared complete by this partial delivery.
