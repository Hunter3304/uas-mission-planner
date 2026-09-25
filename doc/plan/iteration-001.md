# Iteration 001: Environment and map-data round trip

## Agreement

The user approved Python 3.13, Node.js 24 LTS, npm 11, and uv, and selected this first iteration's core scope: **specify an area -> acquire data -> save -> reload**.

Dependency preparation and the core round trip are authorized. GitHub CLI has been installed and authenticated with the user's browser authorization. The public repository and Iteration 001 Milestone have been created. Create associated Issues before starting their feature branches.

## Goal

Deliver a reusable Python core and a command-line entry point demonstrating a complete small-area OpenStreetMap data round trip. Prepare dependencies for the separately running React frontend without expanding this iteration into a map UI.

## Scope

- Install and lock Python and frontend dependencies in their respective project directories.
- Accept an explicit EPSG:4326 bounding box with named west, south, east, and north coordinates.
- Reject invalid coordinates and excessive query areas before network requests. Choose and document a conservative small-area limit during implementation.
- Acquire building, highway, landuse, and natural features through OSMnx/Overpass.
- Preserve OSM element type and ID, relevant tags, geometry, and CRS.
- Save a dataset to GeoPackage with JSON acquisition metadata.
- Reload the saved dataset without network access and report counts, bounds, and CRS.
- Cache requests and distinguish no matching features from failed requests.
- Add offline tests and a small live acquisition demonstration.

## Acceptance criteria

1. Locked dependencies install in the agreed local environment, and core libraries import successfully.
2. A documented command accepts a small bounding box and produces a local dataset and metadata.
3. Metadata includes source, query bounds, requested tags, acquisition time, feature count, schema version, and dataset checksum.
4. Reloading preserves feature identity, relevant attributes, geometry, feature count, and CRS. Geometry comparisons use an appropriate equality check rather than file byte equality.
5. Reloading works without an external service connection.
6. Invalid input, empty results, network failure, and an existing output destination have explicit behavior; existing datasets are not silently overwritten.
7. Tests cover the meaningful failure cases and persistence round trip with a fixed offline fixture.
8. A live small-area run is recorded separately from offline tests. If the service is unavailable, report that limitation rather than claiming live validation passed.
9. README, iteration feedback, and HANDOFF describe the actual delivered state and limitations.

## Planned Issues (create before corresponding feature branches)

| Work item | Acceptance focus |
| --- | --- |
| Establish reproducible development environments | Lockfiles, runtime pins, dependency import checks, documented setup |
| Implement bounded OSM feature acquisition | Input validation, source adapter, identity preservation, errors and cache |
| Implement dataset persistence and offline reload | GeoPackage, metadata, safe output handling, round-trip tests |
| Deliver and validate the core command-line workflow | End-to-end commands, live demonstration, documentation and retrospective |

All Issues belong to the **Iteration 001** Milestone. Feature branches originate from `iteration/001`, merge into that branch through PRs, and are deleted after merge. Close completed Issues explicitly when necessary. Merge the complete iteration into `main` after acceptance.

## Deferred scope

React application screens, interactive map selection, HTTP acquisition endpoints, population datasets, risk modelling, route planning, and deployment are subsequent work. The research core must remain independent of FastAPI and the frontend.

## Proposed demonstration

Use a small Braunschweig bounding box, selected during implementation. Keep the downloaded dataset local; retain commands and a concise evidence report in the repository. OSM features do not constitute authoritative aviation restrictions.
