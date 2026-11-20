from math import fsum

import networkx as nx
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import Point, box, mapping

from uas_planner.acquisition.pedestrian import product_path, write_product
from uas_planner.api.app import create_app
from uas_planner.core.experiment import checksum
from uas_planner.core.mid_profiles import (
    DURATION_BINS,
    WINDOWS,
    expected_minutes,
    mean_interval_overlap,
    window_metadata,
)
from uas_planner.core.pedestrian_exposure import DISTANCE_DECAY_M, MODEL_VERSION, allocate


def test_public_timing_partitions_a_day_and_credits_window_overlap():
    base = expected_minutes()
    assert sum(window_metadata(key)["minutes"] for key in WINDOWS) == 1440
    assert tuple(base) == tuple(WINDOWS)
    assert window_metadata("22-05")["overnight"] is True
    assert mean_interval_overlap(0, 60, 30, 60, 90) == pytest.approx(7.5)
    assert mean_interval_overlap(22 * 60, 24 * 60, 60, 24 * 60, 25 * 60) == pytest.approx(15)
    assert fsum(base.values()) == pytest.approx(
        fsum(((lo + hi) / 2 if hi is not None else 90) * p / 100 for lo, hi, p in DURATION_BINS)
    )
    assert fsum(expected_minutes(120).values()) - fsum(
        expected_minutes(60).values()
    ) == pytest.approx(60 * DURATION_BINS[-1][2] / 100)


def test_spatial_allocation_reconciles_outdoor_covered_outside_and_unavailable():
    cells = [
        (box(0, -10, 50, 10), "origin", 50),
        (box(50, -10, 75, 10), "outdoor", 0),
        (box(75, -10, 100, 10), "unknown", None),
        (box(300, -10, 350, 10), "unconnected", 10),
    ]
    graph = nx.Graph()
    for start in (25, 50, 75, 100):
        graph.add_edge(
            (start, 0, "0"),
            (start + 25, 0, "0"),
            length=25,
            shelter="covered" if start == 25 else "outdoor",
        )
    placements, unavailable, diagnostics = allocate(
        cells, [60, 0, 0, 10], graph, [(Point(125, 0), ("work",))]
    )
    values, ledger = placements[DISTANCE_DECAY_M]
    assert values == [0, 15, None, None]
    assert unavailable == {2: "ghsl_coverage", 3: "no_mapped_connection"}
    assert diagnostics["unresolved_origin_daily_departures"] == {"no_mapped_connection": 10}
    assert ledger == pytest.approx(
        {
            "budget": 70,
            "outdoor_in_region": 15,
            "covered": 15,
            "unallocated": 25,
            "outside_region": 15,
        }
    )


def test_precomputed_api_uses_common_scale_and_reports_stale_or_missing_product(tmp_path):
    study = tmp_path / "hannover"
    study.mkdir()
    manifest = study / "study.json"
    manifest.write_text("{}", encoding="utf-8")
    client = TestClient(create_app(tmp_path))
    endpoint = "/api/datasets/hannover/study/pedestrian-exposure"
    assert client.get(endpoint, params={"scenario": "other"}).status_code == 422
    assert client.get(endpoint, params={"scenario": "08-10"}).json()["state"] == "unavailable"
    product = {
        "version": MODEL_VERSION,
        "input_kind": "mid-public",
        "study_sha256": checksum(manifest),
        "display_max_people": 6,
        "cells": [
            {
                "id": str(i),
                "area_m2": 22_500,
                "geometry": mapping(box(0, 0, 1, 1)),
                "coverage_reason": "ghsl_coverage" if i == 2 else None,
            }
            for i in range(3)
        ],
        "windows": {
            "08-10": {"mean_people": [0, 3, None]},
            "22-05": {"mean_people": [0, 6, None]},
        },
    }
    write_product(product_path(study), product)
    morning = client.get(endpoint, params={"scenario": "08-10"}).json()
    night = client.get(endpoint, params={"scenario": "22-05"}).json()
    assert morning["input_kind"] == "mid-public"
    assert morning["display_max_people"] == night["display_max_people"] == 6
    cells = [feature["properties"] for feature in morning["layer"]["features"]]
    assert [(cell["state"], cell["mean_people"]) for cell in cells] == [
        ("known", 0),
        ("known", 3),
        ("unavailable", None),
    ]
    assert cells[1]["people_per_km2"] == pytest.approx(3 / 0.0225)
    assert cells[2]["coverage_reason"] == "ghsl_coverage"
    manifest.write_text('{"different":true}', encoding="utf-8")
    assert client.get(endpoint, params={"scenario": "08-10"}).json()["state"] == "unavailable"
