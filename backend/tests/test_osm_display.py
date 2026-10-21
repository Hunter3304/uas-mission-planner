"""Spatial correctness, resource ceilings and display/source lifecycle regressions."""

import json
import os

import geopandas as gpd
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box, shape

from uas_planner.api.app import create_app
from uas_planner.cli import main
from uas_planner.core import osm_display as display
from uas_planner.core.area import StudyRegion
from uas_planner.storage.dataset import checksum, save_dataset


@pytest.fixture
def regional(tmp_path):
    directory = tmp_path / "regional"
    directory.mkdir()
    geometries = [
        Point(10.01, 52.01),
        LineString([(9.99, 52.05), (10.11, 52.05)]),
        box(10.04, 52.04, 10.06, 52.06),
        MultiPolygon([box(10.07, 52.07, 10.075, 52.075), box(10.08, 52.08, 10.085, 52.085)]),
        Polygon([(10.02, 52.02), (10.03, 52.03), (10.03, 52.02), (10.02, 52.03), (10.02, 52.02)]),
        Point(10.10, 52.10),
    ]
    tags = [
        {"natural": "tree", "name": "<script>original</script>", "rare:tag": "retained"},
        {"highway": "service"},
        {"building": "hospital", "landuse": "commercial"},
        {"building": "yes"},
        {"building": "house"},
        {"natural": "tree"},
    ]
    frame = gpd.GeoDataFrame(
        {
            "element_type": ["node", "way", "way", "relation", "way", "node"],
            "osm_id": [1, 2, 3, 4, 5, 6],
        },
        geometry=geometries,
        crs=4326,
    )
    area = StudyRegion(10.0, 52.0, 10.1, 52.1)
    save_dataset(frame, directory / "osm", area, {}, tag_objects=tags)
    (directory / "study.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "regional-source-study",
                "config": {"bounds": {"west": 10.0, "south": 52.0, "east": 10.1, "north": 52.1}},
            }
        )
    )
    return directory, frame, display.DisplayStore(tmp_path / ".osm-display")


def test_preparation_summary_and_originals(regional):
    directory, frame, store = regional
    before = {p.name: checksum(p) for p in (directory / "osm").iterdir()}
    assert store.status(directory)["state"] == "not_prepared"
    progress = []
    result = store.prepare(directory, progress=progress.append)
    assert result["verified"]
    assert result["feature_count"] == len(frame)
    assert result["drawable_count"] == len(frame) - 1
    assert result["layer_counts"] == {"building": 3, "highway": 1, "landuse": 1, "natural": 2}
    assert result["diagnostics"]["counts"] == {"invalid_source_geometry": 1}
    assert result["diagnostics"]["samples"][0]["osm_id"] == 5
    assert result["source_index_entries"] == len(frame)
    assert store.prepare(directory)["database_sha256"] == result["database_sha256"]
    assert {p.name: checksum(p) for p in (directory / "osm").iterdir()} == before


@pytest.mark.parametrize(
    "bbox",
    [
        (10.045, 52.045, 10.055, 52.055),
        (10.075, 52.075, 10.08, 52.08),
        (10.0, 52.009, 10.01, 52.011),
        (10.099, 52.099, 10.101, 52.101),
        (10.09, 52.02, 10.095, 52.025),
    ],
)
def test_spatial_queries_agree_with_independent_intersections(regional, bbox):
    directory, frame, store = regional
    store.prepare(directory)
    effective = box(*bbox).intersection(box(10, 52, 10.1, 52.1))
    expected = set(
        frame.loc[frame.geometry.is_valid & frame.geometry.intersects(effective), "osm_id"]
    )
    result = store.features(directory, bbox)
    assert {f["properties"]["osm_id"] for f in result["features"]} == expected
    assert result["display"]["complete"]
    assert all(shape(f["geometry"]).intersects(effective) for f in result["features"])
    assert all(
        set(f["properties"]) == {"element_type", "osm_id", "categories"} for f in result["features"]
    )


def test_categories_unique_ids_and_clamped_coverage(regional):
    directory, _, store = regional
    store.prepare(directory)
    result = store.features(directory, (9.9, 51.9, 10.2, 52.2), categories="building,landuse")
    assert {f["id"] for f in result["features"]} == {"way/3", "relation/4"}
    assert result["display"]["effective_bounds"] == (10, 52, 10.1, 52.1)
    outside = store.features(directory, (11, 53, 12, 54))
    assert outside["features"] == []
    assert outside["display"]["outside_coverage"]


