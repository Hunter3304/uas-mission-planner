"""Hand-computed graph cases, independent geometry checks and real API round trips."""

from math import hypot, sqrt

import numpy as np
import pytest
import rasterio
from experiment_fixture import create_experiment_fixture
from fastapi.testclient import TestClient
from pyproj import Transformer
from shapely.geometry import box, mapping
from shapely.ops import transform

from uas_planner.api.app import create_app
from uas_planner.cli import main
from uas_planner.core.experiment import checksum, read_json, write_json
from uas_planner.core.grid import build_grid
from uas_planner.core.routing import connect_endpoints, constraint_checker, plan_route, search_graph
from uas_planner.route_demo import create_route_demo


def metric_graph(n=3):
    reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform
    cells, edges = [], []
    for row in range(n):
        for col in range(n):
            x, y = 500000 + col * 50, 5800000 + row * 50
            cells.append(
                {
                    "id": f"{row}:{col}",
                    "row": row,
                    "col": col,
                    "center": list(reverse(x, y)),
                    "geometry": mapping(transform(reverse, box(x - 25, y - 25, x + 25, y + 25))),
                    "state": "permitted",
                    "reasons": [],
                }
            )
            for dr, dc in ((0, 1), (1, -1), (1, 0), (1, 1)):
                if 0 <= row + dr < n and 0 <= col + dc < n:
                    edges.append(
                        {
                            "from": f"{row}:{col}",
                            "to": f"{row + dr}:{col + dc}",
                            "length_m": hypot(dr * 50, dc * 50),
                            "state": "permitted",
                        }
                    )
    grid = {
        "cells": cells,
        "edges": edges,
        "analysis_crs": "EPSG:25832",
        "cell_size_m": 50,
        "policy": "block_unresolved",
        "assumptions": {},
        "validation": {
            "boundary": mapping(
                transform(reverse, box(499970, 5799970, 500000 + n * 50, 5800000 + n * 50))
            ),
            "blocked": [],
            "unresolved": False,
        },
    }
    return connect_endpoints(grid, {"start": cells[0]["center"], "end": cells[-1]["center"]})


@pytest.mark.parametrize("algorithm", ["astar", "dijkstra"])
def test_hand_calculated_cardinal_diagonal_and_equal_cost_alternatives(algorithm):
    positions = {"s": (0, 0), "a": (50, 0), "b": (0, 50), "g": (50, 50)}
    edges = [("s", "a", 50), ("s", "b", 50), ("a", "g", 50), ("b", "g", 50)]
    result = search_graph(positions, edges, "s", "g", algorithm=algorithm)
    assert result["length_m"] == 100
    assert search_graph(positions, edges, "s", "g", algorithm=algorithm) == result
    assert search_graph(
        positions, edges + [("s", "g", 50 * sqrt(2))], "s", "g", algorithm=algorithm
    )["length_m"] == pytest.approx(50 * sqrt(2))


def test_forced_detour_disconnection_and_resource_limit():
    positions = {"s": (0, 0), "a": (0, 50), "b": (100, 50), "g": (100, 0)}
    edges = [("s", "a", 50), ("a", "b", 100), ("b", "g", 50)]
    for algorithm in ("astar", "dijkstra"):
        assert search_graph(positions, edges, "s", "g", algorithm=algorithm)["length_m"] == 200
        assert (
            search_graph(positions, edges[:-1], "s", "g", algorithm=algorithm)["status"]
            == "no_path_on_grid"
        )
    assert search_graph(positions, edges, "s", "g", max_expansions=1)["status"] == "resource_limit"


def test_route_exact_endpoints_length_and_zero():
    grid = metric_graph()
    result = plan_route(grid)
    assert result["status"] == "success"
    assert result["length_m"] == pytest.approx(100 * sqrt(2), abs=1e-6)
    assert result["geometry"]["coordinates"][0] == grid["connectors"][0]["coordinate"]
    assert result["geometry"]["coordinates"][-1] == grid["connectors"][1]["coordinate"]
    reverse = Transformer.from_crs(25832, 4326, always_xy=True)
    selected = {
        "start": list(reverse.transform(500005, 5800005)),
        "end": grid["connectors"][1]["coordinate"],
    }
    exact = plan_route(connect_endpoints(grid, selected))
    assert exact["geometry"]["coordinates"][0] == selected["start"]
    assert exact["length_m"] == pytest.approx(100 * sqrt(2) + sqrt(50), abs=1e-6)
    zero = plan_route(
        connect_endpoints(grid, {"start": selected["start"], "end": selected["start"]})
    )
    assert zero["status"] == "success" and zero["length_m"] == 0


