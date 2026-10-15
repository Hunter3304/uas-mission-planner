# Iteration 010 status and next steps

Closeout reviewed 2026-10-11; remote completion reverified 2026-10-15 against GitHub.
The user explicitly authorized completion and remote delivery on 2026-10-11. Earlier
local-only publication restrictions are history; each remote merge still requires
its successful-CI gate.

## Delivery against the approved plan

| Planned work | Current state | Remaining gap |
|---|---|---|
| Source/rule audit | Complete 31-layer/324-feature inventory, 63 checksum checks and four-feature endpoint audit published | Per-category substantive legal conditions/exceptions remain reviewed inputs, not fully executable legal rules |
| Zone decisions and policies | Supported time/height nonintersection, evidence scope and all three policies implemented | Actual source applicability still needs reviewed evidence where automation is unsupported |
| Persistent assessment/permission workflow | Local immutable profiles, UI review/import/save/export, expiry/signature/phase checks implemented | No real permission profiles supplied; launch/landing records are stored but not a separate flight-phase model |
| Temporary restrictions and coverage | Bounded official WFS/notice originals, receipts, reviewed import and unverified coverage/freshness reports implemented | No exhaustive authenticated NOTAM feed or automated interpretation of all notices/schedules |
| Algorithms, map and exports | Shared full-motion checks, distinct decisions/policy exclusions/buildings, result invalidation and exports implemented | A valid conservative route on the real target missions has not been established |
| Acceptance | Final 255 backend passes / one existing Windows permission skip; 14 mocked browser and 12 real-stack smoke passes; profile/active-notice/15 mode/9 NHN comparison acceptance; shared-backend smoke deadline corrected in #94 | Final #92 CI and merged-main run `38159165262` passed on `633b16e` |
| Publication/integration | #87/#89/#94 feature gates and #90 main gate passed; functional main merge `2163974`; #85/#86/#88/#93 closed and feature cleanup verified | #92 merged at `633b16e`; #91 and Milestone 9 are closed |

Feature integration is complete: #87 at `e4889f8`, #89 at `d453961`, with successful
Linux/Windows/frontend runs `38155429114` and `38157301971`. Issues #85/#86/#88 are
closed and merged feature cleanup verified. The final supplemental implementation
passes 255 backend tests / one existing skip, 14 mocked browser and 12 real-stack
smoke cases. Main delivery retains its own separate gate.

Main delivery is now verified: PR #90 at `2163974`, independent main-PR run
`38157731109` and iteration push run `38157643292` successful. The final
documentation record is tracked by #91. Post-merge comparison smoke timing was
corrected by #94 at `3eca995`, after independent run `38158666846` passed all
three jobs. Final PR #92 includes that correction and has its own main gate.
PR #92 merged at `633b16e`; merged-main run `38159165262` passed. Issue #91
and Milestone 9 are closed. Remaining source/permission evidence is
operational follow-up, not unfinished implementation or remote functional delivery.

The delivered result is a usable conservative-avoidance and evidence workflow.
It must not be described as completed legal verification of all DIPUL areas or
completed operational authorization for the intended missions.

## Completed local closeout and operational follow-up

The scoped functional implementation and local acceptance are complete. Final real
mode acceptance retains nine conservative endpoint conflicts, three strict unresolved
cases and three independently verified primary research routes. Read
[the complete source audit](../../data-sources/iteration-010-dipul-audit.md) and
[the acceptance evidence](outcome.md#validation). Final delivery completed through PR #92 and its successful merged-main gate.

The user subsequently authorized the Issue #88 NHN + AGL engineering comparison
before main integration. It supplies explicit offset/uncertainty and numerical
endpoint/whole-motion diagnostics; strict reference verification remains intact.
At zero offset and 100 m AGL, both primary endpoints overlap the control-zone
MSL band. See [height comparison](../../rules/vertical-references.md). Supplemental
feature CI and separate main integration gates passed before delivery.

The following operational evidence work remains, and does not prevent delivery of
the planned evidence/import/avoidance functionality:

1. Local acceptance of the three documented modes is complete. Retain synthetic
   all-three-algorithm detours/prohibited-wall rejection and real conservative
   endpoint failures as regressions. Research results remain explicitly assumed.
2. The primary pair's four-feature source audit is complete. Begin substantive
   condition/permission review with those retained source records:
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
5. Remote delivery is complete through #87/#89/#94 and final main PR #92.
   Preserve iteration history and the final successful merged-main evidence.

Real permission/source evidence and release approval are independent needs. Neither
successful code tests nor a GitHub merge fills a missing operational permission.

## Deferred work outside this iteration

Full-region OSM payload/rendering/cancellation performance, mission-duration
feasibility, national expansion, 3D/terrain-following planning remain deferred. Iteration 008 Part 5 was separately delivered to main through
PR #96 on 2026-10-15; see its current outcome and HANDOFF. These deferred items
are not prerequisites for merely
documenting or testing the three restriction policies.

See [planning modes](../../rules/planning-modes.md),
[approved plan](../../plan/iteration-010.md) and [outcome](outcome.md).
