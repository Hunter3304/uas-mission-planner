"""Request-local automatic cruise intervals; explicit historical intervals stay separate."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from math import ceil, hypot, isfinite
from time import perf_counter
from zoneinfo import ZoneInfo

from pyproj import Transformer

from uas_planner.acquisition.study import validate_study
from uas_planner.core.osm_display import contained, read_object
from uas_planner.core.regional import query_geometry, validate_scenario
from uas_planner.core.risk import nonnegative, signature

MAX_PASSES = 3
REQUEST_SECONDS = 110  # Below the unchanged 120-second browser request timeout.


def timestamp_after(scenario, seconds):
    """Round elapsed time upwards to a microsecond, then format in the declared zone."""
    if not isfinite(seconds) or not 0 <= seconds <= 86400:
        raise ValueError("Automatic cruise duration must be finite and within 24 hours.")
    start = datetime.fromisoformat(scenario["mission_start"])
    if start.tzinfo is None:
        raise ValueError("Departure requires an explicit UTC offset.")
    return (
        (start.astimezone(timezone.utc) + timedelta(microseconds=ceil(seconds * 1_000_000)))
        .astimezone(ZoneInfo(scenario.get("timezone", "Europe/Berlin")))
        .isoformat()
    )


def seed_interval(
    scenario, locations, start_id, end_id, *, start_coordinate=None, end_coordinate=None
):
    if "mission_end" in scenario:
        raise ValueError("Automatic duration accepts departure only; omit mission_end.")
    scenario = deepcopy(scenario)
    sites = {s["id"]: s for s in locations}
    if start_id not in sites or end_id not in sites:
        raise ValueError("Select endpoints from the verified location catalog.")
    endpoints = [
        override if override is not None else [sites[ident]["longitude"], sites[ident]["latitude"]]
        for ident, override in ((start_id, start_coordinate), (end_id, end_coordinate))
    ]
    query_geometry(endpoints)
    # Validate the original speed, offsets and all evidence before dividing.
    provisional = {**scenario, "mission_end": timestamp_after(scenario, 0.000001)}
    validate_scenario(provisional)
    forward = Transformer.from_crs(4326, 25832, always_xy=True).transform
    a, b = [forward(*point) for point in endpoints]
    lower_bound = hypot(b[0] - a[0], b[1] - a[1]) / scenario["speed_m_s"]
    provisional["mission_end"] = timestamp_after(scenario, max(0.000001, lower_bound))
    validate_scenario(provisional)
    return provisional


def provisional_scenario(directory, scenario, start_id, end_id, **endpoints):
    """Small metadata read only; real preparation still verifies all retained sources."""
    manifest = read_object(contained(directory, "study.json"))
    if manifest.get("kind") != "regional-source-study" or manifest.get("schema_version") != 1:
        raise ValueError("Unsupported regional study manifest.")
    validate_study(manifest["config"])
    return seed_interval(scenario, manifest["config"]["locations"], start_id, end_id, **endpoints)


def interval_of(scenario):
    return {key: scenario[key] for key in ("mission_start", "mission_end")}


def automatic_route(directory, scenario, start_id, end_id, *, terrain_directory=None, **controls):
    from uas_planner.core.regional_routing import RegionalPlanner

    started = perf_counter()
    deadline = started + REQUEST_SECONDS
    original = deepcopy(scenario)
    budget = nonnegative(controls.get("time_budget_s", 3), "Planning time budget")
    if budget > 60:
        raise ValueError("Planning time budget must be at most 60 seconds.")
    endpoints = {k: controls[k] for k in ("start_coordinate", "end_coordinate") if k in controls}
    prepared = provisional_scenario(directory, original, start_id, end_id, **endpoints)
    planner = RegionalPlanner(directory, prepared, terrain_directory=terrain_directory)
    source_ms = (perf_counter() - started) * 1000
    planner._request_deadline = deadline
    passes, search_ms, preparation_ms = [], 0.0, source_ms
    result = None
    status, message = (
        "duration_resource_limit",
        "Automatic flight assessment exceeded its shared budget.",
    )
    try:
        # Recompute from the fully verified catalog; never trust a changed seed catalog.
        verified = seed_interval(
            original,
            planner.constraints.manifest["config"]["locations"],
            start_id,
            end_id,
            **endpoints,
        )
        if datetime.fromisoformat(verified["mission_end"]) > datetime.fromisoformat(
            prepared["mission_end"]
        ):
            planner.constraints.expand_interval(verified["mission_end"])
        initial_interval = interval_of(planner.constraints.scenario)
        for number in range(1, MAX_PASSES + 1):
            planner.ensure_deadline()
            remaining = max(0, budget - search_ms / 1000)
            result = planner.plan(start_id, end_id, **{**controls, "time_budget_s": remaining})
            search_ms += result["planner_ms"]
            preparation_ms += result["preparation_ms"]
            passes.append(
                {
                    "pass": number,
                    "status": result["status"],
                    "assessed_interval": interval_of(planner.constraints.scenario),
                    "length_m": result["length_m"],
                }
            )
            if result["status"] != "success":
                break
            duration = result["length_m"] / original["speed_m_s"]
            if not isfinite(duration) or duration > 86400:
                result = {
                    "status": "duration_limit",
                    "message": "Estimated flight interval exceeds 24 hours.",
                }
                break
            arrival = timestamp_after(original, duration)
            assessed_end = datetime.fromisoformat(planner.constraints.scenario["mission_end"])
            if datetime.fromisoformat(arrival) > assessed_end:
                planner.constraints.expand_interval(arrival)
            planner.ensure_deadline()
            checked = planner.check(
                result["geometry"]["coordinates"], controls.get("planning_mode", "strict")
            )
            passes[-1]["complete_interval_state"] = checked["state"]
            passes[-1]["rechecked_interval"] = interval_of(planner.constraints.scenario)
            if checked["state"] == "permitted":
                planner.ensure_deadline()
                current = planner.constraints.scenario
                result["endpoint_diagnostics"] = {
                    name: planner.check([result[name]], controls.get("planning_mode", "strict"))
                    for name in ("start", "end")
                }
                result["research_assumptions"] = list(
                    {signature(item): item for item in checked["assumptions"]}.values()
                )
                result["restriction_report"] = planner.constraints.restriction_report(
                    controls.get("planning_mode", "strict")
                )
                result["restriction_report"]["assessed_interval"] = interval_of(current)
                result["restriction_report"]["planning_mode"] = controls.get(
                    "planning_mode", "strict"
                )
                result["restriction_report"]["policy_exclusions"] = (
                    result["restriction_report"]["counts"].get("unresolved", 0)
                    if controls.get("planning_mode", "strict") == "conservative"
                    else 0
                )
                result["provenance"] = deepcopy(planner.constraints.provenance)
                if result.get("population_active") and result.get("population_model"):
                    result["provenance"].update(
                        ghsl_routing_cost=True,
                        population_model_identity=result["population_model"]["identity"],
                    )
                if isinstance(result.get("assumptions"), dict):
                    result["assumptions"] = deepcopy(current)
                if "risk_model" in result:
                    provenance = result["risk_model"]
                    provenance["source"] = deepcopy(result["provenance"])
                    provenance.pop("model_signature", None)
                    provenance["model_signature"] = signature(provenance)
                result["mission"] = {
                    **current,
                    "mission_end": arrival,
                    "start_id": start_id,
                    "end_id": end_id,
                }
                result["controls"]["duration_mode"] = "automatic"
                result["controls"]["time_budget_s"] = budget
                result["prepared_identity"] = signature(
                    {
                        "provenance": result["provenance"],
                        "controls": result["controls"],
                        "endpoints": {k: result[k] for k in ("start", "end")},
                        **(
                            {"population_model_identity": result["population_model"]["identity"]}
                            if result.get("population_active") and result.get("population_model")
                            else {}
                        ),
                    }
                )
                result["timing"] = {
                    "mode": "automatic",
                    "departure": original["mission_start"],
                    "estimated_arrival": arrival,
                    "cruise_time_s": duration,
                    "estimated_interval": {
                        "mission_start": original["mission_start"],
                        "mission_end": arrival,
                    },
                    "assessed_interval": interval_of(current),
                    "provisional_interval": initial_interval,
                    "passes": passes,
                    "cruise_only": True,
                    "zero_duration_rule": "Instantaneous route; endpoint checked over a conservative one-microsecond interval."
                    if duration == 0
                    else None,
                }
                planner.ensure_deadline()
                break
            result = None
            status, message = (
                "duration_unstable",
                "No candidate passed complete-interval validation within three bounded passes.",
            )
        if result is None or result.get("status") == "success" and "timing" not in result:
            result = {"status": status, "message": message}
    except TimeoutError:
        result = {
            "status": "duration_resource_limit",
            "message": "Automatic flight assessment exceeded its shared request deadline.",
        }
    finally:
        planner.constraints.terrain.close()
    if result["status"] != "success":
        result = {**deepcopy(getattr(planner, "_last_result", {})), **result}
        result.update(
            geometry=None,
            length_m=None,
            risk_length_cost=None,
            population_length_cost=None,
            objective_cost=None,
            cruise_time_s=None,
            cruise_time_range_s=None,
            exact=False,
            solution_kind="none",
            independent_validation=False,
        )
        if result.get("population_active"):
            result["population_assessment"] = "unresolved"
        result["timing"] = {
            "mode": "automatic",
            "estimated_arrival": None,
            "estimated_interval": None,
            "cruise_time_s": None,
            "assessed_interval": interval_of(planner.constraints.scenario),
            "passes": passes,
            "cruise_only": True,
        }
        if isinstance(result.get("controls"), dict):
            result["controls"].update(duration_mode="automatic", time_budget_s=budget)
    result.update(
        runtime_ms=(perf_counter() - started) * 1000,
        source_preparation_ms=source_ms,
        preparation_ms=preparation_ms,
        planner_ms=search_ms,
    )
    return result
