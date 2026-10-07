"""Offline regional preparation and native population queries; no route search."""

import json
import math
import re
from collections import Counter
from copy import deepcopy
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import Window
from shapely.geometry import LineString, Point, box, mapping, shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

from uas_planner.acquisition.study import finite_number, inspect_study
from uas_planner.core.costs import RULES, analyze_feature
from uas_planner.core.experiment import checksum, read_json, safe_file
from uas_planner.core.risk import RiskModel, signature
from uas_planner.storage.dataset import load_dataset

VERSION = "regional-constraints-v1"
LEGAL_SOURCE = "https://www.gesetze-im-internet.de/luftvo_2015/__21h.html"
MAX_QUERY_CELLS = 100000
MAX_TERRAIN_PIXELS = 4000000


def validate_scenario(config):
    if not isinstance(config, dict):
        raise ValueError("Scenario must be an object.")
    finite_number(config["agl_m"], 100, 120, "AGL altitude")
    finite_number(config["speed_m_s"], 25, 35, "Cruise speed")
    finite_number(config.get("clearance_m", 0), 0, 1000, "Safety clearance")
    finite_number(config.get("vertical_clearance_m", 0), 0, 1000, "Vertical clearance")
    if config.get("scenario") not in ("civil", "BOS"):
        raise ValueError("Scenario must be civil or BOS; neither implies an exemption.")
    if config.get("building_unknown_height", "unresolved") not in ("unresolved", "exclude"):
        raise ValueError("Unknown building-height policy.")
    start, end = [datetime.fromisoformat(config[k]) for k in ("mission_start", "mission_end")]
    if start.tzinfo is None or end.tzinfo is None or not 0 < (end - start).total_seconds() <= 86400:
        raise ValueError(
            "An explicit offset-aware scenario interval of at most 24 hours is required."
        )
    zone = ZoneInfo(config.get("timezone", "Europe/Berlin"))
    if any(t.utcoffset() != t.astimezone(zone).utcoffset() for t in (start, end)):
        raise ValueError("Scenario offsets must match the declared timezone.")
    if not isinstance(config.get("zone_assessments", {}), dict):
        raise ValueError("Zone assessments must be an object keyed by source ID.")
    return config


def metric_geometry(geometry):
    return transform(Transformer.from_crs(4326, 25832, always_xy=True).transform, geometry)


def query_geometry(coordinates, clearance_m=0):
    if not isinstance(coordinates, (list, tuple)) or not coordinates:
        raise ValueError("Supply at least one coordinate pair.")
    for pair in coordinates:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("Expected longitude/latitude pairs.")
        finite_number(pair[0], -180, 180, "Longitude")
        finite_number(pair[1], -90, 90, "Latitude")
    geometry = metric_geometry(
        Point(coordinates[0]) if len(set(map(tuple, coordinates))) == 1 else LineString(coordinates)
    )
    finite_number(clearance_m, 0, 1000, "Safety clearance")
    # Circumscribed GEOS approximation, matching the existing routing checker.
    return geometry.buffer(clearance_m / math.cos(math.pi / 64)) if clearance_m else geometry


