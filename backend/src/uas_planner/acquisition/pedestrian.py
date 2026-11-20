"""Prepare and serve local, precomputed Hannover pedestrian layers."""

import json
from functools import lru_cache
from math import fsum, isfinite
from pathlib import Path
from tempfile import NamedTemporaryFile

import pyogrio
from pyproj import Transformer
from shapely.geometry import mapping
from shapely.ops import transform

from uas_planner.acquisition.pedestrian_inputs import estimate_departures
from uas_planner.acquisition.study import pbf_tags
from uas_planner.core.experiment import checksum, read_json, safe_file
from uas_planner.core.mid_profiles import (
    DURATION_WEIGHTED_BASE,
    START_WEIGHTED_BASE,
    TAIL_SENSITIVITY_MINUTES,
    WINDOWS,
    expected_minutes,
    source_metadata,
    window_metadata,
)
from uas_planner.core.pedestrian_exposure import (
    ALTERNATE_DECAY_M,
    DESTINATION_LIMIT,
    DISTANCE_DECAY_M,
    MODEL_VERSION,
    SNAP_LIMIT_M,
    WALK_LIMIT_M,
    allocate,
    destination_purposes,
    walking_graph,
)
from uas_planner.core.population_costs import prepare_population_surface

GPKG = "osm/features.gpkg"
MAX_BYTES = 50_000_000


