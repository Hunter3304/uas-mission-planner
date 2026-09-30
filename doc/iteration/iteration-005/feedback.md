# Iteration 005 — Part 1 delivery feedback

Part 1 implements repeatable local external snapshots, independent source layers
and location height inspection. Parts 2/3 remain deferred. User approved the new
9.23 km² area, experiment parameters, GitHub work and subsequent merges.

- Source-native core for raster/zone validation, NoData and height inspection.
- Explicit CLI acquisition, checksummed interrupted-download resume and offline
  reload; optional matching OSM snapshot attachment.
- Read-only API and independently toggled GHSL/DIPUL map overlays, source fields,
  provenance and unknown status; existing OSM costs/downloads retained.
- Real GHSL, DIPUL and LGLN payloads validated. The terrain WCS's incorrect unit
  and absent NoData tag are documented against the official product specification.
- Four selected DIPUL static layers only; temporary restrictions, validity and
  applicability remain unresolved. No additional source buffers are invented.
- Real-area inspection required compact OSM tag dictionaries to avoid expanding
  thousands of absent tags into the browser payload. Complete source downloads
  remain unchanged. Experiment maps fit the query area, retaining full source
  geometries without allowing distant geometry to determine the initial view.
- Initial Linux browser CI caught a Leaflet zoom callback after map teardown.
  Dataset fitting is now immediate, CSS zoom animation is disabled, map movement
  is stopped on teardown, and repeated dataset-switch coverage checks page errors.

Reproduction, source observations and checked values: [experiment guide](../../experiments/part1.md).
Implementation tracking: Issue #37, Milestone #5. Feature work was prepared locally
before GitHub authorization; the issue was created before the feature branch.
Feature PR #38 passed Windows/Linux Python and frontend CI, then merged into
`iteration/005` at `89796b130f6d31ed7efcdfa0200427fafa3b1a6d`.
Issue #37 was explicitly closed. The final local gate comprised 85 Python passes,
one Windows symlink skip, 9 mocked browser passes, 12 repeated real-stack browser
passes, Ruff, ESLint and production build. The sprint PR and main merge are the
remaining delivery steps at this point.

Validation results and merge facts are recorded in HANDOFF after final checks.
