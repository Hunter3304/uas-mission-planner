"""Metric building-risk integration, independent of HTTP and route search."""

import hashlib
import json
from functools import lru_cache
from math import isfinite
from pathlib import Path

from pyproj import CRS, Transformer
from shapely.geometry import LineString, Point, shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

from uas_planner.core.costs import RULES, analyze_feature
from uas_planner.core.experiment import safe_file
from uas_planner.storage.dataset import load_dataset

RISK_VERSION = "building-length-risk-v1"


def nonnegative(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} must be a finite nonnegative number.")
    if value < 0:
        raise ValueError(f"{name} must be a finite nonnegative number.")
    return float(value)


def signature(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()
    ).hexdigest()


def metric_crs(value):
    crs = CRS.from_user_input(value)
    if not crs.is_projected or any(axis.unit_name != "metre" for axis in crs.axis_info[:2]):
        raise ValueError("Risk analysis requires a projected CRS with metre axes.")
    return crs


@lru_cache(maxsize=16)
def _coordinate_transform(source, target):
    return Transformer.from_crs(source, target, always_xy=True).transform


class RiskModel:
    """Prepared indexed polygons; max score on overlap, explicit missing support.

    Background applies only outside numeric building polygons. Scores are ordinal
    research preferences; a configured background is an assumption, not OSM data.
    """

    def __init__(
        self,
        collection,
        boundary,
        *,
        input_crs="EPSG:4326",
        analysis_crs="EPSG:25832",
        background_cost=None,
        risk_weight=0.9,
        distance_weight=0.1,
        source=None,
        safety_distance_m=0,
    ):
        self.crs = metric_crs(analysis_crs)
        forward = _coordinate_transform(input_crs, self.crs.to_string())
        self.boundary = transform(forward, shape(boundary))
        if (
            self.boundary.is_empty
            or not self.boundary.is_valid
            or self.boundary.geom_type not in ("Polygon", "MultiPolygon")
        ):
            raise ValueError("Risk boundary must be a valid nonempty polygon.")
        self.background = (
            None if background_cost is None else nonnegative(background_cost, "Background cost")
        )
        self.risk_weight = nonnegative(risk_weight, "Risk weight")
        self.distance_weight = nonnegative(distance_weight, "Distance weight")
        if self.risk_weight + self.distance_weight == 0:
            raise ValueError("At least one objective weight must be positive.")
        self.safety_distance_m = nonnegative(safety_distance_m, "Safety distance")
        self.records, self.diagnostics = [], []
        self.unsupported = False
        for feature in collection["features"]:
            properties = feature["properties"]
            analysis = analyze_feature(properties, "building")
            if analysis is None:
                continue
            ident = f"{properties.get('element_type', 'feature')}/{properties.get('osm_id', feature.get('id', 'unknown'))}"
            geometry = shape(feature["geometry"]) if feature.get("geometry") else None
            if geometry is None or geometry.is_empty or not geometry.is_valid:
                raise ValueError(f"Invalid building geometry: {ident}; source was not repaired.")
            geometry = transform(forward, geometry)
            if not geometry.is_valid:
                raise ValueError(f"Invalid projected building geometry: {ident}.")
            if not geometry.intersects(self.boundary):
                continue
            if geometry.geom_type not in ("Polygon", "MultiPolygon"):
                self.unsupported = True
                self.diagnostics.append({"id": ident, "status": "unsupported_geometry"})
                continue
            geometry = geometry.intersection(self.boundary)
            if geometry.is_empty:
                continue
            score = analysis["cost"]
            self.records.append(
                {
                    "geometry": geometry,
                    "id": ident,
                    "cost": None if score is None else nonnegative(score, "Building cost"),
                    "default": analysis["has_default"],
                    "obstruction": analysis["obstruction"],
                }
            )
        self.tree = STRtree([r["geometry"] for r in self.records])
        self.provenance = {
            "rules_version": RISK_VERSION,
            "classification_version": RULES["version"],
            "classification_sha256": signature(RULES),
            "analysis_crs": self.crs.to_string(),
            "overlap_policy": "maximum_building_score",
            "background_cost": self.background,
            "background_status": "unassessed" if self.background is None else "explicit_assumption",
            "risk_weight": self.risk_weight,
            "distance_weight": self.distance_weight,
            "safety_distance_m": self.safety_distance_m,
            "source": source or {"type": "provided_collection"},
            "collection_sha256": signature(collection),
            "boundary_sha256": signature(boundary),
            "input_crs": CRS.from_user_input(input_crs).to_string(),
            "diagnostics": self.diagnostics,
        }
        self.provenance["model_signature"] = signature(self.provenance)

    def evaluate(self, coordinates, *, input_crs="EPSG:4326"):
        """Evaluate a centreline, including point support for zero-length routes."""
        forward = _coordinate_transform(input_crs, self.crs.to_string())
        points = []
        for coordinate in coordinates:
            if len(coordinate) != 2 or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v)
                for v in coordinate
            ):
                raise ValueError("Risk segment requires finite coordinate pairs.")
            point = forward(*coordinate)
            if not all(isfinite(v) for v in point):
                raise ValueError("Risk segment projection produced nonfinite coordinates.")
            points.append(point)
        if not 1 <= len(points) <= 2:
            raise ValueError("Evaluate one point or one segment; sum segments for a route.")
        line = Point(points[0]) if len(set(points)) == 1 else LineString(points)
        candidates = [self.records[int(i)] for i in self.tree.query(line, predicate="intersects")]
        # Numeric support cannot resolve overlapping regions with missing scores.
        missing = [r for r in candidates if r["cost"] is None]
        numeric = [r for r in candidates if r["cost"] is not None]
        covered = unary_union([r["geometry"] for r in numeric])
        outside = line.difference(covered)
        unresolved = (
            self.unsupported
            or not self.boundary.covers(line)
            or bool(missing)
            or (self.background is None and not outside.is_empty)
        )
        remaining, risk = line, 0.0
        # Partition the intersected line, rather than summing overlapping polygons.
        for score in sorted({r["cost"] for r in numeric}, reverse=True):
            region = unary_union([r["geometry"] for r in numeric if r["cost"] == score])
            risk += remaining.intersection(region).length * score
            remaining = remaining.difference(region)
        if self.background is not None:
            risk += remaining.length * self.background
        length = line.length
        objective = self.risk_weight * risk + self.distance_weight * length
        if not unresolved and not all(isfinite(v) for v in (length, risk, objective)):
            raise ValueError("Risk cost overflow; reduce scores or weights.")
        return {
            "length_m": length,
            "risk_length_cost": None if unresolved else risk,
            "objective_cost": None if unresolved else objective,
            "assessment": "unresolved" if unresolved else "assessed",
            "has_default": any(r["default"] for r in candidates),
            "background_assumed": self.background is not None and not outside.is_empty,
            "source_ids": sorted({r["id"] for r in candidates}),
        }


