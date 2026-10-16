"""Independent, immutable OFMX display snapshots; no routing or legal decisions."""

import hashlib
import json
import math
import re
import shutil
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from shapely.geometry import Point, Polygon, box, mapping
from shapely.validation import explain_validity

from uas_planner.core.area import StudyRegion
from uas_planner.core.experiment import checksum

ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}\Z")
MAX_XML = 60 * 1024 * 1024
FILES = (
    "source.zip",
    "publication.xml",
    "region.json",
    "airspaces.geojson",
    "aerodromes.geojson",
    "details.json",
    "diagnostics.json",
)
SNAPSHOT = "ofm.json"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")


def xml(data):
    if len(data) > MAX_XML or b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("Unsupported XML size or entity declaration.")
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError("Malformed OFM XML.") from exc


def default_region():
    return read(Path(__file__).with_name("ofm_region.json"))


def validate_region(region):
    area = StudyRegion(**region["bounds"])
    if not ID.fullmatch(region["region_id"]):
        raise ValueError("Invalid OFM region ID.")
    sites = region["locations"]
    if not isinstance(sites, list) or not 1 <= len(sites) <= 100:
        raise ValueError("Supply 1-100 reference sites.")
    names = set()
    for site in sites:
        ident = site["id"]
        if not ID.fullmatch(ident) or ident in names:
            raise ValueError("Invalid or duplicate reference-site ID.")
        names.add(ident)
        point = Point(float(site["longitude"]), float(site["latitude"]))
        if not box(*area.as_tuple()).covers(point):
            raise ValueError("Reference site outside the declared OFM region.")
    return area


def publication(data, cycle):
    if not re.fullmatch(r"\d{4}", cycle):
        raise ValueError("AIRAC must be a four-digit cycle.")
    tree = xml(data)
    validity = next((e.attrib for e in tree.iter("cycle") if e.get("id") == cycle), None)
    product = next((e for e in tree.iter("product") if e.get("type") == "OFMX"), None)
    download = product.find("download") if product is not None else None
    if validity is None or download is None or download.get("inProgress", "").lower() != "false":
        raise ValueError("Publication lacks a complete OFMX product and requested cycle.")
    dates = [
        datetime.fromisoformat(validity[k].replace("Z", "+00:00"))
        for k in ("startValidity", "endValidity")
    ]
    if any(d.tzinfo is None for d in dates) or dates[0] >= dates[1]:
        raise ValueError("Invalid AIRAC validity interval.")
    return {"cycle": cycle, "validity": dict(validity), "product": dict(download.attrib)}


def numeric(value):
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None
    return number if math.isfinite(number) else None


def vertical(element, suffix):
    value = element.findtext(f"valDistVer{suffix}")
    unit = element.findtext(f"uomDistVer{suffix}")
    ref = element.findtext(f"codeDistVer{suffix}")
    number = numeric(value)
    return {
        "value": value,
        "unit": unit,
        "reference": ref,
        "metres": number * (0.3048 if unit == "FT" else 1)
        if number is not None and unit in ("FT", "M")
        else None,
        "interpretation": {
            "HEI": "above ground",
            "ALT": "above MSL",
            "STD": "standard atmosphere",
        }.get(ref, "unknown"),
    }


def coordinate(value, limit):
    if not value or not re.fullmatch(r"\d+(?:\.\d+)?[NSEW]", value):
        raise ValueError("Unsupported coordinate notation.")
    direction = value[-1]
    if direction not in ("NS" if limit == 90 else "EW"):
        raise ValueError("Coordinate axis mismatch.")
    number = float(value[:-1]) * (-1 if direction in "SW" else 1)
    if not -limit <= number <= limit:
        raise ValueError("Coordinate outside WGS84 range.")
    return number


def source_id(element):
    uid = element.find(f"{element.tag}Uid")
    if uid is None or not uid.get("mid"):
        raise ValueError("OFMX feature lacks a stable mid.")
    mid = uid.get("mid")
    ident = f"{element.tag.lower()}-{mid}"
    if not ID.fullmatch(ident):
        raise ValueError("Unsupported OFMX identifier.")
    return ident, mid


def polygon_from_shape(element):
    points = []
    for part in (element.findtext("gmlPosList") or "").split():
        xyz = [float(v) for v in part.split(",")]
        if len(xyz) not in (2, 3) or not all(math.isfinite(v) for v in xyz):
            raise ValueError("Invalid shape coordinate.")
        lon, lat = xyz[:2]
        if not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise ValueError("Shape coordinate outside WGS84.")
        points.append((lon, lat))
    if len(points) < 3:
        raise ValueError("Shape requires at least three ring vertices.")
    return Polygon(points)


