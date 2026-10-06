"""Reproducible regional OSM/DIPUL/GHSL snapshots, independent of route readiness."""

import hashlib
import json
import math
import re
import shutil
import sys
import time
import zipfile
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from xml.etree import ElementTree as ET

import geopandas as gpd
import numpy as np
import pyogrio
import rasterio
import requests
from osmnx._errors import InsufficientResponseError
from osmnx.features import _create_gdf
from pyproj import Transformer
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from uas_planner.acquisition.external import MAX_DOWNLOAD_BYTES
from uas_planner.acquisition.osm import _SETTINGS_LOCK, TAGS
from uas_planner.core.area import BoundingBox, StudyRegion
from uas_planner.core.experiment import (
    checksum,
    native_window,
    raster_metadata,
    read_json,
    safe_file,
    validate_zones,
    write_json,
)
from uas_planner.storage.dataset import load_dataset, save_dataset

USER_AGENT = "uas-mission-planner/0.3 (https://github.com/Hunter3304/uas-mission-planner)"
# Public global instances listed by the OSM project. Actual response endpoints
# are retained in receipts; configured custom services are never redirected.
OVERPASS_PRIMARY = "https://overpass-api.de/api/interpreter"
OVERPASS_MIRROR = "https://lambert.openstreetmap.de/api/interpreter"
EXTRACT_POLYGON_URL = "https://download.geofabrik.de/europe/germany/niedersachsen.poly"
PROGRESS = "study-progress.json"
MANIFEST = "study.json"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def finite_number(value, lower, upper, label):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not lower <= value <= upper
    ):
        raise ValueError(f"{label} must be between {lower} and {upper}.")
    return value


def validate_study(config):
    """Regional acquisition configuration is separate from a timed flight experiment."""
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported study configuration schema.")
    area = StudyRegion(**config["bounds"])
    finite_number(config["agl_m"], 100, 120, "AGL altitude")
    finite_number(config["speed_m_s"], 25, 35, "Cruise speed")
    finite_number(config["detour_margin_m"], 0, 20000, "Detour margin")
    finite_number(config.get("chunk_side_m", 4000), 500, 4500, "Chunk side")
    if config["ghsl_epoch"] not in (2020, 2025):
        raise ValueError("Choose GHSL 2020 estimate or 2025 projection.")
    if not 9 <= area.west < area.east <= 11 or not 52 <= area.south < area.north <= 53:
        raise ValueError("This study adapter is scoped to Hannover/Lehrte and Braunschweig.")
    tiles = config["ghsl_tiles"]
    if not isinstance(tiles, list) or not tiles or len(set(tiles)) != len(tiles):
        raise ValueError("GHSL tile identifiers must be a nonempty unique list.")
    if len(tiles) != 1 or not re.fullmatch(r"R\d+_C\d+", tiles[0]):
        raise ValueError("This adapter requires one explicitly selected covering GHSL tile.")
    locations = config["locations"]
    if not isinstance(locations, list) or not locations:
        raise ValueError("A verified location catalog is required.")
    ids = set()
    for site in locations:
        if not isinstance(site["id"], str) or site["id"] in ids:
            raise ValueError("Location identifiers must be unique strings.")
        ids.add(site["id"])
        if not box(*area.as_tuple()).contains(Point(site["longitude"], site["latitude"])):
            raise ValueError(f"Location outside region interior: {site['id']}")
        if site.get("coordinate_status") != "address_geocoded_not_landing_site":
            raise ValueError("Location coordinate verification status is required.")
    for key in ("osm_url", "dipul_url"):
        if not config[key].startswith("https://"):
            raise ValueError("Source endpoints must use HTTPS.")
    if config.get("osm_format", "overpass") not in ("overpass", "geofabrik-pbf"):
        raise ValueError("Unsupported OSM source format.")
    if config.get("osm_format") == "geofabrik-pbf" and not re.fullmatch(
        r"https://download\.geofabrik\.de/europe/germany/niedersachsen-\d{6}\.osm\.pbf",
        config.get("osm_pbf_url", ""),
    ):
        raise ValueError("PBF input requires an explicitly dated Niedersachsen publisher URL.")
    layers = config.get("dipul_layers", "all_advertised")
    if layers != "all_advertised" and (
        not isinstance(layers, list)
        or not layers
        or len(set(layers)) != len(layers)
        or not all(re.fullmatch(r"dipul:[a-z0-9_-]+", name) for name in layers)
    ):
        raise ValueError("Invalid DIPUL layer selection.")
    return area


