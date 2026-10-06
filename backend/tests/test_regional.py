"""Independent native-cell totals, complete-motion constraints and uncertainty gates."""

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString, Point, Polygon, box

from uas_planner.acquisition import terrain
from uas_planner.core import regional
from uas_planner.core.area import BoundingBox
from uas_planner.core.experiment import checksum, write_json
from uas_planner.storage.dataset import save_dataset


@pytest.fixture
def scenario():
    return {
        "agl_m": 100,
        "speed_m_s": 30,
        "scenario": "civil",
        "mission_start": "2026-10-07T10:00:00+02:00",
        "mission_end": "2026-10-07T10:15:00+02:00",
        "clearance_m": 0,
        "vertical_clearance_m": 0,
        "building_unknown_height": "unresolved",
    }


@pytest.fixture
def native_population(tmp_path):
    path = tmp_path / "pop.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        crs="ESRI:54009",
        transform=from_origin(0, 200, 100, 100),
        width=2,
        height=2,
        count=1,
        dtype="float32",
        nodata=-9999,
    ) as dst:
        dst.write(np.array([[0, 20], [40, -9999]], dtype="float32"), 1)
    manifest = {
        "config": {"ghsl_epoch": 2020},
        "sources": {
            "ghsl": {
                "path": "pop.tif",
                "product": "Synthetic native counts",
                "units": "people per native 100 m cell",
            }
        },
    }
    return regional.PopulationInspector(tmp_path, manifest)


def test_population_area_weighting_zero_missing_and_crossed_cells(native_population):
    result = native_population.query(
        box(0, 100, 150, 200), input_crs="ESRI:54009", include_cells=True
    )
    assert result["estimated_people"] == pytest.approx(10)
    assert result["known_zero_cells"] == 1
    assert result["crossed_cell_population_sum"] == 20
    assert len(result["layer"]["features"]) == 2
    assert result["routing_cost"] is False
    missing = native_population.query(box(0, 0, 200, 200), input_crs="ESRI:54009")
    assert missing["estimated_people"] is None
    assert missing["observed_estimated_people"] == 60
    assert missing["unknown_area_m2"] == 10000


def test_population_line_is_crossed_cells_not_area_population(native_population):
    result = native_population.query(LineString([(10, 150), (190, 150)]), input_crs="ESRI:54009")
    assert result["estimated_people"] is None
    assert result["crossed_cell_population_sum"] == 20
    for query in (Point(500, 500), box(400, 400, 500, 500)):
        outside = native_population.query(query, input_crs="ESRI:54009")
        assert outside["complete_support"] is False
        assert outside["crossed_cell_population_sum"] is None


def test_population_preview_is_native_and_preserves_missing(native_population, tmp_path):
    target = tmp_path / "population.svg"
    native_population.svg(target)
    content = target.read_text()
    assert 'fill="url(#missing)"' in content
    assert 'fill="#ffffff"' in content
    assert "native 100 m" in content
    with pytest.raises(FileExistsError):
        native_population.svg(target)


def test_population_grid_edge_queries_include_both_adjacent_cells(native_population):
    result = native_population.query(LineString([(10, 100), (190, 100)]), input_crs="ESRI:54009")
    assert result["known_cells"] == 3
    assert result["unknown_cells"] == 1
    assert result["observed_crossed_cell_population_sum"] == 60
    assert result["complete_support"] is False
    point = native_population.query(Point(100, 150), input_crs="ESRI:54009")
    assert point["known_cells"] == 2


def test_regional_population_api_queries_and_invalid_geometry(tmp_path, monkeypatch):
    from experiment_fixture import create_experiment_fixture
    from fastapi.testclient import TestClient

    from uas_planner.acquisition import study
    from uas_planner.api.app import create_app

    root = tmp_path / "datasets"
    root.mkdir()
    manifest = create_experiment_fixture(root / "case")
    manifest["sources"]["ghsl"]["units"] = "people per native 100 m cell"
    monkeypatch.setattr(study, "inspect_study", lambda _: manifest)
    with TestClient(create_app(root)) as client:
        response = client.get("/api/datasets/case/study/population", params={"cells": True})
        assert response.status_code == 200
        assert response.json()["unknown_cells"] > 0
        assert response.json()["layer"]["features"]
        assert (
            client.get(
                "/api/datasets/case/study/population", params={"geometry_json": "bad"}
            ).status_code
            == 422
        )
        assert (
            client.get("/api/datasets/case/study/population", params={"corridor_m": -1}).status_code
            == 422
        )
        assert client.get("/api/datasets/missing/study").status_code == 404


