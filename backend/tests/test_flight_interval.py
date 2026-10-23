"""Automatic arrival is checked against actual complete-flight restrictions."""

from copy import deepcopy
from datetime import datetime
from importlib.util import find_spec

import pytest
import test_restrictions as restriction_fixtures
from fastapi.testclient import TestClient
from shapely.strtree import STRtree
from test_restrictions import assessment

from uas_planner.api.app import create_app
from uas_planner.core import flight_interval as flight
from uas_planner.core import regional
from uas_planner.core import regional_routing as routing
from uas_planner.core.regional import validate_scenario
from uas_planner.core.risk import signature
from uas_planner.core.routing import route_geojson


@pytest.fixture
def scenario():
    return restriction_fixtures.scenario.__wrapped__()


@pytest.fixture
def model(scenario):
    return restriction_fixtures.model.__wrapped__(scenario)


@pytest.fixture
def automatic(model, monkeypatch):
    model.manifest["config"]["bounds"] = {"west": 9, "south": 52, "east": 10, "north": 53}
    model.manifest["sources"] = {"dipul": {"responses": []}}
    counts = {"prepare": 0, "close": 0}
    model.terrain.close = lambda: counts.update(close=counts["close"] + 1)

    def prepare(directory, scenario, **kwargs):
        counts["prepare"] += 1
        model.scenario = validate_scenario(deepcopy(scenario))
        model.provenance["scenario"] = model.scenario
        return model

    monkeypatch.setattr(routing, "RegionalConstraints", prepare)
    monkeypatch.setattr(regional, "RegionalConstraints", prepare)
    monkeypatch.setattr(
        flight,
        "provisional_scenario",
        lambda directory, scenario, a, b, **kw: flight.seed_interval(
            scenario, model.manifest["config"]["locations"], a, b, **kw
        ),
    )

    def run(**overrides):
        scenario = deepcopy(model.scenario)
        scenario.pop("mission_end")
        return routing.plan_regional_route(
            "unused",
            scenario,
            "a",
            overrides.pop("end_id", "b"),
            duration_mode="automatic",
            objective="distance",
            planning_mode=overrides.pop("planning_mode", "conservative"),
            cell_m=50,
            **overrides,
        )

    return model, counts, run


@pytest.mark.parametrize(
    "start,seconds,end",
    [
        ("2026-10-07T10:00:00+02:00", 3600 / 30, "2026-10-07T10:02:00+02:00"),
        ("2026-10-07T23:59:59+02:00", 2.25, "2026-10-08T00:00:01.250000+02:00"),
        ("2026-03-29T01:59:59+01:00", 2, "2026-03-29T03:00:01+02:00"),
        ("2026-10-25T01:59:59+02:00", 3602, "2026-10-25T02:00:01+01:00"),
        ("2026-10-07T10:00:00+02:00", 1 / 30, "2026-10-07T10:00:00.033334+02:00"),
    ],
)
def test_elapsed_utc_time_fractional_midnight_and_dst(start, seconds, end):
    assert flight.timestamp_after({"mission_start": start}, seconds) == end


def test_actual_detour_expands_interval_without_reloading_or_second_search(automatic):
    model, counts, run = automatic
    result = run()
    assert result["status"] == "success" and result["independent_validation"]
    timing = result["timing"]
    assert result["length_m"] > 350
    assert timing["cruise_time_s"] == pytest.approx(result["length_m"] / 30)
    assert datetime.fromisoformat(timing["estimated_arrival"]) > datetime.fromisoformat(
        timing["provisional_interval"]["mission_end"]
    )
    assert timing["estimated_arrival"] == result["mission"]["mission_end"]
    assert timing["assessed_interval"] == result["restriction_report"]["assessed_interval"]
    assert (
        timing["assessed_interval"]["mission_end"]
        == result["provenance"]["scenario"]["mission_end"]
    )
    assert len(timing["passes"]) == 1 and counts == {"prepare": 1, "close": 1}
    assert route_geojson(result)["metadata"]["timing"] == timing
    assert result["prepared_identity"] == signature(
        {
            "provenance": result["provenance"],
            "controls": result["controls"],
            "endpoints": {key: result[key] for key in ("start", "end")},
        }
    )


def test_notice_activating_during_detour_rejects_candidate(automatic):
    model, counts, run = automatic
    notice = deepcopy(model.records[0])
    notice.update(
        source="notice/soon",
        geometry=model.boundary,
        reviewed_notice=True,
        notice_state="prohibited",
        evidence="Synthetic reviewed notice",
    )
    notice["properties"].update(
        valid_from="2026-10-07T10:00:12+02:00", valid_until="2026-10-07T11:00:00+02:00"
    )
    model.records.append(notice)
    model.tree = STRtree([r["geometry"] for r in model.records])
    result = run()
    assert result["status"] != "success"
    assert result["timing"]["passes"][0]["complete_interval_state"] == "blocked"
    assert result["geometry"] is result["timing"]["estimated_arrival"] is None
    assert counts == {"prepare": 1, "close": 1}


def test_evidence_expiring_during_flight_cannot_retain_permission(automatic):
    model, counts, run = automatic
    zone = model.records[0]
    obstacle = {
        **deepcopy(zone),
        "source": "way/999",
        "category": "building_obstacle",
        "state": "blocked",
        "height_m": 150,
    }
    zone["geometry"] = model.boundary
    consent = assessment()
    consent["valid_until"] = "2026-10-07T10:00:12+02:00"
    model.scenario["zone_assessments"] = {zone["source"]: consent}
    model.records.append(obstacle)
    model.tree = STRtree([r["geometry"] for r in model.records])
    result = run()
    assert result["status"] != "success"
    assert result["timing"]["passes"][0]["complete_interval_state"] == "blocked"
    assert result["length_m"] is result["cruise_time_s"] is None
    assert counts["close"] == 1


