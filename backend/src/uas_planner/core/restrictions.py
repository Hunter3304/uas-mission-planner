"""Traceable zone decisions and immutable local evidence profiles.

No layer name or research policy establishes operational permission.
"""

import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from shapely.geometry import shape

from uas_planner.core.risk import signature

RULES_VERSION = "regional-restrictions-v3"
REVIEW_GROUPS = {
    "airspace": {"kontrollzonen", "flughaefen", "flugplaetze", "flugbeschraenkungsgebiete"},
    "infrastructure": {
        "bahnanlagen",
        "bundesstrassen",
        "bundesautobahnen",
        "binnenwasserstrassen",
        "seewasserstrassen",
        "schifffahrtsanlagen",
        "stromleitungen",
    },
    "nature": {"nationalparks", "naturschutzgebiete", "ffh-gebiete", "vogelschutzgebiete"},
    "residential": {"wohngrundstuecke"},
    "operating_hours": {"freibaeder"},
    "temporary_notice": {"temporaere_betriebseinschraenkungen"},
}


def review_requirement(layer):
    name = layer.split(":")[-1]
    for group, names in REVIEW_GROUPS.items():
        if name in names:
            return group
    return (
        "facility_consent_and_applicability"
        if layer.startswith("dipul:")
        else "reviewed_official_notice"
    )


OFFICIAL_HOSTS = {
    "www.dipul.de",
    "dipul.de",
    "www.dfs.de",
    "dfs.de",
    "uas-betrieb.de",
    "www.gesetze-im-internet.de",
}


def instant(value):
    if not isinstance(value, str):
        raise ValueError("Restriction dates must be ISO strings with a UTC offset.")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Restriction dates need a UTC offset.")
    return parsed.astimezone(timezone.utc)


def interval(record):
    start, end = instant(record["valid_from"]), instant(record["valid_until"])
    if end <= start:
        raise ValueError("Restriction validity must be a positive interval.")
    return start, end


def validate_assessments(assessments):
    if not isinstance(assessments, dict) or len(assessments) > 2000:
        raise ValueError("Assessments must be an object of at most 2,000 entries.")
    for source, item in assessments.items():
        if not isinstance(source, str) or not isinstance(item, dict):
            raise ValueError("Invalid assessment entry.")
        if item.get("state") not in {"prohibited", "conditional_allowed"}:
            raise ValueError("Unknown assessment state.")
        if not all(
            isinstance(item.get(k), str) and item[k].strip()
            for k in ("source_signature", "evidence")
        ):
            raise ValueError("Assessment needs a source signature and evidence.")
        interval(item)
        bounds = item.get("agl_interval_m")
        if (
            not isinstance(bounds, list)
            or len(bounds) != 2
            or any(
                isinstance(v, bool)
                or not isinstance(v, (int, float))
                or not math.isfinite(v)
                or not 0 <= v <= 10000
                for v in bounds
            )
            or bounds[0] > bounds[1]
        ):
            raise ValueError("Assessment needs a finite ordered AGL interval.")
        if item.get("scenario") not in {"civil", "BOS"}:
            raise ValueError("Assessment requires civil or BOS scenario.")
        if item.get("phase", "transit") not in {"transit", "all", "launch", "landing"}:
            raise ValueError("Unknown assessment phase.")
        conditions = item.get("conditions_satisfied")
        if item["state"] == "conditional_allowed" and (
            not isinstance(conditions, list)
            or not conditions
            or not all(isinstance(c, str) and c.strip() for c in conditions)
        ):
            raise ValueError("Conditional allowance needs explicit satisfied conditions.")


