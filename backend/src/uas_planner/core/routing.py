"""Deterministic distance-only search on a prepared, constraint-checked graph."""

from heapq import heappop, heappush
from math import hypot, isfinite
from time import perf_counter

from pyproj import Transformer
from shapely.geometry import LineString, Point, shape
from shapely.ops import transform

RULES_VERSION = "distance-grid-v1"
MAX_EXPANSIONS = 10002


def constraint_checker(grid):
    """Recheck full geometry in metres; boundary contact with obstacles is blocked."""
    forward = Transformer.from_crs(4326, grid["analysis_crs"], always_xy=True).transform
    model = grid["validation"]
    boundary = transform(forward, shape(model["boundary"]))
    obstacles = [transform(forward, shape(g)) for g in model["blocked"]]
    unknown = [transform(forward, shape(g)) for g in model.get("unresolved_regions", [])]

    def check(coordinates):
        points = [forward(*p) for p in coordinates]
        geometry = (
            Point(points[0]) if len(points) == 1 or points[0] == points[-1] else LineString(points)
        )
        if not boundary.covers(geometry) or any(g.intersects(geometry) for g in obstacles):
            return "blocked"
        return (
            "unresolved"
            if model["unresolved"] or any(g.intersects(geometry) for g in unknown)
            else "permitted"
        )

    return check


def connect_endpoints(grid, endpoints):
    """One connector to the containing cell (stable ID tie break on boundaries)."""
    check = constraint_checker(grid)
    forward = Transformer.from_crs(4326, grid["analysis_crs"], always_xy=True).transform
    connectors = []
    for name in ("start", "end"):
        coordinate = endpoints[name]
        if (
            not isinstance(coordinate, (list, tuple))
            or len(coordinate) != 2
            or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v)
                for v in coordinate
            )
        ):
            raise ValueError(f"Invalid {name} endpoint: expected finite longitude/latitude.")
        point = Point(coordinate)
        candidates = sorted(
            (c for c in grid["cells"] if shape(c["geometry"]).covers(point)),
            key=lambda c: c["id"],
        )
        point_state = check([coordinate])
        cell = candidates[0] if candidates else None
        state = check([coordinate, cell["center"]]) if cell else "blocked"
        if cell and cell["state"] != "permitted":
            state = cell["state"]
        a = forward(*coordinate)
        b = forward(*cell["center"]) if cell else a
        reasons = (
            list(cell["reasons"])
            if cell
            else [{"source": "bounds", "reason": "Endpoint outside grid."}]
        )
        segment = Point(a) if a == b else LineString([a, b])
        for zone in grid["validation"].get("zone_diagnostics", []):
            geometry = transform(forward, shape(zone["geometry"]))
            if geometry.intersects(segment):
                reason = {"source": zone["source"], "reason": zone["reason"]}
                if reason not in reasons:
                    reasons.append(reason)
        connectors.append(
            {
                "endpoint": name,
                "coordinate": list(coordinate),
                "cell": cell["id"] if cell else None,
                "length_m": hypot(b[0] - a[0], b[1] - a[1]),
                "state": state,
                "point_state": point_state,
                "reasons": reasons,
            }
        )
    return {**grid, "connectors": connectors}


def search_graph(
    positions, edges, start, goal, *, algorithm="astar", max_expansions=MAX_EXPANSIONS
):
    """A* or its zero-heuristic Dijkstra oracle; finish on current goal pop."""
    if algorithm not in ("astar", "dijkstra"):
        raise ValueError("Unknown routing algorithm.")
    adjacency = {node: [] for node in positions}
    for u, v, length in edges:
        if not isfinite(length) or length < 0:
            raise ValueError("Edge lengths must be finite and nonnegative.")
        if length + 1e-6 < hypot(
            positions[u][0] - positions[v][0], positions[u][1] - positions[v][1]
        ):
            raise ValueError("Edge length is shorter than its metric displacement.")
        adjacency[u].append((v, length))
        adjacency[v].append((u, length))

    def heuristic(node):
        return (
            hypot(positions[node][0] - positions[goal][0], positions[node][1] - positions[goal][1])
            if algorithm == "astar"
            else 0.0
        )

    queue = [(heuristic(start), 0.0, start)]
    distances, previous, expanded = {start: 0.0}, {}, 0
    while queue:
        _, distance, node = heappop(queue)
        if distance != distances[node]:
            continue
        if expanded >= max_expansions:
            return {"status": "resource_limit", "expanded": expanded}
        expanded += 1
        if node == goal:
            path = [goal]
            while path[-1] != start:
                path.append(previous[path[-1]])
            return {
                "status": "success",
                "nodes": path[::-1],
                "length_m": distance,
                "expanded": expanded,
            }
        for neighbor, weight in sorted(adjacency[node]):
            candidate = distance + weight
            if candidate < distances.get(neighbor, float("inf")):
                distances[neighbor], previous[neighbor] = candidate, node
                heappush(queue, (candidate + heuristic(neighbor), candidate, neighbor))
    return {"status": "no_path_on_grid", "expanded": expanded}


