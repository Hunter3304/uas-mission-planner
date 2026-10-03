"""Actual native ABIT* plus failure contracts; no network or acquired data."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from importlib.util import find_spec
from math import isclose
from threading import Event, Timer
from time import perf_counter
from types import SimpleNamespace

import pytest
from pyproj import Transformer
from shapely.geometry import LineString, box, mapping
from shapely.ops import transform

from uas_planner.core import abitstar
from uas_planner.core.abitstar import AbitPlanner, plan_abitstar
from uas_planner.core.grid import build_grid
from uas_planner.core.risk import RiskModel
from uas_planner.core.risk_routing import plan_risk_route
from uas_planner.route_demo import create_route_demo

native = pytest.mark.skipif(find_spec("ompl") is None, reason="Optional native OMPL absent")
reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform


def fixture(*, obstacle=False, wall=False, background=0, clearance=0):
    boundary = box(499990, 5799960, 500110, 5800080)
    obstacles = (
        [box(500045, 5799960 if wall else 5799970, 500055, 5800080 if wall else 5800030)]
        if obstacle or wall
        else []
    )
    building = box(500000, 5799999, 500020, 5800001)
    collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"building": "house", "element_type": "way", "osm_id": 1},
                "geometry": mapping(building),
            }
        ],
    }
    risk = RiskModel(
        collection,
        mapping(boundary),
        input_crs="EPSG:25832",
        background_cost=background,
        safety_distance_m=clearance,
    )
    grid = {
        "analysis_crs": "EPSG:25832",
        "policy": "block_unresolved",
        "assumptions": {},
        "validation": {
            "boundary": mapping(transform(reverse, boundary)),
            "blocked": [mapping(transform(reverse, g)) for g in obstacles],
            "unresolved": False,
        },
    }
    endpoints = {"start": list(reverse(500000, 5800000)), "end": list(reverse(500100, 5800000))}
    return grid, risk, endpoints, boundary, obstacles, building


def test_unavailable_and_preflight(monkeypatch):
    grid, risk, endpoints, *_ = fixture()
    monkeypatch.setattr(
        abitstar, "_load_ompl", lambda: (_ for _ in ()).throw(ImportError("missing native wheel"))
    )
    assert plan_abitstar(grid, risk, endpoints)["status"] == "planner_unavailable"
    grid["validation"]["unresolved"] = True
    assert plan_abitstar(grid, risk, endpoints)["status"] == "unresolved_input"
    grid["validation"]["unresolved"] = False
    endpoints["end"] = list(reverse(500200, 5800000))
    assert plan_abitstar(grid, risk, endpoints)["status"] == "invalid_endpoint"
    assert plan_abitstar(grid, risk, endpoints, cancel=lambda: True)["status"] == "cancelled"
    assert plan_abitstar(grid, risk, endpoints, time_budget_s=0)["status"] == "timeout"


@pytest.mark.parametrize("budget", [-1, float("nan"), float("inf"), True])
def test_invalid_budget(budget):
    with pytest.raises(ValueError, match="Planning time budget"):
        plan_abitstar(*fixture()[:3], time_budget_s=budget)


def test_unassessed_and_expired_preparation():
    grid, risk, endpoints, *_ = fixture(background=None)
    assert plan_abitstar(grid, risk, endpoints)["status"] == "unresolved_input"
    assert (
        plan_abitstar(grid, risk, endpoints, time_budget_s=1, started_at=perf_counter() - 2)[
            "status"
        ]
        == "timeout"
    )


@native
def test_saved_snapshot_entrypoint_and_unresolved_policy(tmp_path):
    directory = tmp_path / "demo"
    manifest = create_route_demo(directory)
    grid = build_grid(directory, manifest, 50)
    result = plan_risk_route(
        directory, manifest, grid=grid, algorithm="abitstar", background_cost=0, time_budget_s=2
    )
    assert result["status"] == "success", result
    assert result["risk_model"]["source"]["osm_sha256"]
    assert result["preparation_ms"] >= 0 and result["setup_ms"] >= 0
    assert "continuous-space" in result["experiment"]["optimality"]
    grid["validation"]["unresolved"] = True
    unresolved = plan_risk_route(
        directory, manifest, grid=grid, algorithm="abitstar", background_cost=0
    )
    assert unresolved["status"] == "unresolved_input" and unresolved["geometry"] is None


@native
def test_actual_detour_callbacks_and_independent_revalidation():
    grid, risk, endpoints, boundary, obstacles, building = fixture(obstacle=True, clearance=1)
    original = deepcopy(grid)
    planner = AbitPlanner(grid, risk, endpoints, time_budget_s=2)
    planner.initialize()
    assert isclose(planner.objective.motionCost(*planner.states).value(), 82, abs_tol=1e-6)
    assert isclose(planner.objective.motionCostHeuristic(*planner.states).value(), 10, abs_tol=1e-6)
    validator, si = planner.motion_validator, planner.simple_setup.getSpaceInformation()
    out = si.allocState()
    out[0], out[1] = 500007, 5800007
    assert validator.checkMotionWithLastValid(*planner.states, out, 0.75) == (False, 0)
    assert (out[0], out[1]) == (planner.states[0][0], planner.states[0][1])
    assert validator.checkMotionWithLastValid(*planner.states, None, 0.75) == (False, 0)
    safe = si.allocState()
    safe[0], safe[1] = 500010, 5800010
    out[0], out[1] = 500007, 5800007
    assert validator.checkMotionWithLastValid(planner.states[0], safe, out, 0.75) == (True, 0.75)
    assert (out[0], out[1]) == (500007, 5800007)
    result = planner.run()
    assert result["status"] == "success", result
    assert result["exact"] and result["solution_kind"] == "exact"
    assert all(result["callbacks"].values())
    assert result["geometry"]["coordinates"][0] == endpoints["start"]
    assert result["geometry"]["coordinates"][-1] == endpoints["end"]
    forward = Transformer.from_crs(4326, 25832, always_xy=True).transform
    points = [forward(*p) for p in result["geometry"]["coordinates"]]
    length = scored = 0
    for a, b in zip(points, points[1:]):
        line = LineString([a, b])
        assert boundary.covers(line.buffer(1))
        assert all(not line.buffer(1).intersects(g) for g in obstacles)
        length += line.length
        scored += 4 * line.intersection(building).length
    assert isclose(result["length_m"], length, abs_tol=1e-6)
    assert isclose(result["risk_length_cost"], scored, abs_tol=1e-6)
    assert isclose(result["objective_cost"], 0.9 * scored + 0.1 * length, abs_tol=1e-6)
    assert result["runtime_ms"] < 3500
    assert grid == original
    with pytest.raises(RuntimeError, match="new planner"):
        planner.run()


@native
def test_cancellation_during_native_search_and_impossible_wall():
    grid, risk, endpoints, *_ = fixture(wall=True)
    event = Event()
    timer = Timer(0.08, event.set)
    timer.start()
    try:
        result = plan_abitstar(grid, risk, endpoints, cancel=event.is_set, time_budget_s=3)
    finally:
        timer.cancel()
        timer.join()
    assert result["status"] == "cancelled" and result["geometry"] is None
    assert result["runtime_ms"] < 1500
    timed = plan_abitstar(grid, risk, endpoints, time_budget_s=0.15)
    assert timed["status"] in ("timeout", "approximate_solution")
    assert not timed["exact"] and timed["geometry"] is None


@native
def test_zero_length_and_concurrent_independent_tasks():
    def task(y):
        grid, risk, endpoints, *_ = fixture()
        endpoints["start"] = list(reverse(500000, 5800000 + y))
        endpoints["end"] = list(reverse(500100, 5800000 + y))
        return plan_abitstar(grid, risk, endpoints, time_budget_s=0.6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(task, [10, 20]))
    assert all(r["status"] == "success" for r in results), results
    assert results[0]["start"] != results[1]["start"]
    grid, risk, endpoints, *_ = fixture()
    endpoints["end"] = endpoints["start"][:]
    zero = plan_abitstar(grid, risk, endpoints, time_budget_s=0.2)
    assert zero["status"] == "success" and zero["objective_cost"] == 0


def test_approximate_candidate_is_never_success_and_final_validation_failure(monkeypatch):
    grid, risk, endpoints, *_ = fixture()
    planner = AbitPlanner(grid, risk, endpoints)
    planner.ob = SimpleNamespace(PlannerTerminationCondition=lambda f: f)
    planner.simple_setup = SimpleNamespace(
        solve=lambda _: "Approximate solution",
        getProblemDefinition=lambda: SimpleNamespace(
            hasExactSolution=lambda: False, hasSolution=lambda: True
        ),
        getSolutionPath=lambda: None,
    )
    monkeypatch.setattr(
        planner,
        "_validate_path",
        lambda p, e: {
            "geometry": {
                "type": "LineString",
                "coordinates": [endpoints["start"], endpoints["start"]],
            }
        },
    )
    result = planner.run()
    assert result["status"] == "approximate_solution"
    assert not result["exact"] and result["geometry"] is None and result["candidate"]
    broken = AbitPlanner(grid, risk, endpoints)
    broken.ob, broken.simple_setup = planner.ob, planner.simple_setup
    monkeypatch.setattr(
        broken,
        "_validate_path",
        lambda p, e: (_ for _ in ()).throw(ValueError("Final path invalid")),
    )
    failed = broken.run()
    assert failed["status"] == "computational_failure" and failed["geometry"] is None


def test_actual_final_validator_rejects_obstacle_crossing():
    grid, risk, endpoints, *_ = fixture(obstacle=True)
    planner = AbitPlanner(grid, risk, endpoints)
    crossing = SimpleNamespace(
        getStateCount=lambda: 2, getState=lambda i: [(500000, 5800000), (500100, 5800000)][i]
    )
    with pytest.raises(ValueError, match="full constraint"):
        planner._validate_path(crossing, exact=True)
