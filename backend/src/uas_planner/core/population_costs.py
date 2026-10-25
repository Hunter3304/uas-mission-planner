"""Count-conserving 250 m population classes; independent of route objectives."""

import json
from bisect import bisect_right
from copy import deepcopy
from functools import lru_cache
from math import ceil, floor, isfinite
from pathlib import Path
from time import perf_counter

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import Window
from shapely import segmentize
from shapely.geometry import box, mapping, shape
from shapely.ops import transform
from shapely.strtree import STRtree

from uas_planner.core.area import StudyRegion
from uas_planner.core.experiment import checksum, raster_metadata, read_json, safe_file
from uas_planner.core.risk import signature

VERSION = "ramke-population-250m-v1"
CELL_M = 250
AREA_TOLERANCE_M2 = 1e-6
MAX_TARGET_CELLS = 100000
MAX_WINDOW_PIXELS = 10000
MAX_DISPLAY_CELLS = 10000
MAX_DISPLAY_BYTES = 5 * 1024 * 1024
PREPARATION_SECONDS = 90


class PopulationResourceLimit(ValueError):
    """A bounded preparation/display operation could not be completed."""


def check_deadline(deadline, cancel=None):
    if cancel is not None and cancel():
        raise PopulationResourceLimit("Population preparation cancelled.")
    if perf_counter() >= deadline:
        raise PopulationResourceLimit("Population preparation deadline reached.")


def classify_density(density, maximum):
    """Exact lower-inclusive cutoffs; no rounding or epsilon-based bin shifting."""
    if not all(isfinite(v) and v >= 0 for v in (density, maximum)) or density > maximum:
        raise ValueError("Invalid population density/reference.")
    if maximum == 0:
        return 0
    return bisect_right([maximum * (i / 5) for i in range(1, 5)], density)


def aggregate_native(src, polygon, *, deadline=float("inf"), cancel=None):
    """Area-weight a polygon already in the native raster plane, without resampling."""
    check_deadline(deadline, cancel)
    if polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
        raise ValueError("Population aggregation requires a valid positive-area polygon.")
    if src.res != (100, 100) or src.transform.b or src.transform.d or src.transform.e != -100:
        raise ValueError("Population aggregation requires north-up native 100 m cells.")
    left, top = ~src.transform @ (polygon.bounds[0], polygon.bounds[3])
    right, bottom = ~src.transform @ (polygon.bounds[2], polygon.bounds[1])
    c0, r0 = max(0, floor(left)), max(0, floor(top))
    c1, r1 = min(src.width, ceil(right)), min(src.height, ceil(bottom))
    width, height = max(0, c1 - c0), max(0, r1 - r0)
    if width * height > MAX_WINDOW_PIXELS:
        raise PopulationResourceLimit("Population native window exceeds pixel limit.")
    values = src.read(1, window=Window(c0, r0, width, height), masked=True)
    known_area, nodata_area, people = 0.0, 0.0, 0.0
    outside = polygon.difference(box(*src.bounds)).area
    for row in range(r0, r1):
        check_deadline(deadline, cancel)
        for col in range(c0, c1):
            x, y = src.transform @ (col, row)
            overlap = polygon.intersection(box(x, y - 100, x + 100, y)).area
            if overlap <= 0:
                continue
            raw = values[row - r0, col - c0]
            if np.ma.is_masked(raw):
                nodata_area += overlap
            elif not isfinite(float(raw)) or float(raw) < 0:
                raise ValueError("Invalid population outside declared NoData.")
            else:
                known_area += overlap
                people += float(raw) * overlap / 10000
    complete = known_area > 0 and nodata_area + outside <= AREA_TOLERANCE_M2
    density = people / known_area * 1_000_000 if complete else None
    if not isfinite(people) or density is not None and not isfinite(density):
        raise ValueError("Population aggregate overflow.")
    return {
        "status": "known" if complete else "unknown",
        "estimated_people": people if complete else None,
        "observed_estimated_people": people,
        "people_per_km2": density,
        "native_support_area_m2": polygon.area,
        "known_area_m2": known_area,
        "nodata_area_m2": nodata_area,
        "outside_area_m2": outside,
        "unknown_area_m2": nodata_area + outside,
    }