def plan_route(grid, *, algorithm="astar", max_expansions=MAX_EXPANSIONS):
    if algorithm not in ("astar", "dijkstra"):
        raise ValueError("Unknown routing algorithm.")
    started = perf_counter()
    check = constraint_checker(grid)
    connectors = {c["endpoint"]: c for c in grid["connectors"]}
    coordinates = {c["id"]: c["center"] for c in grid["cells"]}
    coordinates.update({name: connectors[name]["coordinate"] for name in ("start", "end")})
    result = {
        "algorithm": algorithm,
        "rules_version": RULES_VERSION,
        "cell_size_m": grid["cell_size_m"],
        "analysis_crs": grid["analysis_crs"],
        "policy": grid["policy"],
        "assumptions": grid["assumptions"],
        "connectors": grid["connectors"],
        "start": coordinates["start"],
        "end": coordinates["end"],
        "geometry": None,
        "length_m": None,
    }
    point_states = [check([coordinates[n]]) for n in ("start", "end")]
    if "blocked" in point_states:
        result.update(
            status="invalid_endpoint",
            message="Endpoint outside bounds or touching a modeled obstacle.",
        )
    elif "unresolved" in point_states:
        result.update(
            status="unresolved_input",
            message="Coverage or constraint applicability unresolved; conservative policy prevents a validated route.",
        )
    elif coordinates["start"] == coordinates["end"]:
        result.update(
            status="success",
            length_m=0.0,
            nodes=["start"],
            geometry={
                "type": "LineString",
                "coordinates": [coordinates["start"], coordinates["end"]],
            },
        )
    else:
        valid = {c["id"] for c in grid["cells"] if c["state"] == "permitted"}
        forward = Transformer.from_crs(4326, grid["analysis_crs"], always_xy=True)
        metric_positions = {
            c["id"]: c["center_metric"] for c in grid["cells"] if "center_metric" in c
        }
        positions = {
            n: metric_positions.get(n, forward.transform(*p))
            for n, p in coordinates.items()
            if n in valid or n in ("start", "end")
        }
        by_position = {(c["row"], c["col"]): c["id"] for c in grid["cells"]}
        cells = {c["id"]: c for c in grid["cells"]}
        edges = []
        for edge in grid["edges"]:
            u, v = edge["from"], edge["to"]
            if edge["state"] != "permitted" or u not in valid or v not in valid:
                continue
            a, b = cells[u], cells[v]
            if a["row"] != b["row"] and a["col"] != b["col"]:
                if any(
                    by_position.get(p) not in valid
                    for p in ((a["row"], b["col"]), (b["row"], a["col"]))
                ):
                    continue
            if check([coordinates[u], coordinates[v]]) == "permitted":
                edges.append((u, v, edge["length_m"]))
        for name, c in connectors.items():
            if (
                c["state"] == "permitted"
                and c["cell"] in valid
                and check([coordinates[name], coordinates[c["cell"]]]) == "permitted"
            ):
                edges.append((name, c["cell"], c["length_m"]))
        found = search_graph(
            positions, edges, "start", "end", algorithm=algorithm, max_expansions=max_expansions
        )
        result.update(found)
        if found["status"] == "success":
            path = [coordinates[n] for n in found["nodes"]]
            if any(check([a, b]) != "permitted" for a, b in zip(path, path[1:])):
                result.update(
                    status="computational_failure",
                    length_m=None,
                    message="Final segment validation failed.",
                )
            else:
                result["geometry"] = {"type": "LineString", "coordinates": path}
        elif found["status"] == "no_path_on_grid":
            if any(
                item["state"] == "unresolved"
                for item in grid["cells"] + grid["edges"] + grid["connectors"]
            ):
                result.update(
                    status="unresolved_input",
                    message="Unresolved states or connections excluded by conservative policy; no validated path available.",
                )
            else:
                result["message"] = (
                    "No path on this constructed grid; continuous-space feasibility is not established."
                )
        else:
            result["message"] = "Search resource limit reached; path existence remains unknown."
    result["runtime_ms"] = (perf_counter() - started) * 1000
    return result


def route_geojson(result):
    """Export own route geometry and metadata, never source polygon/raster payloads."""
    return {
        "type": "FeatureCollection",
        "metadata": {k: v for k, v in result.items() if k != "geometry"},
        "features": [
            {
                "type": "Feature",
                "geometry": result["geometry"],
                "properties": {"length_m": result["length_m"], "rules_version": RULES_VERSION},
            }
        ]
        if result["status"] == "success"
        else [],
    }


def route_context(manifest, endpoints):
    """Identical actual mission and model/source provenance for API and CLI exports."""
    return {
        **manifest,
        "config": {**manifest["config"], **endpoints},
        "connector_policy": "Containing cell only; stable ID on boundaries; no direct start-goal edge.",
        "optimality": "Shortest horizontal distance on the constructed graph only.",
        "export_scope": "Own route and provenance only; original source payloads excluded. Retain source attributions and licenses.",
    }
