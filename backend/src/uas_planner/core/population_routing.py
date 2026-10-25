"""Shared population centreline costs and optional composition with building costs."""

from copy import deepcopy
from functools import lru_cache
from math import isfinite
from time import perf_counter

from pyproj import CRS, Transformer
from shapely.geometry import LineString, Point, shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

from uas_planner.core.risk import nonnegative, signature

VERSION = "population-length-risk-v1"
CONTACT_M = 1e-7


@lru_cache(maxsize=8)
def _coordinates(input_crs):
    crs = CRS.from_user_input(input_crs)
    return Transformer.from_crs(crs, 25832, always_xy=True).transform, crs.is_geographic


class PopulationEvaluator:
    """One immutable indexed study, shared by all route algorithms and retries."""

    def __init__(self, surface):
        self.metadata = surface.metadata
        self.crs = CRS.from_epsg(25832)
        self.boundary = shape(self.metadata["study_boundary_metric"]).buffer(CONTACT_M)
        self.cells = tuple(
            (g.buffer(CONTACT_M, join_style="mitre"), ident, score)
            for g, ident, score in surface.metric_cells
        )
        self.tree = STRtree([c[0] for c in self.cells])

    def evaluate(self, coordinates, *, input_crs="EPSG:4326"):
        if not 1 <= len(coordinates) <= 2:
            raise ValueError("Evaluate one point or segment; sum segments for a route.")
        if any(
            len(p) != 2
            or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) for v in p
            )
            for p in coordinates
        ):
            raise ValueError("Population route coordinates must be finite pairs.")
        forward, geographic = _coordinates(str(input_crs))
        if geographic and any(
            not -180 <= p[0] <= 180 or not -85 <= p[1] <= 85 for p in coordinates
        ):
            raise ValueError("Invalid population geographic coordinates.")
        geometry = (
            Point(coordinates[0])
            if len(set(map(tuple, coordinates))) == 1
            else LineString(coordinates)
        )
        geometry = transform(forward, geometry)
        if geometry.is_empty or not all(isfinite(v) for v in geometry.bounds):
            raise ValueError("Invalid transformed population route geometry.")
        candidates = [self.cells[int(i)] for i in self.tree.query(geometry, predicate="intersects")]
        unknown = sorted(ident for _, ident, score in candidates if score is None)
        numeric = [(g, score) for g, _, score in candidates if score is not None]
        outside = not self.boundary.covers(geometry)
        covered = unary_union([g for g, _ in numeric])
        assessed = not unknown and not outside and covered.covers(geometry)
        remaining, cost = geometry, 0.0
        for score in sorted({score for _, score in numeric}, reverse=True):
            region = unary_union([g for g, s in numeric if s == score])
            cost += remaining.intersection(region).length * score
            remaining = remaining.difference(region)
        if not isfinite(cost):
            raise ValueError("Population route cost overflow.")
        return {
            "assessment": "assessed" if assessed else "unresolved",
            "population_length_cost": cost if assessed else None,
            "population_source_ids": sorted(ident for _, ident, _ in candidates),
            "population_unknown_cell_ids": unknown,
            "population_outside_support": outside,
        }


class PopulationRiskModel:
    """Adapter for graph and OMPL planners; existing building semantics stay separate."""

    def __init__(
        self, building, population, *, objective, population_weight, deadline=float("inf")
    ):
        self.building, self.population = building, population
        if not building.crs.equals(population.crs):
            raise ValueError("Building and population cost CRSs must match.")
        self.crs, self.boundary = building.crs, building.boundary
        self.safety_distance_m = building.safety_distance_m
        self.risk_weight, self.distance_weight = building.risk_weight, building.distance_weight
        self.population_weight = nonnegative(population_weight, "Population weight")
        if self.population_weight == 0 or objective not in ("distance", "risk"):
            raise ValueError("Population model requires an active weight and base objective.")
        self.base_objective, self.deadline = objective, deadline
        self.provenance = {
            **deepcopy(building.provenance),
            "rules_version": VERSION,
            "base_objective": objective,
            "population_weight": self.population_weight,
            "population_model": deepcopy(population.metadata),
            "population_routing_cost": True,
            "population_contact_tolerance_m": CONTACT_M,
            "population_boundary_policy": "maximum adjacent score, counted once; any unknown touch unresolved",
        }
        self.provenance["source"] = {
            **deepcopy(building.provenance.get("source", {})),
            "ghsl_routing_cost": True,
            "population_model_identity": population.metadata["identity"],
        }
        self.provenance.pop("model_signature", None)
        self.provenance["model_signature"] = signature(self.provenance)

    def evaluate(self, coordinates, *, input_crs="EPSG:4326"):
        if perf_counter() >= self.deadline:
            raise TimeoutError("Population routing request deadline reached.")
        building = self.building.evaluate(coordinates, input_crs=input_crs)
        population = self.population.evaluate(coordinates, input_crs=input_crs)
        assessed = building["assessment"] == population["assessment"] == "assessed"
        objective = (
            (
                building["objective_cost"]
                + self.population_weight * population["population_length_cost"]
            )
            if assessed
            else None
        )
        if assessed and not isfinite(objective):
            raise ValueError("Combined population objective overflow.")
        return {
            **building,
            **population,
            "assessment": "assessed" if assessed else "unresolved",
            "risk_length_cost": building["risk_length_cost"] if assessed else None,
            "objective_cost": objective,
        }
