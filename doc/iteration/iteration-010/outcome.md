# Regional restrictions and conservative avoidance

Approved 2026-10-11. Milestone 9, Issues #85/#86; integration branch `iteration/010`
from `89afe54`; feature `feature/85-regional-restrictions`.

Implementation and acceptance are local. Automatic approval rejected remote source
publication before the combined commit/push command ran; no code PR or merge is
claimed. Remote publication and CI-gated integration await explicit user approval.

The UI previously sent empty zone assessments and research routing bypassed all
unknown zone applicability. It now defaults to conservative avoidance: unresolved
zone footprints are excluded without being called confirmed legal prohibitions.
A*, Dijkstra and native ABIT* share full-motion checks. Strict and explicit research
policies remain available. See [decision rules](../../rules/restriction-decisions.md).

The [three-mode contract](../../rules/planning-modes.md) and
[status/next steps](status.md) distinguish implemented functionality from remaining
source/permission evidence and pending remote delivery.

## Operation

Restart the backend and refresh the frontend after loading this implementation.
Select `hannover-part1-v4` and complete terrain `hannover-part2-terrain-v1`. Enter
scenario times in Europe/Berlin and select the intended planning policy. Load
scenario layers to inspect separate prohibited, policy-excluded, conditional and
not-applicable footprints, counts and coverage. Building records are counted
separately. Keep the known problematic full-region OSM overlay off.

Open **Restriction assessments and reviewed notices**. Select an assessed zone,
decision, phase, evidence, AGL interval and validity interval. Blank validity inputs
use the entered scenario interval. Conditional allowance requires explicit satisfied
conditions. Add it to the draft, name the profile and **Save and use profile revision**.
Only saved profiles affect planning; edits to an active saved profile deselect it.
Source/time/height/profile changes invalidate the displayed route and scenario layers.
Review profile evidence before use. A launch-only consent does not permit transit;
complete path checks remain conservative, including at exact catalog endpoints.

Profile export/import uses JSON schema version 1 with `name`, `zone_assessments`
and `notices`. Re-importing a saved profile creates a new checked revision. Source
signatures are supplied by scenario layer reports; do not invent or reuse a signature
from another source feature. `civil`/`BOS` does not itself grant any exemption.

API additions:

- GET/POST `/api/datasets/{id}/study/restriction-profiles`: list/save immutable local
  profiles (POST is a local write, not an external application for permission).
- Existing route/layer POSTs accept `profile_id`. Inline evidence and a saved
  profile cannot be combined. Layer requests accept `planning_mode`.
- Results and displayed exports contain `restriction_report`, coverage, policy
  exclusions, model/rule versions and profile identity. API/core defaults remain
  strict for compatibility; the regional UI/CLI default is conservative.

## Temporary restrictions

Acquire a separate bounded snapshot, without overwriting study originals:

```powershell
backend/.venv/Scripts/python.exe -m uas_planner.cli restrictions-fetch --bounds 9.650495867959657 52.32042221571155 10.068841103123809 52.45032927853548 --output .cache/restrictions-new --notice-url https://www.dipul.de/homepage/de/temporaere-betriebseinschraenkungen/
```

This retains capabilities, schema, WFS pages and requested official notice bytes,
with request/timestamp/checksum receipts and `restrictions.json`. It also generates
`profile-template.json`; any acquired features start **unreviewed** and cannot be
used until their normalization is reviewed. Additional individual official notice
URLs can be supplied (maximum ten). The listing is not an exhaustive NOTAM feed.

Reviewed notice entries need a unique `id`, official HTTPS `official_url`, evidence,
offset-aware `checked_at`, `reviewed: true`, valid WGS84 polygon `geometry` and
`properties`. Canonical `valid_from`/`valid_until` mean reviewed explicit intervals;
altitude uses `lower/upper_limit_altitude`, `_unit` (m/ft), `_alt_ref` (AGL/MSL).
Unsupported schedules remain unresolved. `state: prohibited` can be used only with
reviewed prohibition evidence; the importer cannot grant permission. Preserve
original raw fields in addition to reviewed normalization. Import the reviewed
profile through the UI and save it before planning. New snapshots are not applied
silently, and missing feed access never becomes a coverage certificate.

## Real Hannover findings

The retained 100 m scenario, 2026-10-07 10:00–10:15 +02:00, is reproducible
engineering evidence rather than a current flight schedule. With no permission
profiles, all 324 DIPUL features remain unresolved; confirmed prohibitions and
conditional allowances each count zero. Conservative mode excludes those features.

Seven of eight exact sites are blocked: mhh, henriettenstift, rheuma-lister,
rheuma-podbi, amedes-georg, amedes-schiffgraben and friederikenstift. limbach-lehrte
passes the local point check, while global coverage remains unverified. All three
representative pairs to MHH return `invalid_endpoint` under all three algorithms
(nine cases), with no fabricated path. No address was moved and no research bypass
was applied. Local evidence: `.cache/iteration010-real-evidence.json`.

Fresh official acquisition on 2026-10-11 returned zero temporary features in the
Hannover bounds. Original responses and the listing are retained separately at
`.cache/iteration010-temporary-snapshot/`. This does not establish an absence of
temporary restrictions or complete NOTAM coverage.

## Validation

Final local regression: 240 backend passes / one existing Windows permission skip;
14 mocked browser and 12 real-stack smoke passes with clean exits. Ruff and
frontend lint/TypeScript/production build pass. Final scoped popup/profile checks
also pass, with mobile rendering inspected. Added tests cover evidence expiry,
partial validity, changed source, launch-only scope, time/height equality,
unsupported schedules, unreviewed imports, immutable profile revisions and all
three algorithms. Independent Shapely intersections verify successful synthetic
detours; a full-height prohibited wall never produces successful geometry.

## Limits

Substantive conditions still require reviewed evidence. No real permits are supplied
with this iteration; no authenticated exhaustive NOTAM source is configured.
Strict planning still fails regional completeness checks and may also fail on
building/terrain support. This is a functioning conservative avoidance and evidence
workflow, not automatic flight authorization. Fixed-AGL 2D, NHN/MSL uncertainty,
existing source snapshots and deferred mission-duration/OSM performance work remain.
