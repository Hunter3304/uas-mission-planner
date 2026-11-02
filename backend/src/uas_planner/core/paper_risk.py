"""Ramke's OSM/population fusion on a shared 150 m metric lattice."""

from collections import OrderedDict
from copy import deepcopy
from math import isfinite
from threading import Lock
from time import perf_counter

from pyproj import CRS, Transformer
from shapely.geometry import LineString, Point, box, shape
from shapely.strtree import STRtree

from uas_planner.core.costs import RULES, classify_layer
from uas_planner.core.population_costs import check_deadline
from uas_planner.core.population_routing import CONTACT_M, PopulationEvaluator
from uas_planner.core.risk import nonnegative, signature

VERSION = "ramke-fused-risk-150m-v1"
COMPONENTS = ("building", "landuse", "highway", "population")
FIELDS = tuple(f"{name}_length_cost" for name in COMPONENTS)
WEIGHTS = dict(building=0.15, landuse=0.15, highway=0.15, population=0.45, distance=0.1)
_surfaces = OrderedDict()
_surface_lock = Lock()


class FusedSurface:
    """Static, indexed cells with all component values from the same lattice."""

    def __init__(self, population, records, *, background=0, deadline=float("inf")):
        self.metadata = population.metadata
        self.background = nonnegative(background, "Background score")
        raw_cells = population.metric_cells
        if self.metadata["cell_size_m"] != 150:
            raise ValueError("Fused risk requires a shared 150 m population lattice.")
        check_deadline(deadline)
        cell_tree = STRtree([g for g, _, _ in raw_cells])
        categories = {name: [] for name in (*COMPONENTS[:3], "natural")}
        unknown, diagnostics = [], []
        for geometry, tags, ident in records:
            check_deadline(deadline)
            analyses = {name: classify_layer(tags, name) for name in categories}
            if not any(a is not None for a in analyses.values()):
                continue
            if (
                geometry is None
                or geometry.is_empty
                or not all(isfinite(v) for v in geometry.bounds)
            ):
                raise ValueError(f"Unlocalizable OSM cost geometry: {ident}.")
            if not geometry.is_valid or geometry.geom_type not in (
                "Point",
                "LineString",
                "LinearRing",
                "MultiLineString",
                "Polygon",
                "MultiPolygon",
            ):
                unknown.append(box(*geometry.bounds).buffer(CONTACT_M))
                diagnostics.append({"source": ident, "status": "unresolved_geometry"})
                continue
            owner = None
            if geometry.geom_type == "Point":
                touched = cell_tree.query(geometry, predicate="intersects")
                owner = min((raw_cells[int(i)][1] for i in touched), default=None)
            for name, analysis in analyses.items():
                if analysis is None:
                    continue
                if analysis["cost"] is None:
                    diagnostics.append({"source": ident, "category": name, "status": "unscored"})
                    continue
                categories[name].append(
                    (geometry, analysis["cost"], analysis["has_default"], ident, owner)
                )
        trees = {name: STRtree([r[0] for r in rows]) for name, rows in categories.items()}
        unknown_tree = STRtree(unknown)
        self.cells = []
        for polygon, ident, population_score in raw_cells:
            check_deadline(deadline)
            scores, sources, defaults, backgrounds = {}, set(), False, []
            for name, rows in categories.items():
                values = []
                for index in trees[name].query(polygon, predicate="intersects"):
                    g, score, default, source, owner = rows[int(index)]
                    overlap = g.intersection(polygon)
                    contributes = (
                        owner == ident
                        if g.geom_type == "Point"
                        else overlap.area > 0
                        if g.geom_type in ("Polygon", "MultiPolygon")
                        else overlap.length > 0
                    )
                    if contributes:
                        values.append(score)
                        sources.add(source)
                        defaults |= default
                scores[name] = max(values, default=None)
            if scores["landuse"] is None:
                scores["landuse"] = scores["natural"]
            for name in COMPONENTS[:3]:
                if scores[name] is None:
                    scores[name] = self.background
                    backgrounds.append(name)
            values = tuple(scores[name] for name in COMPONENTS[:3]) + (population_score,)
            unresolved = (
                population_score is None
                or len(unknown_tree.query(polygon, predicate="intersects")) > 0
            )
            fused = None if unresolved else sum(values[:3]) / 6 + values[3] / 2
            if fused is not None and not isfinite(fused):
                raise ValueError("Fused cell score overflow.")
            self.cells.append(
                (
                    polygon.buffer(CONTACT_M, join_style="mitre"),
                    ident,
                    values,
                    fused,
                    defaults,
                    tuple(backgrounds),
                    tuple(sorted(sources)),
                )
            )
        self.tree = STRtree([c[0] for c in self.cells])
        self.diagnostics = diagnostics
        check_deadline(deadline)


