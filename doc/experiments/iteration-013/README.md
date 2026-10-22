# Iteration 013 Part 1 - Regional controls and cached overlays

Scope: Hannover regional UI. Parts 2-4 are separate planned work. Original data,
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
inputs. Part 1 still uses the existing **Scenario start and Scenario end** fields;
departure-only input and automatic arrival belong to Part 4. Until inputs are
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
bounded OSM display and its readiness checks remain in place. Source details and
raw scenario popups remain the old behavior until Parts 2-3.

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
