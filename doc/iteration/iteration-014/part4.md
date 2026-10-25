# Iteration 014 Part 4 - Integrated acceptance and resource evidence

Date: 2026-10-25 (Europe/Berlin). Status: implemented and locally accepted.
User authorized implementing the final Part 4 after Parts 2-3 delivery.
Tracking: assigned [Issue #128](https://github.com/Hunter3304/uas-mission-planner/issues/128)
in Milestone 13; `feature/128-population-acceptance` from `iteration/014` at
`38f1b1d`. The delivered base's Checks `40212518930` passed all three jobs.
Backend implementation/measurement base: `663f493`; the final UI additionally
corrects inspection/route-weighting explanations without changing route behavior.
Plan: [Iteration 014](../../plan/iteration-014.md).

## Review finding and correction

Automatic cruise arrival rechecks and refreshes hard-constraint endpoint reports.
That refresh replaced their already assessed population support reports. The
population objective/route were correct, but successful automatic results and
exports lost endpoint population diagnostics. A regression first reproduced
`KeyError: population`, then passed after retaining the independently assessed
population reports while refreshing interval-sensitive hard constraints.

Visual inspection also found old map/inspector explanations claiming population
could not affect routes. They now explain that displaying/inspecting a cell does
not enable weighting and point to `Include population` in route planning. The
existing inspector assertion was updated; final lint/build and all 68 browser
tests passed after the correction. No class/reference identity changed.

The strengthened integration test checks both endpoints' assessment, source IDs,
unknown IDs and zero point cost, including GeoJSON metadata. No population class,
weight, source identity, geometry or hard-constraint policy changed.

Results now expose independent candidate `final_validation_ms`; automatic requests
accumulate it over completed candidate passes and separately expose
`complete_interval_validation_ms` for completed actual-flight-interval checks.
These diagnostics are not cost terms or a complete additive request partition.

## Acceptance coverage

Paths below are relative to `backend/tests/` or `frontend/tests/`.

| Planned contract | Verification |
|---|---|
| Nominal 100 people/100 m to 625/250 m; actual clipped support | `test_population_costs.py`: uniform conversion, fractional intersections and full-study count conservation; independent real source-plane totals |
| Exact bins, adjacent floats, positive lowest class, known zero and NoData | `test_population_costs.py`: boundary/zero/unknown tests; `regional-details.spec.ts` and `population-costs.spec.ts`: five colors plus gray and inspector units |
| Fixed viewport/corridor/automatic reference | Full-study subsets, corridor retries, automatic identity/cost tests; bounded display browser cases |
| Source integrity, changed study/rule, bounded cache | Checksum-before-cache test; new changed-bounds/rule and third-study LRU eviction tests; cache remains capped at two and rebuild preserves reference |
| Length-times-class, shared edges/corners, repeated and zero-length paths | `test_population_routing.py`: hand-computed 350 score-metres, diagonals, max-adjacent boundary, unknown touches, repeated traversal and zero |
| Genuine route choice and graph agreement | Calculable two-corridor threshold 0.125, A*/Dijkstra; independent real graph objective comparison |
| Native evaluator and finite budget | Native population test, explicit budget/deadline/overflow outcomes; isolated real ABIT* off/on |
| Controls, missing support, failures and exports | API/CLI, inactive hidden/zero controls, resource limits, failed independent validation and automatic nonconvergence |
| Automatic endpoint population diagnostics | Strengthened success/export regression reproduces and fixes lost population support |
| UI opt-in, conditional input, cancellation, costs/export | Eight `population-routing.spec.ts` cases plus flight-time/selection/display regressions |
| Mobile, cached visibility and independent display | Five-color/NoData and shared-inspector browser cases; real display and renderer-heap campaign |
| Real sources, runtime and memory | Sequential isolated worker campaign; original study/population/OSM and all terrain TIFF/JSON/XML checksums before/after |

## Final local regression

- Backend: **374 passed / one existing Windows skip** (210.33 s), including
  native OMPL. The new population/automatic/cache focused set passed 36 cases
  (49.44 s). Existing dependency deprecation warnings remain.
- Frontend: final **68 browser tests passed** (56.9 s), **14 real-backend smoke
  tests passed** (45.7 s). Installed Chrome was used locally.
- Ruff lint/format, ESLint, TypeScript/Vite build and acceptance-script syntax pass.
  Regression processes overlapped each other; their elapsed times are validation
  observations, not planner benchmarks. Real resource campaigns run afterwards.

## Measurement method and reproduction

See the [operation/verification guide](../../experiments/iteration-014/README.md).
Core evidence: `.cache/iteration014-part4-core-v2/`; catalog evidence:
`.cache/iteration014-part4-catalog-v1/`; final display evidence:
`.cache/iteration014-part4-display-v2/`. Display v1 passed but exposed stale UI
explanations during image review; final images/measurements supersede it.
The initial core v1 diagnostic failed because the relative output
path changed meaning in subprocesses; resolving it before spawning corrected the
harness. It completed no route campaign and is not counted as acceptance.

Each route profile owns a new worker process. All profiles share the verified
saved study, terrain, frozen 2026-10-07 research scenario, accepted exact endpoints,
250 m graph spacing and 20-second search budget. The route endpoints explicitly
override their catalog addresses; no address is claimed to be a verified launch
or landing site. ABIT* searches continuous space and its finite-budget outcomes
are reported without a global-optimum or statistical-distribution claim.

Population cold means an empty application cache, not a flushed operating-system
filesystem cache. Repeated A* requests retain population cache but still prepare
regional constraints/sources per request. Population-preparation observations are
included in preparation and total request times. Validation timers are separately
scoped; all fields must not be summed as disjoint stages.

Windows process counters include Python/native libraries, full source preparation
and geometry. Peak working set is each process's lifetime high-water mark, not
incremental population allocation. Later repeat peaks include earlier requests.
Renderer measurements are Chrome JS heap after explicit GC plus DOM/listener
counts, excluding native browser/canvas/GPU allocations. No total-browser-memory
or general leak-proof conclusion is claimed.

## Real core results

The core campaign passed all **nine successful requests** on Windows 11 /
Python 3.13.13, including actual native OMPL. A*/Dijkstra agree on the constructed
graph under each objective. Repeated A* results retain identical accepted costs.
Every active success independently re-scores its unbuffered population footprints
and retains both endpoint population reports after automatic arrival.

| Profile | Length m | Building score-metres | Population score-metres | Objective |
|---|---:|---:|---:|---:|
| A* risk, population off (both runs) | 3715.591528 | 1202.148740 | Not evaluated | 1453.493018 |
| A* risk + population (both runs) | 3715.591528 | 1256.815787 | 1512.315622 | 3015.008983 |
| Dijkstra risk, population off | 3715.591528 | 1202.148740 | Not evaluated | 1453.493018 |
| Dijkstra risk + population | 3715.591528 | 1256.815787 | 1512.315622 | 3015.008983 |
| ABIT* risk, population off | 3873.938476 | 1112.765463 | Not evaluated | 1388.882764 |
| ABIT* risk + population | 3869.701888 | 992.420964 | 1367.117464 | 2647.266521 |
| A* distance + population | 2840.878100 | Not evaluated | 1487.690116 | 4328.568216 |

Off and on J are different objectives; their raw values cannot establish improvement
without rescoring the same route under the same weights. Part 2 includes that
separate diagnostic baseline rescore. Native runs use a different search space
and stochastic finite budget; these values establish compatibility, not superiority
or a proven continuous optimum. Synthetic tests establish the calculable route-choice effect.

| Profile | Run | Source s | Preparation s | Search s | Candidate validation ms | Interval validation ms | Total s | Peak MiB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| astar-risk-off | 1 | 55.282 | 67.794 | 0.805 | 130.738 | 267.051 | 70.318 | 1334.18 |
| astar-risk-off | 2 | 53.777 | 66.516 | 0.820 | 119.070 | 310.407 | 69.038 | 1338.23 |
| astar-risk-on | 1 | 54.470 | 82.205 | 1.116 | 143.534 | 276.852 | 85.019 | 1336.20 |
| astar-risk-on | 2 | 53.936 | 66.680 | 1.135 | 137.374 | 297.157 | 69.797 | 1360.77 |
| dijkstra-risk-off | 1 | 53.359 | 65.727 | 0.803 | 118.599 | 258.015 | 68.136 | 1334.30 |
| dijkstra-risk-on | 1 | 55.273 | 82.752 | 1.182 | 132.411 | 262.665 | 85.658 | 1335.43 |
| abitstar-risk-off | 1 | 54.402 | 58.895 | 20.030 | 100.931 | 248.362 | 80.499 | 1334.77 |
| abitstar-risk-on | 1 | 54.517 | 73.913 | 20.032 | 125.113 | 283.901 | 95.675 | 1335.11 |
| astar-distance-on | 1 | 55.718 | 79.673 | 0.528 | 110.245 | 242.421 | 81.817 | 1333.84 |

Source time is included in preparation; population preparation is also included
there. The timing columns overlap and omit some reporting work, and must not be
summed as a disjoint decomposition. Total is the external core-call wall time.
Warm means the second request in the same process, not a warm global planner cache.
Peak is process lifetime and later rows retain their earlier high-water marks.

Standalone population cold construction took **14.557 s**; ten source-verified
cache hits took **3.881-5.530 ms**, median **4.710 ms**. Spatial-index construction
took 200.735 ms; display assembly 300.274 ms and compact Python JSON serialization
84.673 ms (5,047,456 uncompressed response-body bytes). These are independent
observations, not an end-to-end HTTP/rendering latency claim.

In the active A* worker, population preparation was 15.141 s on the first request
and 5.510 ms on its cache hit. Total request time was 85.019/69.797 s; the dominant
53.9-54.5 s source preparation remains request-local. No statistical speedup or
unchanged total latency guarantee follows from these single paired observations.

The standalone worker's working set rose from 122.234 MiB to 158.953 MiB after
population construction; its peak after display and independent conservation was
181.508 MiB. Full route-worker peaks were **1333.84-1360.77 MiB** (about 1.30-1.33 GiB),
dominated by complete source/constraint preparation. This is a material resource
limit of the current regional pipeline, not the population layer's isolated cost.
No source-cache redesign or browser native/GPU memory measurement is claimed.

All 6,759 Hannover cells remain known, with class counts 5322/1051/295/68/23.
Real Hannover has no NoData cells; gray remains verified with synthetic fixtures.
Independent source-plane count conservation differs by 0.000010876 people.
The fixed population identity remains
`79d339b9671be83654c8e6b1237b085878eccddad55258177fffcb61cdbc011e`.
All **127 original files** (study/population/OSM plus 120 terrain TIFFs and four
terrain metadata files) retain their pre-campaign SHA-256 checksums.

## Saved catalog addresses and final display

The actual saved-address conservative campaign (no endpoint overrides) returns
`invalid_endpoint` with population off/on, in 54.417/55.214 s. Both runs export
empty features and null accepted costs/geometry/ETA. Neither prepares population;
the known endpoint conflict remains a hard constraint. These are deliberately
recorded unsuccessful address outcomes, separate from the nine successful nearby
exact-endpoint research requests. All 127 original hashes remain unchanged here too.

Final display v2 passed after the help correction. All 6,759 cells render with
the same five colors and shared inspector on desktop and 390 px mobile; both
final screenshots were visually inspected. First visible full-study load takes
**30.132 s** in the harness, including first page/API/preparation/transfer/render
work. It is not an isolated raster construction or pure drawing measurement.
The actual uncompressed decoded HTTP response body is **5,047,456 bytes**,
below the 5 MiB limit. Earlier Parts sometimes measured JSON re-serialized after
browser parsing; these representations have different byte lengths.

Ten cached hide/show cycles take **219.245-278.527 ms**, median **233.807 ms**.
Exactly one population display request and zero route requests are issued across
the initial view and ten cycles. Source hashes match, no browser exceptions or
horizontal mobile overflow occur, and owned verification services are stopped.

| Chrome renderer metric | Before population | First population | After ten cycles |
|---|---:|---:|---:|
| JS heap after GC, MiB | 10.866 | 30.374 | 31.881 |
| DOM nodes | 1178 | 1257 | 1255 |
| JS event listeners | 602 | 603 | 603 |

Retained JS heap grows 1.507 MiB (4.96%) over those ten cycles, with stable
listener count and two fewer DOM nodes. This bounded observation does not prove
long-run heap convergence, absence of leaks or total native browser/GPU memory.

## Delivery scope

Part 4 is local implementation/acceptance work. No Part 4 push, PR, remote CI or
merge is claimed. Parts 1-3 remain delivered to iteration/014; main and Milestone
13 are unchanged. Complete iteration/main integration remains a separate gate.
