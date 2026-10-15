"""Verify saved Part 5 records and produce compact, version-controlled evidence."""

import argparse
import json
from collections import Counter
from math import isclose
from pathlib import Path

from uas_planner.core.experiment import checksum, read_json
from uas_planner.core.static_experiments import summarize


def verify_records(records):
    for record in records:
        result = record["result"]
        if result["status"] != "success":
            if result["geometry"] is not None or result["length_m"] is not None:
                raise AssertionError(
                    "Failure record contains a successful-looking route."
                )
        elif not result.get("independent_validation"):
            raise AssertionError("Successful route lacks independent core validation.")
        if record["experiment_validation"]["state"] == "failed":
            raise AssertionError("Failed experiment route validation.")
        if (
            result["mission"]["speed_m_s"]
            != result["provenance"]["scenario"]["speed_m_s"]
        ):
            raise AssertionError("Mission/provenance speed mismatch.")
    checks = []
    for fixture in ("risk-detour", "diagonal", "boundary-detour"):
        for algorithm in ("astar", "dijkstra"):
            for objective in ("risk", "distance"):
                selected = {
                    variant: next(
                        r["result"]
                        for r in records
                        if r["label"] == f"synthetic-{fixture}-{variant}"
                        and r["cache_state"] == "fresh_prepared_batch"
                        and r["result"]["algorithm"] == algorithm
                        and r["result"]["objective"] == objective
                    )
                    for variant in ("base", "speed-25", "speed-35", "altitude-120")
                }
                base = selected["base"]
                for result in selected.values():
                    if (
                        result["status"] != base["status"]
                        or result["geometry"] != base["geometry"]
                    ):
                        raise AssertionError(
                            "Speed/altitude changes altered fixed synthetic graph."
                        )
                    if result["status"] == "success":
                        if not isclose(
                            result["objective_cost"], base["objective_cost"]
                        ):
                            raise AssertionError("Speed altered graph objective.")
                        if not isclose(
                            result["cruise_time_s"],
                            result["length_m"] / result["mission"]["speed_m_s"],
                        ):
                            raise AssertionError("Wrong cruise-time estimate.")
                checks.append(
                    {
                        "fixture": fixture,
                        "algorithm": algorithm,
                        "objective": objective,
                        "state": "passed",
                        "base_status": base["status"],
                    }
                )
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--study", type=Path, default=Path("data/hannover-part1-v4"))
    parser.add_argument(
        "--terrain", type=Path, default=Path("data/hannover-part2-terrain-v1")
    )
    parser.add_argument(
        "--scenario",
        type=Path,
        default=Path("doc/experiments/iteration-008/hannover-scenario.json"),
    )
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    report = read_json(args.input / "summary.json")
    if checksum(args.input / "runs.json") != report["runs_sha256"]:
        raise ValueError("Run records changed since experiment completion.")
    records = read_json(args.input / "runs.json")
    observed = {"scenario": checksum(args.scenario)}
    if "study" in report["input_manifest_sha256"]:
        observed.update(
            study=checksum(args.study / "study.json"),
            terrain=checksum(args.terrain / "terrain.json"),
        )
    if observed != report["input_manifest_sha256"]:
        raise ValueError("Input manifests changed since the experiment began.")
    report["input_manifest_reverification"] = "passed"
    checks = verify_records(records)
    report["summaries"] = summarize(records)
    report["speed_and_fixed_synthetic_altitude_checks"] = checks
    report["real_outcomes"] = dict(
        Counter(
            r["result"]["status"] for r in records if r["label"].startswith("real-")
        )
    )
    report["synthetic_outcomes"] = dict(
        Counter(
            r["result"]["status"]
            for r in records
            if r["label"].startswith("synthetic-")
        )
    )
    report["full_records_local_path"] = str(args.input / "runs.json")
    report["representative_real_runs"] = [
        {
            "label": r["label"],
            "pair": r["pair"],
            "result": {k: v for k, v in r["result"].items() if k != "provenance"},
            "provenance": {
                k: v for k, v in r["result"]["provenance"].items() if k != "diagnostics"
            },
        }
        for r in records
        if r["label"] in ("real-100m", "real-120m")
        and r["cache_state"] == "fresh_prepared_batch"
        and r["result"]["algorithm"] == "astar"
        and r["result"]["objective"] == "risk"
    ]
    report["research_preflight"] = []
    for path in sorted(args.input.glob("research-*.json")):
        result = read_json(path)
        report["research_preflight"].append(
            {
                "file": path.name,
                "sha256": checksum(path),
                "status": result["status"],
                "mission": result["mission"],
                "planner_ms": result["planner_ms"],
            }
        )
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                "records": len(records),
                "real": report["real_outcomes"],
                "synthetic": report["synthetic_outcomes"],
                "output": str(args.output),
            }
        )
    )


if __name__ == "__main__":
    main()
