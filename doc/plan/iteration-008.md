# Iteration 008 — Hannover fixed-altitude 2D routing

Date: 2026-10-05 (Europe/Berlin).
Status: Part 1 implemented and validated locally on 2026-10-05; see doc/iteration/iteration-008/part1.md. Parts 2–5 remain deferred.

## Objective and confirmed scope

Transfer the Braunschweig demonstration to a predefined Hannover/Lehrte study region. Deliver reproducible acquisition and cached loading, explicit hard constraints, existing weighted routing algorithms, map visualization and static experiments.

- Initially select both endpoints from all eight locations in the supplied attachment.
- Cover every listed location and provide space for constraint-driven detours.
- Use a fixed-altitude 2D model: configurable 100–120 m, one altitude per run.
- Use constant cruise speed: configurable 25–35 m/s, one speed per run.
- Acquire and integrate OSM, DIPUL and GHSL this iteration.
- Retain the existing risk/distance objective: risk weight 0.9 and horizontal-length weight 0.1. Distance-only routing remains a comparison baseline.
- Retain existing building risk semantics. GHSL acquisition, inspection and statistics are in scope; population costs and cross-layer fusion remain deferred.
- Future functionality allows an arbitrary origin within the supported region and any listed destination.

Provisional engineering defaults, subject to review: 100 m AGL, 30 m/s and an initial 5 km margin around the location extent. These are not supervisor-specified defaults. AGL means above ground level; a fixed-AGL 2D model does not establish 3D clearance or terrain-following feasibility.

Estimate cruise time as t = L / v and show the interval [L / 35, L / 25]. Exclude takeoff, landing, acceleration, wind, hovering and turn dynamics. Keep flight-time estimates separate from computation time. Speed does not change the current geometric objective or constraint model.

## Existing capabilities and implementation approach

Reuse the existing acquisition, storage, experiment/grid, planning, routing, risk, comparison and native ABIT* modules, together with CLI/API/UI and GeoJSON export. Use EPSG:25832 for metric calculations and longitude/latitude for input and display.

Preserve strict/research modes. Unknown coverage or applicability must not silently become permission. Research assumptions remain explicit and exported; such routes are not fully source-validated flight routes.

Assess the full-region grid size, memory and preparation time before selecting resolution and caching strategy. The current 10,000-cell limit and frontend request timeout may be insufficient. Address these explicitly without dropping listed sites, silently shrinking coverage or disabling constraints.

## Part 1 — Locations, region and reproducible acquisition

### Location catalog

Use the supplied `destination_drone.docx` as location data. Verify addresses and coordinates; retain name, type, original address, coordinates, coordinate source and verification status.

| ID | Location | Supplied address |
|---|---|---|
| mhh | Medizinische Hochschule Hannover | Carl-Neuberg-Straße 1, 30625 Hannover |
| henriettenstift | DIAKOVERE Henriettenstift | Marienstraße 72–90, 30171 Hannover |
| rheuma-lister | Rheumapraxis Hannover – Lister Meile | Lister Meile 35, 30161 Hannover |
| rheuma-podbi | Rheumapraxis Hannover – Podbielskistraße | Podbielskistraße 336, 30655 Hannover |
| limbach-lehrte | MVZ Labor Limbach Lehrte | Auf den Pohläckern 12, 31275 Lehrte |
| amedes-georg | amedes MVZ wagnerstibbe | Georgstraße 50, 30159 Hannover |
| amedes-schiffgraben | amedes MVZ genetics | Schiffgraben 30, 30175 Hannover |
| friederikenstift | DIAKOVERE Friederikenstift | Humboldtstraße 5, 30169 Hannover |

An address coordinate is not a verified launch/landing site. Report blocked endpoints rather than silently relocating them.

### Region configuration

1. Construct an extent containing all verified locations, including Lehrte, with a configurable metric detour margin.
2. Start with the provisional 5 km margin and revise it after inspecting constraints and boundary sensitivity. It is not a feasibility guarantee.
3. Keep study-region, source-coverage and planning-boundary definitions consistent and explicit.
4. Compare the initial region with an expanded region. Distinguish boundary truncation, missing data, grid limitations and actual blocking geometry.
5. Save region, source/product parameters, altitude, speed, grid and planning parameters in reproducible configuration.

### Acquisition and snapshots

