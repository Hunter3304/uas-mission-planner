# Iteration 013 Part 4 - Departure-only planning and assessed cruise arrival

Date: 2026-10-22 (Europe/Berlin). Approved scope:
[Iteration 013 Part 4](../../plan/iteration-013.md#part-4---departure-only-input-and-consistent-estimated-arrival).
Assigned [Issue #120](https://github.com/Hunter3304/uas-mission-planner/issues/120)
in verified open Milestone 12 precedes `feature/120-automatic-flight-interval`,
created from iteration/013 at `289c60c`.

Status: implementation, local regression and integrated Hannover acceptance
complete; feature delivery gates are pending. Full iteration/main integration requires
its independent final-head CI gate.

## Result and temporal contract

The Hannover form takes Departure time in Europe/Berlin, with no editable flight
end. A successful current route shows actual verified metric length / entered
cruise speed, duration, local arrival with resulting UTC offset and its containing
assessed interval. Before success or after failure/edit it shows Awaiting route.
Planning computation time is separately labelled. Takeoff, landing, wind and
dynamics are excluded. Endpoints still have their own saved-site/exact-coordinate
section and bounds; unrelated pages keep their existing input contracts.

Automatic API/core mode is explicit: `duration_mode: automatic`, scenario departure
only, no mission_end. Existing `explicit` mode (also the default) keeps historical
start/end semantics and CLI reproduction. Invalid speed/time/offset/extra end are
rejected. A provisional scenario uses EPSG:25832 straight-line distance between
actual catalog/override endpoints divided by speed. It is never called a route ETA.
The small catalog read does not replace full source verification; actual verified
catalog endpoints are checked after preparation and may only broaden the seed.

One request-local RegionalPlanner prepares original sources and indices once.
All non-time controls, geometry, classifications, profiles and risk inputs remain
fixed. If candidate L/v exceeds the assessed end, expand the interval, reevaluate
temporal zone decisions/coverage and check the complete candidate. Safe candidates
can be accepted without a second search. A conflicting candidate triggers a new
search over the broader interval; assessed intervals never shrink. Rechecks cover
the whole path/clearance envelope, not only endpoints or departure applicability.
Evidence/profile expiry and notices becoming active during flight use the complete
interval. Existing strict/conservative/research meanings are preserved.

At most three candidate passes share the requested search budget. Graph/native
searches and source/grid work also observe a cooperative **110 s request deadline**,
below the existing **120 s browser request timeout**, which is unchanged. Checks
are cooperative around bounded operations; native/source I/O is not forcibly
interrupted mid-call. Resource exhaustion, nonconvergence and failed revalidation
produce an explicit unsuccessful result without accepted geometry/length/cruise
time/ETA. Native finite-budget timeout is legitimate, never assumed success.

Elapsed time is added in UTC, then formatted in the declared zone. Timestamps
round upward to microseconds to contain fractional cruise time; the exact numeric
L/v remains available. The UI shows milliseconds/three-decimal duration. Midnight
and DST crossings keep correct resulting offsets. Ambiguous/nonexistent UI wall
times are rejected; explicit offset-bearing API instants must match their zone.
For zero-length routes, actual cruise time is zero and arrival equals departure.
Endpoint checking uses an explicitly recorded conservative one-microsecond
assessment window, rather than fabricating a nonzero flight duration.

## Consistent UI, sources and exports

- Automatic scenario-layer preview uses the same seed helper and is marked
  Provisional preview with its inspection interval. It is not final route evidence.
- Routing waits for already-running preview preparation; the busy state suppresses
  queued previews. This avoids overlapping expensive browser jobs without raising
  request timeouts or changing backend source preparation semantics.
- On success, enabled layers refresh automatically using the returned assessed
  interval. Old preview data cannot appear under that final identity. Hidden
  layers stay hidden and cached response collections remain reusable on toggles.
- Returned timing separates estimated_interval from assessed_interval. Mission
  metadata ends at actual estimated arrival; restriction report, provenance and
  final layer scope use the explicitly containing assessment interval. Source/risk
  provenance and prepared identities are recomputed consistently after expansion.
- The client checks L/v, departure, arrival, containment and mission consistency
  before showing success. Edits/aborts/late responses cannot restore old ETA.
- Evidence editor blank validity fields explicitly use the provisional/completed
  inspection interval. Documented validity can be entered independently. Preview
  validity may expire during a longer flight; it is never silently extended.
- UI export serializes the current accepted result without another solve. Core/
  API GeoJSON metadata keeps the same actual/assessed timing. Unsuccessful exports
  contain no accepted route feature. Existing explicit exports remain unchanged.

## Regression

- Final full backend: **338 passes / one existing Windows permission skip**,
  **99.57 s**. Local final log `.cache/iteration013-part4-python-final.log`.
  Includes 22 new tests: 3,600 m / 30 m/s, fractional microseconds, midnight/DST,
  invalid inputs, actual detour expansion with one preparation, during-flight
  notice activation and evidence expiry, zero-length endpoint validation, bounded
  nonconvergence/deadline/budget reuse, source identity/export, graph/native/API
  and explicit compatibility, and explicitly provisional preview scope.
- Final browser regression: **55 passes**, **36.7 s**; local final log
  `.cache/iteration013-part4-browser-final.log`. Nine new cases cover departure-only
  requests, final overlay promotion/export/invalidation, UTC transitions, zero/
  fractional duration, invalid returned scope, late results and preview waiting.
  Existing map/detail/profile fixtures now use departure-only automatic contracts.
- Real-stack smoke: **14 passes**, **33.4 s**. Other pages/native routing/export,
  OFM and cost controls remain usable. Ruff/format, ESLint/TypeScript/production
  build, experiment syntax and diff checks pass.

## Real acceptance and delivery

Integrated campaign `.cache/iteration013-part4-real-v1/` passes. All 21 measured
application byte hashes match current files. Original OSM/study hashes are
unchanged and owned services stopped. Desktop/mobile screenshots were inspected.
Ten selection cycles retain one outline/summary and zero map shift. Ten initial
and ten final visibility cycles add no requests. There are two scenario loads,
one GHSL load, two browser route requests and one independent explicit baseline;
no browser errors. Both endpoint modes, bounds, readable cards, final assessment
scope, current-result export and edit invalidation pass.

| Actual operation | Time | Result |
| --- | ---: | --- |
| Initial provisional layers | 74.268 s | Straight-line seed ending 10:01:19.816270 +02:00 |
| Conservative automatic route | 40.246 s | invalid_endpoint; no ETA |
| Research automatic route | 50.185 s | Success; complete expanded interval rechecked |
| Independent explicit baseline | 50.595 s | Identical geometry, length, objective and source signature |
| Final assessed layers | 74.498 s | Scope ends at returned assessed arrival |

Successful length is 3715.5915279316932 m, speed 30 m/s, cruise time
123.85305093105644 s, arrival 2026-10-07T10:02:03.853051+02:00. One source
preparation and one candidate search suffice: the expanded complete interval
passes without another search. Export has identical geometry/mission/timing.
Existing
large scenario payload/preparation costs remain; this is not a broad cache or
memory redesign. Originals/private profiles and user services are preserved.

Feature publication/CI, iteration merge, explicit Issue closure and verified
merged-feature cleanup remain pending. Full iteration/main integration requires
separate complete checks; no main delivery is claimed here.
