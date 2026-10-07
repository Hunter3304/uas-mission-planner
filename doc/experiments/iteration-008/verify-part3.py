"""Offline Part 3 real-source preflight evidence, separate from Part 5 experiments."""

import argparse
import json
from pathlib import Path
from time import perf_counter

import requests
from uas_planner.core.experiment import read_json
from uas_planner.core.regional_routing import RegionalPlanner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)

    def forbid(*args, **kwargs):
        raise AssertionError(
            "Network forbidden during offline regional routing verification."
        )

    requests.sessions.Session.request = forbid
    runs = []
    for altitude in (100, 120):
        started = perf_counter()
        planner = RegionalPlanner(
            "data/hannover-part1-v4",
            {
                **read_json("doc/experiments/iteration-008/hannover-scenario.json"),
                "agl_m": altitude,
            },
            terrain_directory="data/hannover-part2-terrain-v1",
        )
        source_ms = (perf_counter() - started) * 1000
        for mode in ("strict", "research"):
            for algorithm in ("astar", "dijkstra", "abitstar"):
                for objective in ("risk", "distance"):
                    result = planner.plan(
                        "rheuma-podbi",
                        "mhh",
                        algorithm=algorithm,
                        objective=objective,
                        planning_mode=mode,
                    )
                    assert result["status"] == "unresolved_input"
                    assert result["planner_ms"] == 0 and result["geometry"] is None
                    runs.append(
                        {
                            "altitude_m": altitude,
                            "mode": mode,
                            "algorithm": algorithm,
                            "objective": objective,
                            "status": result["status"],
                            "source_preparation_ms": source_ms,
                            "endpoint_diagnostics": result["endpoint_diagnostics"],
                            "provenance": result["provenance"],
                        }
                    )
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(
            {
                "scope": "Part 3 integration preflight; no flight experiment or successful real route claimed",
                "offline": True,
                "runs": runs,
            },
            stream,
            indent=2,
            allow_nan=False,
        )
        stream.write("\n")
    print(
        json.dumps(
            {
                "runs": len(runs),
                "outcomes": "all unresolved_input; search not started",
                "output": str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