def region_for_locations(locations, margin_m=5000):
    """Envelope the metric location extent, with a configurable detour allowance."""
    finite_number(margin_m, 0, 20000, "Detour margin")
    to_metric = Transformer.from_crs(4326, 25832, always_xy=True)
    points = [to_metric.transform(s["longitude"], s["latitude"]) for s in locations]
    if not points:
        raise ValueError("No locations supplied.")
    xs, ys = zip(*points, strict=True)
    bounds = (min(xs) - margin_m, min(ys) - margin_m, max(xs) + margin_m, max(ys) + margin_m)
    geographic = Transformer.from_crs(25832, 4326, always_xy=True).transform_bounds(*bounds)
    return StudyRegion(*geographic)


def query_chunks(area, side_m=4000):
    """Partition the entire geographic rectangle; each request retains the 25 km² cap."""
    finite_number(side_m, 500, 4500, "Chunk side")
    west, south, east, north = Transformer.from_crs(4326, 25832, always_xy=True).transform_bounds(
        *area.as_tuple()
    )
    cols, rows = math.ceil((east - west) / side_m), math.ceil((north - south) / side_m)
    return [
        BoundingBox(
            area.west + (area.east - area.west) * col / cols,
            area.south + (area.north - area.south) * row / rows,
            area.west + (area.east - area.west) * (col + 1) / cols,
            area.south + (area.north - area.south) * (row + 1) / rows,
        )
        for row in range(rows)
        for col in range(cols)
    ]


class PayloadStore:
    """Receipted immutable payloads with explicit resume and atomic completion."""

    def __init__(self, output, config, *, resume=False, download_cache=None, offline=False):
        self.root = Path(output)
        self.config = config
        self.offline = offline
        self.cache = Path(download_cache) if download_cache else None
        if resume:
            if (self.root / MANIFEST).exists():
                raise ValueError("Completed snapshots cannot be resumed or overwritten.")
            progress = read_json(safe_file(self.root, PROGRESS))
            if progress["config"] != config:
                raise ValueError("Resume configuration differs from saved acquisition.")
            self.files = progress["files"]
            self.splits = progress.get("osm_subdivisions", [])
            for entry in self.files:
                if checksum(safe_file(self.root, entry["path"])) != entry["sha256"]:
                    raise ValueError("Cannot resume a corrupted saved payload.")
        else:
            self.root.mkdir(parents=True, exist_ok=False)
            (self.root / "raw").mkdir()
            self.files = []
            self.splits = []
            self.save()
        if (self.root / "raw").resolve() != self.root.resolve() / "raw":
            raise ValueError("Raw directory must remain inside the snapshot.")
        if self.cache:
            self.cache.mkdir(parents=True, exist_ok=True)

    def save(self):
        write_json(
            self.root / PROGRESS,
            {"config": self.config, "files": self.files, "osm_subdivisions": self.splits},
        )

    def fetch(self, name, url, *, params=None, data=None):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            raise ValueError("Payload names cannot contain path components.")
        relative = f"raw/{name}"
        request = {"method": "POST" if data else "GET", "url": url, "params": params, "data": data}
        signature = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        existing = next((entry for entry in self.files if entry["path"] == relative), None)
        if existing:
            if existing["request"] != request:
                raise ValueError("Saved payload request has changed.")
            return self.root / relative
        if self.offline:
            raise ValueError(f"Offline reconstruction requires the missing original: {relative}")
        target = self.root / relative
        if target.exists():
            raise ValueError("Unreceipted payload exists; choose a new snapshot.")
        cache_receipt = self.cache / f"{signature}.json" if self.cache else None
        if cache_receipt and cache_receipt.exists():
            cached = read_json(cache_receipt)
            payload = self.cache / f"{signature}.payload"
            if cached["request"] != request or checksum(payload) != cached["sha256"]:
                raise ValueError("Download cache integrity/request mismatch.")
            shutil.copyfile(payload, target)
            receipt = {**cached, "cache_reused_at_utc": utc_now()}
        else:
            print(f"Fetching {name}", file=sys.stderr, flush=True)
            receipt = self._download(target, request)
            if name.startswith("osm-") and name.endswith(".json"):
                payload = read_json(target)
                if payload.get("remark") or not isinstance(payload.get("elements"), list):
                    raise ValueError(
                        "Overpass response is incomplete; it is not cached or receipted."
                    )
            receipt.update(request=request, sha256=checksum(target))
            if cache_receipt:
                # Cache entries are immutable; receipts are the completion marker.
                payload = self.cache / f"{signature}.payload"
                if payload.exists():
                    if checksum(payload) != receipt["sha256"]:
                        raise ValueError("Unreceipted cache payload conflicts with this response.")
                else:
                    shutil.copyfile(target, payload)
                write_json(cache_receipt, receipt)
        self.files.append({**receipt, "path": relative})
        self.save()
        return target

    @staticmethod
    def _download(target, request):
        partial = target.with_suffix(target.suffix + ".part")
        started = utc_now()
        for attempt in range(3):
            if partial.exists():
                partial.unlink()  # Only this adapter's named, incomplete transfer.
            is_pbf = target.name.endswith(".osm.pbf")
            deadline = time.monotonic() + (900 if is_pbf else 240)
            byte_limit = 650 * 1024 * 1024 if is_pbf else MAX_DOWNLOAD_BYTES
            endpoint = request["url"]
            if attempt > 0 and request["method"] == "POST" and endpoint == OVERPASS_PRIMARY:
                endpoint = OVERPASS_MIRROR
                print(
                    f"Retrying bounded Overpass query through {endpoint}",
                    file=sys.stderr,
                    flush=True,
                )
            try:
                with requests.request(
                    request["method"],
                    endpoint,
                    params=request["params"],
                    data=request["data"],
                    headers={"User-Agent": USER_AGENT},
                    stream=True,
                    timeout=(15, 60),
                ) as response:
                    response.raise_for_status()
                    size = 0
                    with partial.open("xb") as stream:
                        for block in response.iter_content(1024 * 1024):
                            size += len(block)
                            if size > byte_limit or time.monotonic() > deadline:
                                raise ValueError("Payload exceeds bounded transfer size/time.")
                            stream.write(block)
                    partial.rename(target)
                    return {
                        "response_url": response.url,
                        "transfer_endpoint": endpoint,
                        "started_at_utc": started,
                        "retrieved_at_utc": utc_now(),
                        "last_modified": response.headers.get("Last-Modified"),
                        "etag": response.headers.get("ETag"),
                        "bytes": size,
                        "attempts": attempt + 1,
                    }
            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
                status = exc.response.status_code if exc.response is not None else None
                if attempt == 2 or status not in (None, 429, 502, 503, 504):
                    raise RuntimeError(
                        f"Source transfer failed: {type(exc).__name__}, HTTP {status}"
                    ) from exc
                time.sleep(2 ** (attempt + 1))
        raise RuntimeError("Source transfer failed.")