def validate_notices(notices):
    if not isinstance(notices, list) or len(notices) > 1000:
        raise ValueError("At most 1,000 reviewed notices are supported.")
    ids = set()
    for notice in notices:
        if not isinstance(notice, dict):
            raise ValueError("Invalid notice.")
        ident = notice.get("id")
        if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", ident):
            raise ValueError("Invalid notice ID.")
        if ident in ids:
            raise ValueError("Duplicate notice ID.")
        ids.add(ident)
        url = urlparse(notice.get("official_url", ""))
        if url.scheme != "https" or url.hostname not in OFFICIAL_HOSTS or url.username:
            raise ValueError("Notice needs an official HTTPS source URL.")
        if not isinstance(notice.get("evidence"), str) or not notice["evidence"].strip():
            raise ValueError("Reviewed notice needs evidence text/reference.")
        if notice.get("reviewed") is not True:
            raise ValueError("Notice normalization requires explicit human review.")
        instant(notice["checked_at"])
        geometry = shape(notice["geometry"])
        if (
            geometry.is_empty
            or not geometry.is_valid
            or geometry.geom_type not in {"Polygon", "MultiPolygon"}
        ):
            raise ValueError("Notice needs valid polygon geometry.")
        x0, y0, x1, y1 = geometry.bounds
        if not (-180 <= x0 <= x1 <= 180 and -90 <= y0 <= y1 <= 90):
            raise ValueError("Notice geometry must be longitude/latitude.")
        # Canonical validity is explicit reviewed input, never scraped date guesses.
        props = notice.get("properties", {})
        if not isinstance(props, dict):
            raise ValueError("Notice properties must be an object.")
        if "valid_from" in props or "valid_until" in props:
            interval(props)
        if notice.get("state", "unresolved") not in {"prohibited", "unresolved"}:
            raise ValueError("A notice cannot grant permission.")


def validate_profile(profile):
    if not isinstance(profile, dict) or profile.get("schema_version") != 1:
        raise ValueError("Restriction profile schema_version must be 1.")
    if not isinstance(profile.get("name"), str) or not profile["name"].strip():
        raise ValueError("Profile requires a name.")
    validate_assessments(profile.get("zone_assessments", {}))
    validate_notices(profile.get("notices", []))
    # Freshness is configurable and is never a completeness certificate.
    age = profile.get("max_source_age_days", 7)
    if isinstance(age, bool) or not isinstance(age, int) or not 1 <= age <= 365:
        raise ValueError("Source freshness must be 1–365 days.")
    return profile


def save_profile(directory, profile):
    profile = validate_profile(profile)
    folder = Path(directory) / "restriction-profiles"
    folder.mkdir(exist_ok=True)
    if not folder.resolve().is_relative_to(Path(directory).resolve()):
        raise ValueError("Profile folder escapes dataset.")
    ident = uuid4().hex
    content = {k: v for k, v in profile.items() if k not in {"id", "saved_at", "profile_signature"}}
    result = {**content, "id": ident, "saved_at": datetime.now(timezone.utc).isoformat()}
    result["profile_signature"] = signature(result)
    serialized = json.dumps(result, indent=2, allow_nan=False)
    with (folder / f"{ident}.json").open("x", encoding="utf-8") as stream:
        stream.write(serialized)
    return result


def load_profile(directory, ident):
    if not isinstance(ident, str) or not re.fullmatch(r"[a-f0-9]{32}", ident):
        raise ValueError("Invalid restriction profile ID.")
    path = Path(directory) / "restriction-profiles" / f"{ident}.json"
    if not path.resolve().is_relative_to(Path(directory).resolve()):
        raise ValueError("Profile path escapes dataset.")
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("id") != ident or result.get("profile_signature") != signature(
        {k: v for k, v in result.items() if k != "profile_signature"}
    ):
        raise ValueError("Restriction profile integrity mismatch.")
    return validate_profile(result)


