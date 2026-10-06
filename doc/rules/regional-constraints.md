# Regional fixed-altitude constraints and population inspection

Implementation: `backend/src/uas_planner/core/regional.py` (`regional-constraints-v1`).
Scope: Iteration 008 Part 2; no routing algorithm or endpoint relocation is performed.

## Scenario and shared geometry

Each preparation requires an explicit offset-aware interval of at most 24 hours,
matching the declared timezone (Europe/Berlin by default), civil/BOS scenario,
100–120 m AGL and 25–35 m/s cruise speed. BOS alone does not grant an exemption.
The example dated 2026-10-07 is an engineering inspection scenario, not a flight
booking, user-selected schedule, or current permission verification.

All point, full-motion, polyline and endpoint-connector checks use EPSG:25832,
the same study boundary and configurable horizontal clearance. A circumscribed
GEOS buffer contains the requested circular envelope. Boundaries apply to the
whole motion/buffer, not only its endpoints. Touching an obstacle is blocked.
The output keeps exact supplied coordinates; blocked addresses are not moved.

## Traceable rule table

| Input/category | Interpretation and source | Buffer | Unknown policy |
|---|---|---|---|
| Study boundary | Region stored in the checksummed Part 1 study | Common scenario clearance | Leaving supported region is blocked |
| OSM polygon building with explicit height | Fixed-AGL engineering footprint model: `height + vertical_clearance >= agl` blocks; strict equality blocks | Common scenario clearance | Unsupported height syntax is missing height |
| OSM building without height | Default unresolved; optional `building_unknown_height=exclude` conservatively blocks its footprint | Common scenario clearance | Exclusion is an explicit engineering assumption, not legal prohibition |
| Invalid building geometry / GeometryCollection / non-polygon building | Original source IDs and diagnostics retained; no silent repair, inferred footprint or omission from hard validation | No invented extent | Unresolved extent remains global unknown building support, including research mode |
| Invalid non-building geometry | Inspection diagnostic only; no building or legal no-go rule follows from it | None | Retained and reported without inventing a restriction |
| OSM roads, land use and natural features | Not automatically legal restrictions; original tag-cost modules remain independent | None | No legal rule is inferred from tags |
| DIPUL zones referring to §21h | Conditional-zone category based on retained source `legal_ref`; conditions/applicability remain unverified | Original delivered DIPUL footprint plus common clearance; no unverified second statutory buffer | Strict mode unresolved unless vertical nonintersection or explicit evidence-backed assessment applies |
| Other DIPUL zones / missing legal reference | Separate unresolved applicability category | Same original footprint policy | Do not assume universal prohibition or permission |
| Evidence-backed prohibition | Matching source feature signature, evidence, scenario, altitude range and overlapping validity interval | Original footprint and common clearance | Block in both strict and research modes |
| Evidence-backed conditional allowance | Matching source signature, complete validity interval and explicit satisfied-condition evidence | Original footprint and common clearance | Records a supplied scenario assertion; does not establish global completeness |
| DIPUL temporary restrictions / NOTAM coverage | Original advertised-layer snapshot and counts are not mission completeness | Global applicability diagnostic | Always unresolved in strict mode; only explicitly labelled research assumption can bypass |
| DGM1 ground elevation | Native LGLN raster; complete conservative bounding-window minimum/maximum, not a center sample | Entire motion/buffer window | Missing tiles, NoData or pixel-budget exhaustion remain unknown in both modes |