- OSM: reuse acquisition of buildings, roads, land use and natural features needed by the existing workflow. Preserve source IDs, geometry and attributes.
- DIPUL: verify official service/download availability and schema; acquire relevant zones and restrictions. Preserve coverage, effective dates, schedules, vertical limits and unresolved fields. Screenshots are not the sole input.
- GHSL: reuse population acquisition. Record product, version/year, resolution, units, CRS, NoData and coverage. Population and built-up products are distinct; identify any separately required built-up product explicitly.
- Terrain: retain existing elevation input and unknown-state checks where required for AGL/altitude diagnostics. Do not invalidate existing vertical-reference checks by changing cruise altitude.
- Preserve original responses/files, processed data and a manifest with retrieval time, extent, parameters, versions, checksums and processing steps.
- Support bounded source requests, retries, chunking and caching as appropriate. Incomplete acquisition must not produce a complete-looking snapshot. Refreshes create new snapshots rather than overwrite evidence.
- Separate online acquisition from offline loading. After initial acquisition, run experiments using saved snapshots without network access.

Acceptance: all eight sites lie inside the region with documented margins; OSM/DIPUL/GHSL acquisition and loading are reproducible; derived data can be rebuilt from preserved originals after clearing derived caches.

## Part 2 — Fixed-altitude hard constraints and GHSL inspection

### Constraint rules

Document each rule's source, category, applicability, 2D interpretation, buffer, unknown policy and rationale.

- DIPUL: distinguish prohibited, conditionally allowed and unresolved zones. Evaluate the selected altitude and a documented scenario interval; do not reuse historical Braunschweig mission dates as current verification. Do not compare AGL numbers directly with other vertical references or absent limits.
- OSM: buildings, roads and land use are not automatically legal no-go areas. Introduce obstacle/restriction rules only with explicit source or modelling justification.
- Building obstacles: compare available height with cruise altitude and configured clearance. Missing heights remain explicit. A conservative footprint exclusion is a modelling assumption, distinct from legal prohibition and from a soft building score.
- Report hospital/laboratory endpoint conflicts; do not invent exemptions for unmodelled takeoff/landing.
- Use consistent point, complete-motion, endpoint-connector and safety-buffer checks across all algorithms.
- Keep confirmed blocked geometry separate from unknown coverage, time and altitude applicability. Strict mode retains explicit unresolved outcomes.

### Existing soft building risk

Preserve the approved building-only risk map, classification values, maximum-score overlap policy, explicit background assessment and non-polygon diagnostics. A high soft score is not a hard prohibition. Unknown support must not become observed zero risk.

### GHSL scope

Acquire, crop, transform, validate units/NoData, visualize and inspect population data. Provide region statistics and reusable corridor/crossed-cell queries with native resolution and missing-support information.

GHSL is not a legal prohibition source or a routing cost in this iteration. NoData is not zero population, and population counts are not automatically flight-risk scores.

Acceptance: applicable constraints reflect the selected altitude and documented scenario; rules are traceable; GHSL can be inspected without changing the existing weighted objective.

## Part 3 — Weighted algorithm integration

Reuse A*, Dijkstra and native ABIT* with the Hannover snapshot, listed endpoints and shared hard constraints.

For segment e, retain the existing approved calculation:

R(e) = sum(length(e intersect A_i) * r_i)
J(e) = 0.9 * R(e) + 0.1 * length(e)

Use the existing non-overlapping effective building-risk map and unbuffered route centerline. Sum segment costs including exact endpoint connectors. Do not reinterpret ordinal building scores as calibrated probabilities.

- Weighted routing is the primary requested objective. Retain distance-only mode as a baseline using the same constraints, clearance and planning mode.
- A*/Dijkstra share graph construction and endpoint connectors. For weighted A*, retain an admissible lower bound consistent with nonnegative costs (0.1 times straight-line distance); Dijkstra uses zero heuristic.
- ABIT* uses the same weighted segment objective, risk semantics, geometry checks, region, altitude and clearance. Record search budget and stochastic variability.
- A*/Dijkstra agreement is evaluated on the same discrete graph. ABIT* is continuous-space planning; do not require graph-identical lengths or claim global optimality from finite runs.
- Include source snapshots, rules, region, altitude, grid, objective, weights, risk/background policies and clearance in prepared-model cache identity as applicable. Speed belongs in mission/result metadata and time estimates, not geometric cost.
- CLI/API/UI share configuration and core logic. Return length, accumulated risk, weighted objective, speed, cruise-time estimate/range, preparation/search/total durations, assumptions and provenance.
- Distinguish invalid endpoints, unresolved inputs, no graph path, resource limits, native unavailability, timeout and computational failure.
- Independently validate final full-route geometry and recompute objective components.