def comparison_terrain(terrain, scenario, mode):
    """Return an explicitly assumed comparison frame without changing source data."""
    if (
        mode == "strict"
        or scenario.get("vertical_reference_policy", "source") != "nhn_as_msl_assumption"
        or terrain.get("status") != "known"
        or terrain.get("vertical_datum") != "DHHN2016_NHN"
    ):
        return terrain, None
    offset = scenario.get("nhn_msl_offset_m", 0)
    uncertainty = scenario.get("nhn_msl_uncertainty_m", 0)
    lower = terrain["minimum_m"] + offset - uncertainty
    upper = terrain["maximum_m"] + offset + uncertainty
    assumption = {
        "policy": "nhn_as_msl_assumption",
        "source_vertical_datum": "DHHN2016_NHN",
        "comparison_reference": "MSL",
        "offset_m": offset,
        "uncertainty_m": uncertainty,
        "ground_nhn_bounds_m": [terrain["minimum_m"], terrain["maximum_m"]],
        "ground_comparison_bounds_m": [lower, upper],
        "reason": "Explicit engineering NHN/MSL approximation, not a verified datum transformation.",
    }
    return {**terrain, "vertical_datum": "MSL", "minimum_m": lower, "maximum_m": upper}, assumption


def decision(record, scenario, terrain, vertical_check, evidence_check, *, mode="strict"):
    """Nonintersection proves only this zone inapplicable to this scenario/query."""
    props = record["properties"]
    source = record["source"]
    result = {
        "source": source,
        "source_signature": record["source_signature"],
        "layer": record["layer"],
        "rules_version": RULES_VERSION,
        "required_review": review_requirement(record["layer"]),
        "legal_reference": props.get("legal_ref"),
        "state": "unresolved",
        "vertical_relation": "unknown",
        "reason": "No evidence-backed scenario assessment.",
    }
    # Only normalized, reviewed notices use canonical time fields.
    if record.get("reviewed_notice") and ("valid_from" in props or "valid_until" in props):
        start, end = interval(props)
        if instant(scenario["mission_end"]) <= start or instant(scenario["mission_start"]) >= end:
            return {
                **result,
                "state": "not_applicable",
                "reason": "Outside reviewed validity interval.",
            }
    comparison, assumption = comparison_terrain(terrain, scenario, mode)
    uses_msl = any(
        props.get(f"{p}_limit_alt_ref") == "MSL" and props.get(f"{p}_limit_altitude") is not None
        for p in ("lower", "upper")
    )
    if assumption and uses_msl:
        result["vertical_reference_assumption"] = assumption
        result["aircraft_comparison_bounds_m"] = [
            comparison["minimum_m"] + scenario["agl_m"],
            comparison["maximum_m"] + scenario["agl_m"],
        ]
        result["vertical_comparison_quality"] = "engineering_assumption"
    state, reason = vertical_check(props, scenario["agl_m"], comparison)
    result["vertical_state"] = state
    if (
        uses_msl
        and comparison.get("status") == "known"
        and comparison.get("vertical_datum") == "MSL"
    ):
        result["zone_msl_bounds_m"] = {
            p: props[f"{p}_limit_altitude"]
            * (0.3048 if props.get(f"{p}_limit_unit") == "ft" else 1)
            for p in ("lower", "upper")
            if isinstance(props.get(f"{p}_limit_altitude"), (int, float))
            and not isinstance(props.get(f"{p}_limit_altitude"), bool)
            and math.isfinite(props[f"{p}_limit_altitude"])
            and props.get(f"{p}_limit_unit") in {"m", "ft"}
            and props.get(f"{p}_limit_alt_ref") == "MSL"
        }
        bounds = [
            comparison["minimum_m"] + scenario["agl_m"],
            comparison["maximum_m"] + scenario["agl_m"],
        ]
        result["aircraft_comparison_bounds_m"] = bounds
        reason += f" Aircraft comparison interval {bounds[0]:.3f}–{bounds[1]:.3f} m MSL; zone limits {result['zone_msl_bounds_m']}."
        if assumption:
            reason += " NHN + AGL engineering approximation."
    if state == "outside_vertical":
        return {
            **result,
            "state": "not_applicable",
            "vertical_relation": "outside",
            "reason": reason,
        }
    limits = result.get("zone_msl_bounds_m", {})
    if (
        limits
        and state == "unresolved"
        and all(props.get(f"{p}_limit_altitude") is None or p in limits for p in ("lower", "upper"))
        and (len(limits) < 2 or limits["lower"] <= limits["upper"])
    ):
        result["vertical_relation"] = "overlap" if len(limits) == 2 else "potential_overlap"
    # An imported prohibition must be reviewed and have compatible vertical overlap.
    # A stale or generic allowance must not downgrade this independent prohibition.
    if record.get("reviewed_notice") and record.get("notice_state") == "prohibited":
        limits = [props.get(f"{p}_limit_altitude") for p in ("lower", "upper")]
        compatible = any(v is not None for v in limits) and all(
            v is None
            or (
                isinstance(v, (int, float))
                and not isinstance(v, bool)
                and math.isfinite(v)
                and props.get(f"{p}_limit_unit") in {"m", "ft"}
                and (
                    props.get(f"{p}_limit_alt_ref") == "AGL"
                    or props.get(f"{p}_limit_alt_ref") == "MSL"
                    and comparison.get("status") == "known"
                    and comparison.get("vertical_datum") == "MSL"
                )
            )
            for p, v in zip(("lower", "upper"), limits)
        )
        references = {
            props.get(f"{p}_limit_alt_ref")
            for p, value in zip(("lower", "upper"), limits)
            if value is not None
        }
        compatible = compatible and len(references) == 1
        if all(v is not None for v in limits):
            values = (
                [
                    v * (0.3048 if props.get(f"{p}_limit_unit") == "ft" else 1)
                    for p, v in zip(("lower", "upper"), limits)
                ]
                if compatible
                else []
            )
            compatible = compatible and values[0] <= values[1]
        if (
            compatible
            and "valid_from" in props
            and "valid_until" in props
            and not props.get("schedule")
        ):
            return {
                **result,
                "state": "prohibited",
                "reason": "Reviewed active prohibition overlaps the compatible comparison interval.",
                "evidence": record["evidence"],
            }
    assessment = scenario.get("zone_assessments", {}).get(source)
    if assessment is not None:
        if assessment.get("source_signature") != record["source_signature"]:
            return {**result, "reason": "Source changed; assessment requires renewed review."}
        if assessment.get("state") == "conditional_allowed" and assessment.get(
            "phase", "transit"
        ) not in {"all", "transit"}:
            return {
                **result,
                "reason": "Launch/landing permission cannot grant transit permission.",
            }
        state, reason = evidence_check(record, scenario)
        if state != "unresolved":
            return {
                **result,
                "state": "prohibited" if state == "blocked" else state,
                "reason": reason,
                "evidence": assessment["evidence"],
            }
        return {**result, "reason": reason}
    return {**result, "reason": reason}


