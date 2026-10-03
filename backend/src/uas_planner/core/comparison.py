"""Bounded offline comparisons; all returned exact routes are independently checked."""

import platform
from importlib.metadata import PackageNotFoundError, version
from math import isclose
from statistics import mean, median
from time import perf_counter

from uas_planner.core.grid import build_grid
from uas_planner.core.planning import plan_saved_route
from uas_planner.core.risk import nonnegative, prepare_risk_model
from uas_planner.core.routing import constraint_checker


def compare_routes(
    directory,
    manifest,
    *,
    cell_m=25,
    background_cost=None,
    risk_weight=0.9,
    distance_weight=0.1,
    safety_distance_m=0,
    time_budget_s=3,
    repetitions=3,
    endpoints=None,
):
    if (
        isinstance(repetitions, bool)
        or not isinstance(repetitions, int)
        or not 1 <= repetitions <= 10
    ):
        raise ValueError("Repetitions must be an integer from 1 to 10.")
    nonnegative(time_budget_s, "Time budget")
    if time_budget_s > 60 or time_budget_s * repetitions > 60:
        raise ValueError("Comparison ABIT* solve budgets must total at most 60 seconds.")
    started = perf_counter()
    grid = build_grid(directory, manifest, cell_m)
    model = prepare_risk_model(
        directory,
        manifest,
        grid,
        background_cost=background_cost,
        risk_weight=risk_weight,
        distance_weight=distance_weight,
        safety_distance_m=safety_distance_m,
    )
    check = constraint_checker(grid, safety_distance_m)
    selected = endpoints or {name: manifest["config"][name] for name in ("start", "end")}
    runs = []
    specs = [
        ("distance A*", "astar", "distance"),
        ("weighted A*", "astar", "risk"),
        ("weighted Dijkstra", "dijkstra", "risk"),
    ]
    specs += [(f"ABIT* run {i + 1}", "abitstar", "risk") for i in range(repetitions)]
    for label, algorithm, objective in specs:
        result = plan_saved_route(
            directory,
            manifest,
            grid=grid,
            cell_m=cell_m,
            algorithm=algorithm,
            objective=objective,
            background_cost=background_cost,
            risk_weight=risk_weight,
            distance_weight=distance_weight,
            safety_distance_m=safety_distance_m,
            time_budget_s=time_budget_s,
            endpoints=selected,
        )
        verification = {"status": "no_exact_route"}
        if result["exact"]:
            points = result["geometry"]["coordinates"]
            costs = [model.evaluate([a, b]) for a, b in zip(points, points[1:])]
            constraints = (
                len(points) >= 2
                and points[0] == list(selected["start"])
                and points[-1] == list(selected["end"])
                and all(check([a, b]) == "permitted" for a, b in zip(points, points[1:]))
            )
            if not constraints or any(c["assessment"] != "assessed" for c in costs):
                verification = {
                    "status": "unresolved_risk" if constraints else "failed_constraints"
                }
            else:
                totals = {
                    key: sum(c[key] for c in costs)
                    for key in ("length_m", "risk_length_cost", "objective_cost")
                }
                keys = (
                    ("length_m", "risk_length_cost", "objective_cost")
                    if objective == "risk"
                    else ("length_m",)
                )
                matches = all(
                    isclose(totals[k], result[k], rel_tol=1e-7, abs_tol=1e-5) for k in keys
                )
                verification = {"status": "verified" if matches else "failed_costs", **totals}
        runs.append({"label": label, "result": result, "comparison_costs": verification})
    abit = [r for r in runs if r["result"]["algorithm"] == "abitstar"]
    exact = [
        r for r in abit if r["result"]["exact"] and r["comparison_costs"]["status"] == "verified"
    ]
    values = [r["comparison_costs"]["objective_cost"] for r in exact]
    complete = all(
        r["result"]["exact"] and r["comparison_costs"]["status"] == "verified" for r in runs
    )
    packages = {}
    for name in ("ompl", "shapely", "pyproj", "rasterio"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {
        "status": "complete" if complete else "incomplete",
        "synthetic": manifest.get("synthetic", False),
        "runs": runs,
        "runtime_ms": (perf_counter() - started) * 1000,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "packages": packages,
        },
        "abitstar_summary": {
            "repetitions": repetitions,
            "time_budget_s_per_run": time_budget_s,
            "total_solve_budget_s": time_budget_s * repetitions,
            "verified_exact_solution_rate": len(exact) / repetitions,
            "objective_distribution": {
                "values": values,
                "min": min(values),
                "max": max(values),
                "mean": mean(values),
                "median": median(values),
            }
            if values
            else None,
            "seed_supported": False,
            "seeds": [None] * repetitions,
        },
        "assumptions": model.provenance,
        "limitations": [
            "Scores are ordinal building preferences, not population or collision probabilities.",
            "The distance baseline is re-scored under the same weighted model for comparison.",
            "Grid and continuous spaces have different candidates; optimality claims are separate.",
            "Per-task seeding is unavailable; timings and stochastic paths need not repeat exactly.",
            "Timeouts do not establish continuous-space infeasibility.",
        ],
    }
