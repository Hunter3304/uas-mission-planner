"""Analytical costs, independent graph oracle, clearance and snapshot integrity."""

from copy import deepcopy
from math import cos, pi, sin

import pytest
from pyproj import Transformer
from shapely.geometry import Point, Polygon, box, mapping
from shapely.ops import transform
from test_routing import metric_graph

from uas_planner.core.experiment import load_experiment, read_json, write_json
from uas_planner.core.grid import build_grid
from uas_planner.core.risk import RiskModel, _prepared_model, prepare_risk_model
from uas_planner.core.risk_routing import plan_risk_route
from uas_planner.core.routing import connect_endpoints, constraint_checker, plan_route, search_graph
from uas_planner.route_demo import create_route_demo


def collection(*entries):
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"element_type": "way", "osm_id": i, "building": tag},
                "geometry": mapping(geometry),
            }
            for i, (geometry, tag) in enumerate(entries)
        ],
    }


def model(features=None, **options):
    return RiskModel(
        features or collection(),
        mapping(box(-10, -10, 110, 110)),
        input_crs="EPSG:25832",
        **options,
    )


def evaluate(risk, *points):
    return risk.evaluate(points, input_crs="EPSG:25832")


def test_hand_calculated_lengths_and_subdivision():
    risk = model(collection((box(0, -1, 20, 1), "house")), background_cost=0)
    whole = evaluate(risk, (0, 0), (100, 0))
    assert whole["length_m"] == 100
    assert whole["risk_length_cost"] == 80
    assert whole["objective_cost"] == 82
    halves = [evaluate(risk, (0, 0), (10, 0)), evaluate(risk, (10, 0), (100, 0))]
    assert sum(part["risk_length_cost"] for part in halves) == whole["risk_length_cost"]
    assert sum(part["objective_cost"] for part in halves) == whole["objective_cost"]
    assert whole["source_ids"] == ["way/0"]
    assert whole["background_assumed"]


def test_overlap_maximum_duplicates_and_background_not_added_under_buildings():
    features = collection(
        (box(0, -1, 50, 1), "yes"),
        (box(25, -1, 75, 1), "house"),
        (box(25, -1, 75, 1), "house"),
    )
    result = evaluate(model(features, background_cost=3), (0, 0), (100, 0))
    assert result["risk_length_cost"] == 25 * 2 + 50 * 4 + 25 * 3
    assert result["source_ids"] == ["way/0", "way/1", "way/2"]


def test_unknown_support_default_classification_and_obstruction_only():
    assert evaluate(model(), (0, 0), (100, 0))["assessment"] == "unresolved"
    known = model(collection((box(0, -1, 100, 1), "new-type")))
    result = evaluate(known, (0, 0), (100, 0))
    assert result["risk_length_cost"] == 200 and result["has_default"]
    missing = model(collection((box(10, -1, 20, 1), "kindergarten")), background_cost=0)
    assert evaluate(missing, (0, 0), (100, 0))["assessment"] == "unresolved"
    # A historical obstruction flag does not automatically forbid a scored house/school.
    school = model(collection((box(0, -1, 100, 1), "school")))
    assert evaluate(school, (0, 0), (100, 0))["risk_length_cost"] == 400


def test_point_support_zero_length_and_outside_domain():
    risk = model(collection((box(0, -1, 20, 1), "house")))
    assert evaluate(risk, (10, 0))["risk_length_cost"] == 0
    assert evaluate(risk, (50, 0), (50, 0))["assessment"] == "unresolved"
    assert evaluate(model(background_cost=0), (200, 0))["assessment"] == "unresolved"
    with pytest.raises(ValueError, match="sum segments"):
        evaluate(risk, (0, 0), (10, 0), (0, 0))


def test_invalid_and_nonpolygon_buildings_are_explicit():
    invalid = Polygon([(0, 0), (10, 10), (0, 10), (10, 0)])
    with pytest.raises(ValueError, match="not repaired"):
        model(collection((invalid, "house")))
    risk = model(collection((Point(10, 10), "house")), background_cost=0)
    assert risk.provenance["diagnostics"][0]["status"] == "unsupported_geometry"
    assert evaluate(risk, (0, 0), (100, 0))["assessment"] == "unresolved"
    with pytest.raises(ValueError, match="projected CRS"):
        model(analysis_crs="EPSG:4326")


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True])
@pytest.mark.parametrize(
    "key", ["background_cost", "risk_weight", "distance_weight", "safety_distance_m"]
)
def test_invalid_configuration(value, key):
    with pytest.raises(ValueError, match="finite nonnegative"):
        model(**{key: value})


def test_weighted_search_admissible_heuristic_and_separate_distance():
    positions = {"s": (0, 0), "a": (0, 50), "b": (100, 50), "g": (100, 0)}
    edges = [("s", "g", 100, 30), ("s", "a", 50, 5), ("a", "b", 100, 10), ("b", "g", 50, 5)]
    for algorithm in ("astar", "dijkstra"):
        result = search_graph(positions, edges, "s", "g", algorithm=algorithm, objective="risk")
        assert result["objective_cost"] == 20 and result["length_m"] == 200
        assert result["nodes"] == ["s", "a", "b", "g"]
    assert search_graph(positions, edges, "s", "g")["length_m"] == 100
    with pytest.raises(ValueError, match="lower bound"):
        search_graph(positions, [("s", "g", 100, 1)], "s", "g", objective="risk")


