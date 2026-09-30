"""Metric preparation graph with explicit, conservative uncertainty semantics."""

from __future__ import annotations

from contextlib import ExitStack
from math import ceil, floor, hypot, isfinite

import rasterio
from pyproj import Transformer
from shapely.geometry import LineString, Point, box, mapping, shape
from shapely.ops import transform
from shapely.prepared import prep

from uas_planner.core.experiment import read_json, safe_file, validate_config

DEFAULT_CELL_M = 50.0
MAX_GRID_CELLS = 10000


def validate_cell_size(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError("Grid cell size must be a finite positive number of metres.")
    if value <= 0:
        raise ValueError("Grid cell size must be positive.")
    return float(value)


def _altitude_limit(properties, prefix, agl, ground):
    value = properties.get(prefix + "_limit_altitude")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        return "unknown"
    unit = properties.get(prefix + "_limit_unit")
    reference = properties.get(prefix + "_limit_alt_ref")
    if unit not in ("m", "ft") or reference not in ("AGL", "MSL"):
        return "unknown"
    metres = value if unit == "m" else value * 0.3048
    if reference == "MSL":
        if ground is None:
            return "unknown"
        return (ground + agl, metres)
    return (agl, metres)


def _zone_state(properties, agl, ground):
    """Only prove vertical nonintersection; legal permission requires verified rules."""
    lower = _altitude_limit(properties, "lower", agl, ground)
    upper = _altitude_limit(properties, "upper", agl, ground)
    if lower == "unknown" or upper == "unknown":
        return "unresolved", "Altitude limit or reference cannot be interpreted."
    if lower is not None and lower[0] < lower[1]:
        return "permitted", "Flight altitude below the reported lower limit."
    if upper is not None and upper[0] > upper[1]:
        return "permitted", "Flight altitude above the reported upper limit."
    return "unresolved", "Vertical overlap; legal, time and scenario conditions unverified."


def _population(src, source, polygon):
    """Area-weight native counts; density uses observed support only."""
    native = transform(Transformer.from_crs(25832, src.crs, always_xy=True).transform, polygon)
    bounds = native.bounds
    col0, row0 = ~src.transform @ (bounds[0], bounds[3])
    col1, row1 = ~src.transform @ (bounds[2], bounds[1])
    total, observed, unknown = 0.0, 0.0, 0.0
    outside = native.difference(box(*src.bounds)).area
    # Ignore sub-micrometre-square round-trip projection slivers at raster edges.
    unknown += outside if outside > 1e-6 else 0.0
    for row in range(max(0, floor(row0)), min(src.height, ceil(row1))):
        for col in range(max(0, floor(col0)), min(src.width, ceil(col1))):
            x, y = src.transform @ (col, row)
            pixel = box(x, y - 100, x + 100, y)
            overlap = native.intersection(pixel).area
            if overlap <= 0:
                continue
            value = src.read(1, window=((row, row + 1), (col, col + 1)), masked=True)[0, 0]
            if (
                bool(getattr(value, "mask", False))
                or not isfinite(float(value))
                or float(value) == source["raster"]["effective_nodata"]
            ):
                unknown += overlap
            elif float(value) < 0:
                raise ValueError("Negative GHSL population outside declared NoData.")
            else:
                observed += overlap
                total += float(value) * overlap / 10000
    return {
        "estimated_people": None if unknown else total,
        "people_per_km2": None if unknown or not observed else total / observed * 1_000_000,
        "known_area_m2": observed,
        "unknown_area_m2": unknown,
        "native_support_m": 100,
    }


def build_grid(directory, manifest, cell_m=DEFAULT_CELL_M, endpoints=None):
    """Prepare cells and candidate edges without performing route search."""
    cell_m = validate_cell_size(cell_m)
    config = manifest["config"]
    area = validate_config(config)
    forward = Transformer.from_crs(4326, 25832, always_xy=True).transform
    reverse = Transformer.from_crs(25832, 4326, always_xy=True).transform
    footprint = transform(forward, box(*area.as_tuple()))
    minx, miny, maxx, maxy = footprint.bounds
    nx, ny = ceil((maxx - minx) / cell_m), ceil((maxy - miny) / cell_m)
    if nx * ny > MAX_GRID_CELLS:
        raise ValueError(f"Grid exceeds {MAX_GRID_CELLS} cells; increase cell size.")
    zones = []
    for response in manifest["sources"]["dipul"]["responses"]:
        for feature in read_json(safe_file(directory, response["path"]))["features"]:
            geometry = transform(forward, shape(feature["geometry"]))
            zones.append(
                (
                    feature["id"],
                    response["type_name"],
                    geometry,
                    prep(geometry),
                    feature["properties"],
                )
            )
    with ExitStack() as stack:
        population_src = stack.enter_context(
            rasterio.open(safe_file(directory, manifest["sources"]["ghsl"]["path"]))
        )
        terrain_src = stack.enter_context(
            rasterio.open(safe_file(directory, manifest["sources"]["terrain"]["path"]))
        )
        terrain_forward = Transformer.from_crs(4326, terrain_src.crs, always_xy=True).transform
        cells, metric = [], []
        for row in range(ny):
            for col in range(nx):
                polygon = box(
                    minx + col * cell_m,
                    miny + row * cell_m,
                    min(minx + (col + 1) * cell_m, maxx),
                    min(miny + (row + 1) * cell_m, maxy),
                ).intersection(footprint)
                if polygon.is_empty or polygon.area <= 0:
                    continue
                center = polygon.representative_point()
                lon, lat = reverse(center.x, center.y)
                tx, ty = terrain_forward(lon, lat)
                tr, tc = terrain_src.index(tx, ty)
                ground = None
                if 0 <= tr < terrain_src.height and 0 <= tc < terrain_src.width:
                    raw = terrain_src.read(1, window=((tr, tr + 1), (tc, tc + 1)), masked=True)[
                        0, 0
                    ]
                    if (
                        not bool(getattr(raw, "mask", False))
                        and isfinite(float(raw))
                        and float(raw)
                        != manifest["sources"]["terrain"]["raster"]["effective_nodata"]
                    ):
                        ground = float(raw)
                reasons = []
                if ground is None:
                    reasons.append({"source": "terrain", "reason": "Ground elevation unknown."})
                for zone_id, layer, _, prepared, properties in zones:
                    if prepared.intersects(polygon):
                        # A center sample does not bound terrain across a cell.
                        state, reason = _zone_state(properties, config["agl_m"], None)
                        if state == "unresolved":
                            reasons.append({"source": f"{layer}/{zone_id}", "reason": reason})
                reasons.append(
                    {"source": "DIPUL", "reason": "Temporary restriction coverage unverified."}
                )
                ident = f"{row}:{col}"
                cells.append(
                    {
                        "id": ident,
                        "row": row,
                        "col": col,
                        "geometry": mapping(transform(reverse, polygon)),
                        "center": [lon, lat],
                        "terrain_m": ground,
                        "aircraft_altitude_m": None if ground is None else ground + config["agl_m"],
                        "population": _population(
                            population_src, manifest["sources"]["ghsl"], polygon
                        ),
                        "state": "unresolved",
                        "reasons": reasons,
                    }
                )
                metric.append((center.x, center.y, polygon))
    by_position = {(cell["row"], cell["col"]): i for i, cell in enumerate(cells)}
    edges = []
    for i, cell in enumerate(cells):
        x, y, polygon = metric[i]
        for dr, dc in ((0, 1), (1, -1), (1, 0), (1, 1)):
            j = by_position.get((cell["row"] + dr, cell["col"] + dc))
            if j is None:
                continue
            nx_, ny_, other = metric[j]
            line = LineString([(x, y), (nx_, ny_)])
            reasons = []
            if (
                dr
                and dc
                and (
                    (cell["row"], cell["col"] + dc) not in by_position
                    or (cell["row"] + dr, cell["col"]) not in by_position
                )
            ):
                reasons.append({"source": "grid", "reason": "Diagonal corner cutting."})
            for zone_id, layer, _, prepared, properties in zones:
                if prepared.intersects(line):
                    state, reason = _zone_state(properties, config["agl_m"], None)
                    if state == "unresolved":
                        reasons.append({"source": f"{layer}/{zone_id}", "reason": reason})
            reasons.extend(cell["reasons"] + cells[j]["reasons"])
            edges.append(
                {
                    "from": cell["id"],
                    "to": cells[j]["id"],
                    "length_m": hypot(nx_ - x, ny_ - y),
                    "state": "blocked"
                    if any(r["reason"] == "Diagonal corner cutting." for r in reasons)
                    else "unresolved",
                    "reasons": reasons,
                }
            )
    connectors = []
    selected = endpoints or {name: config[name] for name in ("start", "end")}
    for name in ("start", "end"):
        coordinate = selected[name]
        if (
            len(coordinate) != 2
            or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v)
                for v in coordinate
            )
            or not (
                area.west <= coordinate[0] <= area.east
                and area.south <= coordinate[1] <= area.north
            )
        ):
            raise ValueError(
                f"Invalid {name} endpoint: expected a finite point inside the experiment bounds."
            )
        x, y = forward(*coordinate)
        point = Point(x, y)
        candidates = [(i, point.distance(polygon)) for i, (_, _, polygon) in enumerate(metric)]
        i = min(candidates, key=lambda item: item[1])[0]
        cell = cells[i]
        line = LineString([(x, y), metric[i][:2]])
        reasons = list(cell["reasons"])
        for zone_id, layer, _, prepared, properties in zones:
            if prepared.intersects(line):
                state, reason = _zone_state(properties, config["agl_m"], None)
                if state == "unresolved":
                    reasons.append({"source": f"{layer}/{zone_id}", "reason": reason})
        connectors.append(
            {
                "endpoint": name,
                "coordinate": list(coordinate),
                "cell": cell["id"],
                "length_m": line.length,
                "state": "unresolved",
                "reasons": reasons,
            }
        )
    return {
        "cell_size_m": cell_m,
        "analysis_crs": "EPSG:25832",
        "policy": "block_unresolved",
        "cell_count": len(cells),
        "edge_count": len(edges),
        "cells": cells,
        "edges": edges,
        "connectors": connectors,
        "assumptions": {
            "scenario": config["scenario"],
            "agl_m": config["agl_m"],
            "mission_start": config["mission_start"],
            "mission_end": config["mission_end"],
            "temporary_restrictions": config["temporary_restrictions"],
        },
    }
