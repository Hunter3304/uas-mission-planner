"""Compact/detail/demo agreement and bounded original-object inspection."""

import json

import geopandas as gpd
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import GeometryCollection, LineString, Point, Polygon, shape

from uas_planner.api.app import create_app
from uas_planner.core import osm_display as display
from uas_planner.core.area import StudyRegion
from uas_planner.core.costs import analyze_all_layers
from uas_planner.storage.dataset import checksum, save_dataset


@pytest.fixture
def classified(tmp_path):
    tags = [
        {"building": "hospital", "highway": "service", "landuse": "military", "name": "mixed"},
        {"building": "house;future_value", "natural": "water"},
        {"building": ["hut", "barn", "apartements"]},
        {"building": "civic", "name": "costless obstruction"},
        {"highway": "corridor", "rare": "<script>original</script>"},
        {"building": "no", "highway": "no", "landuse": "", "natural": []},
        {"building": None, "natural": "tree"},
        {"building": 42, "natural": {"malformed": True}},
        {"natural": "wood;water", "landuse": "farmland"},
        {"building": "house", "note": "invalid original"},
        {"landuse": "military", "note": "unsupported original"},
        {"name": "no category"},
    ]
    geometries = [Point(10.01 + i * 0.001, 52.01) for i in range(len(tags))]
    geometries[9] = Polygon(
        [(10.02, 52.02), (10.03, 52.03), (10.03, 52.02), (10.02, 52.03), (10.02, 52.02)]
    )
    geometries[10] = GeometryCollection(
        [Point(10.04, 52.04), LineString([(10.04, 52.04), (10.05, 52.05)])]
    )
    frame = gpd.GeoDataFrame(
        {"element_type": ["way"] * len(tags), "osm_id": list(range(1, len(tags) + 1))},
        geometry=geometries,
        crs=4326,
    )
    directory = tmp_path / "classified"
    directory.mkdir()
    save_dataset(frame, directory / "osm", StudyRegion(10, 52, 10.1, 52.1), {}, tag_objects=tags)
    (directory / "study.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "regional-source-study",
                "config": {"bounds": {"west": 10, "south": 52, "east": 10.1, "north": 52.1}},
            }
        )
    )
    store = display.DisplayStore(tmp_path / ".osm-display")
    store.prepare(directory)
    return directory, tags, geometries, store


@pytest.mark.parametrize("category", display.CATEGORIES)
def test_compact_and_detail_agree_with_existing_demo(classified, category):
    directory, tags, geometries, store = classified
    source_hash = checksum(directory / "osm/features.gpkg")
    demo = analyze_all_layers({"features": [{"properties": t} for t in tags]})
    result = store.features(directory, (10, 52, 10.1, 52.1), style="cost", cost_category=category)
    expected = {
        f"way/{i + 1}"
        for i, (geometry, feature) in enumerate(zip(geometries, demo["features"]))
        if geometry.is_valid
        and geometry.geom_type != "GeometryCollection"
        and feature["layer_analyses"][category] is not None
    }
    assert {f["id"] for f in result["features"]} == expected
    assert result["display"]["complete"]
    for feature in result["features"]:
        index = feature["properties"]["osm_id"] - 1
        original = demo["features"][index]["layer_analyses"][category]
        assert feature["cost_analysis"] == {key: original[key] for key in display.SCORE_FIELDS}
        assert set(feature["cost_analysis"]) == set(display.SCORE_FIELDS)
        assert all(
            type(feature["cost_analysis"][f]) is bool for f in ("has_default", "obstruction")
        )
        detail = store.detail(directory, "way", index + 1)
        assert detail["properties"] == {**tags[index], "element_type": "way", "osm_id": index + 1}
        assert detail["layer_analyses"] == demo["features"][index]["layer_analyses"]
        assert shape(detail["geometry"]).equals_exact(geometries[index], 0)
        assert detail["display"]["identity"] == result["display"]["identity"]
        assert detail["display"]["classification_complete"]
    assert checksum(directory / "osm/features.gpkg") == source_hash


def test_cost_flags_stay_independent_and_membership_is_not_classification(classified):
    directory, _, _, store = classified
    first = store.detail(directory, "way", 1)["layer_analyses"]
    assert first["building"]["cost"] == 4 and first["building"]["obstruction"]
    assert first["highway"]["cost"] == 1 and not first["highway"]["obstruction"]
    assert first["landuse"]["cost"] is None and first["landuse"]["obstruction"]
    unknown = store.detail(directory, "way", 2)["layer_analyses"]["building"]
    assert unknown["cost"] == 4 and unknown["has_default"]  # mixed known/default stays gray
    result = store.features(directory, (10, 52, 10.1, 52.1))
    assert len({f["id"] for f in result["features"]}) == len(result["features"])
    excluded = next(f for f in result["features"] if f["id"] == "way/6")
    assert excluded["properties"]["categories"] == list(display.CATEGORIES)
    assert "cost_analysis" not in excluded
    assert all(a is None for a in store.detail(directory, "way", 6)["layer_analyses"].values())


@pytest.mark.parametrize(
    "identifier,reason,kind",
    [
        (10, "invalid_source_geometry", "Polygon"),
        (11, "unsupported_geometry_type", "GeometryCollection"),
    ],
)
def test_diagnostics_remain_inspectable_without_source_repair(classified, identifier, reason, kind):
    directory, _, geometries, store = classified
    detail = store.detail(directory, "way", identifier)
    assert detail["display"]["diagnostic"] == reason
    assert not detail["display"]["drawable"]
    assert detail["display"]["geometry_type"] == kind
    assert shape(detail["geometry"]).equals_exact(geometries[identifier - 1], 0)
    assert detail["layer_analyses"]
    assert detail["display"]["geometry_complete"]


