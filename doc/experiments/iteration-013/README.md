# Iteration 013 - Regional controls and shared inspection

Scope: Hannover regional UI and automatic cruise intervals. Original data,
costs, routing objectives, permissions and the small-area UI are preserved.

## Using the controls

Restart the backend after this update (the constraint preparation admission guard
is server-side), restart/refresh the frontend, and select `hannover-part1-v4`.

The Origin and destination section is independent of other planning inputs:

- Choose from saved sites is the default. Each dropdown contains the eight sites.
- Enter exact coordinates replaces those dropdowns with four decimal-degree
  inputs. The displayed WGS84 study range is rounded for readability; input limits,
  calculations and exports retain the exact coordinates. Out-of-range values are
  rejected, never clamped. Focus buttons/markers follow the active coordinates.
- Switching endpoint mode or editing route inputs clears the old route/export.
  Original catalog IDs remain reference metadata when exact coordinates are used.

Map layers is one area with independently collapsible Base map & references,
OSM, GHSL population, DIPUL restrictions and Scenario coverage & diagnostics.
Collapsing a group preserves its layer visibility and cached data. Mixed building,
DIPUL and notice/coverage derivatives are grouped by provenance, not just color.
There is no separate Original DIPUL switch/raw overlay or full-region OSM renderer.
Fit study is in Base map & references; OSM source counts are in a disclosure.

Scenario overlays load automatically once an enabled layer has valid scenario
inputs. The current regional form takes **Departure time** only; the explicit
Scenario start/end inputs were Part 1's historical intermediate state. Until inputs are
ready, source groups explain what is missing. Valid edits are debounced by 300 ms.
Plan regional route remains an explicit independent action; layer toggles never
call the route endpoint. The old Load scenario layers button is removed.

The first successful scenario response is retained in page memory, including
hidden and empty collections. Subsequent checks/unchecks only show/hide them,
without a network or source-verification request. GHSL cells have their own cached
load. A relevant scenario/profile/terrain change selects a different identity;
only one scenario result is retained rather than an unlimited parameter history.
Dataset switching, page reload or the sidebar Refresh resets this page cache.
After replacing sources on disk, use the sidebar Refresh to discard old results;
visibility toggles deliberately do not poll/rehash unchanged source files.

Only one scenario preparation runs at a time in the page. Superseded preparation
is awaited, then only the latest requested scenario is loaded; old results never
appear under new inputs. The backend also permits one active constraint-layer
preparation per app process and returns 503 with a retry message when occupied.
This admission guard still applies after an HTTP client disconnects. Failed loads
are not cached as empty results. Source-local Retry recovers from errors.

Initial preparation still reads the full existing constraint model, including
many uncertain buildings. This Part caches that response; it does not redesign
preparation or bound the scenario payload to OSM viewport limits. The independent
bounded OSM display and its readiness checks remain in place. Parts 2-3 below
add shared selection and richer source formatting/help.

## Selecting objects (Part 2)

Click an OSM object, DIPUL restriction, GHSL cell or derived scenario area. A
black outline with a white halo follows its actual geometry and preserves its
original fill. The outline does not intercept clicks. One selected object is
shared across all sources; choosing another replaces its outline and details.

The left sidebar shows Object details with its own scroll area. The small map
summary's View details button expands and focuses this inspector without moving
the map. Closing the summary or folding a source group retains the selection.
Clear selection removes it. Hiding its layer, changing dataset/source identity,
replacing its displayed collection or moving outside the object clears stale
selection. A small pan retains an object that remains in the current collection.
Late original-object responses cannot overwrite the latest choice.

OSM overview cells are labelled aggregate cells, with assigned-object/category
counts and Zoom for objects. They do not represent individual objects or cost
scores. Source geometry diagnostics remain inspectable with original tags and
an explicit No drawable geometry message; they never create an invented outline.
Individual OSM details load on demand; selecting does not fetch the full regional
source collection. Group folding does not reload originals.

On mobile, the same inspector becomes one bottom detail sheet, at most 55% of
the viewport height. Collapse object details reduces it to its heading/actions;
Expand object details or View details reveals the content again. Main facts and
original attributes are retained; Part 3 below adds source-specific cards, units
and color-mode explanations. Departure-only timing remains Part 4.

## Reproducing Part 2 real acceptance

