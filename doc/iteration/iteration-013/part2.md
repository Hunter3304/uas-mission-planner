# Iteration 013 Part 2 - Shared map selection and left inspector

Date: 2026-10-22 (Europe/Berlin). Approved scope:
[Iteration 013 Part 2](../../plan/iteration-013.md#part-2---shared-selection-black-outline-and-left-inspector).
Tracking: assigned [Issue #116](https://github.com/Hunter3304/uas-mission-planner/issues/116)
in verified Milestone 12, created before `feature/116-regional-selection-inspector`
from `iteration/013` at `515ccda`.

Status: implementation and local acceptance complete; feature publication/CI/
merge remain pending. Parts 3-4 and main integration remain deferred.

## Result

- OSM, DIPUL, GHSL and derived scenario overlays share one selected-object state.
  A dedicated noninteractive SVG pane draws a white halo and black actual-geometry
  outline/ring. Source fills are preserved; points, lines, multipart polygons and
  interior holes keep their geometry. No bounding rectangle substitutes for it.
- OSM original details moved from above the map to the existing left sidebar.
  One bounded scroll area, source badge, empty/loading/error/retry states, Clear
  selection and Collapse/Expand object details serve all sources. A short map
  summary offers View details, focusing the inspector without panning or scrolling.
  Rapid reselection leaves one renderer, one outline and one summary.
- Closing a summary or folding a group retains selection. Hiding the owning
  layer, refreshing/changing datasets, changing source identity, losing the
  displayed object or replacing detail with overview clears stale state. Small
  pans retain still-displayed objects. Superseded original requests are aborted;
  source and object identities are checked before applying details.
- Aggregate cells explicitly show counts and Zoom for objects. Diagnostic
  originals show original tags and No drawable geometry, with no invented outline.
  Mobile uses the same inspector as a collapsible fixed bottom sheet, bounded to
  55% of viewport height. No second inspector or horizontal overflow is introduced.

## Regression

- ESLint, TypeScript/production build, experiment JavaScript syntax, Python Ruff
  and `git diff --check` pass.
- **37 browser tests passed (29.4 s)**, including nine new selection cases:
  outline geometry/hit testing/layout/focus, cross-source replacement and mobile,
  late responses/diagnostics, aggregate/pan/overview, original identity mismatch,
  dataset refresh cleanup, changed display identity before a delayed replacement,
  line geometry and multipart holes. Existing OSM assertions now use the shared
  inspector. Original tags are rendered safely as text.
- **14 real-stack smoke tests passed (35.8 s)**, covering small-area workflows,
  native routing, controls, OFM, downloads and exports. Backend application code,
  contracts and planner semantics are unchanged in this Part. Part 1's 316 Python
  passes / one existing Windows skip are historical baseline, not a new run.

## Real Hannover acceptance

Final source-hashed campaign **`.cache/iteration013-part2-final-v2/` passes**:

- Current byte hashes match all seven measured application files. Ten OSM
  selection replacements retain one outline/renderer/summary; map vertical
  displacement is **0 px**. Folding the OSM group adds no source/detail requests.
- Actual original `way/49499709` and alternate `way/72340862` load in the left
  inspector. Diagnostic `relation/49267` loads original tags, Drawable: false and
  No drawable geometry, with zero outline paths. Aggregate inspection/zoom passes.
- DIPUL residential object `dipul:wohngrundstuecke/wohngrundstuecke.1398` and GHSL
  cell `47:112` share the same inspector. Initial scenario preparation takes
  **85.289 s**, with **one** scenario and **one** population request. GHSL
  visibility reuses its cache; no route request occurs. The existing preparation
  cost/payload is unchanged; this Part makes no speedup claim.
- Desktop OSM/DIPUL/GHSL and 390 x 844 mobile expanded/collapsed screenshots were
  visually checked. No horizontal overflow, duplicate sheet or browser error.
  Owned services stopped, as recorded in services.json.
- Original OSM SHA-256 before/after remains
  `6678ed0b55cb58dbfc23b570dda5474d42da78f984563cae910cde673e65e8a6`;
  study.json remains
  `6b8a4cfadcc11395d186ee03d0d5a1da237697a624ee6f5c806f2a1e66e0898e`.

The earlier exploratory `.cache/iteration013-part2-real-v1/` passed but predates
the final display-identity guard. First final attempt
`.cache/iteration013-part2-final/` encountered the existing bounded-query fallback;
its driver waited for detail instead of zooming further and failed. It is retained
as diagnostic evidence with owned services stopped. The driver now allows up to
two further zooms without increasing query budgets; final-v2 needed zero. Only
the completed, matching final-v2 campaign is final acceptance.

## Scope and delivery limits

The current page/session cache from Part 1 and bounded OSM requests remain intact.
Selecting OSM originals remains an on-demand request; this is not a persistent
original-details cache. Closing/collapsing details does not change layer loading.
Existing full scenario payload/preparation cost is unchanged. No source data,
private profile, permission claim or route objective is modified.

Richer source-specific detail cards/help, color-mode explanations and departure/
arrival calculation remain Parts 3-4. No main merge is included. Feature PR,
exact-head Linux/Windows/frontend CI, merge into `iteration/013`, explicit Issue
closure and verified merged-feature cleanup remain delivery gates until recorded.
