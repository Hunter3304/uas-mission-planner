"""Retained Hannover inputs; independent metric checks, no HTTP or source writes."""

import argparse
import json
from itertools import pairwise
from math import ceil, cos, hypot, isclose, pi
from pathlib import Path
from time import perf_counter

from shapely.geometry import LineString
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from uas_planner.core.costs import analyze_feature
from uas_planner.core.experiment import checksum
from uas_planner.core.regional_routing import RegionalPlanner
from uas_planner.core.routing import route_geojson


def independent(planner, result):
    """Never call planner.check, plan_route or RiskModel.evaluate for acceptance."""
    if result["status"] != "success":
        return {"accepted": False, "reason": result.get("message", result["status"])}
    coordinates = result["geometry"]["coordinates"]
    points = [planner.forward(*p) for p in coordinates]
    path = LineString(points)
    model = planner.constraints
    length = sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in pairwise(points))
    known = [
        r["geometry"]
        for r in model.records
        if r["category"] == "building_obstacle" and r["state"] == "blocked"
    ]
    known += [
        r["geometry"]
        for r in model.derived_obstacles
        if r["uncertain_geometry"]
        or r["height_m"] is not None
        and r["height_m"]
        >= result["mission"]["agl_m"] - result["mission"].get("vertical_clearance_m", 0)
    ]
    clearance = result["mission"].get("clearance_m", 0)
    envelope = path.buffer(clearance / cos(pi / 64)) if clearance else path
    obstacles_clear = not any(g.intersects(envelope) for g in known)
    terrain_known = True
    for a, b in pairwise(points):
        count = max(1, ceil(hypot(b[0] - a[0], b[1] - a[1]) / 250))
        for i in range(count):
            segment = LineString(
                [
                    tuple(a[j] + (b[j] - a[j]) * t / count for j in (0, 1))
                    for t in (i, i + 1)
                ]
            )
            terrain_known &= model.terrain.bounds(segment)["status"] == "known"
    risk = None
    objective = length
    if result["objective"] == "risk":
        query = transform(planner.reverse, path.envelope.buffer(1))
        records = []
        for index in model.risk_tree.query(query, predicate="intersects"):
            geometry, tags, _, _ = model.research_risk_records[int(index)]
            records.append(
                (
                    transform(planner.forward, geometry),
                    analyze_feature(tags, "building")["cost"],
                )
            )
        tree = STRtree([g for g, _ in records])
        risk = 0.0
        assessed = True
        for a, b in pairwise(points):
            segment = LineString([a, b])
            nearby = [
                records[int(i)] for i in tree.query(segment, predicate="intersects")
            ]
            assessed &= all(score is not None for _, score in nearby)
            remaining = segment
            for score in sorted(
                {score for _, score in nearby if score is not None}, reverse=True
            ):
                region = unary_union([g for g, value in nearby if value == score])
                risk += remaining.intersection(region).length * score
                remaining = remaining.difference(region)
            if result["controls"]["background_cost"] is None:
                assessed &= remaining.is_empty
            else:
                risk += remaining.length * result["controls"]["background_cost"]
        objective = (
            result["controls"]["risk_weight"] * risk
            + result["controls"]["distance_weight"] * length
        )
    else:
        assessed = True
    checks = {
        "endpoints": coordinates[0] == result["start"]
        and coordinates[-1] == result["end"],
        "boundary": model.boundary.covers(envelope),
        "known_obstacles": obstacles_clear,
        "terrain": terrain_known,
        "scored_support": assessed,
        "length": isclose(length, result["length_m"], rel_tol=1e-7, abs_tol=1e-6),
        "cost": isclose(
            objective, result["objective_cost"], rel_tol=1e-7, abs_tol=1e-6
        ),
        "cruise": isclose(
            length / result["mission"]["speed_m_s"],
            result["cruise_time_s"],
            rel_tol=1e-7,
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "length_m": length,
        "risk_length_cost": risk,
        "objective_cost": objective,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[3]
    scenario = json.loads(
        (root / "doc/experiments/iteration-008/hannover-scenario.json").read_text()
    )
    scenario.update(
        research_geometry="derived", research_height_m=30, research_geometry_buffer_m=20
    )
    started = perf_counter()
    planner = RegionalPlanner(
        root / "data/hannover-part1-v4",
        scenario,
        terrain_directory=root / "data/hannover-part2-terrain-v1",
    )
    source_seconds = perf_counter() - started
    print(f"Sources verified/prepared: {source_seconds:.2f} s", flush=True)
    cases = [
        (name, "astar", "risk", 500, "research")
        for name in ("rheuma-podbi", "amedes-georg", "limbach-lehrte")
    ]
    cases += [
        ("rheuma-podbi", algorithm, objective, 250, mode)
        for algorithm, objective, mode in [
            ("astar", "risk", "research"),
            ("dijkstra", "risk", "research"),
            ("astar", "distance", "research"),
            ("abitstar", "risk", "research"),
            ("astar", "risk", "strict"),
        ]
    ]
    evidence = []
    for name, algorithm, objective, cell, mode in cases:
        result = planner.plan(
            name,
            "mhh",
            planning_mode=mode,
            algorithm=algorithm,
            objective=objective,
            cell_m=cell,
            background_cost=0,
            time_budget_s=3,
        )
        validation = independent(planner, result)
        result["external_validation"] = validation
        filename = f"{name}-{algorithm}-{objective}-{cell}-{mode}.geojson"
        target = args.output / filename
        target.write_text(
            json.dumps(route_geojson(result), indent=2, allow_nan=False),
            encoding="utf8",
        )
        evidence.append(
            {
                "file": filename,
                "sha256": checksum(target),
                "status": result["status"],
                "length_m": result["length_m"],
                "objective_cost": result["objective_cost"],
                "preparation_ms": result["preparation_ms"],
                "planner_ms": result["planner_ms"],
                "runtime_ms": result["runtime_ms"],
                "external_validation": validation,
            }
        )
        print(filename, result["status"], result["length_m"], validation, flush=True)
        if result["status"] == "success" and not validation["accepted"]:
            raise RuntimeError("Independent real route verification failed")
    (args.output / "evidence.json").write_text(
        json.dumps(
            {
                "source_preparation_s": source_seconds,
                "scenario": scenario,
                "source_identity": planner.constraints.provenance["model_signature"],
                "derived_geometry": planner.constraints.geometry_assumptions,
                "runs": evidence,
            },
            indent=2,
        ),
        encoding="utf8",
    )
    planner.constraints.terrain.close()


if __name__ == "__main__":
    main()
