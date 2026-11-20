"""Allocate resident walking budgets on the saved metric study grid."""

from collections import Counter, defaultdict
from functools import lru_cache
from heapq import heappop, heappush
from math import fsum, hypot, isclose

import networkx as nx
from shapely import LineString, STRtree, linestrings, points

MODEL_VERSION = "pedestrian-exposure-150m-mid-public-v2"
WALK_LIMIT_M = 2500
SNAP_LIMIT_M = 150
DESTINATION_LIMIT = 6
DISTANCE_DECAY_M = 500
ALTERNATE_DECAY_M = 750
FOOT_ACCESS = {"yes", "designated", "permissive", "official"}
NO_ACCESS = {"no", "private", "customers", "permit", "delivery"}
WALK_HIGHWAYS = {
    "footway",
    "pedestrian",
    "path",
    "steps",
    "living_street",
    "residential",
    "service",
    "unclassified",
    "track",
}
SIDEWALK_HIGHWAYS = {"primary", "secondary", "tertiary", "trunk"}
SHELTER_KEYS = ("covered", "tunnel", "indoor")


def is_walkable(tags):
    highway = tags.get("highway")
    foot = tags.get("foot")
    if (
        highway in {None, "motorway", "motorway_link", "construction", "proposed"}
        or foot in NO_ACCESS
    ):
        return False
    if foot in FOOT_ACCESS:
        return True
    if tags.get("access") in NO_ACCESS or tags.get("service") in {"driveway", "parking_aisle"}:
        return False
    return highway in WALK_HIGHWAYS or (
        highway in SIDEWALK_HIGHWAYS and tags.get("sidewalk") in {"yes", "both", "left", "right"}
    )


def shelter_state(tags):
    values = {tags.get(key) for key in SHELTER_KEYS}
    if values.intersection({"unknown", "uncertain"}):
        return "uncertain"
    if values.difference({None, "", "no", "0", "false"}):
        return "covered"
    return "outdoor"


def destination_purposes(tags):
    """Use only declared land use, functions and mapped places."""
    if tags.get("access") in NO_ACCESS:
        return ()
    amenity, building, landuse = (tags.get(key) for key in ("amenity", "building", "landuse"))
    uses = set()
    if (
        tags.get("office")
        or building in {"office", "industrial", "warehouse", "commercial"}
        or landuse in {"commercial", "industrial"}
    ):
        uses.add("work")
    education = {"school", "college", "university", "kindergarten", "childcare"}
    if amenity in education or building in education:
        uses.add("education")
    if (
        tags.get("shop") not in (None, "", "no", "vacant")
        or building in {"retail", "supermarket"}
        or landuse == "retail"
        or amenity in {"pharmacy", "clinic", "hospital", "bank", "post_office", "marketplace"}
    ):
        uses.add("errands")
    if (
        tags.get("leisure")
        in {"park", "garden", "playground", "sports_centre", "pitch", "nature_reserve"}
        or tags.get("tourism") in {"attraction", "museum", "gallery"}
        or amenity in {"restaurant", "cafe", "library", "theatre", "community_centre"}
        or landuse in {"recreation_ground", "village_green"}
    ):
        uses.add("leisure")
    return tuple(sorted(uses))


def walking_graph(features):
    """Connect shared vertices of mapped ways, keeping elevated interiors separate."""
    graph = nx.Graph()
    for geom, tags in features:
        if not is_walkable(tags) or geom is None or geom.is_empty or not geom.is_valid:
            continue
        lines = geom.geoms if geom.geom_type == "MultiLineString" else (geom,)
        for line in lines:
            if line.geom_type != "LineString":
                continue
            coords = [(x, y) for x, y, *_ in line.coords]
            level = tags.get("layer", "0")
            if level == "0" and tags.get("bridge") not in (None, "no"):
                level = "bridge"
            if level == "0" and tags.get("tunnel") not in (None, "no"):
                level = "tunnel"
            vertices = [
                (*coord, "0" if index in (0, len(coords) - 1) else level)
                for index, coord in enumerate(coords)
            ]
            shelter = shelter_state(tags)
            for start, end in zip(vertices, vertices[1:]):
                length = hypot(start[0] - end[0], start[1] - end[1])
                if length <= 0:
                    continue
                existing = graph.get_edge_data(start, end)
                state = "uncertain" if existing and existing["shelter"] != shelter else shelter
                graph.add_edge(start, end, length=length, shelter=state)
    return graph


def split_edge(start, end, cells, tree):
    """Return lengths by cell, assigning shared-edge geometry once in cell order."""
    segment = LineString((start[:2], end[:2]))
    remaining = segment
    lengths = []
    for index in sorted(int(idx) for idx in tree.query(segment, predicate="intersects")):
        polygon = cells[index][0]
        length = remaining.intersection(polygon).length
        if length > 0:
            lengths.append((index, length))
            remaining = remaining.difference(polygon)
    outside = max(0, segment.length - sum(length for _, length in lengths))
    return lengths, outside


def nearby_destinations(graph, origin, destination_nodes):
    """Settle routes only as far as the nearest eligible destinations."""
    previous = {}
    distances = {origin: 0.0}
    queue = [(0.0, origin)]
    chosen = []
    while queue and len(chosen) < DESTINATION_LIMIT:
        distance, node = heappop(queue)
        if distance != distances[node]:
            continue
        if node != origin and node in destination_nodes:
            chosen.append((distance, node, destination_nodes[node]))
        for neighbor, edge in graph[node].items():
            length = distance + edge["length"]
            if length <= WALK_LIMIT_M and length < distances.get(neighbor, float("inf")):
                distances[neighbor] = length
                previous[neighbor] = node
                heappush(queue, (length, neighbor))
    return chosen, previous


