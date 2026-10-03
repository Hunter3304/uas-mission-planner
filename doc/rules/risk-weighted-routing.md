# Metric building-risk routing — Iteration 006 Part 1

Implemented core policy: `building-length-risk-v1`. Classification remains
`ramke-building-tags-v1`; its canonical JSON SHA-256 is recorded with results.
These are ordinal research costs, not accident probabilities.

## Coordinates and physical lengths

Source/display coordinates are EPSG:4326, always longitude then latitude.
The Braunschweig research region is evaluated in EPSG:25832 (metres).
All risk intersections, physical lengths and collision clearance use the same
projected metric CRS. Exported routes remain EPSG:4326. The model rejects a
geographic or non-metre analysis CRS.

## Classification and coverage

Reuse the existing [building table](building-costs.md) and executable
`backend/src/uas_planner/core/cost_rules.json`. Only explicit building polygon
and multipolygon features contribute numeric scores in this part. Roads,
land use, natural features and population remain separate.

- Unknown building classifications retain provisional score 2 and `has_default`.
- Invalid/missing/empty building geometry raises an explicit preparation error;
  original geometry is not silently repaired.
- A point/line building inside the analysis boundary has no inferred footprint.
  It is recorded as unsupported and leaves the model unresolved globally.
- Obstruction-only entries have no invented numeric cost. Crossing/touching their
  polygon leaves risk assessment unresolved, even with an explicit background.
- A historical paper obstruction flag is metadata, not an automatic legal ban.
  Scored school/hospital polygons remain soft costs unless the separate explicit
  scenario constraint model blocks them.
- Uncovered space is unassessed by default. A caller may explicitly supply a
  nonnegative background score for a research scenario; results record it as an
  assumption, and flag its use on the selected route. It cannot resolve unknown
  legal constraints, unsupported footprints or missing building scores.

## Length multiplied by risk

For each segment e, partition its centreline by the effective building score:

`R(e) = sum(intersected_length_m * score)`

Where polygons overlap, use the maximum numeric building score at each location.
Duplicate features do not add risk again; retain all contributing OSM identities.
The background applies only outside numeric building coverage, not underneath
buildings. Implementation queries an STRtree, then subtracts already counted
line portions in descending score order. Scores and weights must be finite and
nonnegative; at least one objective weight must be positive.

Use centreline intersection lengths, never a buffered corridor's perimeter.
Sum segment evaluations for a path, including exact endpoint connectors. This
also counts repeated traversal correctly. A zero-length route contributes zero
cost but still needs valid constraint and risk support at its point.

Default objective:

`J(e) = 0.9 * R(e) + 0.1 * length_m(e)`

Example: 100 m route, 20 m in score 4, remaining 80 m explicitly assumed score 0:
`R = 20 * 4 = 80`, `J = 0.9 * 80 + 0.1 * 100 = 82`.
Changing the weight does not normalize the inputs or express a percentage of
real-world risk. The reported risk quantity has units of score-metres.

## Graph search and outcomes

Existing distance mode remains the CLI/API/UI default. The reusable core accepts
a prepared RiskModel to enable risk weighting. Graph edges keep physical length
separate from objective weight. Weighted A* uses the admissible lower bound
`distance_weight * Euclidean_distance_to_goal`; Dijkstra uses zero heuristic.
Unassessed edges are excluded. The optimum is on the assessed constructed graph,
not a continuous-space or global optimum. A*/Dijkstra are compared using total
objective, not only physical length.

Results separately expose `length_m`, `risk_length_cost`, `objective_cost`,
`assessment_flags`, `risk_model` provenance and the existing explicit statuses.
Final segments are independently checked and risk costs recomputed. Missing
endpoint support returns `unresolved_input`; excluded unresolved edges prevent
a no-path result from being misrepresented as proven infeasibility.

## Collision checks and safety distance

`safety_distance_m` is finite and nonnegative; default 0 m preserves existing
point/centreline behavior. For positive values, buffer points and complete
segments by that distance. The entire checked geometry must stay inside the
allowed boundary. Any overlap or contact with a blocked polygon is invalid,
including partial overlap of a buffered point. Never use obstacle containment
of the whole buffered point as the collision criterion.

Circular buffers use 16 segments per quadrant with radius expanded by
`1 / cos(pi / 64)` so the polygon approximation contains the requested circular
clearance envelope instead of slightly underestimating it.

At 0 m, check the original Point/LineString directly (Point.buffer(0) is empty).
To conservatively handle projection round-trip error, obstacle separations of
at most `1e-7` m are treated as contact. Clearance does not change the risk
centreline or risk values. Unknown constraint regions intersecting the checked
geometry remain unresolved. Positive clearance is a horizontal research buffer,
not a 3D building-height model.

Distance routing now reports `distance-grid-v2` for the explicit clearance and
numerical-contact policy; risk mode reports `building-length-risk-v1`.

## Offline entry point and provenance

From a Python session in the project environment:

```python
from pathlib import Path
from uas_planner.core.experiment import load_experiment
from uas_planner.core.risk_routing import plan_risk_route
from uas_planner.core.routing import route_geojson

directory = Path("data/synthetic-route-demo")
manifest = load_experiment(directory)
result = plan_risk_route(directory, manifest, background_cost=0)
oracle = plan_risk_route(directory, manifest, background_cost=0, algorithm="dijkstra")
exported = route_geojson(result)
```

Background 0 above is an explicit synthetic research assumption. Omitting it
keeps outside-building space unassessed. `plan_risk_route` can reuse a prepared
grid from the same verified manifest; its default builds one. It performs no
new acquisition. Real Braunschweig constraint uncertainty remains unresolved.
OMPL and risk controls in API/CLI/UI are deferred to subsequent parts.

Saved OSM files are integrity-checked on every preparation call before an LRU
cache can be used. Cache/model identity includes the source GeoPackage checksum,
feature/tag payload, classification hash, risk rule version, experiment manifest,
grid, CRS, boundary, overlap/background policy, weights and safety distance.
Route exports include the same model identity and source information. Cached
model provenance is copied into results so editing a result cannot change it.

Regression evidence and remaining work are recorded in
[Part 1 feedback](../iteration/iteration-006/part1.md).

## Public controls and comparisons — Part 3

`core/planning.py` is the shared CLI/API entry point. Default `distance` uses
weights 0/1 regardless of supplied risk weights and does not require assessed
building coverage; distance ABIT* uses an empty zero-background metric model.
`risk` uses the assessed surface and supplied weights. Both preserve the same
hard constraints and clearance. Blank background is never silently zero.

Comparisons evaluate distance A*, weighted A*, weighted Dijkstra and repeated
ABIT* on identical endpoints/costs/constraints. Re-score the distance baseline
with the weighted model before comparing objectives. Independently check final
endpoints, constraints and segment costs. Grid and finite-budget continuous
optimality remain separate. Per-task native seeds are unsupported; reports
record null seeds, budgets, repeated outcomes/distributions and versions.

Exact paths and failure/approximate diagnostics retain controls and provenance.
UI exports preserve the displayed result; API GET exports describe that solve.
See [Part 3 operations and evidence](../iteration/iteration-006/part3.md).
