"""Exercise the actual official ABIT* binding with the project's metric core."""

import json
from math import isclose
from pathlib import Path
from time import perf_counter

from ompl import base as ob
from ompl import geometric as og
from ompl import util as ou
from pyproj import Transformer
from shapely.geometry import LineString, Point, box, mapping
from shapely.ops import transform

from uas_planner.core.risk import RiskModel
from uas_planner.core.routing import constraint_checker


OFFSET = (500000, 5800000)
reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform


def metric(point):
    return (point[0] + OFFSET[0], point[1] + OFFSET[1])


def geographic(point):
    return reverse(*metric(point))


def local_box(x1, y1, x2, y2):
    return box(x1 + OFFSET[0], y1 + OFFSET[1], x2 + OFFSET[0], y2 + OFFSET[1])


def coords(state):
    return (state[0], state[1])


def build_fixture(obstacle=False, clearance=0):
    boundary = local_box(-10, -40, 110, 80)
    blocked = [local_box(45, -30, 55, 30)] if obstacle else []
    feature = {
        "type": "Feature",
        "properties": {"element_type": "way", "osm_id": 1, "building": "house"},
        "geometry": mapping(local_box(0, -1, 20, 1)),
    }
    risk = RiskModel(
        {"type": "FeatureCollection", "features": [feature]},
        mapping(boundary), input_crs="EPSG:25832", background_cost=0,
        safety_distance_m=clearance,
    )
    grid = {
        "analysis_crs": "EPSG:25832",
        "validation": {
            "boundary": mapping(transform(reverse, boundary)),
            "blocked": [mapping(transform(reverse, g)) for g in blocked],
            "unresolved": False,
        },
    }
    check = constraint_checker(grid, clearance)
    return risk, check, boundary, blocked


def context(obstacle=False, clearance=0):
    risk, check, boundary, blocked = build_fixture(obstacle, clearance)
    counters = {"state": 0, "motion": 0, "cost": 0, "heuristic": 0, "cost_to_go": 0}
    space = ob.RealVectorStateSpace(2)
    bounds = ob.RealVectorBounds(2)
    bounds.setLow(0, -10)
    bounds.setHigh(0, 110)
    bounds.setLow(1, -40)
    bounds.setHigh(1, 80)
    space.setBounds(bounds)
    setup = og.SimpleSetup(space)
    si = setup.getSpaceInformation()

    class StateValidator(ob.StateValidityChecker):
        def isValid(self, state):
            counters["state"] += 1
            return check([geographic(coords(state))]) == "permitted"

    class MotionValidator(ob.MotionValidator):
        def checkMotion(self, start, end):
            counters["motion"] += 1
            return check([geographic(coords(start)), geographic(coords(end))]) == "permitted"

    class Objective(ob.OptimizationObjective):
        def stateCost(self, state):
            return ob.Cost(0)

        def motionCost(self, start, end):
            counters["cost"] += 1
            result = risk.evaluate([metric(coords(start)), metric(coords(end))],
                                   input_crs="EPSG:25832")
            assert result["assessment"] == "assessed"
            return ob.Cost(result["objective_cost"])

        def motionCostHeuristic(self, start, end):
            counters["heuristic"] += 1
            return ob.Cost(0.1 * si.distance(start, end))

    state_validator = StateValidator(si)
    motion_validator = MotionValidator(si)
    objective = Objective(si)
    def cost_to_go(state, goal):
        counters["cost_to_go"] += 1
        return ob.Cost(0.1 * max(0.0, goal.distanceGoal(state) - goal.getThreshold()))
    objective.setCostToGoHeuristic(cost_to_go)
    setup.setStateValidityChecker(state_validator)
    si.setMotionValidator(motion_validator)
    setup.setOptimizationObjective(objective)
    planner = og.ABITstar(si)
    planner.setSamplesPerBatch(100)
    setup.setPlanner(planner)

    def state(point):
        result = si.allocState()
        result[0], result[1] = point
        return result

    start, goal = state((0, 0)), state((100, 0))
    setup.setStartAndGoalStates(start, goal)
    setup.setup()
    # Explicit references retain Python subclasses for the entire C++ solve.
    return locals()


