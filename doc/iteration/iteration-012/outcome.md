# Iteration 012 Part 4 - Real-data acceptance and delivery

Date: 2026-10-22 (Europe/Berlin).
Tracking: assigned [Issue #110](https://github.com/Hunter3304/uas-mission-planner/issues/110)
in verified Milestone 11, created before `feature/110-osm-real-acceptance` from
`iteration/012` at `aba6a4e`. The user requested project review followed by Part 4
completion if no blocking problem was found. Parts 1-3 remain delivered through
PRs #105, #107 and #109. Part 4 is delivered to `iteration/012` through
[PR #111](https://github.com/Hunter3304/uas-mission-planner/pull/111) at `db7427f`.
Independent main integration remains pending.
Part 4 implementation and full local real-data acceptance are complete; the final
harness exits successfully with `browser_passed: true` / `passed: true`.

## Review and acceptance fix

Repository state matched the handoff, and the starting worktree was clean. The
existing bounded display/source/classification implementation passed regression
and fresh independent real-source checks. Full Hannover source reads remain
guarded; source costs and planner semantics remain independent of map styling.

The acceptance campaign found an initial-view bottleneck: `RegionalRouting`
requested `/study`, whose complete inspection hashes all retained inputs and
loads the regional GeoDataFrame/population data. An OSM overview could finish
while the eight site markers were still absent. This was an outstanding catalog
read from the plan's metadata-read audit, not a viewport-query failure.

The map now requests `/study?catalog_only=true`: bounded manifest/configuration
validation, saved locations/bounds and attribution only. The response explicitly
reports `verified: false` and `validated_catalog_metadata_only`; it never claims
source verification. The default `/study`, source layers and route planning keep
their complete checks. There is no new source acquisition or planning shortcut.
A regression verifies the catalog succeeds without source payloads while full
inspection still fails, malformed/oversized catalogs fail clearly, and the
frontend never requests full study inspection just to draw labels.

## Reproducible evidence

Use the [operation and reproduction guide](../../experiments/iteration-012/README.md).
Tracked `verify-part4.py` starts hidden isolated current-code services and samples
actual Windows process trees; `verify-part4.mjs` drives the built production
frontend through installed Chrome. Detailed originals, caches, measurements,
screenshots and displayed-route exports stay local, excluded from Git.

- Final full-stack campaign: `.cache/iteration012-part4-final/`.
- Fresh independent spatial/classification verification:
  `.cache/iteration012-part4-independent-real/`.
- Diagnostic runs in `iteration012-part4-real-v1/v2/v3` are superseded. The first
  two exposed harness setup/readiness issues; v3 was intentionally stopped after
  successful off/on warm-ups to run final regressions before the complete campaign.
  No diagnostic run is counted as a completed acceptance pass.

The retained source is `hannover-part1-v4`: 326,334 objects, 326,311 drawable,
13 invalid and 10 unsupported originals retained with diagnostics; the exact
411.74 km² Hannover/Lehrte bounds, 5,000 m margin and eight sites are unchanged.
OSM source SHA-256 is
`6678ed0b55cb58dbfc23b570dda5474d42da78f984563cae910cde673e65e8a6`.
Display schema 2 uses `ramke-building-tags-v1` with zero geometry simplification.
Raw-byte metadata/rule hashes and canonical cache-identity hashes are recorded
separately; those different representations must not be confused.

Measurement host: Windows 11 build 26200, AMD Ryzen 5 5600 (6 cores / 12 logical
CPUs), 34,282,184,704 bytes RAM, Python 3.13.13, Node 24.14.1 and installed Chrome
155.0.8059.84. Desktop is 1440×1000; mobile is 390×844. Street tile requests are
blocked and the street basemap is disabled. New processes and a fresh preparation
cache separate application-cold work from warm queries; the OS disk cache is
not flushed. No other verification suites run during final measurement.

## Correctness and compatibility

Fresh independent verification checks the same 20 fixed spatial windows used by
the TCP campaign against original GDAL/Pyogrio selection, 80 category-cost
responses against the existing demo classifier, 221 original-object details and
all 23 diagnostic originals. All agree; ASGI cost-query p95 is 0.07049 s and max
0.12500 s. These are separate from TCP/browser timings below. Source bytes remain
unchanged.

The full-stack campaign checks full-study overview/eight sites, dense central
Hannover/MHH/Podbi/Lehrte/boundary views, four independent category toggles and all
four cost categories, original tags, rapid obsolete views, bounded cache/layer
state and desktop/mobile layout. Braunschweig retains its 31,496 originals,
four category costs and independent population/DIPUL/terrain inspection. OFM
compatibility and layer/export behavior also pass the separate real-stack suite.

The route case is the explicit historical research scenario from 2026-10-07
10:00–10:15 Europe/Berlin, rheuma-podbi → mhh, A*, weighted risk 0.9 / distance 0.1,
250 m grid, 100 m AGL, 30 m/s, background score 0, derived building geometry,
30 m missing-height estimate and the existing NHN/MSL engineering assumption.
It does not imply present flight permission. OSM is switched off/on without
changing that request; both states get a warm-up, followed by three alternating
measured runs each. Source preparation remains part of every actual route request
and is reported separately from search. Geometry, numeric costs, mission, endpoint
diagnostics, assumptions and restriction decisions must be identical. Every
displayed export must match the returned geometry and exact catalog endpoints.
The conservative request must still return `invalid_endpoint` and no geometry.

The six measured route runs are:

| OSM state | Wall time (s) | Source preparation (s) | Search (s) |
|---|---:|---:|---:|
| Off 1 | 51.9656 | 41.0950 | 0.6479 |
| On 1 | 52.0228 | 41.1946 | 0.6737 |
| On 2 | 51.6950 | 40.4046 | 0.6389 |
| Off 2 | 52.2479 | 41.4724 | 0.6340 |
| Off 3 | 51.9728 | 41.1523 | 0.6385 |
| On 3 | 51.8365 | 40.9097 | 0.6338 |

Median off/on is **51.9728 / 51.8365 s**, or **−0.2623%** observed overhead,
passing the <=20% gate. This small negative difference is run variation, not an
OSM speedup claim. Warm-ups are 51.7658 s off and 52.3108 s on, excluded from the
comparison; every request still performs full regional source preparation.
All eight runs have the same comparison digest
`9d833eea22e3fefb9052dc476b08acb39539372f0fcab83772da7b34510cfb5b`:
length **3,715.5915279316932 m**, risk-length **1,202.1487395414197** and objective
**1,453.493018380447**, with the exact catalog endpoints. Route updates issue
zero OSM requests and preserve map position. No frontend timeout occurs.

## Display latency and bounded retained state

Adopted warm gates remain the plan's 2 s API p95, 3 s browser p95 and <=20% median
route overhead. All three pass without changing those thresholds.

| Measurement | Observed |
|---|---:|
| Fresh cache command, process wall time | 73.2671 s |
| Preparation work reported inside CLI | 71.901 s |
| Fresh-process TCP summary verification | 0.6024 s |
| First TCP detail after verification | 0.0517 s / 509 objects / 166,890 bytes |
| 20 warm TCP queries, p95 / max | 0.1651 / 0.2725 s |
| Initial complete fitted browser view including sites | 10.9566 s |
| 20 browser views, p95 / max | 0.9803 / 11.0827 s |
| Largest observed OSM response | 1,676,982 bytes |
| Largest returned detail / coordinate count | 5,000 / 36,165 |
| Largest serialized nearby cache during 50 cycles | 2,884,625 bytes / four entries |
| Sampled uncollected JS heap peak during 50 cycles | 49,265,628 bytes |

Every successful collection is checked against the adopted byte/object/coordinate
ceilings. Dense views that hit the 5,000-object ceiling are explicitly incomplete
and replaced by labelled aggregate grids; no partial collection becomes a complete
individual-object display. The 1,580-cell initial overview remains visible with
street tiles disabled.

The final 20-view sequence has settled-view-to-painted p95 **0.9803 s**, below the
3 s target. The maximum is **11.0827 s**, at the first MHH zoom-17 transition;
the other 19 views are at most 0.9803 s. This outlier is retained in the result,
not removed as a warm-up. Passing the percentile gate does not claim every view
finishes within three seconds. A superseded initial overview request also
returned an explicit 503; the subsequent fitted-view request succeeded. Obsolete
work did not replace the current view or leave the display in an error state.

All 50 settled cycles finish with zero outstanding OSM browser requests. The
five identical boundary-overview checkpoints have **42 live map layers / 39
render paths / one Canvas**, eight site markers, and identical map-handler
counts. The LRU remains within four entries / 8 MiB serialized JSON. At these
checkpoints it holds **1,629,098 bytes**. The repeated-state measurements cover
the original 1,580-cell overview and dense detail/fallback views without
accumulating layers or listeners.

Retained JavaScript heap after explicit garbage collection at cycles 10/20/30/40/50
is **7,940,400 / 8,047,328 / 8,120,992 / 8,143,612 / 8,179,840 bytes**: +3.02%
between the first and last identical checkpoints, within the harness's 20%
investigation trigger. All five retained checkpoints have **1,231 DOM nodes /
458 JavaScript event listeners**. Natural uncollected heap peaks are reported
separately in the final evidence and must not be substituted with these GC values.

The final full-stack run lasts 645.69 s. Representative sampled process-tree peaks
are recorded below in bytes (working set / private committed memory):

| Phase/process | Working set | Private |
|---|---:|---:|
| Fresh display preparation | 107,044,864 | 440,692,736 |
| Warm TCP backend | 138,694,656 | 465,829,888 |
| Initial browser loading, backend | 1,196,285,952 | 1,550,700,544 |
| 50 display cycles, backend | 287,600,640 | 612,618,240 |
| Route comparison, backend | 1,433,518,080 | 1,794,424,832 |
| Mobile/Braunschweig, backend | 1,461,288,960 | 1,877,790,720 |
| 50 display cycles, Node + Chrome tree | 949,116,928 | 1,240,350,720 |
| Mobile/Braunschweig, Node + Chrome tree | 2,308,030,464 | 2,298,474,496 |

The fresh preparation OS working-set peak (sum including the small venv launcher)
is 107,077,632 bytes. Whole-run backend working-set peak is 1,461,686,272 bytes;
Node + Chrome process-tree summed lifetime working-set peaks are 2,391,269,376
bytes and may not be simultaneous. These figures expose the heavier initial
startup, planner and legacy full Braunschweig analysis, rather than presenting
the display's serialized-cache cap as a process-memory guarantee. Initial fit
still takes about 11 s and the first detail transition is slow; these are retained
cold/startup limits despite the successful warm percentile gates.

## Validation and delivery state

- Final backend regression: **314 passed / one existing Windows permission skip**,
  104.40 s. Ruff lint and format pass, including the new catalog regression.
- Frontend ESLint, TypeScript and production build pass. All **22 mocked browser
  checks** pass; the five OSM cases also pass after adding the catalog-request
  assertion. All **14 real-stack smoke checks** pass in 35.5 s.
- Windows sandbox execution cannot exercise native OMPL reliably (invalid-handle
  termination) or TestClient sockets; the successful full suites run in isolated
  host processes with the installed environment. This is not a skipped OMPL gate.
- Existing Starlette TestClient and Rasterio deprecation warnings remain nonfatal.
- [Checks run 39766913176](https://github.com/Hunter3304/uas-mission-planner/actions/runs/39766913176)
  explicitly completed Linux Python, Windows Python and frontend successfully
  on reviewed head `af80714143c482267f80cab2df481e0f1a4948a3` before PR #111
  merged at `db7427f28b9c017397acd0b882a416fb61cf7d7c`. Issue #110 is explicitly
  closed as completed. Local iteration synchronized; feature ancestry, expected-
  head remote deletion, local deletion, fetch/prune, branch -a and ls-remote
  verified cleanup. Main and historical iteration references remain. Independent
  iteration-to-main CI/integration remain pending; all detailed evidence is local.
- The final browser completes without page errors or horizontal mobile overflow;
  real Braunschweig start/end population/terrain inspection and DIPUL/GHSL
  switches succeed. The conservative route returns `invalid_endpoint` with null
  geometry. Original OSM/study/metadata/rule byte hashes are unchanged. Harness
  services are stopped and their ports are no longer listening.

## Limits retained

Browser timings include debounce, verification, layer construction and two
animation frames, plus automation dispatch overhead. They approximate a settled
viewport becoming painted; they do not instrument physical input-to-photon delay.
JavaScript heap and DOM counters are measured separately from the Node/Chrome
process tree and sampled backend private/working-set memory. Forced-GC retained
checkpoints are separate from natural heap peaks; sampled counters can miss short
private-memory spikes. A stable 50-cycle sequence establishes the observed bound,
not an unlimited-duration memory guarantee.

Display ceilings remain 5,000 objects, 5 MiB and 100,000 coordinates per detail
response, 1,600 overview cells, four nearby cache entries / 8 MiB serialized JSON,
and two active backend display queries. No universal total-process RAM cap was
specified in this iteration. Long route source preparation and the legacy
Braunschweig full-analysis payload remain measured existing costs, not hidden
behind the display's warm latency result. No planner-cache redesign is included.

Strict unresolved-source behavior, conservative endpoint conflicts, unverified
temporary coverage, mission-duration enforcement, expanded acquisition, 3D/flight
phases and OFM integration into route decisions retain their earlier scope/limits.
Original sources, private profiles and user-owned services are preserved.

## Iteration feedback

The four-part delivery addresses the measured source-null expansion and full-map
layer construction separately from classifier semantics: bounded indexed access,
precomputed shared styles/on-demand original details, independent regional layers
and finally measured real-data acceptance. Explicit overview and completeness
states make a dense or limited response reviewable instead of silently incomplete.

The last campaign also exposed how a metadata request can recreate expensive
source materialization outside the primary display path. The catalog-only fix
keeps that path bounded and explicitly scoped. Future performance work should
measure cold imports/catalog startup, repeated route source/model preparation
and the legacy Braunschweig analysis as separate tasks. The current warm display
gates pass without claiming those remaining costs are solved. Keep original
snapshots, independent permission/coverage gates and exact displayed-route exports
as baselines for subsequent work.
