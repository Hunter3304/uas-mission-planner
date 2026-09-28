import json

import geopandas as gpd
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString, Point

from uas_planner.api.app import create_app
from uas_planner.core.area import BoundingBox
from uas_planner.storage.dataset import save_dataset


@pytest.fixture
def dataset(tmp_path):
    frame = gpd.GeoDataFrame(
        {
            "element_type": ["node", "way"],
            "osm_id": [1, 2],
            "natural": ["tree", None],
            "highway": [None, "footway"],
            "landuse": [None, "recreation_ground"],
            "name": ["<script>unsafe</script>", None],
        },
        geometry=[Point(10.52, 52.27), LineString([(10.52, 52.27), (10.521, 52.271)])],
        crs=4326,
    )
    save_dataset(frame, tmp_path / "demo", BoundingBox(10.519, 52.269, 10.522, 52.272), {})
    return tmp_path, frame


def test_list_details_features_and_downloads(dataset):
    root, _ = dataset
    client = TestClient(create_app(root))
    listing = client.get("/api/datasets").json()["datasets"]
    assert len(listing) == 1
    details = client.get("/api/datasets/demo").json()
    assert details["feature_count"] == 2
    assert details["layer_counts"] == {"building": 0, "highway": 1, "landuse": 1, "natural": 1}
    assert details["verified"]
    features = client.get("/api/datasets/demo/features").json()
    assert len(features["features"]) == 2
    assert features["features"][0]["properties"]["osm_id"] == 1
    assert client.get("/api/datasets/demo/download/geojson").json() == features
    gpkg = client.get("/api/datasets/demo/download/gpkg")
    assert gpkg.content == (root / "demo/features.gpkg").read_bytes()
    assert "attachment" in gpkg.headers["content-disposition"]
    assert client.get("/api/datasets/demo/download/metadata").json()["feature_count"] == 2
    assert client.get("/api/datasets/demo/download/exe").status_code == 422


def test_all_tag_costs_analyze_standalone_features(dataset):
    root, _ = dataset
    client = TestClient(create_app(root))
    response = client.get("/api/datasets/demo/features?analysis=tag-costs")
    assert response.status_code == 200
    data = response.json()
    assert data["layer_summaries"]["building"]["features"] == 0
    assert data["layer_summaries"]["highway"]["features"] == 1
    assert data["layer_summaries"]["landuse"]["features"] == 1
    assert data["layer_summaries"]["natural"]["features"] == 1
    assert data["features"][1]["layer_analyses"]["highway"]["cost"] == 3
    assert data["features"][1]["layer_analyses"]["landuse"]["cost"] == 4
    raw = client.get("/api/datasets/demo/features").json()
    assert raw == client.get("/api/datasets/demo/download/geojson").json()
    assert "layer_analyses" not in raw["features"][0]


def test_missing_and_invalid_dataset_ids(dataset):
    root, _ = dataset
    client = TestClient(create_app(root))
    for path in ("missing", "%2E%2E", "..%5Cdemo", "demo%2F..%2F..", "demo%5C.."):
        assert client.get(f"/api/datasets/{path}").status_code == 404


def test_corrupt_dataset_has_explicit_error(dataset):
    root, _ = dataset
    (root / "demo/features.gpkg").write_bytes(b"corrupt")
    client = TestClient(create_app(root))
    assert client.get("/api/datasets/demo").status_code == 422
    assert client.get("/api/datasets/demo/download/gpkg").status_code == 422
    assert client.get("/api/datasets").json()["datasets"][0]["verified"] is False


def test_empty_dataset_and_missing_root(dataset):
    root, frame = dataset
    save_dataset(frame.iloc[:0], root / "empty", BoundingBox(10.519, 52.269, 10.522, 52.272), {})
    client = TestClient(create_app(root))
    assert client.get("/api/datasets/empty/features").json()["features"] == []
    assert client.get("/api/datasets/empty").json()["feature_bounds"] is None
    assert TestClient(create_app(root / "absent")).get("/api/datasets").json() == {"datasets": []}


def test_building_analysis_is_opt_in_and_preserves_downloads(tmp_path):
    from uas_planner.sample import create_sample

    create_sample(tmp_path / "sample")
    client = TestClient(create_app(tmp_path))
    before = (tmp_path / "sample/features.gpkg").read_bytes()
    source = client.get("/api/datasets/sample/features").json()
    response = client.get("/api/datasets/sample/features?analysis=building-costs")
    assert response.status_code == 200
    result = response.json()
    assert result["cost_summary"]["buildings"] == 1
    for raw, derived in zip(source["features"], result["features"], strict=True):
        assert raw["properties"] == derived["properties"]
        assert raw["geometry"] == derived["geometry"]
    building = next(feature for feature in result["features"] if feature["cost_analysis"])
    assert building["cost_analysis"]["cost"] == 2
    assert building["cost_analysis"]["rule_version"] == "ramke-building-tags-v1"
    assert client.get("/api/datasets/sample/download/geojson").json() == source
    assert (tmp_path / "sample/features.gpkg").read_bytes() == before
    assert client.get("/api/datasets/sample/features?analysis=bad").status_code == 422


def test_manifest_malformed_is_reported(dataset):
    root, _ = dataset
    (root / "demo/metadata.json").write_text(json.dumps({"schema_version": 99}))
    response = TestClient(create_app(root)).get("/api/datasets/demo")
    assert response.status_code == 422
    assert str(root) not in response.text


def test_external_symlink_is_not_exposed(dataset, tmp_path):
    root, _ = dataset
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    try:
        (root / "external").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("OS does not permit creating symlinks")
    client = TestClient(create_app(root))
    assert client.get("/api/datasets/external").status_code == 404
    assert "external" not in [item["id"] for item in client.get("/api/datasets").json()["datasets"]]


def test_missing_query_bounds_is_reported(dataset):
    root, _ = dataset
    manifest = root / "demo/metadata.json"
    metadata = json.loads(manifest.read_text())
    del metadata["query_bounds"]
    manifest.write_text(json.dumps(metadata))
    client = TestClient(create_app(root))
    assert client.get("/api/datasets/demo").status_code == 422
    assert client.get("/api/datasets").json()["datasets"][0]["verified"] is False
