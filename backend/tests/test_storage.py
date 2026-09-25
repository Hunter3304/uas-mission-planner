import json

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point, Polygon

from uas_planner.core.area import BoundingBox
from uas_planner.storage.dataset import load_dataset, save_dataset


@pytest.fixture
def features():
    return gpd.GeoDataFrame(
        {
            "element_type": ["node", "way", "relation"],
            "osm_id": [1, 1, 2],
            "name": ["Baum", None, "Park"],
            "extra": [["a", "b"], "road", None],
        },
        geometry=[
            Point(10.52, 52.27),
            LineString([(10.52, 52.27), (10.521, 52.271)]),
            Polygon([(10.52, 52.27), (10.521, 52.27), (10.521, 52.271), (10.52, 52.27)]),
        ],
        crs=4326,
    )


AREA = BoundingBox(10.519, 52.269, 10.522, 52.272)


def test_roundtrip_preserves_tags_identity_geometry_crs(tmp_path, features):
    destination = tmp_path / "dataset"
    save_dataset(features, destination, AREA, {"building": True})
    loaded, metadata = load_dataset(destination)
    assert list(loaded.osm_id) == [1, 1, 2]
    assert list(loaded.element_type) == list(features.element_type)
    assert list(loaded["name"]) == list(features["name"])
    assert list(loaded.extra) == list(features.extra)
    assert loaded.geometry.geom_equals(features.geometry).all()
    assert loaded.crs == features.crs
    assert metadata["feature_count"] == 3
    with pytest.raises(FileExistsError):
        save_dataset(features, destination, AREA, {})


def test_empty_dataset_roundtrip(tmp_path, features):
    destination = tmp_path / "empty"
    save_dataset(features.iloc[:0], destination, AREA, {})
    loaded, metadata = load_dataset(destination)
    assert loaded.empty
    assert loaded.crs.to_epsg() == 4326
    assert metadata["feature_count"] == 0


def test_corrupted_dataset_is_rejected(tmp_path, features):
    destination = tmp_path / "corrupt"
    save_dataset(features, destination, AREA, {})
    with (destination / "features.gpkg").open("ab") as stream:
        stream.write(b"corruption")
    with pytest.raises(ValueError, match="checksum"):
        load_dataset(destination)


def test_metadata_count_mismatch_is_rejected(tmp_path, features):
    destination = tmp_path / "wrong-count"
    save_dataset(features, destination, AREA, {})
    path = destination / "metadata.json"
    metadata = json.loads(path.read_text())
    metadata["feature_count"] = 0
    path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="count"):
        load_dataset(destination)


def test_duplicate_identity_rejected_before_output(tmp_path, features):
    features.loc[1, "element_type"] = "node"
    with pytest.raises(ValueError, match="unique"):
        save_dataset(features, tmp_path / "duplicate", AREA, {})
    assert not (tmp_path / "duplicate").exists()


@pytest.mark.parametrize(
    "change",
    [
        None,
        [],
        {"tag_columns": None},
        {"tag_columns": ["name", "name"]},
        {"tag_columns": ["geometry"]},
        {"query_bounds": None},
        {"feature_count": True},
        {"sha256": "bad"},
        {"crs": "EPSG:3857"},
    ],
)
def test_malformed_manifest_is_rejected(tmp_path, features, change):
    destination = tmp_path / "invalid"
    metadata = save_dataset(features, destination, AREA, {})
    if isinstance(change, dict):
        metadata.update(change)
    else:
        metadata = change
    (destination / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError):
        load_dataset(destination)


@pytest.mark.parametrize("tags", ["[]", "null", "broken"])
def test_malformed_stored_tags_are_rejected(tmp_path, features, tags):
    from uas_planner.storage.dataset import checksum

    destination = tmp_path / "invalid-tags"
    metadata = save_dataset(features, destination, AREA, {})
    stored = gpd.read_file(destination / "features.gpkg", layer="features")
    stored["tags_json"] = tags
    stored.to_file(
        destination / "features.gpkg", layer="features", driver="GPKG", mode="w", index=False
    )
    metadata["sha256"] = checksum(destination / "features.gpkg")
    (destination / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="tags"):
        load_dataset(destination)