def import_snapshot(archive, publication_path, output, *, cycle, region=None, receipts=None):
    """Rebuild display derivatives from originals; output must never already exist."""
    archive, publication_path, output = map(Path, (archive, publication_path, output))
    region = default_region() if region is None else region
    area = validate_region(region)
    extent = box(*area.as_tuple())
    catalog = publication(publication_path.read_bytes(), cycle)
    if archive.stat().st_size > 30 * 1024 * 1024:
        raise ValueError("OFMX ZIP exceeds 30 MiB.")
    try:
        with ZipFile(archive) as bundle:
            members = bundle.infolist()
            if len(members) > 500 or len({i.filename for i in members}) != len(members):
                raise ValueError("Duplicate or excessive ZIP members.")
            if sum(i.file_size for i in members) > 250 * 1024 * 1024:
                raise ValueError("Expanded OFMX archive exceeds resource limit.")
            prefix = "ofmx_ed/isolated/"
            raw = bundle.read(prefix + "ofmx_ed.ofmx")
            tree = xml(raw)
            shape_name = prefix + "ofmx_ed_ofmShapeExtension.xml"
            shapes = xml(bundle.read(shape_name)) if shape_name in bundle.namelist() else None
            readme = next((i for i in members if i.filename == "ofmx_ed/readme.pdf"), None)
            readme_hash = hashlib.sha256(bundle.read(readme)).hexdigest() if readme else None
    except (BadZipFile, KeyError) as exc:
        raise ValueError("Archive lacks the isolated Germany OFMX product.") from exc
    if tree.tag != "OFMX-Snapshot" or tree.get("version") != "0.1":
        raise ValueError("Only inspected OFMX-Snapshot 0.1 is supported.")
    effective = datetime.fromisoformat(tree.attrib["effective"].replace("Z", "+00:00"))
    if effective.tzinfo is None:
        raise ValueError("Snapshot effective time must include its timezone.")
    inventory = dict(Counter(e.tag for e in tree))
    semantic_groups = defaultdict(list)
    for element in tree.findall("Ase"):
        semantic_groups[source_id(element)[1]].append(element)
    airspaces = {mid: group[0] for mid, group in semantic_groups.items()}
    conflicts = {
        mid
        for mid, group in semantic_groups.items()
        if len(
            {ET.canonicalize(ET.tostring(e, encoding="unicode"), strip_text=True) for e in group}
        )
        > 1
    }
    boundaries = defaultdict(list)
    for e in tree.findall("Abd"):
        uid = e.find("AbdUid/AseUid")
        if uid is not None:
            boundaries[uid.get("mid")].append(e)
    shape_map = defaultdict(list)
    if shapes is not None:
        for e in shapes.findall("Ase"):
            mid = e.find("AseUid").get("mid")
            shape_map[mid].append(e)
    # Capture direct relationships, without cloning the complete national database.
    associations = defaultdict(list)
    for e in tree:
        for uid in e.iter("AseUid"):
            if e.tag != "Ase":
                associations[uid.get("mid")].append(e)
        for uid in e.iter("AhpUid"):
            if e.tag != "Ahp":
                associations[uid.get("mid")].append(e)
    details, diagnostics = {}, []
    layers = {
        name: {"type": "FeatureCollection", "features": []} for name in ("airspaces", "aerodromes")
    }

    def add(element, layer, geometry, quality, reason=None, candidate=True):
        ident, mid = source_id(element)
        uid = element.find(f"{element.tag}Uid")
        properties = {
            "source": "OpenFlightMaps",
            "source_id": mid,
            "name": element.findtext("txtName") or uid.findtext("codeId") or mid,
            "code_id": uid.findtext("codeId"),
            "type": uid.findtext("codeType") or element.findtext("codeType"),
            "class": element.findtext("codeClass"),
            "geometry_quality": quality,
            "snapshot_effective": tree.get("effective"),
            "cycle": cycle,
        }
        if element.tag == "Ase":
            properties.update(lower=vertical(element, "Lower"), upper=vertical(element, "Upper"))
        else:
            properties["elevation"] = {
                "value": element.findtext("valElev"),
                "unit": element.findtext("uomDistVer"),
            }
        feature = {"type": "Feature", "id": ident, "geometry": geometry, "properties": properties}
        if candidate:
            layers[layer]["features"].append(feature)
        related = associations[mid]
        # Services and their frequencies are linked through the Sae/Ser identifiers.
        service_ids = {u.get("mid") for e in related for u in e.iter("SerUid")}
        related += [
            e
            for e in tree.findall("Fqy")
            if any(u.get("mid") in service_ids for u in e.iter("SerUid"))
        ]
        details[ident] = {
            "feature": feature,
            "selected_region_candidate": candidate,
            "attributes_xml": ET.tostring(element, encoding="unicode"),
            "semantic_variants_xml": [
                ET.tostring(e, encoding="unicode") for e in semantic_groups.get(mid, [element])
            ],
            "relationships": [
                {"kind": e.tag, "xml": ET.tostring(e, encoding="unicode")} for e in related
            ],
            "remarks": element.findtext("txtRmk"),
            "schedule_xml": [ET.tostring(e, encoding="unicode") for e in element.findall("Att")],
            "geometry_note": reason or "Display geometry only; no legal applicability.",
            "legal_state": "not_evaluated",
        }
        if reason:
            diagnostics.append(
                {
                    "feature_id": ident,
                    "name": properties["name"],
                    "reason": reason,
                    "quality": quality,
                    "region_relation": "candidate" if candidate else "unknown",
                }
            )

    for mid, element in airspaces.items():
        polygon, quality, reason = None, "missing", None
        try:
            if mid in conflicts:
                raise ValueError(
                    "Conflicting duplicate semantic records; no variant selected for display."
                )
            if mid in shape_map:
                if len(shape_map[mid]) != 1:
                    raise ValueError(
                        "Multiple shape-extension parts require explicit geometry review."
                    )
                polygon = polygon_from_shape(shape_map[mid][0])
                quality = "provider_shape_extension"
            elif mid in boundaries:
                if len(boundaries[mid]) != 1:
                    raise ValueError("Multiple raw boundaries require explicit geometry review.")
                boundary = boundaries[mid][0]
                vertices = boundary.findall("Avx")
                if not vertices or any(v.findtext("codeType") != "GRC" for v in vertices):
                    raise ValueError(
                        "Unsupported raw arc/frontier geometry; shape extension absent."
                    )
                polygon = Polygon(
                    [
                        (
                            coordinate(v.findtext("geoLong"), 180),
                            coordinate(v.findtext("geoLat"), 90),
                        )
                        for v in vertices
                    ]
                )
                quality = "raw_vertex_display_approximation"
            else:
                raise ValueError("Missing direct boundary/shape; derived geometry not resolved.")
            if polygon.is_empty:
                raise ValueError("Empty airspace shape.")
            if not polygon.is_valid:
                reason, quality = explain_validity(polygon), "invalid"
            candidate = box(*polygon.bounds).intersects(extent)
            if not candidate:
                continue
            if reason:
                add(element, "airspaces", None, quality, reason)
            elif polygon.intersects(extent):
                add(element, "airspaces", mapping(polygon), quality)
        except (ValueError, TypeError, IndexError) as exc:
            # Without a usable extent, report uncertainty rather than certify absence.
            add(element, "airspaces", None, "unsupported", str(exc), candidate=False)
    for element in tree.findall("Ahp"):
        try:
            point = Point(
                coordinate(element.findtext("geoLong"), 180),
                coordinate(element.findtext("geoLat"), 90),
            )
            if element.findtext("codeDatum") != "WGE":
                raise ValueError("Aerodrome coordinate datum is unsupported.")
            if extent.covers(point):
                add(element, "aerodromes", mapping(point), "source_point")
        except ValueError as exc:
            add(element, "aerodromes", None, "unsupported", str(exc), candidate=False)
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(archive, output / "source.zip")
    shutil.copyfile(publication_path, output / "publication.xml")
    write(output / "region.json", region)
    for name, collection in layers.items():
        write(output / f"{name}.geojson", collection)
    write(output / "details.json", details)
    write(output / "diagnostics.json", diagnostics)
    manifest = {
        "schema_version": 1,
        "kind": "ofm-display-snapshot",
        "synthetic": bool(region.get("synthetic", False)),
        "source": "OpenFlightMaps",
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "publication": catalog,
        "source_xml": dict(tree.attrib),
        "region": region,
        "inventory": inventory,
        "duplicate_semantic_groups": sum(len(g) > 1 for g in semantic_groups.values()),
        "conflicting_semantic_groups": len(conflicts),
        "layers": {
            k: {
                "count": len(v["features"]),
                "drawable": sum(f["geometry"] is not None for f in v["features"]),
            }
            for k, v in layers.items()
        },
        "diagnostic_count": len(diagnostics),
        "coverage": "qualified; unsupported/invalid geometry remains unresolved",
        "geometry_policy": "Complete source extents; provider display derivatives are not certified raw-geometry reconstruction.",
        "license": {
            "name": "OFMA General Users/Data User License",
            "status": "full_text_not_archived; public redistribution not reviewed",
            "readme_sha256": readme_hash,
            "attribution": "OpenFlightMaps association - https://openflightmaps.org",
        },
        "receipts": receipts or {"method": "offline import of supplied originals"},
        "files": {name: checksum(output / name) for name in FILES},
    }
    write(output / SNAPSHOT, manifest)  # Completion marker is always written last.
    return manifest


def load_snapshot(directory):
    directory = Path(directory).resolve()
    marker = directory / SNAPSHOT
    if marker.is_symlink() or marker.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Invalid OFM manifest.")
    manifest = read(marker)
    if manifest.get("kind") != "ofm-display-snapshot" or manifest.get("schema_version") != 1:
        raise ValueError("Unsupported OFM snapshot.")
    if set(manifest["files"]) != set(FILES):
        raise ValueError("OFM file inventory changed.")
    for name in FILES:
        path = directory / name
        if path.is_symlink() or not path.resolve().is_relative_to(directory):
            raise ValueError("OFM file escapes snapshot directory.")
        if checksum(path) != manifest["files"][name]:
            raise ValueError(f"OFM checksum mismatch: {name}")
    if read(directory / "region.json") != manifest["region"]:
        raise ValueError("OFM region metadata mismatch.")
    validate_region(manifest["region"])
    return manifest
