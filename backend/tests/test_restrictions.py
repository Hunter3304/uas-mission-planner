"""Evidence expiration, full-motion avoidance and independent path intersections."""

import json
from copy import deepcopy
from importlib.util import find_spec
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pyproj import Transformer
from shapely.geometry import LineString, box, mapping
from shapely.ops import transform
from shapely.strtree import STRtree

from uas_planner.api.app import create_app
from uas_planner.core.regional import (
    RegionalConstraints,
    assessed_zone,
    constraint_layers,
    vertical_state,
)
from uas_planner.core.regional_routing import RegionalPlanner
from uas_planner.core.restrictions import (
    coverage_report,
    decision,
    load_profile,
    save_profile,
    validate_profile,
)


@pytest.fixture
def scenario():
    return {
        "agl_m": 100,
        "speed_m_s": 30,
        "scenario": "civil",
        "clearance_m": 0,
        "mission_start": "2026-10-07T10:00:00+02:00",
        "mission_end": "2026-10-07T10:15:00+02:00",
    }


def record():
    return {
        "source": "dipul:test/1",
        "source_signature": "original",
        "layer": "dipul:test",
        "properties": {
            "lower_limit_altitude": 0,
            "lower_limit_unit": "m",
            "lower_limit_alt_ref": "AGL",
        },
    }


def assessment(state="conditional_allowed"):
    return {
        "state": state,
        "source_signature": "original",
        "evidence": "Synthetic fixture consent",
        "conditions_satisfied": ["synthetic condition"],
        "scenario": "civil",
        "phase": "transit",
        "valid_from": "2026-10-07T09:00:00+02:00",
        "valid_until": "2026-10-07T11:00:00+02:00",
        "agl_interval_m": [100, 120],
    }


def evaluate(item, scenario):
    return decision(item, scenario, {"status": "unknown"}, vertical_state, assessed_zone)


def test_assessments_expire_change_source_and_do_not_grant_transit(scenario):
    item = record()
    scenario["zone_assessments"] = {item["source"]: assessment()}
    assert evaluate(item, scenario)["state"] == "conditional_allowed"
    scope = scenario["zone_assessments"][item["source"]]
    scope["valid_until"] = "2026-10-07T10:05:00+02:00"
    assert evaluate(item, scenario)["state"] == "unresolved"
    scope["state"] = "prohibited"
    assert evaluate(item, scenario)["state"] == "prohibited"
    scope["source_signature"] = "changed"
    assert evaluate(item, scenario)["state"] == "unresolved"
    scope.update(assessment(), phase="launch")
    assert "transit" in evaluate(item, scenario)["reason"]
    scope.update(assessment(), scenario="BOS")
    assert evaluate(item, scenario)["state"] == "unresolved"
    scope.update(assessment(), agl_interval_m=[110, 120])
    assert evaluate(item, scenario)["state"] == "unresolved"


def test_reviewed_notice_time_height_boundaries_and_unsupported_schedule(scenario):
    item = {
        **record(),
        "reviewed_notice": True,
        "notice_state": "prohibited",
        "evidence": "Fixture notice",
    }
    props = item["properties"]
    props.update(
        valid_from="2026-10-07T08:00:00Z",
        valid_until="2026-10-07T09:00:00Z",
        upper_limit_altitude=100,
        upper_limit_unit="m",
        upper_limit_alt_ref="AGL",
    )
    assert evaluate(item, scenario)["state"] == "prohibited"  # height equality overlaps
    scenario["agl_m"] = 120
    assert evaluate(item, scenario)["state"] == "not_applicable"
    scenario["agl_m"] = 100
    props["upper_limit_alt_ref"] = "MSL"
    assert evaluate(item, scenario)["state"] == "unresolved"
    props["upper_limit_alt_ref"] = "AGL"
    props["schedule"] = "unsupported daily schedule"
    assert evaluate(item, scenario)["state"] == "unresolved"
    props.pop("schedule")
    props["lower_limit_altitude"] = 150
    assert evaluate(item, scenario)["state"] == "unresolved"  # inverted limits cannot prohibit
    props["lower_limit_altitude"] = 0
    props["valid_from"] = "2026-10-07T07:00:00Z"
    props["valid_until"] = scenario["mission_start"]
    assert evaluate(item, scenario)["state"] == "not_applicable"  # interval ends at departure