def test_warm_costs_and_details_use_indexed_reads(classified, monkeypatch):
    directory, _, _, store = classified

    def forbidden(*args, **kwargs):
        pytest.fail("Warm display must not load/hash the source or reclassify viewport objects")

    monkeypatch.setattr(display, "checksum", forbidden)
    monkeypatch.setattr(display, "classify_layer", forbidden)
    monkeypatch.setattr(gpd, "read_file", forbidden)
    for category in display.CATEGORIES:
        assert store.features(
            directory, (10, 52, 10.1, 52.1), style="cost", cost_category=category
        )["display"]["complete"]
    assert store.detail(directory, "way", 1)["properties"]["name"] == "mixed"


def test_cost_queries_keep_resource_limits(classified, monkeypatch):
    directory, _, _, store = classified
    monkeypatch.setattr(display, "MAX_FEATURES", 1)
    result = store.features(directory, (10, 52, 10.1, 52.1), style="cost", cost_category="building")
    assert len(result["features"]) == 1
    assert result["display"]["limit_reason"] == "feature_limit"
    assert not result["display"]["complete"]


def test_geometry_budget_does_not_prevent_tag_diagnostic_inspection(classified, monkeypatch):
    directory, _, _, store = classified
    monkeypatch.setattr(display, "MAX_COORDINATES", 1)
    result = store.detail(directory, "way", 10)
    assert result["geometry"] is None
    assert result["display"]["geometry_omitted"] == "coordinate_limit"
    assert not result["display"]["geometry_complete"]
    assert result["display"]["classification_complete"]
    assert result["properties"]["note"] == "invalid original"
    monkeypatch.setattr(display, "MAX_COORDINATES", 100_000)
    monkeypatch.setattr(display, "MAX_SOURCE_GEOMETRY_BYTES", 1)
    result = store.detail(directory, "way", 10)
    assert result["geometry"] is None
    assert result["display"]["geometry_omitted"] == "source_geometry_byte_limit"
    assert result["display"]["tags_complete"]


def test_detail_expansion_and_response_budgets_are_explicit(classified, monkeypatch):
    directory, _, _, store = classified
    monkeypatch.setattr(display, "MAX_DETAIL_TAGS", 1)
    with pytest.raises(display.DisplayLimit, match="explanations"):
        store.detail(directory, "way", 1)
    monkeypatch.setattr(display, "MAX_DETAIL_TAGS", 512)
    monkeypatch.setattr(display, "MAX_DETAIL_TOKENS", 1)
    with pytest.raises(display.DisplayLimit, match="explanations"):
        store.detail(directory, "way", 3)
    monkeypatch.setattr(display, "MAX_DETAIL_TOKENS", 4096)
    monkeypatch.setattr(display, "MAX_BYTES", 300)
    with pytest.raises(display.DisplayLimit, match="response"):
        store.detail(directory, "way", 1)


def test_api_cost_style_ids_and_detail_errors(classified, monkeypatch):
    directory, _, _, _ = classified
    with TestClient(create_app(directory.parent)) as client:
        base = "/api/datasets/classified/study/osm/features"
        params = {"bbox": "10,52,10.1,52.1", "style": "cost", "cost_category": "highway"}
        response = client.get(base, params=params)
        assert response.status_code == 200
        assert response.json()["display"]["cost_category"] == "highway"
        assert response.headers["content-type"].startswith("application/geo+json")
        for extra in (
            {"cost_category": "bad"},
            {"cost_category": ""},
            {"style": "bad"},
            {"categories": "building"},
            {"style": "category"},
        ):
            assert client.get(base, params={**params, **extra}).status_code == 422
        for suffix in ("bad/1", "way/-1", "way/01", "way/1.0", "way/9223372036854775808"):
            assert client.get(base + "/" + suffix).status_code == 422
        assert client.get(base + "/node/1").status_code == 404
        assert client.get(base + "/way/999").status_code == 404
        assert (
            client.get(base + "/way/5").json()["properties"]["rare"] == "<script>original</script>"
        )
        monkeypatch.setattr(display, "MAX_DETAIL_TAGS", 1)
        response = client.get(base + "/way/1")
        assert response.status_code == 413 and str(directory) not in response.text


def test_schema_upgrade_requires_explicit_preparation(classified, monkeypatch):
    directory, _, _, store = classified
    monkeypatch.setattr(display, "SCHEMA", display.SCHEMA + 1)
    assert store.status(directory)["state"] == "not_prepared"
    with pytest.raises(display.DisplayUnavailable):
        store.detail(directory, "way", 1)


def test_source_changed_during_detail_is_rejected(classified, monkeypatch):
    directory, _, _, store = classified
    original = display.analyze_feature
    changed = False

    def change_source(*args, **kwargs):
        nonlocal changed
        if not changed:
            with (directory / "osm/features.gpkg").open("ab") as stream:
                stream.write(b"changed")
            changed = True
        return original(*args, **kwargs)

    monkeypatch.setattr(display, "analyze_feature", change_source)
    with pytest.raises(display.DisplayUnavailable, match="Source changed"):
        store.detail(directory, "way", 1)
