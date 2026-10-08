"""Experiment assertions catch corrupted costs and misleading failure summaries."""

from copy import deepcopy

import pytest

from uas_planner.core.static_experiments import (
    independent_synthetic_check,
    planner_at_speed,
    run_matrix,
    summarize,
    synthetic_planner,
)

SCENARIO = {
    "agl_m": 100,
    "speed_m_s": 30,
    "scenario": "civil",
    "mission_start": "2026-10-07T10:00:00+02:00",
    "mission_end": "2026-10-07T10:15:00+02:00",
    "clearance_m": 0,
}


def test_analytic_checker_rejects_cost_and_endpoint_corruption():
    planner = synthetic_planner("risk-detour", SCENARIO)
    result = planner.plan("a", "b", cell_m=50, background_cost=0)
    assert independent_synthetic_check(planner, result)["state"] == "passed"
    for field in ("objective_cost", "risk_length_cost", "length_m", "cruise_time_s"):
        corrupt = deepcopy(result)
        corrupt[field] += 1
        assert independent_synthetic_check(planner, corrupt)["state"] == "failed"
    corrupt = deepcopy(result)
    corrupt["geometry"]["coordinates"][0] = corrupt["end"]
    assert independent_synthetic_check(planner, corrupt)["state"] == "failed"


def test_boundary_expansion_changes_feasibility_without_moving_endpoints():
    initial = synthetic_planner("boundary-detour", SCENARIO)
    expanded = synthetic_planner("boundary-detour", SCENARIO, expanded=True)
    before = initial.plan("a", "b", cell_m=50, objective="distance")
    after = expanded.plan("a", "b", cell_m=50, objective="distance")
    assert before["status"] == "no_path_on_grid"
    assert after["status"] == "success"
    assert before["start"] == after["start"] and before["end"] == after["end"]
    assert independent_synthetic_check(expanded, after)["state"] == "passed"


def test_speed_changes_only_estimates_for_deterministic_graph():
    results = [
        synthetic_planner("risk-detour", {**SCENARIO, "speed_m_s": speed}).plan(
            "a", "b", cell_m=50, background_cost=0
        )
        for speed in (25, 30, 35)
    ]
    for speed, result in zip((25, 30, 35), results, strict=True):
        assert result["geometry"] == results[0]["geometry"]
        assert result["objective_cost"] == pytest.approx(results[0]["objective_cost"])
        assert result["cruise_time_s"] == pytest.approx(result["length_m"] / speed)
    with pytest.raises(ValueError):
        synthetic_planner("risk-detour", {**SCENARIO, "speed_m_s": 36})


def test_failure_summary_has_no_successful_variation_or_graph_agreement():
    planner = synthetic_planner("boundary-detour", SCENARIO)
    records = run_matrix(
        planner, ("a", "b"), label="blocked", cache_state="fresh", source_ms=0, budget_s=0
    )
    summaries = summarize(records)
    assert len(records) == 10
    for item in summaries:
        assert item["graph_objective_agreement"] == "not_applicable"
        assert item["abitstar"]["attempts"] == 3
        assert item["abitstar"]["success_rate"] == 0
        assert item["abitstar"]["successful_run_variation"]["length_m"] is None
    assert all(r["experiment_validation"]["state"] == "not_applicable" for r in records)


def test_summary_rejects_graph_disagreement():
    planner = synthetic_planner("risk-detour", SCENARIO)
    a = planner.plan("a", "b", cell_m=50, background_cost=0)
    d = planner.plan("a", "b", cell_m=50, background_cost=0, algorithm="dijkstra")
    d["objective_cost"] += 1
    records = [
        {"label": "bad", "pair": ["a", "b"], "cache_state": "fresh", "result": r} for r in (a, d)
    ]
    with pytest.raises(AssertionError, match="disagree"):
        summarize(records)


def test_speed_sweep_preserves_previous_records_and_signs_changed_metadata():
    original = synthetic_planner("risk-detour", SCENARIO)
    original_signature = original.constraints.provenance["model_signature"]
    changed = planner_at_speed(original, 35)
    assert original.constraints.scenario["speed_m_s"] == 30
    assert original.constraints.provenance["model_signature"] == original_signature
    assert changed.constraints.provenance["model_signature"] != original_signature
    assert changed.constraints.provenance["scenario"]["speed_m_s"] == 35
    assert changed.constraints.boundary is original.constraints.boundary