Acceptance: all three algorithms use Hannover inputs and the same constraint/risk semantics; weighted A*/Dijkstra agree on graph objective; successful routes pass independent checks; bounded ABIT* failures are reported honestly.

## Part 4 — Endpoint selection and visualization

- Add Hannover as a new dataset while preserving historical Braunschweig evidence.
- Provide origin and destination selectors containing all eight sites. Explain same-site selections.
- Display boundary, locations, OSM, original DIPUL zones, effective constraints, unknown areas, GHSL and route with independent layer switches and clear legends.
- Show altitude, speed, objective/weights, mode, length, risk cost, weighted objective, estimated cruise time and computation durations.
- Invalidate stale results when endpoints, altitude, objective/weights, algorithm, sources or rules change. Speed-only changes may reuse geometry but must refresh time estimates and exports.
- Export exact endpoints, source/rule provenance, assumptions, objective components, mission parameters and timings.
- Arbitrary map-selected origins and out-of-region acquisition remain future extensions.

## Part 5 — Static experiments and evidence

Candidate pairs, subject to coordinate and constraint verification:

1. rheuma-podbi → mhh: local scenario.
2. amedes-georg → mhh: urban scenario.
3. limbach-lehrte → mhh: cross-city and larger-region scenario.
4. henriettenstift → friederikenstift: another hospital pair.

Evaluate at least three representative pairs and retain actual endpoint-conflict/no-path evidence. Do not move addresses, remove constraints or silently select research mode to manufacture success. If real inputs remain unresolved, use separately labelled synthetic fixtures to verify algorithms and preserve the real failure findings.

Record endpoints, snapshot/region, altitude, speed, mode, algorithm, objective/weights, grid/clearance, length, risk, objective value, estimated cruise time/range, preparation/search/total durations, outcome and independent checks.

Compare the inherited building-weighted objective with the distance-only baseline where feasible. This is not a new GHSL-aware objective. Repeat ABIT* at least three times per scenario; record budget, success rate and length/objective/runtime variation. Separate cold and warm caches.

For representative pairs, check 120 m altitude, expanded boundaries and grid-resolution sensitivity. Verify speed limits and time estimates at 25, 30 and 35 m/s. Neither altitude setting is required to produce a feasible route.

Document coverage/applicability uncertainty, missing building heights, fixed-AGL 2D limitations, unmodelled takeoff/landing and dynamics, GHSL year/resolution, graph discretization/resource limits and ABIT* randomness. A research route is not flight permission.

## Implementation order and validation

1. Inspect existing module contracts and estimate region/resource scale.
2. Verify sites and save region/source/mission configuration.
3. Acquire OSM/DIPUL/GHSL and create rebuildable snapshots.
4. Prepare altitude-dependent constraints, retain building risk and add independent GHSL inspection.
5. Integrate weighted A*/Dijkstra/ABIT*, distance baseline and CLI/API contracts.
6. Implement endpoint selectors, visualization and exports.
7. Run static experiments, sensitivity checks and document evidence.

Necessary checks cover site/region coverage, snapshot integrity and offline rebuilds, GHSL units/NoData, altitude applicability, speed bounds/time estimates, obstacles/clearance/connectors, inherited weighted costs and graph agreement, cache isolation, explicit resource failures, UI stale results and export provenance. Run appropriate backend regression, lint, frontend build and browser checks.

## Delivery and workflow

Deliver the eight-site catalog, full-region configuration, reproducible source pipeline, traceable constraint rules, inherited weighted algorithm integration, distance baseline, map/parameter/export functionality and at least three experiment records with operating instructions and limitations.

Update README and HANDOFF. All version-controlled code, iteration plans, project documents, issues and pull requests use English; Chinese review explanations may remain in chat.

Follow the existing milestone/iteration-branch/issue-before-feature-branch workflow when implementation is authorized. The initial request created documentation only. The user subsequently authorized Part 1 implementation and source acquisition on 2026-10-05. Milestone 7 and Issue #66 track Part 1 on feature/66-hannover-acquisition, based on iteration/008. The user subsequently authorized commit and feature-branch publication on 2026-10-06. The user subsequently authorized PR integration into main on 2026-10-06, with successful CI required; this delivery covers Part 1 only.

Deferred: arbitrary origins, endpoint-driven region expansion, OpenFlightMaps, GHSL population soft costs, cross-layer risk fusion and comparison against a newly population-aware objective. Existing building-weighted routing is retained now, not deferred.
