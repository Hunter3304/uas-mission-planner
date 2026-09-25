# Iteration 001 feedback

## Scope delivered locally

Specify a small geographic area, acquire OpenStreetMap features, save a GeoPackage dataset and JSON manifest, and reload it without network access. Dependencies for the future React frontend are installed and locked; the UI and HTTP endpoints are outside this iteration.

## Validation evidence

- Python 3.13.13 on Windows; Node.js 24.14.1 and npm 11.11.0.
- 20 offline tests passed. Ruff lint and formatting checks pass.
- Installed frontend dependencies resolve successfully; npm reported zero vulnerabilities at installation time. This is not an application security audit.
- Real OSM acquisition for west=10.519, south=52.269, east=10.521, north=52.271 in Braunschweig.
- Query area: approximately 0.03038 km².
- Downloaded 91 features: 49 Points, 27 LineStrings, 15 Polygons.
- Saved and reloaded with EPSG:4326, matching counts and verified SHA-256.
- GeoPackage SHA-256: `4110326e65d343a3539ec714527b40cc46f07b8a092a52b1991a5a642235de69`.
- The initial live response was cached; the successful end-to-end retry reused that actual response after a compatibility fix. No synthetic data was substituted for the live result.
- Synthetic round-trip tests additionally verify tag values, identity, and geometric equality; CLI inspection tests explicitly forbid HTTP requests.
- Generated files remain local under `data/braunschweig-demo/` and are excluded from Git.

## Findings and decisions

1. Current OSMnx returns index names `element/id`, while the initial fixture used `element_type/osmid`. The live test found this mismatch, the adapter now normalizes both known schemas, and regression tests cover both.
2. OSM tags can contain lists and missing values. A JSON tag column inside GeoPackage preserves JSON-compatible values and avoids lossy automatic string conversion. Reload expands the original tag columns; missing values normalize to null.
3. Complete source features can extend outside the query box. This is documented rather than silently clipping geometries.
4. A saved manifest and checksum make offline reuse verifiable. Existing output directories are rejected to protect previous experiment data.
5. GitHub connector access and CLI authentication are separate. The user authorized the newly installed CLI, enabling repository and Milestone creation.

## Known limitations

- Acquisition is limited to 25 km², coordinate spans of one degree, and non-polar/non-dateline-crossing bounds.
- Public service backoff can exceed the 60-second individual request timeout. There is no total job deadline or background task queue yet.
- Invalid source geometries are counted and retained. The pipeline does not yet repair them or evaluate semantic completeness.
- A partial directory can remain after a failed write; without a manifest it will not load as a successful dataset.
- Cache operation times are not source edit dates. Preserve dataset files for repeatable research.
- No map UI, FastAPI endpoints, risk model, population layer, or path planner is delivered in this iteration.

## Process

Issues #1-#4 belong to Milestone 1. Feature PRs target `iteration/001`; the complete sprint is submitted separately to `main`. Remote CI and final merge outcomes will be recorded after verification.

## Next discussion

Choose the next sprint with the user: connect a small FastAPI interface to the core and add a React map display, or strengthen dataset quality/metadata first. Neither direction is authorized as a new sprint yet.
