# Iteration 002 feedback

## Delivered

- Read-only FastAPI dataset listing, integrity-checked statistics, GeoJSON features, and three download formats.
- React/Leaflet explorer with four layer switches, unique visible counts, query boundary, feature search and tag inspection, and responsive layout.
- Explicit empty, unavailable, corrupted-data, and basemap-failure states.
- Separate frontend/backend processes, with the reusable Python core independent of both UI and API.

## Validation

- Real Braunschweig dataset displayed: 91 objects (49 points, 27 lines, 15 polygons). Buildings: 9; roads/paths: 29; land use: 2; natural: 51.
- Real browser smoke check: layer switching, object selection, GeoJSON download, and a 390-pixel mobile viewport without horizontal overflow.
- Six automated browser tests cover overlapping layer counts, vector removal, safe tag rendering, downloads, mobile layout, empty/missing/corrupt data, retry, and unavailable basemap.
- API tests verify download bytes, storage corruption, malformed metadata, dataset identifiers, empty datasets, and filesystem containment.
- CI runs Python lint/format/tests on Windows and Linux; frontend lint, production build, and Chromium tests run on Linux.

## Lessons and limitations

Layer counts overlap, so summing them is not a unique feature total. Display and exports explicitly distinguish visibility from the full dataset. Metadata needed for rendering is validated before exposing a dataset. Live tiles are optional and are excluded from automated tests.

The prototype reads all data into memory and revalidates each API request; this is appropriate for the current small-area demonstration. Larger datasets will need a separately planned performance iteration. Acquisition remains in the CLI. No new sprint is approved.

## Delivery records

Milestone: Iteration 002 (#2). Implementation issues: #14, #15, #16. API PR #17 and explorer PR #18 merged into iteration/002; their feature branches were removed locally and remotely. Final integration evidence is recorded in HANDOFF.md.
