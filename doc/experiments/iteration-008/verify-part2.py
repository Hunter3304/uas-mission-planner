"""Reproduce real Part 2 evidence offline; requires retained local source snapshots."""

import argparse
import json
import time
from collections import Counter
from pathlib import Path

import requests
from shapely.geometry import LineString
from uas_planner.core.experiment import read_json, write_json
from uas_planner.core.regional import RegionalConstraints, metric_geometry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, default=Path("data/hannover-part1-v4"))
    parser.add_argument(
        "--terrain", type=Path, default=Path("data/hannover-part2-terrain-v1")
    )
    parser.add_argument(
        "--scenario",
        type=Path,
        default=Path("doc/experiments/iteration-008/hannover-scenario.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)

    def forbid_network(*args, **kwargs):
        raise AssertionError(
            "Network access forbidden during Part 2 offline verification."
        )

    requests.sessions.Session.request = forbid_network
    results = []
    for altitude in (100, 120):
        started = time.perf_counter()
        scenario = {**read_json(args.scenario), "agl_m": altitude}
        model = RegionalConstraints(
            args.study, scenario, terrain_directory=args.terrain
        )
        summary = model.summary()
        sites = {
            s["id"]: [s["longitude"], s["latitude"]]
            for s in model.manifest["config"]["locations"]
        }
        motions = []
        for origin, destination in (
            ("rheuma-podbi", "mhh"),
            ("amedes-georg", "mhh"),
            ("limbach-lehrte", "mhh"),
        ):
            coordinates = [sites[origin], sites[destination]]
            corridor = metric_geometry(LineString(coordinates)).buffer(50)
            motions.append(
                {
                    "origin": origin,
                    "destination": destination,
                    "coordinates": coordinates,
                    "strict": model.check(coordinates),
                    "research": model.check(coordinates, mode="research"),
                    "population_corridor_100m": model.population.query(corridor),
                }
            )
        summary["verification"] = {
            "offline_network_forbidden": True,
            "preparation_and_inspection_s": time.perf_counter() - started,
            "endpoint_states": dict(Counter(e["state"] for e in summary["endpoints"])),
            "motions": motions,
        }
        results.append(summary)
        print(
            json.dumps(
                {
                    "altitude": altitude,
                    "counts": summary["counts"],
                    "terrain_coverage": summary["terrain_coverage"],
                    "verification_s": summary["verification"][
                        "preparation_and_inspection_s"
                    ],
                }
            ),
            flush=True,
        )
        del model
    write_json(
        args.output,
        {"kind": "iteration-008-part2-offline-evidence", "scenarios": results},
    )


if __name__ == "__main__":
    main()
