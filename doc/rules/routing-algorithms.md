# Constrained shortest-path routing rules

Status: algorithm roles confirmed on 2026-09-29; Part 3 implementation authorized
on 2026-09-30. Original baseline version: `distance-grid-v1`; Iteration 006
Part 1 reports `distance-grid-v2` for configurable clearance and conservative
numerical contact checks. See [risk-weighted routing](risk-weighted-routing.md).
See the [approved scope](../plan/iteration-005.md) and
[Part 3 outcome](../iteration/iteration-005/part3.md).

## Implemented model details

Each exact endpoint connects only to its containing grid cell center; choose the
lexicographically smallest cell ID when multiple polygons contain a boundary
point. There is no additional radius, snapping or direct start-goal edge. A valid
start equal to goal yields a zero-length GeoJSON LineString with two equal
coordinates. The grid conservatively excludes entire cells intersecting synthetic
obstacles. Every allowed edge and connector, then every final segment, receives
continuous vector intersection checking in EPSG:25832. Obstacle boundary contact
is blocked. Default clearance remains 0 m. The core now supports positive metre
buffers and conservatively treats obstacle separations up to 1e-7 m as contact.

Queue ties sort by `(f, g, node ID)` and neighbors by ID. A* and Dijkstra share the
same filtered graph and weights; verification compares lengths within 1e-6 m and
path existence, not vertex sequences. Metric round-trip differences of up to
1e-6 m are tolerated in the weight/displacement consistency check.
The search expansion limit is 10,002 (10,000 cells plus exact endpoints).
Runtime measures graph filtering, search and final checks, excluding snapshot
verification and cached grid preparation. Resolution/source/mission changes
invalidate prepared graphs; endpoint changes replace connectors without
modifying the cached graph. No route cache is maintained.

Real snapshots remain globally unresolved due to temporary coverage and legal
applicability. Only explicitly marked, exclusively synthetic source experiments
use `synthetic-obstacles-v1`; their supplied zone polygons are modeled obstacles,
with no legal interpretation. Missing synthetic terrain remains unresolved.
An unresolved input yields no validated route; exported failures contain empty
features plus the explicit outcome metadata. NoData population is inspectable
and does not affect these distance-only weights.

## Scope and algorithm roles

- **A*** is the primary route-search algorithm.
- **Dijkstra** is the reference algorithm for verifying shortest-path results on
  small graphs. A second user-facing planner selector is not required.
- Both operate on the same graph, endpoints, valid edges and distance weights.
- Optimize horizontal metric length only. Flight AGL and mission time are fixed
  scenario inputs, not search dimensions. SORA is excluded from this iteration.
- GHSL population and existing OSM classification scores remain inspectable;
  neither contributes a route penalty or automatically forbids traversal.

## Graph and distance model

Use a square grid in an appropriate projected metric CRS. Default cell side
length is 50 m and is user-configurable. Represent candidate states by cell
centers, connected to up to eight neighboring centers. Resolution changes must
rebuild the graph and invalidate dependent routes. Validate positive finite
resolution and enforce a documented cell-count limit before allocation.

For valid edge `(u, v)`, use Euclidean horizontal distance in metres:

```text
w(u, v) = sqrt((x_v - x_u)^2 + (y_v - y_u)^2)
route_length = sum(w(u, v) for every route edge)
```

At spacing `s`, cardinal edges have length `s` and diagonal edges `s * sqrt(2)`.
All weights must be finite and nonnegative. Do not calculate metric distance
directly from longitude/latitude degrees.

Keep the exact selected start and goal as graph states, with validated connectors
to nearby grid states. Do not silently snap or move endpoints. The connector
neighborhood/search radius must be documented before implementation and used
identically by both algorithms. Any extra connection, including a direct
start-to-goal connection if supported, must satisfy the same validity checks.

## Constraints and validity

Prepare constraints separately from route cost. Interpret applicable DIPUL
attributes under the agreed scenario, height and mission interval; the presence
of a zone alone does not establish a universal prohibition.

- Retain permitted, blocked and unresolved states with reasons and provenance.
- Exclude forbidden states and edges, rather than assigning a large finite cost.
- Validate the full segment of every candidate edge and endpoint connector
  against vector constraints; checking endpoints alone is insufficient.
- Disallow diagonal corner cutting: both adjacent cardinal neighbor states must
  be traversable, and the diagonal segment must also pass the vector checks.
- Treat contact with a blocked boundary as blocked in this baseline. Document any
  numerical geometry tolerance; it must not silently introduce a clearance buffer.
- Missing coverage, elevation or rule interpretation must not silently mean free
  space. Resolve the unknown-data policy before implementation, using either
  explicit unresolved results or a documented conservative blocking policy.
- Validate the final route again using the same constraint model.

These checks establish validity only against modeled constraints. They do not
establish executable terrain following, obstacle-height clearance or flight
authorization. Constant AGL may imply varying altitude above sea level.

## A* search

Use accumulated distance `g(n)` and the straight-line distance to the exact goal:

```text
h(n) = Euclidean_distance(n, goal)
f(n) = g(n) + h(n)
```

This heuristic is admissible and consistent for the stated Euclidean edge costs,
including endpoint connectors. Do not multiply it by a factor greater than one
while claiming the same shortest-path guarantee.

Initialize the start with `g = 0` and other distances with infinity. Repeatedly
pop the lowest-priority current entry, skip stale entries, and relax its valid
neighbors. On improvement, update the best distance and predecessor and enqueue
the new priority. Finish when the goal is popped with its current best distance,
not when it is first discovered. Reconstruct the path through predecessors.
An exhausted queue means no path exists on this constructed graph.

Use stable neighbor ordering and a deterministic queue tie-breaker for repeatable
results. Equally short alternative paths remain mathematically valid.

## Dijkstra verification

Use the same relaxation procedure with priority `g(n)` only, equivalent to
setting `h(n) = 0`. Keep the graph and edge weights identical to A*.

Compare path existence and total length, not exact vertex sequences: equal-cost
routes may differ. Use a documented floating-point comparison tolerance.
Dijkstra alone cannot detect a shared graph or collision-checking error, so
include independently hand-checkable geometry and distance fixtures.

## Results and acceptance

Distinguish successful route, invalid endpoint, unresolved input, no path on this
grid, and computational failure/resource limit. Never report a resource limit
as proof that no route exists. A valid start equal to the goal returns zero
length; invalid or unresolved input still follows the same validation policy.

Return exact endpoints, route geometry, horizontal length, algorithm/rules version,
grid configuration, mission parameters, source versions and constraint assumptions.
Report runtime separately from route quality.

Required verification cases:

1. Empty-grid cardinal/diagonal routes with hand-calculated distances.
2. A forced detour and a fully disconnected graph, compared with Dijkstra.
3. A thin forbidden polygon crossing an edge whose endpoints are free.
4. Diagonal corner cutting and blocked-boundary contact.
5. Exact endpoint connectors, invalid endpoints and start equal to goal.
6. Missing/unresolved inputs, changed grid resolution and resource limits.
7. Equal-cost alternatives and repeatable runs.

The guarantee is shortest distance on the constructed graph. A coarse-grid
failure does not prove no continuous-space route exists. Continuous-space exact
optimality, smoothing, population-weighted routing, energy/time optimization and
dynamic replanning are outside this baseline.

## References

- [NetworkX A* documentation](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.shortest_paths.astar.astar_path.html)
- [NetworkX Dijkstra documentation](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.shortest_paths.weighted.dijkstra_path.html)

These references explain algorithm behavior; they do not select a runtime
library or add a dependency to the project.
