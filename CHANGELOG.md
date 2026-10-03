# Changelog

## Unreleased — Explorer panel controls

- Accessible folding controls for all six analysis/planning/inspection panels.
- Feature panels stay available and open together for any selected feature.
- Risk inputs appear only for the weighted objective, retaining previous values.
- Map and route results survive folding; real API and mobile coverage added.

## Unreleased — Iteration 006 Part 3

- Compatible CLI/API/UI planner, objective, weight, clearance, background and
  ABIT* budget controls; exact/approximate status, costs and assumptions displayed.
- UI exports the displayed snapshot without replanning; failure diagnostics and
  full provenance preserve real-data uncertainty.
- Synthetic low-risk detour and bounded four-planner comparisons with independent
  endpoint/constraint/cost checks, repeated ABIT* distributions and environment versions.
- Explicit unsupported per-task seeds; native callback cycles removed while
  retaining OMPL metric arithmetic; native CLI stdout remains JSON.
- Backend and real API/browser coverage plus reproducibility documentation.

## Unreleased — Iteration 006 Part 2

- Optional official OMPL C++ ABIT* adapter for native Windows Python 3.13,
  using a pinned patched wheel with source/build provenance and licenses.
- Independent continuous-space tasks share metric risk/geometry rules, enforce
  cooperative total planning budgets and cancellation, and return structured
  exact/approximate/timeout/unresolved/failure outcomes.
- Exact final routes preserve endpoints, recheck full constraints and recompute
  length/risk/objective. No global path files or graph_tool dependency.
- README installation and Windows native tests added; graph routing remains
  available without OMPL. New CLI/API/UI controls remain deferred to Part 3.

## Unreleased — Iteration 006 Part 1

- Metric centreline building-risk integration using existing tag classifications,
  maximum score in overlaps and explicit unassessed/background-assumption handling.
- Weighted A*/Dijkstra with separate physical length, risk-length and objective
  outputs; default risk/length weights 0.9/0.1 and offline Python entry point.
- Configurable shared point/motion clearance, conservative obstacle boundary
  contact checks, verified source/rule/config cache identity and export provenance.
- Calculation rules documented under `doc/rules/risk-weighted-routing.md`.
  Existing distance-only CLI/API/UI remain default; OMPL and new UI controls deferred.

## Unreleased — Iteration 005 Part 3

- Deterministic distance-only A* on the preparation graph, Dijkstra verification,
  exact endpoint connectors and continuous final segment validation.
- Map/coordinate endpoint selection, route length/runtime, optional unvalidated
  straight-line reference, explicit outcomes and route GeoJSON provenance export.
- Network-free synthetic obstacle demo and CLI routing/export, with conservative
  unresolved behavior retained for real restriction coverage and applicability.

## Unreleased — Iteration 005 Part 2

- Configurable metric preparation grid, native GHSL area-weighted estimates,
  explicit unknown support and zero preservation.
- Conservative DIPUL altitude diagnostics, segment intersection checks,
  horizontal candidate lengths and exact endpoint connectors.
- Grid API with verified manifest/resolution cache and browser cell/edge inspection.
- Unknown MSL terrain profiles and temporary/legal applicability remain unresolved;
  the research policy blocks unresolved traversal. Route search remains deferred.

## Unreleased — Iteration 005 Part 1

- Bounded GHSL/DIPUL/LGLN experiment acquisition, source-native storage, SHA-256
  verification, explicit interrupted-acquisition resume and offline inspection.
- Independent population and zone map layers, source attributes/provenance,
  fixed AGL plus terrain and aircraft height display, explicit unknown values.
- Matching OSM snapshot attachment and compact API reads for sparse large samples.
- Reproducible Braunschweig experiment configuration and documented real-payload
  validation, including terrain metadata exceptions and partial zone coverage.
- No grid, routing, applicability engine or SORA implementation.

## Unreleased — Iteration 004

- Independent costs for buildings, roads, land use and natural features.
- Versioned paper-based classification, explicit unknown defaults and separate obstruction flags.
- Category-specific map colors, statistics, per-tag explanations and tag search.
- Read-only analysis API; original datasets and downloads remain unchanged.
- Rule tables, methodology, offline walkthrough and regression coverage.

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
