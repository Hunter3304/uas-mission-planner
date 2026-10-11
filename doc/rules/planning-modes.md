# Regional planning modes

Recorded 2026-10-11 for Iteration 010. Applies to Hannover regional planning with
A*, Dijkstra and native ABIT*. A mode is a constraint-handling policy; it does not
select an algorithm or constitute flight permission.

## Comparison

| Policy | API/CLI value | Confirmed applicable prohibition | Unresolved zone restrictions | Unverified regional coverage |
|---|---|---|---|---|
| Strict verification | `strict` | Exclude | Exclude from traversal; report unresolved input | Stop and report the gap |
| Conservative avoidance (regional UI/CLI default) | `conservative` | Exclude | Route around as engineering policy exclusions | Candidate routing may run; coverage remains explicitly unverified |
| Research assumptions | `research` | Exclude | May traverse under recorded research assumptions | Retain incomplete-verification findings in the result and export |

The underlying regional API/core defaults remain `strict` for backward compatibility.
Clients must pass `planning_mode` explicitly to request another policy. The UI and
regional `study-route` CLI default to `conservative`. Historical small-area
experiment controls have their own strict/research contract; conservative regional
behavior must not be inferred for those endpoints.

## Shared checks

- All three algorithms check exact endpoints, endpoint connectors, complete motion
  segments and the final path. A blocked endpoint stops before search.
- Confirmed applicable prohibitions, known tall buildings, supported-region boundaries
  and required terrain support cannot be bypassed by switching modes.
- Missing terrain remains unresolved in every mode. Unknown building information
  has a separate policy; unknown-zone bypass does not make it measured or complete.
- In the current regional UI, conservative/research modes explicitly use the existing
  derived building geometry and configurable missing-height estimate (default 30 m).
  Uncertain localized extents remain excluded with the configured 20 m geometry
  uncertainty buffer. Strict mode retains original geometry/height uncertainty gates.
- Cost assessment is separate from zone permission. Unknown risk support may still
  prevent weighted routing; `distance` does not bypass hard constraints.
- The user-authorized NHN + AGL engineering comparison is enabled by default in
  the regional conservative/research UI, with explicit offset/uncertainty controls.
  Strict mode does not adopt this assumption; API/core source-reference defaults
  remain unchanged. See [height comparison rules](vertical-references.md).
- Time selectors validate a positive Berlin interval of at most 24 hours. They do
  not certify that cruise duration fits that interval; duration feasibility is deferred.

## Zone decisions and evidence

`prohibited`, `conditional_allowed`, `not_applicable` and `unresolved` describe a
zone's evaluated relationship to the specified mission. They are separate from the
mode. Only conservative policy creates engineering exclusions from unresolved zones.
An exclusion must never be reported as a confirmed legal prohibition.

Evidence is scoped to source identity/signature, validity, scenario and AGL interval.
Expired/partial conditional allowance and changed sources cannot continue to permit
travel. Launch/landing-only records do not grant transit. The current planner applies
transit checks to the complete planned polyline; it does not yet model independent
takeoff/landing flight phases. Saving an assessment is not applying to an authority
or verifying the authenticity of a permit.

Changing scenario time, altitude, profile or mode invalidates displayed results and
scenario layers. Saved profile revisions must be selected explicitly; unsaved drafts
do not affect planning. Reload scenario layers after saving/selecting a revision.

## Current Hannover behavior

Without supplied permission profiles, the retained snapshot has 324 unresolved zone
features and no confirmed prohibited/conditional-allowed decisions. These are not
324 confirmed no-fly zones. For the retained 100 m historical test scenario:

- `strict` cannot search with unresolved restriction/NOTAM completeness. Known
  endpoint obstacles can also produce an earlier `invalid_endpoint` result.
- `conservative` excludes the unknown footprints. Seven of eight catalog sites,
  including MHH, are blocked; the nine tested representative-pair/algorithm cases
  return `invalid_endpoint`. This is expected preflight behavior.
- `research` may produce engineering routes under the declared assumptions, but
  a known prohibition or other hard constraint still blocks travel. A finite ABIT*
  budget does not guarantee success.

`Search 0.00 s` with `invalid_endpoint` means search was never started. Raising the
ABIT* budget or changing algorithms cannot resolve that endpoint conflict.

## Verification and source limitations

Strict mode is not an automatic legal certification service. The current real
regional implementation always retains an unresolved global temporary/NOTAM
coverage finding: no complete authenticated NOTAM feed has been established.
Neither an empty temporary-layer response nor reviewed individual notices proves
complete coverage. Conservative/research success is an engineering candidate result.

The current rule engine automatically checks supported time/height nonintersection
and supplied evidence scope. The 31-layer review table is not a complete executable
catalog of substantive legal conditions and exceptions. Those conditions still need
reviewed evidence; unsupported schedules and vertical datum comparisons stay unknown.

See [restriction rules](restriction-decisions.md),
[operation and acceptance](../iteration/iteration-010/outcome.md), and
[remaining work](../iteration/iteration-010/status.md).