def make_terrain(root, *, bounds=(0, 0, 10, 10), missing=False):
    root.mkdir()
    data = np.full((10, 10), 80, dtype="float32")
    data[5, 5] = -9999 if missing else 130
    with rasterio.open(
        root / "tile.tif",
        "w",
        driver="GTiff",
        crs="EPSG:25832",
        transform=from_origin(bounds[0], bounds[3], 1, 1),
        width=10,
        height=10,
        count=1,
        dtype="float32",
        nodata=-9999,
    ) as dst:
        dst.write(data, 1)
    write_json(
        root / "terrain.json",
        {
            "schema_version": 1,
            "kind": "bounded-native-terrain",
            "vertical_datum": "DHHN2016_NHN",
            "tiles": [
                {"path": "tile.tif", "bounds": list(bounds), "sha256": checksum(root / "tile.tif")}
            ],
        },
    )
    return root


def test_terrain_bounds_include_peak_away_from_endpoints_and_unknown(tmp_path, monkeypatch):
    support = regional.TerrainSupport(make_terrain(tmp_path / "known"))
    result = support.bounds(LineString([(1, 1), (9, 9)]))
    assert result["status"] == "known"
    assert (result["minimum_m"], result["maximum_m"]) == (80, 130)
    assert support.bounds(LineString([(1, 1), (12, 12)]))["status"] == "unknown"
    missing = regional.TerrainSupport(make_terrain(tmp_path / "missing", missing=True))
    assert missing.bounds(LineString([(1, 1), (9, 9)]))["minimum_m"] is None
    assert support.bounds(Point(10, 10))["status"] == "known"
    monkeypatch.setattr(regional, "MAX_TERRAIN_PIXELS", 1)
    assert support.bounds(LineString([(1, 1), (9, 9)]))["status"] == "resource_limit"
    with (tmp_path / "known/tile.tif").open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        regional.TerrainSupport(tmp_path / "known")


def test_vertical_altitude_units_boundaries_and_datum():
    unknown = {"status": "unknown"}
    properties = {
        "upper_limit_altitude": 100,
        "upper_limit_unit": "m",
        "upper_limit_alt_ref": "AGL",
    }
    assert regional.vertical_state(properties, 100, unknown)[0] == "unresolved"
    assert regional.vertical_state(properties, 120, unknown)[0] == "outside_vertical"
    properties["upper_limit_unit"] = "ft"
    assert regional.vertical_state(properties, 100, unknown)[0] == "outside_vertical"
    properties.update(upper_limit_alt_ref="MSL", upper_limit_altitude=200, upper_limit_unit="m")
    terrain_bounds = {"status": "known", "minimum_m": 80, "maximum_m": 130, "vertical_datum": "MSL"}
    assert regional.vertical_state(properties, 100, terrain_bounds)[0] == "unresolved"
    terrain_bounds["minimum_m"] = 110
    assert regional.vertical_state(properties, 100, terrain_bounds)[0] == "outside_vertical"
    terrain_bounds["vertical_datum"] = "DHHN2016_NHN"
    assert regional.vertical_state(properties, 100, terrain_bounds)[0] == "unresolved"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("100 m", 100),
        ("100 ft", 30.48),
        ("12;15", None),
        (None, None),
        (True, None),
        (-1, None),
        ("nan", None),
    ],
)
def test_building_height_is_not_inferred_from_levels(value, expected):
    result = regional.building_height({"height": value, "building:levels": 100})
    assert result == pytest.approx(expected) if expected is not None else result is None


@pytest.fixture
def regional_case(tmp_path, monkeypatch):
    area = BoundingBox(10.519, 52.269, 10.522, 52.272)
    building = box(10.5204, 52.2702, 10.5206, 52.2708)
    frame = gpd.GeoDataFrame(
        {
            "element_type": ["way", "way"],
            "osm_id": [1, 2],
            "building": ["hospital", "yes"],
            "height": ["110", None],
        },
        geometry=[building, box(10.521, 52.271, 10.5212, 52.2712)],
        crs=4326,
    )
    save_dataset(frame, tmp_path / "osm", area, {"building": True}, synthetic=True)
    # Constraints use actual GeoPackage storage; source acquisition is tested separately.
    manifest = {
        "config": {
            "bounds": {
                "west": area.west,
                "south": area.south,
                "east": area.east,
                "north": area.north,
            },
            "ghsl_epoch": 2020,
            "locations": [],
        },
        "sources": {"dipul": {"responses": []}, "ghsl": {"path": "population.tif"}},
    }
    (tmp_path / "population.tif").write_bytes(b"not queried in constraint tests")
    monkeypatch.setattr(regional, "inspect_study", lambda _: manifest)
    return tmp_path, manifest, building


