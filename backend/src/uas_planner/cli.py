"""Command-line workflow for acquisition and network-free dataset inspection."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from uas_planner.core.area import BoundingBox
from uas_planner.storage.dataset import load_dataset, save_dataset


def parser():
    result = argparse.ArgumentParser(description="Small-area OSM dataset acquisition")
    commands = result.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch", help="Acquire, save, and verify a new dataset")
    for name in ("west", "south", "east", "north"):
        fetch.add_argument(f"--{name}", type=float, required=True)
    fetch.add_argument("--output", type=Path, required=True, help="New dataset directory")
    fetch.add_argument("--cache", type=Path, default=Path(".cache/osmnx"))
    inspect = commands.add_parser(
        "inspect", help="Reload and verify a local dataset without network"
    )
    inspect.add_argument("directory", type=Path)
    sample = commands.add_parser("sample", help="Create a synthetic offline demonstration dataset")
    sample.add_argument("--output", type=Path, required=True, help="New dataset directory")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "fetch":
            # Import the network adapter only for acquisition, never for inspect.
            from uas_planner.acquisition.osm import TAGS, acquire

            area = BoundingBox(args.west, args.south, args.east, args.north)
            if args.output.exists():
                raise FileExistsError(f"Output already exists: {args.output}")
            started = datetime.now(timezone.utc).isoformat()
            frame = acquire(area, args.cache)
            frame.attrs["acquisition_started_at_utc"] = started
            frame.attrs["acquisition_finished_at_utc"] = datetime.now(timezone.utc).isoformat()
            save_dataset(frame, args.output, area, TAGS)
            directory = args.output
        elif args.command == "sample":
            from uas_planner.sample import create_sample

            create_sample(args.output)
            directory = args.output
        else:
            directory = args.directory
        frame, metadata = load_dataset(directory)
        summary = {
            "dataset": str(directory.resolve()),
            "feature_count": len(frame),
            "crs": frame.crs.to_string(),
            "feature_bounds": frame.total_bounds.tolist() if not frame.empty else None,
            "geometry_counts": frame.geom_type.value_counts().to_dict(),
            "query_bounds": metadata["query_bounds"],
            "sha256": metadata["sha256"],
            "verified": True,
            "synthetic": metadata.get("synthetic", False),
        }
        print(json.dumps(summary, indent=2, allow_nan=False))
        return 0
    except KeyboardInterrupt:
        print(
            "Cancelled. No completed dataset is guaranteed; check the output directory.",
            file=sys.stderr,
        )
        return 130
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
