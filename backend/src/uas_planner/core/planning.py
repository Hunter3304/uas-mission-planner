"""Shared public planner controls with compatible distance-only defaults."""

from time import perf_counter

from uas_planner.core.grid import build_grid
from uas_planner.core.risk import RiskModel, nonnegative
from uas_planner.core.risk_routing import plan_risk_route
from uas_planner.core.routing import connect_endpoints, plan_route, route_context


def plan_saved_route(
    directory,
    manifest,
    *,
    grid=None,
    cell_m=50,
    endpoints=None,
    algorithm="astar",
    objective="distance",
    background_cost=None,
    risk_weight=0.9,
    distance_weight=0.1,
    safety_distance_m=0,
    time_budget_s=3,
    started_at=None,
):
    started = perf_counter() if started_at is None else started_at
    if algorithm not in ("astar", "dijkstra", "abitstar"):
        raise ValueError("Unknown routing algorithm.")
    if objective not in ("distance", "risk"):
        raise ValueError("Unknown routing objective.")
    for value, label in (
        (risk_weight, "Risk weight"),
        (distance_weight, "Distance weight"),
        (safety_distance_m, "Safety distance"),
        (time_budget_s, "Time budget"),
    ):
        nonnegative(value, label)
    if objective == "risk" and risk_weight + distance_weight == 0:
        raise ValueError("At least one objective weight must be positive.")
    if background_cost is not None:
        nonnegative(background_cost, "Background cost")
    if time_budget_s > 60:
        raise ValueError("Time budget must not exceed 60 seconds per run.")
    selected = endpoints or {name: manifest["config"][name] for name in ("start", "end")}
    prepared = grid if grid is not None else build_grid(directory, manifest, cell_m)
    if objective == "risk":
        result = plan_risk_route(
            directory,
            manifest,
            grid=prepared,
            endpoints=selected,
            algorithm=algorithm,
            background_cost=background_cost,
            risk_weight=risk_weight,
            distance_weight=distance_weight,
            safety_distance_m=safety_distance_m,
            time_budget_s=max(0, time_budget_s - (perf_counter() - started)),
        )
    elif algorithm == "abitstar":
        from uas_planner.core.abitstar import plan_abitstar

        # Distance planning does not require an assessed building-risk surface.
        model = RiskModel(
            {"type": "FeatureCollection", "features": []},
            prepared["validation"]["boundary"],
            analysis_crs=prepared["analysis_crs"],
            background_cost=0,
            risk_weight=0,
            distance_weight=1,
            safety_distance_m=safety_distance_m,
        )
        result = plan_abitstar(
            prepared, model, selected, time_budget_s=time_budget_s, started_at=started
        )
        result.update(objective="distance", risk_length_cost=None)
        result.pop("risk_model", None)
    else:
        result = plan_route(
            connect_endpoints(prepared, selected, safety_distance_m=safety_distance_m),
            algorithm=algorithm,
            safety_distance_m=safety_distance_m,
        )
    result["exact"] = result["status"] == "success"
    result.setdefault("solution_kind", "exact" if result["exact"] else "none")
    result["runtime_ms"] = (perf_counter() - started) * 1000
    result["controls"] = {
        "algorithm": algorithm,
        "objective": objective,
        "cell_m": cell_m,
        "background_cost": background_cost,
        "risk_weight": risk_weight,
        "distance_weight": distance_weight,
        "safety_distance_m": safety_distance_m,
        "time_budget_s": time_budget_s,
        "effective_weights": {
            "risk": risk_weight if objective == "risk" else 0,
            "distance": distance_weight if objective == "risk" else 1,
        },
    }
    result["experiment"] = route_context(manifest, selected)
    result.setdefault("optimality", result["experiment"]["optimality"])
    result["experiment"]["optimality"] = result["optimality"]
    if algorithm == "abitstar":
        result["experiment"]["connector_policy"] = "Exact endpoints in continuous space."
        result["randomness"] = {
            "seed_supported": False,
            "seed": None,
            "reason": "Bindings do not expose per-task planner/sampler seeding; global RNG is not reset.",
        }
    return result
