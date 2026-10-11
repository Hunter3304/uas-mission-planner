"""Real NHN + AGL engineering comparison, with original datum preserved."""

import argparse
import json
from pathlib import Path

from uas_planner.core.regional import RegionalConstraints


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a new output file.")
    root = Path(__file__).resolve().parents[3]
    scenario = {
        "agl_m": 100,
        "speed_m_s": 30,
        "scenario": "civil",
        "timezone": "Europe/Berlin",
        "mission_start": "2026-10-07T10:00:00+02:00",
        "mission_end": "2026-10-07T10:15:00+02:00",
        "research_geometry": "derived",
        "research_height_m": 30,
        "vertical_reference_policy": "nhn_as_msl_assumption",
        "nhn_msl_offset_m": 0,
        "nhn_msl_uncertainty_m": 0,
        "zone_assessments": {},
    }
    model = RegionalConstraints(
        root / "data/hannover-part1-v4",
        scenario,
        terrain_directory=root / "data/hannover-part2-terrain-v1",
    )
    sites = {s["id"]: s for s in model.manifest["config"]["locations"]}
    points = [
        [sites[name]["longitude"], sites[name]["latitude"]]
        for name in ("rheuma-podbi", "mhh")
    ]
    rows = []
    try:
        for name, coordinates in [
            ("origin", [points[0]]),
            ("destination", [points[1]]),
            ("complete_direct_motion", points),
        ]:
            for mode in ("strict", "conservative", "research"):
                report = model.check(coordinates, mode=mode)
                comparisons = [
                    {
                        k: zone[k]
                        for k in (
                            "source",
                            "state",
                            "vertical_relation",
                            "reason",
                            "zone_msl_bounds_m",
                            "aircraft_comparison_bounds_m",
                            "vertical_reference_assumption",
                        )
                        if k in zone
                    }
                    for zone in report["zones"]
                    if zone["source"] == "dipul:kontrollzonen/kontrollzonen.57"
                ]
                if mode != "strict":
                    assert (
                        comparisons and comparisons[0]["vertical_relation"] == "overlap"
                    )
                    assert report["terrain"]["vertical_datum"] == "DHHN2016_NHN"
                elif comparisons:
                    assert "aircraft_comparison_bounds_m" not in comparisons[0]
                rows.append(
                    {
                        "query": name,
                        "mode": mode,
                        "state": report["state"],
                        "terrain": report["terrain"],
                        "control_zone_comparison": comparisons,
                        "blocked": report["blocked"],
                    }
                )
        result = {
            "scenario": scenario,
            "provenance": model.provenance,
            "runs": rows,
            "interpretation": "Engineering zero-offset/zero-uncertainty comparison; overlap does not grant permission.",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
        for row in rows:
            if row["mode"] == "conservative":
                print(
                    json.dumps(
                        {
                            "query": row["query"],
                            "state": row["state"],
                            "comparison": row["control_zone_comparison"],
                        }
                    ),
                    flush=True,
                )
    finally:
        model.terrain.close()


if __name__ == "__main__":
    main()
