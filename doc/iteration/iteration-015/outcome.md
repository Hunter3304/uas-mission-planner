# Iteration 015 implementation and publication outcome

Historical implementation record: 2026-10-27 (Europe/Berlin).
Baseline: main `2b3efce`. Implementation was performed locally on `iteration/015`.
The historical verification and timings below were recorded then; they do not
establish the results of a new release check or macOS execution.

## Publication preparation (2026-11-02)

The user authorized publishing the latest Iteration 015 features and merging them
into `main`. Fresh local release checks completed before publication:

- Windows backend: **391 passed, one existing skip**, 168.86 s; Ruff check and
  format verification pass (73 Python files).
- Frontend lint and production build pass; mocked browser suite **67/67 passes**.
- Real-stack smoke: 13/14 passed initially; one Chrome process exited before page
  startup. That isolated case passed on rerun, so all 14 distinct cases passed.
- Independent read-only implementation review found no material release blocker.

Logs are retained locally under `.cache/iteration015-publish-20261102/`.
Remote CI and integration are separate from these local results and are recorded
by the publication PR and its GitHub checks. The publication includes source and
setup documentation, with datasets and `data.zip` excluded.

README was reconciled with the implemented fused-risk controls and documents
standard macOS/Linux A*/Dijkstra setup separately from the Windows-only OMPL extra.
There is no verified macOS OMPL build or macOS route-success claim. The retained
30 s per-graph preparation cap remains independent of the selected search budget
and 300 s backend / 310 s browser limits, so merging does not by itself resolve
an expanded-graph preparation timeout.

## Delivered behavior

The user approved the [updated plan](../../plan/iteration-015.md), explicitly
replacing regional `risk` rather than adding a paper mode. Regional risk now
uses fixed building/landuse/highway/population fusion:

`J = 0.15 B + 0.15 LU + 0.15 H + 0.45 P + 0.1 L`.

The reusable model rasterizes OSM onto a shared 150 m cost lattice, directly
aggregates native GHSL counts to that lattice, uses one full-study population
normalization reference and integrates the complete centreline. Natural supplies
cell-level landuse fallback; category overlaps take the maximum score. Explicit
project choices and deviations from the paper are in the
[routing rules](../../rules/paper-risk-routing.md).

The page retains its layout and two objective values. Risk displays fixed weights
instead of old adjustable controls; population is mandatory there. Default risk,
research planning mode, background 0 and native ABIT* are applied. Distance retains
its optional 250 m population term. Source inspection, map groups and the 250 m
population display remain independent of the routing objective. Help text now
distinguishes the 150 m fusion grid from the 250 m display and search spacing.

Core/API/CLI, graph connectors, native OMPL callbacks, independent final checks,
automatic arrival and exports use the same scoring contract. Separate B/LU/H/P,
fused F, physical L and objective J are preserved. Failure clears accepted geometry,
costs and ETA. The historical synthetic experiment harness was migrated to the
new regional contract; small-area building-risk experiments retain their behavior.

The user additionally authorized extending the total request limit. Regional
backend requests now have 300 s, and regional browser requests 310 s with response
grace. Other browser API calls retain 120 s. Search budgets remain separate;
raising the request limit does not make a 3 s ABIT* solve search for 300 s.

## Historical local verification (2026-10-27)

- Full backend regression: **391 passed / one existing skip**, 179.81 s.
  Subsequently, the all-regional request-deadline adjustment passed **81** targeted
  routing/experiment/flight-interval cases (79.56 s); the descriptive 150 m metadata
  correction passed **17** fused-risk cases (10.64 s).
- The final numerical fixtures include hand-computed J=235, duplicate overlap,
  natural fallback, background/default distinctions, unknown contact, exact points,
  shared-edge component consistency and independently computed native transfers.
  Highway-only and landuse-only changes each cause a route-choice change with
  other inputs fixed. Corrupted component totals fail independent final validation.
- Frontend: **67** browser cases pass, including the actual two-value objective
  dropdown, fixed weights, research/background defaults, request timeout selection,
  separate results/export and stale-result cancellation. Desktop/mobile screenshots
  are inspected. **14** real-backend smoke cases pass (35.6 s), preserving the
  existing small-area pages and other source inspection flows.
- Ruff check/format, frontend ESLint, TypeScript/Vite build and diff whitespace
  checks pass. The pre-existing Starlette/httpx and rasterio deprecation warnings
  remain; they are not new failures.

