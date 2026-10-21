"""Reproduce Part 1 real Hannover indexed-query/API evidence without source writes.

Run with backend Python; an already prepared display cache is required. Output
must be a new directory. This script does not start servers or use the network.
"""

import argparse
import ctypes
import json
import math
import platform
import sqlite3
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

import pyogrio
from fastapi.testclient import TestClient
from shapely.geometry import box
from uas_planner.api.app import create_app
from uas_planner.core.osm_display import CATEGORIES, DisplayStore, context
from uas_planner.storage.dataset import checksum


def process_memory():
    if sys.platform != "win32":
        return {
            "available": False,
            "reason": "This measurement helper uses Windows process counters.",
        }
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "PeakWorkingSetSize",
                "WorkingSetSize",
                "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage",
                "PagefileUsage",
                "PeakPagefileUsage",
                "PrivateUsage",
            )
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    function = ctypes.windll.psapi.GetProcessMemoryInfo
    function.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
    if not function(
        ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
    ):
        return {"available": False, "reason": "Windows process counter call failed."}
    return {
        name: getattr(counters, name)
        for name in ("PeakWorkingSetSize", "WorkingSetSize", "PrivateUsage")
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("data/hannover-part1-v4"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Explicitly rebuild and measure display preparation first",
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    directory = args.dataset.resolve()
    ctx = context(directory)
    initial_hash = checksum(ctx["source"])
    store = DisplayStore(directory.parent / ".osm-display")
    memory_before = process_memory()
    preparation = None
    if args.prepare:
        preparation_start = perf_counter()
        store.prepare(directory, refresh=True)
        preparation = {
            "wall_s": perf_counter() - preparation_start,
            "memory_after": process_memory(),
        }
        # Measure startup verification with a new store after explicit preparation.
        store = DisplayStore(directory.parent / ".osm-display")
    start = perf_counter()
    summary = store.summary(directory)
    cold_verification_s = perf_counter() - start
    regions = [
        ("mhh", 9.8044306, 52.3834796),
        ("podbi", 9.7967855, 52.4044919),
        ("central", 9.738, 52.373),
        ("lehrte", 10.0, 52.375),
        ("boundary", ctx["bounds"][0] + 0.001, ctx["bounds"][1] + 0.001),
    ]
    records = []
    with sqlite3.connect(ctx["source"].as_uri() + "?mode=ro", uri=True) as source:
        source_query_plan = source.execute(
            "EXPLAIN QUERY PLAN SELECT f.fid FROM rtree_features_geom s "
            "JOIN features f ON f.fid=s.id WHERE s.maxx>=? AND s.minx<=? AND s.maxy>=? AND s.miny<=?",
            (9.8, 9.81, 52.38, 52.39),
        ).fetchall()
    with TestClient(create_app(directory.parent)) as client:
        # Separate first API-process verification from the warm query samples.
        start = perf_counter()
        response = client.get(f"/api/datasets/{directory.name}/study/osm/summary")
        response.raise_for_status()
        api_cold_s = perf_counter() - start
        for region, lon, lat in regions:
            for span in (0.001, 0.002, 0.004, 0.008):
                bbox = (lon - span, lat - span / 2, lon + span, lat + span / 2)
                params = {"bbox": ",".join(map(str, bbox)), "zoom": 16}
                start = perf_counter()
                response = client.get(
                    f"/api/datasets/{directory.name}/study/osm/features", params=params
                )
                response.raise_for_status()
                elapsed = perf_counter() - start
                result = response.json()
                assert len(response.content) <= summary["limits"]["response_bytes"]
                assert len(result["features"]) <= summary["limits"]["features"]
                assert (
                    result["display"].get("coordinates", 0)
                    <= summary["limits"]["coordinates"]
                )
                effective = result["display"]["effective_bounds"]
                independently_selected = pyogrio.read_dataframe(
                    ctx["source"],
                    layer="features",
                    bbox=tuple(effective),
                    columns=["element_type", "osm_id", "tags_json"],
                )
                supported = independently_selected.geometry.geom_type.isin(
                    [
                        "Point",
                        "MultiPoint",
                        "LineString",
                        "MultiLineString",
                        "Polygon",
                        "MultiPolygon",
                    ]
                )
                valid = independently_selected.geometry.is_valid
                intersects = independently_selected.geometry.intersects(box(*effective))
                membership = independently_selected.tags_json.map(
                    lambda raw: any(
                        json.loads(raw).get(name) is not None for name in CATEGORIES
                    )
                )
                selected = independently_selected[
                    supported & valid & intersects & membership
                ]
                expected = {
                    f"{r.element_type}/{r.osm_id}" for r in selected.itertuples()
                }
                actual = {f["id"] for f in result["features"]}
                assert actual.issubset(expected)
                if result["display"]["complete"]:
                    assert actual == expected
                records.append(
                    {
                        "region": region,
                        "bbox": bbox,
                        "seconds": elapsed,
                        "bytes": len(response.content),
                        "independent_source_count": len(expected),
                        **result["display"],
                    }
                )
        overview = client.get(
            f"/api/datasets/{directory.name}/study/osm/overview",
            params={"bbox": ",".join(map(str, ctx["bounds"]))},
        )
        overview.raise_for_status()
        whole = overview.json()
        assert (
            sum(f["properties"]["objects"] for f in whole["features"])
            == summary["drawable_count"]
        )
        assert len(whole["features"]) <= summary["limits"]["overview_cells"]
        assert len(overview.content) <= summary["limits"]["response_bytes"]
        guard_start = perf_counter()
        guard = client.get(
            f"/api/datasets/{directory.name}/features?analysis=tag-costs"
        )
        assert guard.status_code == 413
        guard_s = perf_counter() - guard_start
        catalog_start = perf_counter()
        details = client.get(f"/api/datasets/{directory.name}")
        details.raise_for_status()
        catalog_s = perf_counter() - catalog_start
    times = sorted(r["seconds"] for r in records)
    assert checksum(ctx["source"]) == initial_hash
    evidence = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "versions": {name: version(name) for name in ("shapely", "pyogrio", "fastapi")},
        "source_identity": ctx["identity"],
        "source_bytes": ctx["source"].stat().st_size,
        "original_source_unchanged": True,
        "source_index_query_plan": source_query_plan,
        "prepared_summary": summary,
        "measured_preparation": preparation,
        "cold_source_cache_verification_s": cold_verification_s,
        "api_cold_verification_s": api_cold_s,
        "warm_query_count": len(records),
        "warm_api_p95_s": times[math.ceil(len(times) * 0.95) - 1],
        "warm_api_max_s": max(times),
        "within_budget_complete_queries": sum(r["complete"] for r in records),
        "overview_cells": len(whole["features"]),
        "overview_bytes": len(overview.content),
        "legacy_guard_s": guard_s,
        "warm_dataset_details_s": catalog_s,
        "memory_before": memory_before,
        "memory_after": process_memory(),
        "browser_memory": "Not measured: Part 1 is API/data access, without frontend integration.",
        "transport": "In-process ASGI TestClient; includes API serialization, excludes real TCP/browser rendering.",
        "queries": records,
    }
    (args.output / "evidence.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    (args.output / "overview.geojson").write_bytes(overview.content)
    print(
        json.dumps(
            {
                key: evidence[key]
                for key in (
                    "warm_query_count",
                    "warm_api_p95_s",
                    "warm_api_max_s",
                    "within_budget_complete_queries",
                    "overview_cells",
                    "overview_bytes",
                    "original_source_unchanged",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
