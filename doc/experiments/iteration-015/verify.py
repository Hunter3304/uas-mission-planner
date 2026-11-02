"""Sequential retained-source acceptance; no source downloads or rewrites."""

import argparse
import ctypes
import json
import sys
from copy import deepcopy
from itertools import pairwise
from math import isclose
from pathlib import Path
from time import perf_counter

from shapely.geometry import LineString
from shapely.ops import transform
from uas_planner.core.experiment import checksum
from uas_planner.core.paper_risk import FIELDS
from uas_planner.core.regional_routing import (
    REQUEST_SECONDS,
    RegionalPlanner,
    plan_regional_route,
)
from uas_planner.core.routing import route_geojson

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data/hannover-part1-v4"
TERRAIN = ROOT / "data/hannover-part2-terrain-v1"
SCENARIO = {
    "agl_m": 100,
    "speed_m_s": 30,
    "clearance_m": 0,
    "vertical_clearance_m": 0,
    "mission_start": "2026-10-07T10:00:00+02:00",
    "mission_end": "2026-10-07T10:15:00+02:00",
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
CONTROLS = {
    "planning_mode": "research",
    "cell_m": 250,
    "time_budget_s": 20,
    "background_cost": 0,
    "start_coordinate": [9.7967855, 52.4044919],
    "end_coordinate": [9.8044306, 52.3834796],
}


def save(path, result):
    path.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")


def memory():
    if sys.platform != "win32":
        return {"available": False}
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "peak_working_set",
                "working_set",
                "peak_paged",
                "paged",
                "peak_nonpaged",
                "nonpaged",
                "pagefile",
                "peak_pagefile",
                "private",
            )
        ]

    value = Counters()
    value.cb = ctypes.sizeof(value)
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    fn = ctypes.windll.psapi.GetProcessMemoryInfo
    fn.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
    if not fn(kernel.GetCurrentProcess(), ctypes.byref(value), value.cb):
        raise RuntimeError("Cannot inspect owned worker memory")
    return {
        "working_set_mib": value.working_set / 1048576,
        "peak_working_set_mib": value.peak_working_set / 1048576,
    }


def verify_sources():
    study = json.loads((DATA / "study.json").read_text(encoding="utf-8"))
    terrain = json.loads((TERRAIN / "terrain.json").read_text(encoding="utf-8"))
    receipts = [(DATA / entry["path"], entry["sha256"]) for entry in study["files"]]
    receipts += [
        (TERRAIN / entry["path"], entry["sha256"]) for entry in terrain["tiles"]
    ]
    receipts += [
        (TERRAIN / name, entry["sha256"])
        for name, entry in terrain.get("metadata", {}).items()
    ]
    for path, expected in receipts:
        assert checksum(path) == expected, str(path)
    return {"checked_files": len(receipts), "all_receipts_match": True}


