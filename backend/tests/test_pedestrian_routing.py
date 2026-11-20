import pytest
from pyproj import Transformer
from shapely.geometry import box, mapping
from shapely.ops import transform

from uas_planner.acquisition.pedestrian import product_path, write_product
from uas_planner.core.experiment import checksum
from uas_planner.core.mid_profiles import departure_window
from uas_planner.core.pedestrian_exposure import MODEL_VERSION
from uas_planner.core.pedestrian_routing import EXPOSURE_FIELD, PedestrianRouteCost
from uas_planner.core.routing import search_graph


@pytest.mark.parametrize(
    ("timestamp", "expected"),
    [
        ("2026-10-07T07:59:59+02:00", "05-08"),
        ("2026-10-07T08:00:00+02:00", "08-10"),
        ("2026-10-07T22:00:00+02:00", "22-05"),
        ("2026-10-08T00:00:00+02:00", "22-05"),
        ("2026-10-08T05:00:00+02:00", "05-08"),
        ("2026-10-25T02:30:00+02:00", "22-05"),
        ("2026-10-25T02:30:00+01:00", "22-05"),
    ],
)
def test_half_open_berlin_departure_windows(timestamp, expected):
    assert departure_window(timestamp) == expected


def test_astar_trade_off_and_independent_coverage(tmp_path):
    directory = tmp_path / "study"
    directory.mkdir()
    study = directory / "study.json"
    study.write_text("{}", encoding="utf-8")
    to_geo = Transformer.from_crs(25832, 4326, always_xy=True).transform
    x, y = 550000, 5800000
    busy = box(x + 100, y - 25, x + 200, y + 25)
    boundary = box(x - 100, y - 100, x + 400, y + 200)
    polygons = [busy, boundary.difference(busy)]
    write_product(
        product_path(directory),
        {
            "version": MODEL_VERSION,
            "study_sha256": checksum(study),
            "input_kind": "mid-public",
            "display_max_people": 2.5,
            "cells": [
                {"id": str(i), "area_m2": p.area, "geometry": mapping(transform(to_geo, p))}
                for i, p in enumerate(polygons)
            ],
            "windows": {
                "08-10": {"mean_people": [0.005, 0]},
                "13-16": {"mean_people": [2.5, 0]},
                "22-05": {"mean_people": [None, 0]},
            },
        },
    )
    positions = {"start": (x, y), "end": (x + 300, y), "detour": (x + 150, y + 125)}
    geographic = {key: to_geo(*point) for key, point in positions.items()}
    paths = []
    for window in ("08-10", "13-16", "22-05"):
        model = PedestrianRouteCost(directory, window, 0)
        edges = []
        for a, b in (("start", "end"), ("start", "detour"), ("detour", "end")):
            score = model.evaluate([geographic[a], geographic[b]])
            if score["assessment"] == "assessed":
                edges.append((a, b, score["length_m"], score["objective_cost"]))
        selected = search_graph(
            positions, edges, "start", "end", objective="risk", distance_weight=1
        )
        assert selected["status"] == "success"
        paths.append(selected["nodes"])
        checked = model.independently_score([geographic[n] for n in selected["nodes"]])
        assert checked["objective_cost"] == pytest.approx(selected["objective_cost"])
        assert checked[EXPOSURE_FIELD] == pytest.approx(
            selected["objective_cost"] - selected["length_m"]
        )
    assert paths == [["start", "end"], ["start", "detour", "end"], ["start", "detour", "end"]]
    assert model.evaluate([to_geo(x + 150, y)])["unavailable_cell_ids"] == ["0"]
    assert model.independently_score([geographic["start"], geographic["end"]]) is None
    assert model.evaluate([geographic["start"], to_geo(x - 120, y)])["objective_cost"] is None