```powershell
npm --prefix frontend run build
backend/.venv/Scripts/python.exe doc/experiments/iteration-013/verify-part2.py --output .cache/iteration013-part2-new
```

Use a new output directory. The wrapper uses free isolated ports 8020/5190 by
default, hidden services and owned-process cleanup. It needs installed Chrome,
the existing locked backend environment and prepared Hannover display. Optional
--api-port and --ui-port select other free ports. Run outside Windows socket/
native-handle sandbox restrictions. No acquisition or profile edit is performed.

The driver verifies aggregate-to-object inspection, ten selection replacements,
non-drawable diagnostic originals, left layout without map displacement, source
group retention, DIPUL/GHSL selection, cached GHSL visibility, desktop/mobile
screenshots, zero route requests, unchanged original OSM/study hashes and no
browser errors. It uses historical scenario 2026-10-07 10:00-10:15 Europe/Berlin
solely to prepare assessed overlays. Existing first-load preparation costs remain.
Evidence is local/ignored, including source/implementation hashes and services.json.
See [Part 2 outcome](../../iteration/iteration-013/part2.md) for actual results.

## Reading source details (Part 3)

Each selection shows main facts and interpretation first. Original attributes,
matched rules and provenance are separately expandable; Advanced: raw JSON is
closed initially. Nested original objects/arrays appear as readable labelled
lists, and long values wrap. The desktop inspector and mobile sheet retain their
bounded scrolling and selection behavior.

OSM shows its original identity, available name/type, category memberships, height/
address tags and independent ordinal costs. Height-tag units are preserved;
unqualified numeric OSM height tags are metres. Building levels are not converted
to measured height. A provisional score can contain both known matches and
default values. Historical paper obstruction flags do not establish current flight
restrictions. Expand Matched rules and evidence for rule reasons/references.

DIPUL/scenario cards separate assessment decision, reason, policy/uncertainty and
supplied time/height scope from original source facts. Source limits retain units
and references (for example ft AGL versus m MSL); absent limits remain unknown.
Current assessed responses do not always include original zone names/limits/
validity. The UI does not invent them or fetch a separate raw source overlay.
Source validity and compared assessment bounds are distinct facts. A policy
exclusion is not a confirmed prohibition; conditional evidence is scoped.

GHSL values are estimated people per native cell, not exact headcounts or people
exposed to a flight. Resolution/epoch come from the returned cell/query. Known
zero is very pale green; NoData is gray and never counted as zero. Small positive
values below 0.01 display as less than 0.01. Query coverage can be incomplete even
when the selected cell is known. Original precision stays in expanded attributes.

OSM color view has two choices:

- Feature category uses fixed category colors. With multiple memberships, the
  first enabled category wins: buildings, roads/paths, land use, natural features.
  Hiding one can reveal another membership of the same object.
- Category cost shows one selected category's independent 0-4 ordinal score:
  very low, low, medium, high, very high. Costs are not added; this is not an
  overall risk surface. Unknown/default/unscored objects are gray/dashed. Dark
  paper-obstruction strokes are explained separately. Blank areas are unassessed.
- OSM cost category enables/selects the category to inspect; it does not change
  route objective. Overview always uses aggregate category colors, with no object
  cost score. Zoom in to inspect individual costs.
- Refresh OSM reloads prepared local display data without acquiring originals.
  Fit study in Base map & references changes extent only.

## Reproducing Part 3 real acceptance

```powershell
npm --prefix frontend run build
backend/.venv/Scripts/python.exe doc/experiments/iteration-013/verify-part3.py --output .cache/iteration013-part3-new
```

Use a new output directory; defaults are isolated ports 8022/5192. Prerequisites
and hidden owned-service lifecycle match Part 2. The driver adds assertions for
actual readable OSM/DIPUL/GHSL facts, native units/epoch, assessment scope, matched
rules and closed raw JSON; it retains selection/cache/source-hash/mobile checks.
Evidence/screenshots stay local and ignored. See
[Part 3 outcome](../../iteration/iteration-013/part3.md) for completed results.

## Departure and automatic arrival (Part 4)

Enter Departure time in Europe/Berlin and the existing 25-35 m/s cruise speed.
There is no editable flight end time. Before a successful current route, Estimated
arrival shows Awaiting route. On success it shows actual verified route length /
speed, cruise duration and local arrival with the resulting offset, plus the
containing assessed interval. Computation time is separate. Cruise only excludes
takeoff/landing/wind/dynamics. Edits, failed planning and late responses cannot
restore an old arrival/route/export.