@pytest.mark.parametrize("allowance_kind", ["valid", "expired", "changed_source", "launch_only"])
def test_active_notice_prohibition_cannot_be_downgraded_by_an_allowance(scenario, allowance_kind):
    item = {
        **record(),
        "reviewed_notice": True,
        "notice_state": "prohibited",
        "evidence": "Fixture active notice",
    }
    item["properties"].update(valid_from="2026-10-07T08:00:00Z", valid_until="2026-10-07T09:00:00Z")
    allowance = assessment()
    if allowance_kind == "expired":
        allowance["valid_until"] = "2026-10-07T09:30:00+02:00"
    elif allowance_kind == "changed_source":
        allowance["source_signature"] = "old"
    elif allowance_kind == "launch_only":
        allowance["phase"] = "launch"
    scenario["zone_assessments"] = {item["source"]: allowance}
    assert evaluate(item, scenario)["state"] == "prohibited"


def test_profiles_are_immutable_and_integrity_checked(tmp_path):
    profile = {
        "schema_version": 1,
        "name": "Fixture",
        "zone_assessments": {"dipul:test/1": assessment()},
        "notices": [],
    }
    first = save_profile(tmp_path, profile)
    second = save_profile(tmp_path, profile)
    assert first["id"] != second["id"]
    assert load_profile(tmp_path, first["id"])["name"] == "Fixture"
    revision = save_profile(tmp_path, first)
    assert load_profile(tmp_path, revision["id"])["name"] == "Fixture"
    path = tmp_path / "restriction-profiles" / f"{first['id']}.json"
    changed = json.loads(path.read_text())
    changed["name"] = "changed"
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="integrity"):
        load_profile(tmp_path, first["id"])
    with pytest.raises(ValueError):
        load_profile(tmp_path, "../../outside")
    bad = deepcopy(profile)
    bad["zone_assessments"]["dipul:test/1"]["agl_interval_m"] = [float("nan"), 120]
    with pytest.raises(ValueError):
        validate_profile(bad)


def test_profile_api_revisions_and_validation(tmp_path):
    (tmp_path / "case").mkdir()
    with TestClient(create_app(tmp_path)) as client:
        endpoint = "/api/datasets/case/study/restriction-profiles"
        response = client.post(
            endpoint,
            json={"schema_version": 1, "name": "Fixture", "zone_assessments": {}, "notices": []},
        )
        assert response.status_code == 201
        assert client.get(endpoint).json()["profiles"][0]["id"] == response.json()["id"]
        assert (
            client.post(
                endpoint,
                json={
                    "schema_version": 1,
                    "name": "Missing evidence",
                    "zone_assessments": {"a": {}},
                    "notices": [],
                },
            ).status_code
            == 422
        )


def test_empty_temporary_response_and_source_age_never_certify_completeness(scenario):
    manifest = {
        "config": {"bounds": {"west": 9, "south": 52, "east": 10, "north": 53}},
        "sources": {
            "dipul": {
                "responses": [
                    {"type_name": "dipul:temporaere_betriebseinschraenkungen", "feature_count": 0}
                ]
            }
        },
        "files": [{"path": "raw/dipul-test.geojson", "retrieved_at_utc": "2026-09-01T00:00:00Z"}],
    }
    report = coverage_report(manifest, [], scenario)
    assert report["temporary_layer_acquired"] and report["temporary_features"] == 0
    assert report["status"] == report["notam_completeness"] == "unverified"
    assert report["source_freshness"] == "stale"


def test_invalid_and_unreviewed_notices_are_rejected():
    notice = {
        "id": "fixture",
        "reviewed": True,
        "official_url": "https://www.dipul.de/fixture",
        "evidence": "Synthetic official notice fixture",
        "checked_at": "2026-10-07T08:00:00Z",
        "geometry": mapping(box(9, 52, 9.1, 52.1)),
        "state": "prohibited",
        "properties": {"valid_from": "2026-10-07T08:00:00Z", "valid_until": "2026-10-07T09:00:00Z"},
    }
    profile = {"schema_version": 1, "name": "Fixture", "zone_assessments": {}, "notices": [notice]}
    validate_profile(profile)
    notice["reviewed"] = False
    with pytest.raises(ValueError, match="review"):
        validate_profile(profile)
    notice["reviewed"] = True
    notice["official_url"] = "https://example.com/unofficial"
    with pytest.raises(ValueError, match="official"):
        validate_profile(profile)


