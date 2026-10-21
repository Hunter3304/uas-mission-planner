"""Reproduce compact cost/detail agreement against retained original Hannover OSM.

Requires an explicitly prepared schema-2 display cache. Writes a new evidence
directory only; does not acquire data, launch servers or modify original sources.
Timings use in-process ASGI requests, excluding browser/TCP/rendering.
"""

import argparse
import importlib.util
import json
import math
import platform
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import pyogrio
from fastapi.testclient import TestClient
from shapely.geometry import box, shape
from uas_planner.api.app import create_app
from uas_planner.core.costs import analyze_feature
from uas_planner.core.osm_display import (
    CATEGORIES,
    SCORE_FIELDS,
    DisplayStore,
    context,
    read_database,
)
from uas_planner.storage.dataset import checksum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("data/hannover-part1-v4"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    directory = args.dataset.resolve()
    ctx = context(directory)
    original_hash = checksum(ctx["source"])
    started = perf_counter()
    summary = DisplayStore(directory.parent / ".osm-display").summary(directory)
    cold_s = perf_counter() - started
    records, details, inspected = [], [], set()
    regions = [
        ("mhh", 9.8044306, 52.3834796),
        ("podbi", 9.7967855, 52.4044919),
        ("central", 9.738, 52.373),
        ("lehrte", 10.0, 52.375),
        ("boundary", ctx["bounds"][0] + 0.001, ctx["bounds"][1] + 0.001),
    ]
    with TestClient(create_app(directory.parent)) as client:
        base = f"/api/datasets/{directory.name}/study/osm"
        started = perf_counter()
        client.get(base + "/summary").raise_for_status()
        api_cold_s = perf_counter() - started
        for region, lon, lat in regions:
            for span in (0.001, 0.002, 0.004, 0.008):
                requested = (lon - span, lat - span / 2, lon + span, lat + span / 2)
                params = {"bbox": ",".join(map(str, requested)), "zoom": 16}
                response = client.get(base + "/features", params=params)
                response.raise_for_status()
                category_result = response.json()
                effective = category_result["display"]["effective_bounds"]
                source = pyogrio.read_dataframe(
                    ctx["source"],
                    layer="features",
                    bbox=tuple(effective),
                    columns=["element_type", "osm_id", "tags_json"],
                )
                source = source[
                    source.geometry.is_valid
                    & source.geometry.intersects(box(*effective))
                    & source.geometry.geom_type.isin(
                        [
                            "Point",
                            "MultiPoint",
                            "LineString",
                            "MultiLineString",
                            "Polygon",
                            "MultiPolygon",
                        ]
                    )
                ]
                original = {
                    f"{row.element_type}/{row.osm_id}": (
                        json.loads(row.tags_json),
                        row.geometry,
                    )
                    for row in source.itertuples()
                }
                expected_category = {
                    key
                    for key, (tags, _) in original.items()
                    if any(tags.get(name) is not None for name in CATEGORIES)
                }
                assert {
                    f["id"] for f in category_result["features"]
                } == expected_category
                for category in CATEGORIES:
                    started = perf_counter()
                    response = client.get(
                        base + "/features",
                        params={
                            **params,
                            "style": "cost",
                            "cost_category": category,
                        },
                    )
                    elapsed = perf_counter() - started
                    response.raise_for_status()
                    result = response.json()
                    assert result["display"]["complete"]
                    assert len(response.content) <= summary["limits"]["response_bytes"]
                    assert len(result["features"]) <= summary["limits"]["features"]
                    assert (
                        result["display"]["coordinates"]
                        <= summary["limits"]["coordinates"]
                    )
                    expected = {}
                    for key, (tags, _) in original.items():
                        analysis = analyze_feature(tags, category)
                        if analysis is not None:
                            expected[key] = {
                                field: analysis[field] for field in SCORE_FIELDS
                            }
                    assert {f["id"] for f in result["features"]} == set(expected)
                    for feature in result["features"]:
                        assert feature["cost_analysis"] == expected[feature["id"]]
                    records.append(
                        {
                            "region": region,
                            "span": span,
                            "category": category,
                            "seconds": elapsed,
                            "bytes": len(response.content),
                            "objects": len(result["features"]),
                            "coordinates": result["display"]["coordinates"],
                            "independent_ids_and_demo_costs_agree": True,
                        }
                    )
                    for feature in result["features"][:2] + result["features"][-2:]:
                        key = feature["id"]
                        if key in inspected:
                            continue
                        inspected.add(key)
                        started = perf_counter()
                        response = client.get(base + "/features/" + key)
                        elapsed = perf_counter() - started
                        response.raise_for_status()
                        detail = response.json()
                        tags, geometry = original[key]
                        element, osm_id = key.split("/")
                        assert detail["properties"] == {
                            **tags,
                            "element_type": element,
                            "osm_id": int(osm_id),
                        }
                        assert detail["layer_analyses"] == {
                            name: analyze_feature(tags, name) for name in CATEGORIES
                        }
                        assert shape(detail["geometry"]).equals_exact(geometry, 0)
                        assert (
                            detail["display"]["identity"]
                            == result["display"]["identity"]
                        )
                        assert (
                            len(response.content) <= summary["limits"]["response_bytes"]
                        )
                        details.append(
                            {
                                "id": key,
                                "seconds": elapsed,
                                "bytes": len(response.content),
                            }
                        )
        diagnostic_records = []
        for item in summary["diagnostics"]["samples"]:
            key = f"{item['element_type']}/{item['osm_id']}"
            response = client.get(base + "/features/" + key)
            response.raise_for_status()
            detail = response.json()
            assert detail["display"]["diagnostic"] == item["reason"]
            assert not detail["display"]["drawable"]
            assert detail["display"]["tags_complete"]
            diagnostic_records.append(
                {
                    "id": key,
                    "diagnostic": item["reason"],
                    "bytes": len(response.content),
                }
            )
    with sqlite3.connect(ctx["source"].as_uri() + "?mode=ro", uri=True) as source:
        query_plan = source.execute(
            "EXPLAIN QUERY PLAN SELECT tags_json FROM features WHERE fid=?",
            (1,),
        ).fetchall()
    cache_database = (
        directory.parent / ".osm-display" / ctx["key"] / summary["database"]
    )
    with read_database(cache_database) as cache:
        cost_query_plan = cache.execute(
            "EXPLAIN QUERY PLAN SELECT o.id,o.element_type,o.osm_id,o.mask,o.coordinates,o.geometry_bytes "
            "FROM spatial s JOIN objects o ON o.id=s.id "
            "JOIN costs c ON c.object_id=o.id AND c.category=? "
            "WHERE s.maxx>=? AND s.minx<=? AND s.maxy>=? AND s.miny<=? "
            "AND (o.mask & ?)!=0 LIMIT ?",
            ("building", 9.8, 9.81, 52.38, 52.39, 15, 10001),
        ).fetchall()
    assert checksum(ctx["source"]) == original_hash
    # Reuse the platform-specific process counter helper from Part 1's guide.
    spec = importlib.util.spec_from_file_location(
        "part1_evidence", Path(__file__).with_name("verify-part1.py")
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    elapsed = sorted(record["seconds"] for record in records)
    result = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "identity": ctx["identity"],
        "summary": summary,
        "cold_verification_s": cold_s,
        "api_cold_verification_s": api_cold_s,
        "warm_cost_queries": len(records),
        "all_queries_complete_and_agree": True,
        "warm_cost_api_p95_s": elapsed[math.ceil(len(elapsed) * 0.95) - 1],
        "warm_cost_api_max_s": max(elapsed),
        "details_checked": len(details),
        "diagnostics_checked": len(diagnostic_records),
        "original_source_unchanged": True,
        "detail_source_query_plan": query_plan,
        "cost_query_plan": cost_query_plan,
        "process_memory": helper.process_memory(),
        "queries": records,
        "details": details,
        "diagnostics": diagnostic_records,
        "limitations": "In-process ASGI timings; no TCP, browser or route-overhead measurement.",
    }
    (args.output / "evidence.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "warm_cost_queries",
                    "warm_cost_api_p95_s",
                    "warm_cost_api_max_s",
                    "details_checked",
                    "diagnostics_checked",
                    "original_source_unchanged",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