def overpass_query(area):
    bbox = f"{area.south},{area.west},{area.north},{area.east}"
    selectors = "".join(f'nwr["{tag}"]({bbox});' for tag in TAGS)
    return f"[out:json][timeout:120];({selectors});out body;>;out skel qt;"


def subdivide(chunk):
    x, y = (chunk.west + chunk.east) / 2, (chunk.south + chunk.north) / 2
    return [
        BoundingBox(*bounds)
        for bounds in (
            (chunk.west, chunk.south, x, y),
            (x, chunk.south, chunk.east, y),
            (chunk.west, y, x, chunk.north),
            (x, y, chunk.east, chunk.north),
        )
    ]


def osm_leaves(area, config, splits):
    """Deterministic request partition including recorded bounded subdivisions."""

    def visit(chunk, label, depth=0):
        if label not in splits:
            return [(f"raw/osm-{label}.json", chunk)]
        if depth >= 2:
            raise ValueError("OSM subdivision exceeds the bounded depth.")
        return [
            leaf
            for index, child in enumerate(subdivide(chunk))
            for leaf in visit(child, f"{label}-{index}", depth + 1)
        ]

    return [
        leaf
        for index, chunk in enumerate(query_chunks(area, config.get("chunk_side_m", 4000)))
        for leaf in visit(chunk, f"{index:03d}")
    ]


def osm_frame(paths, area):
    """Rebuild exclusively from original Overpass responses using the pinned OSMnx parser."""
    elements = {}
    conflicts = 0
    timestamps = []
    for path in paths:
        response = read_json(path)
        if response.get("remark") or not isinstance(response.get("elements"), list):
            raise ValueError("Overpass error/incomplete response; snapshot cannot complete.")
        timestamps.append(response.get("osm3s", {}).get("timestamp_osm_base"))
        for element in response["elements"]:
            identity = (element["type"], element["id"])
            if identity in elements:
                previous = elements[identity]
                # A skeleton dependency must not replace the full tagged object.
                if "tags" in element and "tags" not in previous:
                    elements[identity] = element
                elif "tags" in previous and "tags" in element and previous != element:
                    conflicts += 1  # Deterministically retain first; originals retain both.
            else:
                elements[identity] = element
    with _SETTINGS_LOCK:
        try:
            frame = _create_gdf(
                [{"elements": list(elements.values())}], box(*area.as_tuple()), TAGS
            )
            frame = frame.rename_axis(index=["element_type", "osm_id"]).reset_index()
        except InsufficientResponseError as exc:
            if "No matching features" not in str(exc):
                raise ValueError("OSM response could not be reconstructed.") from exc
            frame = gpd.GeoDataFrame(
                {"element_type": [], "osm_id": []}, geometry=[], crs="EPSG:4326"
            )
    return frame, {"source_base_timestamps": timestamps, "conflicting_tagged_versions": conflicts}