class PopulationInspector:
    """Windowed native-cell queries. Counts are not risk or legal restrictions."""

    def __init__(self, directory, manifest):
        self.path = safe_file(directory, manifest["sources"]["ghsl"]["path"])
        self.source = manifest["sources"]["ghsl"]
        self.epoch = manifest["config"]["ghsl_epoch"]

    def query(self, geometry, *, input_crs=25832, include_cells=False):
        if geometry.is_empty or not geometry.is_valid:
            raise ValueError("Population query requires valid nonempty geometry.")
        with rasterio.open(self.path) as src:
            native = transform(
                Transformer.from_crs(input_crs, src.crs, always_xy=True).transform, geometry
            )
            if geometry.area > 0:
                outside = native.difference(box(*src.bounds)).area
            else:
                outside = native.difference(box(*src.bounds)).length
            left, top = ~src.transform @ (native.bounds[0], native.bounds[3])
            right, bottom = ~src.transform @ (native.bounds[2], native.bounds[1])
            # Include both neighbours when a point/line lies on a native cell edge.
            # Polygon queries discard zero-area touches below.
            c0, r0 = max(0, math.floor(left) - 1), max(0, math.floor(top) - 1)
            c1, r1 = min(src.width, math.floor(right) + 1), min(src.height, math.floor(bottom) + 1)
            if max(0, c1 - c0) * max(0, r1 - r0) > MAX_QUERY_CELLS:
                raise ValueError("Population query exceeds native-cell resource limit.")
            values = src.read(
                1, window=Window(c0, r0, max(0, c1 - c0), max(0, r1 - r0)), masked=True
            )
            known_area, unknown_area, weighted, crossed_sum = 0.0, 0.0, 0.0, 0.0
            known, unknown, zeros, cells = 0, 0, 0, []
            reverse = Transformer.from_crs(src.crs, 4326, always_xy=True).transform
            for row in range(r0, r1):
                for col in range(c0, c1):
                    x, y = src.transform @ (col, row)
                    pixel = box(x, y - 100, x + 100, y)
                    if not pixel.intersects(native):
                        continue
                    intersection = pixel.intersection(native)
                    if native.area > 0 and intersection.area <= 0:
                        continue
                    raw = values[row - r0, col - c0]
                    value = None if np.ma.is_masked(raw) or not np.isfinite(raw) else float(raw)
                    if value is not None and value < 0:
                        raise ValueError("Negative population outside declared NoData.")
                    if value is None:
                        unknown += 1
                        unknown_area += intersection.area
                    else:
                        known += 1
                        zeros += value == 0
                        known_area += intersection.area
                        weighted += value * intersection.area / 10000
                        crossed_sum += value
                    if include_cells:
                        cells.append(
                            {
                                "type": "Feature",
                                "id": f"{row}:{col}",
                                "geometry": mapping(transform(reverse, pixel)),
                                "properties": {
                                    "people_per_cell": value,
                                    "status": "unknown" if value is None else "known",
                                    "native_support_m": 100,
                                    "epoch": self.epoch,
                                },
                            }
                        )
            complete = unknown == 0 and outside <= 1e-6 and known > 0
            if native.geom_type == "Point":
                complete &= box(*src.bounds).covers(native)
            result = {
                "product": self.source["product"],
                "epoch": self.epoch,
                "units": self.source["units"],
                "native_support_m": 100,
                "area_basis": "native ESRI:54009 planar cell intersections; distinct from geodesic study area",
                "known_cells": known,
                "unknown_cells": unknown,
                "known_zero_cells": zeros,
                "known_area_m2": known_area,
                "unknown_area_m2": unknown_area,
                "outside_support_measure": outside,
                "complete_support": complete,
                "estimated_people": weighted if complete and native.area > 0 else None,
                "observed_estimated_people": weighted if native.area > 0 else None,
                "crossed_cell_population_sum": crossed_sum if complete else None,
                "observed_crossed_cell_population_sum": crossed_sum,
                "interpretation": "Area-weighted native counts assume uniform population within each cell; crossed-cell sum counts whole cells, not people exposed to a flight.",
                "routing_cost": False,
            }
            if include_cells:
                result["layer"] = {"type": "FeatureCollection", "features": cells}
            return result

    def svg(self, output):
        """Standalone native crop preview; preserves zero and missing visually."""
        with rasterio.open(self.path) as src:
            if src.width * src.height > MAX_QUERY_CELLS:
                raise ValueError("Population preview exceeds native-cell resource limit.")
            values = src.read(1, masked=True)
            valid = values.compressed()
            if np.any(~np.isfinite(valid)) or np.any(valid < 0):
                raise ValueError("Invalid population preview values.")
            peak = float(valid.max()) if valid.size else 0
            width = max(src.width, 340)
            parts = [
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width * 2}" height="{(src.height + 62) * 2}" viewBox="0 0 {width} {src.height + 62}">',
                '<rect width="100%" height="100%" fill="white"/>',
                '<defs><pattern id="missing" width="4" height="4" patternUnits="userSpaceOnUse"><path d="M0 0L4 4" stroke="#d10080"/></pattern></defs>',
                f'<text x="4" y="12" font-size="10">{escape(self.source["product"])} / {self.epoch} / native 100 m</text>',
            ]
            for row in range(src.height):
                for col in range(src.width):
                    raw = values[row, col]
                    if np.ma.is_masked(raw):
                        fill = "url(#missing)"
                    elif raw == 0:
                        fill = "#ffffff"
                    else:
                        level = math.log1p(float(raw)) / math.log1p(peak)
                        shade = round(245 - 210 * level)
                        fill = f"rgb({shade},{shade},230)"
                    parts.append(
                        f'<rect x="{col}" y="{row + 20}" width="1" height="1" fill="{fill}"/>'
                    )
            parts.extend(
                [
                    f'<text x="4" y="{src.height + 34}" font-size="9">White: known zero. Magenta hatch: NoData. Blue: log(count+1).</text>',
                    f'<text x="4" y="{src.height + 46}" font-size="9">Peak: {peak:.2f} people/cell. Full aligned crop includes edge margin.</text>',
                    f'<text x="4" y="{src.height + 58}" font-size="9">Population inspection only; no routing cost or legal prohibition.</text>',
                    "</svg>",
                ]
            )
            with Path(output).open("x", encoding="utf-8") as stream:
                stream.write("\n".join(parts))


