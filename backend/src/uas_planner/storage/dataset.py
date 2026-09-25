"""Versioned GeoPackage datasets with a JSON manifest and integrity checks."""

import hashlib
import json
import math
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import geopandas as gpd
import pandas as pd

from uas_planner.core.area import BoundingBox

IDENTITY = ["element_type", "osm_id"]


def _json_value(value):
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if value is None or value is pd.NA:
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"Unsupported tag value type: {type(value).__name__}")


def checksum(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save_dataset(
    frame: gpd.GeoDataFrame,
    directory: Path,
    area: BoundingBox,
    tags: dict,
    *,
    synthetic: bool = False,
) -> dict:
    """Create a new dataset; manifest written last marks successful completion.

    On a write failure a partial directory may remain for diagnosis. It will not
    load as a valid dataset and is never silently overwritten on a retry.
    """
    directory = Path(directory)
    if frame.crs is None:
        raise ValueError("Dataset must have a CRS.")
    if not set(IDENTITY).issubset(frame.columns):
        raise ValueError("Dataset must have OSM element_type and osm_id columns.")
    if frame[IDENTITY].isna().any().any() or frame.duplicated(IDENTITY).any():
        raise ValueError("OSM identities must be non-null and unique.")
    if frame.geometry.isna().any() or frame.geometry.is_empty.any():
        raise ValueError("Dataset contains missing or empty geometries.")
    frame = frame.to_crs(4326)
    tag_columns = [name for name in frame.columns if name not in [*IDENTITY, frame.geometry.name]]
    rows = [
        json.dumps({name: _json_value(row[name]) for name in tag_columns}, allow_nan=False)
        for _, row in frame.iterrows()
    ]
    output = frame[IDENTITY + [frame.geometry.name]].copy()
    output["tags_json"] = rows
    directory.mkdir(parents=True, exist_ok=False)
    path = directory / "features.gpkg"
    output.to_file(path, layer="features", driver="GPKG", engine="pyogrio", index=False)
    metadata = {
        "schema_version": 1,
        "source": "OpenStreetMap via OSMnx/Overpass",
        "attribution": "© OpenStreetMap contributors",
        "license_url": "https://www.openstreetmap.org/copyright",
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
        "acquisition_started_at_utc": frame.attrs.get("acquisition_started_at_utc"),
        "acquisition_finished_at_utc": frame.attrs.get("acquisition_finished_at_utc"),
        "cache_policy": "OSMnx cache enabled; acquisition time is not the source edit time.",
        "query_bounds": asdict(area),
        "query_area_km2": area.area_km2,
        "query_tags": tags,
        "geometry_policy": "Complete source features intersecting the query; not clipped.",
        "feature_count": len(frame),
        "invalid_geometry_count": int((~frame.geometry.is_valid).sum()),
        "crs": "EPSG:4326",
        "tag_columns": tag_columns,
        "sha256": checksum(path),
        "versions": {name: version(name) for name in ["osmnx", "geopandas", "pyogrio", "shapely"]},
    }
    metadata["synthetic"] = synthetic
    if synthetic:
        metadata.update(
            {
                "source": "Synthetic demonstration sample",
                "attribution": "Synthetic sample; not surveyed or acquired from OpenStreetMap.",
                "license_url": None,
                "cache_policy": "Generated locally; no network or cache used.",
                "geometry_policy": "Fixed synthetic geometries; identifiers are illustrative only.",
            }
        )
    (directory / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def load_dataset(directory: Path) -> tuple[gpd.GeoDataFrame, dict]:
    """Load only local files, validating schema, checksum, count, identity, and CRS."""
    directory = Path(directory)
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    if metadata.get("schema_version") != 1:
        raise ValueError("Unsupported dataset schema version.")
    path = directory / "features.gpkg"
    if checksum(path) != metadata.get("sha256"):
        raise ValueError("Dataset checksum mismatch.")
    stored = gpd.read_file(path, layer="features", engine="pyogrio")
    if len(stored) != metadata.get("feature_count"):
        raise ValueError("Dataset feature count does not match metadata.")
    if stored.crs is None or stored.crs.to_string() != metadata.get("crs"):
        raise ValueError("Dataset CRS does not match metadata.")
    if not {*IDENTITY, "tags_json"}.issubset(stored.columns):
        raise ValueError("Dataset is missing required columns.")
    if stored[IDENTITY].isna().any().any() or stored.duplicated(IDENTITY).any():
        raise ValueError("Dataset has invalid OSM identities.")
    tag_rows = [json.loads(value) for value in stored["tags_json"]]
    reserved = {*IDENTITY, "geometry", "tags_json"}
    if reserved.intersection(metadata["tag_columns"]):
        raise ValueError("Dataset tag columns conflict with reserved fields.")
    result = stored.drop(columns="tags_json")
    for name in metadata["tag_columns"]:
        result[name] = [row.get(name) for row in tag_rows]
    return result, metadata
