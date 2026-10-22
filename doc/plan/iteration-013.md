# Iteration 013 - Hannover map controls, inspection and estimated arrival

Date: 2026-10-22 (Europe/Berlin).
Status: approved by the user; Part 1 implementation authorized on 2026-10-22.
Part 1 tracking: assigned Issue #114 in verified Milestone 12, with
`feature/114-hannover-map-controls` created from `iteration/013` at the baseline
below. Part 1 implementation and local acceptance are complete: backend 316
passes / one existing Windows skip, 28 browser and 14 real-stack smoke passes,
plus final Hannover acceptance with zero-request cached visibility cycles.
See [Part 1 outcome](../iteration/iteration-013/part1.md). Publication and feature
integration have not run. Parts 2-4 remain planned.
Baseline: clean local `main` at `4ed0023`, including verified Iteration 012.

## Requested result and confirmed decisions

The Hannover regional page should have one coherent map-control area, organized
by source, and a persistent place to inspect the selected object. Selecting an
object must not insert a large block above the map or move the map down the page.
Flight planning should ask for departure time only and calculate estimated
arrival from the actual successful route and the entered cruise speed.

The user explicitly confirmed:

- Apply this iteration to the Hannover regional planning page first. Preserve
  the Braunschweig/small-area experiment page's existing functionality.
- OSM, DIPUL and GHSL share one left-side detail inspector. Selected objects have
  a black outline, and the map may retain a short summary with View details.
- Estimate constant-speed cruise only. Do not add takeoff, landing, wind or
  waiting time. Without a successful current route, arrival is Awaiting route.
- Endpoint selection gets a dedicated full-width row, separate from other
  planning inputs. A selection-method dropdown defaults to choosing origin and
  destination from the eight saved sites. Its second mode exposes exact
  longitude/latitude inputs and the current study's coordinate bounds.
- Remove the old `Use explicitly selected launch/landing coordinates` checkbox.
  The new dropdown is the only endpoint-mode switch.
- Remove the `Original DIPUL - purple, applicability unverified` map-layer
  control and its separate raw-zone overlay from the Hannover UI. Keep assessed
  DIPUL decision layers and source attributes/provenance needed for inspection
  and planning; do not delete retained source data or other pages' APIs.
- Scenario-dependent overlays, including orange policy exclusions, load
  automatically when enabled and refresh when their relevant inputs change.
  After a successful first load, cache the result: subsequent checks/unchecks
  for the same valid scenario only show/hide layers, with no repeat request or
  preparation. Hiding or collapsing a group must not discard its cached data.
  The user clarified that the unwanted prerequisite button is `Load scenario
  layers`: remove it. Keep `Plan regional route` for explicit route calculation;
  viewing a layer must not require or automatically trigger route planning.

Project UI and repository documents retain their existing English language.
The Chinese explanation accompanying this plan explains the proposed behavior.

## Current implementation findings

- `RegionalMap.tsx` renders a flat regional checkbox list above the independent
  controls owned by `RegionalOsm.tsx`. Related source controls are separated.
- `RegionalOsm.tsx` mounts `ObjectDetails` inside its own section above the map.
  Selection loads original details but does not draw a dedicated selected outline.
- `RegionalMap.tsx` uses `JSON.stringify(feature.properties)` in source/constraint
  popups. The aggregate OSM popup also embeds serialized category counts.
- `App.tsx` already has a 286 px left sidebar, with unused space on regional pages.
  The regional map is currently mounted through a portal from `RegionalRouting`.
- Constraint collections are organized by decision state, not exclusively by
  source. They mix OSM building obstacles, DIPUL/notice decisions and regional
  coverage uncertainty. Moving every existing checkbox under DIPUL would be wrong.
- The current regional renderer uses bounded OSM access. A separate all-brown
  regional OSM toggle is not present in the inspected `RegionalMap` controls.
  Treat the requested removal as retiring any legacy uniform-color/full-region
  display entry, not removing the brown Buildings color from Category mode.