def test_official_acquisition_preserves_originals_and_requires_review(tmp_path, monkeypatch):
    from uas_planner.acquisition import restrictions
    from uas_planner.core.experiment import checksum

    class Store:
        def __init__(self, output, config):
            self.root = output
            self.config = config
            self.files = []
            (output / "raw").mkdir(parents=True)

        def fetch(self, name, url):
            path = self.root / "raw" / name
            path.write_bytes(b"Original notice bytes")
            self.files.append(
                {
                    "path": f"raw/{name}",
                    "retrieved_at_utc": "2026-10-07T08:00:00Z",
                    "sha256": checksum(path),
                }
            )
            return path

    def fetch(store, area):
        path = store.root / "raw/temp.geojson"
        path.write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "id": "temp.1",
                            "geometry": mapping(box(9, 52, 9.01, 52.01)),
                            "properties": {"raw_time": "unsupported"},
                        }
                    ],
                }
            )
        )
        store.files.append(
            {
                "path": "raw/temp.geojson",
                "retrieved_at_utc": "2026-10-07T08:00:00Z",
                "sha256": checksum(path),
            }
        )
        return {
            "responses": [
                {
                    "type_name": "dipul:temporaere_betriebseinschraenkungen",
                    "pages": ["raw/temp.geojson"],
                    "feature_count": 1,
                }
            ]
        }

    monkeypatch.setattr(restrictions, "PayloadStore", Store)
    monkeypatch.setattr(restrictions, "fetch_dipul", fetch)
    target = tmp_path / "snapshot"
    result = restrictions.acquire_restrictions(
        [9, 52, 9.1, 52.1], target, ["https://www.dipul.de/fixture"]
    )
    assert len(result["files"]) == 2
    template = json.loads((target / "profile-template.json").read_text())
    assert template["notices"][0]["properties"] == {"raw_time": "unsupported"}
    with pytest.raises(ValueError, match="evidence|review"):
        validate_profile(template)


@pytest.fixture
def model(scenario):
    model = RegionalConstraints.__new__(RegionalConstraints)
    model.scenario = scenario
    model.boundary = box(500000, 5800000, 500400, 5800400)
    model.terrain = SimpleNamespace(
        bounds=lambda _: {"status": "known"}, tiles=["fixture"], close=lambda: None
    )
    item = {
        **record(),
        "geometry": box(500175, 5800100, 500225, 5800300),
        "category": "conditional_zone",
        "state": "unresolved",
        "basis": "fixture",
        "buffer_m": 0,
        "buffer_basis": "fixture",
    }
    model.records = [item]
    model.tree = STRtree([item["geometry"]])
    model.diagnostics = []
    model.geometry_assumptions = []
    model.derived_obstacles = []
    model.derived_tree = STRtree([])
    model.research_risk_records = []
    model.risk_records = []
    model.risk_tree = STRtree([])
    model.provenance = {"synthetic": True, "model_signature": "fixture"}
    model.restriction_coverage = {
        "status": "unverified",
        "reason": "Synthetic coverage remains unverified",
    }
    reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform
    model.manifest = {
        "config": {
            "locations": [
                {"id": name, "longitude": reverse(x, y)[0], "latitude": reverse(x, y)[1]}
                for name, x, y in (("a", 500025, 5800225), ("b", 500375, 5800225))
            ]
        }
    }
    return model


def test_full_motion_and_map_policy_separate_from_prohibition(model):
    reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform
    path = [reverse(500025, 5800225), reverse(500375, 5800225)]
    assert model.check(path, mode="research")["state"] == "permitted"
    assert model.check(path, mode="strict")["state"] == "unresolved"
    assert model.check(path, mode="conservative")["state"] == "blocked"
    assert all(model.check([p], mode="conservative")["state"] == "permitted" for p in path)
    layers = constraint_layers(model, "conservative")
    assert layers["restriction_report"]["counts"]["prohibited"] == 0
    assert len(layers["excluded"]["features"]) == 1
    model.scenario["zone_assessments"] = {record()["source"]: assessment("prohibited")}
    assert model.check(path, mode="research")["state"] == "blocked"
    assert constraint_layers(model)["restriction_report"]["counts"]["prohibited"] == 1


