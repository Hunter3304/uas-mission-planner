"""Explicit bounded native terrain acquisition, separate from immutable studies."""

import math
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from uuid import uuid4

import rasterio
from pyproj import Transformer
from shapely.geometry import box

from uas_planner.acquisition.external import TERRAIN, download
from uas_planner.acquisition.study import finite_number
from uas_planner.core.experiment import checksum, read_json, safe_file, write_json

MAX_TILES = 144
TILE_SIDE_M = 2000


def terrain_tiles(bounds):
    """Partition a declared WGS84 extent into bounded native 2 km requests."""
    if len(bounds) != 4:
        raise ValueError("Expected west south east north bounds.")
    west, south, east, north = bounds
    for value in bounds:
        finite_number(value, -180, 180, "Terrain bounds")
    if not 9 <= west < east <= 11 or not 52 <= south < north <= 53:
        raise ValueError("Terrain acquisition is scoped to the supported study area.")
    extent = Transformer.from_crs(4326, 25832, always_xy=True).transform_bounds(
        *bounds, densify_pts=21
    )
    x0, y0 = [math.floor(v / TILE_SIDE_M) * TILE_SIDE_M for v in extent[:2]]
    x1, y1 = [math.ceil(v / TILE_SIDE_M) * TILE_SIDE_M for v in extent[2:]]
    count = ((x1 - x0) // TILE_SIDE_M) * ((y1 - y0) // TILE_SIDE_M)
    if count > MAX_TILES:
        raise ValueError(
            f"Terrain request exceeds {MAX_TILES} tiles; acquire explicit bounded subregions separately."
        )
    return [
        [x, y, x + TILE_SIDE_M, y + TILE_SIDE_M]
        for y in range(y0, y1, TILE_SIDE_M)
        for x in range(x0, x1, TILE_SIDE_M)
    ]


def acquire_terrain(bounds, output, *, resume=False, workers=1):
    """Preserve original WCS bytes and verified receipts, with explicit resume."""
    planned = terrain_tiles(bounds)
    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 3:
        raise ValueError("Terrain workers must be an integer between 1 and 3.")
    root = Path(output)
    progress = {
        "schema_version": 1,
        "kind": "bounded-native-terrain",
        "bounds_wgs84": list(bounds),
        "planned_bounds": planned,
        "tiles": [],
        "source": TERRAIN,
        "vertical_datum": "DHHN2016_NHN",
        "units": "metres",
        "product": "LGLN DGM1",
        "native_resolution_m": 1,
        "vertical_reference_policy": "NHN is not automatically equivalent to DIPUL MSL",
        "metadata_evidence": "https://www.lgln.niedersachsen.de/download/207140/Kundeninformation_1_2024.pdf",
    }
    if resume:
        if (root / "terrain.json").exists():
            raise ValueError("Completed terrain snapshots cannot be resumed.")
        saved = read_json(safe_file(root, "terrain-progress.json"))
        if saved["bounds_wgs84"] != list(bounds) or saved["planned_bounds"] != planned:
            raise ValueError("Terrain resume scope differs from the original request.")
        progress = saved
        for tile in progress["tiles"]:
            if checksum(safe_file(root, tile["path"])) != tile["sha256"]:
                raise ValueError("Terrain resume checksum mismatch.")
    else:
        root.mkdir(parents=True, exist_ok=False)
        write_json(root / "terrain-progress.json", progress)

    def preserve_unreceipted(target):
        if not target.exists():
            return
        # Explicit resume archives our unreceipted payload instead of overwriting it.
        if not resume:
            raise ValueError(f"Unreceipted terrain payload {target.name}.")
        archive = root / f"{target.name}.unreceipted-{uuid4().hex}"
        resolved_root = root.resolve()
        if not target.resolve().is_relative_to(
            resolved_root
        ) or not archive.resolve().is_relative_to(resolved_root):
            raise ValueError("Terrain recovery path outside the snapshot directory.")
        target.rename(archive)

    for name, request in (
        ("capabilities.xml", {"service": "WCS", "request": "GetCapabilities"}),
        (
            "description.xml",
            {
                "service": "WCS",
                "version": "2.0.1",
                "request": "DescribeCoverage",
                "coverageId": "ni_dgm1",
            },
        ),
    ):
        if name in progress.get("metadata", {}):
            if checksum(safe_file(root, name)) != progress["metadata"][name]["sha256"]:
                raise ValueError("Terrain metadata checksum mismatch.")
            continue
        target = root / name
        preserve_unreceipted(target)
        receipt = download(TERRAIN, target, request)
        progress.setdefault("metadata", {})[name] = {**receipt, "sha256": checksum(target)}
        write_json(root / "terrain-progress.json", progress)
    existing = {tuple(t["requested_bounds"]) for t in progress["tiles"]}
    pending = [extent for extent in planned if tuple(extent) not in existing]

    def fetch_tile(extent):
        west, south, east, north = extent
        name = f"dgm1-{west}-{south}.tif"
        target = root / name
        preserve_unreceipted(target)
        params = [
            ("service", "WCS"),
            ("version", "2.0.1"),
            ("request", "GetCoverage"),
            ("coverageId", "ni_dgm1"),
            ("format", "image/tiff"),
            ("subset", f"x({west},{east})"),
            ("subset", f"y({south},{north})"),
        ]
        receipt = download(TERRAIN, target, params)
        with rasterio.open(target) as src:
            if (
                src.crs.to_epsg() != 25832
                or src.res != (1, 1)
                or src.count != 1
                or src.transform.b
                or src.transform.d
                or src.width > east - west + 2
                or src.height > north - south + 2
                or not box(*src.bounds).covers(box(west, south, east, north))
            ):
                raise ValueError("Unexpected native terrain response grid/coverage.")
            tile_bounds = list(src.bounds)
        return {
            "path": name,
            "sha256": checksum(target),
            "bounds": tile_bounds,
            "requested_bounds": [west, south, east, north],
            "request": params,
            **receipt,
        }

    failures = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetch_tile, extent) for extent in pending]
        for future in as_completed(futures):
            try:
                progress["tiles"].append(future.result())
                progress["tiles"].sort(key=lambda tile: tile["requested_bounds"])
                write_json(root / "terrain-progress.json", progress)
                print(
                    f"Terrain: {len(progress['tiles'])}/{len(planned)} verified tiles",
                    file=sys.stderr,
                    flush=True,
                )
            except Exception as exc:
                failures.append(exc)
                for queued in futures:
                    queued.cancel()
    if failures:
        raise ValueError(
            f"Terrain acquisition incomplete; verified receipts preserved: {failures[0]}"
        ) from failures[0]
    from uas_planner.core.regional import TerrainSupport

    write_json(root / "terrain.json", progress)
    try:
        TerrainSupport(root)
    except Exception:
        (root / "terrain.json").unlink()
        raise
    return progress
