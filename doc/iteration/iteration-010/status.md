# Iteration 010 status and next steps

Reviewed 2026-10-11 against the approved plan, local implementation commit `e2813fa`,
test results and retained real-data evidence. This is a status clarification, not
authorization for remote source publication or a new implementation scope.

## Delivery against the approved plan

| Planned work | Current state | Remaining gap |
|---|---|---|
| Source/rule audit | 31 layers and 324 features inspected; review-topic table documented | Per-category substantive legal conditions/exceptions are not fully executable rules |
| Zone decisions and policies | Supported time/height nonintersection, evidence scope and all three policies implemented | Actual source applicability still needs reviewed evidence where automation is unsupported |
| Persistent assessment/permission workflow | Local immutable profiles, UI review/import/save/export, expiry/signature/phase checks implemented | No real permission profiles supplied; launch/landing records are stored but not a separate flight-phase model |
| Temporary restrictions and coverage | Bounded official WFS/notice originals, receipts, reviewed import and unverified coverage/freshness reports implemented | No exhaustive authenticated NOTAM feed or automated interpretation of all notices/schedules |
| Algorithms, map and exports | Shared full-motion checks, distinct decisions/policy exclusions/buildings, result invalidation and exports implemented | A valid conservative route on the real target missions has not been established |
| Acceptance | 240 backend passes / one existing Windows permission skip; 14 mocked browser and 12 real-stack smoke passes; native synthetic independent geometry and nine real conflict cases | User acceptance of the local workflow is ongoing; remote Linux/Windows/frontend CI has not run on this change |
| Publication/integration | Local feature commit exists; Milestone 9 and Issues #85/#86 exist | No code push, PR or main integration; explicit publication approval required after automatic-review rejection |

The delivered result is a usable conservative-avoidance and evidence workflow.
It must not be described as completed legal verification of all DIPUL areas or
completed operational authorization for the intended missions.

## Recommended next sequence

1. Complete local acceptance of the three documented modes. Use synthetic fixtures
   for all-three-algorithm detours and prohibited-wall rejection; retain the real
   conservative endpoint failures. Research results remain explicitly assumed.
2. Audit the primary pair's four unique endpoint-related source features first:
   `dipul:wohngrundstuecke/wohngrundstuecke.1398`,
   `dipul:kontrollzonen/kontrollzonen.57`,
   `dipul:krankenhaeuser/krankenhaeuser.2275`, and
   `dipul:flugplaetze/flugplaetze.106`. The control zone affects both endpoints.
   Record original rule/reference, vertical/time scope, missing conditions and
   required evidence. Do not turn missing evidence into a permission assertion.
3. Where real evidence exists, enter scoped profile records and verify matching,
   expiration and source changes. Recheck endpoints, then attempt the conservative
   route to discover any remaining corridor restrictions. Endpoint allowance alone
   does not clear an entire route; do not move catalog coordinates automatically.
4. Improve source-specific automatic rules only when the needed inputs and official
   semantics are established. Track unsupported schedules, datum compatibility,
   NOTAM access and phase-specific endpoint modeling as explicit work items; these
   require a further agreed implementation scope, not undocumented assumptions.
5. After explicit remote publication approval, push the reviewed changes, create
   PRs and run separate successful-CI gates for feature -> iteration/010 -> main.
   Record merge/issue/cleanup facts only after verification. Keep iteration history.

Real permission/source evidence and release approval are independent needs. Neither
successful code tests nor a GitHub merge fills a missing operational permission.

## Deferred work outside this iteration

Full-region OSM payload/rendering/cancellation performance, mission-duration
feasibility, national expansion, 3D/terrain-following planning and the separate
Iteration 008 Part 5 scope remain deferred. They are not prerequisites for merely
documenting or testing the three restriction policies.

See [planning modes](../../rules/planning-modes.md),
[approved plan](../../plan/iteration-010.md) and [outcome](outcome.md).
