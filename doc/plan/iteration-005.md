# Iteration 005 — Part 1: reproducible external layers

Delivery: Part 1 merged into `main` through PR #39 on 2026-09-30. Parts 2 and 3
in the discussion draft are not part of this delivery.

Approved scope: user requested Part 1 on 2026-09-29 and confirmed the new
Braunschweig area and mission parameters. Parts 2 and 3 remain deferred.
User subsequently authorized GitHub objects, pushes and merges. Milestone #5 and
Issue #37 track Part 1; the issue preceded the feature branch. The earlier draft
and source assessments are retained as planning history.

- Civil research scenario; EPSG:4326 bounds west 10.50, south 52.25,
  east 10.545, north 52.277 (below the existing 25 km² limit).
- Exact demonstration endpoints: [10.505, 52.254] and [10.54, 52.273].
- Fixed 60 m AGL; 2026-10-01 10:00–10:15 Europe/Berlin (+02:00).
- GHS-POP R2023A, 2020 estimate, native 100 m Mollweide cells; population
  counts remain separate from OSM tag scores.
- DIPUL WFS 2.0.0 bounded GeoJSON snapshots, source IDs and original properties.
  Temporary restrictions and mission-time applicability remain unverified.
- LGLN DGM1 terrain, 1 m, ETRS89/UTM32, metres NHN in DHHN2016.
  Unknown elevation must yield unknown aircraft altitude.
- Preserve original payloads and SHA-256, capture source metadata/requests,
  validate before saving the final experiment manifest, and reload offline.
- Independent population/zones inspection and location-based height inspection
  alongside existing OSM. No routing, grid, constraint evaluation or SORA.
- Preserve the existing tiny datasets. New bounded OSM acquisition is authorized
  for this newly confirmed experiment only.

Implementation sequence: independent core/storage and bounded adapters; CLI/API;
map controls and inspectors; offline fixtures and regression checks; real local
acquisition and recorded validation. Keep native data out of Git.

Acceptance: aligned bounds/CRS; native population support and NoData distinct
from zero; source identities and unmodified attributes; checked height arithmetic;
repeatable verified reload; existing OSM regression tests passing. Record source
contradictions and unresolved coverage explicitly before considering Part 2.

The GHSL distribution is a fixed archive tile larger than the experiment area.
Retain that original archive for provenance; read only the bounded native-pixel
window for the experiment. The 25 km² cap applies to the experiment/query area,
not the publisher's indivisible archive footprint.