def pbf_frame(path, area):
    """Read complete intersecting OSM geometries using the installed GDAL OSM driver."""
    if "OSM" not in pyogrio.list_drivers():
        raise ValueError("The installed GDAL runtime has no OSM/PBF driver.")
    frames = []
    pattern = re.compile(r'"((?:\\.|[^"\\])*)"=>"((?:\\.|[^"\\])*)"')
    for layer, element_type in (
        ("points", "node"),
        ("lines", "way"),
        ("multipolygons", None),
        ("multilinestrings", "relation"),
        ("other_relations", "relation"),
    ):
        print(f"Reading regional PBF layer {layer}", file=sys.stderr, flush=True)
        source = pyogrio.read_dataframe(path, layer=layer, bbox=area.as_tuple())
        rows = []
        for _, feature in source.iterrows():
            tags = {}
            other = feature.get("other_tags")
            if isinstance(other, str):
                for match in pattern.finditer(other):
                    key, value = (
                        json.loads('"' + part + '"', strict=False) for part in match.groups()
                    )
                    tags[key] = value
            # GDAL extracts common tags as columns; computed fields are not OSM tags.
            for key in source.columns:
                if key in ("geometry", "osm_id", "osm_way_id", "other_tags", "z_order"):
                    continue
                value = feature[key]
                if isinstance(value, str):
                    tags[key] = value
            if not any(tag in tags for tag in TAGS):
                continue
            identity = feature.get("osm_id")
            kind = element_type
            if layer == "multipolygons":
                way_id = feature.get("osm_way_id")
                if isinstance(way_id, str) and way_id:
                    identity, kind = way_id, "way"
                else:
                    kind = "relation"
            if identity is None or str(identity) in ("", "nan", "None"):
                raise ValueError("PBF feature lacks original OSM identity.")
            rows.append(
                {
                    "element_type": kind,
                    "osm_id": int(identity),
                    "_source_tags": tags,
                    "geometry": feature.geometry,
                }
            )
        if rows:
            frames.append(gpd.GeoDataFrame(rows, geometry="geometry", crs=4326))
    if not frames:
        return gpd.GeoDataFrame({"element_type": [], "osm_id": []}, geometry=[], crs=4326), {}
    import pandas as pd

    frame = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), geometry="geometry", crs=4326)
    # Closed tagged ways can appear as both lines and polygons. Prefer area geometry.
    frame["_area_priority"] = frame.geom_type.isin(("Polygon", "MultiPolygon")).astype(int)
    frame = frame.sort_values("_area_priority", ascending=False, kind="stable")
    duplicates = int(frame.duplicated(["element_type", "osm_id"]).sum())
    frame = frame.drop_duplicates(["element_type", "osm_id"]).drop(columns="_area_priority")
    return frame.reset_index(drop=True), {
        "source_base_timestamps": [],
        "conflicting_tagged_versions": 0,
        "duplicate_layer_representations": duplicates,
        "parser": "GDAL OSM driver; common tag columns plus original other_tags",
        "gdal_version": pyogrio.__gdal_version_string__,
    }


def extract_polygon(path):
    """Read the publisher's Osmosis polygon without inferring coverage from a bbox."""
    lines = iter(Path(path).read_text(encoding="utf-8").splitlines()[1:])
    shells, holes = [], []
    for name in lines:
        name = name.strip()
        if name == "END":
            break
        if not name:
            continue
        coordinates = []
        for line in lines:
            if line.strip() == "END":
                break
            coordinates.append(tuple(map(float, line.split())))
        polygon = Polygon(coordinates)
        if polygon.is_empty or not polygon.is_valid:
            raise ValueError("Invalid publisher extract polygon.")
        (holes if name.startswith("!") else shells).append(polygon)
    if not shells:
        raise ValueError("Publisher extract polygon is empty.")
    return unary_union(shells).difference(unary_union(holes))


