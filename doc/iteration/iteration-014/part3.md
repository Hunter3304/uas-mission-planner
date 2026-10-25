# Iteration 014 Part 3 - Optional population routing UI

Date: 2026-10-25 (Europe/Berlin). Status: implemented and locally accepted.
Implementation authorized after Part 2 publication.
Local feature: `feature/125-population-routing-ui`, assigned Issue #125 in
[Milestone 13](https://github.com/Hunter3304/uas-mission-planner/milestone/13).
Base: published Part 2 head `8dac2a6d608e04935c6d4750f60d507013e38e0c`.
Plan: [Iteration 014](../../plan/iteration-014.md).
Operating guide: [Population routing](../../experiments/iteration-014/README.md).
Rules: [Population costs](../../rules/population-costs.md).

## Part 2 publication

The user explicitly requested checking and pushing Part 2 before completing Part 3.
Its accepted backend/frontend trees were unchanged. Ruff/format and 22 population
routing tests passed (35.16 s). Published the existing Part 2 feature and opened
[PR #126](https://github.com/Hunter3304/uas-mission-planner/pull/126), targeting
iteration/014. Exact-head Checks run `40209689283` passed Windows Python, Linux
Python and frontend, including all test steps. PR #126 and Issue #124 remain open;
no Part 2 merge/deletion is claimed. Part 3 is stacked locally on that head.

## Implemented behavior

- `Include population` sits beside the regional distance/risk objective, default
  unchecked. `Population weight` appears only while selected, initially 1.
  The controls form one responsive objective row. Active input is required, finite
  and nonnegative. Empty stays empty, rather than becoming zero on edit.
- Requests send the population flag and only include the numeric weight when
  selected. Unchecking retains the entered text but hides/omits it; invalid hidden
  values cannot block an inactive solve. A submitted zero preserves the Part 2
  inactive contract, with null population cost and no population preparation.
- Both base objectives work. Help text explains length-times-class and the combined
  objective. Population controls cancel obsolete requests and clear route, ETA and
  export. They do not automatically solve. Late responses cannot restore stale data.
- Results separate physical length, building/population score-metres when evaluated,
  objective cost, returned effective weights and population assessment. Distance mode
  does not display a building cost. Inactive population is not evaluated, not zero.
  Population model/reference metadata and endpoint support diagnostics remain available.
- Displayed-result GeoJSON preserves complete response/source metadata, requested
  versus effective controls, and costs/effective weights/objective in successful
  feature properties. Failure exports contain no successful route features or ETA.
- Population display visibility is independent from weighting and never invalidates
  a route. Route weighting does not fetch the display GeoJSON. The five-color 250 m
  grid, gray NoData, shared inspector, exact endpoints and departure-only planning
  from previous Parts remain intact. Backend implementation and source data are unchanged.

## Validation

Final frontend: **68 browser tests passed (48.5 s)**, including eight new population
routing cases. **14 real-backend smoke tests passed (37.4 s)**. TypeScript/Vite build,
ESLint, acceptance-script syntax and diff whitespace checks pass. Local Windows
uses installed Chrome via `PLAYWRIGHT_CHANNEL=chrome`; an initial default-browser
attempt could not launch because the Playwright headless-shell binary is absent.

The new tests cover default inactive payloads, conditional/retained inputs, empty
and negative active values, zero weight, both objectives, separate returned costs,
effective weights, export metadata, independent display toggles, cancellation by
checkbox/weight, unknown support failures and mobile layout. Both final fixture
screenshots were visually inspected; desktop groups objective/checkbox/weight in
one row and mobile stacks them without horizontal overflow.

The unchanged backend retains Part 2's complete 372 passes / one existing skip,
focused integration, numerical/native routing and real-data evidence. This UI-only
Part does not claim another complete local backend run. Part 2 remote CI ran its
complete backend suites on the exact published base.

## Real Hannover UI acceptance

`node doc/experiments/iteration-014/verify-part3.mjs` passed against isolated real
backend/frontend services and existing Hannover/terrain snapshots. It uses the
established frozen 2026-10-07 research scenario, exact accepted endpoints, 250 m
graph spacing, a 20-second search budget and automatic arrival. It does not make
a present-day operational permission claim. Evidence:
`.cache/iteration014-part3-real-v1/acceptance.json`, displayed-result GeoJSON files
and desktop/mobile routing screenshots. Both real screenshots were visually inspected.

| UI objective | Length m | Building score-metres | Population score-metres | Objective |
|---|---:|---:|---:|---:|
| Building risk + population, weight 1 | 3715.591528 | 1256.815787 | 1512.315622 | 3015.008983 |
| Distance + population, weight 1 | 2840.878100 | Not evaluated | 1487.690116 | 4328.568216 |

Both succeed with independent backend validation and automatic ETA. Displayed
costs, effective weights, source identity and exported values match their actual
responses. Recomputing the combined objective from returned quantities matches
within `0.000001`. Both retain the accepted Part 1 population identity
`79d339b9671be83654c8e6b1237b085878eccddad55258177fffcb61cdbc011e`.

Exactly two route requests and zero population-display requests were issued.
Unchecking then cleared route/ETA/weight/export without another solve. Original
study manifest, population raster and OSM GeoPackage hashes match before/after.
No browser exceptions or mobile horizontal overflow occurred. Owned verification
services were stopped. Initial verification attempts needed selector corrections
for existing duplicate DIPUL/coverage labels and a select's implicit label; they
did not reach planning or reveal an application failure.

Measured browser elapsed time through displayed-result export was 83.43 s for
risk plus population and 57.82 s for distance plus population. These include
source preparation, planning, response/display and export and differ in cache/base
objective conditions; they are not a latency comparison. Real-data algorithm here
is A*. Dijkstra/native compatibility remains covered by Part 2. Broader algorithm,
memory and performance acceptance remains Part 4.

## Delivery scope

Part 3 is local only; no push, PR, remote CI, merge or feature cleanup is claimed.
The second Part's explicit push authorization is recorded separately above.
Part 4 remains for broader integrated acceptance/performance/resource completion.
Main and iteration/014 remain at their previously verified commits.
