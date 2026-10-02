"""Reproducible offline synthetic experiment for the routing demo, never real data."""

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin
from shapely.geometry import box, mapping

from uas_planner.core.experiment import (
    checksum,
    load_experiment,
    raster_metadata,
    read_json,
    write_json,
)
from uas_planner.sample import create_sample


def create_route_demo(directory, *, low_risk=False):
    directory = Path(directory)
    directory.mkdir(exist_ok=False)
    if low_risk:
        import geopandas as gpd

        from uas_planner.core.area import BoundingBox
        from uas_planner.storage.dataset import save_dataset

        bounds = {"west": 10.519, "south": 52.269, "east": 10.522, "north": 52.272}
        # A high-score band crosses the direct path; a longer route avoids it.
        frame = gpd.GeoDataFrame(
            {
                "element_type": ["way"],
                "osm_id": [100],
                "building": ["house"],
                "name": ["Synthetic high-risk building band"],
            },
            geometry=[box(10.5202, 52.2701, 10.5208, 52.2709)],
            crs=4326,
        )
        save_dataset(
            frame, directory / "osm", BoundingBox(**bounds), {"building": True}, synthetic=True
        )
    else:
        create_sample(directory / "osm")
        bounds = read_json(directory / "osm/metadata.json")["query_bounds"]
    config = {
        "bounds": bounds,
        "scenario": "civil",
        "agl_m": 60,
        "start": [10.5192, 52.2693],
        "end": [10.5208, 52.2707],
        "timezone": "Europe/Berlin",
        "mission_start": "2026-10-01T10:00:00+02:00",
        "mission_end": "2026-10-01T10:15:00+02:00",
        "ghsl_epoch": 2020,
        "temporary_restrictions": "unverified",
    }
    if low_risk:
        config["start"] = [10.5193, 52.2705]
        config["end"] = [10.5217, 52.2705]
    sources = {}
    for kind, crs, spacing, value in [
        ("ghsl", "ESRI:54009", 100, 20),
        ("terrain", "EPSG:25832", 1, 80),
    ]:
        converter = Transformer.from_crs(4326, crs, always_xy=True)
        w, s, e, n = converter.transform_bounds(
            bounds["west"], bounds["south"], bounds["east"], bounds["north"]
        )
        x, y = np.floor(w / spacing) * spacing - spacing, np.ceil(n / spacing) * spacing + spacing
        width, height = int(np.ceil((e - x) / spacing)) + 1, int(np.ceil((y - s) / spacing)) + 1
        filename = f"{kind}.tif"
        with rasterio.open(
            directory / filename,
            "w",
            driver="GTiff",
            crs=crs,
            count=1,
            width=width,
            height=height,
            dtype="float32",
            transform=from_origin(x, y, spacing, spacing),
            nodata=-9999,
        ) as dst:
            dst.write(np.full((height, width), value, dtype="float32"), 1)
        sources[kind] = {
            "path": filename,
            "source_id": f"SYNTHETIC-{kind}",
            "product": "Synthetic routing demo",
            "attribution": "Synthetic demonstration data",
            "license": "CC0 synthetic fixture",
            "raster": raster_metadata(directory / filename, kind),
        }
    sources["terrain"]["vertical_datum"] = "Synthetic metres NHN / DHHN2016"
    # Vertical wall with a passage to its north forces a visible detour.
    zones = {
        "type": "FeatureCollection",
        "numberMatched": 1,
        "numberReturned": 1,
        "features": [
            {
                "type": "Feature",
                "id": "synthetic-wall",
                "geometry": mapping(box(10.5199, bounds["south"], 10.5201, 52.27025)),
                "properties": {"name": "Synthetic blocked wall"},
            }
        ],
    }
    if low_risk:
        zones.update(numberMatched=0, numberReturned=0, features=[])
    write_json(directory / "zones.geojson", zones)
    sources["dipul"] = {
        "source_id": "SYNTHETIC-zones",
        "product": "Synthetic routing obstacles",
        "license": "CC0 synthetic fixture",
        "attribution": "Synthetic demonstration data",
        "coverage": "Synthetic model only, no real restriction coverage",
        "responses": [
            {
                "path": "zones.geojson",
                "type_name": "synthetic:obstacle",
                "feature_count": 0 if low_risk else 1,
            }
        ],
    }
    manifest = {
        "schema_version": 1,
        "synthetic": True,
        "routing_fixture": "synthetic-obstacles-v1",
        "demo_kind": "low-risk-detour" if low_risk else "obstacle-detour",
        "demo_assumptions": {"background_cost": 0} if low_risk else {},
        "config": config,
        "sources": sources,
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_crs": "EPSG:25832",
        "display_crs": "EPSG:4326",
        "files": [
            {"path": name, "sha256": checksum(directory / name)}
            for name in ("ghsl.tif", "terrain.tif", "zones.geojson")
        ],
    }
    write_json(directory / "experiment.json", manifest)
    return load_experiment(directory)
