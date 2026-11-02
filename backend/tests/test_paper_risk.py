"""Independent arithmetic, rasterization, boundary and route-choice fixtures."""

from copy import deepcopy
from time import perf_counter
from types import SimpleNamespace

import pytest
from shapely.geometry import LineString, Point, Polygon, box, mapping
from test_regional_routing import planner as planner

from uas_planner.core.paper_risk import VERSION, FusedSurface, PaperRiskModel
from uas_planner.core.population_costs import prepare_population_surface
from uas_planner.core.risk import signature

X, Y = 500000, 5800000


def population(cells):
    boundary = cells[0][0]
    for cell in cells[1:]:
        boundary = boundary.union(cell[0])
    return SimpleNamespace(
        metadata={
            "identity": signature([(mapping(g), ident, s) for g, ident, s in cells]),
            "cell_size_m": 150,
            "study_boundary_metric": mapping(boundary),
        },
        metric_cells=cells,
    )


def model(cells, records=(), **kwargs):
    return PaperRiskModel(FusedSurface(population(cells), records, **kwargs), source={})


def test_paper_weights_have_hand_computed_235_objective():
    cell = box(X, Y, X + 150, Y + 150)
    records = [(cell, {"building": "house", "landuse": "grass", "highway": "track"}, "all")]
    # Use separately known classifications: house=4, grass=2, track=0.
    m = model([(cell, "one", 3)], records)
    result = m.evaluate([(X + 20, Y + 50), (X + 120, Y + 50)], input_crs=25832)
    assert result["assessment"] == "assessed"
    assert [
        result[f"{n}_length_cost"] for n in ("building", "landuse", "highway", "population")
    ] == pytest.approx([400, 200, 0, 300])
    assert result["fused_risk_length_cost"] == pytest.approx(250)
    assert result["objective_cost"] == pytest.approx(235)
    assert m.provenance["rules_version"] == VERSION


def test_natural_fallback_and_lines_are_rasterized_without_invented_width():
    a, b = box(X, Y, X + 150, Y + 150), box(X + 150, Y, X + 300, Y + 150)
    natural = (a.union(b), {"natural": "water"}, "water")
    road = (LineString([(X + 1, Y + 70), (X + 149, Y + 70)]), {"highway": "footway"}, "road")
    land = (b, {"landuse": "industrial"}, "land")
    s = FusedSurface(population([(a, "a", 0), (b, "b", 0)]), [natural, road, land])
    assert s.cells[0][2][:3] == (0, 0, 3)
    assert s.cells[1][2][:3] == (0, 3, 0)
    assert s.cells[0][5] == ("building",)


def test_duplicate_overlap_max_background_and_provisional_score():
    cell = box(X, Y, X + 150, Y + 150)
    low = (cell, {"building": "shed"}, "low")
    high = (cell, {"building": "house"}, "high")
    m = model([(cell, "one", 0)], [low, high, high], background=2)
    result = m.evaluate([(X + 20, Y + 20), (X + 120, Y + 20)], input_crs=25832)
    assert result["building_length_cost"] == pytest.approx(400)
    assert result["landuse_length_cost"] == result["highway_length_cost"] == pytest.approx(200)
    assert result["background_assumed"]
    unknown = model([(cell, "one", 0)], [(cell, {"building": "unrecognized"}, "unknown")])
    result = unknown.evaluate([(X + 20, Y + 20)], input_crs=25832)
    assert result["has_default"] and result["assessment"] == "assessed"


def test_shared_edge_selects_one_fused_cell_and_preserves_components():
    a, b = box(X, Y, X + 150, Y + 150), box(X + 150, Y, X + 300, Y + 150)
    m = model([(a, "a", 0), (b, "b", 2)], [(a, {"building": "house"}, "building")])
    path = [(X + 150, Y + 20), (X + 150, Y + 120)]
    result = m.evaluate(path, input_crs=25832)
    # Left fused=4/6; right fused=2/2. Choose right, not independent component maxima.
    assert result["building_length_cost"] == 0
    assert result["population_length_cost"] == pytest.approx(200)
    assert result["fused_risk_length_cost"] == pytest.approx(100)
    reverse = m.evaluate(path[::-1], input_crs=25832)
    assert reverse["objective_cost"] == result["objective_cost"]


def test_unknown_corner_zero_length_and_invalid_source_are_not_background():
    a, b = box(X, Y, X + 150, Y + 150), box(X + 150, Y, X + 300, Y + 150)
    m = model([(a, "a", 0), (b, "missing", None)], background=0)
    for path in [[(X + 150, Y + 50)], [(X + 20, Y + 20), (X + 150, Y + 150)]]:
        result = m.evaluate(path, input_crs=25832)
        assert result["assessment"] == "unresolved"
        assert result["objective_cost"] is result["building_length_cost"] is None
    zero = m.evaluate([(X + 20, Y + 20)], input_crs=25832)
    assert zero["assessment"] == "assessed" and zero["objective_cost"] == 0
    invalid = Polygon([(X, Y), (X + 100, Y + 100), (X, Y + 100), (X + 100, Y), (X, Y)])
    m = model([(a, "a", 0)], [(invalid, {"landuse": "industrial"}, "bad")])
    assert m.evaluate([(X + 20, Y + 20)], input_crs=25832)["assessment"] == "unresolved"


