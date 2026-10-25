"""Independent numerical, source-integrity and API checks for population classes."""

import json
from math import nextafter
from time import perf_counter

import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from pyproj import Transformer
from rasterio.transform import from_origin
from shapely.geometry import box
from shapely.ops import transform

from uas_planner.api.app import create_app
from uas_planner.core import population_costs as pc
from uas_planner.core.experiment import checksum, raster_metadata, write_json


def raster(path, values, *, x=0, y=500):
    values = np.array(values, dtype="float64")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        crs="ESRI:54009",
        transform=from_origin(x, y, 100, 100),
        width=values.shape[1],
        height=values.shape[0],
        count=1,
        dtype="float64",
        nodata=-9999,
    ) as src:
        src.write(values, 1)
    return path


def study(tmp_path, value=100):
    directory = tmp_path / "study"
    directory.mkdir()
    bounds = {"west": 9.8, "south": 52.38, "east": 9.81, "north": 52.39}
    convert = Transformer.from_crs(4326, "ESRI:54009", always_xy=True)
    w, s, e, n = convert.transform_bounds(*bounds.values())
    x, y = np.floor(w / 100) * 100 - 100, np.ceil(n / 100) * 100 + 100
    values = np.full((int(np.ceil((y - s) / 100)) + 1, int(np.ceil((e - x) / 100)) + 1), value)
    path = raster(directory / "population.tif", values, x=x, y=y)
    manifest = {
        "kind": "regional-source-study",
        "schema_version": 1,
        "config": {"bounds": bounds, "ghsl_epoch": 2020},
        "sources": {
            "ghsl": {
                "path": "population.tif",
                "product": "Synthetic counts",
                "raster": raster_metadata(path, "ghsl"),
            }
        },
        "files": [{"path": "population.tif", "sha256": checksum(path)}],
    }
    write_json(directory / "study.json", manifest)
    return directory, manifest


def test_uniform_100_to_625_and_actual_clipped_area(tmp_path):
    path = raster(tmp_path / "p.tif", np.full((5, 5), 100))
    with rasterio.open(path) as src:
        full = pc.aggregate_native(src, box(0, 0, 250, 250))
        clipped = pc.aggregate_native(src, box(25, 25, 150, 250))
    assert full["estimated_people"] == 625
    assert full["people_per_km2"] == 10000
    assert clipped["estimated_people"] == pytest.approx(125 * 225 / 100)
    assert clipped["people_per_km2"] == 10000


def test_nonuniform_fractional_intersections_conserve_counts(tmp_path):
    path = raster(tmp_path / "p.tif", [[0, 20], [40, 80]], y=200)
    with rasterio.open(path) as src:
        whole = pc.aggregate_native(src, box(25, 25, 175, 175))
        parts = [
            pc.aggregate_native(src, box(a, 25, b, 175))
            for a, b in ((25, 75), (75, 130), (130, 175))
        ]
    assert whole["estimated_people"] == pytest.approx(140 * 0.75**2)
    assert sum(p["estimated_people"] for p in parts) == pytest.approx(whole["estimated_people"])


def test_nodata_partial_and_outside_support_are_unknown(tmp_path):
    path = raster(tmp_path / "p.tif", [[0, 20], [40, -9999]], y=200)
    with rasterio.open(path) as src:
        missing = pc.aggregate_native(src, box(0, 0, 200, 200))
        outside = pc.aggregate_native(src, box(-100, 100, 100, 200))
        empty = pc.aggregate_native(src, box(500, 500, 750, 750))
    assert missing["observed_estimated_people"] == 60
    assert missing["estimated_people"] is missing["people_per_km2"] is None
    assert missing["nodata_area_m2"] == 10000
    assert outside["outside_area_m2"] == 10000
    assert empty["outside_area_m2"] == 62500
    assert all(p["status"] == "unknown" for p in (missing, outside, empty))


@pytest.mark.parametrize("maximum", [10000.0, 12345.67])
def test_exact_bin_boundaries_and_their_adjacent_floats(maximum):
    assert pc.classify_density(0, maximum) == 0
    assert pc.classify_density(maximum, maximum) == 4
    for score in range(1, 5):
        threshold = maximum * (score / 5)
        assert pc.classify_density(nextafter(threshold, 0), maximum) == score - 1
        assert pc.classify_density(threshold, maximum) == score
        assert pc.classify_density(nextafter(threshold, float("inf")), maximum) == score
    assert pc.classify_density(0, 0) == 0
    for invalid in (-1, float("nan"), float("inf"), maximum + 1):
        with pytest.raises(ValueError):
            pc.classify_density(invalid, maximum)


