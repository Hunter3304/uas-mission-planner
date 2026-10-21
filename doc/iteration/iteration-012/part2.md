# Iteration 012 Part 2 - Shared OSM classification and original-object details

Date: 2026-10-21 (Europe/Berlin). User requested Part 1 review, then Part 2 if
no blocking issue was found. Tracking: Milestone 11 / Issue #106, assigned to
Hunter3304 before branch `feature/106-osm-classification-details` was created
from `iteration/012` at `80037e6`. Local implementation and acceptance are complete;
Feature publication and CI-gated integration were explicitly authorized on
2026-10-21 and are pending. Parts 3-4 and main integration
remain outside this Part 2 delivery.

Implementation and local acceptance are committed at `4309115`. Automatic
approval review rejected the attempted push of `feature/106-osm-classification-details`
to `https://github.com/Hunter3304/uas-mission-planner.git`, citing sensitive egress
of private project code and missing explicit authorization for this payload and
destination. The push was not executed or retried. Part 2 has no remote feature
branch/PR/CI/merge yet; Issue #106 remains open. Explicit authorization is needed
to publish this completed Part 2 branch, create its PR and integrate it into
`iteration/012` after successful checks. Earlier recorded Part 1 publication
authorization does not claim to authorize this new payload. The user subsequently
explicitly authorized this Part 2 push, PR and CI-gated merge into `iteration/012`
on 2026-10-21, superseding the publication block. Proceed with the authorized
feature delivery and verified merged-branch cleanup; preserve the iteration branch.

## Part 1 review

Verified clean repository state and merged PR #105 / closed Issue #104 against
GitHub. Focused Part 1/classification regressions: **47 passed**. Re-ran the
retained-source acceptance into `.cache/iteration012-part1-review-host/`:
all 20 complete viewports agreed with independent source selection; API p95
0.169 s, maximum 0.258 s; overview 1,580 cells / 591,227 bytes. Original source
SHA-256 unchanged. No blocking Part 1 defect was found. Local ASGI event-loop
sockets require running the checks outside the restricted sandbox; the initial
restricted runs were stopped, then completed successfully on the host.

## Implemented behavior

- `core/costs.py` exposes the shared primary-layer classifier. Full demo
  explanations and compact display preparation use the same classifier and
  unchanged `cost_rules.json`. Classification remains based on original tags.
- Explicit preparation streams independent category scores into a schema-2
  cache table keyed by object/category. Warm viewport queries use the spatial
  index and primary-key score lookups, with no source-tag scan, full GeoDataFrame
  or repeated classification. Source/rule/schema identity invalidates old products;
  ordinary explicit preparation builds a separate schema-2 generation.
- `/study/osm/features?...&style=cost&cost_category=building` returns only the
  chosen category's compact cost/status/default/obstruction fields. Existing
  category-only response properties remain compact. Object/byte/coordinate/
  candidate/time/concurrency limits are preserved.
- `/study/osm/features/{element_type}/{osm_id}` resolves a stable identity and
  reads original sparse tags/geometry by the source fid primary key. It returns
  full existing per-category explanations and source/rule/geometry diagnostics.
  Invalid polygons and unsupported GeometryCollections remain inspectable without
  repair. Original geometries and planner inputs are unchanged.
- Detail geometry over its byte/coordinate budget is explicitly omitted with
  a reason, while tags/classifications remain available within their own limits.
  Oversized explanation expansion/response returns 413 and a source-export
  instruction. Canonical IDs and styles are checked before expensive reads;
  valid missing objects return 404, unprepared snapshots 409, capacity/time
  failures 503 and invalid/failed verification 422.
- `osmStyles.ts` shares category/cost palettes, gray default/unscored styling,
  dashes and qualified historical obstruction outlines with the existing demo.
  Frontend types distinguish compact scores and original-object detail. Regional
  map wiring and controls are deliberately left to Part 3.

## Overlap and score semantics