def test_points_use_one_stable_cell_and_deadline_is_bounded():
    a, b = box(X, Y, X + 150, Y + 150), box(X + 150, Y, X + 300, Y + 150)
    m = model([(a, "a", 0), (b, "b", 0)], [(Point(X + 150, Y + 50), {"natural": "scrub"}, "point")])
    assert m.surface.cells[0][2][1] == 1
    assert m.surface.cells[1][2][1] == 0
    m.deadline = perf_counter() - 1
    with pytest.raises(TimeoutError):
        m.evaluate([(X + 20, Y + 20)], input_crs=25832)


def test_150m_population_has_independent_identity_and_preserves_250m(tmp_path):
    from test_population_costs import study

    directory, _ = study(tmp_path)
    display = prepare_population_surface(directory)
    before = deepcopy(display.metadata)
    fusion = prepare_population_surface(directory, cell_m=150)
    assert fusion.metadata["cell_size_m"] == 150
    assert fusion.metadata["routing_cost"] is True
    assert "deferred" not in fusion.metadata["interpretation"]
    assert fusion.metadata["identity"] != display.metadata["identity"]
    assert fusion.metadata["estimated_people"] == pytest.approx(
        before["estimated_people"], abs=0.001
    )
    assert fusion.metadata["maximum_people_per_km2"] == pytest.approx(10000)
    assert prepare_population_surface(directory).metadata == before
    assert all(ident.startswith("population150:") for _, ident, _ in fusion.metric_cells)


@pytest.mark.parametrize("values", [[[0, 20], [40, 80]], [[0, 20], [40, -9999]]])
def test_batched_native_intersections_match_independent_scalar_aggregation(tmp_path, values):
    import rasterio
    from test_population_costs import raster

    from uas_planner.core.population_costs import aggregate_native

    path = raster(tmp_path / "native.tif", values, y=200)
    with rasterio.open(path) as src:
        for polygon in (box(25, 25, 175, 175), box(-100, 50, 100, 150), box(500, 500, 750, 750)):
            scalar = aggregate_native(src, polygon)
            batched = aggregate_native(src, polygon, vectorized=True)
            for key, value in scalar.items():
                assert (
                    batched[key] == pytest.approx(value)
                    if isinstance(value, float)
                    else batched[key] == value
                )


@pytest.mark.parametrize("category,value", [("highway", "motorway"), ("landuse", "residential")])
@pytest.mark.parametrize("algorithm", ["astar", "dijkstra"])
def test_road_or_landuse_alone_changes_route_choice(category, value, algorithm):
    from pyproj import Transformer

    from uas_planner.core.routing import plan_route

    cells = [
        (box(X + c * 150, Y + r * 150, X + (c + 1) * 150, Y + (r + 1) * 150), f"{r}:{c}", 0)
        for r in range(2)
        for c in range(2)
    ]
    feature = (
        LineString([(X + 1, Y + 75), (X + 299, Y + 75)])
        if category == "highway"
        else box(X, Y, X + 300, Y + 150)
    )
    base, changed = model(cells), model(cells, [(feature, {category: value}, "changed")])
    reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform
    nodes = [
        ("a", X + 25, Y + 75, 0, 0),
        ("b", X + 275, Y + 75, 0, 1),
        ("c", X + 25, Y + 225, 1, 0),
        ("d", X + 275, Y + 225, 1, 1),
    ]
    positions = {n: list(reverse(x, y)) for n, x, y, _, _ in nodes}
    grid = {
        "analysis_crs": "EPSG:25832",
        "cell_size_m": 150,
        "policy": "fixture",
        "assumptions": {"clearance_m": 0},
        "_constraint_check": lambda p: "permitted",
        "cells": [
            {
                "id": n,
                "center": positions[n],
                "center_metric": [x, y],
                "row": r,
                "col": c,
                "state": "permitted",
            }
            for n, x, y, r, c in nodes
        ],
        "edges": [
            {"from": a, "to": b, "state": "permitted"}
            for a, b in [("a", "b"), ("a", "c"), ("c", "d"), ("d", "b")]
        ],
        "connectors": [
            {
                "endpoint": name,
                "cell": n,
                "coordinate": positions[n],
                "state": "permitted",
                "length_m": 0,
            }
            for name, n in [("start", "a"), ("end", "b")]
        ],
    }
    original = plan_route(grid, risk_model=base, algorithm=algorithm)
    detour = plan_route(grid, risk_model=changed, algorithm=algorithm)
    assert original["status"] == detour["status"] == "success"
    assert original["length_m"] == pytest.approx(250)
    assert detour["length_m"] == pytest.approx(550)
    assert detour["objective_cost"] == pytest.approx(145, abs=1e-5)


@pytest.mark.parametrize(
    "field",
    [
        "building_length_cost",
        "landuse_length_cost",
        "highway_length_cost",
        "fused_risk_length_cost",
    ],
)
def test_independent_validation_rejects_changed_component(planner, monkeypatch, field):
    from uas_planner.core import regional_routing as routing

    original = routing.plan_route

    def corrupt(*args, **kwargs):
        result = original(*args, **kwargs)
        result[field] += 1
        return result

    monkeypatch.setattr(routing, "plan_route", corrupt)
    result = planner.plan("a", "b", cell_m=50)
    assert result["status"] == "computational_failure"
    assert all(
        result.get(name) is None for name in ("geometry", "length_m", "objective_cost", field)
    )
