"""Retain real mode failures and independently check research paths, offline."""

import argparse
import importlib.util
import json
from pathlib import Path
from time import perf_counter

from uas_planner.core.experiment import checksum
from uas_planner.core.regional_routing import RegionalPlanner
from uas_planner.core.routing import route_geojson


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(
        "iteration009_independent",
        root / "doc/experiments/iteration-009/verify-real-routes.py",
    )
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    scenario = {
        "agl_m": 100,
        "speed_m_s": 30,
        "scenario": "civil",
        "timezone": "Europe/Berlin",
        "mission_start": "2026-10-07T10:00:00+02:00",
        "mission_end": "2026-10-07T10:15:00+02:00",
        "clearance_m": 0,
        "vertical_clearance_m": 0,
        "research_geometry": "derived",
        "research_height_m": 30,
        "research_geometry_buffer_m": 20,
        "zone_assessments": {},
    }
    started = perf_counter()
    planner = RegionalPlanner(
        root / "data/hannover-part1-v4",
        scenario,
        terrain_directory=root / "data/hannover-part2-terrain-v1",
    )
    source_seconds = perf_counter() - started
    cases = [
        (origin, "conservative", algorithm)
        for origin in ("rheuma-podbi", "amedes-georg", "limbach-lehrte")
        for algorithm in ("astar", "dijkstra", "abitstar")
    ]
    cases += [
        ("rheuma-podbi", mode, algorithm)
        for mode in ("strict", "research")
        for algorithm in ("astar", "dijkstra", "abitstar")
    ]
    runs = []
    try:
        for origin, mode, algorithm in cases:
            result = planner.plan(
                origin,
                "mhh",
                planning_mode=mode,
                algorithm=algorithm,
                objective="distance",
                cell_m=250,
                time_budget_s=3,
            )
            if mode == "conservative":
                assert (
                    result["status"] == "invalid_endpoint"
                    and result["geometry"] is None
                )
            elif mode == "strict":
                assert result["status"] != "success" and result["geometry"] is None
            else:
                if algorithm != "abitstar":
                    assert result["status"] == "success"
                result["external_validation"] = verifier.independent(planner, result)
                if result["status"] == "success":
                    assert result["external_validation"]["accepted"]
            filename = f"{origin}-{mode}-{algorithm}.geojson"
            target = args.output / filename
            target.write_text(
                json.dumps(route_geojson(result), indent=2, allow_nan=False),
                encoding="utf-8",
            )
            runs.append(
                {
                    "origin": origin,
                    "mode": mode,
                    "algorithm": algorithm,
                    "status": result["status"],
                    "length_m": result["length_m"],
                    "external_validation": result.get("external_validation"),
                    "file": filename,
                    "sha256": checksum(target),
                }
            )
            print(json.dumps(runs[-1]), flush=True)
        graph = [
            r for r in runs if r["mode"] == "research" and r["algorithm"] != "abitstar"
        ]
        assert abs(graph[0]["length_m"] - graph[1]["length_m"]) < 1e-6
        evidence = {
            "scenario": scenario,
            "source_preparation_s": source_seconds,
            "provenance": planner.constraints.provenance,
            "restriction_report": planner.constraints.restriction_report(),
            "runs": runs,
            "interpretation": "No real permissions supplied; conservative failures and research assumptions retained.",
        }
        (args.output / "evidence.json").write_text(
            json.dumps(evidence, indent=2, allow_nan=False), encoding="utf-8"
        )
    finally:
        planner.constraints.terrain.close()


if __name__ == "__main__":
    main()
