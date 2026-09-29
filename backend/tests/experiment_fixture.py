"""Synthetic hand-checkable native rasters; never represented as acquired data."""

from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin
from shapely.geometry import box, mapping

from uas_planner.core.experiment import checksum, raster_metadata, read_json, write_json
from uas_planner.sample import create_sample


def create_experiment_fixture(directory):
    directory = Path(directory)
    directory.mkdir()
    create_sample(directory / "osm")
    bounds = read_json(directory / "osm/metadata.json")["query_bounds"]
    config = {
        "bounds": bounds,
        "scenario": "civil",
        "agl_m": 60,
        "start": [10.5195, 52.2695],
        "end": [10.5205, 52.2705],
        "timezone": "Europe/Berlin",
        "mission_start": "2026-10-01T10:00:00+02:00",
        "mission_end": "2026-10-01T10:15:00+02:00",
        "ghsl_epoch": 2020,
        "temporary_restrictions": "unverified",
    }
    sources = {}
    for kind, crs, spacing, value in [
        ("ghsl", "ESRI:54009", 100, 20),
        ("terrain", "EPSG:25832", 1, 80),
    ]:
        convert = Transformer.from_crs(4326, crs, always_xy=True)
        w, s, e, n = convert.transform_bounds(
            bounds["west"], bounds["south"], bounds["east"], bounds["north"]
        )
        x, y = np.floor(w / spacing) * spacing - spacing, np.ceil(n / spacing) * spacing + spacing
        width, height = int(np.ceil((e - x) / spacing)) + 1, int(np.ceil((y - s) / spacing)) + 1
        values = np.full((height, width), value, dtype="float32")
        transform = from_origin(x, y, spacing, spacing)
        # Start deliberately has real zero, end deliberately has NoData.
        for point, special in [(config["start"], 0), (config["end"], -9999)]:
            px, py = convert.transform(*point)
            col, row = ~transform @ (px, py)
            values[int(row), int(col)] = special
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
            transform=transform,
            nodata=-9999 if kind == "ghsl" else None,
        ) as dst:
            dst.write(values, 1)
        sources[kind] = {
            "path": filename,
            "source_id": f"TEST-{kind}",
            "product": "Synthetic fixture",
            "attribution": "Synthetic test data",
            "license": "Test fixture",
            "raster": raster_metadata(directory / filename, kind),
        }
    sources["terrain"]["vertical_datum"] = "DHHN2016 / NHN (EPSG:7837)"
    zones = {
        "type": "FeatureCollection",
        "numberMatched": 1,
        "numberReturned": 1,
        "features": [
            {
                "type": "Feature",
                "id": "test-zone.42",
                "geometry": mapping(box(10.519, 52.269, 10.52, 52.27)),
                "properties": {
                    "name": "<img src=x onerror=alert(1)>",
                    "upper_limit_altitude": 100,
                    "upper_limit_unit": "ft",
                    "upper_limit_alt_ref": "MSL",
                },
            }
        ],
    }
    write_json(directory / "zones.geojson", zones)
    sources["dipul"] = {
        "source_id": "TEST-DIPUL",
        "product": "Synthetic fixture",
        "license": "Test fixture",
        "attribution": "Synthetic test data",
        "coverage": "partial synthetic fixture",
        "responses": [{"path": "zones.geojson", "type_name": "test:zone", "feature_count": 1}],
    }
    manifest = {
        "schema_version": 1,
        "synthetic": True,
        "config": config,
        "sources": sources,
        "saved_at_utc": "2026-09-29T10:00:00Z",
        "analysis_crs": "EPSG:25832",
        "display_crs": "EPSG:4326",
        "files": [
            {"path": name, "sha256": checksum(directory / name)}
            for name in ("ghsl.tif", "terrain.tif", "zones.geojson")
        ],
    }
    write_json(directory / "experiment.json", manifest)
    return manifest