def fetch_dipul(store, area):
    url = store.config["dipul_url"]
    capabilities = store.fetch(
        "dipul-capabilities.xml",
        url,
        params={"service": "WFS", "version": "2.0.0", "request": "GetCapabilities"},
    )
    available = sorted(
        {
            e.text
            for e in ET.parse(capabilities).findall(".//{http://www.opengis.net/wfs/2.0}Name")
            if e.text and re.fullmatch(r"dipul:[a-z0-9_-]+", e.text)
        }
    )
    names = store.config.get("dipul_layers", "all_advertised")
    names = available if names == "all_advertised" else names
    if not names or len(names) > 40 or not set(names).issubset(available):
        raise ValueError("Requested DIPUL layers are unavailable or exceed the layer cap.")
    responses = []
    for name in names:
        stem = name.split(":", 1)[1]
        store.fetch(
            f"dipul-{stem}-schema.xml",
            url,
            params={
                "service": "WFS",
                "version": "2.0.0",
                "request": "DescribeFeatureType",
                "typeNames": name,
            },
        )
        features, pages, total = [], [], None
        for page in range(100):
            path = store.fetch(
                f"dipul-{stem}-{page:03d}.geojson",
                url,
                params={
                    "service": "WFS",
                    "version": "2.0.0",
                    "request": "GetFeature",
                    "typeNames": name,
                    "outputFormat": "application/json",
                    "count": 2000,
                    "startIndex": len(features),
                    "srsName": "CRS:84",
                    "bbox": ",".join(map(str, area.as_tuple())) + ",urn:ogc:def:crs:OGC:1.3:CRS84",
                },
            )
            payload = read_json(path)
            matched = payload.get("numberMatched", payload.get("totalFeatures"))
            if str(matched) == "unknown" or matched is None:
                raise ValueError("DIPUL matched count is unknown; completeness unresolved.")
            count = int(matched)
            if count < 0 or (total is not None and total != count):
                raise ValueError("DIPUL matched count changed during pagination.")
            total = count
            batch = payload.get("features")
            if payload.get("type") != "FeatureCollection" or not isinstance(batch, list):
                raise ValueError("Invalid DIPUL page.")
            if payload.get("numberReturned", len(batch)) != len(batch):
                raise ValueError("DIPUL returned-count mismatch.")
            # Check CRS, geometry and IDs on each original page, separately from pagination.
            validate_zones(
                {**payload, "numberMatched": len(batch), "totalFeatures": len(batch)}, area
            )
            features.extend(batch)
            pages.append(str(path.relative_to(store.root)).replace("\\", "/"))
            if len(features) == total:
                break
            if not batch or len(features) > total:
                raise ValueError("DIPUL pagination is incomplete or inconsistent.")
        else:
            raise ValueError("DIPUL pagination exceeds bounded request count.")
        collection = {"type": "FeatureCollection", "numberMatched": total, "features": features}
        validate_zones(collection, area)  # Detect duplicate IDs across pages.
        responses.append(
            {
                "type_name": name,
                "pages": pages,
                "feature_count": total,
                "property_names": sorted({k for f in features for k in f["properties"]}),
            }
        )
    return {
        "source_id": "DIPUL:WFS:2.0.0",
        "advertised_layers": available,
        "responses": responses,
        "license": "CC BY-ND 4.0",
        "attribution": "dipul",
        "coverage": "selected advertised layers, bounded query, verified response counts",
        "temporary_restrictions": "acquired, applicability unresolved"
        if "dipul:temporaere_betriebseinschraenkungen" in names
        else "not acquired",
        "validity": "unresolved; acquisition is not mission applicability verification",
        "sharing": "original bytes retained locally; derived DIPUL exports not enabled",
    }


def derive_population(archive_path, destination, area):
    """Aligned native-pixel crop without population resampling or a display-size cap."""
    with zipfile.ZipFile(archive_path) as archive:
        members = [n for n in archive.namelist() if n.lower().endswith(".tif")]
        if len(members) != 1 or archive.getinfo(members[0]).file_size > 600 * 1024 * 1024:
            raise ValueError("Unexpected GHSL archive contents.")
        scratch = destination.with_suffix(".native-part.tif")
        if scratch.exists():
            scratch.unlink()
        with archive.open(members[0]) as source, scratch.open("xb") as target:
            shutil.copyfileobj(source, target)
        try:
            raster_metadata(scratch, "ghsl")
            with rasterio.open(scratch) as src:
                window = native_window(src, area)
                if (
                    window.col_off < 0
                    or window.row_off < 0
                    or window.col_off + window.width > src.width
                    or window.row_off + window.height > src.height
                ):
                    raise ValueError("Selected GHSL tile does not cover the full study region.")
                values = src.read(window=window)
                masked = src.read(1, window=window, masked=True)
                valid = masked.compressed()
                if np.any(~np.isfinite(valid)) or np.any(valid < 0):
                    raise ValueError("Invalid population outside declared NoData.")
                profile = src.profile.copy()
                profile.update(
                    width=int(window.width),
                    height=int(window.height),
                    transform=src.window_transform(window),
                    compress="deflate",
                )
                with rasterio.open(destination, "w", **profile) as dst:
                    dst.write(values)
            return members[0]
        finally:
            scratch.unlink()


def ghsl_request(config):
    product = f"GHS_POP_E{config['ghsl_epoch']}_GLOBE_R2023A_54009_100"
    tile = f"{product}_V1_0_{config['ghsl_tiles'][0]}"
    return tile, (
        "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/"
        f"{product}/V1-0/tiles/{tile}.zip"
    )