- Regional scenario construction requires both `mission_start` and `mission_end`.
  Restriction decisions and evidence validity depend on that interval. The route
  result already computes `cruise_time_s = length_m / speed_m_s`, but this estimate
  is not currently used to derive or validate the mission end.
- Origin/destination currently share the generic `regional-controls` grid with
  terrain, time and other inputs. A separate override checkbox reveals four
  coordinate fields later in the form; it provides no study-specific bounds.
- Scenario overlays currently consume `constraints` only after an explicit
  `loadConstraints()` request from `Load scenario layers`. Their checkboxes only
  change visibility; `solve()` does not initiate that separate layer request.

## Part 1 - Grouped map controls and a dedicated endpoint row

Replace the two separated control blocks with one compact Map layers area near
the map. Each group expands/collapses independently; collapsing a group never
turns its layers off. Keep group state and layer visibility separate.

Proposed hierarchy:

```text
Map layers
  Base map & references
    Street map / Study boundary / Sites / Route
    Focus origin / Focus destination / Fit study
  OSM
    Saved objects: Buildings / Roads & paths / Land use / Natural features
    Color by: Feature category / Category cost
    Cost category / Legend / Refresh OSM
    Building obstacle and building-uncertainty overlays, if scenario data exist
  GHSL population
    Population cells / Legend / Dataset epoch and resolution
  DIPUL restrictions
    Prohibited / Excluded by current policy / Conditions satisfied / Not applicable
    Unresolved DIPUL zones
  Scenario coverage & diagnostics
    Region-wide unknown coverage / Terrain or other unclassified findings
```

Route and site references are not OSM source objects. Street tiles are a separate
online background, even though they are provided by OpenStreetMap. Temporary
notice derivatives must be identified by their actual provenance and cannot be
relabelled as original DIPUL records. Split mixed decision collections using
source/category metadata; preserve decision semantics and traceable original
attributes in the inspector. Remove the separate Original DIPUL checkbox and
purple raw-zone overlay rather than moving them into the new group or simply
hiding the checkbox while leaving that overlay active. Do not fetch raw zones
solely for that retired overlay. Retain original files and APIs used by planning,
provenance, or other pages.

There must be one active regional OSM object-rendering path. Remove obsolete
uniform-color/full-region UI entries if encountered; never restore the legacy
Hannover full-object request. Keep source APIs/exports needed by other pages.

Use group-local loading, failure, disabled and retry states. Show short legends
beside their controls; put detailed counts, provenance and diagnostics inside
collapsed disclosures rather than long paragraphs before the map.

Acceptance: every retained regional layer is mapped to its correct group; the
retired Original DIPUL control/overlay and duplicate OSM display entries are
absent, with no raw-zone display request from the retired path. Collapse/expand preserves visibility,
selected controls, map position and route results. Groups have accessible names,
keyboard-operable disclosure buttons and visible expanded state.

### Automatic scenario-layer loading and cached visibility

Remove the `Load scenario layers` button and the instruction requiring a manual
scenario-layer load. Enabling orange policy exclusions, effective prohibitions,
conditions-satisfied, inactive, unknown or building-derived overlays first checks
the matching scenario cache. On a miss it automatically requests and caches the
required collections, then displays the enabled ones. On a hit it only shows the
existing collection; unchecking only hides it.
Already-enabled defaults follow the same rule on initial page load once required
inputs are ready. No extra click or successful route is required.

- Present Pending inputs, Loading, Ready, Updating, Empty and Error states near
  the corresponding source group. For missing departure, invalid active endpoints
  or unavailable required data, identify the field to complete; do not silently
  show an empty map or describe missing data as a verified empty collection.
- Debounce valid scenario edits (proposed 300 ms) and refresh enabled dependent
  layers automatically. Include dataset/source identity, terrain, departure and
  current assessed/provisional interval, planning mode, evidence profile, height,
  clearance and other actual scenario dependencies in the request identity.
  Active endpoints/speed matter when they determine the automatic interval.
