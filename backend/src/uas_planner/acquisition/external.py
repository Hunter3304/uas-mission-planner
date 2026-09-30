"""Explicit, bounded network acquisition for the Part 1 Braunschweig experiment."""

import math
import shutil
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import rasterio
import requests
from pyproj import Transformer

from uas_planner.core.experiment import (
    checksum,
    load_experiment,
    native_window,
    population_layer,
    raster_metadata,
    read_json,
    safe_file,
    validate_config,
    validate_zones,
    write_json,
)

DIPUL = "https://uas-betrieb.de/geoservices/dipul/ows"
TERRAIN = "https://opendata.geoservices.lgln.niedersachsen.de/dgm_wcs"
# A deliberately limited source selection, never advertised as complete restriction coverage.
ZONE_TYPES = ("kontrollzonen", "bahnanlagen", "bundesstrassen", "naturschutzgebiete")
MAX_DOWNLOAD_BYTES = 150 * 1024 * 1024


def download(url, path, params=None):
    """Preserve exact response bytes; no implicit retries or overwrite."""
    started = datetime.now(timezone.utc).isoformat()
    deadline = time.monotonic() + 180
    with requests.get(url, params=params, stream=True, timeout=(15, 45)) as response:
        response.raise_for_status()
        size = 0
        with Path(path).open("xb") as stream:
            for block in response.iter_content(1024 * 1024):
                size += len(block)
                if size > MAX_DOWNLOAD_BYTES or time.monotonic() > deadline:
                    raise ValueError(
                        "Source download exceeded size/time limit; incomplete file retained."
                    )
                stream.write(block)
        return {
            "url": response.url,
            "started_at_utc": started,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "last_modified": response.headers.get("Last-Modified"),
            "etag": response.headers.get("ETag"),
            "bytes": size,
            "content_type": response.headers.get("Content-Type"),
        }


