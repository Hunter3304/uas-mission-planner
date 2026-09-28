from copy import deepcopy

import pytest

from uas_planner.core.costs import (
    RULES,
    analyze_all_layers,
    analyze_building,
    analyze_collection,
    classify_tag,
)


def test_independent_layers_include_nonbuildings_and_keep_flags_separate():
    source = {
        "features": [
            {"properties": props}
            for props in [
                {"highway": "footway", "landuse": "residential"},
                {"natural": "water"},
                {"natural": "tree"},
                {"landuse": "military", "building": "yes"},
                {"highway": "corridor"},
                {"name": "unclassified object"},
            ]
        ]
    }
    result = analyze_all_layers(source)
    summary = result["layer_summaries"]
    assert summary["highway"]["features"] == 2
    assert summary["highway"]["levels"]["3"] == 1
    assert summary["highway"]["without_numeric_cost"] == 1
    assert summary["natural"]["levels"]["0"] == 1
    assert summary["natural"]["defaulted"] == 1
    assert summary["landuse"]["obstruction_flagged"] == 1
    assert summary["building"]["obstruction_flagged"] == 0
    layers = result["features"][0]["layer_analyses"]
    assert layers["building"] is None
    assert layers["highway"]["cost"] == 3
    assert layers["landuse"]["cost"] == 4
    assert "layer_analyses" not in source["features"][0]
    empty = analyze_all_layers({"features": []})
    assert all(summary["features"] == 0 for summary in empty["layer_summaries"].values())


@pytest.mark.parametrize(
    "value,cost", [("hut", 0), ("barn", 1), ("yes", 2), ("warehouse", 3), ("house", 4)]
)
def test_paper_examples(value, cost):
    result = analyze_building({"building": value})
    assert result["cost"] == cost
    assert result["status"] == "matched"
    assert not result["has_default"]
    assert result["tags"][0]["matches"][0]["source"].startswith("Ramke")


@pytest.mark.parametrize("value", [None, "", "  ", "no", ["no"], []])
def test_absent_buildings_are_not_assigned_zero(value):
    assert analyze_building({"building": value, "landuse": "residential"}) is None


def test_unknown_and_known_medium_are_distinct():
    for value in ["future_type", 42, {"unexpected": True}]:
        result = classify_tag("building", value)
        assert result["cost"] == 2
        assert result["has_default"]
        assert result["value"] == value
    assert not classify_tag("building", "yes")["has_default"]
    assert classify_tag("name", "school")["cost"] is None
    assert classify_tag("name", "school")["status"] == "unscored"


def test_obstruction_is_independent_of_numeric_cost():
    school = analyze_building({"building": "school"})
    assert school["cost"] == 4 and school["obstruction"]
    kindergarten = analyze_building({"building": "kindergarten"})
    assert kindergarten["cost"] is None and kindergarten["obstruction"]
    assert kindergarten["status"] == "obstruction_only"
    assert not kindergarten["has_default"]
    assert classify_tag("highway", "corridor")["status"] == "excluded"


def test_other_tags_do_not_change_building_cost_or_infer_use():
    result = analyze_building(
        {
            "building": "yes",
            "landuse": "military",
            "natural": "water",
            "height": "10",
            "amenity": "school",
            "name": "Test",
            "osm_id": 123,
            "element_type": "way",
        }
    )
    assert result["cost"] == 2
    assert result["obstruction"]  # landuse flag, not the amenity
    tags = {tag["key"]: tag for tag in result["tags"]}
    assert tags["natural"]["cost"] == 0
    assert tags["height"]["status"] == "unscored"
    assert tags["amenity"]["cost"] is None
    assert "osm_id" not in tags
    assert not analyze_building({"building": "yes", "amenity": "school"})["obstruction"]


def test_multiple_values_preserve_unknown_and_obstruction_evidence():
    result = classify_tag("building", [" shed ; HOUSE ", "mystery", "kindergarten", "house"])
    assert result["cost"] == 4
    assert result["has_default"] and result["obstruction"]
    assert len(result["matches"]) == 4
    assert "Multiple values" in result["reason"]
    assert classify_tag("building", "no;house")["cost"] == 4


@pytest.mark.parametrize(
    "original,normalized,cost",
    [
        ("apartements", "apartments", 4),
        ("farm_auxilary", "farm_auxiliary", 1),
        ("train_staion", "train_station", 3),
        ("semidetached-house", "semidetached_house", 4),
    ],
)
def test_transcription_corrections_are_explained(original, normalized, cost):
    for value in (original, normalized):
        result = classify_tag("building", value)
        assert result["cost"] == cost
        assert result["matches"][0]["normalized"] == normalized
        assert "Project policy" in result["matches"][0]["reason"]
        assert result["value"] == value


def test_summary_and_source_preservation():
    source = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": None, "properties": tags}
            for tags in [
                {"building": "house", "landuse": "industrial"},
                {"building": "mystery"},
                {"building": "kindergarten"},
                {"highway": "residential"},
                {"building": "house", "landuse": "mystery"},
            ]
        ],
    }
    original = deepcopy(source)
    result = analyze_collection(source)
    assert source == original
    summary = result["cost_summary"]
    assert summary["buildings"] == 4
    assert summary["levels"] == {"0": 0, "1": 0, "2": 1, "3": 0, "4": 2}
    assert summary["defaulted"] == 1
    assert summary["obstruction_flagged"] == 1
    assert summary["without_numeric_cost"] == 1
    assert len(summary["unmatched_tags"]) == 2
    assert result["features"][3]["cost_analysis"] is None
    assert analyze_collection({"features": []})["cost_summary"]["buildings"] == 0


def test_config_has_unique_categories_and_valid_costs():
    for layer in RULES["layers"].values():
        assert set(layer["levels"]) == {"0", "1", "2", "3", "4"}
        values = [value for row in layer["levels"].values() for value in row]
        assert len(values) == len(set(values))
        assert not set(layer.get("supplements", {})).intersection(values)