class PopulationSurface:
    """Prepared study-wide classes; subsets never change the reference or lattice."""

    def __init__(self, boundary, source_path, source, epoch, *, deadline=None, cancel=None):
        deadline = perf_counter() + PREPARATION_SECONDS if deadline is None else deadline
        check_deadline(deadline, cancel)
        if boundary.is_empty or not boundary.is_valid or boundary.area <= 0:
            raise ValueError("Invalid metric population study boundary.")
        minx, miny, maxx, maxy = boundary.bounds
        x0, y0 = floor(minx / CELL_M) * CELL_M, floor(miny / CELL_M) * CELL_M
        nx, ny = ceil((maxx - x0) / CELL_M), ceil((maxy - y0) / CELL_M)
        if nx * ny > MAX_TARGET_CELLS:
            raise PopulationResourceLimit("Population target grid exceeds 100,000 cells.")
        native_forward = Transformer.from_crs(25832, "ESRI:54009", always_xy=True).transform
        reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform
        self._cells = []
        with rasterio.open(source_path) as src:
            if src.crs is None or src.crs.to_string() != "ESRI:54009":
                raise ValueError("Unexpected population native CRS.")
            for row in range(ny):
                for col in range(nx):
                    check_deadline(deadline, cancel)
                    polygon = boundary.intersection(
                        box(
                            x0 + col * CELL_M,
                            y0 + row * CELL_M,
                            x0 + (col + 1) * CELL_M,
                            y0 + (row + 1) * CELL_M,
                        )
                    )
                    if polygon.is_empty or polygon.area <= 0:
                        continue
                    # Densify curved CRS transformations, with shared lattice edges.
                    native = transform(native_forward, segmentize(polygon, 25))
                    properties = aggregate_native(src, native, deadline=deadline, cancel=cancel)
                    properties.update(
                        layer_kind="population_cost",
                        cell_size_m=CELL_M,
                        native_support_m=100,
                        epoch=epoch,
                        row=row,
                        col=col,
                        metric_area_m2=polygon.area,
                    )
                    self._cells.append(
                        (
                            polygon,
                            {
                                "type": "Feature",
                                "id": f"population250:{row}:{col}",
                                "geometry": mapping(transform(reverse, polygon)),
                                "properties": properties,
                            },
                        )
                    )
        complete = [f["properties"] for _, f in self._cells if f["properties"]["status"] == "known"]
        maximum = max((p["people_per_km2"] for p in complete), default=None)
        bins = []
        if maximum is not None:
            for score in range(5):
                lower, upper = maximum * (score / 5), maximum * ((score + 1) / 5)
                bins.append(
                    {
                        "score": score,
                        "lower_people_per_km2": lower,
                        "upper_people_per_km2": upper,
                        "upper_inclusive": score == 4 or maximum == 0 and score == 0,
                        "nominal_100m_count_bounds": [lower * 0.01, upper * 0.01],
                        "nominal_250m_count_bounds": [lower * 0.0625, upper * 0.0625],
                    }
                )
        counts = {str(i): 0 for i in range(5)}
        for _, feature in self._cells:
            p = feature["properties"]
            density = p["people_per_km2"]
            p["risk_score"] = None if density is None else classify_density(density, maximum)
            p["normalized_density"] = (
                None if density is None else density / maximum if maximum else 0
            )
            if p["risk_score"] is not None:
                counts[str(p["risk_score"])] += 1
                selected = bins[p["risk_score"]]
                p["density_bin"] = selected
                p["actual_cell_count_bounds"] = [
                    selected[key] * p["native_support_area_m2"] / 1_000_000
                    for key in ("lower_people_per_km2", "upper_people_per_km2")
                ]
        self._metadata = {
            "version": VERSION,
            "state": "ready" if complete else "unresolved",
            "source": deepcopy(source),
            "epoch": epoch,
            "analysis_crs": "EPSG:25832",
            "native_crs": "ESRI:54009",
            "cell_size_m": CELL_M,
            "native_support_m": 100,
            "origin_metric": [x0, y0],
            "study_boundary_metric": mapping(boundary),
            "normalization_scope": "complete_saved_study",
            "maximum_people_per_km2": maximum,
            "all_zero": maximum == 0,
            "bins": bins,
            "class_counts": counts,
            "cell_count": len(self._cells),
            "known_cells": len(complete),
            "unknown_cells": len(self._cells) - len(complete),
            "observed_estimated_people": sum(
                f["properties"]["observed_estimated_people"] for _, f in self._cells
            ),
            "estimated_people": sum(p["estimated_people"] for p in complete)
            if len(complete) == len(self._cells)
            else None,
            "area_tolerance_m2": AREA_TOLERANCE_M2,
            "densify_m": 25,
            "area_basis": "native ESRI:54009 planar intersection areas",
            "aggregation": "native count multiplied by intersected native-cell fraction; uniform density within each native cell",
            "classification": "five equal-width intervals over [0,1], lower-inclusive; last upper-inclusive; no rounding",
            "interpretation": "Ordinal population classes, not probabilities. Score 0 can contain people. NoData is not zero. Route integration is deferred to Part 2.",
            "routing_cost": False,
        }
        self._metadata["identity"] = signature(self._metadata)
        self._display_tree = STRtree([shape(f["geometry"]) for _, f in self._cells])
        check_deadline(deadline, cancel)

    @property
    def metadata(self):
        return deepcopy(self._metadata)

    def display(self, bbox=None):
        """Bounded geographic subset, preserving full-study classification metadata."""
        metadata = self.metadata
        if len(json.dumps(metadata, allow_nan=False).encode()) > 60000:
            raise PopulationResourceLimit("Population display metadata exceeds size limit.")
        view = None if bbox is None else box(*bbox)
        indices = (
            range(len(self._cells))
            if view is None
            else sorted(self._display_tree.query(view, predicate="intersects"))
        )
        selected = [self._cells[int(i)][1] for i in indices]
        features, size = [], 0
        for feature in selected[:MAX_DISPLAY_CELLS]:
            # Bin definitions are shared in metadata, not duplicated thousands of times.
            compact = {
                **feature,
                "properties": {
                    k: v
                    for k, v in feature["properties"].items()
                    if k not in ("density_bin", "actual_cell_count_bounds")
                },
            }
            size += len(json.dumps(compact, allow_nan=False, separators=(",", ":")).encode())
            if size > MAX_DISPLAY_BYTES - 65536:
                break
            features.append(compact)
        return {
            **metadata,
            "display": {
                "returned_count": len(features),
                "matched_count": len(selected),
                "complete": len(features) == len(selected),
                "bounds": bbox,
            },
            "layer": {"type": "FeatureCollection", "features": deepcopy(features)},
        }


