"""Command-line workflow for acquisition and network-free dataset inspection."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from uas_planner import __version__
from uas_planner.core.area import BoundingBox
from uas_planner.storage.dataset import load_dataset, save_dataset


def parser():
    result = argparse.ArgumentParser(description="Small-area OSM dataset acquisition")
    result.add_argument("--version", action="version", version=f"uas-planner {__version__}")
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
    experiment = commands.add_parser(
        "experiment-fetch", help="Acquire a new bounded external-layer experiment"
    )
    experiment.add_argument(
        "--resume",
        action="store_true",
        help="Explicitly continue a verified incomplete acquisition",
    )
    experiment.add_argument("--config", type=Path, required=True)
    experiment.add_argument("--output", type=Path, required=True)
    external = commands.add_parser("experiment-inspect", help="Verify external payloads offline")
    external.add_argument("directory", type=Path)
    external.add_argument("--longitude", type=float)
    external.add_argument("--latitude", type=float)
    attach = commands.add_parser(
        "experiment-add-osm", help="Copy a verified matching OSM snapshot into an experiment"
    )
    attach.add_argument("directory", type=Path)
    attach.add_argument("--dataset", type=Path, required=True)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command.startswith("experiment-"):
            from uas_planner.core.experiment import inspect_location, load_experiment, read_json

            if args.command == "experiment-add-osm":
                import shutil

                manifest = load_experiment(args.directory)
                _, osm_metadata = load_dataset(args.dataset)
                if osm_metadata["query_bounds"] != manifest["config"]["bounds"]:
                    raise ValueError("OSM and experiment bounds must match exactly.")
                target = args.directory / "osm"
                target.mkdir(exist_ok=False)
                for name in ("features.gpkg", "metadata.json"):
                    shutil.copy2(args.dataset / name, target / name)
                load_dataset(target)
            elif args.command == "experiment-fetch":
                from uas_planner.acquisition.external import acquire_experiment

                manifest = acquire_experiment(
                    read_json(args.config), args.output, resume=args.resume
                )
            else:
                manifest = load_experiment(args.directory)
                if (args.longitude is None) != (args.latitude is None):
                    raise ValueError("Supply both longitude and latitude.")
                if args.longitude is not None:
                    manifest = inspect_location(
                        args.directory, manifest, args.longitude, args.latitude
                    )
            print(json.dumps(manifest, indent=2, allow_nan=False))
            return 0
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