class TerrainSupport:
    """Sparse native DGM1 tiles; conservative bounds over complete query windows."""

    def __init__(self, directory=None):
        self.root = Path(directory) if directory else None
        self.manifest = read_json(safe_file(directory, "terrain.json")) if directory else None
        self.tiles = []
        if self.manifest:
            if (
                self.manifest.get("kind") != "bounded-native-terrain"
                or self.manifest.get("schema_version") != 1
            ):
                raise ValueError("Unsupported terrain manifest.")
            if self.manifest.get("source", "").startswith("https://"):
                metadata = self.manifest.get("metadata", {})
                if set(metadata) != {"capabilities.xml", "description.xml"}:
                    raise ValueError("Terrain service metadata receipts are incomplete.")
                for name, entry in metadata.items():
                    if checksum(safe_file(directory, name)) != entry["sha256"]:
                        raise ValueError("Terrain metadata checksum mismatch.")
                actual = [tuple(tile["requested_bounds"]) for tile in self.manifest["tiles"]]
                if len(actual) != len(set(actual)) or set(actual) != set(
                    map(tuple, self.manifest["planned_bounds"])
                ):
                    raise ValueError(
                        "Terrain tile coverage differs from the declared acquisition plan."
                    )
            for entry in self.manifest["tiles"]:
                path = safe_file(directory, entry["path"])
                if checksum(path) != entry["sha256"]:
                    raise ValueError("Terrain checksum mismatch.")
                with rasterio.open(path) as src:
                    if (
                        src.crs.to_epsg() != 25832
                        or src.res != (1, 1)
                        or src.count != 1
                        or src.transform.b
                        or src.transform.d
                    ):
                        raise ValueError("Terrain must retain the native EPSG:25832 1 m grid.")
                    if list(src.bounds) != entry["bounds"]:
                        raise ValueError("Terrain bounds mismatch.")
                    if "requested_bounds" in entry and not box(*src.bounds).covers(
                        box(*entry["requested_bounds"])
                    ):
                        raise ValueError("Terrain response does not cover its requested tile.")
                    if "requested_bounds" in entry:
                        requested = entry["requested_bounds"]
                        if (
                            src.width > requested[2] - requested[0] + 2
                            or src.height > requested[3] - requested[1] + 2
                        ):
                            raise ValueError(
                                "Terrain response exceeds its bounded native tile dimensions."
                            )
                    self.tiles.append((path, box(*src.bounds)))

    def bounds(self, geometry):
        selected = [
            (path, footprint) for path, footprint in self.tiles if footprint.intersects(geometry)
        ]
        covered = unary_union([footprint for _, footprint in selected])
        complete = covered.covers(geometry)
        low, high, pixels = None, None, 0
        for path, footprint in selected:
            with rasterio.open(path) as src:
                intersection = geometry.intersection(footprint)
                if intersection.is_empty:
                    continue
                x0, y0, x1, y1 = intersection.bounds
                c0, r0 = ~src.transform @ (x0, y1)
                c1, r1 = ~src.transform @ (x1, y0)
                c0, r0 = (
                    min(src.width - 1, max(0, math.floor(c0))),
                    min(src.height - 1, max(0, math.floor(r0))),
                )
                c1, r1 = (
                    min(src.width, max(c0 + 1, math.floor(c1) + 1)),
                    min(src.height, max(r0 + 1, math.floor(r1) + 1)),
                )
                pixels += max(0, c1 - c0) * max(0, r1 - r0)
                if pixels > MAX_TERRAIN_PIXELS:
                    return {
                        "status": "resource_limit",
                        "minimum_m": None,
                        "maximum_m": None,
                        "pixels": pixels,
                    }
                values = src.read(1, window=Window(c0, r0, c1 - c0, r1 - r0), masked=True)
                missing = (
                    np.ma.getmaskarray(values) | ~np.isfinite(values.data) | (values.data == -9999)
                )
                complete &= not bool(missing.any()) and values.size > 0
                valid = values.data[~missing]
                if valid.size:
                    low = float(valid.min()) if low is None else min(low, float(valid.min()))
                    high = float(valid.max()) if high is None else max(high, float(valid.max()))
        return {
            "status": "known" if complete and low is not None else "unknown",
            "minimum_m": low if complete else None,
            "maximum_m": high if complete else None,
            "pixels": pixels,
            "vertical_datum": self.manifest["vertical_datum"] if self.manifest else None,
            "method": "conservative complete native bounding windows; not center samples or 3D clearance",
        }


