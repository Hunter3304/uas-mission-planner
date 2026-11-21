# Iteration 017 — Weighted outdoor pedestrian exposure routing

Approved for implementation on 20 November 2026. Baseline main at fab46ce.
Iteration 016 delivered the seven Hannover–Lehrte pedestrian exposure windows
and an A* route planner that scores the entire route against the Berlin
departure window. The existing regional planner already supports A*, Dijkstra
and native OMPL ABIT* for its other objectives.
[Iteration 016 routing outcome](../iteration/iteration-016/phase-2.md)

## Routing and page defaults

- Prefer the saved dataset **hannover-part1-v4** when opening the website. If it
  is absent from the local catalog, open the first available saved dataset.
  Keep the user's current selection when refreshing a catalog that still
  contains it.
- Open the Hannover route panel in **Outdoor pedestrian exposure** mode and
  default the algorithm selector to **ABIT\***. Offer **A\*** and **Dijkstra**
  in the same selector. Keep **Existing planning** available for distance
  and fused-risk routing.
- Connect the pedestrian objective to the existing graph search for A* and
  Dijkstra and to the existing native continuous-space ABIT* planner. Use the
  same exposure data, cost definition, exact endpoints and regional feasibility
  checks across all three. Recheck the full path, score and assessed flight
  interval before reporting a successful route.
- Use the existing supported Windows x64 OMPL setup for native verification.
  If the runtime cannot load ABIT*, report that the selected algorithm is
  unavailable and let the user choose A* or Dijkstra from the same panel.
- In pedestrian mode, show **Search budget (s)** when ABIT* is selected.
  Default to 30 seconds and accept a user-selected budget up to 120 seconds.
  Apply it to native search across flight-interval passes. Data preparation
  and final validation also contribute to the total request time.

## Origin and destination

Reuse the **Selection method** control from **Existing planning** in
**Outdoor pedestrian exposure** mode. Default to **Choose from saved sites**.

- **Choose from saved sites** offers all eight saved Hannover–Lehrte sites
  in both the origin and destination dropdowns.
- **Enter exact coordinates** accepts a longitude and latitude for each
  endpoint in WGS84 decimal degrees. Show the study bounds and validate each
  coordinate using the existing rules. The planner uses the entered
  coordinates as the route endpoints at their full input precision.

Support both selection methods with A*, Dijkstra and ABIT*. Use the selected
points consistently for map markers, scenario preview, route search, flight
interval assessment and GeoJSON export. Apply the same feasibility and
exposure coverage checks to saved and manually entered endpoints. Clear the
displayed result when the selection method or an endpoint changes.

## Distance and exposure weights

Add two numeric inputs in **Outdoor pedestrian exposure** mode. **Distance
weight** defaults to **0.1** and **Exposure weight** defaults to **0.9**.
Use the same defaults for pedestrian route requests that omit either weight.
Validate the inputs in the browser and the planner. Accept finite,
nonnegative values with at least one positive weight. Apply the values
directly without normalization.

Use the Iteration 016 definitions of horizontal route length and integrated
pedestrian exposure. For length l_g in an assessed cell g, use the modelled
pedestrian density rho_g from the selected departure window and the reference
density rho_ref of 100 people/km².

~~~text
L = sum_g(l_g)
E = sum_g(l_g * rho_g / rho_ref)
J = distance_weight * L + exposure_weight * E
J_default = 0.1 * L + 0.9 * E
~~~

The search and independent score must use the same weights. Use
distance_weight multiplied by straight-line distance as the lower bound for
A* and ABIT*. Dijkstra uses a zero heuristic. Preserve the pedestrian mode's
assessed-coverage requirement for every weight combination, including zero
exposure weight. Report L, E, J, both effective weights, the departure window
and the exposure model version or identity in the route result and GeoJSON
export. A weight edit invalidates the displayed route until a new result is
available. Scope the new inputs and objective to pedestrian routing.

## Map panels

Place **Outdoor pedestrians** and **DIPUL restrictions** side by side in equal
columns where space permits. Stack them on narrow screens, with **Outdoor
pedestrians** first. Keep **OSM** full-width above that pair and retain each
panel's separate collapse control.

## Acceptance

- Open the page with a catalog containing Hannover and another dataset. Verify
  the Hannover dataset, pedestrian mode, ABIT* and weights 0.1 and 0.9 on
  first load. Verify the catalog fallback when Hannover is absent, switching
  between routing modes, and the missing-OMPL path.
- Verify the default 30-second native search budget, a custom 120-second
  request, and rejection of values above 120 seconds by the planner.
- In pedestrian mode, verify that each saved-site dropdown lists all eight
  locations. Switch to exact coordinates and verify that the map markers,
  planner request, successful route geometry and GeoJSON use the entered
  points. Verify that an out-of-bounds entry is rejected and that switching
  back to saved sites clears the previous result. Exercise manually entered
  endpoints with all three algorithms.
- Check that custom weights reach the planner and that results and GeoJSON
  contain the applied values. Independently recompute L, E and J on returned
  geometry. Use a controlled two-route case to verify that changing the
  weights can change the route choice. Cover single-zero weights, invalid
  values, missing exposure support and existing regional routing objectives.
- Run all three algorithms on the short **Rheumapraxis
  Hannover–Podbielskistraße → MHH** case and the longer **MHH → MVZ Labor
  Limbach Lehrte** case. Pin the departure timestamp, dataset, exposure layer,
  endpoints, weights, flight constraints and configured search budget per
  case. Record solve status, feasibility checks, L, E, J, preparation time,
  search time and total request time. Check matching optimal costs when A*
  and Dijkstra both finish on the same graph. Repeat ABIT* runs at the same
  settings and report success rate and the observed spread in cost and time.
- Verify the two-panel row on desktop and the stacked layout without horizontal
  overflow on mobile. Record the experiment settings and results in
  doc/iteration/iteration-017/.
