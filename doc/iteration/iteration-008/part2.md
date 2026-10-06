# Iteration 008 Part 2 — Fixed-altitude constraints and GHSL inspection

Date: 2026-10-06 (Europe/Berlin).
Tracking: Milestone 7 / [Issue #69](https://github.com/Hunter3304/uas-mission-planner/issues/69).
Branch: `feature/69-regional-constraints`, created from `iteration/008` after issue creation.
Scope: Part 2 implementation authorized by the user; Parts 3–5 remain deferred.
Status: implemented and validated locally, including full-region native terrain
and offline real-source verification. User authorized final review and feature ->
iteration/008 -> main publication/integration on 2026-10-06, gated by successful CI.

## Implemented behavior

- Regional source verification and indexed shared point/full-motion/polyline/
  endpoint-connector checks at 100–120 m AGL, with common safety buffers and
  exact endpoint preservation.
- Explicit offset-aware scenario dates and civil/BOS parameters, with no inferred
  exemptions or reuse of historical Braunschweig dates. The dated example is an
  engineering inspection scenario, not a flight schedule.
- Building-height/vertical-clearance obstacles, explicit missing-height policies,
  source IDs for invalid/collection/non-polygon geometries and no silent repair.
  Non-building geometry errors do not automatically introduce legal restrictions.
- DIPUL conditional/unresolved categories, m/ft and AGL diagnostics, compatible
  bounded-terrain requirements for MSL, and evidence-backed prohibitions or
  conditional allowances scoped to exact source signatures and full scenario
  applicability. No such legal assessments ship in the default scenario.
- Separate native DGM1 snapshot acquisition using bounded 2 km requests, one to
  three workers, immutable original bytes, metadata/request/checksum receipts,
  explicit verified resume and complete-marker gating. NHN is not silently MSL.
- Conservative native terrain minimum/maximum over whole motion bounding windows;
  missing tiles, NoData and pixel limits remain unknown in both strict/research.
- Existing building-only `RiskModel` reuse with 0.9/0.1 weights, max-overlap policy,
  unassessed background and unsupported-building provenance retained. GHSL never
  changes the cost or becomes a no-go layer.
- Native GHSL region/corridor/crossed-cell queries with area-weighted estimates,
  observed partial totals, explicit zeros/missing support, optional native cell
  GeoJSON and standalone SVG preview.
- CLI `terrain-fetch`, `study-prepare`, `study-check`, `study-population`; read-only
  study/population API. Source study remains separate from route-ready experiments.

Rules: [regional constraints](../../rules/regional-constraints.md).
Operations: [Part 2 guide](../../experiments/iteration-008/README.md#part-2-regional-constraints-and-native-population-inspection).
Offline real-evidence runner: `doc/experiments/iteration-008/verify-part2.py`.

## Validation

- Complete backend regression: **208 passed, one existing Windows permission skip**
  (55.77 s). The 21 new tests additionally passed after final bounded-dimension
  and native tile-boundary checks.
- Ruff lint and format checks pass. Frontend ESLint and production build pass;
  no frontend source changed. Existing dependency deprecation warnings are non-failing.
- Browser-rendered native population SVG was inspected using installed Chrome;
  no browser package or runtime dependency installed.
- New tests cover hand-computed native population fractions, known zero vs NoData,
  line totals vs area estimates, outside support, SVG semantics, API errors,
  full-motion building crossings with clear endpoints, horizontal clearance,
  altitude thresholds, soft/hard separation, invalid-building refusal, scoped
  source/permission evidence, terrain peaks away from endpoints, seam points,
  terrain checksum mutation, query budgets and interrupted/resumed acquisition.
- The original 70-file study is retained unchanged and verified before preparation.
  Original source datasets, native terrain and caches remain local and excluded
  from Git.

## Real data findings

Initial offline preparation with only the MHH terrain probe took 34.97 s with
network calls forbidden. It retained 13 invalid geometries, 10 GeometryCollections
and 67 non-polygon building diagnostics. Only relevant building geometry affects
hard building validation; all source diagnostics remain reported.

At 100 m AGL with zero additional vertical clearance, the initial study contains
13,279 polygon buildings with reported heights below the threshold, 162,010 with
missing/uninterpretable height and one at/above the threshold. These are model
states, not legal classifications or verified roof surveys.

Native region population inspection finds 41,725 intersecting cells, 20,415 known
zeros and no missing cells. The area-weighted 2020 estimate is approximately
666,980 people under the uniform-within-cell assumption. This excludes the aligned
crop's outer margin and is distinct from the complete crop's 43,605 cells. Native
Mollweide support area is not the geodesic study-area measure. The population
preview covers the entire aligned crop, with a peak of about 258.64 people/cell.

The MHH address intersects hospital, airfield and control-zone source footprints;
the other addresses also retain applicable building/source uncertainty. No address
is silently relocated and no hospital or laboratory exemption is manufactured.
Unverified DIPUL temporary/time/scenario coverage still prevents strict permission,
even when complete terrain is present.

## Native acquisition and remaining interpretation

The MHH native one-kilometre probe completed successfully. Full-region acquisition
uses 120 native two-kilometre tiles. A transient server 502 interrupted the first
run after 86 verified tiles; explicit resume reused them with two workers rather
than reacquiring verified sources. Final full-region results are recorded below
after offline verification.

Part 2 does not make unresolved sources flight-ready. Long complete-motion terrain
queries can honestly report resource limits; Part 3 must handle route subdivision,
grid size and caches explicitly. Algorithm/CLI/API routing integration belongs to
Part 3; endpoint selectors and regional map controls belong to Part 4; flight
experiments belong to Part 5. No commit, push, PR or merge is included in this
local implementation request. Issue #69 stays open until the project delivery
workflow closes it.

## Final full-region verification

All **120/120 native terrain tiles** completed and were verified offline, totaling
**1,314,968,709 original TIFF bytes**. The catalog's grid footprints cover the
complete study region. Both metadata documents and every tile checksum/request
footprint were checked; native DGM1 bytes, resolution and datum remain unchanged.

The evidence runner forbade HTTP access and completed 100 m and 120 m scenarios
in **37.66 s** and **37.59 s** respectively, including region statistics, all eight
addresses and three representative motions/corridors. Every address and motion
had known complete terrain support. All eight addresses and all three motions
remained `unresolved` in strict/research due to retained building/source uncertainty;
no searched route or flight permission is claimed.

Reported `way/590712193` height is **282 m**, so its fixed-AGL footprint remains
blocked at both 100 m and 120 m. The count of height-unresolved polygon buildings
is unchanged at 162,010. DIPUL includes 320 conditional-reference zone records and
four records whose applicability category remains unresolved; zero operator/
scenario approval assessments were supplied.

The 100 m-wide straight inspection corridors yield approximately 987.81 people
for rheuma-podbi → mhh, 2,129.53 for amedes-georg → mhh and 2,470.56 for
limbach-lehrte → mhh, under uniform-within-native-cell area weighting. These are
population-inspection estimates along supplied straight lines, not flight-risk
costs, route results or counts of people exposed to a flight. They do not depend
on changing altitude between these two scenarios.

Machine-readable [evidence summary](part2-evidence.json) preserves source/terrain/
model signatures, counts, endpoint/motion states, native ground bounds and population
queries. The complete local diagnostic report is `.cache/hannover-part2-final-evidence.json`;
its SHA-256 is recorded in the summary. The preview is
`.cache/hannover-part2-population.svg`, with browser-inspected PNG alongside it.
Reproduction commands are in the operating guide. No source data was added to Git.

## Final integration review

Review found and fixed native GHSL edge queries: a point or line exactly on a cell
edge now includes both neighbouring cells, including any NoData support. Added a
hand-checkable boundary regression. Polygon/corridor estimates discard zero-area
touches and retain their previously recorded values. Final review validation has
22 Part 2 regression cases; earlier 21-case/208-pass records remain historical.
Final reviewed backend regression: **209 passed / one existing Windows permission
skip** (63.38 s); Ruff lint/format checks passed.
The user authorized commit, push and both PR merges after successful CI. Parts 3–5
remain deferred; the iteration is not complete after this Part 2 delivery.