def counts(decisions):
    counter = Counter(item["state"] for item in decisions)
    return {
        name: counter[name]
        for name in ("prohibited", "conditional_allowed", "not_applicable", "unresolved")
    }


def coverage_report(manifest, notices, scenario):
    dipul = manifest["sources"]["dipul"]
    responses = dipul["responses"]
    temporary = [
        r for r in responses if r["type_name"] == "dipul:temporaere_betriebseinschraenkungen"
    ]
    dates = [
        item["retrieved_at_utc"]
        for item in manifest.get("files", [])
        if "dipul-" in item.get("path", "") and item.get("retrieved_at_utc")
    ]
    oldest = min(dates, key=instant) if dates else None
    age = (
        (instant(scenario["mission_start"]) - instant(oldest)).total_seconds() / 86400
        if oldest
        else None
    )
    return {
        "status": "unverified",
        "scope": manifest["config"]["bounds"],
        "mission_start": scenario["mission_start"],
        "mission_end": scenario["mission_end"],
        "temporary_layer_acquired": bool(temporary),
        "temporary_features": sum(r.get("feature_count", 0) for r in temporary),
        "reviewed_notices": len(notices),
        "notam_completeness": "unverified",
        "oldest_dipul_retrieval": oldest,
        "age_at_mission_days": age,
        "source_freshness": "unknown"
        if age is None
        else "stale"
        if age > scenario.get("max_source_age_days", 7)
        else "future_snapshot"
        if age < 0
        else "within_configured_age",
        "reason": "A static snapshot and reviewed notices do not prove complete temporary/NOTAM coverage.",
    }
