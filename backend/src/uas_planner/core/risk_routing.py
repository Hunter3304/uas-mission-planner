"""Compatibility entry point for weighted saved-data planning."""


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
    time_budget_s=3,
    cancel=None,
    planning_mode="strict",
):
    """Compatibility entry point using shared readiness, timing and research controls."""
    from uas_planner.core.planning import plan_saved_route

    return plan_saved_route(
        directory,
        manifest,
        grid=grid,
        cell_m=cell_m,
        endpoints=endpoints,
        algorithm=algorithm,
        objective="risk",
        background_cost=background_cost,
        risk_weight=risk_weight,
        distance_weight=distance_weight,
        safety_distance_m=safety_distance_m,
        time_budget_s=time_budget_s,
        cancel=cancel,
        planning_mode=planning_mode,
    )