def building_height(tags):
    value = tags.get("height")
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) and value >= 0 else None
    if isinstance(value, str) and re.fullmatch(r"\s*\d+(?:\.\d+)?\s*(?:m|ft)?\s*", value):
        height = float(re.search(r"\d+(?:\.\d+)?", value)[0]) * (
            0.3048 if value.strip().endswith("ft") else 1
        )
        return height if math.isfinite(height) else None
    # Levels, roof estimates and mixed heights are not measured height bounds.
    return None


def vertical_state(properties, agl, terrain):
    limits = []
    for prefix in ("lower", "upper"):
        raw = properties.get(prefix + "_limit_altitude")
        if raw is None:
            limits.append(None)
            continue
        unit, reference = (
            properties.get(prefix + "_limit_unit"),
            properties.get(prefix + "_limit_alt_ref"),
        )
        if (
            isinstance(raw, bool)
            or not isinstance(raw, (int, float))
            or not math.isfinite(raw)
            or unit not in ("m", "ft")
        ):
            return "unresolved", "Unknown altitude value or unit."
        limit = raw * (0.3048 if unit == "ft" else 1)
        if reference == "AGL":
            interval = (agl, agl)
        elif (
            reference == "MSL"
            and terrain["status"] == "known"
            and terrain.get("vertical_datum") == "MSL"
        ):
            interval = (agl + terrain["minimum_m"], agl + terrain["maximum_m"])
        else:
            return (
                "unresolved",
                "Vertical reference requires compatible bounded terrain; NHN is not silently treated as MSL.",
            )
        limits.append((limit, interval))
    lower, upper = limits
    if (
        lower
        and upper
        and properties.get("lower_limit_alt_ref") == properties.get("upper_limit_alt_ref")
        and lower[0] > upper[0]
    ):
        return "unresolved", "Inverted vertical limits."
    if lower and lower[1][1] < lower[0] or upper and upper[1][0] > upper[0]:
        return "outside_vertical", "Complete query altitude interval is outside reported limits."
    return (
        "unresolved",
        "Vertical overlap or absent limits; permission, time and scenario applicability unverified.",
    )


