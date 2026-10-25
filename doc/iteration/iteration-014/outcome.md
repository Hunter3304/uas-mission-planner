# Iteration 014 - Optional population routing outcome

Date: 2026-10-25 (Europe/Berlin).
Plan: [Iteration 014](../../plan/iteration-014.md).
Operation and reproduction: [guide](../../experiments/iteration-014/README.md).

Parts 1-3 are delivered to iteration/014 through PRs #123, #126 and #127.
Part 4 completes local integrated acceptance and resource evidence on
`feature/128-population-acceptance` / Issue #128 in Milestone 13. Part 4 remote
publication and full iteration/main integration remain separate gates. Main
remains `4ed0023`; no complete-iteration delivery to main is claimed.

## Implemented result

- Saved native 100 m GHSL counts transfer into a stable clipped 250 m UTM lattice
  by source-plane intersection area. Supported density is normalized once against
  the complete saved study's maximum and assigned ordinal classes 0-4. Exact
  fifths and this grid/reference are explicit project policies inspired by Ramke
  (2020), not universal population-count thresholds or accident probabilities.
- At equal density, a nominal threshold of 100 people per complete 100 m square
  corresponds to 625 per complete 250 m square. Actual clipped/transformed support
  uses its real area. This example does not introduce a fixed 100-person class cutoff.
- Hannover replaces the former green native-count bins with five green-to-red
  population classes and gray NoData. Legend and shared inspection distinguish
  positive lowest-class cells from zero and unknown, with density/support/reference.
- The regional distance/risk objective has a default-off `Include population`
  checkbox. Only checking it reveals `Population weight`, initially 1. Inactive
  hidden weights are omitted; finite nonnegative active weights are required.
  Zero remains inactive, with no population preparation/support requirement.
- All three planners, exact connectors and final independent checks share
  `P = sum(length_m inside each population cell × its class)`. Risk base uses
  `J = w_building B + w_distance L + w_population P`; distance base uses
  `J = L + w_population P`. B, L and P remain separate, with effective weights.
- Changing population controls cancels stale solves and clears route/ETA/export
  without replanning. Display visibility does not enable or disable route costs;
  weighting works without fetching the map population display. Success/failure,
  actual automatic arrival and exported quantities retain the same scoped identity.
- Part 4 preserves assessed endpoint population diagnostics when automatic arrival
  refreshes hard constraints. It also corrects map/inspector help that still claimed
  population could not affect routes, and adds explicit validation timing diagnostics.

See the exact [population rules](../../rules/population-costs.md) and Part reports:
[Part 1](part1.md), [Part 2](part2.md), [Part 3](part3.md), [Part 4](part4.md).

## Integrated evidence

The final backend regression passes **374 cases / one existing Windows skip**;
**68 browser tests and 14 real-backend smoke tests pass**, covering controls, colors/NoData,
shared selection, mobile, cancellation, time intervals and exports. Part 4 adds
changed-bounds/rule invalidation, two-entry cache eviction/rebuild and the automatic
endpoint/export regression. Numerical fixtures prove nominal 100-to-625 conversion,
fractional count conservation, exact bins, uncertainty and a real route-choice
threshold of population weight 0.125 in the two-corridor graph.

The sequential real campaign completes **nine successful requests** on the same
saved Hannover sources/terrain, frozen research interval, accepted exact endpoints,
250 m graph spacing and 20-second search budget. A*/Dijkstra agree on the graph
objective, all active routes independently re-score population cost, and both
native ABIT* off/on runs succeed. A* repeat costs and population references match.
The actual saved-address conservative off/on campaign separately returns
`invalid_endpoint` in both cases, with no route/cost/ETA or population preparation.
Addresses are preserved; successful research comparisons use explicit nearby
exact endpoints, not relocated catalog sites or asserted launch permission.

The 6,759 known Hannover population cells retain class counts
5322/1051/295/68/23 and identity
`79d339b9671be83654c8e6b1237b085878eccddad55258177fffcb61cdbc011e`.
Independent source-plane count conservation differs by approximately 0.000011
people. **127 original study/population/OSM/terrain files retain their hashes.**
Real Hannover has no NoData cells; gray is tested with synthetic data.

## Actual performance and practical limits

Final real map display passes on desktop and 390 px mobile. First full-study
visible load takes **30.132 s**; ten cached hide/show cycles have median
**233.807 ms**, issuing one population request and no route requests. The actual
decoded HTTP body is 5,047,456 bytes, below 5 MiB. Renderer JS heap after GC is
30.374 MiB after first population load and 31.881 MiB after ten cycles, with stable
event listeners. This measures renderer JS only, not native/canvas/GPU memory or
general long-run leak freedom. Final screenshots and original hashes are verified.

Population-only cold preparation takes **14.557 s**; ten verified cache hits take
**3.881-5.530 ms** (median 4.710 ms). In the active A* route worker, population
preparation takes 15.141 s cold / 5.510 ms cached; whole requests take
**85.019 / 69.797 s**. Full regional source/constraint preparation remains the
dominant cost. An inactive baseline takes 70.318/69.038 s in its separate worker.
These are scoped single observations, without an OS cache flush or statistical
latency claim; a warm population surface does not make full regional planning instant.

Full route-worker peaks are **1333.84-1360.77 MiB**, including full source/constraint
preparation and libraries. Population-only construction raises its worker working
set from 122.234 to 158.953 MiB; peak after display/conservation is 181.508 MiB.
The complete regional pipeline remains resource-heavy. Process high-water marks
are not incremental population allocation, and a two-request repeat does not prove
general long-run memory behavior.

All timings, per-profile accepted L/B/P/J, unsuccessful address outcomes, memory
scope and reproduction commands are in [Part 4](part4.md). Native runs are bounded
and stochastic in continuous space; they do not prove global optimality, a runtime
distribution or superiority over the different graph search space. General source
caching, arbitrary-scale performance, total browser/native/GPU memory and source
downloads are outside this change. Population remains a soft ordinal preference;
existing hard-constraint, source completeness and engineering-assumption policies
remain explicit.
