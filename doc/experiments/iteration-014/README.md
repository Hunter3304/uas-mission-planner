# Iteration 014 population routing operation guide

Use the existing local frontend/backend with the saved Hannover study and terrain.
Original source snapshots remain unchanged; the 250 m population product is derived.

## Planning a route

1. Select the Hannover saved dataset. In `Regional route planning`, choose saved
   sites or enter exact endpoints, select terrain and enter a Europe/Berlin departure.
   Retain the existing explicit constraint, height and planning-mode assumptions.
2. Choose the base `Objective`: `risk` uses building cost and distance weights;
   `distance` uses physical length with building/distance coefficients 0/1.
3. `Include population` starts unchecked. Check it to reveal `Population weight`,
   initially 1. Enter a finite nonnegative value. It need not sum to 1 with other
   weights; 0 disables the population contribution and its support requirements.
4. Click `Plan regional route`. A*, Dijkstra and ABIT* use the same population
   evaluator. The grid remains 250 m by default; ABIT* searches continuous space.
5. Read physical length, building and population costs in score-metres when active,
   objective cost, effective weights, assessment and estimated arrival separately.
   `Distance + population` minimizes length plus weighted population cost; it is
   a combined objective. Population is a soft preference, with constraints assessed
   separately. The ordinal score is not a casualty probability.
6. `Export displayed result` saves that response, its source/classification
   identity and controls, without replanning. Successful feature properties also
   contain separate costs and effective weights. Unsuccessful results have no
   route features or successful ETA; use their endpoint/support diagnostics.

Population cost is `sum(length in each 250 m cell × its class 0–4)`. The lowest
class may contain people. See [exact rules](../../rules/population-costs.md),
including shared boundaries, unknown touches and the fixed whole-study reference.
An unknown required population cell leaves active population routing unresolved.

Editing the population checkbox or weight clears the route/ETA/export and cancels
obsolete requests. It never starts another solve automatically. Unchecking hides
and retains the weight locally but omits it from the inactive request, so an
invalid hidden value cannot block planning. Rechecking restores the entered value.

## Viewing the grid

The map's `GHSL — population risk (250 m)` toggle shows the independent cached
display product: five green-to-red classes and gray NoData. Click a cell to inspect
population, density, support and full-study thresholds in the shared inspector.
This toggle does not change a route objective or clear a result. Route weighting
works while this layer is hidden, without fetching its display GeoJSON.

## Verification

Browser fixtures cover active/inactive requests, conditional inputs, retained
invalid values, zero weight, both objectives, late-request cancellation, failures,
exports, independent map visibility and mobile layout:

```powershell
cd frontend
$env:PLAYWRIGHT_CHANNEL = 'chrome' # use the installed Chrome on Windows
npm run test:e2e
npm run test:smoke
```

From the repository root, real Hannover checks use existing sources only:

```powershell
backend/.venv/Scripts/python.exe doc/experiments/iteration-014/verify-part2.py --output .cache/iteration014-part2-new
node doc/experiments/iteration-014/verify-part3.mjs .cache/iteration014-part3-new
```

The Part 3 script uses isolated backend/frontend ports 8016/5188, refuses occupied
ports, blocks online map tiles, and stops only its owned services. It plans risk
plus population and distance plus population through the UI with the established
frozen 2026-10-07 research scenario, checks displayed/exported costs and automatic
arrival, records screenshots and hashes original study/population/OSM files.
It does not download or modify source data. This acceptance scenario is distinct
from present-day operational permission. Actual results and limits are in
[Part 2](../../iteration/iteration-014/part2.md) and
[Part 3](../../iteration/iteration-014/part3.md).

## Part 4 integrated/resource verification

Use a new output directory for each core campaign, from the repository root:

```powershell
backend/.venv/Scripts/python.exe doc/experiments/iteration-014/verify-part4.py --output .cache/iteration014-part4-core-new
backend/.venv/Scripts/python.exe doc/experiments/iteration-014/verify-part4.py --catalog-only --output .cache/iteration014-part4-catalog-new
node doc/experiments/iteration-014/verify-part4.mjs .cache/iteration014-part4-display-new
```

Run the core campaign sequentially with other tests/CPU-heavy tasks finished. It
hashes original study/population/OSM and all retained terrain TIFF/JSON/XML files
before/after, starts isolated worker processes, and records every route outcome.
It measures population cold construction, ten verified cache hits, spatial index,
display/serialization, count conservation, and nine real requests when native OMPL
is installed: A* risk off/on repeated twice each, Dijkstra risk off/on, ABIT* risk
off/on and A* distance plus population. All share the frozen scenario, accepted
exact endpoints, 250 m spacing and 20-second search budget. ABIT* remains continuous
and stochastic; a single bounded run does not establish its optimum or distribution.

The separate catalog-only campaign uses the actual saved address coordinates in
conservative mode, with population off/on and no endpoint overrides. It records
blocked/unresolved address outcomes with no accepted geometry/costs/ETA rather than
moving a site or inventing launch clearance. This complements the accepted exact
nearby endpoints used for successful research comparisons.

Cold means an empty application cache in a fresh process, without flushing the
operating system's filesystem cache. Only A* risk is repeated in-process for warm
population reuse; full regional constraint/source preparation remains request-local.
Windows memory counters report each worker's current/peak working set and private
usage, including imported libraries and all sources. Peak is a process lifetime
high-water mark, not the population layer's incremental allocation. Other platforms
report those Windows measurements unavailable rather than fabricating values.

The display campaign owns ports 8020/5190, refuses occupied ports and stops its
own services. It records first full-study render, response bytes, ten cached
visibility cycles, Chrome renderer JS heap after explicit garbage collection,
DOM/listener counts and desktop/mobile screenshots. Renderer heap excludes native
browser, canvas/GPU allocations; these measurements do not prove total memory or
absence of every possible leak. Real routes are independently replayed against
unbuffered classified footprints; graph A*/Dijkstra objectives must agree.
See the [Part 4 report](../../iteration/iteration-014/part4.md) and
[iteration outcome](../../iteration/iteration-014/outcome.md) for actual evidence.
