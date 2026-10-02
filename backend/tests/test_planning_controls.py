"""Public controls, export contracts and independently scored comparisons."""

import json
import subprocess
import sys
from importlib.util import find_spec
from math import isclose
from weakref import ref

import pytest
from fastapi.testclient import TestClient

from uas_planner.api.app import create_app
from uas_planner.cli import main
from uas_planner.core import abitstar
from uas_planner.core.comparison import compare_routes
from uas_planner.core.experiment import write_json
from uas_planner.core.grid import build_grid
from uas_planner.core.planning import plan_saved_route
from uas_planner.core.routing import plan_route, route_geojson
from uas_planner.route_demo import create_route_demo

native = pytest.mark.skipif(find_spec("ompl") is None, reason="Optional native OMPL absent")


@pytest.fixture
def demo(tmp_path):
    directory = tmp_path / "risk-demo"
    manifest = create_route_demo(directory, low_risk=True)
    return directory, manifest


def test_compatible_default_and_weighted_detour(demo):
    directory, manifest = demo
    grid = build_grid(directory, manifest, 25)
    old = plan_route(grid)
    default = plan_saved_route(directory, manifest, grid=grid, cell_m=25)
    assert old["geometry"] == default["geometry"]
    assert old["length_m"] == default["length_m"]
    assert default["objective"] == "distance" and default["exact"]
    assert default["risk_length_cost"] is None
    weighted = [
        plan_saved_route(
            directory, manifest, cell_m=25, objective="risk", algorithm=a, background_cost=0
        )
        for a in ("astar", "dijkstra")
    ]
    assert all(r["status"] == "success" for r in weighted)
    assert weighted[0]["length_m"] > default["length_m"]
    assert isclose(weighted[0]["objective_cost"], weighted[1]["objective_cost"])
    assert weighted[0]["risk_length_cost"] == 0
    exported = route_geojson(weighted[0])
    assert exported["metadata"]["controls"]["background_cost"] == 0
    assert exported["metadata"]["risk_model"]["source"]["synthetic"]


def test_api_parameters_exports_and_unresolved(demo):
    directory, manifest = demo
    client = TestClient(create_app(directory.parent))
    url = "/api/datasets/risk-demo/experiment/route"
    params = {
        "algorithm": "dijkstra",
        "objective": "risk",
        "background_cost": 0,
        "risk_weight": 0.7,
        "distance_weight": 0.3,
        "safety_distance_m": 2,
    }
    result = client.get(url, params=params).json()
    assert result["exact"] and result["algorithm"] == "dijkstra"
    assert result["controls"]["effective_weights"] == {"risk": 0.7, "distance": 0.3}
    exported = client.get(url, params={**params, "export": True}).json()
    assert exported["features"][0]["geometry"] == result["geometry"]
    for invalid in (
        {"algorithm": "bad"},
        {"objective": "bad"},
        {"time_budget_s": 61},
        {"risk_weight": "nan"},
        {"safety_distance_m": -1},
        {"risk_weight": 0, "distance_weight": 0, "objective": "risk"},
    ):
        assert client.get(url, params=invalid).status_code == 422
    assert client.get(url, params={"objective": "risk"}).json()["status"] == "unresolved_input"
    manifest.pop("routing_fixture")
    manifest["synthetic"] = False
    write_json(directory / "experiment.json", manifest)
    result = client.get(url, params=params).json()
    assert result["status"] == "unresolved_input" and not result["exact"]


def test_cli_controls_and_no_overwrite(demo, tmp_path, capsys):
    directory, _ = demo
    output = tmp_path / "route.geojson"
    args = [
        "experiment-route",
        str(directory),
        "--algorithm",
        "dijkstra",
        "--objective",
        "risk",
        "--background-cost",
        "0",
        "--cell-m",
        "25",
        "--output",
        str(output),
    ]
    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert json.loads(output.read_text())["metadata"] == {
        k: v for k, v in result.items() if k != "geometry"
    }
    before = output.read_bytes()
    assert main(args) == 1
    assert output.read_bytes() == before
    assert main(["experiment-route", str(directory), "--time-budget-s", "nan"]) == 1


