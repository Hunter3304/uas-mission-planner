"""OFMX semantics, immutable originals, malformed inputs and independent API checks."""

import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient
from ofm_fixture import create_ofm_fixture, fixture_files

from uas_planner.acquisition.ofm import official_url, rebuild_ofm
from uas_planner.api.app import create_app
from uas_planner.core.ofm import (
    default_region,
    import_snapshot,
    load_snapshot,
    publication,
    read,
    xml,
)
from uas_planner.core.ofm_preview import export_preview


def test_default_region_matches_the_saved_eight_site_study():
    canonical = read(
        Path(__file__).parents[2] / "doc/experiments/iteration-008/hannover-study.json"
    )
    region = default_region()
    assert region["bounds"] == canonical["bounds"]
    assert region["detour_margin_m"] == 5000
    assert len(region["locations"]) == 8
    assert {p["id"] for p in region["locations"]} == {p["id"] for p in canonical["locations"]}


def test_region_selection_retains_height_references_and_unresolved_geometry(tmp_path):
    output = create_ofm_fixture(tmp_path)
    manifest = load_snapshot(output)
    assert manifest["synthetic"]
    assert manifest["layers"]["airspaces"] == {"count": 3, "drawable": 2}
    assert manifest["layers"]["aerodromes"]["count"] == 1
    air = {f["id"]: f for f in read(output / "airspaces.geojson")["features"]}
    assert air["ase-ctr"]["properties"]["upper"]["metres"] == 762
    assert air["ase-ctr"]["properties"]["upper"]["reference"] == "ALT"
    assert air["ase-tma"]["properties"]["lower"]["metres"] is None
    assert air["ase-tma"]["properties"]["lower"]["unit"] == "FL"
    assert air["ase-bad"]["geometry"] is None
    diagnostics = read(output / "diagnostics.json")
    assert {d["region_relation"] for d in diagnostics} == {"candidate", "unknown"}
    details = read(output / "details.json")
    assert "TIMSH" in details["ase-ctr"]["schedule_xml"][0]
    assert any("123.450" in r["xml"] for r in details["ase-ctr"]["relationships"])
    assert any(r["kind"] == "Rwy" for r in details["ahp-inside"]["relationships"])
    assert all(d["legal_state"] == "not_evaluated" for d in details.values())


def test_offline_rebuild_preserves_derivatives_and_refuses_overwrite(tmp_path, monkeypatch):
    output = create_ofm_fixture(tmp_path)
    before = load_snapshot(output)
    monkeypatch.setattr("requests.sessions.Session.request", lambda *a, **k: pytest.fail("Network"))
    rebuilt = rebuild_ofm(output, tmp_path / "rebuilt")
    assert rebuilt["files"] == before["files"]
    with pytest.raises(FileExistsError):
        rebuild_ofm(output, output)
    (output / "airspaces.geojson").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum"):
        load_snapshot(output)
    with pytest.raises(ValueError):
        rebuild_ofm(output, tmp_path / "corrupted-rebuild")


@pytest.mark.parametrize("payload", [b"<bad>", b'<!DOCTYPE x [<!ENTITY y "boom">]><x>&y;</x>'])
def test_rejects_malformed_or_entity_xml(payload):
    with pytest.raises(ValueError):
        xml(payload)


def test_conflicting_duplicate_semantics_are_quarantined(tmp_path):
    archive, index, region = fixture_files(tmp_path / "inputs")
    with ZipFile(archive) as bundle:
        files = {name: bundle.read(name) for name in bundle.namelist()}
    name = "ofmx_ed/isolated/ofmx_ed.ofmx"
    tree = ET.fromstring(files[name])
    other = deepcopy(tree.find("Ase"))
    other.find("valDistVerUpper").text = "9999"
    tree.append(other)
    files[name] = ET.tostring(tree)
    with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
        for name, data in files.items():
            bundle.writestr(name, data)
    result = import_snapshot(archive, index, tmp_path / "result", cycle="2610", region=region)
    assert result["conflicting_semantic_groups"] == 1
    assert "ase-ctr" not in {
        f["id"] for f in read(tmp_path / "result/airspaces.geojson")["features"]
    }
    assert len(read(tmp_path / "result/details.json")["ase-ctr"]["semantic_variants_xml"]) == 2


