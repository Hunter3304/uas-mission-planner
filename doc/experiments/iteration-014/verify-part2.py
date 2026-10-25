"""Offline real Hannover population routing acceptance; no services or acquisition."""

import argparse
import json
from itertools import pairwise
from math import isclose
from pathlib import Path
from time import perf_counter

from pyproj import Transformer
from shapely.geometry import LineString
from shapely.ops import transform, unary_union
from uas_planner.core.experiment import checksum
from uas_planner.core.population_costs import prepare_population_surface
from uas_planner.core.regional_routing import plan_regional_route
from uas_planner.core.routing import route_geojson

ROOT = Path(__file__).resolve().parents[3]


def raw_population_cost(geometry, cells):
    """Re-score exported geometry using unbuffered metric population footprints."""
    forward = Transformer.from_crs(4326, 25832, always_xy=True).transform
    total = 0.0
    for a, b in pairwise(geometry["coordinates"]):
        line = transform(forward, LineString([a, b]))
        selected = [(g, s) for g, _, s in cells if g.intersects(line)]
        for score in range(4, -1, -1):
            region = unary_union([g for g, s in selected if s == score])
            total += line.intersection(region).length * score
            line = line.difference(region)
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    data = ROOT / "data/hannover-part1-v4"
    original = {
        name: checksum(data / name)
        for name in ("population.tif", "study.json", "osm/features.gpkg")
    }
    scenario = {
        "agl_m": 100,
        "speed_m_s": 30,
        "clearance_m": 0,
        "vertical_clearance_m": 0,
        "mission_start": "2026-10-07T10:00:00+02:00",
        "scenario": "civil",
        "timezone": "Europe/Berlin",
        "building_unknown_height": "unresolved",
        "zone_assessments": {},
        "research_geometry": "derived",
        "research_height_m": 30,
        "research_geometry_buffer_m": 20,
        "vertical_reference_policy": "nhn_as_msl_assumption",
        "nhn_msl_offset_m": 0,
        "nhn_msl_uncertainty_m": 0,
    }
    options = {
        "duration_mode": "automatic",
        "terrain_directory": ROOT / "data/hannover-part2-terrain-v1",
        "algorithm": "astar",
        "objective": "risk",
        "planning_mode": "research",
        "cell_m": 250,
        "time_budget_s": 20,
        "corridor_margin_m": 1000,
        "risk_weight": 0.9,
        "distance_weight": 0.1,
        "background_cost": 0,
        "start_coordinate": [9.7967855, 52.4044919],
        "end_coordinate": [9.8044306, 52.3834796],
    }
    results = {}
    for label, extra in [
        ("baseline", {}),
        ("population-risk", {"include_population": True, "population_weight": 1}),
        (
            "population-distance",
            {
                "include_population": True,
                "objective": "distance",
                "population_weight": 1,
            },
        ),
    ]:
        start = perf_counter()
        result = plan_regional_route(
            data, scenario, "rheuma-podbi", "mhh", **{**options, **extra}
        )
        elapsed = perf_counter() - start
        results[label] = result
        (args.output / f"{label}.geojson").write_text(
            json.dumps(route_geojson(result), allow_nan=False), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "run": label,
                    "seconds": elapsed,
                    "status": result["status"],
                    "length_m": result["length_m"],
                    "population_length_cost": result.get("population_length_cost"),
                    "objective_cost": result["objective_cost"],
                }
            ),
            flush=True,
        )
        assert result["status"] == "success", result.get("message")
        if extra:
            assert result["population_active"] and result["independent_validation"]
            assert (
                result["population_model"]["identity"]
                == prepare_population_surface(data).metadata["identity"]
            )
            assert result["provenance"]["ghsl_routing_cost"]
            assert (
                result["timing"]["estimated_arrival"]
                == result["mission"]["mission_end"]
            )
            assert result["population_length_cost"] > 0
            expected = (
                0.9 * result["risk_length_cost"] + 0.1 * result["length_m"]
                if result["objective"] == "risk"
                else result["length_m"]
            ) + result["population_length_cost"]
            assert isclose(result["objective_cost"], expected, rel_tol=1e-8)
            # Independent unbuffered native metric footprints; partition by max class.
            cells = prepare_population_surface(data).metric_cells
            independent = raw_population_cost(result["geometry"], cells)
            assert isclose(
                independent,
                result["population_length_cost"],
                rel_tol=1e-7,
                abs_tol=1e-4,
            )
            result["independent_unbuffered_population_cost"] = independent
    assert results["baseline"]["population_length_cost"] is None
    baseline_population = raw_population_cost(
        results["baseline"]["geometry"], prepare_population_surface(data).metric_cells
    )
    baseline_combined = results["baseline"]["objective_cost"] + baseline_population
    assert results["population-risk"]["objective_cost"] <= baseline_combined + 1e-4
    assert (
        results["population-risk"]["population_model"]["identity"]
        == results["population-distance"]["population_model"]["identity"]
    )
    assert original == {name: checksum(data / name) for name in original}
    summary = {
        "passed": True,
        "baseline_rescored_population_cost": baseline_population,
        "baseline_rescored_combined_objective": baseline_combined,
        "original_hashes": original,
        "population_identity": results["population-risk"]["population_model"][
            "identity"
        ],
        "runs": {
            name: {
                k: r.get(k)
                for k in (
                    "status",
                    "length_m",
                    "risk_length_cost",
                    "population_length_cost",
                    "objective_cost",
                    "runtime_ms",
                    "source_preparation_ms",
                    "preparation_ms",
                    "planner_ms",
                    "independent_unbuffered_population_cost",
                )
            }
            for name, r in results.items()
        },
        "risk_route_changed": results["baseline"]["geometry"]
        != results["population-risk"]["geometry"],
    }
    (args.output / "acceptance.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8"
    )
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