- Deduplicate collection preparation across enabled overlays sharing a scenario;
  a single constraint response may supply several source/decision display groups.
  Cache every returned collection, including currently hidden groups and valid
  empty results. If one request already returned excluded, blocked, allowed and
  unknown collections, enabling another of those groups must reuse that response.
  Do not cache failures as successful empty results.
- Retain the successful current-scenario cache independently of layer component
  visibility/mounting. Unchecking, closing a popup, collapsing a group or disabling
  all scenario overlays must not clear it. Subsequent off/on cycles with unchanged
  dependencies issue zero layer-data requests, source verification requests or
  preparation jobs and do not trigger routing. A category color or disclosure
  change also must not invalidate constraints or the current route.
- Reuse results only for matching scenario and known source identity. Invalidate
  or replace them when relevant parameters, dataset/source revision or evidence
  identity changes, or on an explicit refresh/retry that actually requires new
  data. With valid enabled layers, automatically load a missing replacement;
  hidden layers load only if later needed. Keep current-scenario data bounded
  and separate from Iteration 012's independent viewport OSM cache; do not retain
  an unbounded history of scenario versions.
- Cancel/deprecate obsolete requests and reject late results using identity and
  request generation. Bound backend work as well as browser requests; rapid input
  edits must not launch an unbounded series of full preparation jobs. Hide stale
  scenario geometry while replacing it and clear its invalid selected details.
- Disabling a layer hides it immediately; an outstanding response must not show
  it again. If another enabled overlay still needs the shared request, allow that
  request to finish for those consumers. If none remain, stop obsolete work where
  supported. Keep valid route results and map position on visibility changes.
- Failures stay local to the affected group, with a contextual Retry action.
  Retry is an error recovery action, not a replacement mandatory load button.
- Before a route exists, show the provisional interval defined in Part 4 as a
  preview, not a verified flight-duration assessment. After a successful route,
  automatically update enabled layers to the returned assessed interval. This
  update must not clear the just-completed route or recursively trigger planning.

Acceptance: after valid inputs, enabling orange exclusions displays their loading
state and then their geometry without clicking either old load or plan buttons.
Verify initial enabled defaults, missing/invalid inputs, auto-refresh, empty/error
states, retry, fast edits, switching off during a request and one shared request
for multiple overlays. No `Load scenario layers` button or manual-load instruction
remains. After one successful load, repeat at least ten off/on cycles and collapse/
expand cycles: no further layer-data or verification requests, no preparation or
routing calls, and the same data becomes visible again. Verify reuse of hidden
collections from a shared response and valid empty collections; a relevant input
change must instead invalidate old data and load its enabled replacement once.
Toggling layers never calls the route endpoint. The explicit Plan button
continues to work independently, including when all scenario overlays are hidden.

### Endpoint selection row

Place a clearly labelled Origin and destination section at the start of the
planning form, on its own full-width row. Terrain, departure time, speed,
algorithm and other parameters begin in a separate section below it. Endpoint
controls must not flow into that generic parameter grid.

Provide one Selection method dropdown with exactly two modes:

1. Choose from saved sites (default): show Origin and Destination dropdowns, each
   containing the existing eight saved sites. Hide the coordinate inputs and do
   not require or submit inactive manual-coordinate values.
2. Enter exact coordinates: show Start longitude, Start latitude, End longitude
   and End latitude, with explicit decimal-degree labels. Replace the site
   dropdowns in the visible row rather than leaving two competing endpoint inputs.
   Remove the old `Use explicitly selected launch/landing coordinates` checkbox
   entirely; do not keep it as a second switch or an advanced option.

Illustrative desktop structure (input widths remain responsive):

```text
Origin and destination
  Selection method [Choose from saved sites v]  Origin [site v]  Destination [site v]

or

Origin and destination
  Selection method [Enter exact coordinates v]
  Start longitude [ ]  Start latitude [ ]  End longitude [ ]  End latitude [ ]
  Study bounds: longitude west to east; latitude south to north (decimal degrees)

Flight and planning parameters
  Terrain [...]  Departure [...]  Cruise speed [...]  ...
```

