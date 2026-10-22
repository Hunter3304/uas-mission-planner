# Iteration 013 Part 3 - Readable source details and color help

Date: 2026-10-22 (Europe/Berlin). Approved scope:
[Iteration 013 Part 3](../../plan/iteration-013.md#part-3---readable-source-details-and-explanations).
Assigned [Issue #118](https://github.com/Hunter3304/uas-mission-planner/issues/118)
in verified open Milestone 12 precedes `feature/118-readable-regional-details`,
created from `iteration/013` at `516ffcb`.

Status: implementation and local/real Hannover acceptance complete; feature
publication/CI/merge remain pending. Part 4 and main integration are deferred.

## Result

- One source-card system retains Part 2's left inspector and mobile sheet. Main
  facts, interpretation and assessment uncertainty show before closed original
  attributes/provenance. Nested objects/arrays render as labelled lists, with
  wrapping for long values. Raw JSON is only a closed Advanced: raw JSON option.
  Source strings render as escaped React/DOM text, never HTML. Derived building
  records with validated OSM type/numeric identity link to the fixed OpenStreetMap
  host; arbitrary source URLs are not made executable links.
- OSM shows supplied name/readable type, original identity and memberships,
  height/minimum-height/address/levels tags when supplied. Numeric source height
  tags use metres; explicit units remain unchanged. Levels are not converted to
  height. Missing heights/costs and incomplete tags/classification stay explicit.
- Independent category cards retain actual 0-4 scores/ordinal labels, provisional
  default flags, unscored status, separate historical paper-obstruction meaning
  and expandable matched rules/reasons/references. Scores are never summed into
  an overall risk or permission conclusion. Other pages retain their existing
  cost components.
- Aggregate cards show assigned/category counts, overlapping-membership and
  representative-point/whole-cell counting limitations, plus Zoom for objects;
  they never invent individual-object cost scores.
- DIPUL and scenario derivatives show decision/reason first, distinguish policy
  exclusions from assessed prohibitions, then show supplied clearance/buffer,
  scenario time/AGL scope and comparison assumptions. Source name/type/identity,
  supplied lower/upper limits with original units/references, validity and legal
  references are separate. Current assessed responses omit some original fields;
  these remain Not supplied, with no extra whole-source/raw DIPUL fetch.
- GHSL shows estimated people per native cell (rounded for readability), native
  resolution, epoch, cell/product identity and query coverage. Known zero differs
  from NoData; tiny positive values show less than 0.01 instead of a fabricated
  zero. The actual existing palette is very pale green (`#f1f9eb`) for zero and
  gray (`#747b86`) for NoData. Labels/help now match those colors; the old
  white/pink wording is superseded without changing other pages' palette.
- OSM choices are Feature category / Category cost. Nearby help explains category
  precedence, independent ordinal costs/default styling/obstruction flags,
  unassessed blanks, cost category selection, aggregate overview behavior,
  prepared-local Refresh OSM and extent-only Fit study. Display changes do not
  change the route objective, acquire data or plan routes.

## Regression

- **46 browser checks pass (35.5 s)**. Nine new source-detail cases cover nested/
  long/untrusted strings, missing heights/costs, mixed native units/reference
  frames, independent scores/defaults, zero/NoData/tiny positives, query coverage,
  assessment/source separation, mode help and validated derived-building original
  identity links. Part 2 fixtures moved to a shared
  helper; its selection/invalidation tests remain. One old legend assertion was
  updated for the new ordinal label.
- **14 real-stack smoke checks pass (36.1 s)**, including small-area costs,
  routing/native solver, export/download and OFM. ESLint, TypeScript/production
  build, experiment JavaScript syntax, Python Ruff/format and diff checks pass.
- Backend code/contracts, prepared sources, scoring rules, planner parameters,
  permissions and profile data are unchanged. No claim of a newly repeated local
  full Python suite; the final PR still requires Linux/Windows/frontend CI.

## Real data and delivery

Final source-hashed campaign **`.cache/iteration013-part3-final-v3/` passes**:

- Current byte hashes match all eleven measured application files. Original
  OSM/study hashes are unchanged and owned services stopped. OSM remains
  `6678ed0b55cb58dbfc23b570dda5474d42da78f984563cae910cde673e65e8a6`;
  study.json remains
  `6b8a4cfadcc11395d186ee03d0d5a1da237697a624ee6f5c806f2a1e66e0898e`.
- Actual original `way/49499709` shows readable natural/water facts, independent
  cost 0/Very low and expandable matched-rule evidence. Diagnostic `relation/49267`
  remains readable without a fabricated outline. Ten selections retain one
  renderer/outline/summary and zero map vertical shift. Group folding adds no
  source/detail request. No extra fallback zoom was needed in this campaign.
- Actual assessed DIPUL residential zone shows policy-exclusion uncertainty,
  source availability and its 100 m AGL/time scope. GHSL cell `48:112` shows the
  0.31 rounded population estimate, 100 m native resolution and 2020 epoch. Raw
  JSON stays closed by default; no separate raw zone/full-source fetch was added.
- One scenario load takes **85.778 s**; **one** population request serves cached
  display toggles. **Zero** route calls/browser errors. Desktop OSM/DIPUL/GHSL
  and 390 x 844 mobile expanded/collapsed screenshots were visually checked.
  The map summary stays within horizontal map bounds and long inspector headings
  remain visible. Mobile has one bounded sheet and no horizontal overflow.

See the [operation guide](../../experiments/iteration-013/README.md).
The first campaign passed functional checks (86.680 s scenario preparation), but
visual review found an edge summary clipping and long-inspector heading issue.
The final layout reserves extra space and explicitly checks popup bounds and
the inspector's visible top; the earlier campaign is not final acceptance.
v2 passes these layout assertions; final-v3 also records the final added original OSM
identity link for derived buildings. Those links are separately browser-tested.

Existing first full scenario preparation/payload costs remain; no speedup or
memory redesign is claimed. Original details remain on demand. Reformatting uses
only already-loaded metadata/original responses; it adds no source acquisition or
new API. Main and Part 4 timing/backend reassessment remain deferred. Feature PR,
final-head CI, iteration merge, explicit Issue closure and verified merged-feature
cleanup are pending until recorded.