The restricted Windows sandbox hung TestClient's initial loopback socket pair
before an application request. Stack inspection identified the environment issue;
API/browser suites passed outside that sandbox. No application socket workaround
or runtime dependency changes were introduced.

## Historical retained Hannover acceptance (2026-10-27, Windows host)

The reproduction script is
[`verify.py`](../../experiments/iteration-015/verify.py). It uses retained OSM,
GHSL and terrain only, the explicit historical 2026-10-07 scenario, 100 m AGL,
30 m/s, background 0 and the existing derived-geometry/height assumptions.
Successful comparisons use explicit endpoints `[9.7967855, 52.4044919]` and
`[9.8044306, 52.3834796]`; catalog sites are never moved implicitly.

The shared 150 m population grid has 18,574 supported cells, no NoData, and
class counts 15,483 / 2,486 / 482 / 113 / 10. Its complete-study maximum density
is approximately 19,929.1779 people/km2, epoch 2020. These are model-specific
classes, not exposure probabilities or interchangeable 250 m display thresholds.

The sequential comparison campaign in `.cache/iteration015-real-01/` completed
successful A*, Dijkstra and native ABIT* requests. An independent partition of
accepted paths checked all component totals and fusion identities. The A*/Dijkstra
graph objective agrees:

| Quantity | A* | Dijkstra | Native ABIT* with 20 s search |
|---|---:|---:|---:|
| Horizontal length m | 2840.878100 | 2840.878100 | 2394.488085 |
| Building B | 9603.640486 | 9603.640486 | 8254.388927 |
| Landuse LU | 9970.420439 | 9970.420439 | 8443.520845 |
| Highway H | 8527.453771 | 8527.453771 | 7383.066443 |
| Population P | 781.580137 | 781.580137 | 1226.970919 |
| Fused F | 5074.375851 | 5074.375851 | 4626.981495 |
| Objective J | 4851.026076 | 4851.026076 | 4403.732154 |

Automatic arrival and full-interval checks also succeed. Separately, the original
catalog-address conservative request returns `invalid_endpoint`, with no accepted
route. Algorithm changes do not override that endpoint conflict. These tests
establish engineering consistency against retained inputs, not current flight
permission or superiority of continuous search over a different graph space.

## Historical preparation time and resource limits (2026-10-27)

An early full cold request exhausted the former 110 s request limit before
search. Primary-layer-only classification avoids repeatedly constructing complete
inspection cards, and the 150 m population preparer batches bounded native pixel
intersections in GEOS/NumPy. Scalar-versus-batched tests retain fractional-count,
NoData and outside-support semantics. The default 250 m path is unchanged.

After optimization, a fresh worker with the 3 s ABIT* budget completed in
**97.979 s** (`.cache/iteration015-cold-03/`). Another complete fresh worker under
the final 300 s request policy completed in **119.675 s**
(`.cache/iteration015-cold-04/`):

| Diagnostic | Observed seconds |
|---|---:|
| Source preparation | 53.614 |
| 150 m population preparation | 21.378 |
| OSM/fused surface preparation | 40.297 |
| Aggregate preparation | 115.354 |
| ABIT* planner | 3.060 |
| Complete request wall time | 119.675 |

Diagnostics do not form an exact additive partition of every operation. The
worker's peak working set was **1332.03 MiB**, with **501.11 MiB** observed after
the accepted request. This includes source verification/parsing and libraries,
not incremental fusion memory. **192 original files match their saved checksum
receipts after the run.** No source raster, GeoPackage, terrain tile or receipt
was rewritten.

A warm population/fused surface removes that construction work, but each request
still verifies/prepares regional sources. One warm automatic A* request took
50.927 s, including 43.272 s source preparation. Timings are scoped observations
with no OS cache flush and some simultaneous regression activity; they are not
latency distributions or guarantees. Preparation remains the dominant limitation.
ABIT* is stochastic; a fixed budget is not a promise of success for other pairs.

## Reproduction

Use fresh output directories:

```powershell
backend/.venv/Scripts/python.exe doc/experiments/iteration-015/verify.py --output .cache/iteration015-review-new
backend/.venv/Scripts/python.exe doc/experiments/iteration-015/verify.py --cold --output .cache/iteration015-cold-new
```

The standard campaign reuses verified request-local sources for algorithm
comparisons, whereas `--cold` invokes the complete automatic request in a fresh
process. The latter measures source preparation too. Rules and outcome distinguish
those scopes. Source acquisition remains separate from this implementation;
remote publication status is recorded in the publication section above.
