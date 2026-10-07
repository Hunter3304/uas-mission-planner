"""Bounded Hannover routing using existing graph/native planners and regional checks."""

from functools import lru_cache
from math import ceil, hypot, isclose
from time import perf_counter

from pyproj import Transformer
from shapely.geometry import box, mapping
from shapely.ops import transform

from uas_planner.core.grid import MAX_GRID_CELLS, validate_cell_size
from uas_planner.core.regional import RegionalConstraints
from uas_planner.core.risk import RiskModel, nonnegative, signature
from uas_planner.core.routing import connect_endpoints, plan_route


class RegionalPlanner:
    """Request-scoped source verification; bounded motion cache never crosses snapshots."""

    def __init__(self, directory, scenario, *, terrain_directory=None):
        self.constraints = RegionalConstraints(
            directory, scenario, terrain_directory=terrain_directory
        )
        self.forward = Transformer.from_crs(4326, 25832, always_xy=True).transform
        self.reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform

    def check(self, coordinates, mode):
        # Bound each complete terrain window, preserving the whole polyline and buffers.
        # Subdivision changes query resource usage, never relaxes unknown support.
        points = [self.forward(*p) for p in coordinates]
        pieces = []
        for a, b in zip(points, points[1:]):
            count = max(1, ceil(hypot(b[0] - a[0], b[1] - a[1]) / 500))
            if count + len(pieces) > 10000:
                return {
                    "state": "unresolved",
                    "blocked": [],
                    "unresolved": [
                        {"source": "resources", "reason": "Motion subdivision limit reached."}
                    ],
                    "assumptions": [],
                }
            for i in range(count):
                pieces.append(
                    [
                        self.reverse(*(a[j] + (b[j] - a[j]) * t / count for j in (0, 1)))
                        for t in (i, i + 1)
                    ]
                )
        reports = (
            [self.constraints.check(piece, mode=mode) for piece in pieces]
            if pieces
            else [self.constraints.check(coordinates, mode=mode)]
        )
        result = {
            key: [item for report in reports for item in report[key]]
            for key in ("blocked", "unresolved", "assumptions")
        }
        result["state"] = (
            "blocked"
            if result["blocked"]
            else "unresolved"
            if result["unresolved"]
            else "permitted"
        )
        return result

    def grid(self, endpoints, cell_m, mode, check):
        deadline = perf_counter() + 30
        boundary = self.constraints.boundary
        minx, miny, maxx, maxy = boundary.bounds
        nx, ny = ceil((maxx - minx) / cell_m), ceil((maxy - miny) / cell_m)
        if nx * ny > MAX_GRID_CELLS:
            return None, nx * ny
        cells, positions = [], {}
        for row in range(ny):
            for col in range(nx):
                if perf_counter() >= deadline:
                    return None, "preparation exceeded 30 seconds"
                polygon = box(
                    minx + col * cell_m,
                    miny + row * cell_m,
                    min(maxx, minx + (col + 1) * cell_m),
                    min(maxy, miny + (row + 1) * cell_m),
                ).intersection(boundary)
                if polygon.is_empty or polygon.area <= 0:
                    continue
                point = polygon.representative_point()
                center = list(self.reverse(point.x, point.y))
                ident = f"{row}:{col}"
                positions[row, col] = ident
                cells.append(
                    {
                        "id": ident,
                        "row": row,
                        "col": col,
                        "center": center,
                        "center_metric": [point.x, point.y],
                        "geometry": mapping(transform(self.reverse, polygon)),
                        "state": check([center]),
                        "reasons": [],
                    }
                )
        edges = []
        by_id = {c["id"]: c for c in cells}
        for cell in cells:
            if perf_counter() >= deadline:
                return None, "preparation exceeded 30 seconds"
            for dr, dc in ((0, 1), (1, -1), (1, 0), (1, 1)):
                other_id = positions.get((cell["row"] + dr, cell["col"] + dc))
                if other_id is None:
                    continue
                other = by_id[other_id]
                state = (
                    check([cell["center"], other["center"]])
                    if cell["state"] == other["state"] == "permitted"
                    else "unresolved"
                    if "unresolved" in (cell["state"], other["state"])
                    else "blocked"
                )
                edges.append({"from": cell["id"], "to": other_id, "state": state, "reasons": []})
        grid = self.base_grid(check)
        grid.update(
            cell_size_m=cell_m,
            cells=cells,
            edges=edges,
            cell_count=len(cells),
            edge_count=len(edges),
        )
        return connect_endpoints(
            grid, endpoints, safety_distance_m=self.constraints.scenario.get("clearance_m", 0)
        ), nx * ny

    def base_grid(self, check):
        return {
            "analysis_crs": "EPSG:25832",
            "policy": "block_unresolved",
            "assumptions": self.constraints.scenario,
            "validation": {
                "boundary": mapping(transform(self.reverse, self.constraints.boundary)),
                "blocked": [],
                "unresolved": False,
            },
            "_constraint_check": check,
            "cell_size_m": None,
            "cells": [],
            "edges": [],
            "connectors": [],
        }

    def plan(
        self,
        start_id,
        end_id,
        *,
        cell_m=250,
        algorithm="astar",
        objective="risk",
        planning_mode="strict",
        background_cost=None,
        risk_weight=0.9,
        distance_weight=0.1,
        time_budget_s=3,
    ):
        started = perf_counter()
        cell_m = validate_cell_size(cell_m)
        if (
            algorithm not in ("astar", "dijkstra", "abitstar")
            or objective not in ("risk", "distance")
            or planning_mode not in ("strict", "research")
        ):
            raise ValueError("Unknown regional planner controls.")
        for value, label in (
            (risk_weight, "Risk weight"),
            (distance_weight, "Distance weight"),
            (time_budget_s, "Time budget"),
        ):
            nonnegative(value, label)
        if time_budget_s > 60 or objective == "risk" and risk_weight + distance_weight == 0:
            raise ValueError("Invalid budget or zero objective weights.")
        if background_cost is not None:
            nonnegative(background_cost, "Background cost")
        sites = {s["id"]: s for s in self.constraints.manifest["config"]["locations"]}
        if start_id not in sites or end_id not in sites:
            raise ValueError("Select an endpoint from the verified location catalog.")
        endpoints = {
            name: [sites[ident]["longitude"], sites[ident]["latitude"]]
            for name, ident in (("start", start_id), ("end", end_id))
        }

        @lru_cache(maxsize=50000)
        def cached(points):
            return self.check(points, planning_mode)["state"]

        def check(points):
            return cached(tuple(tuple(p) for p in points))

        reports = {n: self.check([p], planning_mode) for n, p in endpoints.items()}
        result = {
            "algorithm": algorithm,
            "objective": objective,
            "rules_version": "regional-routing-v1",
            "start": endpoints["start"],
            "end": endpoints["end"],
            "geometry": None,
            "length_m": None,
            "risk_length_cost": None,
            "objective_cost": None,
            "status": "unresolved_input",
            "planning_mode": planning_mode,
            "endpoint_diagnostics": reports,
        }
        model = None
        if any(r["state"] == "blocked" for r in reports.values()):
            result.update(
                status="invalid_endpoint",
                message="An exact catalog endpoint intersects a modeled obstacle or boundary.",
            )
        elif any(r["state"] == "unresolved" for r in reports.values()):
            result["message"] = (
                "Regional endpoint or source support remains unresolved; search was not started."
            )
        else:
            try:
                model = (
                    self.constraints.risk_model(
                        background_cost=background_cost,
                        mode=planning_mode,
                        risk_weight=risk_weight,
                        distance_weight=distance_weight,
                    )
                    if objective == "risk"
                    else None
                )
            except ValueError as error:
                result["message"] = str(error)
            else:
                if model and any(
                    model.evaluate([p])["assessment"] != "assessed" for p in endpoints.values()
                ):
                    result["message"] = "Endpoint building-risk support is unassessed."
                else:
                    grid = self.base_grid(check)
                    if algorithm != "abitstar":
                        grid, count = self.grid(endpoints, cell_m, planning_mode, check)
                        if grid is None:
                            result.update(
                                status="resource_limit",
                                message=f"Full-region grid preparation refused ({count}); limit is {MAX_GRID_CELLS} candidate cells and 30 seconds. Increase cell_m explicitly.",
                            )
                    if grid is not None:
                        preparation_ms = (perf_counter() - started) * 1000
                        search_started = perf_counter()
                        if algorithm == "abitstar":
                            from uas_planner.core.abitstar import plan_abitstar

                            native_model = model or RiskModel(
                                {"type": "FeatureCollection", "features": []},
                                grid["validation"]["boundary"],
                                background_cost=0,
                                risk_weight=0,
                                distance_weight=1,
                                safety_distance_m=self.constraints.scenario.get("clearance_m", 0),
                            )
                            result.update(
                                plan_abitstar(
                                    grid, native_model, endpoints, time_budget_s=time_budget_s
                                )
                            )
                            result["randomness"] = {
                                "seed_supported": False,
                                "budget_s": time_budget_s,
                                "variability": "Independent finite-budget stochastic runs; global optimality not established.",
                            }
                            if objective == "distance":
                                result.update(objective="distance", risk_length_cost=None)
                                result.pop("risk_model", None)
                        else:
                            result.update(
                                plan_route(
                                    grid,
                                    algorithm=algorithm,
                                    risk_model=model,
                                    safety_distance_m=self.constraints.scenario.get(
                                        "clearance_m", 0
                                    ),
                                )
                            )
                        result.update(
                            preparation_ms=preparation_ms,
                            planner_ms=(perf_counter() - search_started) * 1000,
                        )
        if result["status"] == "success":
            path = result["geometry"]["coordinates"]
            valid = (
                path[0] == endpoints["start"]
                and path[-1] == endpoints["end"]
                and self.check(path, planning_mode)["state"] == "permitted"
            )
            length = sum(
                hypot(*(b[i] - a[i] for i in (0, 1)))
                for a, b in zip(
                    [self.forward(*p) for p in path], [self.forward(*p) for p in path][1:]
                )
            )
            valid &= isclose(length, result["length_m"], rel_tol=1e-7, abs_tol=1e-6)
            if model:
                assessments = [model.evaluate([a, b]) for a, b in zip(path, path[1:])]
                valid &= all(a["assessment"] == "assessed" for a in assessments)
                for field in ("risk_length_cost", "objective_cost"):
                    valid &= isclose(
                        sum(a[field] for a in assessments),
                        result[field],
                        rel_tol=1e-7,
                        abs_tol=1e-6,
                    )
            else:
                valid &= isclose(length, result["objective_cost"], rel_tol=1e-7, abs_tol=1e-6)
            result["independent_validation"] = bool(valid)
            if not valid:
                result.update(
                    status="computational_failure",
                    geometry=None,
                    length_m=None,
                    risk_length_cost=None,
                    objective_cost=None,
                    message="Independent route validation failed.",
                )
        result.setdefault("planner_ms", 0.0)
        result.setdefault("preparation_ms", (perf_counter() - started) * 1000)
        scenario = self.constraints.scenario
        result.update(
            controls={
                "cell_m": cell_m,
                "algorithm": algorithm,
                "objective": objective,
                "planning_mode": planning_mode,
                "background_cost": background_cost,
                "risk_weight": risk_weight,
                "distance_weight": distance_weight,
                "time_budget_s": time_budget_s,
            },
            provenance=self.constraints.provenance,
            mission={**scenario, "start_id": start_id, "end_id": end_id},
            exact=result["status"] == "success",
            runtime_ms=(perf_counter() - started) * 1000,
        )
        result.setdefault("solution_kind", "exact" if result["exact"] else "none")
        result.setdefault(
            "optimality",
            "Minimum objective on the assessed constructed graph only."
            if algorithm != "abitstar"
            else "Finite-budget continuous search; global optimality not established.",
        )
        result["research_assumptions"] = [
            item for report in reports.values() for item in report["assumptions"]
        ]
        if result["status"] == "success":
            result["research_assumptions"] = self.check(
                result["geometry"]["coordinates"], planning_mode
            )["assumptions"]
        result["prepared_identity"] = signature(
            {
                "provenance": self.constraints.provenance,
                "controls": result["controls"],
                "endpoints": endpoints,
            }
        )
        length = result["length_m"]
        result["cruise_time_s"] = length / scenario["speed_m_s"] if length is not None else None
        result["cruise_time_range_s"] = [length / 35, length / 25] if length is not None else None
        result["time_estimate_scope"] = (
            "Constant cruise only; excludes takeoff, landing, wind and dynamics."
        )
        result["constraint_validation"] = (
            "research_assumptions" if planning_mode == "research" else "strict_model"
        )
        result["runtime_ms"] = (perf_counter() - started) * 1000
        return result


def plan_regional_route(
    directory, scenario, start_id, end_id, *, terrain_directory=None, **controls
):
    started = perf_counter()
    planner = RegionalPlanner(directory, scenario, terrain_directory=terrain_directory)
    source_ms = (perf_counter() - started) * 1000
    result = planner.plan(start_id, end_id, **controls)
    result["source_preparation_ms"] = source_ms
    result["preparation_ms"] += source_ms
    result["runtime_ms"] += source_ms
    return result
