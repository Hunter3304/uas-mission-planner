"""Explicit artificial OFMX files for offline parser/API/browser acceptance."""

import xml.etree.ElementTree as ET
from copy import deepcopy
from zipfile import ZIP_DEFLATED, ZipFile

from uas_planner.core.ofm import default_region, import_snapshot


def fixture_files(root):
    root.mkdir(parents=True, exist_ok=True)
    region = deepcopy(default_region())
    region["synthetic"] = True
    tree = ET.Element(
        "OFMX-Snapshot",
        version="0.1",
        effective="2026-10-12T12:00:00Z",
        created="2026-10-12T12:00:00Z",
        origin="explicit synthetic test fixture",
    )
    shapes = ET.Element("OFM-AixmPlugin")
    for ident, kind, name, ring in (
        (
            "ctr",
            "CTR",
            "Synthetic CTR <img src=x onerror=window.ofmXss=1>",
            "9.70,52.34,0 9.9,52.34,0 9.9,52.43,0 9.7,52.43,0",
        ),
        (
            "tma",
            "TMA",
            "Synthetic upper TMA",
            "9.72,52.35,0 9.92,52.35,0 9.92,52.42,0 9.72,52.42,0",
        ),
        ("bad", "R", "Synthetic invalid ring", "9.7,52.34,0 9.9,52.43,0 9.9,52.34,0 9.7,52.43,0"),
        ("missing", "R", "Synthetic missing boundary", None),
    ):
        element = ET.SubElement(tree, "Ase")
        uid = ET.SubElement(element, "AseUid", mid=ident, region="ED")
        ET.SubElement(uid, "codeType").text = kind
        ET.SubElement(uid, "codeId").text = ident
        ET.SubElement(element, "txtName").text = name
        ET.SubElement(element, "codeClass").text = "D"
        for suffix, value in (
            ("Lower", "65" if kind == "TMA" else "0"),
            ("Upper", "100" if kind == "TMA" else "2500"),
        ):
            ET.SubElement(element, "codeDistVer" + suffix).text = (
                "STD" if kind == "TMA" else "HEI" if suffix == "Lower" else "ALT"
            )
            ET.SubElement(element, "valDistVer" + suffix).text = value
            ET.SubElement(element, "uomDistVer" + suffix).text = "FL" if kind == "TMA" else "FT"
        ET.SubElement(
            element, "txtRmk"
        ).text = "Unreviewed test text </script><script>window.ofmXss=2</script>"
        att = ET.SubElement(element, "Att")
        ET.SubElement(att, "codeWorkHr").text = "TIMSH"
        if ring:
            shape = ET.SubElement(shapes, "Ase")
            ET.SubElement(shape, "AseUid", mid=ident)
            ET.SubElement(shape, "gmlPosList").text = ring
    for ident, lon in (("inside", "9.8"), ("outside", "10.5")):
        airport = ET.SubElement(tree, "Ahp")
        uid = ET.SubElement(airport, "AhpUid", mid=ident, region="ED")
        ET.SubElement(uid, "codeId").text = ident
        for key, value in {
            "txtName": "Synthetic aerodrome " + ident,
            "codeType": "AD",
            "geoLat": "52.39N",
            "geoLong": lon + "E",
            "codeDatum": "WGE",
            "valElev": "180",
            "uomDistVer": "FT",
        }.items():
            ET.SubElement(airport, key).text = value
    rwy = ET.SubElement(tree, "Rwy")
    uid = ET.SubElement(rwy, "RwyUid", mid="runway")
    ET.SubElement(uid, "AhpUid", mid="inside")
    ET.SubElement(rwy, "valLen").text = "1000"
    sae = ET.SubElement(tree, "Sae")
    uid = ET.SubElement(sae, "SaeUid", mid="service-link")
    ET.SubElement(uid, "AseUid", mid="ctr")
    ET.SubElement(uid, "SerUid", mid="service")
    fqy = ET.SubElement(tree, "Fqy")
    uid = ET.SubElement(fqy, "FqyUid", mid="frequency")
    ET.SubElement(uid, "SerUid", mid="service")
    ET.SubElement(uid, "valFreqTrans").text = "123.450"
    ET.SubElement(fqy, "uomFreq").text = "MHZ"
    archive = root / "source.zip"
    with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
        bundle.writestr("ofmx_ed/isolated/ofmx_ed.ofmx", ET.tostring(tree))
        bundle.writestr("ofmx_ed/isolated/ofmx_ed_ofmShapeExtension.xml", ET.tostring(shapes))
    publication = root / "publication.xml"
    publication.write_text(
        """<publications><cycle id="2610" startValidity="2026-10-01T00:00:00Z"
    endValidity="2026-10-29T00:00:00Z"/><product type="OFMX"><download inProgress="False"
    URL="https://snapshots.openflightmaps.org/live/2610/ofmx/ed/latest/ofmx_ed.zip"/>
    </product></publications>""",
        encoding="utf-8",
    )
    return archive, publication, region


def create_ofm_fixture(root):
    archive, index, region = fixture_files(root / ".ofm-originals")
    output = root / ".ofm" / "synthetic-ofm"
    import_snapshot(archive, index, output, cycle="2610", region=region)
    return output
