"""Hand-computed costs, actual route-choice effects and shared planner contracts."""

import json
from importlib.util import find_spec
from math import sqrt
from time import perf_counter
from types import SimpleNamespace

import pytest
import test_flight_interval as flight_fixtures
import test_population_costs as population_fixtures
import test_regional_routing as regional_fixtures
from fastapi.testclient import TestClient
from shapely.geometry import box, mapping

from uas_planner.api.app import create_app
from uas_planner.core import regional_routing as routing
from uas_planner.core.population_costs import PopulationResourceLimit, prepare_population_surface
from uas_planner.core.population_routing import PopulationEvaluator, PopulationRiskModel
from uas_planner.core.risk import RiskModel, signature
from uas_planner.core.routing import plan_route, route_geojson

X, Y = 500000, 5800000


def surface(boundary, cells):
    metadata = {
        "identity": signature([(mapping(g), ident, score) for g, ident, score in cells]),
        "study_boundary_metric": mapping(boundary),
        "version": "ramke-population-250m-v1",
        "normalization_scope": "complete_saved_study",
        "maximum_people_per_km2": 10000,
        "cell_size_m": 250,
        "native_support_m": 100,
    }
    return SimpleNamespace(metadata=metadata, metric_cells=tuple(cells))


def squares(unknown=False):
    boundary = box(X, Y, X + 400, Y + 400)
    cells = [
        (box(X, Y, X + 250, Y + 250), "lower-left", None if unknown else 4),
        (box(X + 250, Y, X + 400, Y + 250), "lower-right", 0),
        (box(X, Y + 250, X + 250, Y + 400), "upper-left", 0),
        (box(X + 250, Y + 250, X + 400, Y + 400), "upper-right", 0),
    ]
    return surface(boundary, cells)


def composite(population, weight=1, objective="distance", **weights):
    base = RiskModel(
        {"type": "FeatureCollection", "features": []},
        population.metadata["study_boundary_metric"],
        input_crs=25832,
        background_cost=0,
        risk_weight=weights.get("risk_weight", 0),
        distance_weight=weights.get("distance_weight", 1),
    )
    return PopulationRiskModel(
        base, PopulationEvaluator(population), objective=objective, population_weight=weight
    )


def test_length_times_class_diagonals_repeated_traversal_and_zero():
    s = surface(
        box(X, Y, X + 250, Y + 100),
        [(box(X, Y, X + 100, Y + 100), "one", 1), (box(X + 100, Y, X + 250, Y + 100), "three", 3)],
    )
    model = PopulationEvaluator(s)
    a, b = (X + 50, Y + 50), (X + 200, Y + 50)
    result = model.evaluate([a, b], input_crs=25832)
    assert result["population_length_cost"] == pytest.approx(350, abs=1e-5)
    assert model.evaluate([b, a], input_crs=25832)["population_length_cost"] == pytest.approx(
        350, abs=1e-5
    )
    assert sum(
        model.evaluate(p, input_crs=25832)["population_length_cost"] for p in ([a, b], [b, a])
    ) == pytest.approx(700, abs=1e-5)
    assert model.evaluate([a], input_crs=25832)["population_length_cost"] == 0
    diagonal = model.evaluate([(X + 25, Y + 25), (X + 75, Y + 75)], input_crs=25832)
    assert diagonal["population_length_cost"] == pytest.approx(50 * sqrt(2))


def test_shared_edge_maximum_counted_once_and_unknown_point_touch():
    s = surface(
        box(X, Y, X + 200, Y + 100),
        [(box(X, Y, X + 100, Y + 100), "one", 1), (box(X + 100, Y, X + 200, Y + 100), "three", 3)],
    )
    points = [(X + 100, Y + 20), (X + 100, Y + 80)]
    assert PopulationEvaluator(s).evaluate(points, input_crs=25832)[
        "population_length_cost"
    ] == pytest.approx(180)
    s.metric_cells = (*s.metric_cells[:1], (s.metric_cells[1][0], "missing", None))
    model = PopulationEvaluator(s)
    for path in (points, [points[0]], [(X + 20, Y + 20), (X + 100, Y + 100)]):
        result = model.evaluate(path, input_crs=25832)
        assert result["assessment"] == "unresolved"
        assert result["population_length_cost"] is None
        assert result["population_unknown_cell_ids"] == ["missing"]