def test_overview_counts_each_drawable_object_once(regional):
    directory, _, store = regional
    summary = store.prepare(directory)
    result = store.overview(directory, (10, 52, 10.1, 52.1))
    assert result["display"]["representation"] == "aggregate_overview"
    assert sum(f["properties"]["objects"] for f in result["features"]) == summary["drawable_count"]
    totals = {
        n: sum(f["properties"]["category_counts"][n] for f in result["features"])
        for n in display.CATEGORIES
    }
    assert totals == {"building": 2, "highway": 1, "landuse": 1, "natural": 2}
    assert len(result["features"]) <= 1600
    assert len(display.encode(result).encode()) < display.MAX_BYTES


@pytest.mark.parametrize(
    "limit,value,reason",
    [
        ("MAX_FEATURES", 1, "feature_limit"),
        ("MAX_COORDINATES", 1, "geometry_budget"),
        ("MAX_CANDIDATES", 1, "candidate_or_time_limit"),
        ("MAX_BYTES", 8300, "response_byte_limit"),
    ],
)
def test_query_budgets_are_explicit_not_false_complete(regional, monkeypatch, limit, value, reason):
    directory, _, store = regional
    store.prepare(directory)
    monkeypatch.setattr(display, limit, value)
    result = store.features(directory, (10, 52, 10.1, 52.1))
    assert result["display"]["complete"] is False
    assert result["display"]["overview_recommended"]
    assert result["display"]["limit_reason"] == reason
    assert len(display.encode(result).encode()) <= display.MAX_BYTES


def test_warm_catalog_and_queries_never_full_load_or_rehash(regional, monkeypatch):
    directory, _, store = regional
    store.prepare(directory)

    def forbidden(*args, **kwargs):
        raise AssertionError("Warm display must not read/hash the complete source")

    monkeypatch.setattr(display, "checksum", forbidden)
    monkeypatch.setattr(gpd, "read_file", forbidden)
    for _ in range(3):
        assert store.catalog(directory)["verified"]
        assert store.features(directory, (10, 52, 10.1, 52.1))["display"]["complete"]
        assert store.overview(directory, (10, 52, 10.1, 52.1))["display"]["complete"]