def test_zero_length_is_instantaneous_but_endpoint_is_checked(automatic):
    model, _, run = automatic
    result = run(end_id="a")
    assert result["status"] == "success" and result["length_m"] == 0
    timing = result["timing"]
    assert timing["estimated_arrival"] == timing["departure"]
    assert timing["cruise_time_s"] == 0 and "one-microsecond" in timing["zero_duration_rule"]
    assert datetime.fromisoformat(
        timing["assessed_interval"]["mission_end"]
    ) > datetime.fromisoformat(timing["departure"])
    model.records[0]["geometry"] = model.boundary
    model.tree = STRtree([model.boundary])
    assert run(end_id="a")["status"] == "invalid_endpoint"


@pytest.mark.parametrize(
    "algorithm",
    [
        "astar",
        "dijkstra",
        pytest.param(
            "abitstar",
            marks=pytest.mark.skipif(find_spec("ompl") is None, reason="Optional OMPL absent"),
        ),
    ],
)
def test_automatic_native_and_graph_compatibility(automatic, algorithm):
    _, _, run = automatic
    result = run(algorithm=algorithm, time_budget_s=1, planning_mode="research")
    if algorithm == "abitstar" and result["status"] == "timeout":
        assert result["geometry"] is result["timing"]["estimated_arrival"] is None
        return
    assert result["status"] == "success"
    assert result["timing"]["cruise_time_s"] == pytest.approx(result["length_m"] / 30)


def test_bounded_nonconvergence_and_one_shared_search_budget(automatic, monkeypatch):
    model, _, run = automatic
    budgets = []

    def candidate(self, a, b, **controls):
        budgets.append(controls["time_budget_s"])
        return {
            "status": "success",
            "length_m": 1000 * len(budgets),
            "planner_ms": 200,
            "preparation_ms": 0,
            "geometry": {"coordinates": [[9, 52], [9.01, 52]]},
        }

    monkeypatch.setattr(routing.RegionalPlanner, "plan", candidate)
    monkeypatch.setattr(routing.RegionalPlanner, "check", lambda *a, **kw: {"state": "blocked"})
    result = run(time_budget_s=1)
    assert result["status"] == "duration_unstable" and len(budgets) == 3
    assert budgets == pytest.approx([1, 0.8, 0.6])
    assert result["geometry"] is result["timing"]["estimated_arrival"] is None


def test_shared_request_deadline_releases_terrain(automatic, monkeypatch):
    _, counts, run = automatic
    monkeypatch.setattr(flight, "REQUEST_SECONDS", 0)
    result = run()
    assert result["status"] == "duration_resource_limit"
    assert result["timing"]["estimated_arrival"] is None
    assert counts["close"] == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"speed_m_s": 0},
        {"speed_m_s": -30},
        {"speed_m_s": 36},
        {"speed_m_s": True},
        {"mission_start": "2026-03-29T02:30:00+01:00"},
        {"mission_start": "2026-10-07T10:00:00"},
    ],
)
def test_invalid_automatic_inputs_are_rejected(automatic, changes):
    model, _, run = automatic
    model.scenario.update(changes)
    with pytest.raises(ValueError):
        run()


def test_auto_api_and_explicit_compatibility(automatic, tmp_path):
    model, _, _ = automatic
    (tmp_path / "case").mkdir()
    explicit = deepcopy(model.scenario)
    scenario = {k: v for k, v in explicit.items() if k != "mission_end"}
    request = {
        "scenario": scenario,
        "duration_mode": "automatic",
        "start_id": "a",
        "end_id": "b",
        "objective": "distance",
        "planning_mode": "conservative",
        "cell_m": 50,
    }
    with TestClient(create_app(tmp_path)) as client:
        endpoint = "/api/datasets/case/study/route"
        response = client.post(endpoint, json=request)
        assert response.status_code == 200 and response.json()["status"] == "success"
        exported = client.post(endpoint, json={**request, "export": True}).json()
        assert (
            exported["metadata"]["timing"]["estimated_arrival"]
            == response.json()["timing"]["estimated_arrival"]
        )
        assert client.post(endpoint, json={**request, "scenario": explicit}).status_code == 422
        old = client.post(
            endpoint, json={**request, "duration_mode": "explicit", "scenario": explicit}
        )
        assert (
            old.status_code == 200
            and old.json()["mission"]["mission_end"] == explicit["mission_end"]
        )


def test_automatic_preview_is_provisional_and_matches_verified_interval(automatic, tmp_path):
    model, counts, _ = automatic
    (tmp_path / "case").mkdir()
    departure = {k: v for k, v in model.scenario.items() if k != "mission_end"}
    with TestClient(create_app(tmp_path)) as client:
        response = client.post(
            "/api/datasets/case/study/layers/constraints",
            json={
                "duration_mode": "automatic",
                "scenario": departure,
                "start_id": "a",
                "end_id": "b",
                "planning_mode": "conservative",
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert result["flight_interval"]["mode"] == "provisional"
        assert "not a successful route ETA" in result["flight_interval"]["interpretation"]
        assert (
            result["flight_interval"]["assessed_interval"]["mission_end"]
            == result["provenance"]["scenario"]["mission_end"]
        )
        assert counts == {"prepare": 1, "close": 1}
