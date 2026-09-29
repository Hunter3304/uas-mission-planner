"""Offline, source-native external-layer inspection. No routing or web dependencies."""

import hashlib
import json
from datetime import datetime
from math import isfinite
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.windows import Window, from_bounds
from shapely.geometry import Point, box, mapping, shape
from shapely.ops import transform

from uas_planner.core.area import BoundingBox

MAX_DISPLAY_CELLS = 10000


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def checksum(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_config(config):
    area = BoundingBox(**config["bounds"])
    if config["scenario"] not in ("civil", "BOS"):
        raise ValueError("Scenario must be civil or BOS.")
    agl = config["agl_m"]
    if isinstance(agl, bool) or not isinstance(agl, (int, float)) or not isfinite(agl) or agl < 0:
        raise ValueError("AGL must be a finite nonnegative number of metres.")
    for key in ("start", "end"):
        lon, lat = config[key]
        if not (isfinite(lon) and isfinite(lat) and box(*area.as_tuple()).covers(Point(lon, lat))):
            raise ValueError(f"{key} must lie inside the experiment bounds.")
    zone = ZoneInfo(config["timezone"])
    times = [datetime.fromisoformat(config[key]) for key in ("mission_start", "mission_end")]
    for time in times:
        if time.tzinfo is None or time.utcoffset() != time.astimezone(zone).utcoffset():
            raise ValueError("Mission times require offsets matching the specified timezone.")
    if not 0 < (times[1] - times[0]).total_seconds() <= 86400:
        raise ValueError("Mission interval must be positive and at most 24 hours.")
    if config["ghsl_epoch"] not in (2020, 2025):
        raise ValueError("Choose GHSL 2020 estimate or 2025 projection.")
    if config["temporary_restrictions"] != "unverified":
        raise ValueError("This adapter cannot verify temporary-restriction coverage.")
    return area


def safe_file(directory, relative):
    root = Path(directory).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or path == root or not path.is_file():
        raise ValueError("Experiment payload missing or outside its directory.")
    return path


def raster_metadata(path, kind):
    with rasterio.open(path) as src:
        expected = CRS.from_user_input("ESRI:54009" if kind == "ghsl" else "EPSG:25832")
        if src.crs is None or not CRS(src.crs).equals(expected):
            raise ValueError(f"Unexpected {kind} CRS.")
        spacing = 100 if kind == "ghsl" else 1
        if src.count != 1 or src.res != (spacing, spacing) or src.transform.b or src.transform.d:
            raise ValueError(f"Unexpected {kind} native grid; resampling is not accepted.")
        if src.nodata is None and kind == "ghsl":
            raise ValueError(f"Missing {kind} NoData declaration.")
        return {
            "crs": expected.to_string(),
            "crs_wkt": src.crs.to_wkt(),
            "resolution": list(src.res),
            "nodata": None if src.nodata is None else float(src.nodata),
            "effective_nodata": float(src.nodata) if src.nodata is not None else -9999.0,
            "nodata_basis": "GeoTIFF"
            if src.nodata is not None
            else "LGLN DGM product specification (-9999)",
            "bounds": list(src.bounds),
            "width": src.width,
            "height": src.height,
            "dtype": src.dtypes[0],
            "transform": list(src.transform)[:6],
        }


def native_window(src, area):
    converter = Transformer.from_crs(4326, src.crs, always_xy=True)
    bounds = converter.transform_bounds(*area.as_tuple(), densify_pts=21)
    window = from_bounds(*bounds, transform=src.transform)
    left, top = int(np.floor(window.col_off)), int(np.floor(window.row_off))
    right = int(np.ceil(window.col_off + window.width))
    bottom = int(np.ceil(window.row_off + window.height))
    return Window(left, top, right - left, bottom - top)


def validate_zones(collection, area):
    if collection.get("type") != "FeatureCollection" or not isinstance(
        collection.get("features"), list
    ):
        raise ValueError("DIPUL response must be a GeoJSON FeatureCollection.")
    crs = (collection.get("crs") or {}).get("properties", {}).get("name", "")
    if crs and crs not in (
        "urn:ogc:def:crs:OGC:1.3:CRS84",
        "urn:ogc:def:crs:EPSG::4326",
        "EPSG:4326",
    ):
        raise ValueError("DIPUL response must use longitude/latitude WGS84.")
    features = collection["features"]
    matched = collection.get("numberMatched", collection.get("totalFeatures"))
    if matched is None or str(matched) == "unknown" or int(matched) != len(features):
        raise ValueError(
            "DIPUL response completeness cannot be verified (truncated or missing count)."
        )
    if collection.get("numberReturned", len(features)) != len(features):
        raise ValueError("DIPUL returned-count mismatch.")
    ids = set()
    query = box(*area.as_tuple())
    for feature in features:
        identity = feature.get("id")
        if not isinstance(identity, (str, int)) or str(identity) in ids:
            raise ValueError("Missing or duplicate DIPUL source ID.")
        ids.add(str(identity))
        if not isinstance(feature.get("properties"), dict):
            raise ValueError("DIPUL properties must be preserved as an object.")
        geometry = shape(feature["geometry"])
        if (
            geometry.is_empty
            or not geometry.is_valid
            or geometry.geom_type not in ("Polygon", "MultiPolygon")
        ):
            raise ValueError("Invalid or unsupported DIPUL zone geometry.")
        if not geometry.intersects(query):
            raise ValueError("DIPUL geometry outside query; check axis order.")
        if not box(-180, -90, 180, 90).covers(geometry):
            raise ValueError("DIPUL coordinate range mismatch.")
    return features


def load_experiment(directory):
    """Verify every original payload before returning an offline snapshot."""
    manifest = read_json(safe_file(directory, "experiment.json"))
    if manifest["schema_version"] != 1:
        raise ValueError("Unsupported experiment schema.")
    area = validate_config(manifest["config"])
    for entry in manifest["files"]:
        if checksum(safe_file(directory, entry["path"])) != entry["sha256"]:
            raise ValueError(f"Checksum mismatch: {entry['path']}")
    checked = {entry["path"] for entry in manifest["files"]}
    for kind in ("ghsl", "terrain"):
        source = manifest["sources"][kind]
        if source["path"] not in checked:
            raise ValueError("Raster is not in the integrity manifest.")
        actual = raster_metadata(safe_file(directory, source["path"]), kind)
        if actual != source["raster"]:
            raise ValueError("Raster metadata mismatch.")
        with rasterio.open(safe_file(directory, source["path"])) as src:
            window = native_window(src, area)
            if (
                window.col_off < 0
                or window.row_off < 0
                or window.col_off + window.width > src.width
                or window.row_off + window.height > src.height
            ):
                raise ValueError(f"{kind} raster does not cover the experiment bounds.")
    for response in manifest["sources"]["dipul"]["responses"]:
        if response["path"] not in checked:
            raise ValueError("DIPUL response is not in the integrity manifest.")
        validate_zones(read_json(safe_file(directory, response["path"])), area)
    return manifest


def population_layer(directory, manifest):
    """Native cell footprints, not a resampled population surface or planning grid."""
    area = validate_config(manifest["config"])
    source = manifest["sources"]["ghsl"]
    features = []
    with rasterio.open(safe_file(directory, source["path"])) as src:
        window = native_window(src, area)
        if window.width * window.height > MAX_DISPLAY_CELLS:
            raise ValueError("Population display exceeds native-cell limit.")
        values = src.read(1, window=window, masked=True)
        to_wgs = Transformer.from_crs(src.crs, 4326, always_xy=True).transform
        query = box(*area.as_tuple())
        for row in range(values.shape[0]):
            for col in range(values.shape[1]):
                r, c = row + int(window.row_off), col + int(window.col_off)
                x, y = src.transform @ (c, r)
                polygon = transform(to_wgs, box(x, y - 100, x + 100, y))
                if not polygon.intersects(query):
                    continue
                raw = values[row, col]
                value = None if np.ma.is_masked(raw) or not np.isfinite(raw) else float(raw)
                if value is not None and value < 0:
                    raise ValueError("Negative GHSL population outside declared NoData.")
                features.append(
                    {
                        "type": "Feature",
                        "id": f"{source['source_id']}:x{x:g}:y{y:g}",
                        "geometry": mapping(polygon),
                        "properties": {
                            "people_per_cell": value,
                            "people_per_km2": None if value is None else value * 100,
                            "status": "unknown" if value is None else "known",
                            "support_m": 100,
                            "epoch": manifest["config"]["ghsl_epoch"],
                        },
                    }
                )
    return {"type": "FeatureCollection", "features": features}


def zone_layer(directory, manifest):
    result = []
    area = validate_config(manifest["config"])
    for response in manifest["sources"]["dipul"]["responses"]:
        for feature in validate_zones(read_json(safe_file(directory, response["path"])), area):
            result.append(
                {
                    **feature,
                    "source_layer": response["type_name"],
                    "inspection_status": "applicability_unresolved",
                }
            )
    return {"type": "FeatureCollection", "features": result}


def sample_raster(directory, source, lon, lat):
    with rasterio.open(safe_file(directory, source["path"])) as src:
        x, y = Transformer.from_crs(4326, src.crs, always_xy=True).transform(lon, lat)
        row, col = src.index(x, y)
        if not (0 <= row < src.height and 0 <= col < src.width):
            return None
        value = src.read(1, window=Window(col, row, 1, 1), masked=True)[0, 0]
        return (
            None
            if np.ma.is_masked(value)
            or not np.isfinite(value)
            or value == source["raster"]["effective_nodata"]
            else float(value)
        )


def inspect_location(directory, manifest, lon, lat):
    area = validate_config(manifest["config"])
    if not (isfinite(lon) and isfinite(lat) and box(*area.as_tuple()).covers(Point(lon, lat))):
        raise ValueError("Inspection location must lie inside the experiment bounds.")
    ground = sample_raster(directory, manifest["sources"]["terrain"], lon, lat)
    population = sample_raster(directory, manifest["sources"]["ghsl"], lon, lat)
    if population is not None and population < 0:
        raise ValueError("Negative GHSL population outside declared NoData.")
    agl = manifest["config"]["agl_m"]
    return {
        "longitude": lon,
        "latitude": lat,
        "agl_m": agl,
        "terrain_m": ground,
        "aircraft_altitude_m": None if ground is None else ground + agl,
        "vertical_datum": manifest["sources"]["terrain"]["vertical_datum"],
        "height_status": "unknown" if ground is None else "known",
        "people_per_cell": population,
        "population_status": "unknown" if population is None else "known",
        "zones": [
            f
            for f in zone_layer(directory, manifest)["features"]
            if shape(f["geometry"]).covers(Point(lon, lat))
        ],
        "applicability": "unresolved",
        "temporary_restrictions": "unverified",
    }