def test_complete_motion_and_endpoint_connectors_cross_building(regional_case, scenario):
    root, _, _ = regional_case
    model = regional.RegionalConstraints(root, scenario)
    endpoints = [[10.5200, 52.2705], [10.5209, 52.2705]]
    assert all(not model.check([point])["blocked"] for point in endpoints)
    assert model.check(endpoints)["state"] == "blocked"
    assert model.check(endpoints, mode="research")["state"] == "blocked"
    higher = regional.RegionalConstraints(root, {**scenario, "agl_m": 120})
    assert not higher.check(endpoints)["blocked"]
    # Missing terrain remains unresolved even with explicit research mode.
    assert higher.check(endpoints, mode="research")["state"] == "unresolved"
    missing_height = model.check([[10.5211, 52.2711]], mode="research")
    assert any(r["reason"] == "missing height" for r in missing_height["unresolved"])


def test_safety_buffer_and_height_exclusion_preserve_exact_endpoint(regional_case, scenario):
    root, _, _ = regional_case
    point = [10.5203, 52.2705]
    assert not regional.RegionalConstraints(root, scenario).check([point])["blocked"]
    buffered = regional.RegionalConstraints(root, {**scenario, "clearance_m": 10})
    assert buffered.check([point])["state"] == "blocked"
    conservative = regional.RegionalConstraints(
        root, {**scenario, "building_unknown_height": "exclude"}
    )
    assert conservative.check([[10.5211, 52.2711]])["state"] == "blocked"
    assert conservative.check([[10.53, 52.27]])["blocked"][0]["source"] == "boundary"


def test_soft_risk_remains_separate_from_obstacles_and_ghsl(regional_case, scenario):
    root, _, _ = regional_case
    model = regional.RegionalConstraints(root, scenario)
    points = [[10.5203, 52.2705], [10.5207, 52.2705]]
    risk = model.risk_model(background_cost=0).evaluate(points)
    assert risk["assessment"] == "assessed"
    assert risk["objective_cost"] == pytest.approx(
        0.9 * risk["risk_length_cost"] + 0.1 * risk["length_m"]
    )
    assert model.check(points)["state"] == "blocked"
    assert model.provenance["ghsl_routing_cost"] is False
    changed = regional.RegionalConstraints(
        root, {**scenario, "mission_start": "2026-10-07T09:59:00+02:00"}
    )
    assert changed.provenance["model_signature"] != model.provenance["model_signature"]


def test_invalid_geometry_stays_diagnostic_and_blocks_risk_support(regional_case, scenario):
    root, _, _ = regional_case
    invalid = Polygon(
        [(10.520, 52.270), (10.521, 52.271), (10.520, 52.271), (10.521, 52.270), (10.520, 52.270)]
    )
    # Write a new source directory; preserve the original test payload.
    frame = gpd.GeoDataFrame(
        {"element_type": ["way"], "osm_id": [3], "building": ["yes"]}, geometry=[invalid], crs=4326
    )
    other = root / "invalid"
    other.mkdir()
    save_dataset(
        frame,
        other / "osm",
        BoundingBox(10.519, 52.269, 10.522, 52.272),
        {"building": True},
        synthetic=True,
    )
    (other / "population.tif").write_bytes(b"unused")
    model = regional.RegionalConstraints(other, scenario)
    assert model.diagnostics[0]["status"] == "invalid_geometry"
    with pytest.raises(ValueError, match="unresolved"):
        model.risk_model(mode="research")


