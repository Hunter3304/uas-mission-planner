"""Readiness takes precedence over native setup; research is explicit and isolated."""

from copy import deepcopy
from time import perf_counter

import pytest
from fastapi.testclient import TestClient

from uas_planner.api.app import create_app
from uas_planner.core import abitstar
from uas_planner.core.grid import build_grid
from uas_planner.core.planning import plan_saved_route
from uas_planner.core.research import planning_grid
from uas_planner.core.routing import route_geojson
from uas_planner.route_demo import create_route_demo


@pytest.fixture
def snapshot(tmp_path):
    path = tmp_path / "research-demo"
    manifest = create_route_demo(path, low_risk=True)
    # Use real-adapter constraint semantics on explicitly synthetic test data.
    manifest.pop("routing_fixture")
    return path, manifest


@pytest.mark.parametrize("algorithm", ["astar", "dijkstra", "abitstar"])
def test_strict_readiness_precedes_zero_budget_and_native_import(snapshot, algorithm, monkeypatch):
    path, manifest = snapshot
    monkeypatch.setattr(
        abitstar, "plan_abitstar", lambda *a, **kw: pytest.fail("Native solver called")
    )
    result = plan_saved_route(path, manifest, algorithm=algorithm, time_budget_s=0)
    assert result["status"] == "unresolved_input"
    assert "Temporary restriction" in result["message"]
    assert result["planner_ms"] == 0
    assert result["readiness"]["global_reasons"]
    invalid = plan_saved_route(
        path,
        manifest,
        algorithm=algorithm,
        time_budget_s=0,
        endpoints={"start": [10.5, 52.25], "end": manifest["config"]["end"]},
    )
    assert invalid["status"] == "invalid_endpoint"


def test_research_routes_match_and_cached_strict_grid_is_unchanged(snapshot):
    path, manifest = snapshot
    grid = build_grid(path, manifest, 25)
    before = deepcopy(grid)
    results = [
        plan_saved_route(
            path,
            manifest,
            grid=grid,
            cell_m=25,
            planning_mode="research",
            objective="risk",
            background_cost=0,
            algorithm=a,
        )
        for a in ("astar", "dijkstra")
    ]
    assert grid == before
    assert all(r["status"] == "success" for r in results)
    assert results[0]["objective_cost"] == pytest.approx(results[1]["objective_cost"])
    assert results[0]["geometry"]["coordinates"][0] == manifest["config"]["start"]
    exported = route_geojson(results[0])
    assert exported["metadata"]["planning_mode"] == "research"
    assert exported["metadata"]["research_assumptions"]
    assert exported["metadata"]["experiment"]["synthetic"] is True
    assert plan_saved_route(path, manifest, grid=grid)["status"] == "unresolved_input"


def test_research_retains_obstacles_terrain_and_corner_checks(snapshot):
    path, manifest = snapshot
    grid = build_grid(path, manifest, 25)
    cell = next(c for c in grid["cells"] if c["terrain_m"] is not None)
    grid["validation"]["blocked"] = [cell["geometry"]]
    missing = grid["cells"][-1]
    missing["terrain_m"] = None
    result = planning_grid(grid, "research", manifest["config"])
    cells = {c["id"]: c for c in result["cells"]}
    assert cells[cell["id"]]["state"] == "blocked"
    assert cells[missing["id"]]["state"] in ("blocked", "unresolved")
    assert missing["geometry"] in result["validation"]["unresolved_regions"]
    for edge in result["edges"]:
        if edge["from"] in (cell["id"], missing["id"]) or edge["to"] in (cell["id"], missing["id"]):
            assert edge["state"] != "permitted"


def test_search_budget_is_not_reduced_by_preparation(snapshot, monkeypatch):
    path, manifest = snapshot
    seen = {}

    def solve(grid, model, endpoints, **options):
        seen.update(options)
        return {
            "status": "timeout",
            "algorithm": "abitstar",
            "geometry": None,
            "objective": "risk",
            "rules_version": "test",
            "length_m": None,
        }

    monkeypatch.setattr(abitstar, "plan_abitstar", solve)
    result = plan_saved_route(
        path,
        manifest,
        planning_mode="research",
        algorithm="abitstar",
        background_cost=0,
        objective="risk",
        time_budget_s=3,
        started_at=perf_counter() - 10,
    )
    assert seen == {"time_budget_s": 3}
    assert result["preparation_ms"] >= 10000


def test_api_mode_validation_and_export(snapshot):
    path, manifest = snapshot
    from uas_planner.core.experiment import write_json

    write_json(path / "experiment.json", manifest)
    client = TestClient(create_app(path.parent))
    url = "/api/datasets/research-demo/experiment/route"
    assert client.get(url).json()["status"] == "unresolved_input"
    assert client.get(url, params={"planning_mode": "bad"}).status_code == 422
    result = client.get(url, params={"planning_mode": "research", "export": True}).json()
    assert result["features"]
    assert result["metadata"]["constraint_validation"] == "research_assumptions"


def test_nonpolygon_building_policy_is_explicit_and_preserves_diagnostics():
    from shapely.geometry import box, mapping

    from uas_planner.core.risk import RiskModel

    collection = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [10.52, 52.27]},
                "properties": {"building": "house", "element_type": "node", "osm_id": 7},
            }
        ],
    }
    boundary = mapping(box(10.519, 52.269, 10.522, 52.272))
    strict = RiskModel(collection, boundary, background_cost=0)
    research = RiskModel(
        collection, boundary, background_cost=0, unsupported_policy="polygon_only_research"
    )
    assert strict.evaluate([[10.5195, 52.2695]])["assessment"] == "unresolved"
    assert research.evaluate([[10.5195, 52.2695]])["assessment"] == "assessed"
    assert research.provenance["unsupported_geometry_policy"] == "polygon_only_research"
    assert research.diagnostics == [{"id": "node/7", "status": "unsupported_geometry"}]
    with pytest.raises(ValueError):
        RiskModel(collection, boundary, unsupported_policy="silent")


def test_unassessed_grid_connector_reports_local_reason_before_search(snapshot, monkeypatch):
    from shapely.geometry import box, mapping

    from uas_planner.core import planning, routing
    from uas_planner.core.risk import RiskModel

    path, manifest = snapshot
    grid = build_grid(path, manifest, 25)
    prepared = planning_grid(grid, "research", manifest["config"])
    cell_id = prepared["connectors"][0]["cell"]
    lon, lat = next(c["center"] for c in prepared["cells"] if c["id"] == cell_id)
    model = RiskModel(
        {
            "features": [
                {
                    "properties": {"building": "house", "osm_id": 123},
                    "geometry": mapping(
                        box(lon - 0.000001, lat - 0.000001, lon + 0.000001, lat + 0.000001)
                    ),
                }
            ]
        },
        prepared["validation"]["boundary"],
        background_cost=0,
    )
    model.records[0]["cost"] = None
    monkeypatch.setattr(planning, "prepare_risk_model", lambda *a, **kw: model)
    monkeypatch.setattr(routing, "search_graph", lambda *a, **kw: pytest.fail("Search started"))
    result = plan_saved_route(
        path, manifest, grid=grid, planning_mode="research", objective="risk", background_cost=0
    )
    assert result["status"] == "unresolved_input"
    assert "Endpoint-to-grid connector" in result["message"]
    assert result["readiness"]["endpoint_reasons"][0]["endpoint"] == "start"
    assert result["planner_ms"] == 0
