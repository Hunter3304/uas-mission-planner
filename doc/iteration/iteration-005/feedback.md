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

Reproduction, source observations and checked values: [experiment guide](../../experiments/part1.md).
Implementation tracking: Issue #37, Milestone #5. Feature work was prepared locally
before GitHub authorization; the issue was created before the feature branch.

Validation results and merge facts are recorded in HANDOFF after final checks.
