"""Independent numerical and API regressions for the preparation graph."""

import numpy as np
import pytest
import rasterio
from experiment_fixture import create_experiment_fixture
from fastapi.testclient import TestClient
from pyproj import Transformer
from shapely.geometry import LineString, Point, box, mapping
from shapely.ops import transform

from uas_planner.api.app import create_app, prepared_grid
from uas_planner.core.experiment import checksum, read_json, write_json
from uas_planner.core.grid import _population, build_grid


def test_population_transfer_preserves_counts_and_outside_support(tmp_path):
    directory = tmp_path / "experiment"
    manifest = create_experiment_fixture(directory)
    source = manifest["sources"]["ghsl"]
    with rasterio.open(directory / source["path"]) as src:
        x, y = src.transform @ (0, 0)
        to_metric = Transformer.from_crs(src.crs, 25832, always_xy=True).transform
        pixel = box(x, y - 100, x + 100, y)
        full = _population(src, source, transform(to_metric, pixel))
        halves = [
            _population(src, source, transform(to_metric, polygon))
            for polygon in (box(x, y - 100, x + 50, y), box(x + 50, y - 100, x + 100, y))
        ]
        assert full["estimated_people"] == pytest.approx(20, abs=1e-5)
        assert sum(item["estimated_people"] for item in halves) == pytest.approx(20, abs=1e-5)
        assert full["people_per_km2"] == pytest.approx(2000)
        outside = _population(src, source, transform(to_metric, box(x - 100, y - 100, x - 50, y)))
        assert outside["estimated_people"] is None
        assert outside["unknown_area_m2"] == pytest.approx(5000, abs=1e-5)


def test_grid_edges_lengths_limits_and_exact_connectors(tmp_path):
    directory = tmp_path / "experiment"
    manifest = create_experiment_fixture(directory)
    grid = build_grid(directory, manifest)
    forward = Transformer.from_crs(4326, 25832, always_xy=True)
    cells = {cell["id"]: cell for cell in grid["cells"]}
    for edge in grid["edges"]:
        a = np.array(forward.transform(*cells[edge["from"]]["center"]))
        b = np.array(forward.transform(*cells[edge["to"]]["center"]))
        assert edge["length_m"] == pytest.approx(np.linalg.norm(a - b))
    for connector in grid["connectors"]:
        assert connector["coordinate"] == manifest["config"][connector["endpoint"]]
    with pytest.raises(ValueError, match="exceeds"):
        build_grid(directory, manifest, 0.1)
    with pytest.raises(ValueError, match="Invalid start"):
        build_grid(
            directory, manifest, endpoints={"start": [0, 0], "end": manifest["config"]["end"]}
        )


def test_api_grid_cache_revalidates_sources_and_mission(tmp_path):
    directory = tmp_path / "experiment"
    manifest = create_experiment_fixture(directory)
    client = TestClient(create_app(tmp_path))
    url = "/api/datasets/experiment/experiment/grid"
    prepared_grid.cache_clear()
    first = client.get(url).json()
    assert client.get(url).json() == first
    assert prepared_grid.cache_info().hits == 1
    assert client.get(url, params={"cell_m": 100}).json()["cell_count"] < first["cell_count"]
    for size in ["0", "-1", "nan", "inf", "0.1"]:
        assert client.get(url, params={"cell_m": size}).status_code == 422
    manifest["config"]["agl_m"] = 70
    write_json(directory / "experiment.json", manifest)
    assert client.get(url).json()["assumptions"]["agl_m"] == 70
    with rasterio.open(directory / "ghsl.tif", "r+") as src:
        src.write(np.full((src.height, src.width), 40, dtype="float32"), 1)
    # A cached result must never bypass integrity verification.
    assert client.get(url).status_code == 422
    manifest["files"][0]["sha256"] = checksum(directory / "ghsl.tif")
    write_json(directory / "experiment.json", manifest)
    updated = client.get(url).json()
    assert all(cell["population"]["estimated_people"] is not None for cell in updated["cells"])
    assert updated["cells"] != first["cells"]


def test_zone_crossed_between_centers_is_reported(tmp_path):
    directory = tmp_path / "experiment"
    manifest = create_experiment_fixture(directory)
    original = build_grid(directory, manifest)
    cells = {cell["id"]: cell for cell in original["cells"]}
    edge = original["edges"][0]
    forward = Transformer.from_crs(4326, 25832, always_xy=True).transform
    reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform
    a = Point(*forward(*cells[edge["from"]]["center"]))
    b = Point(*forward(*cells[edge["to"]]["center"]))
    middle = LineString([a, b]).interpolate(0.5, normalized=True)
    narrow_zone = middle.buffer(0.5)
    assert not narrow_zone.intersects(a) and not narrow_zone.intersects(b)
    zones = read_json(directory / "zones.geojson")
    zones["features"][0]["geometry"] = mapping(transform(reverse, narrow_zone))
    zones["features"][0]["properties"] = {
        "lower_limit_altitude": 0,
        "lower_limit_unit": "m",
        "lower_limit_alt_ref": "AGL",
    }
    write_json(directory / "zones.geojson", zones)
    updated = build_grid(directory, manifest)
    crossed = next(
        item
        for item in updated["edges"]
        if item["from"] == edge["from"] and item["to"] == edge["to"]
    )
    assert any("test-zone.42" in reason["source"] for reason in crossed["reasons"])
    assert crossed["state"] == "unresolved"