def test_missing_or_outside_population_cannot_be_filled_by_building_background():
    model = composite(squares(unknown=True))
    a = [X + 25, Y + 225]
    assert model.evaluate([a], input_crs=25832)["assessment"] == "unresolved"
    outside = model.population.evaluate([[X + 500, Y + 50]], input_crs=25832)
    assert outside["population_outside_support"] and outside["population_length_cost"] is None
    for bad in ([[float("nan"), Y]], [[True, Y]], [[190, 52]], []):
        with pytest.raises(ValueError):
            model.population.evaluate(bad)


def controlled_graph(weight, algorithm):
    s = squares()
    model = composite(s, weight)
    reverse = routing.Transformer.from_crs(25832, 4326, always_xy=True).transform
    nodes = [
        ("a", X + 25, Y + 225, 0, 0),
        ("b", X + 375, Y + 225, 0, 1),
        ("c", X + 25, Y + 275, 1, 0),
        ("d", X + 375, Y + 275, 1, 1),
    ]
    cells = [
        {
            "id": name,
            "center": list(reverse(x, y)),
            "center_metric": [x, y],
            "row": row,
            "col": col,
            "state": "permitted",
        }
        for name, x, y, row, col in nodes
    ]
    coordinates = {c["id"]: c["center"] for c in cells}
    grid = {
        "analysis_crs": "EPSG:25832",
        "cell_size_m": 250,
        "policy": "fixture",
        "assumptions": {"clearance_m": 0},
        "validation": {
            "boundary": mapping(
                s.metric_cells[0][0]
                .union(s.metric_cells[1][0])
                .union(s.metric_cells[2][0])
                .union(s.metric_cells[3][0])
            )
        },
        "_constraint_check": lambda p: "permitted",
        "cells": cells,
        "edges": [
            {"from": a, "to": b, "state": "permitted"}
            for a, b in [("a", "b"), ("a", "c"), ("c", "d"), ("d", "b")]
        ],
        "connectors": [
            {
                "endpoint": name,
                "cell": cell,
                "coordinate": coordinates[cell],
                "state": "permitted",
                "length_m": 0,
            }
            for name, cell in [("start", "a"), ("end", "b")]
        ],
    }
    return plan_route(grid, risk_model=model, algorithm=algorithm)


@pytest.mark.parametrize("algorithm", ["astar", "dijkstra"])
def test_calculable_route_choice_threshold(algorithm):
    # Two alternatives: L=350,P=900 versus L=450,P=100; switch at w=0.125.
    low = controlled_graph(0.1, algorithm)
    high = controlled_graph(0.2, algorithm)
    assert low["status"] == high["status"] == "success"
    assert low["length_m"] == pytest.approx(350)
    assert low["population_length_cost"] == pytest.approx(900, abs=1e-5)
    assert low["objective_cost"] == pytest.approx(440, abs=1e-5)
    assert high["length_m"] == pytest.approx(450)
    assert high["population_length_cost"] == pytest.approx(100, abs=1e-5)
    assert high["objective_cost"] == pytest.approx(470, abs=1e-5)


@pytest.fixture
def planner(monkeypatch):
    planner = regional_fixtures.planner.__wrapped__(monkeypatch)
    calls = []

    def prepare(directory, **kwargs):
        calls.append(kwargs)
        return squares()

    monkeypatch.setattr(routing, "prepare_population_surface", prepare)
    planner.population_preparations = calls
    return planner


def test_regional_distance_population_is_separate_and_changes_route(planner):
    baseline = planner.plan("a", "b", objective="distance", cell_m=50)
    a = planner.plan("a", "b", objective="distance", cell_m=50, include_population=True)
    d = planner.plan(
        "a", "b", objective="distance", cell_m=50, include_population=True, algorithm="dijkstra"
    )
    assert a["status"] == d["status"] == "success"
    assert a["independent_validation"] and d["independent_validation"]
    assert a["objective_cost"] == pytest.approx(d["objective_cost"])
    assert a["geometry"] != baseline["geometry"] and a["length_m"] > baseline["length_m"]
    assert a["risk_length_cost"] is None
    assert a["objective_cost"] == pytest.approx(a["length_m"] + a["population_length_cost"])
    assert a["effective_weights"] == {"building": 0, "distance": 1, "population": 1}
    assert a["objective"] == "distance" and a["effective_objective"] == "distance+population"
    assert a["provenance"]["ghsl_routing_cost"] is True
    assert len(planner.population_preparations) == 1
    exported = json.loads(json.dumps(route_geojson(a)))
    assert exported["metadata"]["population_model"]["identity"] == a["population_model"]["identity"]
    assert (
        exported["features"][0]["properties"]["population_length_cost"]
        == a["population_length_cost"]
    )