def test_publication_cycle_and_url_validation(tmp_path):
    _, index, _ = fixture_files(tmp_path)
    with pytest.raises(ValueError):
        publication(index.read_bytes(), "2609")
    for url in (
        "http://snapshots.openflightmaps.org/a",
        "https://localhost/a",
        "https://user:secret@snapshots.openflightmaps.org/a",
    ):
        with pytest.raises(ValueError):
            official_url(url)


def test_api_independence_exports_and_corruption_failure(tmp_path):
    output = create_ofm_fixture(tmp_path)
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/api/datasets").json() == {"datasets": []}
        assert client.get("/api/ofm/snapshots").json()["snapshots"][0]["verified"]
        base = "/api/ofm/snapshots/synthetic-ofm"
        assert client.get(base).json()["region"] == read(output / "region.json")
        layer = client.get(base + "/features").json()
        assert len(layer["features"]) == 3 and layer["provenance"]["source_sha256"]
        assert client.get(base + "/features?layer=bad").status_code == 422
        assert client.get(base + "/features/missing").status_code == 404
        assert client.get(base + "/features/ase-missing").json()["legal_state"] == "not_evaluated"
        assert client.get(base + "/diagnostics").json()["diagnostics"]
        assert client.get("/ofm").status_code == 200
        (output / "source.zip").write_bytes(b"changed")
        assert client.get(base + "/features").status_code == 422
        assert not client.get("/api/ofm/snapshots").json()["snapshots"][0]["verified"]


def test_standalone_export_escapes_source_text_and_does_not_overwrite(tmp_path):
    output = create_ofm_fixture(tmp_path)
    preview = tmp_path / "preview.html"
    export_preview(output, preview)
    text = preview.read_text(encoding="utf-8")
    assert "/*OFM_EMBEDDED*/null" not in text
    assert "</script><script>window.ofmXss" not in text
    assert "\\u003c/script>" in text
    with pytest.raises(FileExistsError):
        export_preview(output, preview)


def test_manifest_file_inventory_cannot_escape_snapshot(tmp_path):
    output = create_ofm_fixture(tmp_path)
    marker = output / "ofm.json"
    manifest = read(marker)
    manifest["files"]["../escape"] = "x"
    marker.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="inventory"):
        load_snapshot(output)


def test_download_limit_and_redirect_host_are_enforced(tmp_path, monkeypatch):
    from uas_planner.acquisition.ofm import download

    class Response:
        is_redirect = False
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self):
            pass

        def iter_content(self, size):
            yield b"12345"

    monkeypatch.setattr("requests.get", lambda *a, **k: Response())
    with pytest.raises(ValueError, match="limit"):
        download("https://snapshots.openflightmaps.org/a", tmp_path / "bounded", 4)
    Response.is_redirect = True
    Response.headers = {"Location": "http://localhost/private"}
    with pytest.raises(ValueError, match="official"):
        download("https://snapshots.openflightmaps.org/a", tmp_path / "redirect", 100)


def test_empty_aerodrome_layer_is_valid_without_region_expansion(tmp_path):
    archive, index, region = fixture_files(tmp_path / "originals")
    with ZipFile(archive) as bundle:
        payloads = {name: bundle.read(name) for name in bundle.namelist()}
    name = "ofmx_ed/isolated/ofmx_ed.ofmx"
    tree = ET.fromstring(payloads[name])
    for element in tree.findall("Ahp"):
        tree.remove(element)
    payloads[name] = ET.tostring(tree)
    with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
        for name, data in payloads.items():
            bundle.writestr(name, data)
    result = import_snapshot(archive, index, tmp_path / "result", cycle="2610", region=region)
    assert result["region"] == region
    assert result["layers"]["aerodromes"] == {"count": 0, "drawable": 0}


def test_unsupported_schema_cannot_create_a_completed_snapshot(tmp_path):
    archive, index, region = fixture_files(tmp_path / "originals")
    with ZipFile(archive) as bundle:
        payloads = {name: bundle.read(name) for name in bundle.namelist()}
    name = "ofmx_ed/isolated/ofmx_ed.ofmx"
    payloads[name] = payloads[name].replace(b'version="0.1"', b'version="0.2"')
    with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
        for name, data in payloads.items():
            bundle.writestr(name, data)
    target = tmp_path / "result"
    with pytest.raises(ValueError, match="0.1"):
        import_snapshot(archive, index, target, cycle="2610", region=region)
    assert not (target / "ofm.json").exists()
