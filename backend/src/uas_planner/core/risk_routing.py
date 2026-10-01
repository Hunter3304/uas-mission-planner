"""Offline Part 1 entry point using verified snapshots and existing grid planners."""

from uas_planner.core.grid import build_grid
from uas_planner.core.risk import prepare_risk_model
from uas_planner.core.routing import connect_endpoints, plan_route, route_context


def plan_risk_route(
    directory,
    manifest,
    *,
    grid=None,
    cell_m=50,
    endpoints=None,
    algorithm="astar",
    background_cost=None,
    risk_weight=0.9,
    distance_weight=0.1,
    safety_distance_m=0,
):
    """Plan without new acquisition. Background is unassessed unless supplied.

    The caller provides an integrity-verified experiment manifest (load_experiment).
    An optional grid is already prepared from that same manifest.
    """
    selected = endpoints or {name: manifest["config"][name] for name in ("start", "end")}
    prepared = grid if grid is not None else build_grid(directory, manifest, cell_m)
    model = prepare_risk_model(
        directory,
        manifest,
        prepared,
        background_cost=background_cost,
        risk_weight=risk_weight,
        distance_weight=distance_weight,
        safety_distance_m=safety_distance_m,
    )
    connected = connect_endpoints(prepared, selected, safety_distance_m=safety_distance_m)
    result = plan_route(connected, algorithm=algorithm, risk_model=model)
    result["experiment"] = route_context(manifest, selected)
    result["experiment"]["optimality"] = (
        "Minimum weighted objective on the assessed constructed graph only."
    )
    return result