Enabled layers initially show a clearly marked provisional inspection interval,
seeded by actual-endpoint metric straight-line duration. This is not a route ETA.
After success they refresh automatically using the returned assessed interval;
old preview findings disappear while that final result loads. Same-identity
visibility toggles still use cached collections. A solve waits for already-running
preview preparation; valid queued previews are suspended while it runs. The first
preview, route preparation and final-layer preparation can each remain substantial.

Source preparation is reused only within one automatic request. Candidate flight
time can expand the assessment, and the complete route is checked again. A conflict
requires replan; there are at most three candidate passes under one shared search
budget and cooperative 110 s request deadline. The browser timeout stays 120 s.
Explicit timeout/nonconvergence outcomes have no accepted route/ETA. Evidence is
not extended to fit a route: expired/out-of-scope validity is reevaluated. The
evidence editor's blank dates explicitly use its shown provisional/completed
inspection interval; enter the documented broader validity when appropriate.

Actual zero-length cruise is instantaneous after endpoint checks. Its conservative
one-microsecond assessment envelope is explicitly recorded. Fractional timestamps
round upward to microseconds; UI displays milliseconds. UTC elapsed arithmetic
handles midnight/DST; missing/ambiguous UI departure times are rejected.

API callers select `duration_mode: "automatic"`, provide normal start/end catalog
IDs/optional coordinates and omit `scenario.mission_end`. The same mode on
`study/layers/constraints` requests a provisional preview. Route responses return
`timing.estimated_interval`, `timing.assessed_interval`, exact numeric cruise time
and the pass audit. Mission end is the estimated arrival; restriction/provenance
scope explicitly uses the containing assessed interval. UI and API exports retain
both. Historical `duration_mode: "explicit"` (also the default) keeps mandatory
offset-aware start/end and unchanged explicit CLI/API semantics.

## Reproducing Part 4 integrated acceptance

```powershell
npm --prefix frontend run build
backend/.venv/Scripts/python.exe doc/experiments/iteration-013/verify-part4.py --output .cache/iteration013-part4-new
```

Use a new directory; isolated hidden services default to 8024/5194. Prerequisites
and owned-service cleanup match earlier campaigns. The driver includes actual
category/cost display, selection/cards/diagnostics/mobile, provisional conservative
layers and failure, exact-endpoint automatic research routing, explicit-baseline
geometry/cost comparison, final assessed overlays, ten cached visibility cycles,
matching export and stale-time invalidation. It records source/application hashes
and separate preparation/route timings; it never acquires originals or edits a
private profile. No map tiles are needed. Evidence stays local/ignored. See
[Part 4 status](../../iteration/iteration-013/part4.md) and
[iteration outcome](../../iteration/iteration-013/outcome.md).

## Reproducing real acceptance

Use the locked installed backend environment, installed Node/Chrome, local
Hannover study/terrain and existing prepared OSM display. Build first:

```powershell
npm --prefix frontend run build
backend/.venv/Scripts/python.exe doc/experiments/iteration-013/verify-part1.py --output .cache/iteration013-part1-new
```

The output directory must not exist. Ports default to 8018/5188; use `--api-port`
and `--ui-port` for other free ports. The wrapper checks availability, launches
hidden isolated production-preview/backend services, and stops only its own
process trees. It reuses the established lifecycle helpers from Iteration 012.
On Windows, run outside socket/native-handle sandbox restrictions.

The browser checks eight sites, removed controls, automatic conservative loading,
ten zero-request cache cycles, GHSL cache reuse, exact-coordinate bounds/focus,
one historical research route/export, mobile width and source hashes. It records
implementation hashes, response sizes, requests, timings and screenshots locally.
No acquisition or permission profile modification is performed. Street tiles
are blocked, proving saved layers work independently of the online background.

Browser checks use the real historical scenario 2026-10-07 10:00-10:15
Europe/Berlin, 100 m AGL, 30 m/s and the existing explicit research assumptions.
Research success is separate from conservative endpoint feasibility.

Detailed evidence stays local and is excluded from Git. See
[Part 1 outcome](../../iteration/iteration-013/part1.md) for completed checks and
actual delivery status rather than treating an interrupted directory as a pass.