def test_saved_profile_is_applied_to_real_api_routing_and_expires(model, tmp_path, monkeypatch):
    from uas_planner.core import regional_routing
    from uas_planner.core.regional import validate_scenario

    def prepared(directory, scenario, **kwargs):
        model.scenario = validate_scenario(deepcopy(scenario))
        return model

    monkeypatch.setattr(regional_routing, "RegionalConstraints", prepared)
    (tmp_path / "case").mkdir()
    request = {
        "scenario": deepcopy(model.scenario),
        "start_id": "a",
        "end_id": "b",
        "planning_mode": "conservative",
        "algorithm": "astar",
        "objective": "distance",
        "cell_m": 50,
    }
    with TestClient(create_app(tmp_path)) as client:
        endpoint = "/api/datasets/case/study/route"
        excluded = client.post(endpoint, json=request)
        assert excluded.status_code == 200 and excluded.json()["status"] == "success"
        assert excluded.json()["length_m"] > 350
        saved = client.post(
            "/api/datasets/case/study/restriction-profiles",
            json={
                "schema_version": 1,
                "name": "Synthetic transit consent",
                "notices": [],
                "zone_assessments": {record()["source"]: assessment()},
            },
        )
        assert saved.status_code == 201
        request["profile_id"] = saved.json()["id"]
        allowed = client.post(endpoint, json=request).json()
        assert allowed["status"] == "success"
        assert allowed["restriction_report"]["counts"]["conditional_allowed"] == 1
        assert allowed["length_m"] == pytest.approx(350)
        assert allowed["mission"]["restriction_profile"]["id"] == saved.json()["id"]
        forward = Transformer.from_crs(4326, 25832, always_xy=True).transform
        assert transform(forward, LineString(allowed["geometry"]["coordinates"])).intersects(
            model.records[0]["geometry"]
        )
        request["scenario"].update(
            mission_start="2026-10-07T11:30:00+02:00", mission_end="2026-10-07T11:45:00+02:00"
        )
        expired = client.post(endpoint, json=request).json()
        assert expired["restriction_report"]["counts"]["unresolved"] == 1
        assert expired["length_m"] > 350
        model.records[0]["source_signature"] = "new-source"
        request["scenario"].update(
            mission_start="2026-10-07T10:00:00+02:00", mission_end="2026-10-07T10:15:00+02:00"
        )
        changed = client.post(endpoint, json=request).json()
        assert changed["restriction_report"]["counts"]["unresolved"] == 1
        assert changed["length_m"] > 350
        request["scenario"]["zone_assessments"] = {record()["source"]: assessment()}
        assert client.post(endpoint, json=request).status_code == 422


@pytest.mark.parametrize(
    "ground,relation", [(40, "outside"), (55.7, "overlap"), (60, "overlap"), (700, "outside")]
)
def test_explicit_nhn_agl_comparison_uses_aircraft_height_and_keeps_source(
    scenario, ground, relation
):
    item = record()
    item["properties"].update(
        lower_limit_altitude=155.7,
        lower_limit_unit="m",
        lower_limit_alt_ref="MSL",
        upper_limit_altitude=762,
        upper_limit_unit="m",
        upper_limit_alt_ref="MSL",
    )
    terrain = {
        "status": "known",
        "minimum_m": ground,
        "maximum_m": ground,
        "vertical_datum": "DHHN2016_NHN",
    }
    scenario["vertical_reference_policy"] = "nhn_as_msl_assumption"
    result = decision(item, scenario, terrain, vertical_state, assessed_zone, mode="conservative")
    assert result["vertical_relation"] == relation
    assert result["aircraft_comparison_bounds_m"] == pytest.approx([ground + 100, ground + 100])
    assert result["state"] == ("not_applicable" if relation == "outside" else "unresolved")
    assert terrain["vertical_datum"] == "DHHN2016_NHN" and terrain["minimum_m"] == ground
    assert result["vertical_reference_assumption"]["offset_m"] == 0
    strict = decision(item, scenario, terrain, vertical_state, assessed_zone, mode="strict")
    assert strict["state"] == "unresolved" and "vertical_reference_assumption" not in strict
    scenario["vertical_reference_policy"] = "source"
    assert (
        decision(item, scenario, terrain, vertical_state, assessed_zone, mode="conservative")[
            "vertical_relation"
        ]
        == "unknown"
    )