Legal context checked on 2026-10-06: [§21h LuftVO](https://www.gesetze-im-internet.de/luftvo_2015/__21h.html)
and [DIPUL geographic areas](https://www.dipul.de/homepage/de/informationen/geografische-gebiete/).
Their conditions are not a substitute for scenario-specific consent, operational
category, schedules, NOTAM checks or restrictions beyond the saved snapshot.
Hospital and laboratory address conflicts receive no invented takeoff/landing
exemption. In particular, a laboratory tag alone does not establish the protected
laboratory conditions described by the law.

## Vertical and temporal interpretation

Native numeric m/ft AGL limits can prove complete vertical nonintersection;
boundary equality remains overlap. Unknown units/references and inverted limits
remain unresolved. MSL limits require compatible complete terrain bounds. LGLN
DGM1 heights use DHHN2016/NHN, which is not silently equated with an unspecified
DIPUL MSL reference. AGL input never directly compares with an MSL value.

Original zone properties, including time/schedule fields, stay in zone inspection
results. The adapter does not claim to interpret undocumented schedules or infer
their inactivity from a download timestamp. Optional `zone_assessments` are
explicit supplied assertions, scoped to the exact source feature signature,
scenario, altitude interval and validity dates. No assessments ship with the
Hannover example. `conditional_allowed` requires a nonempty list of satisfied
conditions and explicit evidence. A prohibition overlapping any portion of the
scenario blocks. Partial allowance coverage remains unresolved.

The height-footprint model is a fixed-AGL 2D assumption, not proof of roof survey
accuracy, 3D clearance, terrain-following feasibility or vehicle dynamics. Do not
derive measured heights from floor counts. Current numeric building scores remain
soft preferences; high scores alone never create hard restrictions.

## Native terrain resource design

`terrain-fetch` saves separate snapshots without changing Part 1 data. It requests
native 2 km EPSG:25832 tiles, at most 144 tiles per operation and at most three
workers (one by default). Existing transport bounds apply: 150 MiB and a 180 s
cooperative deadline per response. Each original response, WCS capability/
description document, request, timestamp, checksum and requested/actual footprint
is retained. Explicit resume verifies scope and existing receipts; unreceipted
partial files are archived inside the same output directory before a fresh request.
Verified source files are never overwritten. No incomplete
snapshot gets a completion marker. The earlier one-kilometre MHH probe remains
separate evidence, not a full-region terrain claim.

Terrain queries read at most 4,000,000 native pixels. This is a diagnostic resource
bound, not a whole-region grid. Long diagonal motions may exceed their conservative
bounding-window budget and return `resource_limit` rather than a false clearance.
Part 3 must choose bounded subdivision/caching for route preparation explicitly.
Ground windows conservatively include all pixels in each intersecting tile's query
bounding rectangle; off-line holes may therefore yield unknown support. This
policy avoids underestimating elevation with endpoint/center samples.

Units, NHN datum and effective -9999 NoData follow the existing verified
[LGLN DGM specification](https://www.lgln.niedersachsen.de/download/207140/Kundeninformation_1_2024.pdf).
Retain the known WCS metadata discrepancy: DescribeCoverage may report radiance
units and TIFF may omit NoData; no radiance conversion is applied.

## Existing building risk

`RegionalConstraints.risk_model` calls the existing `RiskModel`: approved 0–4
classification, maximum score on polygon overlaps, explicit background policy and
non-polygon source diagnostics remain intact. Weights remain 0.9 risk / 0.1 length.
Unassessed background is not observed zero risk. Invalid/collection building
support prevents risk preparation. Research can explicitly omit non-polygon
buildings from soft scoring with diagnostics; their unbounded hard-obstacle extent
still remains unknown. No GHSL count is added to the objective.

## Population interpretation and visualization

Windowed GHSL queries retain native 100 m ESRI:54009 cells, population units,
2020 estimate/2025 projection metadata, known zeros and NoData. At most 100,000
candidate cells are examined. Returned region/corridor population estimates sum
native counts multiplied by intersected cell fractions, assuming uniform
distribution within each cell. Areas are in the native Mollweide raster plane,
distinct from geodesic/UTM study area. Missing or outside support makes the full
estimate null while observed partial totals remain explicit.

Line/point queries report whole crossed-cell counts separately; these do not mean
people exposed to a flight. Polygon/corridor queries additionally report an
area-weighted estimate. Optional cell GeoJSON preserves original resolution and
can be visualized later in Part 4. The standalone SVG preview displays the complete
aligned source crop, including edge margin: white means known zero, magenta hatch
means missing, and blue uses `log(count + 1)`. It is neither a risk map nor a legal
no-go map. GHSL acquisition/inspection stays independent from route costs.

Model identity includes complete study and terrain manifests, source checksums,
scenario dates/altitude/clearance/policies and classification rules. Objects copy
the supplied scenario to prevent parameter mutation after signature creation.
Source datasets are verified before preparation. No persistent planning cache or
flight-ready experiment schema is introduced in Part 2.
