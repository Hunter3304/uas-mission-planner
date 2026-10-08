"""Reproduce Part 5 offline static experiments without altering source snapshots."""

import argparse
import json
import platform
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from time import perf_counter
from zoneinfo import ZoneInfo

import requests
from pyproj import Transformer
from shapely.geometry import box
from uas_planner.acquisition.study import region_for_locations
from uas_planner.core.experiment import checksum, read_json
from uas_planner.core.regional_routing import RegionalPlanner
from uas_planner.core.static_experiments import (
    PAIRS,
    planner_at_speed,
    run_matrix,
    summarize,
    synthetic_planner,
)


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def forbid_network(*args, **kwargs):
    raise AssertionError("Part 5 experiments must be offline.")


def boundary_evidence(manifest, terrain):
    config = manifest["config"]
    expanded = region_for_locations(config["locations"], 10000)
    bounds = expanded.as_tuple()
    initial = config["bounds"]
    initial_box = box(*(initial[k] for k in ("west", "south", "east", "north")))
    covered = initial_box.covers(box(*bounds))
    forward = Transformer.from_crs(4326, 25832, always_xy=True)
    sizes = []
    for label, rectangle in (
        ("initial-5km", initial_box.bounds),
        ("expanded-10km", bounds),
    ):
        west, south, east, north = forward.transform_bounds(*rectangle)
        for cell in (100, 250, 500):
            from math import ceil

            count = ceil((east - west) / cell) * ceil((north - south) / cell)
            sizes.append(
                {
                    "region": label,
                    "cell_m": cell,
                    "candidate_cells_upper_bound": count,
                    "exceeds_10000": count > 10000,
                }
            )
    return {
        "expanded_margin_m": 10000,
        "expanded_bounds": asdict(expanded),
        "retained_study_covers_expansion": covered,
        "retained_terrain_covers_expansion": box(*terrain["bounds_wgs84"]).covers(
            box(*bounds)
        ),
        "status": "missing_source_coverage" if not covered else "covered",
        "routing_attempted": False,
        "reason": "The larger OSM PBF is retained, but DIPUL pages, GHSL crop and terrain are scoped to the original region. A larger region needs a separate complete snapshot; no invented coverage or cropped search.",
        "grid_scale": sizes,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="New directory; never overwritten"
    )
    parser.add_argument("--study", type=Path, default=Path("data/hannover-part1-v4"))
    parser.add_argument(
        "--terrain", type=Path, default=Path("data/hannover-part2-terrain-v1")
    )
    parser.add_argument(
        "--scenario",
        type=Path,
        default=Path("doc/experiments/iteration-008/hannover-scenario.json"),
    )
    parser.add_argument("--synthetic-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    requests.sessions.Session.request = forbid_network
    scenario = read_json(args.scenario)
    records = []
    preparations = []
    boundary = None
    input_hashes = {"scenario": checksum(args.scenario)}
    started = perf_counter()
    if not args.synthetic_only:
        input_hashes.update(
            study=checksum(args.study / "study.json"),
            terrain=checksum(args.terrain / "terrain.json"),
        )
        for altitude in (100, 120):
            prepared_started = perf_counter()
            planner = RegionalPlanner(
                args.study,
                {**scenario, "agl_m": altitude},
                terrain_directory=args.terrain,
            )
            source_ms = (perf_counter() - prepared_started) * 1000
            preparations.append(
                {
                    "kind": "real",
                    "altitude_m": altitude,
                    "source_preparation_ms": source_ms,
                    "cache_state": "fresh_prepared_model",
                }
            )
            if boundary is None:
                boundary = boundary_evidence(
                    planner.constraints.manifest,
                    read_json(args.terrain / "terrain.json"),
                )
            for cache in ("fresh_prepared_batch", "reused_prepared_batch"):
                for pair in PAIRS:
                    records.extend(
                        run_matrix(
                            planner,
                            pair,
                            label=f"real-{altitude}m",
                            cache_state=cache,
                            source_ms=source_ms
                            if cache == "fresh_prepared_batch"
                            else 0,
                            budget_s=1,
                        )
                    )
            # A changed resolution never bypasses exact endpoint preflight.
            for cell in (100, 500):
                for pair in PAIRS:
                    records.extend(
                        run_matrix(
                            planner,
                            pair,
                            label=f"real-{altitude}m-grid-{cell}",
                            cache_state="reused_prepared_batch",
                            source_ms=0,
                            cell_m=cell,
                            budget_s=1,
                        )
                    )
            for speed in (25, 35):
                speed_planner = planner_at_speed(planner, speed)
                for pair in PAIRS:
                    batch = run_matrix(
                        speed_planner,
                        pair,
                        label=f"real-{altitude}m-speed-{speed}",
                        cache_state="reused_prepared_batch",
                        source_ms=0,
                        budget_s=1,
                    )
                    records.extend(batch)
            # Research mode is explicit evidence, not an automatic fallback.
            for pair in PAIRS:
                result = planner.plan(*pair, planning_mode="research")
                write_json(args.output / f"research-{altitude}-{pair[0]}.json", result)
            print(
                f"Real {altitude} m: {len(records)} records; preparation {source_ms:.0f} ms",
                flush=True,
            )
            del planner
    for fixture in ("risk-detour", "diagonal", "boundary-detour"):
        variants = [
            ("base", {}, False, 50),
            ("altitude-120", {"agl_m": 120}, False, 50),
            ("speed-25", {"speed_m_s": 25}, False, 50),
            ("speed-35", {"speed_m_s": 35}, False, 50),
            ("grid-25", {}, False, 25),
            ("grid-100", {}, False, 100),
            ("expanded", {}, True, 50),
        ]
        for variant, changes, expanded, cell in variants:
            t = perf_counter()
            planner = synthetic_planner(
                fixture, {**scenario, **changes}, expanded=expanded
            )
            source_ms = (perf_counter() - t) * 1000
            preparations.append(
                {
                    "kind": "synthetic",
                    "fixture": fixture,
                    "variant": variant,
                    "source_preparation_ms": source_ms,
                }
            )
            records.extend(
                run_matrix(
                    planner,
                    ("a", "b"),
                    label=f"synthetic-{fixture}-{variant}",
                    cache_state="fresh_prepared_batch",
                    source_ms=source_ms,
                    cell_m=cell,
                )
            )
            if variant == "base":
                records.extend(
                    run_matrix(
                        planner,
                        ("a", "b"),
                        label=f"synthetic-{fixture}-{variant}",
                        cache_state="reused_prepared_batch",
                        source_ms=0,
                        cell_m=cell,
                    )
                )
            print(f"Synthetic {fixture}/{variant} complete", flush=True)
    summary = summarize(records)
    comparisons = []
    for label in sorted(
        {r["label"] for r in records if r["label"].startswith("synthetic-")}
    ):
        successful = {
            r["result"]["objective"]: r
            for r in records
            if r["label"] == label
            and r["result"]["algorithm"] == "astar"
            and r["cache_state"] == "fresh_prepared_batch"
            and r["result"]["status"] == "success"
        }
        if len(successful) == 2:
            weighted, distance = [successful[o] for o in ("risk", "distance")]
            comparisons.append(
                {
                    "label": label,
                    "weighted_length_m": weighted["result"]["length_m"],
                    "distance_length_m": distance["result"]["length_m"],
                    "weighted_risk_cost": weighted["experiment_validation"][
                        "building_risk_cost"
                    ],
                    "distance_route_risk_cost": distance["experiment_validation"][
                        "building_risk_cost"
                    ],
                    "weighted_objective": weighted["experiment_validation"][
                        "weighted_objective"
                    ],
                    "distance_route_weighted_objective": distance[
                        "experiment_validation"
                    ]["weighted_objective"],
                }
            )
    report = {
        "schema_version": 1,
        "created_at": datetime.now(ZoneInfo("Europe/Berlin")).isoformat(),
        "scope": "Static offline research experiments; synthetic success is not a real Hannover route",
        "offline": True,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "input_manifest_sha256": input_hashes,
        "cache_policy": "Fresh/reused prepared model batches. OS filesystem caches are uncontrolled. Every solve has a new bounded motion cache; no cached route is reused. source_preparation_ms is shared batch cost, not a repeated measured per-solve cost.",
        "preparations": preparations,
        "boundary_sensitivity": boundary,
        "record_count": len(records),
        "outcomes": dict(Counter(r["result"]["status"] for r in records)),
        "summaries": summary,
        "synthetic_objective_comparisons": comparisons,
        "wall_ms": (perf_counter() - started) * 1000,
    }
    write_json(args.output / "runs.json", records)
    report["runs_sha256"] = checksum(args.output / "runs.json")
    write_json(args.output / "summary.json", report)
    print(
        json.dumps(
            {
                "records": len(records),
                "outcomes": report["outcomes"],
                "output": str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
