"""Isolated, sequential real Hannover timing/memory and population acceptance."""

import argparse
import ctypes
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from importlib.util import find_spec
from itertools import pairwise
from math import floor, isclose
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import rasterio
from pyproj import Transformer
from shapely import segmentize
from shapely.geometry import LineString, box, shape
from shapely.ops import transform, unary_union

from uas_planner.core import population_costs as pc
from uas_planner.core import regional_routing as routing
from uas_planner.core.experiment import checksum
from uas_planner.core.population_routing import PopulationEvaluator
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
OPTIONS = {
    "duration_mode": "automatic",
    "terrain_directory": TERRAIN,
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
PROFILES = [f"{a}-risk-{p}" for a in ("astar", "dijkstra", "abitstar") for p in ("off", "on")]
PROFILES.append("astar-distance-on")


def memory():
    """Current process only; peak is the OS lifetime high-water mark, not an allocation delta."""
    if sys.platform != "win32":
        return {"available": False, "reason": "Windows process counters required"}
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

    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenProcess(0x410, False, os.getpid())
    if not handle:
        raise RuntimeError("Cannot read owned process counters")
    try:
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        fn = ctypes.windll.psapi.GetProcessMemoryInfo
        fn.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
        if not fn(handle, ctypes.byref(counters), counters.cb):
            raise RuntimeError("Process counter query failed")
        return {
            "available": True,
            **{
                k: getattr(counters, k)
                for k in (
                    "working_set",
                    "peak_working_set",
                    "private",
                )
            },
        }
    finally:
        kernel.CloseHandle(handle)


def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")


def independent_population(geometry, cells):
    forward = Transformer.from_crs(4326, 25832, always_xy=True).transform
    total = 0.0
    for a, b in pairwise(geometry["coordinates"]):
        line = transform(forward, LineString([a, b]))
        selected = [(g, s) for g, _, s in cells if g.intersects(line)]
        assert all(s is not None for _, s in selected)
        for score in range(4, -1, -1):
            region = unary_union([g for g, s in selected if s == score])
            total += line.intersection(region).length * score
            line = line.difference(region)
    return total


def surface_worker(output):
    before = memory()
    started = perf_counter()
    surface = pc.prepare_population_surface(DATA)
    cold = (perf_counter() - started) * 1000
    prepared_memory = memory()
    warm = []
    for _ in range(10):
        started = perf_counter()
        assert pc.prepare_population_surface(DATA) is surface
        warm.append((perf_counter() - started) * 1000)
    started = perf_counter()
    evaluator = PopulationEvaluator(surface)
    index_ms = (perf_counter() - started) * 1000
    started = perf_counter()
    display = surface.display()
    display_ms = (perf_counter() - started) * 1000
    started = perf_counter()
    payload = json.dumps(display, separators=(",", ":"), allow_nan=False).encode()
    serialization_ms = (perf_counter() - started) * 1000
    assert display["display"]["complete"] and len(payload) < pc.MAX_DISPLAY_BYTES
    view = surface.display([9.79, 52.38, 9.81, 52.41])
    assert view["identity"] == display["identity"] and view["bins"] == display["bins"]
    native = transform(
        Transformer.from_crs(25832, "ESRI:54009", always_xy=True).transform,
        segmentize(shape(surface.metadata["study_boundary_metric"]), 25),
    )
    independent_total = 0.0
    with rasterio.open(DATA / "population.tif") as raster:
        w, s, e, n = native.bounds
        for x in range(floor(w / 5000) * 5000, int(e) + 5000, 5000):
            for y in range(floor(s / 5000) * 5000, int(n) + 5000, 5000):
                piece = native.intersection(box(x, y, x + 5000, y + 5000))
                if piece.area > 0:
                    independent_total += pc.aggregate_native(raster, piece)["estimated_people"]
    assert isclose(independent_total, surface.metadata["estimated_people"], abs_tol=1e-3)
    assert evaluator.metadata["identity"] == display["identity"]
    return {
        "passed": True,
        "cold_prepare_ms": cold,
        "warm_prepare_ms": warm,
        "index_ms": index_ms,
        "display_build_ms": display_ms,
        "display_serialization_ms": serialization_ms,
        "display_bytes": len(payload),
        "metadata": surface.metadata,
        "independent_people": independent_total,
        "count_difference": independent_total - surface.metadata["estimated_people"],
        "memory_before": before,
        "memory_after_surface": prepared_memory,
        "memory_after_display_and_validation": memory(),
        "cache": pc._prepared.cache_info()._asdict(),
    }


def route_worker(profile, output):
    algorithm, objective, enabled = profile.split("-")
    active = enabled == "on"
    calls = 2 if algorithm == "astar" and objective == "risk" else 1
    records = []
    for iteration in range(calls):
        preparation = []
        original = routing.prepare_population_surface

        def measured(*args, **kwargs):
            cache = pc._prepared.cache_info()
            started = perf_counter()
            value = original(*args, **kwargs)
            preparation.append(
                {
                    "ms": (perf_counter() - started) * 1000,
                    "cache_hit": pc._prepared.cache_info().hits > cache.hits,
                    "identity": value.metadata["identity"],
                }
            )
            return value

        before = memory()
        started = perf_counter()
        with patch.object(routing, "prepare_population_surface", measured):
            result = routing.plan_regional_route(
                DATA,
                SCENARIO,
                "rheuma-podbi",
                "mhh",
                **OPTIONS,
                algorithm=algorithm,
                objective=objective,
                include_population=active,
                population_weight=1,
            )
        elapsed = (perf_counter() - started) * 1000
        after = memory()
        exported = route_geojson(result)
        save(output / f"{profile}-{iteration}.geojson", exported)
        independent = None
        if result["status"] == "success":
            assert result["independent_validation"]
            assert result["geometry"]["coordinates"][0] == OPTIONS["start_coordinate"]
            assert result["geometry"]["coordinates"][-1] == OPTIONS["end_coordinate"]
            timing = result["timing"]
            assert timing["estimated_arrival"] == result["mission"]["mission_end"]
            assert datetime.fromisoformat(timing["estimated_arrival"]) <= datetime.fromisoformat(
                timing["assessed_interval"]["mission_end"]
            )
            if active:
                prepared = pc.prepare_population_surface(DATA)
                independent = independent_population(result["geometry"], prepared.metric_cells)
                assert isclose(
                    independent, result["population_length_cost"], abs_tol=1e-4, rel_tol=1e-7
                )
                for endpoint in ("start", "end"):
                    assert (
                        result["endpoint_diagnostics"][endpoint]["population"]["assessment"]
                        == "assessed"
                    )
                assert result["population_model"]["identity"] == prepared.metadata["identity"]
            else:
                assert result["population_length_cost"] is None and not preparation
            weights = result["effective_weights"]
            combined = (
                weights["distance"] * result["length_m"]
                + weights["building"] * (result["risk_length_cost"] or 0)
                + weights["population"] * (result["population_length_cost"] or 0)
            )
            assert isclose(result["objective_cost"], combined, abs_tol=1e-5)
            assert (
                exported["features"][0]["properties"]["population_length_cost"]
                == result["population_length_cost"]
            )
        else:
            assert not exported["features"]
            assert (
                result["geometry"]
                is result["population_length_cost"]
                is result["objective_cost"]
                is None
            )
            assert result["timing"]["estimated_arrival"] is None
        records.append(
            {
                "iteration": iteration,
                "status": result["status"],
                "message": result.get("message"),
                "elapsed_ms": elapsed,
                **{
                    k: result.get(k)
                    for k in (
                        "length_m",
                        "risk_length_cost",
                        "population_length_cost",
                        "objective_cost",
                        "source_preparation_ms",
                        "preparation_ms",
                        "planner_ms",
                        "final_validation_ms",
                        "complete_interval_validation_ms",
                        "effective_weights",
                    )
                },
                "population_preparation": preparation,
                "independent_population_cost": independent,
                "memory_before": before,
                "memory_after_request": after,
                "population_identity": result.get("population_model", {}).get("identity")
                if result.get("population_model")
                else None,
            }
        )
        # Keep every completed run even if later verification fails.
        save(output / f"{profile}.json", {"profile": profile, "runs": records})
    return {"profile": profile, "runs": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", choices=["surface", *PROFILES])
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.worker:
        result = (
            surface_worker(args.output)
            if args.worker == "surface"
            else route_worker(args.worker, args.output)
        )
        save(args.output / f"{args.worker}.json", result)
        return
    args.output.mkdir(parents=True, exist_ok=False)
    sources = [DATA / n for n in ("population.tif", "study.json", "osm/features.gpkg")]
    sources.extend(p for p in TERRAIN.iterdir() if p.suffix in (".tif", ".json", ".xml"))
    before = {str(p.relative_to(ROOT)): checksum(p) for p in sources}
    save(args.output / "source-hashes-before.json", before)
    profiles = [p for p in PROFILES if not p.startswith("abitstar") or find_spec("ompl")]
    evidence = {}
    for profile in ["surface", *profiles]:
        with (args.output / f"{profile}.log").open("w", encoding="utf-8") as log:
            subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--output",
                    str(args.output),
                    "--worker",
                    profile,
                ],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=330,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        evidence[profile] = json.loads(
            (args.output / f"{profile}.json").read_text(encoding="utf-8")
        )
        print(
            json.dumps(
                {
                    "completed": profile,
                    "statuses": [r["status"] for r in evidence[profile].get("runs", [])],
                }
            ),
            flush=True,
        )
    assert before == {str(p.relative_to(ROOT)): checksum(p) for p in sources}
    for profile in (
        "astar-risk-off",
        "astar-risk-on",
        "dijkstra-risk-off",
        "dijkstra-risk-on",
        "astar-distance-on",
    ):
        assert all(r["status"] == "success" for r in evidence[profile]["runs"]), profile
    for flag in ("off", "on"):
        a = evidence[f"astar-risk-{flag}"]["runs"][0]
        b = evidence[f"dijkstra-risk-{flag}"]["runs"][0]
        assert isclose(a["objective_cost"], b["objective_cost"], abs_tol=1e-5)
    identities = {
        r["population_identity"]
        for p in profiles
        for r in evidence[p]["runs"]
        if r["population_identity"]
    }
    assert identities == {evidence["surface"]["metadata"]["identity"]}
    save(
        args.output / "acceptance.json",
        {
            "passed": True,
            "platform": platform.platform(),
            "python": platform.python_version(),
            "measurement_scope": "Sequential isolated worker processes. Cold means empty application cache, not cold OS filesystem cache. Warm A* repeats retain population surface only; regional source preparation remains request-local. Memory is OS process lifetime high-water, not incremental population allocation. Single finite-budget native runs establish no optimum/distribution.",
            "source_hashes": before,
            "evidence": evidence,
        },
    )
    print(json.dumps({"passed": True, "output": str(args.output)}), flush=True)


if __name__ == "__main__":
    main()