def acquire_experiment(config, output, *, resume=False):
    """Create external snapshots only. OSM uses the unchanged acquisition pipeline."""
    area = validate_config(config)
    # This first adapter intentionally targets one validated distribution tile / state.
    if not (10 <= area.west < area.east <= 11 and 52 <= area.south < area.north <= 53):
        raise ValueError("This source adapter currently supports the Braunschweig region only.")
    output = Path(output)
    if resume:
        if (output / "experiment.json").exists():
            raise ValueError("Completed snapshots cannot be resumed or overwritten.")
        progress = read_json(safe_file(output, "acquisition-progress.json"))
        if progress["config"] != config:
            raise ValueError("Resume configuration does not match the saved acquisition.")
        files = progress["files"]
        for record in files:
            if checksum(safe_file(output, record["path"])) != record["sha256"]:
                raise ValueError("Cannot resume: saved payload checksum mismatch.")
    else:
        output.mkdir(parents=True, exist_ok=False)
        (output / "raw").mkdir()
        files = []
    raw = output / "raw"
    if raw.resolve() != output.resolve() / "raw":
        raise ValueError("Raw payload directory must not redirect outside the experiment.")

    def fetch(name, url, params=None):
        existing = next((r for r in files if r["path"] == f"raw/{name}"), None)
        if existing:
            expected_url = requests.Request("GET", url, params=params).prepare().url
            if existing["url"] != expected_url:
                raise ValueError("Cannot resume a payload with a changed source request.")
            return existing
        print(f"Downloading {name}...", flush=True)
        record = download(url, raw / name, params)
        record.update(path=f"raw/{name}", sha256=checksum(raw / name))
        files.append(record)
        write_json(output / "acquisition-progress.json", {"config": config, "files": files})
        return record

    epoch = config["ghsl_epoch"]
    product = f"GHS_POP_E{epoch}_GLOBE_R2023A_54009_100"
    tile = f"{product}_V1_0_R3_C19"
    url = (
        f"https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/"
        f"{product}/V1-0/tiles/{tile}.zip"
    )
    fetch("ghsl.zip", url)
    if not any(record["path"] == "population.tif" for record in files):
        with zipfile.ZipFile(raw / "ghsl.zip") as archive:
            members = [n for n in archive.namelist() if n.lower().endswith(".tif")]
            if len(members) != 1 or archive.getinfo(members[0]).file_size > 600 * 1024 * 1024:
                raise ValueError("Unexpected GHSL archive contents.")
            # Do not extract publisher paths. The original ZIP remains immutable.
            with archive.open(members[0]) as source, (raw / "ghsl-tile.tif").open("xb") as target:
                shutil.copyfileobj(source, target)
        raster_metadata(raw / "ghsl-tile.tif", "ghsl")
        with rasterio.open(raw / "ghsl-tile.tif") as src:
            window = native_window(src, area)
            if (
                window.col_off < 0
                or window.row_off < 0
                or window.col_off + window.width > src.width
                or window.row_off + window.height > src.height
            ):
                raise ValueError("Selected GHSL tile does not cover the requested area.")
            profile = src.profile.copy()
            profile.update(
                width=int(window.width),
                height=int(window.height),
                transform=src.window_transform(window),
                compress="deflate",
            )
            with rasterio.open(output / "population.tif", "w", **profile) as dst:
                dst.write(src.read(window=window))
        # The extracted scratch TIFF is redundant with the exact ZIP, and belongs to this new output.
        (raw / "ghsl-tile.tif").unlink()
        files.append(
            {
                "path": "population.tif",
                "sha256": checksum(output / "population.tif"),
                "derived_from": "raw/ghsl.zip",
                "member": members[0],
                "operation": "native pixel window, no resampling",
            }
        )

    write_json(output / "acquisition-progress.json", {"config": config, "files": files})
    fetch("dgm-capabilities.xml", TERRAIN, {"service": "WCS", "request": "GetCapabilities"})
    fetch(
        "dgm-description.xml",
        TERRAIN,
        {
            "service": "WCS",
            "version": "2.0.1",
            "request": "DescribeCoverage",
            "coverageId": "ni_dgm1",
        },
    )
    extent = Transformer.from_crs(4326, 25832, always_xy=True).transform_bounds(*area.as_tuple())
    west, south, east, north = [
        math.floor(v) if i < 2 else math.ceil(v) for i, v in enumerate(extent)
    ]
    fetch(
        "terrain.tif",
        TERRAIN,
        [
            ("service", "WCS"),
            ("version", "2.0.1"),
            ("request", "GetCoverage"),
            ("coverageId", "ni_dgm1"),
            ("format", "image/tiff"),
            ("subset", f"x({west},{east})"),
            ("subset", f"y({south},{north})"),
        ],
    )
    terrain_meta = raster_metadata(raw / "terrain.tif", "terrain")

    fetch(
        "dipul-capabilities.xml",
        DIPUL,
        {"service": "WFS", "version": "2.0.0", "request": "GetCapabilities"},
    )
    capabilities = ET.parse(raw / "dipul-capabilities.xml")
    available = {e.text for e in capabilities.findall(".//{http://www.opengis.net/wfs/2.0}Name")}
    responses = []
    for name in ZONE_TYPES:
        type_name = f"dipul:{name}"
        if type_name not in available:
            raise ValueError(f"DIPUL layer missing from capabilities: {type_name}")
        fetch(
            f"{name}-schema.xml",
            DIPUL,
            {
                "service": "WFS",
                "version": "2.0.0",
                "request": "DescribeFeatureType",
                "typeNames": type_name,
            },
        )
        record = fetch(
            f"{name}.geojson",
            DIPUL,
            {
                "service": "WFS",
                "version": "2.0.0",
                "request": "GetFeature",
                "typeNames": type_name,
                "outputFormat": "application/json",
                "count": 10000,
                "srsName": "CRS:84",
                "bbox": ",".join(map(str, area.as_tuple())) + ",urn:ogc:def:crs:OGC:1.3:CRS84",
            },
        )
        collection = read_json(raw / f"{name}.geojson")
        features = validate_zones(collection, area)
        responses.append(
            {
                "path": record["path"],
                "type_name": type_name,
                "feature_count": len(features),
                "property_names": sorted({key for f in features for key in f["properties"]}),
                "source_timestamp": collection.get("timeStamp"),
            }
        )

    manifest = {
        "schema_version": 1,
        "synthetic": False,
        "config": config,
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": files,
        "analysis_crs": "EPSG:25832",
        "display_crs": "EPSG:4326",
        "sources": {
            "ghsl": {
                "source_id": tile,
                "path": "population.tif",
                "product": "GHS-POP R2023A V1.0",
                "epoch_kind": "estimate" if epoch == 2020 else "projection",
                "units": "people per native 100 m cell",
                "license": "EC reuse policy; acknowledge source",
                "attribution": "European Commission, Joint Research Centre (JRC), GHS-POP R2023A",
                "raster": raster_metadata(output / "population.tif", "ghsl"),
            },
            "terrain": {
                "source_id": "LGLN:ni_dgm1",
                "path": "raw/terrain.tif",
                "product": "DGM1",
                "units": "metres",
                "vertical_datum": "DHHN2016 / NHN (EPSG:7837)",
                "surface": "bare-earth terrain",
                "native_support_m": 1,
                "license": "CC BY 4.0",
                "attribution": "LGLN (2026), CC BY 4.0",
                "survey_epoch": None,
                "raster": terrain_meta,
                "unit_evidence": "https://www.lgln.niedersachsen.de/download/207140/Kundeninformation_1_2024.pdf",
                "metadata_discrepancy": "WCS DescribeCoverage reports W.m-2.Sr-1 and the returned TIFF omits NoData. Metres, DHHN2016 and -9999 NoData are taken from the official DGM product specification; no radiance conversion applied. Original response bytes are retained.",
            },
            "dipul": {
                "source_id": "DIPUL:WFS:2.0.0",
                "product": "WFS 2.0.0 snapshot",
                "license": "CC BY-ND 4.0",
                "attribution": "dipul",
                "responses": responses,
                "coverage": "partial: selected static layers only",
                "temporary_restrictions": "unverified",
                "validity": "unresolved; download timestamp is not mission validity",
                "vertical_reference": "source properties retained; applicability unresolved",
                "buffers": "source geometries retained unchanged; no extra buffer applied",
                "sharing": "local inspection only; derived export not enabled",
            },
        },
    }
    population_layer(
        output, manifest
    )  # Validate numeric values and display cap before final manifest.
    write_json(output / "experiment.json", manifest)
    return load_experiment(output)