def test_unavailable_comparison_and_budget_limits(demo, monkeypatch):
    directory, manifest = demo
    monkeypatch.setattr(
        abitstar, "_load_ompl", lambda: (_ for _ in ()).throw(ImportError("absent"))
    )
    report = compare_routes(directory, manifest, background_cost=0, repetitions=2)
    assert report["status"] == "incomplete"
    assert (
        report["runs"][0]["comparison_costs"]["objective_cost"]
        > report["runs"][1]["comparison_costs"]["objective_cost"]
    )
    assert all(r["result"]["status"] == "planner_unavailable" for r in report["runs"][3:])
    assert report["abitstar_summary"]["verified_exact_solution_rate"] == 0
    for options in ({"repetitions": 11}, {"time_budget_s": 31, "repetitions": 2}):
        with pytest.raises(ValueError):
            compare_routes(directory, manifest, **options)
    client = TestClient(create_app(directory.parent))
    response = client.get(
        "/api/datasets/risk-demo/experiment/compare",
        params={"background_cost": 0, "repetitions": 1, "start_lon": 0, "start_lat": 0},
    )
    assert response.status_code == 200
    assert all(r["result"]["status"] == "invalid_endpoint" for r in response.json()["runs"])


def test_comparison_rejects_corrupted_costs_and_wrong_endpoints(demo, monkeypatch):
    from uas_planner.core import comparison

    directory, manifest = demo
    real_plan = comparison.plan_saved_route

    def corrupted(*args, **options):
        result = real_plan(*args, **options)
        if result["exact"] and options["algorithm"] == "astar":
            result["length_m"] += 1
        elif result["exact"] and options["algorithm"] == "dijkstra":
            # Claim a different goal consistently in both result and geometry.
            # Independent verification must compare with the requested mission.
            wrong_end = result["geometry"]["coordinates"][-2]
            result["geometry"]["coordinates"][-1] = wrong_end
            result["end"] = wrong_end
        return result

    monkeypatch.setattr(comparison, "plan_saved_route", corrupted)
    report = compare_routes(directory, manifest, background_cost=0, repetitions=1, time_budget_s=0)
    assert [r["comparison_costs"]["status"] for r in report["runs"][:3]] == [
        "failed_costs",
        "failed_costs",
        "failed_constraints",
    ]
    assert report["status"] == "incomplete"


@native
def test_native_comparison_and_distance_without_risk_assessment(demo):
    directory, manifest = demo
    report = compare_routes(directory, manifest, background_cost=0, repetitions=2, time_budget_s=1)
    assert report["status"] == "complete", report
    assert report["abitstar_summary"]["verified_exact_solution_rate"] == 1
    assert len(report["abitstar_summary"]["objective_distribution"]["values"]) == 2
    distance = plan_saved_route(directory, manifest, algorithm="abitstar", time_budget_s=0.5)
    assert distance["exact"] and distance["objective"] == "distance"
    assert distance["risk_length_cost"] is None and "risk_model" not in distance
    assert distance["experiment"]["connector_policy"] == "Exact endpoints in continuous space."


@native
def test_callback_lifetime_does_not_retain_owner():
    from test_abitstar import fixture

    planner = abitstar.AbitPlanner(*fixture()[:3])
    planner.initialize()
    reference = ref(planner)
    del planner
    assert reference() is None


@native
def test_native_cli_stdout_is_json(demo):
    directory, _ = demo
    process = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "uas_planner.cli",
            "experiment-route",
            str(directory),
            "--algorithm",
            "abitstar",
            "--time-budget-s",
            "0.5",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["exact"]
    assert "leaked" not in process.stderr
