# Iteration 005 — Part 2 grid and constraint preparation

Part 2 was authorized on 2026-09-30. The backend prepares an EPSG:25832 square
grid, default 50 m, with a maximum of 10,000 cells. The API accepts a positive
finite cell size. The browser rebuilds the grid when the value changes. The API
cache key includes the verified experiment manifest and cell size, so changed
source checksums or mission assumptions invalidate the prepared result.

GHSL counts are apportioned by the intersection area of each native 100 m
Mollweide pixel with each grid cell. The grid exposes estimated people, density,
known and unknown support area. A cell touching NoData has an unknown count and
density; zero remains numeric zero. These fields do not affect edge lengths.

The model checks reported DIPUL altitude limits in metres or feet against fixed
AGL. Terrain-derived MSL altitude is shown at cell centers; it cannot bound the
terrain profile across cells or segments, so MSL constraints remain unresolved.
AGL vertical nonintersection can be established; vertical overlap remains unresolved because legal conditions,
mission-time validity and scenario applicability are unverified. The saved four
static layer types do not verify temporary restriction coverage. Thus each cell
and connector is unresolved under the `block_unresolved` research policy. The
graph offers candidate connections and explicit diagnostics, not a validated
permission graph. OSM tag risk classes are not obstacles.

Every candidate center-to-center segment and endpoint connector is checked
against DIPUL vector geometry, including zones crossed between endpoints.
Diagonal connections missing an orthogonal supporting cell are blocked. Cell
and edge reasons are exposed in the API and browser inspector. Endpoint
coordinates remain exact. Edge length is horizontal metric length.

No route search, legal clearance, dynamic timing, 3D clearance or flight
feasibility is claimed. Resolving temporary coverage and an approved legal rule
catalogue is required before a validated traversable graph can be produced.

## Closeout validation (2026-09-30)

Issue #46 tracks this part in Milestone #5. Local implementation preceded remote
tracking; its feature branch followed issue assignment and was based on the
iteration branch synchronized with the Part 1 maintenance baseline.

Population tests independently check a native 20-person pixel and its two
halves, zero versus NoData, and support outside the raster. Graph tests check
metric lengths, exact connectors, resolution limits and a narrow zone crossed
between centers. API tests verify resolution/config/source cache invalidation
and require checksum validation even on a cache hit.

Local validation: 96 Python tests pass with one Windows symlink-permission skip;
9 mocked browser tests and 5 real-stack browser tests pass; Ruff lint/format,
ESLint and production build pass. Existing dependency deprecation warnings
remain non-failing. Native rasters and snapshots are unchanged.

The actual `braunschweig-part1-v2` snapshot produces 3,809 cells and 14,867 edges
at 50 m, and 978 cells and 3,726 edges at 100 m. Every cell is unresolved under
the declared coverage policy. Cold API preparation measured about 35 s / 10 s
respectively on this machine. Exact start/end coordinates and horizontal
connector lengths were inspected. Chrome verified cell selection, resolution
rebuild and mobile layout without page errors. Screenshots are local-only at
`.cache/part2-real-grid.png` and `.cache/part2-real-mobile.png`.

The user requested closeout of Part 2; route search remains separate. Part 2 is
ready for integration after CI; final PR/merge/cleanup evidence will be recorded
after delivery. The fixed v0.3.0 tag is retained.
