"""Length and pedestrian exposure on one precomputed study window."""

from math import fsum, isfinite

from pyproj import CRS, Transformer
from shapely import STRtree, intersection, union_all
from shapely import length as lengths
from shapely.geometry import LineString, Point, shape
from shapely.ops import transform

from uas_planner.acquisition.pedestrian import read_pedestrian_product
from uas_planner.core.mid_profiles import window_metadata

OBJECTIVE = "pedestrian_exposure"
REFERENCE_DENSITY = 100.0  # people/km², fixed comparison scale across model windows
EXPOSURE_WEIGHT = 1.0  # a metre at reference density adds one metre to the objective
EXPOSURE_FIELD = "pedestrian_exposure_m"
DEFAULT_GRID_M = 500
DEFAULT_SEARCH_SECONDS = 30
CONTACT_M = 1e-6


class PedestrianRouteCost:
    """Cost adapter for the existing graph search, with explicit missing support."""

    crs = CRS.from_epsg(25832)
    distance_weight = 1.0
    component_fields = (EXPOSURE_FIELD,)

    def __init__(self, directory, window, clearance):
        product, identity = read_pedestrian_product(directory)
        self.safety_distance_m = clearance
        self.forward = Transformer.from_crs(4326, self.crs, always_xy=True).transform
        self.polygons = []
        self.densities = []
        self.ids = []
        for cell, people in zip(
            product["cells"], product["windows"][window]["mean_people"], strict=True
        ):
            area = cell["area_m2"]
            if (
                not isfinite(area)
                or area <= 0
                or people is not None
                and (not isfinite(people) or people < 0)
            ):
                raise ValueError("Invalid pedestrian grid dimensions or count.")
            self.polygons.append(transform(self.forward, shape(cell["geometry"])))
            self.densities.append(None if people is None else people * 1_000_000 / area)
            self.ids.append(cell["id"])
        self.tree = STRtree(self.polygons)
        self.provenance = {
            "rules_version": "pedestrian-distance-v1",
            "window": window_metadata(window),
            "layer_identity": f"{identity}:{window}",
            "model_version": product["version"],
            "study_sha256": product["study_sha256"],
            "reference_density_people_per_km2": REFERENCE_DENSITY,
            "lambda": EXPOSURE_WEIGHT,
        }

    def evaluate(self, coordinates):
        points = [self.forward(*point) for point in coordinates]
        geometry = Point(points[0]) if len(set(points)) == 1 else LineString(points)
        length = geometry.length
        candidates = self.tree.query(
            geometry.buffer(CONTACT_M) if not length else geometry, predicate="intersects"
        )
        unknown = []
        exposure = 0.0
        if not length:
            unknown = [self.ids[i] for i in candidates if self.densities[i] is None]
            assessed = len(candidates) > 0 and not unknown
        else:
            pieces = lengths(intersection(geometry, self.tree.geometries[candidates]))
            known = []
            for i, metres in zip(candidates, pieces, strict=True):
                if metres <= 0:
                    continue
                density = self.densities[i]
                if density is None:
                    if metres > CONTACT_M:
                        unknown.append(self.ids[i])
                else:
                    known.append((i, metres, density))
            covered = fsum(metres for _, metres, _ in known)
            if covered > length + CONTACT_M:
                # A line on a shared boundary counts once, at the larger density.
                remaining = geometry
                for i, _, density in sorted(known, key=lambda part: (-part[2], part[0])):
                    exposure += remaining.intersection(self.polygons[i]).length * density
                    remaining = remaining.difference(self.polygons[i])
                covered = length - remaining.length
            else:
                exposure = fsum(metres * density for _, metres, density in known)
            assessed = not unknown and abs(length - covered) <= CONTACT_M
        exposure /= REFERENCE_DENSITY
        return {
            "assessment": "assessed" if assessed else "unresolved",
            "length_m": length,
            EXPOSURE_FIELD: exposure if assessed else None,
            "objective_cost": length + EXPOSURE_WEIGHT * exposure if assessed else None,
            "risk_length_cost": 0.0,
            "has_default": False,
            "background_assumed": False,
            "source_ids": sorted(self.ids[i] for i in candidates),
            "unavailable_cell_ids": sorted(unknown),
        }

    def independently_score(self, coordinates):
        """Recompute the whole path by density-band intersection, independent of edge scores."""
        points = [self.forward(*point) for point in coordinates]
        route_length = exposure = 0.0
        for a, b in zip(points, points[1:]):
            if a == b:
                continue
            line = LineString([a, b])
            remaining = line
            groups = {}
            for i in self.tree.query(line, predicate="intersects"):
                density = self.densities[i]
                if density is None:
                    if line.intersection(self.polygons[i]).length > CONTACT_M:
                        return None
                else:
                    groups.setdefault(density, []).append(self.polygons[i])
            for density in sorted(groups, reverse=True):
                region = union_all(groups[density])
                exposure += remaining.intersection(region).length * density / REFERENCE_DENSITY
                remaining = remaining.difference(region)
            if remaining.length > CONTACT_M:
                return None
            route_length += line.length
        return {
            "length_m": route_length,
            EXPOSURE_FIELD: exposure,
            "objective_cost": route_length + EXPOSURE_WEIGHT * exposure,
        }
