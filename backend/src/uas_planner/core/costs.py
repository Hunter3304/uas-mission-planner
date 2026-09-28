"""Explainable ordinal tag costs; independent of storage, HTTP and the frontend."""

import json
from copy import deepcopy
from importlib.resources import files

RULES = json.loads(
    files("uas_planner.core").joinpath("cost_rules.json").read_text(encoding="utf-8")
)
LABELS = ["Very low", "Low", "Medium", "High", "Very high"]
POLICY = "Project policy v1"


def _tokens(value):
    if isinstance(value, list):
        return [token for item in value for token in _tokens(item)] or [None]
    if isinstance(value, str):
        return [part.strip().lower() for part in value.split(";")]
    return [None]


def classify_tag(key, value):
    """Retain original values; reduce multiple values by max, never by addition."""
    rule = RULES["layers"].get(key)
    result = {"key": key, "value": value, "cost": None, "obstruction": False, "has_default": False}
    if rule is None:
        return {
            **result,
            "status": "unscored",
            "matches": [],
            "reason": "No cost rule for this tag. Preserved for inspection; not scored.",
            "source": POLICY,
        }
    matches = []
    for token in dict.fromkeys(_tokens(value)):
        canonical = rule.get("aliases", {}).get(token, token)
        cost = next(
            (int(level) for level, values in rule["levels"].items() if canonical in values), None
        )
        obstruction = canonical in rule["obstructions"]
        source = f"Ramke (2020), {rule['table']}"
        status = "matched"
        reason = f"The paper assigns {key}={canonical} to cost {cost}."
        if canonical in rule.get("supplements", {}):
            extra = rule["supplements"][canonical]
            cost, source, reason = extra["cost"], extra["source"], extra["reason"]
        elif canonical in rule.get("excluded", []):
            status, reason = "excluded", "Explicitly excluded from this cost layer."
        elif cost is None and obstruction:
            status, reason = (
                "obstruction_only",
                "Paper obstruction entry; no numeric cost assigned.",
            )
        elif cost is None:
            cost, status, source = RULES["default_cost"], "default", POLICY
            reason = (
                "Unrecognized or malformed value: provisional cost 2, not a known classification."
            )
        correction = rule.get("corrections", {}).get(canonical)
        if correction:
            reason += f" {correction} ({POLICY})"
        if obstruction:
            reason += (
                " Historical paper obstruction flag; current flight restrictions are not assessed."
            )
        matches.append(
            {
                "input": token,
                "normalized": canonical,
                "cost": cost,
                "status": status,
                "obstruction": obstruction,
                "source": source,
                "reason": reason,
            }
        )
    costs = [match["cost"] for match in matches if match["cost"] is not None]
    result.update(
        cost=max(costs) if costs else None,
        obstruction=any(match["obstruction"] for match in matches),
        has_default=any(match["status"] == "default" for match in matches),
        matches=matches,
        source="; ".join(dict.fromkeys(match["source"] for match in matches)),
        reason="Each tag layer stays separate; costs are not added across tags.",
    )
    result["status"] = (
        "default"
        if result["has_default"]
        else "matched"
        if costs
        else "obstruction_only"
        if result["obstruction"]
        else "excluded"
    )
    if len(matches) > 1:
        result["reason"] += f" Multiple values: maximum numeric cost ({POLICY}), not a paper rule."
    return result


def analyze_feature(properties, layer="building", *, legacy_flags=False):
    """Analyze a present tag layer without inferring tags from nearby features."""
    value = properties.get(layer)
    if value is None or value == [] or all(token in ("", "no") for token in _tokens(value)):
        return None
    tags = [
        classify_tag(key, value)
        for key, value in sorted(properties.items(), key=lambda pair: (pair[0] != layer, pair[0]))
        if value is not None and key not in ("element_type", "osm_id")
    ]
    primary = next(tag for tag in tags if tag["key"] == layer)
    cost = primary["cost"]
    return {
        "rule_version": RULES["version"],
        "cost": cost,
        "label": LABELS[cost] if cost is not None else "No numeric cost",
        "has_default": primary["has_default"],
        "status": primary["status"],
        "obstruction": any(tag["obstruction"] for tag in tags)
        if legacy_flags
        else primary["obstruction"],
        "tags": tags,
    }


def analyze_building(properties):
    return analyze_feature(properties, legacy_flags=True)


def analyze_collection(collection, layer=None):
    """Return a derived copy with foreign GeoJSON members, preserving source tags."""
    output = deepcopy(collection)
    summary = {
        "buildings": 0,
        "levels": {str(level): 0 for level in range(5)},
        "defaulted": 0,
        "obstruction_flagged": 0,
        "without_numeric_cost": 0,
        "unmatched_tags": [],
    }
    unmatched = {}
    for feature in output["features"]:
        analysis = (
            analyze_feature(feature["properties"], layer)
            if layer
            else analyze_building(feature["properties"])
        )
        feature["cost_analysis"] = analysis
        if analysis is None:
            continue
        summary["buildings"] += 1
        if analysis["cost"] is not None:
            summary["levels"][str(analysis["cost"])] += 1
        else:
            summary["without_numeric_cost"] += 1
        summary["defaulted"] += int(analysis["has_default"])
        summary["obstruction_flagged"] += int(analysis["obstruction"])
        for tag in analysis["tags"]:
            if tag["has_default"] and (layer is None or tag["key"] == layer):
                key = (tag["key"], json.dumps(tag["value"], sort_keys=True, ensure_ascii=False))
                unmatched[key] = unmatched.get(key, 0) + 1
    summary["unmatched_tags"] = [
        {"key": key, "value": json.loads(value), "count": count}
        for (key, value), count in sorted(unmatched.items())
    ]
    output["cost_summary"] = summary
    output["cost_policy"] = {
        "version": RULES["version"],
        "source": RULES["source"],
        "scope": "Explicit building objects; other tags scored independently when a rule exists.",
        "aggregation": "Map color uses building cost only. Multiple values use maximum numeric cost.",
        "unknown": "Unknown classified values default to 2. Uncovered map areas are unassessed.",
        "limits": "Ordinal research costs, not probabilities. Paper flags are not current legal restrictions.",
    }
    return output


def analyze_all_layers(collection):
    """Independent layer results; no cross-layer cost or obstruction aggregation."""
    results = {key: analyze_collection(collection, key) for key in RULES["layers"]}
    output = results["building"]
    output["layer_summaries"] = {}
    for key, result in results.items():
        summary = result["cost_summary"].copy()
        summary["features"] = summary.pop("buildings")
        output["layer_summaries"][key] = summary
    for index, feature in enumerate(output["features"]):
        feature["layer_analyses"] = {
            key: result["features"][index]["cost_analysis"] for key, result in results.items()
        }
    output["cost_policy"]["scope"] = "Each supported tag layer is assessed on all saved objects."
    output["cost_policy"]["aggregation"] = (
        "Selected-layer costs and flags only; no cross-layer fusion. Multiple values use maximum numeric cost."
    )
    return output