def assessed_zone(record, scenario):
    """Optional evidence-backed scenario assertions; never infer operator consent."""
    assessment = scenario.get("zone_assessments", {}).get(record["source"])
    if assessment is None:
        return "unresolved", "No evidence-backed scenario assessment."
    if (
        assessment.get("source_signature") != record["source_signature"]
        or not isinstance(assessment.get("evidence"), str)
        or not assessment["evidence"].strip()
    ):
        raise ValueError("Zone assessment needs matching source signature and explicit evidence.")
    if assessment.get("state") not in ("prohibited", "conditional_allowed"):
        raise ValueError("Unknown zone assessment state.")
    times = [datetime.fromisoformat(assessment[k]) for k in ("valid_from", "valid_until")]
    if any(t.tzinfo is None for t in times) or times[1] <= times[0]:
        raise ValueError("Zone assessment requires an offset-aware positive validity interval.")
    altitude = assessment["agl_interval_m"]
    if len(altitude) != 2:
        raise ValueError("Zone assessment requires altitude interval bounds.")
    for value in altitude:
        finite_number(value, 0, 10000, "Assessed altitude")
    if altitude[0] > altitude[1]:
        raise ValueError("Inverted assessed altitude interval.")
    start, end = [datetime.fromisoformat(scenario[k]) for k in ("mission_start", "mission_end")]
    if (
        assessment.get("scenario") != scenario["scenario"]
        or not altitude[0] <= scenario["agl_m"] <= altitude[1]
    ):
        return "unresolved", "Scenario/altitude outside the documented assessment."
    if assessment["state"] == "prohibited" and start < times[1] and end > times[0]:
        return "blocked", "Evidence-backed prohibition overlaps the scenario interval."
    if times[0] <= start and end <= times[1] and assessment["state"] == "conditional_allowed":
        conditions = assessment.get("conditions_satisfied")
        if (
            not isinstance(conditions, list)
            or not conditions
            or not all(isinstance(c, str) and c.strip() for c in conditions)
        ):
            return "unresolved", "Conditional allowance lacks satisfied-condition evidence."
        return (
            "conditional_allowed",
            "Supplied evidence asserts all listed conditions for the complete scenario.",
        )
    return "unresolved", "Assessment does not cover the complete scenario interval."