def write_product(path, value):
    """Publish a complete snapshot with one atomic replacement."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, encoding="utf-8", mode="w", delete=False) as stream:
        temp = Path(stream.name)
        try:
            json.dump(value, stream, separators=(",", ":"), allow_nan=False)
            stream.write("\n")
        except BaseException:
            stream.close()
            temp.unlink(missing_ok=True)
            raise
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def product_path(directory):
    directory = Path(directory).resolve()
    root = directory.parent
    path = (root / ".pedestrian-exposure" / (directory.name + ".json")).resolve()
    if not path.is_relative_to(root) or path.is_relative_to(directory):
        raise ValueError("Pedestrian product path must be inside the local data root.")
    return path


def study_osm(directory, manifest):
    """Reuse all roads and destinations already saved in the study, then add POIs."""
    receipts = {record["path"]: record["sha256"] for record in manifest["files"]}
    bounds = tuple(manifest["config"]["bounds"][key] for key in ("west", "south", "east", "north"))
    gpkg = safe_file(directory, GPKG)
    if checksum(gpkg) != receipts.get(GPKG):
        raise ValueError("Saved OSM GeoPackage checksum mismatch.")
    frame = pyogrio.read_dataframe(
        gpkg,
        columns=["element_type", "osm_id", "tags_json"],
        where="tags_json LIKE '%\"highway\"%' OR tags_json LIKE '%\"shop\"%' "
        "OR tags_json LIKE '%\"office\"%' OR tags_json LIKE '%\"amenity\"%' "
        "OR tags_json LIKE '%\"leisure\"%' OR tags_json LIKE '%\"tourism\"%' "
        "OR tags_json LIKE '%\"landuse\"%' OR tags_json LIKE '%\"building\"%'",
    ).to_crs(25832)
    roads = []
    destinations = {}
    for row in frame.itertuples(index=False):
        tags = json.loads(row.tags_json)
        if "highway" in tags:
            roads.append((row.geometry, tags))
        uses = destination_purposes(tags)
        if (
            uses
            and row.geometry is not None
            and row.geometry.is_valid
            and not row.geometry.is_empty
        ):
            destinations[(row.element_type, str(row.osm_id))] = (row.geometry, uses)

    supplemental = 0
    source_kind = "saved_geopackage"
    for raw in manifest.get("osm_raw_paths", []):
        if not raw.endswith(".pbf"):
            continue
        path = safe_file(directory, raw)
        if checksum(path) != receipts.get(raw):
            raise ValueError("Saved OSM PBF checksum mismatch.")
        source_kind = "saved_geopackage_and_pbf"
        for layer, query in (
            (
                "points",
                " OR ".join(
                    f'''other_tags LIKE '%"{key}"=>%' '''
                    for key in ("amenity", "shop", "office", "leisure", "tourism")
                ),
            ),
            (
                "multipolygons",
                " OR ".join(
                    f"{key} IS NOT NULL"
                    for key in ("amenity", "shop", "office", "leisure", "tourism")
                ),
            ),
        ):
            source = pyogrio.read_dataframe(path, layer=layer, bbox=bounds, where=query).to_crs(
                25832
            )
            for _, row in source.iterrows():
                way = row.get("osm_way_id")
                key = (
                    ("node", str(row["osm_id"]))
                    if layer == "points"
                    else ("way", way)
                    if isinstance(way, str) and way
                    else ("relation", str(row["osm_id"]))
                )
                if key in destinations:
                    continue
                uses = destination_purposes(pbf_tags(row))
                geom = row.geometry
                if uses and geom is not None and geom.is_valid and not geom.is_empty:
                    destinations[key] = (geom, uses)
                    supplemental += 1
        if checksum(path) != receipts[raw]:
            raise ValueError("Saved OSM PBF changed during preparation.")
    if checksum(gpkg) != receipts[GPKG]:
        raise ValueError("Saved OSM GeoPackage changed during preparation.")
    provenance = {
        **manifest["sources"]["osm"],
        "input": source_kind,
        "sha256": {
            path: receipts[path]
            for path in (GPKG, *manifest.get("osm_raw_paths", []))
            if path == GPKG or path.endswith(".pbf")
        },
        "supplemental_destinations": supplemental,
        "destination_features": len(destinations),
    }
    return walking_graph(roads), list(destinations.values()), provenance


def prepare_product(directory, workbook, boundaries, *, boundary_release, progress=print):
    directory = Path(directory).resolve()
    study = safe_file(directory, "study.json")
    study_hash = checksum(study)
    manifest = read_json(study)
    if manifest.get("config", {}).get("region_id") != "hannover-lehrte-5km":
        raise ValueError("Pedestrian exposure is prepared for the saved Hannover–Lehrte study.")
    progress("Aggregating the saved GHSL raster on the 150 m grid.")
    population = prepare_population_surface(directory, cell_m=150)
    cells = population.metric_population_cells
    raster = safe_file(directory, population.metadata["source"]["path"])
    progress("Joining the public MiD municipal estimates and BKG boundaries.")
    departures, municipality = estimate_departures(
        population, raster, Path(workbook), Path(boundaries), boundary_release
    )
    progress(
        f"Joined {len(municipality['municipalities'])} municipalities across the saved footprint."
    )
    progress("Reading saved OSM roads and destinations.")
    graph, destinations, osm = study_osm(directory, manifest)
    if not graph or not destinations:
        raise ValueError(
            "The saved OSM sources yielded no usable pedestrian network or destinations."
        )
    progress(f"Allocating walking budgets on {graph.number_of_edges():,} mapped edges.")
    allocations, unavailable, diagnostics = allocate(cells, departures, graph, destinations)
    outdoor, spatial_ledger = allocations[DISTANCE_DECAY_M]
    alt_outdoor, alt_ledger = allocations[ALTERNATE_DECAY_M]
    base_minutes = expected_minutes()
    profile_source = source_metadata()
    reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform
    geometry = []
    for i, (polygon, cell_id, _) in enumerate(cells):
        geometry.append(
            {
                "id": cell_id,
                "geometry": mapping(transform(reverse, polygon)),
                "area_m2": polygon.area,
                "coverage_reason": unavailable.get(i),
            }
        )
    windows = {}
    for key, minutes in base_minutes.items():
        window = window_metadata(key)
        scale = minutes / window["minutes"]
        windows[key] = {
            **window,
            "mean_people": [None if value is None else value * scale for value in outdoor],
            "expected_daily_walking_departures": (
                spatial_ledger["budget"] * profile_source["start_percentages"][key] / 100
            ),
            "mean_outdoor_people_in_region": spatial_ledger["outdoor_in_region"] * scale,
            "ledger": {category: budget * minutes for category, budget in spatial_ledger.items()},
        }
    sensitivity = {
        "open_duration_bin": [
            {
                "minutes": tail,
                "mean_trip_minutes": fsum(alternate.values()),
                "outdoor_mean_people_by_window": {
                    key: spatial_ledger["outdoor_in_region"] * mins / windows[key]["minutes"]
                    for key, mins in alternate.items()
                },
            }
            for tail in TAIL_SENSITIVITY_MINUTES
            for alternate in (expected_minutes(tail),)
        ],
        "start_record_availability": {
            "factor": START_WEIGHTED_BASE / DURATION_WEIGHTED_BASE,
            "basis": "Start-table weighted bases relative to duration table, a sensitivity check for time-record coverage only",
            "outdoor_mean_people_by_window": {
                key: window["mean_outdoor_people_in_region"]
                * START_WEIGHTED_BASE
                / DURATION_WEIGHTED_BASE
                for key, window in windows.items()
            },
        },
        "distance_decay": {
            "alternate_m": ALTERNATE_DECAY_M,
            "outdoor_mean_people_by_window": {
                key: alt_ledger["outdoor_in_region"] * minutes / windows[key]["minutes"]
                for key, minutes in base_minutes.items()
            },
            "total_absolute_change_in_cell_departure_equivalents": fsum(
                abs(first - second)
                for first, second in zip(outdoor, alt_outdoor, strict=True)
                if first is not None and second is not None
            ),
        },
    }
    if checksum(study) != study_hash or checksum(raster) != population.metadata["source"]["sha256"]:
        raise ValueError("Saved study or population input changed during pedestrian preparation.")
    representation = {
        "version": MODEL_VERSION,
        "study_sha256": study_hash,
        "input_kind": "mid-public",
        "source": {
            "profiles": profile_source,
            "ghsl": population.metadata["source"],
            "osm": osm,
        },
        "coverage": {
            **municipality,
            "known_estimate_cells": len(cells) - len(unavailable),
            "unavailable_area_m2": fsum(cells[i][0].area for i in unavailable),
        },
        "allocation": {
            "walk_limit_m": WALK_LIMIT_M,
            "snap_limit_m": SNAP_LIMIT_M,
            "destination_limit": DESTINATION_LIMIT,
            "distance_decay_m": DISTANCE_DECAY_M,
            "spatial_rule": "Fixed paths and travel minutes in proportion to segment length",
            "mean_trip_minutes": fsum(base_minutes.values()),
            "daily_walking_departures": spatial_ledger["budget"],
            **diagnostics,
        },
        "sensitivity": sensitivity,
        "display_max_people": max(
            (
                value
                for window in windows.values()
                for value in window["mean_people"]
                if value is not None
            ),
            default=0,
        ),
        "cells": geometry,
        "windows": windows,
    }
    path = product_path(directory)
    write_product(path, representation)
    return {
        "path": str(path),
        "input_kind": representation["input_kind"],
        "cell_count": len(cells),
        "shared_display_max_people": representation["display_max_people"],
        "coverage": representation["coverage"],
        "allocation": representation["allocation"],
        "sensitivity": sensitivity,
        "windows": {
            key: {name: value for name, value in window.items() if name != "mean_people"}
            for key, window in windows.items()
        },
    }


@lru_cache(maxsize=2)
def _load_product(path, metadata_key):
    return read_json(path)


class PedestrianProductUnavailable(ValueError):
    """The requested study has no current public exposure product."""


def read_pedestrian_product(directory):
    """Share the same saved snapshot and identity between display and routing."""
    path = product_path(directory)
    if not path.is_file():
        raise PedestrianProductUnavailable("No prepared pedestrian layer for this study.")
    try:
        stat = path.stat()
    except FileNotFoundError as exc:
        raise PedestrianProductUnavailable("No prepared pedestrian layer for this study.") from exc
    if stat.st_size > MAX_BYTES:
        raise ValueError("Pedestrian product exceeds the supported size.")
    identity = (stat.st_mtime_ns, stat.st_size)
    snapshot = _load_product(path, identity)
    if snapshot["version"] != MODEL_VERSION:
        raise PedestrianProductUnavailable("Prepare this study with the current pedestrian model.")
    if snapshot["study_sha256"] != checksum(safe_file(directory, "study.json")):
        raise PedestrianProductUnavailable("Study inputs changed. Prepare the layer again.")
    maximum = snapshot["display_max_people"]
    if snapshot["input_kind"] != "mid-public" or not isfinite(maximum) or maximum < 0:
        raise ValueError("Invalid pedestrian product metadata.")
    return snapshot, f"{identity[0]}:{identity[1]}"


def display_product(directory, scenario):
    """Serve one precomputed window from the product pinned to this study."""
    if scenario not in WINDOWS:
        raise ValueError("Unsupported pedestrian time window.")
    base = {
        "window": window_metadata(scenario),
        "layer": {"type": "FeatureCollection", "features": []},
    }
    try:
        snapshot, identity = read_pedestrian_product(directory)
    except PedestrianProductUnavailable as exc:
        return {**base, "state": "unavailable", "reason": str(exc)}
    window = snapshot["windows"][scenario]
    features = []
    for cell, people in zip(snapshot["cells"], window["mean_people"], strict=True):
        area = cell["area_m2"]
        features.append(
            {
                "type": "Feature",
                "id": cell["id"],
                "geometry": cell["geometry"],
                "properties": {
                    "layer_kind": "pedestrian_exposure",
                    "state": "unavailable" if people is None else "known",
                    "coverage_reason": cell["coverage_reason"],
                    "mean_people": people,
                    "area_m2": area,
                    "people_per_km2": None if people is None else people * 1_000_000 / area,
                },
            }
        )
    return {
        **base,
        "state": "ready",
        "input_kind": snapshot["input_kind"],
        "display_max_people": snapshot["display_max_people"],
        "model_version": MODEL_VERSION,
        "identity": f"{identity}:{scenario}",
        "layer": {"type": "FeatureCollection", "features": features},
    }
