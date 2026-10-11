# NHN + AGL comparison with MSL zone limits

User-authorized Iteration 010 supplement on 2026-10-11; Issue #88.
Rules version `regional-restrictions-v3`. Original source datums and terrain files
are preserved. This feature supplies an explicit engineering comparison rather
than a verified conversion between height datums.

## Meaning and formula

AGL is height above the local ground; MSL is height relative to mean sea level.
LGLN DGM terrain is recorded in DHHN2016/NHN. Adding 100 m AGL to an NHN ground
height yields a height relative to the NHN frame, not automatically verified MSL.
The user-requested approximation explicitly uses:

```text
aircraft comparison lower = minimum ground NHN + AGL + offset - uncertainty
aircraft comparison upper = maximum ground NHN + AGL + offset + uncertainty
```

The offset means assumed MSL minus NHN, in metres. UI defaults are offset 0 m and
uncertainty 0 m; these express the requested approximation, not certified accuracy.
Uncertainty expands the comparison interval symmetrically. Configure bounds only
with an understood basis. Ground bounds cover the complete query/safety envelope;
the regional planner subdivides long motions into bounded complete segments.

## Policies and controls

- Regional conservative/research UI enables **Compare MSL zones using NHN + AGL
  (engineering assumption)** by default for this authorized supplement. Uncheck it
  to retain source-reference-only behavior. Set **NHN to MSL offset (m)** and
  **NHN to MSL uncertainty (m)** explicitly; changes invalidate prior results/layers.
- API/CLI scenario fields: `vertical_reference_policy: nhn_as_msl_assumption`,
  `nhn_msl_offset_m`, `nhn_msl_uncertainty_m`. Without the policy field, the API/core
  keeps source-reference-only behavior; this is not a global source-data relabeling.
- Strict mode never uses the approximate NHN/MSL policy. Compatible verified source
  references are still required and global coverage remains independently unresolved.
- Known terrain with an unrecognized datum, missing tiles, NoData and resource limits
  remain unresolved. Unknown support cannot be bypassed by the approximation.
- Full comparison outside the zone's supported altitude limits makes that zone
  inapplicable under the declared engineering assumption. Equality counts as overlap.
  Overlap only establishes a potential altitude conflict; it does not prove legal
  prohibition or satisfy operating conditions/permissions.
- Independently active reviewed MSL prohibitions remain blocked when they overlap
  the compatible comparison interval. A generic or stale allowance cannot bypass them.

Diagnostics/export carry original ground bounds/datum, offset, uncertainty, aircraft
comparison bounds, converted source MSL limits, relation and engineering quality.
The result shows numeric endpoint comparisons. Whole-zone map classification can
remain unresolved when complete footprint terrain exceeds the bounded query limit,
even though a particular endpoint/motion has known support; inspect those query
comparisons separately.

## Real primary-pair evidence

100 m AGL, offset/uncertainty 0 m, original Hannover sources and complete terrain;
historical 2026-10-07 10:00–10:15 +02:00 engineering scenario. Control zone
`dipul:kontrollzonen/kontrollzonen.57` has original limits 510.826788–2500 ft MSL,
approximately 155.700–762.000 m MSL.

| Query | Native ground NHN (m) | Aircraft comparison (m) | Height relation |
|---|---:|---:|---|
| rheuma-podbi origin | 56.747 | 156.747 | overlap |
| MHH destination | 57.035 | 157.035 | overlap |
| Complete direct segment bounding window | 52.899–60.694 | 152.899–160.694 | overlap |

Under this approximation both endpoints and the complete direct-motion interval
overlap the control-zone altitude range. The zone remains applicability-unresolved
without assessed conditions/permission, and conservative mode still excludes it.
Other residential/hospital/aerodrome constraints remain independent.

Nine strict/conservative/research point/motion checks retain original NHN terrain
and numeric assumptions. Reproduce into a fresh output:

```powershell
backend/.venv/Scripts/python.exe doc/experiments/iteration-010/verify-nhn-agl.py --output .cache/nhn-check-new.json
```

Retained evidence: `.cache/iteration010-nhn-real-evidence.json` (local-only).
Tests cover whole-motion height variation, lower/upper boundaries, offset and
uncertainty, missing support, strict behavior, original-data preservation and
reviewed prohibitions.

Official source for the DGM vertical frame:
[LGLN DGM product information](https://www.lgln.niedersachsen.de/download/122447/Produktinformation_DGM.pdf).
The specific DIPUL floor/ceiling/reference come from retained original WFS fields;
neither this note nor the approximation establishes a verified datum transformation.