class RegionalConstraints:
    """Shared indexed point/full-motion/connector checker, independent of algorithms."""

    def __init__(self, directory, scenario, *, terrain_directory=None):
        self.root = Path(directory)
        self.manifest = inspect_study(directory)
        self.scenario = validate_scenario(deepcopy(scenario))
        scenario = self.scenario
        self.boundary = metric_geometry(
            box(*[self.manifest["config"]["bounds"][k] for k in ("west", "south", "east", "north")])
        )
        self.terrain = TerrainSupport(terrain_directory)
        self.records, self.diagnostics, self.risk_records = [], [], []
        frame, metadata = load_dataset(self.root / "osm", compact=True)
        projected_geometries = frame.to_crs(25832).geometry
        for row, tags, projected in zip(
            frame.itertuples(index=False),
            frame.attrs["source_tags"],
            projected_geometries,
            strict=True,
        ):
            geometry = row.geometry
            ident = f"{row.element_type}/{row.osm_id}"
            if not geometry.is_valid or geometry.geom_type == "GeometryCollection":
                self.diagnostics.append(
                    {
                        "source": ident,
                        "status": "invalid_geometry"
                        if not geometry.is_valid
                        else "unsupported_geometry",
                        "building": tags.get("building") is not None,
                    }
                )
                # Do not repair shapes or infer the extent of invalid/collection geometries.
                continue
            if analyze_feature(tags, "building") is None:
                continue
            if projected.is_empty or not projected.is_valid:
                self.diagnostics.append(
                    {"source": ident, "status": "invalid_projected_geometry", "building": True}
                )
                continue
            if geometry.geom_type not in ("Polygon", "MultiPolygon"):
                self.diagnostics.append(
                    {"source": ident, "status": "non_polygon_building", "building": True}
                )
                continue
            height = building_height(tags)
            threshold = scenario["agl_m"] - scenario.get("vertical_clearance_m", 0)
            state = (
                "blocked"
                if height is not None and height >= threshold
                else "clear"
                if height is not None
                else "blocked"
                if scenario.get("building_unknown_height") == "exclude"
                else "unresolved"
            )
            self.records.append(
                {
                    "source": ident,
                    "category": "building_obstacle",
                    "state": state,
                    "geometry": projected,
                    "height_m": height,
                    "basis": "reported height plus configured vertical clearance"
                    if height is not None
                    else "missing height; conservative footprint assumption"
                    if state == "blocked"
                    else "missing height",
                }
            )
            self.risk_records.append((geometry, tags, row.element_type, str(row.osm_id)))
        for response in self.manifest["sources"]["dipul"]["responses"]:
            for page in response["pages"]:
                for feature in read_json(safe_file(directory, page))["features"]:
                    self.records.append(
                        {
                            "source": f"{response['type_name']}/{feature['id']}",
                            "category": "conditional_zone"
                            if "21h" in str(feature["properties"].get("legal_ref", ""))
                            else "zone_applicability_unresolved",
                            "state": "unresolved",
                            "geometry": metric_geometry(shape(feature["geometry"])),
                            "properties": feature["properties"],
                            "layer": response["type_name"],
                            "source_signature": signature(feature),
                            "basis": LEGAL_SOURCE,
                            "buffer_m": 0,
                            "buffer_basis": "use delivered DIPUL zone footprint; no unverified second legal buffer",
                        }
                    )
        self.tree = STRtree([r["geometry"] for r in self.records])
        available = {r["source"] for r in self.records if r["category"] != "building_obstacle"}
        if not set(scenario.get("zone_assessments", {})).issubset(available):
            raise ValueError("Zone assessment references a missing source ID.")
        for record in self.records:
            if record["category"] != "building_obstacle":
                record["state"] = assessed_zone(record, scenario)[0]
        self.provenance = {
            "version": VERSION,
            "study_signature": signature(self.manifest),
            "scenario": scenario,
            "terrain_signature": signature(self.terrain.manifest),
            "classification_sha256": signature(RULES),
            "risk_weights": [0.9, 0.1],
            "risk_overlap": "maximum_building_score",
            "ghsl_routing_cost": False,
            "diagnostics": self.diagnostics,
            "osm_sha256": metadata["sha256"],
        }
        self.provenance["model_signature"] = signature(self.provenance)
        self.population = PopulationInspector(directory, self.manifest)

    def check(self, coordinates, *, mode="strict"):
        if mode not in ("strict", "research"):
            raise ValueError("Unknown planning mode.")
        query = query_geometry(coordinates, self.scenario.get("clearance_m", 0))
        terrain = self.terrain.bounds(query)
        blocked, unresolved, assumptions, zones = [], [], [], []
        if not self.boundary.covers(query):
            blocked.append(
                {
                    "source": "boundary",
                    "reason": "Complete motion or safety envelope leaves supported region.",
                }
            )
        if terrain["status"] != "known":
            unresolved.append(
                {
                    "source": "terrain",
                    "reason": "Complete motion has unknown or resource-limited terrain support.",
                }
            )
        unknown_building_geometry = [d for d in self.diagnostics if d["building"]]
        if unknown_building_geometry:
            unresolved.append(
                {
                    "source": "OSM geometry",
                    "reason": "Invalid/unsupported source extents prevent complete constraint validation.",
                    "count": len(unknown_building_geometry),
                }
            )
        for index in self.tree.query(query, predicate="intersects"):
            record = self.records[int(index)]
            if record["category"] == "building_obstacle":
                reason = {
                    "source": record["source"],
                    "reason": record["basis"],
                    "height_m": record["height_m"],
                }
                if record["state"] == "blocked":
                    blocked.append(reason)
                elif record["state"] == "unresolved":
                    unresolved.append(reason)
            else:
                state, reason = vertical_state(
                    record["properties"], self.scenario["agl_m"], terrain
                )
                if state != "outside_vertical":
                    assessed, assessment_reason = assessed_zone(record, self.scenario)
                    if assessed != "unresolved":
                        state, reason = assessed, assessment_reason
                zones.append(
                    {
                        "source": record["source"],
                        "category": "prohibited" if state == "blocked" else record["category"],
                        "state": state,
                        "reason": reason,
                        "source_signature": record["source_signature"],
                        "properties": record["properties"],
                        "buffer_m": record["buffer_m"],
                        "buffer_basis": record["buffer_basis"],
                    }
                )
                if state == "blocked":
                    blocked.append({"source": record["source"], "reason": reason})
                elif state == "conditional_allowed":
                    assumptions.append({"source": record["source"], "reason": reason})
                elif state != "outside_vertical":
                    target = unresolved if mode == "strict" else assumptions
                    target.append({"source": record["source"], "reason": reason})
        temporary = {
            "source": "DIPUL",
            "reason": "Temporary/NOTAM completeness and scenario applicability unverified; acquisition dates are not validity.",
        }
        (unresolved if mode == "strict" else assumptions).append(temporary)
        return {
            "state": "blocked" if blocked else "unresolved" if unresolved else "permitted",
            "blocked": blocked,
            "unresolved": unresolved,
            "assumptions": assumptions,
            "mode": mode,
            "terrain": terrain,
            "zones": zones,
            "model_signature": self.provenance["model_signature"],
        }

    def risk_model(
        self, *, background_cost=None, mode="strict", risk_weight=0.9, distance_weight=0.1
    ):
        """Reuse approved soft semantics; unsafe source support remains explicit."""
        if mode not in ("strict", "research"):
            raise ValueError("Unknown planning mode.")
        if any(
            d["building"] and (mode == "strict" or d["status"] != "non_polygon_building")
            for d in self.diagnostics
        ):
            raise ValueError(
                "Building risk support unresolved; invalid buildings cannot be omitted."
            )
        reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform
        return RiskModel(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": mapping(g),
                        "properties": {**tags, "element_type": element, "osm_id": ident},
                    }
                    for g, tags, element, ident in self.risk_records
                ],
            },
            mapping(transform(reverse, self.boundary)),
            background_cost=background_cost,
            source=self.provenance,
            risk_weight=risk_weight,
            distance_weight=distance_weight,
            safety_distance_m=self.scenario.get("clearance_m", 0),
        )

    def summary(self):
        endpoints = [
            {
                "id": s["id"],
                "coordinate_status": s["coordinate_status"],
                **self.check([[s["longitude"], s["latitude"]]]),
            }
            for s in self.manifest["config"]["locations"]
        ]
        return {
            "kind": "regional-constraint-preparation",
            "schema_version": 1,
            "provenance": self.provenance,
            "counts": dict(Counter(f"{r['category']}:{r['state']}" for r in self.records)),
            "geometry_diagnostic_counts": dict(Counter(d["status"] for d in self.diagnostics)),
            "blocked_buildings": [
                {k: r[k] for k in ("source", "height_m", "basis")}
                for r in self.records
                if r["category"] == "building_obstacle" and r["state"] == "blocked"
            ],
            "terrain_coverage": {
                "tile_count": len(self.terrain.tiles),
                "grid_covers_region": unary_union([g for _, g in self.terrain.tiles]).covers(
                    self.boundary
                ),
                "vertical_datum": self.terrain.manifest["vertical_datum"]
                if self.terrain.manifest
                else None,
                "value_completeness": "NoData and native pixel budget checked independently for each complete query",
            },
            "endpoints": endpoints,
            "population": self.population.query(self.boundary),
            "readiness": "constraint inspection only; routing integration belongs to Part 3",
        }


def prepare_regional(directory, scenario, output, *, terrain_directory=None):
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    model = RegionalConstraints(directory, scenario, terrain_directory=terrain_directory)
    result = model.summary()
    # Completion output is written only after all checks/queries succeed.
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return result