def build_derived(root, config, source_files, osm_paths, *, original_sources=None, splits=None):
    """Only local originals are read; source snapshot files are never modified."""
    area = validate_study(config)
    root = Path(root)
    print("Preparing native population crop and OSM dataset", file=sys.stderr, flush=True)
    member = derive_population(safe_file(root, "raw/ghsl.zip"), root / "population.tif", area)
    pbf = config.get("osm_format") == "geofabrik-pbf"
    if pbf:
        if not extract_polygon(safe_file(root, "raw/osm-source.poly")).covers(
            box(*area.as_tuple())
        ):
            raise ValueError("The publisher extract does not cover the entire study region.")
        path = safe_file(root, "raw/osm-source.osm.pbf")
        published = safe_file(root, "raw/osm-source.md5").read_text().split()[0]
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "md5").hexdigest()
        if actual != published:
            raise ValueError("Publisher PBF checksum mismatch.")
        frame, diagnostics = pbf_frame(path, area)
    else:
        frame, diagnostics = osm_frame([safe_file(root, path) for path in osm_paths], area)
    frame.attrs["source"] = (
        "OpenStreetMap via Geofabrik/GDAL" if pbf else "OpenStreetMap via Overpass/OSMnx"
    )
    frame.attrs["cache_policy"] = (
        "Original immutable source payloads preserved; receipts retain original retrieval and cache reuse times."
    )
    osm_receipts = [record for record in source_files if record["path"] in osm_paths]
    times = [
        record.get("retrieved_at_utc") for record in osm_receipts if record.get("retrieved_at_utc")
    ]
    started = [
        record.get("started_at_utc") for record in osm_receipts if record.get("started_at_utc")
    ]
    if started:
        frame.attrs["acquisition_started_at_utc"] = min(started)
    if times:
        frame.attrs["acquisition_finished_at_utc"] = max(times)
    tag_objects = frame["_source_tags"].tolist() if "_source_tags" in frame else None
    if tag_objects is not None:
        frame = frame.drop(columns="_source_tags")
    save_dataset(frame, root / "osm", area, TAGS, tag_objects=tag_objects)
    tile, _ = ghsl_request(config)
    derived = [
        {"path": path, "sha256": checksum(root / path)}
        for path in ("population.tif", "osm/features.gpkg", "osm/metadata.json")
    ]
    result = {
        "schema_version": 1,
        "kind": "regional-source-study",
        "synthetic": False,
        "config": config,
        "saved_at_utc": utc_now(),
        "analysis_crs": "EPSG:25832",
        "files": source_files + derived,
        "osm_raw_paths": osm_paths,
        "osm_subdivisions": splits or [],
        "versions": {name: version(name) for name in ("osmnx", "rasterio", "pyproj")},
        "sources": {
            "osm": {
                "feature_count": len(frame),
                "query_tags": TAGS,
                **diagnostics,
                "geometry_policy": "whole intersecting source features; not clipped",
                "attribution": "© OpenStreetMap contributors",
                "license": "ODbL",
                "rebuild_adapter": "GDAL OSM/PBF driver"
                if pbf
                else "OSMnx features._create_gdf; regression-tested",
                "source_format": "geofabrik-pbf" if pbf else "overpass",
                "publisher_url": config.get("osm_pbf_url") if pbf else config["osm_url"],
            },
            "ghsl": {
                "source_id": tile,
                "path": "population.tif",
                "member": member,
                "product": "GHS-POP R2023A V1.0",
                "units": "people per native 100 m cell",
                "epoch_kind": "estimate" if config["ghsl_epoch"] == 2020 else "projection",
                "attribution": "European Commission, Joint Research Centre",
                "license": "EC reuse policy; acknowledge source",
                "operation": "aligned native window; no resampling",
                "raster": raster_metadata(root / "population.tif", "ghsl"),
            },
            "dipul": original_sources,
            "terrain": {
                "status": "not acquired by the regional source-study workflow",
                "reason": "Full-region native DGM1 acquisition/planner preparation requires a separate bounded design in Part 2; no 3D clearance is claimed.",
            },
        },
        "readiness": "source snapshot only; no routing/flight applicability claim",
    }
    verify_study(root, result)
    write_json(root / MANIFEST, result)  # Completion marker is written only after validation.
    return result


