# Native Python ABIT* implementation survey

Date: 2026-10-01 (Europe/Berlin).
User decision: implement native Python ABIT*, without OMPL or a Linux runtime;
first investigate existing implementations and their validation evidence.

## Finding

Public Python candidates exist, including one whose six ABIT*-specific tests
were reproduced locally. No candidate reviewed establishes a drop-in,
research-validated implementation suitable for the project's risk objective.
Absence from this search is not proof that no such implementation exists.

The [authors' reference implementation](https://robotic-esp.com/code/abitstar/)
is part of OMPL. Use the [original paper](https://arxiv.org/abs/2002.06589)
and reference source as algorithm specifications, without adding an OMPL runtime.

## Candidates inspected

### zhm-real/PathPlanning

[ABIT_star3D.py](https://github.com/zhm-real/PathPlanning/blob/master/Sampling_based_Planning/rrt_3D/ABIT_star3D.py)
is a native Python skeleton, not a usable complete planner. Sampling, heuristic,
tree cost and measure methods contain `pass`; the main loop also references
undefined variables such as `m`. Repository license metadata reports MIT.
Do not confuse the README's algorithm/paper listing with validated execution.
Rejected as an integration base; no execution attempted.

### bailehang/100pathfinding-algorithms

[060_abit_star.py](https://github.com/bailehang/100pathfinding-algorithms/blob/main/Search_2D/060_abit_star.py)
is a native Python, visualization-oriented subclass of the repository's BIT*
demo. Uses per-batch linear inflation/truncation schedules. Its truncation bound
multiplies incumbent cost by the factor, widening candidate admission rather
than implementing the original paper's stopping criterion. No closed/inconsistent
vertex repair sets were identified in this subclass. These are source-review
findings, not a formal proof about every inherited behavior.

The [documented tests](https://github.com/bailehang/100pathfinding-algorithms#testing)
are import/layout smoke checks, not ABIT* correctness or convergence tests.
Repository license is Apache-2.0 with attribution requirements. Not executed
locally; not selected as a validated algorithm dependency.

### robotics-study/navigation_basic

Best executable candidate found. Inspected revision:
`a98698104edf66329a1fa5c4d6b4e07dc4397903`.

[Python source](https://github.com/robotics-study/navigation_basic/blob/a98698104edf66329a1fa5c4d6b4e07dc4397903/python/navigation/global_planning/sampling/abit_star.py)
contains batched sampling, vertex/edge queues, inflated heuristic ordering,
truncation and descendant cost propagation. It imports NumPy and local Python
modules; no OMPL import appears in the reviewed planner/helper sources.

[Six tests](https://github.com/robotics-study/navigation_basic/blob/a98698104edf66329a1fa5c4d6b4e07dc4397903/python/tests/test_abit_star.py)
cover open-space goal arrival and full-path motion checks, a separating wall,
open-space cost within 15% of straight-line distance after deflation, one fixed
comparison with RRT, heavy inflation and parameter validation.

Reproduced locally on Windows CPython 3.13.13, using existing NumPy/PyYAML/pytest
without installing any package or modifying the candidate's source. Isolated
sparse checkout: `D:/Aostfalia/tmp/abit-research-navigation`.

```powershell
$env:PYTHONPATH = 'D:\Aostfalia\tmp\abit-research-navigation\python'
$env:PYTHONDONTWRITEBYTECODE = '1'
& 'D:\Aostfalia\develop\uas-mission-planner\backend\.venv\Scripts\python.exe' -X utf8 -m pytest python\tests\test_abit_star.py -q -p no:cacheprovider --basetemp D:\Aostfalia\tmp\abit-candidate-pytest-utf8
```

Result: **6 passed in 1.20 s**. First run without UTF-8 mode failed all six during
configuration decoding under Windows GBK, before exercising the algorithm.

Limitations identified by source inspection:

- Searches each added batch with a linearly scheduled inflation/truncation;
  does not expose the paper's same-approximation repair cycle with closed and
  inconsistent vertex sets. Formal algorithm equivalence is unverified.
- Uses `space.distance` for geometry, heuristic and edge objective alike.
  Our risk-integrated cost must be separate from distance and its lower bound;
  simply replacing that method would also change neighbor selection and sampling.
- No elapsed-time budget/cancellation checks in this planner. Neighbor graph
  preparation is quadratic, with no cooperative interruption points.
- Tests do not establish theoretical convergence, arbitrary-obstacle performance,
  risk-weighted objectives, boundary-contact clearance or concurrent task isolation.
  The finite RRT comparison is one scenario, not a general guarantee that ABIT*
  beats RRT under equal budgets.
- No LICENSE/COPYING file found in the repository tree, no license identified
  by GitHub metadata, and no license field in its Python pyproject. Permission
  to copy this source into the project has not been established. Treat it as
  an inspected reference, not vendored code.

### Academic Python implementation evidence

[Sugiura and Matsutani, 2023](https://arxiv.org/pdf/2306.17625), sections 6.1
and 6.2, report implementing an ABIT* baseline in Python and evaluating it in
2D/3D experiments. They describe two searches of each batch with different
inflation factors, unlike the per-batch schedules above. This is stronger
experimental evidence that native Python is feasible. No downloadable ABIT*
source tied to that experiment was located in this search; it cannot be treated
as an available reusable implementation.

## Implementation direction

Proceed with an independent Python implementation from the original algorithm,
using existing Part 1 geometry and risk core. Do not vendor unlicensed code or
claim reference-implementation equivalence from these six demo tests. Document
inflation/truncation and repair invariants explicitly. Validate known sampled
graphs against Dijkstra, subtree updates, repaired search, obstacle detours,
weighted risk, zero distance weight, deadlines/cancellation and task isolation.
Finite tests support implementation behavior, not a new proof of asymptotic
optimality. Continuous-space optimality remains distinct from graph optimality.

This session completed discovery, source inspection and candidate test
reproduction. No application planner or dependencies were changed.
