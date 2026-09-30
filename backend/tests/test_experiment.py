import copy

import pytest
import rasterio
from experiment_fixture import create_experiment_fixture
from fastapi.testclient import TestClient

from uas_planner.api.app import create_app
from uas_planner.cli import main
from uas_planner.core.experiment import (
    inspect_location,
    load_experiment,
    population_layer,
    raster_metadata,
    read_json,
    safe_file,
    validate_config,
    validate_zones,
    write_json,
    zone_layer,
)


@pytest.fixture
def experiment(tmp_path):
    path = tmp_path / "experiment"
    return path, create_experiment_fixture(path)


def test_repeatable_reload_native_values_and_heights(experiment):
    path, original = experiment
    first = load_experiment(path)
    assert first == original == load_experiment(path)
    start = inspect_location(path, first, *first["config"]["start"])
    assert start["terrain_m"] == 0
    assert start["aircraft_altitude_m"] == 60
    assert start["people_per_cell"] == 0
    assert start["height_status"] == start["population_status"] == "known"
    assert start["zones"][0]["id"] == "test-zone.42"
    end = inspect_location(path, first, *first["config"]["end"])
    assert end["terrain_m"] is end["aircraft_altitude_m"] is end["people_per_cell"] is None
    assert end["height_status"] == end["population_status"] == "unknown"
    layer = population_layer(path, first)
    assert layer == population_layer(path, load_experiment(path))
    values = [f["properties"] for f in layer["features"]]
    assert any(p["people_per_cell"] == 20 and p["people_per_km2"] == 2000 for p in values)
    assert any(p["people_per_cell"] == 0 and p["status"] == "known" for p in values)
    assert any(p["people_per_cell"] is None and p["status"] == "unknown" for p in values)
    assert all("osm_id" not in f["properties"] for f in layer["features"])
    assert zone_layer(path, first)["features"][0]["properties"]["upper_limit_unit"] == "ft"


@pytest.mark.parametrize(
    "key,value",
    [
        ("agl_m", -1),
        ("agl_m", float("nan")),
        ("agl_m", True),
        ("scenario", "unknown"),
        ("ghsl_epoch", 2023),
        ("start", [10, 51]),
        ("mission_start", "2026-10-01T10:00:00"),
        ("mission_end", "2026-10-01T10:00:00+02:00"),
        ("mission_start", "2026-10-01T10:00:00+01:00"),
        ("bounds", {"west": 10, "south": 52, "east": 11, "north": 53}),
    ],
)
def test_invalid_mission(experiment, key, value):
    _, manifest = experiment
    config = copy.deepcopy(manifest["config"])
    config[key] = value
    with pytest.raises(ValueError):
        validate_config(config)


def test_corruption_and_path_escape(experiment):
    path, manifest = experiment
    (path / "zones.geojson").write_text("{}")
    with pytest.raises(ValueError, match="Checksum"):
        load_experiment(path)
    with pytest.raises(ValueError, match="outside"):
        safe_file(path, "../missing")
    manifest["files"][0]["path"] = "../outside.tif"
    write_json(path / "experiment.json", manifest)
    with pytest.raises(ValueError):
        load_experiment(path)


def test_missing_payload_and_unregistered_raster(experiment):
    path, manifest = experiment
    manifest["files"] = manifest["files"][1:]
    write_json(path / "experiment.json", manifest)
    with pytest.raises(ValueError, match="integrity manifest"):
        load_experiment(path)


def test_invalid_raster_resolution_and_crs(experiment):
    path, _ = experiment
    with rasterio.open(path / "ghsl.tif", "r+") as src:
        src.crs = "EPSG:25832"
    with pytest.raises(ValueError, match="CRS"):
        raster_metadata(path / "ghsl.tif", "ghsl")
    with rasterio.open(path / "terrain.tif", "r+") as src:
        src.transform = src.transform @ src.transform.scale(2, 2)
    with pytest.raises(ValueError, match="native grid"):
        raster_metadata(path / "terrain.tif", "terrain")


def test_dipul_empty_null_crs_truncation_duplicate_and_axis_order(experiment):
    path, manifest = experiment
    area = validate_config(manifest["config"])
    assert (
        validate_zones(
            {"type": "FeatureCollection", "features": [], "numberMatched": 0, "crs": None}, area
        )
        == []
    )
    source = read_json(path / "zones.geojson")
    source["numberMatched"] = 2
    with pytest.raises(ValueError, match="completeness"):
        validate_zones(source, area)
    source["numberReturned"] = 2
    source["features"].append(copy.deepcopy(source["features"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        validate_zones(source, area)
    source = read_json(path / "zones.geojson")
    rings = source["features"][0]["geometry"]["coordinates"]
    source["features"][0]["geometry"]["coordinates"] = [
        [[lat, lon] for lon, lat in ring] for ring in rings
    ]
    with pytest.raises(ValueError, match="axis order"):
        validate_zones(source, area)


def test_api_layers_height_legacy_and_bounds(experiment):
    path, manifest = experiment
    client = TestClient(create_app(path.parent))
    base = "/api/datasets/experiment"
    assert client.get(base).json()["has_experiment"]
    assert client.get(base + "/features").json()["features"]
    assert client.get(base + "/download/gpkg").content == (path / "osm/features.gpkg").read_bytes()
    assert client.get(base + "/experiment").json() == manifest
    assert client.get(base + "/experiment/layers/population").json()["features"]
    assert (
        client.get(base + "/experiment/layers/zones").json()["features"][0]["id"] == "test-zone.42"
    )
    assert (
        client.get(
            base + "/experiment/inspect", params={"longitude": 10.5195, "latitude": 52.2695}
        ).json()["aircraft_altitude_m"]
        == 60
    )
    for lon, lat in [(0, 0), ("nan", 52.27), ("inf", 52.27)]:
        assert (
            client.get(
                base + "/experiment/inspect", params={"longitude": lon, "latitude": lat}
            ).status_code
            == 422
        )
    manifest["config"]["bounds"]["east"] -= 0.0001
    write_json(path / "experiment.json", manifest)
    assert client.get(base + "/experiment").status_code == 422


def test_cli_offline_inspection_and_resume_refuses_complete(experiment, capsys):
    path, manifest = experiment
    assert (
        main(["experiment-inspect", str(path), "--longitude", "10.5195", "--latitude", "52.2695"])
        == 0
    )
    assert '"aircraft_altitude_m": 60.0' in capsys.readouterr().out
    assert main(["experiment-inspect", str(path), "--longitude", "10.5195"]) == 1
    from uas_planner.acquisition.external import acquire_experiment

    with pytest.raises(ValueError, match="Completed"):
        acquire_experiment(manifest["config"], path, resume=True)