def acquire_study(config, output, *, resume=False, download_cache=None):
    area = validate_study(config)
    store = PayloadStore(output, config, resume=resume, download_cache=download_cache)
    tile, url = ghsl_request(config)
    store.fetch("ghsl.zip", url)
    dipul = fetch_dipul(store, area)

    def fetch_chunk(chunk, label, depth=0):
        if label not in store.splits:
            try:
                store.fetch(
                    f"osm-{label}.json", config["osm_url"], data={"data": overpass_query(chunk)}
                )
                time.sleep(1)
                return
            except (RuntimeError, ValueError) as exc:
                transient = "Source transfer failed" in str(
                    exc
                ) or "Overpass response is incomplete" in str(exc)
                if not transient or depth >= 2:
                    raise
                print(f"Subdividing failed OSM chunk {label}", file=sys.stderr, flush=True)
                store.splits.append(label)
                store.save()
        for index, child in enumerate(subdivide(chunk)):
            fetch_chunk(child, f"{label}-{index}", depth + 1)

    if config.get("osm_format") == "geofabrik-pbf":
        store.fetch("osm-source.poly", EXTRACT_POLYGON_URL)
        store.fetch("osm-source.md5", config["osm_pbf_url"] + ".md5")
        store.fetch("osm-source.osm.pbf", config["osm_pbf_url"])
        osm_paths = ["raw/osm-source.osm.pbf"]
    else:
        for index, chunk in enumerate(query_chunks(area, config.get("chunk_side_m", 4000))):
            fetch_chunk(chunk, f"{index:03d}")
        osm_paths = [path for path, _ in osm_leaves(area, config, store.splits)]
    if (store.root / "osm").exists() or (store.root / "population.tif").exists():
        raise ValueError("Derived output already exists; use study-rebuild on preserved originals.")
    return build_derived(
        store.root, config, store.files, osm_paths, original_sources=dipul, splits=store.splits
    )


def inspect_study(directory):
    """Verify complete regional sources offline; no population-display materialization."""
    root = Path(directory)
    manifest = read_json(safe_file(root, MANIFEST))
    return verify_study(root, manifest)


def verify_study(root, manifest):
    """Validate a candidate manifest before publishing its completion marker."""
    root = Path(root)
    if manifest.get("schema_version") != 1 or manifest.get("kind") != "regional-source-study":
        raise ValueError("Unsupported study manifest.")
    area = validate_study(manifest["config"])
    checked = set()
    for record in manifest["files"]:
        if record["path"] in checked:
            raise ValueError("Duplicate manifest path.")
        if checksum(safe_file(root, record["path"])) != record["sha256"]:
            raise ValueError(f"Checksum mismatch: {record['path']}")
        checked.add(record["path"])
    required = {
        "raw/ghsl.zip",
        "raw/dipul-capabilities.xml",
        "population.tif",
        "osm/features.gpkg",
        "osm/metadata.json",
        *manifest["osm_raw_paths"],
    }
    if not required.issubset(checked):
        raise ValueError("Required source/derived payloads are absent from the integrity manifest.")
    pbf = manifest["config"].get("osm_format") == "geofabrik-pbf"
    leaves = (
        [("raw/osm-source.osm.pbf", area)]
        if pbf
        else osm_leaves(area, manifest["config"], manifest.get("osm_subdivisions", []))
    )
    paths, chunks = zip(*leaves, strict=True)
    if len(manifest["osm_raw_paths"]) != len(chunks):
        raise ValueError("OSM chunk coverage is incomplete.")
    if len(set(manifest["osm_raw_paths"])) != len(chunks):
        raise ValueError("OSM chunk paths must be unique.")
    if list(paths) != manifest["osm_raw_paths"]:
        raise ValueError("OSM paths do not match the declared region partition.")
    receipts = {record["path"]: record for record in manifest["files"]}
    for path, chunk in zip(manifest["osm_raw_paths"], chunks, strict=True):
        if pbf:
            if not {"raw/osm-source.md5", "raw/osm-source.poly"}.issubset(checked):
                raise ValueError("Publisher PBF checksum receipt is absent.")
            if not extract_polygon(root / "raw/osm-source.poly").covers(box(*area.as_tuple())):
                raise ValueError("Publisher extract coverage is incomplete.")
            if receipts[path].get("request", {}).get("url") != manifest["config"]["osm_pbf_url"]:
                raise ValueError("PBF request differs from configured publisher version.")
            continue
        expected = {
            "method": "POST",
            "url": manifest["config"]["osm_url"],
            "params": None,
            "data": {"data": overpass_query(chunk)},
        }
        if receipts[path].get("request") != expected:
            raise ValueError("OSM request does not cover the configured chunk.")
        payload = read_json(safe_file(root, path))
        if payload.get("remark") or not isinstance(payload.get("elements"), list):
            raise ValueError("Invalid OSM source payload.")
    frame, metadata = load_dataset(root / "osm", compact=True)
    if (
        metadata["query_bounds"] != asdict(area)
        or len(frame) != manifest["sources"]["osm"]["feature_count"]
    ):
        raise ValueError("OSM region/count differs from study manifest.")
    raster = raster_metadata(root / "population.tif", "ghsl")
    if raster != manifest["sources"]["ghsl"]["raster"]:
        raise ValueError("Population raster metadata mismatch.")
    with rasterio.open(root / "population.tif") as src:
        window = native_window(src, area)
        if (
            window.col_off < 0
            or window.row_off < 0
            or window.col_off + window.width > src.width
            or window.row_off + window.height > src.height
        ):
            raise ValueError("Population does not cover the entire region.")
        values = src.read(1, masked=True).compressed()
        if np.any(~np.isfinite(values)) or np.any(values < 0):
            raise ValueError("Invalid population values.")
    advertised = sorted(
        {
            e.text
            for e in ET.parse(root / "raw/dipul-capabilities.xml").findall(
                ".//{http://www.opengis.net/wfs/2.0}Name"
            )
            if e.text
        }
    )
    requested = manifest["config"].get("dipul_layers", "all_advertised")
    requested = advertised if requested == "all_advertised" else requested
    responses = manifest["sources"]["dipul"]["responses"]
    actual = [response["type_name"] for response in responses]
    if len(set(actual)) != len(actual) or set(actual) != set(requested):
        raise ValueError("DIPUL selected-layer coverage is incomplete.")
    for response in responses:
        features = []
        schema_path = f"raw/dipul-{response['type_name'].split(':', 1)[1]}-schema.xml"
        if schema_path not in checked:
            raise ValueError("DIPUL schema absent from integrity manifest.")
        for path in response["pages"]:
            if path not in checked:
                raise ValueError("DIPUL page is not in integrity manifest.")
            payload = read_json(safe_file(root, path))
            count = payload.get("numberMatched", payload.get("totalFeatures"))
            if count is None or str(count) == "unknown" or int(count) != response["feature_count"]:
                raise ValueError("DIPUL page matched count is inconsistent.")
            validate_zones({**payload, "numberMatched": len(payload["features"])}, area)
            request = receipts[path].get("request", {})
            params = request.get("params", {})
            if (
                request.get("url") != manifest["config"]["dipul_url"]
                or params.get("typeNames") != response["type_name"]
                or params.get("startIndex") != len(features)
                or params.get("bbox")
                != ",".join(map(str, area.as_tuple())) + ",urn:ogc:def:crs:OGC:1.3:CRS84"
            ):
                raise ValueError("DIPUL request scope/pagination mismatch.")
            features.extend(payload["features"])
        validate_zones(
            {
                "type": "FeatureCollection",
                "numberMatched": response["feature_count"],
                "features": features,
            },
            area,
        )
    return manifest


