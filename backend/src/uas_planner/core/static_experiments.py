"""Offline experiment records, analytic synthetic checks and bounded comparisons."""

from collections import Counter, defaultdict
from copy import copy, deepcopy
from math import isclose
from statistics import mean
from time import perf_counter

from pyproj import Transformer
from shapely.geometry import LineString, Point, box, mapping
from shapely.ops import transform

from uas_planner.core.costs import classify_tag
from uas_planner.core.regional import validate_scenario
from uas_planner.core.regional_routing import RegionalPlanner
from uas_planner.core.risk import RiskModel, signature

PAIRS = (
    ("rheuma-podbi", "mhh"),
    ("amedes-georg", "mhh"),
    ("limbach-lehrte", "mhh"),
)
ALGORITHMS = ("astar", "dijkstra", "abitstar")


class SyntheticConstraints:
    """Explicit artificial metric geometry; no real-source decisions are overridden."""

    def __init__(self, fixture, scenario, expanded=False):
        self.scenario = validate_scenario(deepcopy(scenario))
        self.forward = Transformer.from_crs(4326, 25832, always_xy=True).transform
        self.reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform
        self.boundary = box(500000, 5800000, 500400, 5800400)
        if expanded:
            self.boundary = self.boundary.buffer(100, join_style=2)
        self.risk_polygon = box(500100, 5800100, 500300, 5800300)
        self.score = classify_tag("building", "hospital")["cost"]
        self.obstacle = (
            box(500190, 5800000, 500210, 5800400) if fixture == "boundary-detour" else None
        )
        endpoints = (
            ((500025, 5800025), (500375, 5800375))
            if fixture == "diagonal"
            else ((500025, 5800225), (500375, 5800225))
        )
        self.manifest = {
            "config": {
                "locations": [
                    {"id": name, "longitude": self.reverse(*p)[0], "latitude": self.reverse(*p)[1]}
                    for name, p in zip(("a", "b"), endpoints, strict=True)
                ]
            }
        }
        self.definition = {
            "fixture": fixture,
            "analysis_crs": "EPSG:25832",
            "boundary": mapping(self.boundary),
            "risk_polygon": mapping(self.risk_polygon),
            "building": "hospital",
            "score": self.score,
            "obstacle": mapping(self.obstacle) if self.obstacle is not None else None,
            "endpoints": endpoints,
            "background_cost": 0,
            "height": "Synthetic buildings explicitly below both cruise altitudes.",
        }
        self.provenance = {
            "synthetic": True,
            "model_signature": signature(self.definition),
            "scenario": self.scenario,
            "definition": self.definition,
        }

    def check(self, coordinates, mode="strict"):
        points = [self.forward(*p) for p in coordinates]
        geometry = Point(points[0]) if len(points) == 1 else LineString(points)
        clearance = self.scenario.get("clearance_m", 0)
        if clearance:
            geometry = geometry.buffer(clearance)
        permitted = self.boundary.covers(geometry) and (
            self.obstacle is None or not geometry.intersects(self.obstacle)
        )
        return {
            "state": "permitted" if permitted else "blocked",
            "blocked": [] if permitted else [{"reason": "Synthetic obstacle or boundary"}],
            "unresolved": [],
            "assumptions": [{"reason": "Synthetic complete support and assessed zero background"}],
        }

    def risk_model(self, **controls):
        controls.pop("mode", None)
        return RiskModel(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": mapping(transform(self.reverse, self.risk_polygon)),
                        "properties": {"building": "hospital"},
                    }
                ],
            },
            mapping(transform(self.reverse, self.boundary)),
            safety_distance_m=self.scenario.get("clearance_m", 0),
            **controls,
        )


def synthetic_planner(fixture, scenario, *, expanded=False):
    if fixture not in ("risk-detour", "diagonal", "boundary-detour"):
        raise ValueError("Unknown synthetic fixture.")
    planner = RegionalPlanner.__new__(RegionalPlanner)
    planner.constraints = SyntheticConstraints(fixture, scenario, expanded)
    planner.forward = planner.constraints.forward
    planner.reverse = planner.constraints.reverse
    return planner


def planner_at_speed(planner, speed):
    """Share immutable geometry for speed-only sweeps, with isolated signed metadata."""
    clone = copy(planner)
    clone.constraints = copy(planner.constraints)
    clone.constraints.scenario = validate_scenario(
        {**planner.constraints.scenario, "speed_m_s": speed}
    )
    clone.constraints.provenance = deepcopy(planner.constraints.provenance)
    clone.constraints.provenance["scenario"] = clone.constraints.scenario
    clone.constraints.provenance.pop("model_signature")
    clone.constraints.provenance["model_signature"] = signature(clone.constraints.provenance)
    return clone


