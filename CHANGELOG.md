# Changelog

## 0.3.0 — 2026-09-25

First tagged research prototype, completing Iterations 001–003.

### Included

- Small-area OpenStreetMap acquisition, GeoPackage persistence, and verified offline reload.
- Separate FastAPI and React/Leaflet processes: four semantic layers, unique counts, feature inspection, and GeoJSON/GeoPackage/metadata downloads.
- Offline `uas-planner sample` with three fixed synthetic features and explicit provenance.
- Manifest/tag validation, clean cancellation, actionable network/invalid-response errors, and invalid-download rejection.
- Real-stack offline browser test, mocked failure regressions, Windows/Linux Python CI, and synchronized package/API versions.
- Quick start, port ownership and URL troubleshooting, limitations, and iteration feedback.

### Compatibility and limits

Dataset schema remains version 1; existing valid Iteration 001/002 datasets remain readable. Malformed manifests are rejected earlier. Synthetic samples add optional provenance fields. Fresh sample saves have new timestamps/checksums; feature content is fixed, not byte-identical across runs.

Python 3.13 and Node.js 24 are required. The prototype runs locally and reads complete small datasets into memory. Acquisition remains CLI-based. Flight risk analysis, route planning, and public hosting are not implemented.