@pytest.mark.parametrize("weights", [(0.9, 0.1), (0.2, 0.7), (0, 0)])
def test_combined_building_population_objective_and_population_only(planner, weights):
    risk, distance = weights
    result = planner.plan(
        "a",
        "b",
        cell_m=50,
        background_cost=0,
        include_population=True,
        population_weight=0.3,
        risk_weight=risk,
        distance_weight=distance,
    )
    assert result["status"] == "success" and result["independent_validation"]
    assert result["objective_cost"] == pytest.approx(
        risk * result["risk_length_cost"]
        + distance * result["length_m"]
        + 0.3 * result["population_length_cost"]
    )


def test_inactive_population_skips_preparation_and_hidden_invalid_weight(planner, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Inactive population must not be prepared")

    monkeypatch.setattr(routing, "prepare_population_surface", forbidden)
    a = planner.plan("a", "b", objective="distance", cell_m=50, population_weight=float("nan"))
    b = planner.plan(
        "a", "b", objective="distance", cell_m=50, include_population=True, population_weight=0
    )
    assert a["geometry"] == b["geometry"]
    assert a["population_length_cost"] is b["population_length_cost"] is None
    assert not a["population_active"] and not b["population_active"]
    json.dumps(a, allow_nan=False)
    for bad in (-1, float("nan"), float("inf"), True):
        with pytest.raises(ValueError):
            planner.plan("a", "b", include_population=True, population_weight=bad)
    with pytest.raises(ValueError):
        planner.plan("a", "b", include_population="true")


def test_unknown_endpoint_zero_route_and_resource_limit(planner, monkeypatch):
    monkeypatch.setattr(routing, "prepare_population_surface", lambda *a, **kw: squares(True))
    unknown = planner.plan("a", "b", objective="distance", cell_m=50, include_population=True)
    assert unknown["status"] == "unresolved_input"
    assert unknown["endpoint_diagnostics"]["start"]["population"]["population_unknown_cell_ids"]
    assert unknown["population_length_cost"] is None
    planner._population = None
    monkeypatch.setattr(routing, "prepare_population_surface", lambda *a, **kw: squares())
    same = planner.plan("a", "a", objective="distance", cell_m=50, include_population=True)
    assert same["status"] == "success" and same["population_length_cost"] == same["length_m"] == 0
    planner._population = None

    def limit(*a, **kw):
        raise PopulationResourceLimit("Population preparation deadline reached.")

    monkeypatch.setattr(routing, "prepare_population_surface", limit)
    result = planner.plan("a", "b", objective="distance", cell_m=50, include_population=True)
    assert result["status"] == "resource_limit" and result["controls"]["include_population"]


def test_failed_population_validation_clears_all_costs(planner, monkeypatch):
    original = routing.plan_route

    def corrupt(*args, **kwargs):
        result = original(*args, **kwargs)
        result["population_length_cost"] += 1
        return result

    monkeypatch.setattr(routing, "plan_route", corrupt)
    result = planner.plan("a", "b", objective="distance", cell_m=50, include_population=True)
    assert result["status"] == "computational_failure"
    assert all(
        result[k] is None
        for k in (
            "geometry",
            "length_m",
            "risk_length_cost",
            "population_length_cost",
            "objective_cost",
            "cruise_time_s",
        )
    )


def test_api_controls_and_failure_exports(planner, tmp_path, monkeypatch):
    monkeypatch.setattr(routing, "RegionalPlanner", lambda *a, **kw: planner)
    (tmp_path / "study").mkdir()
    request = {
        "scenario": planner.constraints.scenario,
        "start_id": "a",
        "end_id": "b",
        "objective": "distance",
        "cell_m": 50,
        "include_population": True,
        "population_weight": 0.5,
        "export": True,
    }
    with TestClient(create_app(tmp_path)) as client:
        response = client.post("/api/datasets/study/study/route", json=request)
        assert response.status_code == 200
        result = response.json()["metadata"]
        assert result["population_active"] and result["effective_weights"]["population"] == 0.5
        assert result["population_model"]["normalization_scope"] == "complete_saved_study"
        assert (
            client.post(
                "/api/datasets/study/study/route", json={**request, "population_weight": -1}
            ).status_code
            == 422
        )
        planner.constraints.forced = "blocked"
        failed = client.post("/api/datasets/study/study/route", json=request).json()
        assert failed["features"] == [] and failed["metadata"]["controls"]["include_population"]


@pytest.mark.skipif(find_spec("ompl") is None, reason="Optional native OMPL absent")
def test_native_population_costs_and_budget(planner):
    result = planner.plan(
        "a",
        "b",
        objective="distance",
        algorithm="abitstar",
        include_population=True,
        time_budget_s=0.5,
    )
    assert result["status"] == "success" and result["independent_validation"]
    assert result["objective_cost"] == pytest.approx(
        result["length_m"] + result["population_length_cost"]
    )
    assert result["risk_length_cost"] is None
    expired = planner.plan(
        "a",
        "b",
        objective="distance",
        algorithm="abitstar",
        include_population=True,
        time_budget_s=0,
    )
    assert expired["status"] == "timeout" and expired["population_length_cost"] is None


def test_objective_overflow_and_deadline():
    model = composite(squares(), weight=1e308)
    with pytest.raises(ValueError, match="overflow"):
        model.evaluate([[X + 25, Y + 225], [X + 200, Y + 225]], input_crs=25832)
    model.deadline = perf_counter() - 1
    with pytest.raises(TimeoutError):
        model.evaluate([[X + 25, Y + 225]], input_crs=25832)


def test_corridor_retries_keep_one_population_reference(planner, monkeypatch):
    original = routing.plan_route
    identities = []

    def first_failure(*args, **kwargs):
        identities.append(kwargs["risk_model"].provenance["population_model"]["identity"])
        if len(identities) == 1:
            return {
                "status": "no_path_on_grid",
                "geometry": None,
                "length_m": None,
                "risk_length_cost": None,
                "population_length_cost": None,
                "objective_cost": None,
            }
        return original(*args, **kwargs)

    monkeypatch.setattr(routing, "plan_route", first_failure)
    result = planner.plan(
        "a", "b", objective="distance", cell_m=50, include_population=True, corridor_margin_m=100
    )
    assert result["status"] == "success" and len(result["search_attempts"]) == 2
    assert len(set(identities)) == len(planner.population_preparations) == 1


def test_unknown_edges_are_not_reported_as_proven_infeasibility(planner, monkeypatch):
    boundary = planner.constraints.boundary
    s = surface(
        boundary,
        [
            (box(X, Y, X + 150, Y + 400), "left", 0),
            (box(X + 150, Y, X + 250, Y + 400), "missing", None),
            (box(X + 250, Y, X + 400, Y + 400), "right", 0),
        ],
    )
    monkeypatch.setattr(routing, "prepare_population_surface", lambda *a, **kw: s)
    result = planner.plan("a", "b", objective="distance", cell_m=50, include_population=True)
    assert result["status"] == "unresolved_input"
    assert result["geometry"] is result["population_length_cost"] is None
    assert result["endpoint_diagnostics"]["start"]["population"]["assessment"] == "assessed"
    assert result["endpoint_diagnostics"]["end"]["population"]["assessment"] == "assessed"


def test_automatic_duration_preserves_population_identity_and_costs(monkeypatch):
    model = flight_fixtures.model.__wrapped__(flight_fixtures.scenario.__wrapped__())
    model, counts, run = flight_fixtures.automatic.__wrapped__(model, monkeypatch)
    prepared = []

    def prepare(*a, **kw):
        prepared.append(kw)
        return surface(model.boundary, [(model.boundary, "study", 2)])

    monkeypatch.setattr(routing, "prepare_population_surface", prepare)
    result = run(include_population=True, population_weight=0.3, time_budget_s=3)
    assert result["status"] == "success" and result["independent_validation"]
    assert result["population_length_cost"] == pytest.approx(2 * result["length_m"])
    assert result["objective_cost"] == pytest.approx(1.6 * result["length_m"])
    identity = result["population_model"]["identity"]
    assert result["provenance"]["population_model_identity"] == identity
    assert result["risk_model"]["source"]["ghsl_routing_cost"]
    assert len(prepared) == 1 and counts == {"prepare": 1, "close": 1}
    assert result["mission"]["mission_end"] == result["timing"]["estimated_arrival"]
    assert route_geojson(result)["metadata"]["population_model"]["identity"] == identity
    for endpoint in ("start", "end"):
        report = result["endpoint_diagnostics"][endpoint]["population"]
        assert report["assessment"] == "assessed"
        assert report["population_source_ids"] == ["study"]
        assert report["population_unknown_cell_ids"] == []
        assert report["population_length_cost"] == 0
        assert (
            route_geojson(result)["metadata"]["endpoint_diagnostics"][endpoint]["population"]
            == report
        )


def test_automatic_nonconvergence_retains_population_diagnostics(monkeypatch):
    model = flight_fixtures.model.__wrapped__(flight_fixtures.scenario.__wrapped__())
    model, counts, run = flight_fixtures.automatic.__wrapped__(model, monkeypatch)
    monkeypatch.setattr(
        routing,
        "prepare_population_surface",
        lambda *a, **kw: surface(model.boundary, [(model.boundary, "study", 2)]),
    )
    original = routing.RegionalPlanner.check
    original_plan = routing.RegionalPlanner.plan
    identities = []

    def candidate(self, *args, **kwargs):
        self._flight_recheck = False
        result = original_plan(self, *args, **kwargs)
        identities.append(result["population_model"]["identity"])
        self._flight_recheck = True
        return result

    def block_completed(self, coordinates, mode):
        report = original(self, coordinates, mode)
        # Force only the automatic interval check, after independent route validation.
        if getattr(self, "_flight_recheck", False):
            self._flight_recheck = False
            report["state"] = "blocked"
        return report

    monkeypatch.setattr(routing.RegionalPlanner, "check", block_completed)
    monkeypatch.setattr(routing.RegionalPlanner, "plan", candidate)
    result = run(include_population=True, time_budget_s=3)
    assert result["status"] == "duration_unstable"
    assert len(identities) == 3 and len(set(identities)) == 1
    assert result["controls"]["include_population"]
    assert result["population_model"]["identity"]
    assert (
        result["population_length_cost"] is result["objective_cost"] is result["geometry"] is None
    )
    assert result["timing"]["estimated_arrival"] is None and counts["close"] == 1


def test_population_preparation_uses_deadline_even_on_warm_cache(tmp_path):
    directory, _ = population_fixtures.study(tmp_path)
    prepared = prepare_population_surface(directory)
    assert prepared.metric_cells
    with pytest.raises(PopulationResourceLimit, match="deadline"):
        prepare_population_surface(directory, deadline=perf_counter() - 1)
    with pytest.raises(PopulationResourceLimit, match="cancelled"):
        prepare_population_surface(directory, cancel=lambda: True)


def test_explicit_timeout_preserves_request_metadata_and_closes_sources(planner, monkeypatch):
    closed = []
    planner.constraints.terrain.close = lambda: closed.append(True)
    monkeypatch.setattr(routing, "RegionalPlanner", lambda *a, **kw: planner)

    def deadline():
        raise TimeoutError("Population routing request deadline reached.")

    monkeypatch.setattr(planner, "ensure_deadline", deadline)
    result = routing.plan_regional_route(
        "unused",
        planner.constraints.scenario,
        "a",
        "b",
        include_population=True,
        objective="distance",
        cell_m=50,
    )
    assert result["status"] == "resource_limit" and closed == [True]
    assert (
        result["controls"]["include_population"] and result["controls"]["objective"] == "distance"
    )
    assert result["population_length_cost"] is result["geometry"] is None
    assert route_geojson(result)["features"] == []


def test_cli_population_controls_match_core(planner, tmp_path, monkeypatch, capsys):
    from uas_planner.cli import main

    monkeypatch.setattr(routing, "RegionalPlanner", lambda *a, **kw: planner)
    scenario = tmp_path / "scenario.json"
    scenario.write_text(json.dumps(planner.constraints.scenario), encoding="utf-8")
    assert (
        main(
            [
                "study-route",
                "unused",
                "--scenario",
                str(scenario),
                "--start-id",
                "a",
                "--end-id",
                "b",
                "--cell-m",
                "50",
                "--objective",
                "distance",
                "--include-population",
                "--population-weight",
                ".5",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "success" and result["effective_weights"]["population"] == 0.5
    assert result["population_length_cost"] > 0
