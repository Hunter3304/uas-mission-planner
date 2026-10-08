# Iteration 008 Part 4 — Endpoint selection and regional visualization

Date: 2026-10-07 (Europe/Berlin).
Tracking: Milestone 7 / [Issue #75](https://github.com/Hunter3304/uas-mission-planner/issues/75).
Branch: `feature/75-regional-visualization`, based on `iteration/008` fast-forwarded to main `77cb64b`.
Implementation authorized; changes are local. Part 5 remains deferred.

Commit authorization, 2026-10-08: user requested committing after final review.
No blocking finding identified; backend Ruff lint/format and frontend lint/build
rechecked successfully. Publication and integration are not included in this request.

Integration authorization, 2026-10-08: user authorized remote push and integration
through feature -> iteration/008 -> main, gated by successful CI on each PR.
Implementation commit: `c574a57`. Retain source snapshots and iteration/008;
clean the feature branch only after its merge is verified. Earlier local-only
publication statements describe the preceding implementation stage.

Feature delivery, 2026-10-08: PR #76 merged into iteration/008 at `8eaee93`
after all three CI jobs passed in run `37798466570`. Issue #75 is closed.
Main integration remains separately gated by successful CI. Automatic approval
review rejected branch deletion without explicit user approval; retain the merged
feature branch pending approval. Final main merge facts are reported in chat.

## Behavior and operation

Select the retained `hannover-part1-v4` dataset in the explorer. Historical
Braunschweig datasets retain their existing explorer, planning and evidence.
Regional origin/destination selectors read all eight named addresses from the
verified source manifest. Selected locations are highlighted on the map; same-site
selection explains that endpoint validation still applies. Addresses are not
verified launch/landing facilities and are never silently relocated.

Enter offset-aware scenario start/end times and the terrain dataset ID. Set
altitude, speed, algorithm, objective/weights, mode and clearance, then use
**Load scenario layers** to prepare constraints and **Plan regional route** to solve.
The map has independent boundary, locations, OSM, original DIPUL, effective blocked
constraints, unknown areas, GHSL and route switches with legends. Source OSM,
DIPUL and population layers load on demand; large regional snapshots no longer
require initial tag-cost analysis to use the regional interface. Feature popups
use text nodes, preserving untrusted metadata as text.

Original DIPUL footprints are distinct from scenario-dependent buffered obstacles
and restrictions. Unknown-height footprints are amber. Region-wide temporary/NOTAM
uncertainty is explicitly represented by an unknown boundary footprint; invalid
source geometry and terrain findings remain separate diagnostics. Zone vertical
applicability uses conservative complete native terrain windows and the same
rules as routing. No geometry repair or inferred permission is introduced.
GHSL preserves native people/cell values, zero and NoData and remains inspection
only. Effective/unknown layers require explicit scenario preparation.

Successful geometry appears in green. Results display altitude, speed, algorithm,
objective/weights, mode, length, accumulated building risk, weighted objective,
cruise estimate/range and source/preparation/search/total durations. Unresolved
inputs retain endpoint findings and assumptions; failure geometry is not rendered
or exported as a successful route. Cruise estimates exclude takeoff, landing,
wind and dynamics.

Changing route inputs cancels obsolete requests and invalidates displayed results.
Scenario altitude, time, clearance and terrain changes also invalidate prepared
constraint layers. Dataset refresh remounts regional state. Speed-only changes
conservatively invalidate the result and require another solve; geometry reuse
is optional and is not implemented. No stale time estimates remain exportable.
Exports serialize the displayed result without another solve, retaining all core
mission, source/rule provenance, costs, timings and assumptions plus displayed
controls and exact catalog endpoint records.

Read-only source API: `GET /api/datasets/{id}/study/layers/zones`.
Scenario preparation API: `POST /api/datasets/{id}/study/layers/constraints` with
`scenario` and optional contained `terrain_id`. Existing population/route APIs
remain compatible. Source checksums are verified before layer preparation.

## Validation and practical limits

- Backend regression: 223 passed / one existing Windows permission skip (77.60 s).
- Frontend lint and production build pass; 11 mocked browser checks pass (6.9 s),
  covering all eight selectors, same-site explanation, independent switches,
  source layer loading, displayed-result export/provenance, parameter invalidation
  and 390-pixel mobile layout. Screenshot: `.cache/part4-mobile.png`.
- All 12 real API/browser smoke checks pass with clean exit (30.5 s), preserving
  historical source, routing, export and native ABIT* behavior.
- Offline real Hannover preparation: all eight catalog sites; one blocked feature,
  162,335 unknown features including region-wide uncertainty; 91 diagnostics;
  all layer JSON finite. Preparation took 74.77 s with retained full terrain.
  Compact local evidence: `.cache/part4-real-layers.json`. Sources remain unchanged.

Full-source preparation and large GeoJSON rendering are substantial operations;
unknown/OSM/GHSL overlays default off and load/render only when requested. A complete
successful real regional search remains unestablished because retained source
uncertainties persist. This delivery does not claim a feasible real route or flight
permission. Arbitrary map origins, out-of-region acquisition, GHSL routing costs
and Part 5 experiments remain deferred. No dependency installation or original
source modification was needed.
