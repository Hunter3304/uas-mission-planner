# Regional fused risk routing

Implemented rule: `ramke-fused-risk-150m-v1` (Iteration 015).
Regional `objective=risk` directly replaces the former building-only objective.
There is no additional paper objective. Small-area building-risk experiments
and regional distance/distance-plus-population retain their separate contracts.

## Formula and paper basis

Ramke (2020), *Development of advanced informed planning techniques for BVLOS
UAS operations*, printed pp. 38-39 (PDF pp. 50-51), specifies equal weights for
building/landuse/highway within OSM and half each for OSM/population. Printed
p. 41 (PDF p. 53) specifies 0.9 custom risk and 0.1 path length. Printed pp.
45-46 selects ABIT following planner comparisons. The implementation uses the
project's existing native OMPL ABIT*, with A*/Dijkstra as graph alternatives.

```text
C_osm = (C_building + C_landuse + C_highway) / 3
C_fused = C_osm / 2 + C_population / 2
F = sum(centreline length inside each fused cell * C_fused)
J = 0.9 * F + 0.1 * horizontal length
  = 0.15 B + 0.15 LU + 0.15 H + 0.45 P + 0.1 L
```

B/LU/H/P are separate score-metres on the same 150 m cost grid. F is fused
score-metres, exposed as `fused_risk_length_cost` and the compatibility field
`risk_length_cost`. That compatibility field no longer means building-only risk
for regional requests. Physical `length_m` remains metres. A 100 m path with
scores 4/2/0/3 has B/LU/H/P=400/200/0/300, F=250 and J=235.

Weights are fixed. Risk always includes population; old optional population or
adjustable coefficient arguments cannot add it again or change the weights.
Returned `effective_weights` is authoritative. Distance uses L, or L+wP with
explicitly enabled positive population weight, using the existing 250 m classes.

## Common grid and population

Use EPSG:25832 and a full-study 150 m lattice, snapped down from the complete
study boundary minima. Clip boundary cells. Directly transfer retained native
100 m GHSL counts by native-plane intersected area, compute density using actual
known area and normalize against one complete-study maximum. Classify exact
fifths of [0,1] into 0-4, retaining the known-zero/NoData distinction. This has
its own `ramke-population-150m-v1` identity and stable `population150:row:col` IDs.
The 250 m display product and its default identities are unchanged.

Route graph spacing, corridor expansion and viewport do not change cost grid
resolution or its normalization reference. A*/Dijkstra still default to 250 m
search spacing; native ABIT* uses continuous metric states. Population is census-
derived residential estimation, not real-time presence or accident probability.

## Explicit spatial and missing-data conventions

The paper does not fully specify all rasterization details; these are project
policies rather than claims about the original implementation:

- Reuse the existing building, landuse, highway and natural tag tables. Within
  a category and cell, take the highest intersecting numeric class. Duplicate
  objects do not add risk again. Provisional classifications remain flagged.
- Polygon overlap must have positive area; line overlap must have positive
  length. Highway lines therefore mark their intersected cost cells without
  inventing road widths. A point marks its containing cell, with the smallest
  stable cell ID breaking a boundary tie.
- Natural is a cell-level landuse fallback when no numeric landuse value exists.
  It is not a fourth weighted OSM category; partial-cell blending is not performed.
- Missing category scores use `background_cost`, default 0 at the user's request.
  This is an explicit assumption, recorded in provenance and assessment flags.
  It does not establish observed zero risk. The paper's p. 44 discussion of
  medium uncertainty scores is not adopted as the requested default.
- Obstruction-only historical classifications have no invented numeric score
  and create no automatic legal prohibition. Other numeric support or the explicit
  OSM background determines soft cost. Hard constraints remain separate.
- Derived building polygons follow the selected scenario's existing geometry
  policy. Uncertain building extents remain excluded by hard checks. Invalid
  non-building cost geometry makes intersecting envelope cells unresolved; an
  empty/unlocalizable relevant extent prevents preparation. No silent repair.
- Unknown population cells cannot be filled by OSM background or research mode.
  Any unknown cell contact, including an endpoint/corner, is unresolved.

Partition the complete centreline, including exact endpoint connectors and
repeated traversals. On a shared boundary choose the higher fused cell score
and stable-ID ties; all component totals come from that same selected cell.
Never maximize components independently on a boundary and then claim their
sum equals the fused score. A 1e-7 m cell expansion handles numerical contact;
it is not a flight corridor. Positive safety distance affects hard checks only.

## Validation and resource behavior

A*/Dijkstra, native motion costs and final validation use the same model. A*
uses 0.1 times Euclidean distance as a nonnegative-cost lower bound. Graph
optimality is limited to the constructed graph; finite-budget ABIT* does not
prove continuous global optimality. Exact endpoints and every full segment
still pass the existing constraint engine, with complete-interval reassessment
for automatic arrival. Research is the regional UI/CLI default; core/API retain
strict when a caller omits the policy. Known obstacles and missing terrain cannot
be bypassed by the objective or research mode.

Independently recompute physical length, all four component totals, F and J
before accepting a regional route. Export all quantities and the rule/source
identities. Failures have no accepted route features, component totals or ETA.

Source verification runs on every request. Reuse at most two immutable fused
surfaces keyed by OSM checksum, population identity, classification/fusion rules,
background and geometry policy. Populate from verified saved sources only.
Population and fusion preparation respect the shared request deadline; graph
search/cost preparation and native search retain their budgets. Return a
resource finding rather than silently changing resolution or normalization.
Regional requests have a user-authorized 300 s total deadline; the browser waits
310 s including response grace. Other API calls retain 120 s browser timeouts.
ABIT* search budget remains independent (default 3 s). Native pixel intersection
batching in the 150 m preparer preserves the same count-transfer calculation;
the existing 250 m preparation and identity remain unchanged.

This reproduces the documented fusion hierarchy using modern data and explicit
spatial conventions. It does not claim byte-for-byte reproduction of the author's
code, older GHSL data, figure thresholds or historical route results.