def test_nhn_uncertainty_full_motion_and_unknown_support_are_not_bypassed(model):
    props = model.records[0]["properties"]
    props.update(
        lower_limit_altitude=155.7,
        lower_limit_unit="m",
        lower_limit_alt_ref="MSL",
        upper_limit_altitude=762,
        upper_limit_unit="m",
        upper_limit_alt_ref="MSL",
    )
    model.scenario["vertical_reference_policy"] = "nhn_as_msl_assumption"
    reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform
    points = [reverse(500190, 5800200), reverse(500210, 5800200)]
    model.terrain.bounds = lambda query: {
        "status": "known",
        "minimum_m": 50,
        "maximum_m": 50 if query.geom_type == "Point" else 70,
        "vertical_datum": "DHHN2016_NHN",
    }
    assert all(model.check([p], mode="conservative")["state"] == "permitted" for p in points)
    motion = model.check(points, mode="conservative")
    assert motion["state"] == "blocked"
    assert motion["zones"][0]["aircraft_comparison_bounds_m"] == [150, 170]
    assert any(a.get("policy") == "nhn_as_msl_assumption" for a in motion["assumptions"])
    model.scenario.update(nhn_msl_offset_m=3, nhn_msl_uncertainty_m=4)
    assert model.check([points[0]], mode="conservative")["zones"][0][
        "aircraft_comparison_bounds_m"
    ] == [149, 157]
    assert model.check([points[0]], mode="conservative")["state"] == "blocked"
    model.terrain.bounds = lambda query: {"status": "unknown", "reason": "NoData"}
    assert model.check(points, mode="research")["state"] == "unresolved"
    model.terrain.bounds = lambda query: {
        "status": "known",
        "minimum_m": 50,
        "maximum_m": 50,
        "vertical_datum": "unknown",
    }
    result = model.check(points, mode="conservative")
    assert result["state"] == "blocked" and "aircraft_comparison_bounds_m" not in result["zones"][0]


def test_reviewed_msl_notice_blocks_with_nhn_assumption(scenario):
    item = {
        **record(),
        "reviewed_notice": True,
        "notice_state": "prohibited",
        "evidence": "Fixture reviewed notice",
    }
    item["properties"].update(
        lower_limit_altitude=150,
        lower_limit_unit="m",
        lower_limit_alt_ref="MSL",
        upper_limit_altitude=200,
        upper_limit_unit="m",
        upper_limit_alt_ref="MSL",
        valid_from="2026-10-07T08:00:00Z",
        valid_until="2026-10-07T09:00:00Z",
    )
    scenario["vertical_reference_policy"] = "nhn_as_msl_assumption"
    terrain = {
        "status": "known",
        "minimum_m": 60,
        "maximum_m": 60,
        "vertical_datum": "DHHN2016_NHN",
    }
    result = decision(item, scenario, terrain, vertical_state, assessed_zone, mode="research")
    assert result["state"] == "prohibited"
    assert result["vertical_comparison_quality"] == "engineering_assumption"


@pytest.mark.parametrize(
    "field,value",
    [
        ("vertical_reference_policy", "automatic"),
        ("nhn_msl_offset_m", float("nan")),
        ("nhn_msl_offset_m", True),
        ("nhn_msl_uncertainty_m", -1),
    ],
)
def test_invalid_nhn_reference_controls_are_rejected(scenario, field, value):
    from uas_planner.core.regional import validate_scenario

    scenario[field] = value
    with pytest.raises(ValueError):
        validate_scenario(scenario)


@pytest.mark.parametrize("algorithm", ["astar", "dijkstra", "abitstar"])
def test_three_algorithms_avoid_zone_with_independent_geometry(model, monkeypatch, algorithm):
    if algorithm == "abitstar" and find_spec("ompl") is None:
        pytest.skip("Optional native OMPL unavailable")
    from uas_planner.core import regional_routing

    monkeypatch.setattr(regional_routing, "RegionalConstraints", lambda *a, **k: model)
    planner = RegionalPlanner("unused", model.scenario)
    result = planner.plan(
        "a",
        "b",
        planning_mode="conservative",
        objective="distance",
        algorithm=algorithm,
        cell_m=50,
        time_budget_s=3,
    )
    assert result["status"] == "success"
    forward = Transformer.from_crs(4326, 25832, always_xy=True).transform
    path = transform(forward, LineString(result["geometry"]["coordinates"]))
    assert not path.intersects(model.records[0]["geometry"])
    assert path.length > 350
    model.scenario["zone_assessments"] = {record()["source"]: assessment("prohibited")}
    model.records[0]["geometry"] = box(500175, 5799999, 500225, 5800401)
    model.tree = STRtree([model.records[0]["geometry"]])
    # Full-height wall prevents all routes; no planner may relax it to get success.
    failed = planner.plan(
        "a",
        "b",
        planning_mode="research",
        objective="distance",
        algorithm=algorithm,
        cell_m=50,
        time_budget_s=0.2,
    )
    assert failed["status"] != "success" and failed["geometry"] is None
