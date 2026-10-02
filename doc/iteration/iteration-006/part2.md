# Iteration 006 Part 2 — Official OMPL ABIT* adapter

Date: 2026-10-01 (Europe/Berlin). Implementation: Issue #59 in Milestone 6,
branch `feature/59-ompl-abitstar`, based on `iteration/006` fast-forwarded to
main `e54e245`. Local implementation/verification complete; publication and
integration merges are not yet performed. Part 3 remains deferred.

## Behavior and usage

`core/abitstar.py` provides `AbitPlanner.initialize()`, the `simple_setup`
attribute and `run()`. Each task owns its native planner, state space, endpoint
states, callbacks and search state. `plan_abitstar(grid, risk_model, endpoints)`
is the prepared-input entry point. No path/graph file is written and no
graph_tool dependency is required.

Saved-data entry point, after optional Windows installation in README:

```python
from threading import Event
from uas_planner.core.experiment import load_experiment
from uas_planner.core.risk_routing import plan_risk_route

directory = "data/synthetic-route-demo"
manifest = load_experiment(directory)
cancelled = Event()
result = plan_risk_route(
    directory, manifest, algorithm="abitstar", background_cost=0,
    time_budget_s=3, safety_distance_m=0, cancel=cancelled.is_set,
)
```

Calling `cancelled.set()` from another thread requests cancellation. Background
0 is an explicit assumption; omission retains unknown support. An already
prepared `grid=` avoids repeated grid preparation. Unlike graph planners, ABIT*
does not use grid edges or require graph connectivity: the grid supplies the
existing vector constraint model and provenance. Existing CLI/API/UI still use
their distance-only behavior. New controls belong to Part 3.

## Cost, constraints and results

State/motion callbacks reuse the complete buffered metric geometry checker and
Part 1 risk model. States and full motions must have assessed risk support.
ABIT* uses a two-dimensional metre state space bounded by the model envelope.
Soft building scores remain costs, not new hard restrictions. The motion
heuristic is distance-weight times metric displacement. Cost-to-go subtracts
the goal tolerance before applying that weight; both are nonnegative lower
bounds. Zero distance weight gives a conservative zero heuristic.

The solver preserves exact geographic endpoints and independently rechecks all
output segments with the shared full-geometry checker, recomputes segment costs
and compares their total with the native objective before exposing success.
Assessment flags, source/rule/model provenance, clearance, runtime, setup and
validation durations, stop reason and callback counts accompany the result.
No finite-run global optimality claim is made.

| Status | Meaning |
| --- | --- |
| `success`, `exact=true` | Exact path, complete final validation and cost recomputation passed |
| `approximate_solution` | A validated partial candidate is diagnostic only; successful geometry/cost fields remain empty |
| `timeout` | No validated path within budget; feasibility remains unknown |
| `cancelled` | Caller requested cancellation; even an existing candidate is withheld |
| `invalid_endpoint` | Endpoint fails hard vector constraints |
| `unresolved_input` | Required endpoint/global support is unknown, or unknown samples prevented a validated path |
| `planner_unavailable` | Optional native module missing, unable to load, or lacks ABITstar binding |
| `computational_failure` | Native/callback execution or final path/cost validation failed |

Invalid finite-number/configuration inputs raise ValueError before planning.
Callbacks must not mutate their risk model during a run. Calling run twice on
an instance raises RuntimeError; create a new instance for each task.

## Budget and cancellation limits

The saved-data entry point starts the budget before snapshot/grid/risk
preparation. The prepared-input entry point starts at construction. Setup and
each native termination/state/motion callback check elapsed time/cancellation.
There is no unbounded application solve loop. Native setup, snapshot preparation
and individual Shapely operations cannot be interrupted mid-call. Full final
validation is mandatory and can add overhead beyond the search deadline;
`runtime_ms` measures the whole operation. This is cooperative cancellation,
not a process-enforced hard wall-clock limit. Callback exceptions produce an
explicit computation failure. Cancellation is distinguished by the adapter
even though OMPL calls a terminated native solve `Timeout`.

No process-global random seed is reset; that would interfere with concurrent
tasks. Search instances are separate, but native global RNG internals and the
Python GIL are still library/runtime properties. Timing-based runs may produce
different paths. Deterministic seed/repetition comparisons remain Part 3.

## Dependency and validation

Optional Windows CPython 3.13 x64 dependency: `ompl==2.0.1+uas.1`, repository
wheel and SHA256 pinned in uv.lock; source/patch/tool/license details in
[vendor provenance](../../../backend/vendor/README.md). Baseline graph routing
does not import OMPL. Linux installs preserve baseline dependencies; no Linux
ABIT* runtime result is claimed. Windows CI requests the extra through its
platform marker and runs the native tests. Remote CI has not yet been executed.

Local verification: 151 backend passes, one existing Windows symlink-permission
skip; Ruff check/format, frontend ESLint/build and nine mocked Chrome browser
checks passed. Twelve new tests cover actual obstacle-detour/cost callbacks,
known nonzero risk cost 82 and heuristic 10, last-valid success/failure/null,
independent Shapely clearance/cost checks, saved-snapshot integration, unresolved
constraints, mid-search Event cancellation, sealed-wall timeout, zero length,
concurrent independent tasks and unavailable/approximate/validation failures.
Playwright's default browser was absent; use `PLAYWRIGHT_CHANNEL=chrome` on this
host. Existing real constraint uncertainty and source data are unchanged.
