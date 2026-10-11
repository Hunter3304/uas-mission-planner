# Regional restrictions and conservative avoidance

Approved by the user on 2026-10-11. Milestone 9; integration branch `iteration/010`
from main `89afe54`. Follow HANDOFF.md and retain all original snapshots.

## Outcome

For a declared Hannover mission, classify zones as prohibited, conditional allowed,
not applicable or unresolved, with traceable evidence. A*, Dijkstra and native
ABIT* share full-motion checks. Default conservative avoidance excludes unresolved
zone footprints without claiming they are confirmed legal prohibitions.

## Deliveries

1. Audit 31 layers/324 retained features; publish a source/rule table. Implement
   independent temporal, vertical and evidence-scoped decisions. Persist versioned
   assessment profiles separately from source snapshots; provide import/save/review.
   Default conservative avoidance, explicit strict and research alternatives.
2. Preserve original temporary-restriction responses and referenced official
   notices, timestamps, checksums and scope. Normalize only documented time/height
   fields. Allow reviewed notice import when automated interpretation is unsupported.
   Empty responses never certify NOTAM completeness; report coverage independently.
3. Display evaluated zones, counts, exclusion reasons and coverage separately from
   buildings. Export complete provenance. Invalidate results on scenario/profile
   changes. Verify algorithms, independent geometry, expiration, source changes,
   time/height boundaries and real Hannover endpoint conflicts.

## Contract

- `strict`: unresolved zones and global restriction coverage stop planning.
- `conservative`: unresolved zones are engineering exclusions; global coverage is
  disclosed as unverified. Building/terrain unknowns retain their existing gates;
  optional existing building research assumptions are explicitly recorded.
- `research`: explicit unknown-zone bypass, never bypass a confirmed prohibition.
- All modes retain known obstacles and full boundary/terrain checks.
- Evidence is scoped by source signature, scenario, AGL interval and validity.
  Phase-specific launch/landing permissions cannot grant transit permission.
- Never infer consent from a hospital/laboratory address, BOS, layer name or score.
- Do not create a second statutory buffer around already-delivered DIPUL geometry.
- Missing/unknown data and mismatched vertical references stay unresolved.
- Refresh produces a separate snapshot/profile revision, not edits to originals.

## Acceptance

Three planners reject prohibited crossings (including connector/boundary contact),
route around conservative exclusions or report no path/endpoint conflict. Temporal
nonintersection and compatible vertical nonintersection are reproducible; partial
allowance, expired evidence and changed signatures cannot allow travel. Map/export
counts distinguish confirmed restrictions, policy exclusions and building obstacles.
Retain real Hannover failure evidence, never move addresses or silently relax rules
to obtain success. Run backend, frontend lint/build and browser suites plus native
planner validation and independent final-path geometry checks.

## Scope and limitations

Hannover, fixed-AGL 2D model, existing three algorithms. This iteration does not
automate flight authorization, guarantee complete NOTAM access, convert NHN to MSL,
add nationwide/3D planning, time feasibility or full-region OSM performance fixes.
External feeds requiring unavailable access are reported with a concrete gap and a
reviewed-import path, never fabricated coverage. Operational permission remains
separate from an engineering candidate route.

Official references checked 2026-10-11:
- https://www.dfs.de/homepage/de/drohnenflug/faq-zum-drohnenflug/
- https://www.dipul.de/homepage/de/temporaere-betriebseinschraenkungen/
