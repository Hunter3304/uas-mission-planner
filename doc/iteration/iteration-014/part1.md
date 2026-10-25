# Iteration 014 Part 1 - Population aggregation, classes and colored grid

Date: 2026-10-25 (Europe/Berlin). Status: implemented and locally accepted.
Plan: [Iteration 014](../../plan/iteration-014.md).
Rules: [Population classes](../../rules/population-costs.md).

The user authorized Part 1 and brought forward its map visualization. They then
explicitly requested removal of the old green population-count display in favour
of five risk colors from green to red, with gray NoData. This replaces that
Hannover control; native APIs/CLI and the small-area experiment page retain their
original population inspection contracts. No route objective has changed.

## Delivered behavior

- Fixed 250 m EPSG:25832 lattice over the complete study, clipped at its boundary.
  Actual native raster intersections transfer fractional counts without resampling.
  Density uses actual native support area; complete versus partial/unknown support
  remains explicit. A nominal 100-person 100 m cell corresponds to 625 people
  over a full 250 m square at the same density.
- Separate `ramke-population-250m-v1` classification, using the full-study maximum
  and exact lower-inclusive fifths of [0,1], mapped to ordinal classes 0-4. Known
  zero, positive lowest-class values, all-zero studies and unknown support differ.
  The exact boundaries are project policy, distinguished from paper evidence.
- Population-specific checksums/metadata verification, bounded two-surface cache,
  native-window/target-cell/deadline limits and source checks even on cache hits.
  The endpoint avoids loading unrelated OSM/DIPUL/terrain. A geographic index
  filters views without recalibrating the reference; bounded display payloads
  share bin definitions instead of repeating them in every feature.
- New `/study/population-costs` GET with optional geographic bbox, fixed model
  identity/reference, class/support counts, copied metadata and bounded GeoJSON.
  One preparation at a time, explicit retry/resource-limit outcomes, no originals
  rewritten. `routing_cost` remains false until Part 2.
- Hannover `GHSL — population risk (250 m)` replaces the former native green
  bins. Five numbered colors and gray/dashed NoData, density/people/threshold
  inspector and provenance use the existing shared selection system. The legend
  explains that class 0 can contain people and population is inspection only.
- Cached visibility/folding preserves loaded data. Slow initial preparation
  survives hide/show. Initial map positioning cannot trigger a second request;
  incomplete viewport requests queue behind current preparation and reuse a
  bounded two-response cache. Failures require explicit retry, without a loop.

## Validation

- Backend suite: **350 passed, one existing skip**, 122.52 s. Twelve new numerical/
  API tests cover count conservation, actual clipped areas, 100-to-625, neighbouring
  floats at bin boundaries, zero/unknown/invalid data, subsets, checksum changes,
  cache copies, cancellation and resource limits. After display compaction/index/
  metadata-size changes, focused final checks: **12 passed**, 1.92 s.
- Final Chrome browser suite: **60 passed**, 40.6 s, including existing regional
  selection/controls/arrival flows and new retry, slow preparation, hidden loading,
  cached toggles, bounded views, five colors/NoData and mobile checks.
- Real-backend browser smoke suite: **14 passed**, 33.6 s. Existing small-area
  population, route and native-ABIT* contracts remain usable.
- Ruff/format, frontend ESLint/build, experiment syntax and diff whitespace pass.
  Synthetic six-cell desktop/mobile screenshots were inspected. No screenshot
  represents synthetic population as Hannover data.

Run `node doc/experiments/iteration-014/verify-part1.mjs` with local dependencies
installed for isolated real Hannover browser acceptance. It owns ports 8014/5186,
refuses occupied endpoints, disables only street tiles, verifies the real API,
saves evidence under `.cache/iteration014-real/`, checks original hashes and stops
its own services. Existing user services are not stopped or reused.

Real Hannover acceptance passed with no browser errors:

| Measurement | Result |
|---|---:|
| 250 m cells / complete support | 6,759 / 6,759 |
| Classes 0 / 1 / 2 / 3 / 4 | 5,322 / 1,051 / 295 / 68 / 23 |
| Maximum aggregated density | 16,093.510965584372 people/km2 |
| First browser load to visible grid | 28,673.2792 ms |
| Compact JSON response | 4,978,703 bytes |
| Ten visibility cycles | One total population request |
| Route requests during population inspection | Zero |

Initial core-only measurement, separate from browser rendering: 12.4305 s cold
preparation and 0.00433 s verified warm retrieval. Compact display creation measured
0.2558 s separately. These are local observations, not latency guarantees or total
application startup times; existing source/UI preparation and render costs remain.
No quantitative peak-memory reduction is claimed.

Independent native-cell query over the same densified metric study boundary gives
666,834.5744527713 people; the aggregate gives 666,834.5744418947. The difference
is approximately -0.00001088 people. This compares the same area convention;
historical queries using different boundary transformations need not have the same
total. No rounding is applied before classification.

Original `study.json` and `population.tif` SHA-256 values match before and after
real acceptance. Model identity:
`79d339b9671be83654c8e6b1237b085878eccddad55258177fffcb61cdbc011e`.
Real desktop/mobile screenshots were visually inspected. Hannover has no NoData
cells; gray rendering is covered separately by synthetic browser/numerical tests.

## Delivery state and remaining Parts

Publication explicitly authorized on 2026-10-25 before Part 2. The earlier
credential limitation below is historical: verified local credentials are
available outside the sandbox. Milestone 13, remote `iteration/014` at `d0782d3`
and assigned Issue #122 now exist. Feature renamed to
`feature/122-population-surface`. Part 1 was then pushed as `e7459c6`, and PR #123
passed exact-head Linux/Windows/frontend Checks run `40189193801`. The user
subsequently explicitly approved integration into iteration/014, superseding
the earlier automatic approval block. PR #123 merged at
`d3b01542252b7fdf66d2cabc722e0a66e20c3de5`; Issue #122 was explicitly closed
as completed. Local iteration/014 is synchronized, and the merged tree equals
the accepted Part 1 tree. Main remains unchanged. The user explicitly approved
branch cleanup after the earlier automatic deletion block. The merged feature
was deleted remotely with an exact-head lease and locally; fetch/prune, local
ref checks and ls-remote verified cleanup. See [Part 2 status](part2.md).

Historical pre-publication record (superseded above): local branch
`feature/iteration014-population-surface`, from new local
`iteration/014` at Iteration 013 head `d0782d3`. The GitHub connector does not
support milestone creation and no local GitHub credential was available to the
fallback. Therefore no remote milestone, assigned issue, PR, push, remote CI or
merge is claimed. Remote tracking/publication workflow remains to be completed
before a published delivery. Iteration 013/main integration state is unchanged.

Part 2 adds shared population route evaluation/objective; Part 3 adds the routing
checkbox and conditional weight input; Part 4 completes combined-route acceptance.
The classification/grid portion of Part 3 was explicitly brought into Part 1.
Current routes still use their existing distance/building objectives and constraints.
