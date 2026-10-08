"""Independent costs, constraints, shared adapters and explicit regional outcomes."""

import json
from copy import deepcopy
from importlib.util import find_spec
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pyproj import Transformer
from shapely.geometry import LineString, Point, box, mapping
from shapely.ops import transform

from uas_planner.core import regional_routing as routing
from uas_planner.core.risk import RiskModel
from uas_planner.core.routing import route_geojson


@pytest.fixture
def planner(monkeypatch):
    reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform

    class FixtureConstraints:
        def __init__(self, directory, scenario, **kwargs):
            self.terrain = SimpleNamespace(close=lambda: None)
            self.scenario = deepcopy(scenario)
            self.boundary = box(500000, 5800000, 500400, 5800400)
            self.manifest = {
                "config": {
                    "locations": [
                        {"id": ident, "longitude": reverse(x, y)[0], "latitude": reverse(x, y)[1]}
                        for ident, x, y in (("a", 500025, 5800225), ("b", 500375, 5800225))
                    ]
                }
            }
            self.provenance = {
                "synthetic": True,
                "model_signature": "synthetic-regional-test",
                "scenario": self.scenario,
            }
            self.queries = []
            self.forced = None

        def check(self, coordinates, mode="strict"):
            self.queries.append(coordinates)
            points = [
                Transformer.from_crs(4326, 25832, always_xy=True).transform(*p) for p in coordinates
            ]
            geometry = Point(points[0]) if len(points) == 1 else LineString(points)
            state = self.forced or ("permitted" if self.boundary.covers(geometry) else "blocked")
            return {
                "state": state,
                "blocked": [{"reason": "synthetic blocked"}] if state == "blocked" else [],
                "unresolved": [{"reason": "synthetic missing terrain"}]
                if state == "unresolved"
                else [],
                "assumptions": [],
            }

        def risk_model(self, **kwargs):
            kwargs.pop("mode", None)
            kwargs.pop("search_boundary", None)
            return RiskModel(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": mapping(
                                transform(reverse, box(500100, 5800100, 500300, 5800300))
                            ),
                            "properties": {"building": "hospital"},
                        }
                    ],
                },
                mapping(transform(reverse, self.boundary)),
                safety_distance_m=self.scenario.get("clearance_m", 0),
                **kwargs,
            )

    monkeypatch.setattr(routing, "RegionalConstraints", FixtureConstraints)
    return routing.RegionalPlanner("unused", {"agl_m": 100, "speed_m_s": 30, "clearance_m": 0})


def test_weighted_graph_agreement_and_distance_baseline(planner):
    options = {"cell_m": 50, "background_cost": 0}
    a = planner.plan("a", "b", algorithm="astar", **options)
    d = planner.plan("a", "b", algorithm="dijkstra", **options)
    baseline = planner.plan("a", "b", objective="distance", **options)
    assert a["status"] == d["status"] == baseline["status"] == "success"
    assert a["independent_validation"]
    assert a["objective_cost"] == pytest.approx(d["objective_cost"])
    assert a["objective_cost"] == pytest.approx(0.9 * a["risk_length_cost"] + 0.1 * a["length_m"])
    risk = planner.constraints.risk_model(background_cost=0)
    path = baseline["geometry"]["coordinates"]
    assert a["risk_length_cost"] < sum(
        risk.evaluate([u, v])["risk_length_cost"] for u, v in zip(path, path[1:])
    )
    assert a["length_m"] > baseline["length_m"]
    assert a["cruise_time_s"] == pytest.approx(a["length_m"] / 30)
    assert json.loads(json.dumps(route_geojson(a)))["metadata"]["mission"]["start_id"] == "a"


@pytest.mark.parametrize("algorithm", ["astar", "dijkstra", "abitstar"])
def test_unresolved_and_blocked_preflight(planner, algorithm):
    planner.constraints.forced = "unresolved"
    result = planner.plan("a", "b", algorithm=algorithm)
    assert result["status"] == "unresolved_input" and result["planner_ms"] == 0
    planner.constraints.forced = "blocked"
    assert planner.plan("a", "b", algorithm=algorithm)["status"] == "invalid_endpoint"


@pytest.mark.skipif(find_spec("ompl") is None, reason="Optional native OMPL absent")
def test_native_shared_checker_and_validation(planner):
    result = planner.plan("a", "b", algorithm="abitstar", background_cost=0, time_budget_s=0.5)
    assert result["status"] == "success"
    assert result["independent_validation"]
    assert result["geometry"]["coordinates"][0] == result["start"]
    assert result["randomness"]["seed_supported"] is False


def test_grid_limit_and_inputs(planner):
    assert planner.plan("a", "b", cell_m=0.1, objective="distance")["status"] == "resource_limit"
    with pytest.raises(ValueError):
        planner.plan("missing", "b")
    with pytest.raises(ValueError):
        planner.plan("a", "b", time_budget_s=61)


