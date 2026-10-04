"""Explicit research assumptions without mutating strict cached source grids."""

from copy import deepcopy

from shapely.geometry import LineString, shape

from uas_planner.core.routing import connect_endpoints, constraint_checker

RESEARCH_ASSUMPTION = (
    "Research only: unresolved DIPUL time, height and scenario applicability and "
    "temporary-restriction coverage are assumed not to exclude travel. "
    "Building risk integrates polygon footprints only; non-polygon building objects "
    "are omitted without inferring their extent, with source diagnostics retained. "
    "No flight permission or legal validation; terrain samples do not prove 3D clearance."
)


def planning_grid(grid, mode, endpoints, clearance=0):
    if mode not in ("strict", "research"):
        raise ValueError("Unknown planning mode.")
    result = deepcopy(grid)
    if mode == "research":
        result["policy"] = "explicit_research_assumptions"
        result["assumptions"]["research_constraints"] = RESEARCH_ASSUMPTION
        validation = result["validation"]
        validation["unresolved"] = False
        # Preserve existing unknown regions and add missing terrain support.
        validation["unresolved_regions"] = validation.get("unresolved_regions", []) + [
            c["geometry"] for c in result["cells"] if c["terrain_m"] is None
        ]
        zone_sources = {z["source"] for z in validation.get("zone_diagnostics", [])}
        for cell in result["cells"]:
            if cell["state"] == "blocked":
                validation["blocked"].append(cell["geometry"])
            elif any(
                r["source"] != "DIPUL" and r["source"] not in zone_sources for r in cell["reasons"]
            ):
                validation["unresolved_regions"].append(cell["geometry"])
        check = constraint_checker(result, clearance)
        by_position = {(c["row"], c["col"]): c for c in result["cells"]}
        by_id = {c["id"]: c for c in result["cells"]}
        for cell in result["cells"]:
            cell["source_state"] = cell["state"]
            cell["source_reasons"] = cell["reasons"]
            # Only DIPUL applicability is assumed; preserve other unknown inputs.
            remaining = [
                r
                for r in cell["reasons"]
                if r["source"] == "terrain"
                or (
                    r["source"] != "DIPUL"
                    and not any(
                        r["source"] == z["source"] for z in validation.get("zone_diagnostics", [])
                    )
                )
            ]
            state = check([cell["center"]])
            cell["state"] = (
                "blocked"
                if cell["source_state"] == "blocked" or state == "blocked"
                else "unresolved"
                if remaining or state == "unresolved"
                else "permitted"
            )
            cell["reasons"] = remaining
        for edge in result["edges"]:
            a, b = by_id[edge["from"]], by_id[edge["to"]]
            state = check([a["center"], b["center"]])
            valid = edge["state"] != "blocked" and a["state"] == b["state"] == state == "permitted"
            if a["row"] != b["row"] and a["col"] != b["col"]:
                valid = valid and all(
                    pos in by_position and by_position[pos]["state"] == "permitted"
                    for pos in ((a["row"], b["col"]), (b["row"], a["col"]))
                )
            edge["state"] = "permitted" if valid else "blocked"
            edge["reasons"] = (
                []
                if valid
                else [
                    {
                        "source": "research",
                        "reason": "Retained obstacle, unknown support or corner exclusion.",
                    }
                ]
            )
    return connect_endpoints(result, endpoints, safety_distance_m=clearance)


def readiness(grid):
    global_reasons = []
    if grid["validation"]["unresolved"]:
        global_reasons.append(
            {
                "source": "DIPUL",
                "reason": "Temporary restriction coverage unverified; strict policy excludes all travel.",
            }
        )
    local = [
        {"endpoint": c["endpoint"], "state": c["state"], "reasons": c["reasons"]}
        for c in grid["connectors"]
        if c["state"] != "permitted"
    ]
    return {"global_reasons": global_reasons, "endpoint_reasons": local}


def route_uncertainties(grid, geometry):
    if geometry is None:
        return []
    route = LineString(geometry["coordinates"])
    return [
        {"source": z["source"], "reason": z["reason"]}
        for z in grid["validation"].get("zone_diagnostics", [])
        if shape(z["geometry"]).intersects(route)
    ]