Read the displayed bounds from the current study's `config.bounds`: longitude
`west <= lon <= east`, latitude `south <= lat <= north`, in WGS84 decimal degrees.
Show readable numeric bounds near the coordinate inputs, not hardcoded Hannover
constants or only the generic worldwide +/-180 and +/-90 limits. Handle pending
or unavailable study bounds explicitly. Preserve input precision; validate finite
values and show field-specific errors for missing or out-of-study coordinates.
Do not silently clamp coordinates or move them to a nearby site. A point inside
the bounding range still undergoes the existing endpoint/constraint checks.

Only the active mode determines actual endpoints. Changing mode or either
endpoint invalidates the previous route, estimated arrival and endpoint-dependent
scenario results. Markers, Focus origin/destination, planner requests and exports
must all use those same active endpoints. Retain original catalog references
separately where needed for provenance; they must not override entered coordinates.

Acceptance: initial load uses saved-site mode with eight options per dropdown;
coordinate inputs appear only in the second mode; the old checkbox is absent;
study-specific bounds are visible in coordinate mode; inactive fields do not block
submission or leak into requests. Test exact-coordinate requests, focus/markers,
out-of-bounds errors, switching modes with an existing result, refreshed bounds
and 390 px mobile stacking. The endpoint section remains visually separate from
all other planning parameters on both desktop and mobile.

## Part 2 - Shared selection, black outline and left inspector

Use one selected-object state shared across OSM, GHSL and DIPUL/derived overlays.
Identify selection with dataset/source identity and stable object/cell identity.
Clicking another object replaces the previous selection across all sources.

- Render a dedicated black selection outline above source fills, preserving their
  original color. Follow polygon/multipolygon boundaries; use a black stroke for
  lines and a black ring for points. Do not use an object's rectangular bounds as
  a substitute for its geometry.
- The outline must be noninteractive and must not block clicks on underlying
  features. Distinguish it from existing dark paper-obstruction strokes by a
  consistent width/halo and a Selected indicator in the inspector.
- Mount the inspector in the existing page-left sidebar. Keep it visible alongside
  the map on desktop, with its own bounded scrolling area for long details. Do
  not put the full inspector above the map or inside the map's clipping container.
- A small map summary contains source, name/type and one or two principal values,
  plus View details. This action focuses/reveals the left inspector without
  navigating away or changing the map extent.
- Provide a close/clear action and an empty Select a map object state. Handle
  loading, unavailable fields and retry without displaying old object content.
- Retain selection across a harmless sidebar/group collapse or popup close. On
  map movement, retain it only while that same object remains in the current
  displayed collection; clear when it is removed, its layer is hidden, the dataset
  or source identity changes, or an overview replaces its detail geometry. Late
  detail responses must never overwrite a more recent selection.
- OSM aggregate cells are explicitly labelled overview cells, not individual OSM
  objects. Their outline and summary show category counts and a Zoom for objects
  action. Diagnostic originals without renderable geometry remain readable in the
  inspector with an explicit No drawable geometry state and no fabricated outline.
- At narrow/mobile widths, use one collapsible detail sheet associated with the
  map; avoid horizontal overflow and automatic jumps to a long block above it.

Acceptance: selecting two objects rapidly leaves exactly one matching outline,
summary and inspector. Opening details does not move the desktop map vertically.
Clearing, hiding, changing datasets and returning to overview remove stale state.
Selection does not recreate the map or refetch whole regional source collections.

## Part 3 - Readable source details and explanations

Use a common card layout: source/type badge, useful title, main facts with units,
interpretation/uncertainty, then expandable original attributes and provenance.
Use escaped text/React rendering for source strings, with wrapping for long values.
Raw JSON may remain an explicitly labelled advanced/export option; it is never
the default description in the popup or inspector.

