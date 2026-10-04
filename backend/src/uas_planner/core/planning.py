"""Shared public planner controls with compatible distance-only defaults."""

from time import perf_counter

from uas_planner.core.grid import build_grid
from uas_planner.core.research import (
    RESEARCH_ASSUMPTION,
    planning_grid,
    readiness,
    route_uncertainties,
)
from uas_planner.core.risk import RiskModel, nonnegative, prepare_risk_model
from uas_planner.core.routing import plan_route, route_context


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
    planning_mode="strict",
    cancel=None,
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
    prepared = planning_grid(prepared, planning_mode, selected, safety_distance_m)
    diagnostics = readiness(prepared)
    preflight = (
        any(
            c["point_state"] != "permitted" or c["state"] != "permitted"
            for c in prepared["connectors"]
        )
        or prepared["validation"]["unresolved"]
    )
    model = None
    if objective == "risk" and not preflight:
        model = prepare_risk_model(
            directory,
            manifest,
            prepared,
            background_cost=background_cost,
            unsupported_policy="polygon_only_research" if planning_mode == "research" else "block",
            risk_weight=risk_weight,
            distance_weight=distance_weight,
            safety_distance_m=safety_distance_m,
        )
        preflight = any(
            model.evaluate([selected[n]])["assessment"] != "assessed" for n in ("start", "end")
        )
    if model is not None and algorithm != "abitstar" and not preflight:
        cells = {c["id"]: c for c in prepared["cells"]}
        for connector in prepared["connectors"]:
            assessment = model.evaluate(
                [connector["coordinate"], cells[connector["cell"]]["center"]]
            )
            if assessment["assessment"] != "assessed":
                preflight = True
                sources = ", ".join(assessment["source_ids"]) or "unassessed background"
                connector["state"] = "unresolved"
                diagnostics["endpoint_reasons"].append(
                    {
                        "endpoint": connector["endpoint"],
                        "state": "unresolved",
                        "reasons": [
                            {
                                "source": "building_risk",
                                "reason": f"Endpoint-to-grid connector has unassessed building risk ({sources}); choose another endpoint or a finer grid.",
                            }
                        ],
                    }
                )
    if algorithm == "abitstar" and not preflight and model is None:
        model = RiskModel(
            {"type": "FeatureCollection", "features": []},
            prepared["validation"]["boundary"],
            analysis_crs=prepared["analysis_crs"],
            background_cost=0,
            risk_weight=0,
            distance_weight=1,
            safety_distance_m=safety_distance_m,
        )
    preparation_ms = (perf_counter() - started) * 1000
    search_started = perf_counter()
    if preflight:
        result = plan_route(prepared, risk_model=model, safety_distance_m=safety_distance_m)
        result.update(algorithm=algorithm, objective=objective)
        if result["status"] == "unresolved_input":
            reasons = diagnostics["global_reasons"] + [
                r for c in diagnostics["endpoint_reasons"] for r in c["reasons"]
            ]
            result["message"] = "; ".join(dict.fromkeys(r["reason"] for r in reasons)) or (
                "Non-polygon building geometries have unknown risk support."
                if model and model.unsupported
                else "Building-risk support unassessed; inspect missing scores and supply an explicit background score for unassessed space."
            )
    elif algorithm == "abitstar":
        from uas_planner.core.abitstar import plan_abitstar

        options = {"time_budget_s": time_budget_s}
        if cancel is not None:
            options["cancel"] = cancel
        result = plan_abitstar(prepared, model, selected, **options)
        if objective == "distance":
            result.update(objective="distance", risk_length_cost=None)
            result.pop("risk_model", None)
    else:
        result = plan_route(
            prepared, algorithm=algorithm, risk_model=model, safety_distance_m=safety_distance_m
        )
    result["preparation_ms"] = preparation_ms
    result["planner_ms"] = 0.0 if preflight else (perf_counter() - search_started) * 1000
    result["readiness"] = diagnostics
    result["planning_mode"] = planning_mode
    result["constraint_validation"] = (
        "research_assumptions" if planning_mode == "research" else "strict_model"
    )
    result["research_assumptions"] = [RESEARCH_ASSUMPTION] if planning_mode == "research" else []
    result["crossed_unresolved_zones"] = route_uncertainties(prepared, result.get("geometry"))
    result["exact"] = result["status"] == "success"
    result.setdefault("solution_kind", "exact" if result["exact"] else "none")
    result["runtime_ms"] = (perf_counter() - started) * 1000
    result["controls"] = {
        "planning_mode": planning_mode,
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