Category membership means a non-null original tag, matching the demo. Each
object appears once; the first enabled membership in **building, highway,
landuse, natural** order determines its category color. Hiding a higher-priority
membership exposes the next enabled one. Whole-study category counts overlap.

Cost mode requires its selected category to be enabled and includes objects for
which the existing demo returns an analysis. Absent/null/empty/`no` categories
are not assigned a score. Explicit excluded entries such as `highway=corridor`
remain gray/nonnumeric. Mixed known/unknown values can have a numeric maximum
above 2 but stay gray because `has_default` is true. Costless paper obstruction
flags retain their outline without inventing a numeric score. Costs and flags
never cross category boundaries and do not establish present-day restrictions.

## Real retained Hannover evidence

Final reproducible evidence: `.cache/iteration012-part2-real-final/evidence.json`.
Earlier simultaneous-regression measurements are separate at
`.cache/iteration012-part2-real-v1/`; they are not mixed with the final timings.

| Observation | Final result |
|---|---:|
| Original objects / drawable valid supported objects | 326,334 / 326,311 |
| Explicit schema-2 build timer in manifest | 77.248 s |
| Separate cold source/cache verification | 0.621 s |
| Separate API snapshot verification | 0.616 s |
| Independently selected spatial viewports | 20 |
| Selected-category cost requests agreeing with demo/source | 80 / 80 |
| Warm cost API p95 / maximum | 0.072 s / 0.139 s |
| Maximum tested cost response objects / coordinates | 1,691 / 11,491 |
| Maximum tested cost response | 603,760 bytes |
| Original tag/geometry/full-classification detail checks | 221 |
| Detail request p95 / maximum tested detail bytes | 0.017 s / 9,096 bytes |
| Inspectable geometry diagnostic objects | 23 (13 invalid, 10 unsupported) |

All tested responses respect the adopted limits. GDAL/Pyogrio independently
selects source objects around MHH, Podbi, central Hannover, Lehrte and the study
boundary at four sizes. Expected selected-category IDs/costs use original sparse
tags and the full existing demo classifier. Sampled details retain exact source
geometry and tags and all four independent analyses. SQLite query plans confirm
spatial R-tree access, object/category primary-key cost lookup and source-fid
primary-key detail access.

Original OSM SHA-256 remains
`6678ed0b55cb58dbfc23b570dda5474d42da78f984563cae910cde673e65e8a6`.
The preparation timer excludes the final post-publication snapshot verification.
Final whole-process Windows peak/current working set is 163,454,976 / 161,161,216
bytes, private usage 488,689,664 bytes; these include imported geospatial libraries
and validation, not an isolated preparation peak or cache allocation measure.
API timings use in-process ASGI TestClient including serialization, excluding TCP,
browser rendering/memory and route overhead. They are local acceptance evidence,
not an isolated hardware benchmark or Part 3/4 browser acceptance.

## Validation and remaining work

- Full local backend: **313 passed / one existing Windows permission skip**,
  112.89 s. Final focused Part 2 checks: **14 passed**, including mixed/list/
  semicolon/alias/default/excluded/costless flags, sparse tags, invalid/unsupported
  originals, explicit detail limits, ID/style errors, schema invalidation and
  source changes during detail reads. Existing planner and classifier tests pass.
- Ruff lint/format and frontend lint/TypeScript/production build pass.
- **17 frontend tests** pass (including three shared-style regressions), plus
  **14 real-stack browser smoke tests** with installed Chrome. Existing demo
  category/cost inspection, unknowns/flags, mobile, external layers, OFM and route
  workflows retain their tested behavior. Test services exit cleanly; user-owned
  services were not stopped/restarted.
- Part 3 still connects regional viewport/overview requests, controls, legends,
  request lifecycle and selected-object details. The old regional switch remains
  guarded for Hannover. Part 4 still requires real browser resource/interaction
  and OSM-on route-overhead acceptance and full sprint integration gates.

Operation and reproduction: [API guide](../../experiments/iteration-012/README.md)
and [verify-part2.py](../../experiments/iteration-012/verify-part2.py).