@lru_cache(maxsize=8)
def _prepared_model(payload):
    return RiskModel(**json.loads(payload))


def prepare_risk_model(directory, manifest, grid, **options):
    """Verify saved OSM on every call, then cache by payload/config/rule identity."""
    directory = Path(directory).resolve()
    osm = directory / "osm" if (directory / "osm").is_dir() else directory
    for name in ("metadata.json", "features.gpkg"):
        safe_file(directory, str((osm / name).relative_to(directory)))
    frame, metadata = load_dataset(osm, compact=True)
    if metadata["query_bounds"] != manifest["config"]["bounds"]:
        raise ValueError("Risk OSM and experiment bounds must match.")
    collection = json.loads(frame.to_json(drop_id=True, na="drop"))
    for feature, tags in zip(collection["features"], frame.attrs["source_tags"], strict=True):
        feature["properties"].update(tags)
    payload = {
        "collection": collection,
        "boundary": grid["validation"]["boundary"],
        "analysis_crs": grid["analysis_crs"],
        "source": {
            "osm_sha256": metadata["sha256"],
            "name": metadata["source"],
            "attribution": metadata["attribution"],
            "license_url": metadata["license_url"],
            "saved_at_utc": metadata["saved_at_utc"],
            "synthetic": metadata.get("synthetic", False),
            "experiment_signature": signature(manifest),
            "classification_sha256": signature(RULES),
            "risk_rules_version": RISK_VERSION,
            "grid_signature": signature(grid),
        },
        **options,
    }
    return _prepared_model(json.dumps(payload, sort_keys=True, allow_nan=False))
