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
- GitHub feature PR CI: [36446412570](https://github.com/Hunter3304/uas-mission-planner/actions/runs/36446412570), passed.
- Iteration push CI: [36446647516](https://github.com/Hunter3304/uas-mission-planner/actions/runs/36446647516), passed.
- Sprint PR CI: [36446678245](https://github.com/Hunter3304/uas-mission-planner/actions/runs/36446678245), passed.

- Main push CI: [36446895517](https://github.com/Hunter3304/uas-mission-planner/actions/runs/36446895517), passed for the sprint merge commit.

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
[Feature PR #33](https://github.com/Hunter3304/uas-mission-planner/pull/33) merged
into iteration/004 at 970760eb1c7b9bc00a9facb980188879b4f9db41.
[Sprint PR #34](https://github.com/Hunter3304/uas-mission-planner/pull/34) merged
into main at 7d516065a05e807e26092db1c1c7e969e0211c90.
Issue #32 is closed. The feature branch was deleted locally and remotely;
`git fetch --prune`, local branches and remote heads were checked.
Iteration branches remain as history. Issue #35 tracks this final delivery record.
The release tag v0.3.0 stays fixed; no new release is included in this delivery.
