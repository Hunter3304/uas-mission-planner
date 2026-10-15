"""Reproduce the retained DIPUL audit without exporting original geometries."""

import argparse
import json
from collections import Counter
from pathlib import Path

from uas_planner.core.experiment import checksum, read_json, safe_file
from uas_planner.core.restrictions import RULES_VERSION, review_requirement
from uas_planner.core.risk import signature

PRIMARY_IDS = {
    "dipul:wohngrundstuecke/wohngrundstuecke.1398": "origin",
    "dipul:kontrollzonen/kontrollzonen.57": "origin and destination",
    "dipul:krankenhaeuser/krankenhaeuser.2275": "destination",
    "dipul:flugplaetze/flugplaetze.106": "destination",
}


def audit(directory):
    manifest = read_json(directory / "study.json")
    receipts = {item["path"]: item for item in manifest["files"]}
    verified = set()

    def verify(relative):
        if relative not in receipts:
            raise ValueError(f"No integrity receipt for {relative}")
        if checksum(safe_file(directory, relative)) != receipts[relative]["sha256"]:
            raise ValueError(f"Source checksum mismatch for {relative}")
        verified.add(relative)

    verify("raw/dipul-capabilities.xml")
    layers, primary, fields = [], [], Counter()
    for response in manifest["sources"]["dipul"]["responses"]:
        layer = response["type_name"]
        verify(f"raw/dipul-{layer.split(':', 1)[1]}-schema.xml")
        features = []
        for page in response["pages"]:
            verify(page)
            features.extend(read_json(safe_file(directory, page))["features"])
        if len(features) != response["feature_count"]:
            raise ValueError(f"Layer count mismatch for {layer}")
        layer_fields = Counter()
        for feature in features:
            properties = feature["properties"]
            layer_fields.update(
                k
                for k, value in properties.items()
                if value is not None and value != ""
            )
            source = f"{layer}/{feature['id']}"
            if source in PRIMARY_IDS:
                primary.append(
                    {
                        "source": source,
                        "endpoint_scope": PRIMARY_IDS[source],
                        "source_signature": signature(feature),
                        "legal_reference": properties.get("legal_ref"),
                        "vertical_limits": {
                            k: v
                            for k, v in properties.items()
                            if k.startswith(("lower_limit_", "upper_limit_"))
                        },
                        "required_review": review_requirement(layer),
                        "decision_without_evidence": "unresolved",
                    }
                )
        fields.update(layer_fields)
        layers.append(
            {
                "layer": layer,
                "feature_count": len(features),
                "required_review": review_requirement(layer),
                "nonempty_fields": dict(layer_fields),
            }
        )
    if {item["source"] for item in primary} != set(PRIMARY_IDS):
        raise ValueError("Primary endpoint audit features are missing.")
    return {
        "rules_version": RULES_VERSION,
        "snapshot": directory.name,
        "scope": manifest["config"]["bounds"],
        "layer_count": len(layers),
        "feature_count": sum(item["feature_count"] for item in layers),
        "verified_dipul_files": len(verified),
        "nonempty_fields": dict(fields),
        "layers": layers,
        "primary_endpoints": primary,
        "interpretation": "Zero confirmed prohibitions is a classifier result, not proof that no restrictions exist. No permissions supplied.",
    }


def markdown(result):
    rows = [
        "# Retained Hannover DIPUL source and rule audit",
        "",
        "Verified 2026-10-11 from `hannover-part1-v4`; reproducible with",
        "`doc/experiments/iteration-010/audit-dipul.py`. Original geometries are not exported.",
        "",
        f"{result['layer_count']} layers, {result['feature_count']} features and {result['verified_dipul_files']} original DIPUL files verified by checksum.",
        "",
        "## Complete layer inventory",
        "",
        "| Layer | Features | Required review topic |",
        "|---|---:|---|",
    ]
    rows += [
        f"| `{item['layer']}` | {item['feature_count']} | {item['required_review']} |"
        for item in result["layers"]
    ]
    rows += [
        "",
        "Topics describe missing applicability/evidence checks, not blanket prohibitions or automatic permission rules.",
        "",
        "## Primary endpoint audit",
        "",
        "| Source | Endpoint scope | Original reference | Original vertical limits |",
        "|---|---|---|---|",
    ]
    for item in sorted(result["primary_endpoints"], key=lambda value: value["source"]):
        limits = item["vertical_limits"]
        lower = f"{limits.get('lower_limit_altitude')} {limits.get('lower_limit_unit')} {limits.get('lower_limit_alt_ref')}"
        upper = (
            f"{limits.get('upper_limit_altitude')} {limits.get('upper_limit_unit')} {limits.get('upper_limit_alt_ref')}"
            if "upper_limit_altitude" in limits
            else "upper absent"
        )
        rows.append(
            f"| `{item['source']}` | {item['endpoint_scope']} | {item['legal_reference']} | {lower}; {upper} |"
        )
    rows += [
        "",
        "All four source features remain unresolved without supplied scenario evidence. The control-zone reference is NfL 2026-1-3960, not an inferred universal prohibition.",
        "Its MSL floor cannot be compared directly with 100 m AGL and NHN terrain; no datum conversion or permission is invented.",
        "The other three references are conditional geographic-area provisions. Evaluate the actual task/category, applicable conditions and any authorization; the source footprint alone does not prove a prohibition.",
        "",
        "## Missing evidence and functional acceptance",
        "",
        "Every feature has a legal reference and lower vertical fields; only four have upper vertical fields.",
        "The retained nonempty properties supply no explicit validity interval. Permission/condition evidence is not part of these original WFS features.",
        "A zero-count flight-restriction or temporary layer is an empty response within this snapshot scope; it is not a complete NOTAM clearance.",
        "",
        "The implemented engine supports compatible vertical nonintersection, reviewed canonical notice time nonintersection and scoped supplied assessments.",
        "Every other legal condition/exception stays unresolved until evaluated. Reviewed active prohibitions take precedence over generic, expired or wrong-scope allowances.",
        "Source signatures for the four features are retained in the local audit JSON and computed by the UI; no real permission profiles are supplied.",
        "",
        "Official references checked for this audit:",
        "",
        "- [DIPUL WFS/WMS](https://www.dipul.de/homepage/de/informationen/geografische-gebiete/wfs-wms/)",
        "- [DFS geographic areas and restrictions](https://www.dfs.de/homepage/de/drohnenflug/faq-zum-drohnenflug/)",
        "- [LuftVO §21h](https://www.gesetze-im-internet.de/luftvo_2015/__21h.html)",
        "",
        "The ordinance reference is also preserved in the original source records; publication-specific NfL conditions and complete NOTAM access remain explicit review gaps.",
        "",
    ]
    return "\n".join(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    result = audit(args.directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        with args.markdown.open("x", encoding="utf-8") as stream:
            stream.write(markdown(result))
    print(
        json.dumps(
            {
                key: result[key]
                for key in ("layer_count", "feature_count", "verified_dipul_files")
            },
            indent=2,
        )
    )