def independent_synthetic_check(planner, result):
    """Recompute intersections directly, without RiskModel.evaluate or core checks."""
    if result["status"] != "success":
        return {"state": "not_applicable", "reason": "No successful route geometry."}
    source = planner.constraints
    path = result["geometry"]["coordinates"]
    line = LineString([planner.forward(*p) for p in path])
    risk = sum(
        LineString([planner.forward(*a), planner.forward(*b)])
        .intersection(source.risk_polygon)
        .length
        * source.score
        for a, b in zip(path, path[1:])
    )
    objective = 0.9 * risk + 0.1 * line.length if result["objective"] == "risk" else line.length
    valid = (
        path[0] == result["start"]
        and path[-1] == result["end"]
        and source.boundary.covers(line)
        and (source.obstacle is None or not line.intersects(source.obstacle))
        and isclose(line.length, result["length_m"], rel_tol=1e-7, abs_tol=1e-5)
        and isclose(objective, result["objective_cost"], rel_tol=1e-7, abs_tol=1e-5)
        and (
            result["objective"] == "distance"
            or isclose(risk, result["risk_length_cost"], rel_tol=1e-7, abs_tol=1e-5)
        )
        and isclose(result["cruise_time_s"], line.length / source.scenario["speed_m_s"])
        and all(
            isclose(actual, expected)
            for actual, expected in zip(
                result["cruise_time_range_s"], [line.length / 35, line.length / 25], strict=True
            )
        )
    )
    return {
        "state": "passed" if valid else "failed",
        "length_m": line.length,
        "building_risk_cost": risk,
        "weighted_objective": 0.9 * risk + 0.1 * line.length,
        "method": "Direct metric segment/polygon intersections and endpoint/boundary/obstacle checks",
    }


def run_matrix(planner, pair, *, label, cache_state, source_ms, cell_m=250, budget_s=0.25):
    records = []
    for objective in ("risk", "distance"):
        for algorithm in ALGORITHMS:
            for repeat in range(3 if algorithm == "abitstar" else 1):
                started = perf_counter()
                result = planner.plan(
                    *pair,
                    algorithm=algorithm,
                    objective=objective,
                    cell_m=cell_m,
                    time_budget_s=budget_s,
                    background_cost=0 if planner.constraints.provenance.get("synthetic") else None,
                )
                result = deepcopy(result)
                record = {
                    "label": label,
                    "pair": list(pair),
                    "repeat": repeat + 1,
                    "cache_state": cache_state,
                    "source_preparation_ms": source_ms,
                    "solve_wall_ms": (perf_counter() - started) * 1000,
                    "cold_equivalent_total_ms": source_ms + result["runtime_ms"],
                    "result": result,
                }
                if planner.constraints.provenance.get("synthetic"):
                    record["experiment_validation"] = independent_synthetic_check(planner, result)
                    if record["experiment_validation"]["state"] == "failed":
                        raise AssertionError("Independent synthetic route validation failed.")
                else:
                    record["experiment_validation"] = {
                        "state": "passed"
                        if result.get("independent_validation")
                        else "not_applicable",
                        "reason": "Core independent route check; unsuccessful results retain diagnostics.",
                    }
                records.append(record)
    return records


def summarize(records):
    groups = defaultdict(list)
    for record in records:
        result = record["result"]
        groups[
            (record["label"], tuple(record["pair"]), record["cache_state"], result["objective"])
        ].append(record)
    summaries = []
    for (label, pair, cache_state, objective), group in groups.items():
        graph = {
            r["result"]["algorithm"]: r["result"]
            for r in group
            if r["result"]["algorithm"] != "abitstar"
        }
        agreement = "not_applicable"
        if all(graph.get(a, {}).get("status") == "success" for a in ("astar", "dijkstra")):
            agreement = (
                "passed"
                if isclose(
                    graph["astar"]["objective_cost"],
                    graph["dijkstra"]["objective_cost"],
                    rel_tol=1e-7,
                    abs_tol=1e-5,
                )
                else "failed"
            )
        native = [r for r in group if r["result"]["algorithm"] == "abitstar"]
        successful = [r for r in native if r["result"]["status"] == "success"]
        metrics = {}
        for key in ("length_m", "objective_cost", "planner_ms"):
            values = [r["result"][key] for r in successful]
            metrics[key] = (
                {"min": min(values), "max": max(values), "mean": mean(values)} if values else None
            )
        summaries.append(
            {
                "label": label,
                "pair": list(pair),
                "cache_state": cache_state,
                "objective": objective,
                "outcomes": dict(Counter(r["result"]["status"] for r in group)),
                "graph_objective_agreement": agreement,
                "timings_by_algorithm": {
                    algorithm: {
                        field: {
                            "min": min(values),
                            "max": max(values),
                            "mean": mean(values),
                        }
                        for field in ("preparation_ms", "planner_ms", "runtime_ms")
                        if (
                            values := [
                                r["result"][field]
                                for r in group
                                if r["result"]["algorithm"] == algorithm
                            ]
                        )
                    }
                    for algorithm in ALGORITHMS
                },
                "abitstar": {
                    "attempts": len(native),
                    "budgets_s": sorted({r["result"]["controls"]["time_budget_s"] for r in native}),
                    "search_started": sum(r["result"]["planner_ms"] > 0 for r in native),
                    "success_rate": len(successful) / len(native) if native else None,
                    "successful_run_variation": metrics,
                    "all_attempt_wall_ms": [r["solve_wall_ms"] for r in native],
                    "seed_supported": False,
                },
            }
        )
    if any(s["graph_objective_agreement"] == "failed" for s in summaries):
        raise AssertionError("Weighted A*/Dijkstra disagree on the same graph.")
    return summaries