def allocate(cells, daily_departures, graph, destinations):
    """Distribute fractions of daily walking departures using fixed OSM paths."""
    origin_departures = defaultdict(list)
    unavailable = {i: "ghsl_coverage" for i, cell in enumerate(cells) if cell[2] is None}
    missed = Counter()
    surface_nodes = sorted(node for node in graph if node[2] == "0")
    node_tree = STRtree(points([node[:2] for node in surface_nodes])) if surface_nodes else None

    def snap(point):
        if node_tree is None:
            return None
        # STRtree nearest ties are unspecified. Resolve them by the sorted node order.
        indices, distances = node_tree.query_nearest(
            point, max_distance=SNAP_LIMIT_M, return_distance=True
        )
        if len(indices) == 0 or min(distances) > SNAP_LIMIT_M:
            return None
        return surface_nodes[int(min(indices))]

    for index, ((polygon, _, _), departures) in enumerate(
        zip(cells, daily_departures, strict=True)
    ):
        if departures == 0:
            continue
        if index in unavailable:
            missed["incomplete_ghsl"] += departures
            continue
        node = snap(polygon.representative_point())
        if node is None:
            unavailable[index] = "no_mapped_connection"
            missed["no_mapped_connection"] += departures
        else:
            origin_departures[node].append((index, departures))

    destination_nodes = Counter()
    for geom, uses in destinations:
        node = snap(geom.representative_point())
        if node is not None:
            destination_nodes[node] += len(uses)

    tree = STRtree([polygon for polygon, _, _ in cells])
    shelter_unknown = []
    outdoor_edges = []
    for start, end, edge in graph.edges(data=True):
        segment = (start[:2], end[:2])
        if edge["shelter"] == "uncertain":
            shelter_unknown.append(segment)
        elif edge["shelter"] == "outdoor":
            outdoor_edges.append(segment)
    for index in _intersected_cells(tree, shelter_unknown):
        unavailable.setdefault(index, "uncertain_path_shelter")

    @lru_cache(maxsize=150_000)
    def edge_cells(start, end):
        return split_edge(start, end, cells, tree)

    def path_parts(origin, destination, previous):
        counts = Counter()
        covered = outside = uncertain = 0.0
        while destination != origin:
            start = previous[destination]
            edge = graph[start][destination]
            if edge["shelter"] == "covered":
                covered += edge["length"]
            elif edge["shelter"] == "uncertain":
                uncertain += edge["length"]
            else:
                intersections, beyond = edge_cells(*sorted((start, destination)))
                outside += beyond
                for index, length in intersections:
                    counts[index] += length
            destination = start
        return counts, covered, outside, uncertain

    totals = {
        decay: ([0.0] * len(cells), Counter()) for decay in (DISTANCE_DECAY_M, ALTERNATE_DECAY_M)
    }
    for origin, origins in origin_departures.items():
        candidates, previous = nearby_destinations(graph, origin, destination_nodes)
        departures = fsum(budget for _, budget in origins)
        if not candidates:
            missed["no_reachable_destination"] += departures
            for index, _ in origins:
                unavailable.setdefault(index, "no_reachable_destination")
            continue
        routes = [path_parts(origin, node, previous) for _, node, _ in candidates]
        for decay, (per_cell, ledger) in totals.items():
            weights = [
                capacity / (1 + distance / decay) ** 2 for distance, _, capacity in candidates
            ]
            weight_sum = fsum(weights)
            for (distance, _, _), (placements, covered, outside, uncertain), weight in zip(
                candidates, routes, weights, strict=True
            ):
                per_metre = departures * weight / (weight_sum * distance)
                ledger["covered"] += covered * per_metre
                ledger["outside_region"] += outside * per_metre
                ledger["unallocated"] += uncertain * per_metre
                for index, length in placements.items():
                    per_cell[index] += length * per_metre

    budget = fsum(daily_departures)
    results = {}
    for decay, (per_cell, ledger) in totals.items():
        ledger["budget"] = budget
        ledger["unallocated"] += fsum(missed.values()) + fsum(per_cell[i] for i in unavailable)
        for index in unavailable:
            per_cell[index] = None
        ledger["outdoor_in_region"] = fsum(value for value in per_cell if value is not None)
        if not isclose(
            budget,
            fsum(
                ledger[name]
                for name in ("outdoor_in_region", "covered", "outside_region", "unallocated")
            ),
            abs_tol=1e-7,
        ):
            raise ValueError("Spatial walking budget does not reconcile.")
        results[decay] = (per_cell, dict(ledger))

    diagnostics = {
        "walking_nodes": graph.number_of_nodes(),
        "walking_edges": graph.number_of_edges(),
        "cells_intersecting_outdoor_edges": len(_intersected_cells(tree, outdoor_edges)),
        "destination_nodes": len(destination_nodes),
        "residential_origin_nodes": len(origin_departures),
        "unavailable_cells": dict(Counter(unavailable.values())),
        "unresolved_origin_daily_departures": dict(missed),
    }
    return results, unavailable, diagnostics


def _intersected_cells(tree, segments):
    if not segments:
        return set()
    return set(tree.query(linestrings(segments), predicate="intersects")[1].tolist())