def independent_cost(points):
    building = local_box(0, -1, 20, 1)
    length = risk = 0.0
    for start, end in zip(points, points[1:]):
        geometry = LineString([metric(start), metric(end)])
        length += geometry.length
        risk += 4 * geometry.intersection(building).length
    return {"length_m": length, "risk_length_cost": risk,
            "objective_cost": 0.9 * risk + 0.1 * length}


def run():
    ou.RNG.setSeed(13)
    analytical = context()
    si = analytical["si"]
    objective = analytical["objective"]
    assert isclose(objective.motionCost(analytical["start"], analytical["goal"]).value(), 82)
    assert isclose(objective.motionCostHeuristic(analytical["start"], analytical["goal"]).value(), 10)

    fixture = context(obstacle=True, clearance=1)
    si, validator = fixture["si"], fixture["motion_validator"]
    start, goal, state = fixture["start"], fixture["goal"], fixture["state"]
    assert si.isValid(start) and si.isValid(goal)
    assert not si.checkMotion(start, goal)
    assert not si.isValid(state((44.5, 0)))  # partial overlap of positive clearance
    assert not si.isValid(state((45, 0)))  # obstacle boundary contact
    output = state((7, 7))
    valid, fraction = validator.checkMotionWithLastValid(start, goal, output, 0.75)
    assert not valid and fraction == 0 and coords(output) == coords(start)
    output[0], output[1] = (7, 7)
    valid, fraction = validator.checkMotionWithLastValid(start, state((10, 10)), output, 0.75)
    assert valid and fraction == 0.75 and coords(output) == (7, 7)
    valid, fraction = validator.checkMotionWithLastValid(start, goal, None, 0.75)
    assert not valid and fraction == 0

    deadline = perf_counter() + 3
    termination_calls = 0

    def terminated():
        nonlocal termination_calls
        termination_calls += 1
        return perf_counter() >= deadline

    t0 = perf_counter()
    status = fixture["setup"].solve(ob.PlannerTerminationCondition(terminated))
    elapsed = perf_counter() - t0
    pdef = fixture["setup"].getProblemDefinition()
    assert pdef.hasExactSolution(), str(status)
    path = fixture["setup"].getSolutionPath()
    points = [coords(path.getState(i)) for i in range(path.getStateCount())]
    assert points[0] == (0, 0) and points[-1] == (100, 0)
    for a, b in zip(points, points[1:]):
        assert fixture["check"]([geographic(a), geographic(b)]) == "permitted"
        # Independent full-geometry recheck without the shared checker.
        envelope = LineString([metric(a), metric(b)]).buffer(1)
        assert fixture["boundary"].covers(envelope)
        assert not any(g.intersects(envelope) for g in fixture["blocked"])
    cost = independent_cost(points)
    reported = path.cost(fixture["objective"]).value()
    assert isclose(cost["objective_cost"], reported, rel_tol=1e-9, abs_tol=1e-7)
    assert isclose(cost["length_m"], path.length(), rel_tol=1e-9)
    assert all(fixture["counters"][name] > 0 for name in ("state", "motion", "cost", "heuristic", "cost_to_go"))
    assert termination_calls > 0 and elapsed < 5
    cancellation = context(obstacle=True)
    cancel_start = perf_counter()
    cancelled = cancellation["setup"].solve(ob.PlannerTerminationCondition(lambda: True))
    cancel_elapsed = perf_counter() - cancel_start
    assert not cancellation["setup"].getProblemDefinition().hasExactSolution()
    assert cancel_elapsed < 0.25
    result = {"planner": fixture["planner"].getName(), "status": str(status),
              "exact": True, "runtime_s": elapsed, "cost": cost,
              "callbacks": fixture["counters"], "termination_calls": termination_calls,
              "cancelled_status": str(cancelled), "cancellation_s": cancel_elapsed,
              "checks": {"known_segment_objective": 82, "motion_heuristic": 10,
                         "last_valid_success_failure_null": True,
                         "independent_path_clearance_m": 1, "independent_cost": True},
              "path": points}
    Path(__file__).with_name("probe-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run()