@lru_cache(maxsize=2)
def _prepared(directory, payload):
    manifest = json.loads(payload)
    source = manifest["source"]
    area = StudyRegion(**manifest["bounds"])
    boundary = transform(
        Transformer.from_crs(4326, 25832, always_xy=True).transform, box(*area.as_tuple())
    )
    return PopulationSurface(
        boundary, safe_file(directory, source["path"]), source, manifest["epoch"]
    )


def prepare_population_surface(directory):
    """Verify population-specific source integrity on every call, including cache hits.

    This endpoint does not load or attest unrelated OSM/DIPUL/terrain sources.
    """
    directory = Path(directory).resolve()
    manifest = read_json(safe_file(directory, "study.json"))
    if manifest.get("schema_version") != 1 or manifest.get("kind") != "regional-source-study":
        raise ValueError("Unsupported population study manifest.")
    config, source = manifest["config"], deepcopy(manifest["sources"]["ghsl"])
    if config["ghsl_epoch"] not in (2020, 2025):
        raise ValueError("Unsupported population epoch.")
    area = StudyRegion(**config["bounds"])
    source_path = safe_file(directory, source["path"])
    receipts = [r["sha256"] for r in manifest["files"] if r["path"] == source["path"]]
    actual = checksum(source_path)
    if len(receipts) != 1 or actual != receipts[0]:
        raise ValueError("Population source checksum mismatch.")
    if raster_metadata(source_path, "ghsl") != source["raster"]:
        raise ValueError("Population raster metadata mismatch.")
    source["sha256"] = actual
    payload = json.dumps(
        {
            "source": source,
            "bounds": config["bounds"],
            "epoch": config["ghsl_epoch"],
            "version": VERSION,
        },
        sort_keys=True,
        allow_nan=False,
    )
    # Validate bounds even on a cached call.
    area.as_tuple()
    surface = _prepared(str(directory), payload)
    if checksum(source_path) != actual:
        _prepared.cache_clear()
        raise ValueError("Population source changed during preparation.")
    return surface