def test_thin_crossing_boundary_contact_and_diagonal_corner():
    grid = metric_graph(2)
    # Both cardinal neighbors blocked: a diagonal must not slip through.
    for cell in grid["cells"]:
        if cell["id"] in ("0:1", "1:0"):
            cell["state"] = "blocked"
    assert plan_route(grid)["status"] == "no_path_on_grid"
    reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform
    grid = metric_graph(2)
    wall = mapping(transform(reverse, box(500024, 5799950, 500026, 5800100)))
    grid["validation"]["blocked"] = [wall]
    assert plan_route(grid)["status"] == "no_path_on_grid"
    check = constraint_checker(grid)
    boundary = list(reverse(500024, 5800025))
    assert check([boundary]) == "blocked"
    bad = connect_endpoints(grid, {"start": boundary, "end": grid["connectors"][1]["coordinate"]})
    assert plan_route(bad)["status"] == "invalid_endpoint"


def test_unresolved_and_invalid_endpoints_even_when_equal():
    grid = metric_graph()
    grid["validation"]["unresolved"] = True
    point = grid["connectors"][0]["coordinate"]
    assert (
        plan_route(connect_endpoints(grid, {"start": point, "end": point}))["status"]
        == "unresolved_input"
    )
    outside = connect_endpoints(grid, {"start": [0, 0], "end": point})
    assert plan_route(outside)["status"] == "invalid_endpoint"
    with pytest.raises(ValueError, match="Invalid start"):
        connect_endpoints(grid, {"start": [float("nan"), 0], "end": point})


@pytest.mark.parametrize("length", [-1, float("inf"), float("nan"), 1])
def test_bad_edge_weight_rejected(length):
    with pytest.raises(ValueError):
        search_graph({"s": (0, 0), "g": (50, 0)}, [("s", "g", length)], "s", "g")


def test_synthetic_api_export_repeatability_resolution_and_integrity(tmp_path):
    directory = tmp_path / "routing-demo"
    manifest = create_route_demo(directory)
    client = TestClient(create_app(tmp_path))
    url = "/api/datasets/routing-demo/experiment/route"
    result = client.get(url).json()
    assert result["status"] == "success", result
    again = client.get(url).json()
    assert result["geometry"] == again["geometry"] and result["length_m"] == again["length_m"]
    assert result["experiment"]["files"] == manifest["files"]
    grid = build_grid(directory, manifest)
    oracle = plan_route(grid, algorithm="dijkstra")
    assert oracle["status"] == result["status"]
    assert oracle["length_m"] == pytest.approx(result["length_m"], abs=1e-6)
    exported = client.get(url, params={"export": True})
    assert exported.headers["content-type"].startswith("application/geo+json")
    collection = exported.json()
    assert collection["features"][0]["geometry"] == result["geometry"]
    assert collection["metadata"]["experiment"]["sources"] == manifest["sources"]
    assert client.get(url, params={"cell_m": 25}).json()["status"] == "success"
    assert client.get(url, params={"cell_m": 0.1}).status_code == 422
    assert (
        client.get(url, params={"start_lon": 0, "start_lat": 0}).json()["status"]
        == "invalid_endpoint"
    )
    assert client.get(url, params={"start_lon": 10}).status_code == 422
    (directory / "zones.geojson").write_text("{}")
    assert client.get(url).status_code == 422


def test_real_fixture_cannot_be_promoted_and_exports_explicit_failure(tmp_path):
    directory = tmp_path / "real-policy"
    manifest = create_experiment_fixture(directory)
    client = TestClient(create_app(tmp_path))
    url = "/api/datasets/real-policy/experiment/route"
    assert client.get(url).json()["status"] == "unresolved_input"
    failed = client.get(url, params={"export": True}).json()
    assert failed["features"] == [] and failed["metadata"]["status"] == "unresolved_input"
    manifest["routing_fixture"] = "synthetic-obstacles-v1"
    write_json(directory / "experiment.json", manifest)
    assert client.get(url).status_code == 422


def test_synthetic_blockage_and_cli(tmp_path, capsys):
    directory = tmp_path / "demo"
    assert main(["route-demo", "--output", str(directory)]) == 0
    capsys.readouterr()
    output = tmp_path / "route.geojson"
    assert main(["experiment-route", str(directory), "--output", str(output)]) == 0
    result = read_json(output)
    assert result["metadata"]["status"] == "success"
    assert main(["experiment-route", str(directory), "--output", str(output)]) == 1
    manifest = read_json(directory / "experiment.json")
    zones = read_json(directory / "zones.geojson")
    zones["features"][0]["geometry"] = mapping(box(10.5199, 52.269, 10.5201, 52.272))
    write_json(directory / "zones.geojson", zones)
    manifest["files"][2]["sha256"] = checksum(directory / "zones.geojson")
    write_json(directory / "experiment.json", manifest)
    assert main(["experiment-route", str(directory)]) == 2
    assert plan_route(build_grid(directory, manifest))["status"] == "no_path_on_grid"


def test_missing_synthetic_terrain_remains_unresolved(tmp_path):
    directory = tmp_path / "demo"
    manifest = create_route_demo(directory)
    with rasterio.open(directory / "terrain.tif", "r+") as src:
        src.write(np.full((src.height, src.width), -9999, dtype="float32"), 1)
    manifest["files"][1]["sha256"] = checksum(directory / "terrain.tif")
    write_json(directory / "experiment.json", manifest)
    assert plan_route(build_grid(directory, manifest))["status"] == "unresolved_input"