def test_zone_assessment_is_scoped_and_requires_evidence(scenario):
    record = {"source": "dipul:test/id", "source_signature": "abc"}
    assessment = {
        "state": "conditional_allowed",
        "evidence": "Synthetic operator consent fixture",
        "conditions_satisfied": ["synthetic scenario condition"],
        "scenario": "civil",
        "source_signature": "abc",
        "valid_from": "2026-10-07T09:00:00+02:00",
        "valid_until": "2026-10-07T11:00:00+02:00",
        "agl_interval_m": [100, 120],
    }
    scenario["zone_assessments"] = {record["source"]: assessment}
    assert regional.assessed_zone(record, scenario)[0] == "conditional_allowed"
    assessment["valid_until"] = "2026-10-07T10:05:00+02:00"
    assert regional.assessed_zone(record, scenario)[0] == "unresolved"
    assessment["state"] = "prohibited"
    assert regional.assessed_zone(record, scenario)[0] == "blocked"
    assessment["source_signature"] = "changed"
    with pytest.raises(ValueError, match="signature"):
        regional.assessed_zone(record, scenario)


def test_scenario_requires_explicit_time_and_valid_bounds(scenario):
    for key, value in (
        ("mission_start", "2026-10-07T10:00:00"),
        ("agl_m", 99),
        ("speed_m_s", 36),
        ("clearance_m", True),
    ):
        with pytest.raises(ValueError):
            regional.validate_scenario({**scenario, key: value})


def test_bounded_terrain_requests_and_verified_resume(tmp_path, monkeypatch):
    calls = []

    def fake_download(url, path, params):
        calls.append(path.name)
        if path.suffix == ".xml":
            path.write_text("<synthetic/>")
        else:
            subset = [value for key, value in params if key == "subset"]
            west, east = map(int, subset[0][2:-1].split(","))
            south, north = map(int, subset[1][2:-1].split(","))
            with rasterio.open(
                path,
                "w",
                driver="GTiff",
                crs="EPSG:25832",
                count=1,
                width=east - west,
                height=north - south,
                dtype="float32",
                transform=from_origin(west, north, 1, 1),
                nodata=-9999,
            ) as dst:
                dst.write(np.ones((north - south, east - west), dtype="float32"), 1)
        return {"url": url, "bytes": path.stat().st_size}

    monkeypatch.setattr(terrain, "download", fake_download)
    bounds = [10.519, 52.269, 10.520, 52.270]
    result = terrain.acquire_terrain(bounds, tmp_path / "terrain")
    assert len(result["tiles"]) == len(terrain.terrain_tiles(bounds))
    with pytest.raises(ValueError, match="Completed"):
        terrain.acquire_terrain(bounds, tmp_path / "terrain", resume=True)
    (tmp_path / "terrain/terrain.json").unlink()
    before = len(calls)
    terrain.acquire_terrain(bounds, tmp_path / "terrain", resume=True)
    assert len(calls) == before
    with pytest.raises(ValueError, match="tiles"):
        terrain.terrain_tiles([9.5, 52.2, 10.5, 52.8])
    (tmp_path / "terrain/terrain.json").unlink()
    with pytest.raises(ValueError, match="scope"):
        terrain.acquire_terrain([10.519, 52.269, 10.521, 52.270], tmp_path / "terrain", resume=True)


def test_terrain_interruption_preserves_bytes_and_explicit_resume(tmp_path, monkeypatch):
    root = tmp_path / "interrupted"

    def interrupted(url, path, params):
        path.write_bytes(b"partial source bytes")
        raise OSError("synthetic interrupted transfer")

    monkeypatch.setattr(terrain, "download", interrupted)
    bounds = [10.519, 52.269, 10.520, 52.270]
    with pytest.raises(OSError, match="interrupted"):
        terrain.acquire_terrain(bounds, root)
    assert not (root / "terrain.json").exists()

    def resumed(url, path, params):
        if path.suffix == ".xml":
            path.write_text("<synthetic/>")
        else:
            subset = [value for key, value in params if key == "subset"]
            west, east = map(int, subset[0][2:-1].split(","))
            south, north = map(int, subset[1][2:-1].split(","))
            with rasterio.open(
                path,
                "w",
                driver="GTiff",
                crs="EPSG:25832",
                count=1,
                width=east - west,
                height=north - south,
                dtype="float32",
                transform=from_origin(west, north, 1, 1),
            ) as dst:
                dst.write(np.ones((north - south, east - west), dtype="float32"), 1)
        return {"url": url, "bytes": path.stat().st_size}

    monkeypatch.setattr(terrain, "download", resumed)
    terrain.acquire_terrain(bounds, root, resume=True, workers=2)
    archived = list(root.glob("*.unreceipted-*"))
    assert len(archived) == 1
    assert archived[0].read_bytes() == b"partial source bytes"
    assert (root / "terrain.json").exists()