def independent(path, surface, forward):
    """Independent cell partition, with high-cost tie policy and component totals."""
    totals = dict.fromkeys(FIELDS, 0.0)
    for a, b in pairwise(path):
        remaining = transform(forward, LineString([a, b]))
        cells = [c for c in surface.cells if c[0].intersects(remaining)]
        assert all(c[3] is not None for c in cells)
        for cell in sorted(cells, key=lambda c: (-c[3], c[1])):
            length = remaining.intersection(cell[0]).length
            for field, score in zip(FIELDS, cell[2], strict=True):
                totals[field] += length * score
            remaining = remaining.difference(cell[0])
        assert remaining.is_empty
    totals["fused_risk_length_cost"] = (
        sum(totals[f] for f in FIELDS[:3]) / 6 + totals[FIELDS[3]] / 2
    )
    return totals


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--output", type=Path, required=True)
    args.add_argument(
        "--cold",
        action="store_true",
        help="Fresh complete automatic ABIT* request with the 3 s UI budget",
    )
    options = args.parse_args()
    options.output.mkdir(parents=True, exist_ok=False)
    if options.cold:
        scenario = deepcopy(SCENARIO)
        scenario.pop("mission_end")
        started = perf_counter()
        controls = {**CONTROLS, "time_budget_s": 3}
        result = plan_regional_route(
            DATA,
            scenario,
            "rheuma-podbi",
            "mhh",
            terrain_directory=TERRAIN,
            duration_mode="automatic",
            algorithm="abitstar",
            **controls,
        )
        save(options.output / "automatic.geojson", route_geojson(result))
        save(
            options.output / "report.json",
            {
                "status": result["status"],
                "total_seconds": perf_counter() - started,
                "source_preparation_ms": result.get("source_preparation_ms"),
                "preparation_ms": result.get("preparation_ms"),
                "planner_ms": result.get("planner_ms"),
                "length_m": result.get("length_m"),
                "objective_cost": result.get("objective_cost"),
                "population_preparation_ms": result.get("population_preparation_ms"),
                "fusion_preparation_ms": result.get("fusion_preparation_ms"),
                "memory": memory(),
                "source_integrity": verify_sources(),
            },
        )
        print("cold automatic", result["status"], flush=True)
        return
    report = {}
    started = perf_counter()
    planner = RegionalPlanner(DATA, SCENARIO, terrain_directory=TERRAIN)
    report["source_preparation_seconds"] = perf_counter() - started
    print("source prepared", report["source_preparation_seconds"], flush=True)
    try:
        for algorithm in ("astar", "dijkstra", "abitstar"):
            # Each explicit comparison is an independent bounded request on verified
            # request-local source objects, with static surfaces reused when applicable.
            planner._request_deadline = perf_counter() + REQUEST_SECONDS
            result = planner.plan(
                "rheuma-podbi", "mhh", algorithm=algorithm, **CONTROLS
            )
            save(options.output / f"{algorithm}.geojson", route_geojson(result))
            print(algorithm, result["status"], result.get("length_m"), flush=True)
            report[algorithm] = {
                k: result.get(k)
                for k in (
                    "status",
                    "length_m",
                    "objective_cost",
                    "runtime_ms",
                    *FIELDS,
                    "fused_risk_length_cost",
                )
            }
            if result["status"] == "success":
                assert result["independent_validation"]
                assert (
                    result["geometry"]["coordinates"][0] == CONTROLS["start_coordinate"]
                )
                assert (
                    result["geometry"]["coordinates"][-1] == CONTROLS["end_coordinate"]
                )
                checked = independent(
                    result["geometry"]["coordinates"],
                    planner._paper.surface,
                    planner.forward,
                )
                for key, value in checked.items():
                    assert isclose(value, result[key], abs_tol=1e-6, rel_tol=1e-7)
                assert isclose(
                    result["objective_cost"],
                    0.9 * checked["fused_risk_length_cost"] + 0.1 * result["length_m"],
                    abs_tol=1e-6,
                )
        if all(report[a]["status"] == "success" for a in ("astar", "dijkstra")):
            assert isclose(
                report["astar"]["objective_cost"],
                report["dijkstra"]["objective_cost"],
                abs_tol=1e-6,
            )
        catalog = planner.plan(
            "rheuma-podbi", "mhh", planning_mode="conservative", time_budget_s=20
        )
        save(options.output / "catalog.geojson", route_geojson(catalog))
        assert catalog["status"] == "invalid_endpoint" and catalog["geometry"] is None
        report["catalog_status"] = catalog["status"]
    finally:
        planner.constraints.terrain.close()
        save(options.output / "report.json", report)
    scenario = deepcopy(SCENARIO)
    scenario.pop("mission_end")
    auto = plan_regional_route(
        DATA,
        scenario,
        "rheuma-podbi",
        "mhh",
        terrain_directory=TERRAIN,
        duration_mode="automatic",
        algorithm="astar",
        **CONTROLS,
    )
    save(options.output / "automatic.geojson", route_geojson(auto))
    report["automatic_status"] = auto["status"]
    if auto["status"] == "success":
        assert isclose(auto["timing"]["cruise_time_s"], auto["length_m"] / 30)
        assert auto["timing"]["estimated_arrival"] == auto["mission"]["mission_end"]
        assert auto["independent_validation"]
    save(options.output / "report.json", report)
    print("automatic", auto["status"], flush=True)
    report["memory"] = memory()
    report["source_integrity"] = verify_sources()
    save(options.output / "report.json", report)


if __name__ == "__main__":
    main()
