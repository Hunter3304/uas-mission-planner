# Iteration 004: Explainable building tag costs

## Approved extension

The user subsequently approved standalone road, land-use and natural-feature
cost display. Reuse the four existing tables; add per-category analysis and
summaries, a category selector, separate colors and tag explanations. Preserve
raw data and the existing building API. Do not resume the canceled expanded-area
download or change viewport/acquisition behavior. Validate non-building objects,
overlapping tags, unknown and zero costs, exclusions and category switching.

Scope approved in chat on 2026-09-27: analyze the costs of buildings and their
individual tags in saved maps. Implement a reusable core classifier, an opt-in
read-only API analysis, map coloring, per-tag explanations and dataset statistics.

Use Ramke (2020), Appendix I.II, Tables 7-1 through 7-4 (printed pages 69-70),
with the barn example from Table 3-3 (page 32). Record transcription corrections.
Keep ordinal costs, unknown defaults and historical obstruction flags separate.
Do not sum overlapping semantic tags or infer costs from addresses, height,
amenity, name or other unsupported tags. Blank map areas remain unassessed.

Acceptance: original saved files and downloads remain unchanged; every analyzed
tag shows its raw value, rule, cost/status and source; non-buildings have no
building cost; unknown classifications are distinct from known cost 2; map and
table agree; distribution counts unique OSM building objects. Validate core edge
cases, API/storage compatibility and real API/browser integration.

Excluded: population fusion, grid costs, legal restriction determination,
collision checking, route planning and public deployment.

## Integration workflow (2026-09-28)

- Scope was approved and implemented locally on September 27, before remote
  tracking. This deviation is recorded rather than presenting tracking as earlier.
- User authorized GitHub submission and workflow completion on September 28.
- Milestone: [#4](https://github.com/Hunter3304/uas-mission-planner/milestone/4).
- Implementation: [Issue #32](https://github.com/Hunter3304/uas-mission-planner/issues/32).
- Branch flow: `feature/32-independent-tag-costs` -> `iteration/004` -> `main`.
- Issue creation precedes feature-branch creation. Validate PR CI before merging;
  close the implementation issue and delete the merged feature branch immediately.
- Retain iteration branches; record sprint outcome and post-merge facts in HANDOFF.
- This integration does not publish a new version or alter v0.3.0.

## Outcome

Delivered through feature PR #33 and sprint PR #34 on 2026-09-28. Issue #32
closed; merged feature branch deleted and verified on both local and remote.
See iteration feedback for CI evidence and final delivery documentation (#35).