| Source | Main information |
|---|---|
| OSM object | Name or readable type, OSM identity, category membership, available original height/address tags, independent costs with 0-4 labels, matched rules and provisional/default status |
| OSM aggregate | Aggregate status, assigned-object count, category counts, counting limitations and zoom action; no invented object-level cost |
| GHSL cell | Estimated people per native cell, native resolution, epoch, zero versus NoData, cell/source identity and relevant coverage information |
| DIPUL assessed zone | Decision and reason first, then available original name/type, source identity, lower/upper height and units/reference, validity and legal/source references; no separate raw-zone display |
| Scenario derivative | Decision status, reason, source, buffer/clearance, assessed time/height scope, policy exclusion versus confirmed prohibition, linked original identity when available |

Show only fields actually supplied. Do not turn missing heights into zero,
population estimates into exact headcounts, paper cost labels into permission
decisions, or source zones into confirmed bans. Keep source and assessment facts
separate. Align GHSL legend text with the actual rendered zero/NoData colors.

Replace ambiguous color labels with Feature category and Category cost, and place
short contextual help beside them:

- Feature category: fixed colors identify buildings, roads/paths, land use and
  natural features. For multiple memberships, the first enabled category wins in
  that order. Hiding a category can reveal another membership of the same object.
- Category cost: select one category and color its objects using the existing
  ordinal 0-4 cost palette (very low through very high). Category costs are
  independent, never added together; this view is not an overall risk surface.
- Unknown/default/no numeric cost: gray dashed styling; an uncolored background
  is unassessed. Existing paper-obstruction flags keep a separate explanation.
- Cost category: chooses the category being assessed for display. Selecting a
  category enables it, as today; this does not change the route objective.
- At overview zoom, show aggregate category colors and explain that object cost
  inspection becomes available on zooming in. Do not imply overview cells contain
  a cost score.
- Refresh OSM reloads prepared local display data; it does not acquire new OSM
  originals. Fit study in Base map & references changes map extent only; remove
  the duplicate Fit saved study action from the OSM controls.

Acceptance: a user can understand each selected source feature without reading
JSON. Tests cover missing fields, nested attributes, long values, zero/NoData,
independent costs, units/references and untrusted source text. Normal map controls
explain their visible effect without exposing implementation details.

## Part 4 - Departure-only input and consistent estimated arrival

User-visible behavior:

1. Enter departure date/time in Europe/Berlin and cruise speed in m/s. Remove the
   editable end-time field from this regional form.
2. Before a successful current route, display Estimated arrival: Awaiting route.
3. For a successful route use its verified metric length, not straight-line
   distance: `cruise_time_s = length_m / speed_m_s` and
   `estimated_arrival = departure + cruise_time_s`.
4. Show length, speed, estimated cruise duration and local arrival date/time with
   offset together. Example: 3,600 m / 30 m/s = 120 s; 10:00 departure gives 10:02.
   Label this estimate as cruise only. Planning computation time is not flight time.
5. Changing departure, speed, endpoints or other route-affecting inputs invalidates
   the old route/arrival and relevant scenario results. A failure displays no
   successful-route ETA. Do not recompute arrival from stale route geometry.

This Part includes a backend/API change, not just a form edit. Restriction and
profile expiry checks must cover the estimated flight interval. A hidden constant
end time or a post hoc UI estimate over an unrelated validated interval is invalid.

Implementation design:

- Add an explicit automatic-duration request mode; retain existing explicit
  start/end request compatibility for CLI, experiments and historical reproduction.
- Seed a provisional interval from the metric straight-line lower-bound duration
  between the actual requested endpoints, using the entered speed. This is a
  planning seed, never a successful-route ETA. A zero-length case needs an explicit
  instantaneous/zero-duration rule rather than division or a fabricated duration.
- Find a candidate, derive its actual cruise arrival, and reassess constraints and
  evidence over the complete candidate interval. If the required interval extends
  beyond the assessed interval, extend it and replan/revalidate. Assessed intervals
  only expand within a request, preventing oscillation from shrinking assumptions.