def test_full_study_reference_identity_subsets_and_defensive_copies(tmp_path):
    directory, manifest = study(tmp_path)
    surface = pc.prepare_population_surface(directory)
    whole = surface.display()
    cropped = surface.display([9.8, 52.38, 9.802, 52.382])
    assert len(cropped["layer"]["features"]) < len(whole["layer"]["features"])
    assert cropped["identity"] == whole["identity"]
    assert cropped["bins"] == whole["bins"]
    assert cropped["normalization_scope"] == "complete_saved_study"
    assert cropped["maximum_people_per_km2"] == pytest.approx(10000)
    assert whole["unknown_cells"] == 0
    assert whole["routing_cost"] is False
    assert all(f["properties"]["risk_score"] == 4 for f in whole["layer"]["features"])
    # Independent source-plane area, rather than nominal UTM cell size.
    from shapely import segmentize

    to_metric = Transformer.from_crs(4326, 25832, always_xy=True).transform
    to_native = Transformer.from_crs(25832, "ESRI:54009", always_xy=True).transform
    native_boundary = transform(
        to_native, segmentize(transform(to_metric, box(*manifest["config"]["bounds"].values())), 25)
    )
    assert whole["estimated_people"] == pytest.approx(native_boundary.area / 100, abs=0.001)
    assert pc.prepare_population_surface(directory) is surface
    cropped["bins"].clear()
    whole["layer"]["features"][0]["properties"]["risk_score"] = 99
    assert surface.display()["layer"]["features"][0]["properties"]["risk_score"] == 4
    assert len(surface.metadata["bins"]) == 5


@pytest.mark.parametrize("value, state, score", [(0, "ready", 0), (-9999, "unresolved", None)])
def test_zero_study_and_no_complete_cells(tmp_path, value, state, score):
    directory, _ = study(tmp_path, value)
    data = pc.prepare_population_surface(directory).display()
    assert data["state"] == state
    assert all(f["properties"]["risk_score"] == score for f in data["layer"]["features"])
    assert data["all_zero"] == (value == 0)
    assert data["estimated_people"] == (0 if value == 0 else None)


def test_invalid_source_values_and_window_budget(tmp_path, monkeypatch):
    path = raster(tmp_path / "p.tif", [[-2, float("nan")]], y=100)
    with rasterio.open(path) as src:
        for polygon in (box(0, 0, 100, 100), box(100, 0, 200, 100)):
            with pytest.raises(ValueError, match="Invalid population"):
                pc.aggregate_native(src, polygon)
        monkeypatch.setattr(pc, "MAX_WINDOW_PIXELS", 1)
        with pytest.raises(pc.PopulationResourceLimit, match="window"):
            pc.aggregate_native(src, box(0, 0, 200, 100))


def test_source_verification_before_cache_and_policy_identity(tmp_path):
    directory, manifest = study(tmp_path)
    first = pc.prepare_population_surface(directory)
    manifest["config"]["ghsl_epoch"] = 2025
    write_json(directory / "study.json", manifest)
    assert (
        pc.prepare_population_surface(directory).metadata["identity"] != first.metadata["identity"]
    )
    path = directory / "population.tif"
    with rasterio.open(path, "r+") as src:
        src.write(np.full((src.height, src.width), 50), 1)
    with pytest.raises(ValueError, match="checksum"):
        pc.prepare_population_surface(directory)


def test_preparation_limits_cancel_and_display_limits(tmp_path, monkeypatch):
    directory, _ = study(tmp_path)
    surface = pc.prepare_population_surface(directory)
    with pytest.raises(pc.PopulationResourceLimit, match="deadline"):
        pc.PopulationSurface(
            box(0, 0, 250, 250), directory / "population.tif", {}, 2020, deadline=perf_counter() - 1
        )
    with pytest.raises(pc.PopulationResourceLimit, match="cancelled"):
        pc.PopulationSurface(
            box(0, 0, 250, 250), directory / "population.tif", {}, 2020, cancel=lambda: True
        )
    monkeypatch.setattr(pc, "MAX_TARGET_CELLS", 1)
    with pytest.raises(pc.PopulationResourceLimit, match="target grid"):
        pc.PopulationSurface(box(0, 0, 500, 500), directory / "population.tif", {}, 2020)
    monkeypatch.setattr(pc, "MAX_DISPLAY_CELLS", 1)
    result = surface.display()
    assert result["display"]["complete"] is False
    assert len(result["layer"]["features"]) == 1
    assert len(json.dumps(result).encode()) < pc.MAX_DISPLAY_BYTES


def test_api_bounds_source_verification_and_unchanged_inspection_contract(tmp_path):
    directory, _ = study(tmp_path)
    with TestClient(create_app(tmp_path)) as client:
        url = f"/api/datasets/{directory.name}/study/population-costs"
        response = client.get(url)
        assert response.status_code == 200
        assert response.json()["version"] == pc.VERSION
        for invalid in ("nan,0,1,1", "0,0,1", "0,0,0,1", "0,-90,1,1", "0,0,1,1,1"):
            assert client.get(url, params={"bbox": invalid}).status_code == 422
        small = client.get(url, params={"bbox": "9.8,52.38,9.802,52.382"}).json()
        assert small["identity"] == response.json()["identity"]
        assert client.get("/api/datasets/absent/study/population-costs").status_code == 404
        (directory / "population.tif").write_bytes(b"corrupted")
        assert client.get(url).status_code == 422