def test_subdivision_checks_entire_motion(planner):
    reverse = planner.reverse
    planner.check([reverse(500000, 5800000), reverse(502000, 5802000)], "research")
    assert len(planner.constraints.queries) == 6
    for piece in planner.constraints.queries:
        line = transform(planner.forward, LineString(piece))
        assert line.length <= 500.000001


def test_api_and_cli_share_core(planner, tmp_path, monkeypatch, capsys):
    from uas_planner.api.app import create_app
    from uas_planner.cli import main

    monkeypatch.setattr(routing, "RegionalPlanner", lambda *a, **kw: planner)
    (tmp_path / "study").mkdir()
    request = {
        "scenario": planner.constraints.scenario,
        "start_id": "a",
        "end_id": "b",
        "cell_m": 50,
        "background_cost": 0,
    }
    with TestClient(create_app(tmp_path)) as client:
        result = client.post("/api/datasets/study/study/route", json=request)
        assert result.status_code == 200 and result.json()["status"] == "success"
        exported = client.post("/api/datasets/study/study/route", json={**request, "export": True})
        assert exported.json()["metadata"]["objective_cost"] == pytest.approx(
            result.json()["objective_cost"]
        )
        assert (
            client.post(
                "/api/datasets/study/study/route", json={**request, "terrain_id": "../escape"}
            ).status_code
            == 404
        )
    scenario = tmp_path / "scenario.json"
    scenario.write_text(json.dumps(request["scenario"]))
    assert (
        main(
            [
                "study-route",
                str(tmp_path / "study"),
                "--scenario",
                str(scenario),
                "--start-id",
                "a",
                "--end-id",
                "b",
                "--cell-m",
                "50",
                "--background-cost",
                "0",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["objective_cost"] == pytest.approx(
        result.json()["objective_cost"]
    )


def test_independent_validation_rejects_corruption(planner, monkeypatch):
    original = routing.plan_route

    def corrupt(*args, **kwargs):
        result = original(*args, **kwargs)
        result["objective_cost"] += 1
        return result

    monkeypatch.setattr(routing, "plan_route", corrupt)
    result = planner.plan("a", "b", cell_m=50, background_cost=0)
    assert result["status"] == "computational_failure"
    assert result["geometry"] is None and result["length_m"] is None


def test_speed_changes_only_time_and_same_site(planner):
    a = planner.plan("a", "b", cell_m=50, objective="distance")
    planner.constraints.scenario["speed_m_s"] = 35
    b = planner.plan("a", "b", cell_m=50, objective="distance")
    assert a["geometry"] == b["geometry"] and a["objective_cost"] == b["objective_cost"]
    assert b["cruise_time_s"] == pytest.approx(b["length_m"] / 35)
    same = planner.plan("a", "a", cell_m=50, objective="distance")
    assert same["status"] == "success" and same["length_m"] == 0


def test_preparation_deadline_is_explicit(planner, monkeypatch):
    ticks = iter([0, 31])
    monkeypatch.setattr(routing, "perf_counter", lambda: next(ticks))
    grid, reason = planner.grid({}, 50, "strict", lambda points: "permitted")
    assert grid is None and "30 seconds" in reason


def test_native_unavailability_and_zero_budget(planner, monkeypatch):
    from uas_planner.core import abitstar

    def unavailable():
        raise ImportError("Test unavailable native runtime")

    monkeypatch.setattr(abitstar, "_load_ompl", unavailable)
    result = planner.plan("a", "b", algorithm="abitstar", objective="distance")
    assert result["status"] == "planner_unavailable"
    assert (
        planner.plan("a", "b", algorithm="abitstar", objective="distance", time_budget_s=0)[
            "status"
        ]
        == "timeout"
    )


def test_explicit_endpoint_override_is_validated_and_exported(planner):
    original = planner.constraints.manifest["config"]["locations"][0]
    override = list(planner.reverse(500040, 5800200))
    result = planner.plan("a", "b", objective="distance", cell_m=50, start_coordinate=override)
    assert result["status"] == "success"
    assert result["geometry"]["coordinates"][0] == override
    assert result["endpoint_overrides"]["start"] == override
    assert result["catalog_endpoints"]["start"] == [original["longitude"], original["latitude"]]
    with pytest.raises(ValueError):
        planner.plan("a", "b", start_coordinate=[190, 52])
    assert planner.plan("a", "b", start_coordinate=[9, 52])["status"] == "invalid_endpoint"


def test_corridor_expands_after_no_path_and_reports_attempts(planner, monkeypatch):
    original = routing.plan_route
    calls = 0

    def first_failure(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {
                "status": "no_path_on_grid",
                "message": "Initial corridor has no path.",
                "geometry": None,
                "length_m": None,
                "objective_cost": None,
                "risk_length_cost": None,
            }
        return original(*args, **kwargs)

    monkeypatch.setattr(routing, "plan_route", first_failure)
    result = planner.plan("a", "b", objective="distance", cell_m=50, corridor_margin_m=100)
    assert result["status"] == "success"
    assert len(result["search_attempts"]) == 2
    assert result["independent_validation"]
    assert "message" not in result