def test_source_corruption_and_metadata_changes_cannot_return_stale_verified_data(regional):
    directory, _, store = regional
    store.prepare(directory)
    with (directory / "osm/features.gpkg").open("ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        store.features(directory, (10, 52, 10.1, 52.1))
    metadata_path = directory / "osm/metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["saved_at_utc"] = "changed"
    metadata_path.write_text(json.dumps(metadata))
    assert store.status(directory)["state"] == "not_prepared"


def test_restart_verifies_cache_and_corruption_requires_explicit_refresh(regional):
    directory, _, store = regional
    summary = store.prepare(directory)
    folder = store.cache_root / display.context(directory)["key"]
    db = folder / summary["database"]
    with db.open("ab") as stream:
        stream.write(b"changed")
    restarted = display.DisplayStore(store.cache_root)
    with pytest.raises(ValueError, match="cache checksum"):
        restarted.summary(directory)
    assert restarted.prepare(directory, refresh=True)["verified"]


def test_partial_build_and_prepare_lock_are_not_ready(regional):
    directory, _, store = regional
    folder = store.cache_root / display.context(directory)["key"]
    folder.mkdir(parents=True)
    (folder / "display-incomplete.sqlite").write_bytes(b"partial")
    assert store.status(directory)["state"] == "not_prepared"
    (folder / "prepare.lock").touch()
    assert store.status(directory)["state"] == "preparing"
    with pytest.raises(display.DisplayUnavailable, match="locked"):
        store.prepare(directory)


def test_rule_change_invalidates_display(regional, monkeypatch):
    directory, _, store = regional
    store.prepare(directory)
    monkeypatch.setattr(display, "RULES", {**display.RULES, "version": "new-rules"})
    assert store.status(directory)["state"] == "not_prepared"


def test_source_changed_during_query_is_rejected(regional, monkeypatch):
    directory, _, store = regional
    store.prepare(directory)
    original = display.from_wkb

    def change_source(blob):
        with (directory / "osm/features.gpkg").open("ab") as stream:
            stream.write(b"changed")
        return original(blob)

    monkeypatch.setattr(display, "from_wkb", change_source)
    with pytest.raises(display.DisplayUnavailable, match="Source changed"):
        store.features(directory, (10, 52, 10.1, 52.1))


def test_api_validation_readiness_sparse_legacy_and_catalog(regional, monkeypatch):
    directory, _, _ = regional
    client = TestClient(create_app(directory.parent))
    base = "/api/datasets/regional"
    assert client.get(base + "/study/osm/summary").json()["state"] == "not_prepared"
    assert client.get(base).json()["verified"] is False
    for bbox in ("nan,52,11,53", "10,52,9,53", "10,52,11", "10,52,181,53"):
        assert client.get(base + "/study/osm/features", params={"bbox": bbox}).status_code == 422
    params = {"bbox": "10,52,10.1,52.1"}
    for extra in (
        {"categories": "building,building"},
        {"categories": "bad"},
        {"zoom": 23},
        {"style": "cost"},
    ):
        assert (
            client.get(base + "/study/osm/features", params={**params, **extra}).status_code == 422
        )
    assert client.get(base + "/study/osm/features", params=params).status_code == 409
    app_store = client.app.state.osm_display
    app_store.prepare(directory)
    assert client.get(base).json()["verified"]
    assert client.get("/api/datasets").json()["datasets"][0]["feature_count"] == 6
    response = client.get(base + "/study/osm/features", params=params)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/geo+json")
    assert len(response.content) <= display.MAX_BYTES
    assert (
        client.get(base + "/study/osm/overview", params=params).json()["display"]["representation"]
        == "aggregate_overview"
    )
    legacy = client.get(base + "/features").json()
    point = next(f for f in legacy["features"] if f["properties"]["osm_id"] == 1)
    assert point["properties"]["rare:tag"] == "retained"
    assert "building" not in point["properties"]
    # Guard before calling any full loader, including with requested cost analysis.
    import uas_planner.api.app as app_module

    monkeypatch.setattr(app_module, "MAX_FEATURES", 2)
    monkeypatch.setattr(app_module, "load_dataset", lambda *a, **k: pytest.fail("unbounded read"))
    assert client.get(base + "/features?analysis=tag-costs").status_code == 413
    assert client.get(base + "/features").status_code == 413
    assert client.get(base).status_code == 200


def test_bounded_query_capacity(regional):
    directory, _, store = regional
    store.prepare(directory)
    assert store._queries.acquire(False)
    assert store._queries.acquire(False)
    try:
        with pytest.raises(display.DisplayUnavailable, match="capacity"):
            store.features(directory, (10, 52, 10.1, 52.1))
    finally:
        store._queries.release()
        store._queries.release()


def test_cli_preparation_and_reuse(regional, capsys):
    directory, _, store = regional
    args = ["study-osm-prepare", str(directory), "--cache-root", str(store.cache_root)]
    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["state"] == "ready"
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["database_sha256"] == result["database_sha256"]


def test_bounds_and_geometry_header_validation():
    for blob in (b"", b"GP\x01" + b"\0" * 5, b"GP\x00\xff" + b"\0" * 4):
        with pytest.raises(ValueError):
            display.gpkg_wkb(blob)


def test_corrupt_cache_api_does_not_leak_paths(regional):
    directory, _, _ = regional
    client = TestClient(create_app(directory.parent))
    store = client.app.state.osm_display
    summary = store.prepare(directory)
    folder = store.cache_root / display.context(directory)["key"]
    (folder / summary["database"]).write_bytes(b"corruption")
    response = client.get("/api/datasets/regional/study/osm/summary")
    assert response.status_code == 422
    assert str(directory) not in response.text


def test_same_size_source_edit_with_restored_mtime_invalidates_checksum(regional):
    directory, _, store = regional
    store.prepare(directory)
    source = directory / "osm/features.gpkg"
    stat = source.stat()
    with source.open("r+b") as stream:
        stream.seek(-1, os.SEEK_END)
        byte = stream.read(1)
        stream.seek(-1, os.SEEK_END)
        stream.write(bytes([byte[0] ^ 1]))
    os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with pytest.raises(ValueError, match="source checksum"):
        store.summary(directory)


def test_empty_source_produces_ready_empty_display(regional):
    directory, frame, store = regional
    empty = directory.parent / "empty"
    empty.mkdir()
    save_dataset(frame.iloc[:0], empty / "osm", StudyRegion(10, 52, 10.1, 52.1), {})
    (empty / "study.json").write_bytes((directory / "study.json").read_bytes())
    summary = store.prepare(empty)
    assert summary["feature_count"] == summary["drawable_count"] == 0
    assert store.features(empty, (10, 52, 10.1, 52.1))["features"] == []
    overview = store.overview(empty, (10, 52, 10.1, 52.1))
    assert overview["features"] == []
    assert overview["display"]["complete"]
    assert not overview["display"]["outside_coverage"]