class PaperRiskModel:
    """Shared graph/OMPL adapter; fixed weights and independent component totals."""

    risk_weight = 0.9
    distance_weight = 0.1
    population_weight = 0.45
    component_fields = FIELDS + ("fused_risk_length_cost",)

    def __init__(self, surface, *, source, safety_distance_m=0, deadline=float("inf")):
        self.surface = surface
        self.population = PopulationEvaluator(surface_population(surface))
        self.crs = CRS.from_epsg(25832)
        self.boundary = shape(surface.metadata["study_boundary_metric"])
        self.safety_distance_m = nonnegative(safety_distance_m, "Safety distance")
        self.deadline = deadline
        self.forward = Transformer.from_crs(4326, 25832, always_xy=True).transform
        self.provenance = {
            "rules_version": VERSION,
            "classification_sha256": signature(RULES),
            "population_model": deepcopy(surface.metadata),
            "analysis_crs": "EPSG:25832",
            "cost_grid_m": 150,
            "effective_weights": dict(WEIGHTS),
            "background_cost": surface.background,
            "background_status": "explicit_assumption",
            "osm_cell_policy": "maximum intersecting category score; natural fallback for unscored landuse",
            "boundary_policy": "highest fused adjacent cell; stable ID ties; any unknown contact unresolved",
            "contact_tolerance_m": CONTACT_M,
            "diagnostics": surface.diagnostics,
            "source": deepcopy(source),
        }
        self.provenance["model_signature"] = signature(self.provenance)

    def evaluate(self, coordinates, *, input_crs="EPSG:4326"):
        if perf_counter() >= self.deadline:
            raise TimeoutError("Fused route assessment deadline reached.")
        if not 1 <= len(coordinates) <= 2 or any(
            len(p) != 2
            or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) for v in p
            )
            for p in coordinates
        ):
            raise ValueError("Fused risk requires one point or segment with finite pairs.")
        crs = CRS.from_user_input(input_crs)
        if crs.is_geographic and any(
            not -180 <= p[0] <= 180 or not -85 <= p[1] <= 85 for p in coordinates
        ):
            raise ValueError("Invalid fused risk geographic coordinates.")
        points = (
            [self.forward(*p) for p in coordinates]
            if crs.to_epsg() == 4326
            else [
                Transformer.from_crs(crs, 25832, always_xy=True).transform(*p) for p in coordinates
            ]
        )
        geometry = Point(points[0]) if len(set(points)) == 1 else LineString(points)
        if not all(isfinite(v) for v in geometry.bounds):
            raise ValueError("Invalid fused risk projection.")
        candidates = [
            self.surface.cells[int(i)]
            for i in self.surface.tree.query(geometry, predicate="intersects")
        ]
        unresolved = not self.boundary.buffer(CONTACT_M).covers(geometry) or any(
            c[3] is None for c in candidates
        )
        numeric = sorted((c for c in candidates if c[3] is not None), key=lambda c: (-c[3], c[1]))
        remaining, totals = geometry, [0.0] * 4
        for cell in numeric:
            if perf_counter() >= self.deadline:
                raise TimeoutError("Fused route assessment deadline reached.")
            overlap = remaining.intersection(cell[0])
            for i, score in enumerate(cell[2]):
                totals[i] += overlap.length * score
            remaining = remaining.difference(cell[0])
        unresolved |= not remaining.is_empty
        fused = sum(totals[:3]) / 6 + totals[3] / 2
        objective = 0.9 * fused + 0.1 * geometry.length
        if not all(isfinite(v) for v in (*totals, fused, objective)):
            raise ValueError("Fused route cost overflow.")
        return {
            "length_m": geometry.length,
            "assessment": "unresolved" if unresolved else "assessed",
            "risk_length_cost": None if unresolved else fused,
            "fused_risk_length_cost": None if unresolved else fused,
            "objective_cost": None if unresolved else objective,
            **{
                field: None if unresolved else value
                for field, value in zip(FIELDS, totals, strict=True)
            },
            "has_default": any(c[4] for c in candidates),
            "background_assumed": any(c[5] for c in candidates),
            "source_ids": sorted({s for c in candidates for s in c[6]}),
            "population_source_ids": sorted(c[1] for c in candidates),
        }


def surface_population(surface):
    """Population endpoint diagnostics keep the same 150 m source reference."""
    from types import SimpleNamespace

    return SimpleNamespace(
        metadata=surface.metadata,
        metric_cells=tuple((c[0], c[1], c[2][3]) for c in surface.cells),
    )


def prepare_paper_model(constraints, population, *, mode, background=0, deadline=float("inf")):
    """Bounded static cache; the caller verifies retained sources on every request."""
    check_deadline(deadline)
    metadata = population.metadata
    key = signature(
        {
            "version": VERSION,
            "rules": signature(RULES),
            "population": metadata["identity"],
            "osm": constraints.provenance["osm_sha256"],
            "background": background,
            "derived": mode != "strict"
            and constraints.scenario.get("research_geometry") == "derived",
            "geometry_policy": constraints.scenario.get("research_geometry_buffer_m", 20),
        }
    )
    with _surface_lock:
        surface = _surfaces.get(key)
        if surface is not None:
            _surfaces.move_to_end(key)
    if surface is None:
        surface = FusedSurface(
            population, constraints.paper_features(mode), background=background, deadline=deadline
        )
        check_deadline(deadline)
        with _surface_lock:
            _surfaces[key] = surface
            while len(_surfaces) > 2:
                _surfaces.popitem(last=False)
    check_deadline(deadline)
    return PaperRiskModel(
        surface,
        source=constraints.provenance,
        safety_distance_m=constraints.scenario.get("clearance_m", 0),
        deadline=deadline,
    )
