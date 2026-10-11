# Regional restriction decisions

Rules version `regional-restrictions-v2`; constraint model `regional-constraints-v3`.
The module evaluates a specified interval, AGL altitude and civil/BOS scenario.
It does not infer consent from a layer name, score or task category.

## Source/rule audit

All 31 advertised layers and 324 original features are retained in
`data/hannover-part1-v4`. Every feature has a legal reference and lower altitude
value/unit/reference; only four have upper limits. The retained nonempty
properties contain no validity interval. Raw fields and original geometry remain
unchanged. Source geometry is used as delivered, with only the common configured
engineering clearance; an unverified second statutory buffer is never applied.

The [complete 31-layer and four-endpoint audit](../data-sources/iteration-010-dipul-audit.md)
is reproduced from 63 checksummed original DIPUL files. It distinguishes a zero
classifier prohibition count from an absence of actual restrictions.

| Review topic | Layers | Decision input still required |
|---|---|---|
| Airspace | Airports, aerodromes, control zones, flight-restriction areas | Applicable authorization/clearance, activation, vertical limits and exceptions |
| Infrastructure | Railways, federal roads/motorways, waterways, shipping facilities, power lines | Applicable crossing/clearance rules and documented conditions or consent |
| Nature | Nature reserves, national parks, FFH and bird-protection areas | Applicable protection rules, task conditions and consent/exceptions |
| Residential | Residential properties | Applicable operating conditions and permission evidence |
| Operating hours | Outdoor swimming/bathing facilities | Relevant operating/bathing schedule |
| Temporary notices | Temporary operating restrictions | Original notice, explicit interval, compatible vertical limits and any schedule |
| Facilities | Hospitals, authorities, police/security, military, prisons, industry/energy, laboratories, diplomatic/international premises | Source applicability and relevant operator/authority evidence |

These are review topics, not a complete executable legal rule catalog. In
particular, missing consent is not converted into an asserted legal prohibition.
The current engine automatically evaluates documented temporal/vertical
nonintersection and evidence scope; remaining substantive conditions require a
reviewed assessment. A hospital/laboratory address never supplies that evidence.

## Four decisions

- `prohibited`: a matching evidence-backed prohibition overlaps the mission, or
  a reviewed official notice has overlapping explicit validity and compatible
  noninverted AGL limits, with no unsupported schedule.
  Such an independently active notice cannot be downgraded by a generic, expired,
  changed-source or launch-only allowance. Notice-specific exception authorization
  is not inferred by the current engine.
- `conditional_allowed`: supplied evidence matches source signature, complete
  mission interval, scenario and AGL interval, with listed satisfied conditions.
  Launch/landing-only evidence never permits transit.
- `not_applicable`: reviewed notice validity does not intersect the mission, or
  the complete compatible altitude interval lies outside the zone limits.
- `unresolved`: everything else, including changed signatures, expired/partial
  allowance, unknown datum, absent evidence or unsupported schedule.

Intervals are offset-aware and use half-open time boundaries. Altitude equality
counts as overlap. AGL and MSL are not directly compared; NHN is not treated as MSL.
Mixed units are converted only when documented. No known obstacle is downgraded by
changing planning mode. All point, motion, connector and final polyline checks use
the same engine; touching an excluded footprint is blocked.

## Policies and coverage

See [the three planning modes](planning-modes.md) for the comparison table,
defaults, shared checks, real-data behavior and current verification limits.

`strict` stops for unresolved zones and region-wide coverage. `conservative`
excludes unresolved footprints as engineering policy, with separate counts from
confirmed prohibitions. `research` explicitly bypasses unknown zone applicability.
Both latter policies disclose unverified regional coverage. All modes retain
missing-terrain gates and known building constraints. The UI's conservative
default carries the existing explicit derived-geometry/30 m height estimate;
these are engineering assumptions, not building measurements.

Coverage records scope, mission interval, acquisition of the temporary layer,
feature count, reviewed-notice count, oldest source retrieval and age at mission.
Configurable source age is diagnostic, not a completeness guarantee. Neither an
empty WFS response nor a list of reviewed notices resolves global NOTAM coverage.
No complete authenticated NOTAM feed has been established for this project.

Immutable assessment profiles live beside originals in `restriction-profiles/`.
Each revision has a generated ID and a checked content signature. This signature
detects modification; it is not a digital signature from a permitting authority.
Malformed evidence is rejected. Profiles referencing removed source IDs are
rejected; changed source signatures become unresolved and require renewed review.

## Official references

Checked 2026-10-11. The source/rule review uses these primary references; the engine
does not implement every exception or operational requirement described there.

- [DIPUL WFS/WMS](https://www.dipul.de/homepage/de/informationen/geografische-gebiete/wfs-wms/)
- [DIPUL temporary restrictions](https://www.dipul.de/homepage/de/temporaere-betriebseinschraenkungen/)
- [DFS geographic areas and restriction FAQ](https://www.dfs.de/homepage/de/drohnenflug/faq-zum-drohnenflug/)
- [LuftVO §21h](https://www.gesetze-im-internet.de/luftvo_2015/__21h.html)

Original DIPUL material remains local. Derived decision summaries carry attribution
and source identity; publication of modified source geometries is not enabled.
