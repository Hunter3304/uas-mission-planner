# Iteration 004 feedback

## Delivered scope

Independent building, highway, landuse and natural costs on saved OSM features.
The core reads packaged, versioned rules and returns separate category results.
The explorer switches category colors, statistics, table costs and tag evidence.
Unknowns, exclusions and historical obstruction flags remain distinguishable.
Rules are documented in `doc/rules/`; no source dataset or download is rewritten.

## Validation

- 66 local Python tests passed; one Windows symlink permission skip.
- 9 mocked browser regressions and 3 real-stack browser tests passed.
- Ruff lint/format, ESLint, TypeScript and production build passed.
- Desktop/mobile screenshots inspected; no viewport overflow.
- Coverage includes standalone features, overlapping tags, zero and unknown
  costs, obstruction-only/excluded tags, category switches and raw-data fidelity.
- GitHub PR/iteration/main CI results will be recorded after integration.

## Findings and limitations

- Existing Braunschweig sample: 9 building, 29 highway, 2 landuse and 51 natural
  objects. Categories can overlap; their counts are not a unique total.
- Two highway and 47 natural classifications use provisional defaults. The paper
  does not classify every contemporary OSM value; defaults remain explicit.
- Only the saved acquisition area is analyzed. Basemap buildings outside it are
  context images. Expanded acquisition was canceled and not resumed.
- No grid, population fusion, legal restrictions, buffers or route planning.
- Test fixtures are synthetic; original local datasets are not published.

## Process and integration

The scope was approved before implementation. Remote tracking was established
on September 28 after local preparation: Milestone #4 and Issue #32 were created
before creating the feature branch. Preserve this distinction in the history.
Feature -> iteration -> main PR integration is pending at this document revision.
Temporary merged branches must be deleted; iteration branches remain as history.
The release tag v0.3.0 stays fixed; no new release is included in this delivery.