def test_buffered_partial_overlap_complete_motion_and_boundary():
    grid = metric_graph()
    reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform
    grid["validation"]["blocked"] = [
        mapping(transform(reverse, box(500010, 5799990, 500020, 5800010)))
    ]
    zero, buffered = constraint_checker(grid), constraint_checker(grid, 5)
    near = list(reverse(500007, 5800000))
    assert zero([near]) == "permitted" and buffered([near]) == "blocked"
    assert buffered([list(reverse(500015, 5800000))]) == "blocked"
    assert zero([list(reverse(500010, 5800000))]) == "blocked"
    a, b = list(reverse(500000, 5800000)), list(reverse(500030, 5800000))
    assert zero([a]) == zero([b]) == "permitted"
    assert zero([a, b]) == "blocked"
    outside_clearance = list(reverse(499972, 5800000))
    assert zero([outside_clearance]) == "permitted"
    assert buffered([outside_clearance]) == "blocked"


def test_clearance_circle_approximation_is_conservative():
    grid = metric_graph()
    reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform
    x, y = 500000 + 4.999 * cos(pi / 64), 5800000 + 4.999 * sin(pi / 64)
    grid["validation"]["blocked"] = [
        mapping(transform(reverse, box(x - 0.0001, y - 0.0001, x + 0.0001, y + 0.0001)))
    ]
    origin = list(reverse(500000, 5800000))
    assert constraint_checker(grid)([origin]) == "permitted"
    assert constraint_checker(grid, 5)([origin]) == "blocked"


def test_overflow_and_result_provenance_isolation():
    with pytest.raises(ValueError, match="overflow"):
        evaluate(model(background_cost=1e308), (0, 0), (100, 0))
    grid = metric_graph()
    risk = grid_model(grid)
    result = plan_route(grid, risk_model=risk)
    result["risk_model"]["risk_weight"] = 123
    assert risk.provenance["risk_weight"] == 0.9


def grid_model(grid, features=None, **options):
    return RiskModel(
        features or collection(), grid["validation"]["boundary"], background_cost=0, **options
    )


def test_full_route_risk_detour_connectors_and_oracle():
    grid = metric_graph()
    reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform
    features = collection((transform(reverse, box(500025, 5800025, 500075, 5800075)), "house"))
    risk = grid_model(grid, features)
    baseline = plan_route(grid)
    astar = plan_route(grid, risk_model=risk)
    oracle = plan_route(grid, risk_model=risk, algorithm="dijkstra")
    assert astar["status"] == oracle["status"] == "success"
    assert astar["length_m"] > baseline["length_m"]
    assert astar["objective_cost"] == pytest.approx(oracle["objective_cost"])
    direct = risk.evaluate([c["coordinate"] for c in grid["connectors"]])
    assert astar["objective_cost"] < direct["objective_cost"]
    selected = {
        "start": list(reverse(500005, 5800000)),
        "end": grid["connectors"][1]["coordinate"],
    }
    result = plan_route(connect_endpoints(grid, selected), risk_model=risk)
    segments = result["geometry"]["coordinates"]
    assert segments[0] == selected["start"]
    independent = [risk.evaluate([a, b]) for a, b in zip(segments, segments[1:])]
    assert result["length_m"] == pytest.approx(sum(v["length_m"] for v in independent))
    assert result["risk_length_cost"] == pytest.approx(
        sum(v["risk_length_cost"] for v in independent)
    )
    assert result["objective_cost"] == pytest.approx(
        0.9 * result["risk_length_cost"] + 0.1 * result["length_m"]
    )


def test_risk_missing_support_and_zero_route_flags():
    grid = metric_graph()
    missing = RiskModel(collection(), grid["validation"]["boundary"])
    assert plan_route(grid, risk_model=missing)["status"] == "unresolved_input"
    point = grid["connectors"][0]["coordinate"]
    zero = connect_endpoints(grid, {"start": point, "end": point})
    result = plan_route(zero, risk_model=grid_model(grid))
    assert result["length_m"] == result["risk_length_cost"] == result["objective_cost"] == 0
    assert result["assessment_flags"]["background_assumed"]
    grid["validation"]["unresolved"] = True
    assert plan_route(grid, risk_model=grid_model(grid))["status"] == "unresolved_input"


def test_snapshot_cache_identity_and_integrity_before_cache(tmp_path):
    directory = tmp_path / "demo"
    manifest = create_route_demo(directory)
    grid = build_grid(directory, manifest)
    _prepared_model.cache_clear()
    first = prepare_risk_model(directory, manifest, grid, background_cost=0)
    assert prepare_risk_model(directory, manifest, grid, background_cost=0) is first
    assert _prepared_model.cache_info().hits == 1
    assert prepare_risk_model(directory, manifest, grid, background_cost=2) is not first
    assert prepare_risk_model(directory, manifest, grid, distance_weight=0.2) is not first
    assert prepare_risk_model(directory, manifest, grid, safety_distance_m=5) is not first
    changed = deepcopy(manifest)
    changed["config"]["agl_m"] = 80
    assert prepare_risk_model(directory, changed, grid, background_cost=0) is not first
    result = plan_risk_route(directory, manifest, grid=grid, background_cost=0)
    assert result["status"] == "success"
    assert result["risk_model"]["source"]["osm_sha256"]
    assert "weighted objective" in result["experiment"]["optimality"]
    (directory / "osm/features.gpkg").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        prepare_risk_model(directory, manifest, grid, background_cost=0)


def test_real_policy_stays_unresolved_with_explicit_background(tmp_path):
    directory = tmp_path / "demo"
    create_route_demo(directory)
    manifest = read_json(directory / "experiment.json")
    manifest.pop("routing_fixture")
    write_json(directory / "experiment.json", manifest)
    result = plan_risk_route(directory, load_experiment(directory), background_cost=0)
    assert result["status"] == "unresolved_input"
    assert result["geometry"] is None