- Proposed maximum: three candidate passes under one shared request deadline and
  planner budget, not three independent full budgets. Confirm feasibility against
  the existing browser timeout during implementation. On exhausted budget or
  unstable duration, return an explicit unsuccessful outcome with no accepted
  route/ETA; never silently accept an incompletely checked route or simply raise
  the timeout to hide repeated preparation.
- On success, return both actual estimated cruise interval and assessed interval,
  with the latter containing the former. Any broader assessment is explicit in
  provenance; UI, restriction report, profile review and export use the same
  completed result. Do not rewrite historical explicit-interval semantics.
- Automatic scenario-layer preview before route completion uses the same clearly
  marked provisional interval and is not presented as the final flight assessment.
  After a successful route, automatically refresh enabled layers using its assessed
  interval; stale preview findings must not look like final route findings. No
  manual `Load scenario layers` action is required in either state.
- Add elapsed time in UTC/epoch space and then format Europe/Berlin with its
  resulting offset. Preserve rejection of ambiguous/nonexistent departure times;
  support midnight and DST crossings without adding hours as local clock text.
- Preserve current speed bounds and existing restriction/profile/source checks.
  Share request-local immutable preparation only where interval/source identity
  makes reuse safe; a general planner cache redesign is outside this iteration.

Acceptance: test 3,600 m / 30 m/s, fractional seconds, midnight/DST crossing,
invalid speed/time, no route, same endpoints and stale results. Include synthetic
restrictions that become active during flight, an evidence profile expiring during
flight, an extended route requiring another pass, and bounded nonconvergence.
Exported ETA/mission/assessment metadata must match the displayed current result.

## Validation, compatibility and delivery

- Parts 1-3: frontend lint/build and focused browser interaction checks; add
  backend tests only if source provenance/detail contracts change. Verify actual
  Hannover OSM objects, GHSL cells and assessed DIPUL/scenario derivatives,
  including available original-source facts in their details. Verify removal of
  the Original DIPUL switch, overlay and overlay-only fetching path.
- Part 4: backend/API/time-rule tests plus browser flows; explicit-interval
  regression and A*/Dijkstra/native ABIT* compatibility. Include uncertainty/failure
  paths, not only successful research routes.
- Final real-data acceptance: desktop and 390 px mobile; with street tiles disabled;
  category/cost switches, one selected outline, readable details, group collapse,
  fast reselection, layer hiding, both endpoint modes and displayed study bounds,
  automatic scenario-layer loading/refresh and route/export/focus consistency on
  time changes. Verify that the old coordinate checkbox and `Load scenario layers`
  button are absent and endpoint inputs occupy a separate form row/section.
- Preserve Iteration 012 bounds (5,000 objects / 5 MiB / 100,000 coordinates per
  detail response, bounded overview and four-entry / 8 MiB nearby cache). Check that
  selection and group changes do not reload originals, add repeated handlers or
  alter route costs. Record actual cold/warm and auto-duration costs separately.
- Run the required complete backend/frontend/real-stack checks and independent
  Linux/Windows/frontend CI gates for an authorized implementation delivery.
  A local documentation-only plan needs no application test run.

Suggested delivery order: Part 1 map/endpoint controls, Part 2 selection/layout, Part 3 readable
details/help, Part 4 automatic duration, then integrated acceptance. Each Part must
leave the application usable. Follow the repository milestone -> iteration branch
-> assigned issue -> feature branch workflow when implementation is requested;
record actual remote IDs then. No remote milestone, issue or PR is created merely
by drafting this plan.

Expected outcome: `doc/iteration/iteration-013/outcome.md`, updated operating notes
and HANDOFF/README, with new local `.cache/` evidence and screenshots excluded from
Git. Preserve originals, private evidence profiles and user-owned services.

Outside scope: Braunschweig UI migration, source acquisition/expansion, cost-table
or route-objective changes, new permission rules, OFM planner integration,
takeoff/landing/wind/energy models, 3D planning and broad performance redesign.