def rebuild_study(source, output):
    """Rebuild into a new directory from a verified complete snapshot, without network."""
    source, output = Path(source), Path(output)
    if (source / MANIFEST).exists():
        manifest = read_json(safe_file(source, MANIFEST))
        if manifest.get("schema_version") != 1 or manifest.get("kind") != "regional-source-study":
            raise ValueError("Unsupported source snapshot.")
    else:
        # Recover a failure during derivation when all originals were already received.
        progress = read_json(safe_file(source, PROGRESS))
        area = validate_study(progress["config"])
        store = PayloadStore(source, progress["config"], resume=True, offline=True)
        dipul = fetch_dipul(store, area)
        osm_paths = (
            ["raw/osm-source.osm.pbf"]
            if progress["config"].get("osm_format") == "geofabrik-pbf"
            else [
                path
                for path, _ in osm_leaves(
                    area, progress["config"], progress.get("osm_subdivisions", [])
                )
            ]
        )
        recorded = {record["path"] for record in progress["files"]}
        if not {"raw/ghsl.zip", *osm_paths}.issubset(recorded):
            raise ValueError("Offline rebuild requires all original OSM/GHSL responses.")
        manifest = {
            "config": progress["config"],
            "files": progress["files"],
            "osm_raw_paths": osm_paths,
            "osm_subdivisions": progress.get("osm_subdivisions", []),
            "sources": {"dipul": dipul},
        }
    validate_study(manifest["config"])
    originals = [record for record in manifest["files"] if record["path"].startswith("raw/")]
    for record in originals:
        if checksum(safe_file(source, record["path"])) != record["sha256"]:
            raise ValueError("Original payload checksum mismatch; cannot rebuild.")
    output.mkdir(parents=True, exist_ok=False)
    for record in originals:
        target = output / record["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(safe_file(source, record["path"]), target)
    return build_derived(
        output,
        manifest["config"],
        originals,
        manifest["osm_raw_paths"],
        original_sources=manifest["sources"]["dipul"],
        splits=manifest.get("osm_subdivisions", []),
    )
