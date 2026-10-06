"""Regional coverage, source completeness, verified resume and offline rebuilding."""

import copy
import hashlib
import json
import zipfile
from dataclasses import asdict
from pathlib import Path

import pytest
import rasterio
import requests
from experiment_fixture import create_experiment_fixture
from shapely.geometry import Point, box
from shapely.ops import unary_union

from uas_planner.acquisition import study
from uas_planner.cli import main
from uas_planner.core.area import BoundingBox
from uas_planner.core.experiment import read_json
from uas_planner.storage.dataset import load_dataset


@pytest.fixture
def source_case(tmp_path, monkeypatch):
    fixture_dir = tmp_path / "fixture"
    fixture = create_experiment_fixture(fixture_dir)
    config = {
        "schema_version": 1,
        "bounds": fixture["config"]["bounds"],
        "detour_margin_m": 0,
        "chunk_side_m": 4000,
        "agl_m": 100,
        "speed_m_s": 30,
        "ghsl_epoch": 2020,
        "ghsl_tiles": ["R3_C19"],
        "osm_url": "https://test.invalid/overpass",
        "dipul_url": "https://test.invalid/wfs",
        "dipul_layers": "all_advertised",
        "locations": [
            {
                "id": "test",
                "longitude": 10.52,
                "latitude": 52.27,
                "coordinate_status": "address_geocoded_not_landing_site",
            }
        ],
    }
    calls = []

    def download(target, request):
        calls.append(target.name)
        if target.name == "ghsl.zip":
            with zipfile.ZipFile(target, "w") as archive:
                archive.write(fixture_dir / "ghsl.tif", "publisher/native.tif")
        elif target.name == "dipul-capabilities.xml":
            target.write_text(
                '<FeatureTypeList xmlns="http://www.opengis.net/wfs/2.0">'
                "<Name>dipul:krankenhaeuser</Name></FeatureTypeList>"
            )
        elif target.suffix == ".geojson":
            target.write_text((fixture_dir / "zones.geojson").read_text())
        elif target.name.startswith("osm-"):
            target.write_text(
                json.dumps(
                    {
                        "osm3s": {"timestamp_osm_base": "2026-10-05T00:00:00Z"},
                        "elements": [
                            {
                                "type": "node",
                                "id": 123,
                                "lat": 52.27,
                                "lon": 10.52,
                                "tags": {"building": "yes"},
                            }
                        ],
                    }
                )
            )
        else:
            target.write_text("<metadata/>")
        return {"retrieved_at_utc": "2026-10-05T00:00:00Z", "bytes": target.stat().st_size}

    monkeypatch.setattr(study.PayloadStore, "_download", staticmethod(download))
    monkeypatch.setattr(study.time, "sleep", lambda _: None)
    return config, calls, download


def test_hannover_region_covers_every_site_and_chunks_partition_it():
    root = Path(__file__).resolve().parents[2]
    config = read_json(root / "doc/experiments/iteration-008/hannover-study.json")
    area = study.validate_study(config)
    assert len(config["locations"]) == 8
    assert area.area_km2 > 400
    with pytest.raises(ValueError, match="25"):
        BoundingBox(**config["bounds"])
    assert asdict(study.region_for_locations(config["locations"], 5000)) == config["bounds"]
    chunks = study.query_chunks(area)
    region = box(*area.as_tuple())
    union = unary_union([box(*chunk.as_tuple()) for chunk in chunks])
    assert union.symmetric_difference(region).area < 1e-12
    assert sum(box(*chunk.as_tuple()).area for chunk in chunks) == pytest.approx(region.area)
    assert all(chunk.area_km2 <= 25 for chunk in chunks)
    assert all(region.contains(Point(s["longitude"], s["latitude"])) for s in config["locations"])


@pytest.mark.parametrize(
    "key,value",
    [("agl_m", 99), ("agl_m", 121), ("speed_m_s", 24), ("speed_m_s", 36), ("speed_m_s", True)],
)
def test_mission_parameter_validation(source_case, key, value):
    config, _, _ = source_case
    config[key] = value
    with pytest.raises(ValueError):
        study.validate_study(config)


def test_acquire_offline_inspection_rebuild_and_original_integrity(
    source_case, tmp_path, monkeypatch
):
    config, calls, _ = source_case
    output = tmp_path / "snapshot"
    manifest = study.acquire_study(config, output, download_cache=tmp_path / "cache")
    assert manifest == study.inspect_study(output)
    assert manifest["sources"]["osm"]["feature_count"] == 1
    assert manifest["sources"]["dipul"]["responses"][0]["feature_count"] == 1
    original_values = rasterio.open(output / "population.tif").read(1, masked=True)
    assert original_values.min() == 0
    assert original_values.mask.any()
    count = len(calls)
    monkeypatch.setattr(
        study.requests, "request", lambda *a, **k: pytest.fail("Network used offline")
    )
    assert main(["study-inspect", str(output)]) == 0
    # Derivatives may be lost; preserved originals still suffice to rebuild.
    (output / "population.tif").unlink()
    rebuilt = study.rebuild_study(output, tmp_path / "rebuilt")
    assert rebuilt["sources"]["osm"] == manifest["sources"]["osm"]
    frame, metadata = load_dataset(tmp_path / "rebuilt/osm")
    assert frame.iloc[0]["osm_id"] == 123
    assert metadata["area_scope"] == "region"
    assert len(calls) == count
    (output / "raw/ghsl.zip").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        study.rebuild_study(output, tmp_path / "corrupt-rebuild")
    assert not (tmp_path / "corrupt-rebuild").exists()


def test_resume_and_cache_do_not_redownload_and_refuse_changed_inputs(
    source_case, tmp_path, monkeypatch
):
    config, calls, download = source_case
    output, cache = tmp_path / "partial", tmp_path / "cache"
    interrupted = False

    def interrupt(target, request):
        nonlocal interrupted
        if target.name.startswith("osm-") and not interrupted:
            interrupted = True
            raise RuntimeError("Interrupted")
        return download(target, request)

    monkeypatch.setattr(study.PayloadStore, "_download", staticmethod(interrupt))
    with pytest.raises(RuntimeError, match="Interrupted"):
        study.acquire_study(config, output, download_cache=cache)
    assert not (output / study.MANIFEST).exists()
    changed = copy.deepcopy(config)
    changed["speed_m_s"] = 35
    with pytest.raises(ValueError, match="configuration"):
        study.acquire_study(changed, output, resume=True)
    study.acquire_study(config, output, resume=True, download_cache=cache)
    assert calls.count("ghsl.zip") == 1
    with pytest.raises(ValueError, match="Completed"):
        study.acquire_study(config, output, resume=True)
    monkeypatch.setattr(study.PayloadStore, "_download", lambda *a: pytest.fail("Cache not reused"))
    second = study.acquire_study(config, tmp_path / "second", download_cache=cache)
    assert second["files"][0]["cache_reused_at_utc"]


def test_overpass_error_never_marks_snapshot_complete(source_case, tmp_path, monkeypatch):
    config, _, download = source_case

    def incomplete(target, request):
        result = download(target, request)
        if target.name.startswith("osm-"):
            target.write_text('{"elements": [], "remark": "runtime error: timed out"}')
        return result

    monkeypatch.setattr(study.PayloadStore, "_download", staticmethod(incomplete))
    with pytest.raises(ValueError, match="incomplete"):
        study.acquire_study(config, tmp_path / "incomplete")
    assert not (tmp_path / "incomplete/study.json").exists()


def test_dipul_pagination_rejects_duplicate_and_unknown_counts(source_case, tmp_path, monkeypatch):
    config, _, download = source_case
    config["dipul_layers"] = ["dipul:krankenhaeuser"]

    def pages(target, request):
        result = download(target, request)
        if target.suffix == ".geojson":
            payload = read_json(target)
            payload["numberMatched"] = 2
            target.write_text(json.dumps(payload))
        return result

    monkeypatch.setattr(study.PayloadStore, "_download", staticmethod(pages))
    with pytest.raises(ValueError, match="duplicate"):
        study.acquire_study(config, tmp_path / "duplicates")
    assert not (tmp_path / "duplicates/study.json").exists()

    def unknown(target, request):
        result = download(target, request)
        if target.suffix == ".geojson":
            payload = read_json(target)
            payload["numberMatched"] = "unknown"
            target.write_text(json.dumps(payload))
        return result

    monkeypatch.setattr(study.PayloadStore, "_download", staticmethod(unknown))
    with pytest.raises(ValueError, match="unknown"):
        study.acquire_study(config, tmp_path / "unknown")


def test_ghsl_wrong_tile_coverage_is_rejected(source_case, tmp_path):
    config, _, _ = source_case
    store = study.PayloadStore(tmp_path / "source", config)
    archive = store.fetch("ghsl.zip", "https://test.invalid/population")
    wider = study.StudyRegion(10.5, 52.25, 10.55, 52.28)
    with pytest.raises(ValueError, match="does not cover"):
        study.derive_population(archive, tmp_path / "bad.tif", wider)
    assert not (tmp_path / "bad.tif").exists()


def test_failed_derivation_can_rebuild_offline_from_progress(source_case, tmp_path, monkeypatch):
    config, _, _ = source_case
    output = tmp_path / "failed-derivation"
    original = study.build_derived

    def fail(*args, **kwargs):
        raise RuntimeError("Interrupted derivation")

    monkeypatch.setattr(study, "build_derived", fail)
    with pytest.raises(RuntimeError, match="derivation"):
        study.acquire_study(config, output)
    assert not (output / study.MANIFEST).exists()
    monkeypatch.setattr(study, "build_derived", original)
    monkeypatch.setattr(study.requests, "request", lambda *a, **k: pytest.fail("Offline network"))
    result = study.rebuild_study(output, tmp_path / "recovered")
    assert result["sources"]["osm"]["feature_count"] == 1


def test_inspection_rejects_changed_scope_and_missing_layer(source_case, tmp_path):
    config, _, _ = source_case
    output = tmp_path / "snapshot"
    manifest = study.acquire_study(config, output)
    changed = copy.deepcopy(manifest)
    changed["files"][0]["path"] = "../outside"
    with pytest.raises(ValueError, match="outside"):
        study.verify_study(output, changed)
    changed = copy.deepcopy(manifest)
    changed["sources"]["dipul"]["responses"] = []
    with pytest.raises(ValueError, match="coverage"):
        study.verify_study(output, changed)
    changed = copy.deepcopy(manifest)
    receipt = next(r for r in changed["files"] if r["path"].startswith("raw/osm-"))
    receipt["request"]["data"]["data"] = "query for another region"
    with pytest.raises(ValueError, match="configured chunk"):
        study.verify_study(output, changed)


def test_bounded_transport_retry_records_actual_mirror_and_preserves_partial(tmp_path, monkeypatch):
    endpoints = []

    class Response:
        headers = {}

        def __init__(self, url, status):
            self.url, self.status_code = url, status

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self):
            if self.status_code != 200:
                raise requests.HTTPError(response=self)

        def iter_content(self, size):
            yield b'{"elements": []}'

    def request(method, endpoint, **kwargs):
        endpoints.append(endpoint)
        return Response(endpoint, 504 if endpoint == study.OVERPASS_PRIMARY else 200)

    monkeypatch.setattr(study.requests, "request", request)
    monkeypatch.setattr(study.time, "sleep", lambda _: None)
    target = tmp_path / "osm.json"
    receipt = study.PayloadStore._download(
        target,
        {
            "method": "POST",
            "url": study.OVERPASS_PRIMARY,
            "params": None,
            "data": {"data": "query"},
        },
    )
    assert endpoints == [study.OVERPASS_PRIMARY, study.OVERPASS_MIRROR]
    assert receipt["transfer_endpoint"] == study.OVERPASS_MIRROR
    assert receipt["attempts"] == 2
    assert target.read_bytes() == b'{"elements": []}'
    assert not target.with_suffix(".json.part").exists()


def test_interrupted_transfer_never_publishes_final_payload(tmp_path, monkeypatch):
    class Response:
        headers = {}
        status_code = 200
        url = "https://test.invalid"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self):
            pass

        def iter_content(self, size):
            yield b"partial"
            raise requests.ConnectionError("interrupted")

    monkeypatch.setattr(study.requests, "request", lambda *a, **k: Response())
    monkeypatch.setattr(study.time, "sleep", lambda _: None)
    target = tmp_path / "payload.json"
    with pytest.raises(RuntimeError, match="transfer failed"):
        study.PayloadStore._download(
            target, {"method": "GET", "url": "https://test.invalid", "params": None, "data": None}
        )
    assert not target.exists()
    assert target.with_suffix(".json.part").read_bytes() == b"partial"


def test_adaptive_subdivision_preserves_full_coverage_and_can_rebuild(
    source_case, tmp_path, monkeypatch
):
    config, _, download = source_case

    def overloaded(target, request):
        if target.name == "osm-000.json":
            raise RuntimeError("Source transfer failed: HTTPError, HTTP 504")
        return download(target, request)

    monkeypatch.setattr(study.PayloadStore, "_download", staticmethod(overloaded))
    output = tmp_path / "subdivided"
    manifest = study.acquire_study(config, output)
    assert manifest["osm_subdivisions"] == ["000"]
    assert len(manifest["osm_raw_paths"]) == 4
    leaves = study.osm_leaves(study.validate_study(config), config, ["000"])
    assert unary_union([box(*chunk.as_tuple()) for _, chunk in leaves]).equals(
        box(*study.validate_study(config).as_tuple())
    )
    assert manifest["sources"]["osm"]["feature_count"] == 1  # Duplicate IDs are merged.
    rebuilt = study.rebuild_study(output, tmp_path / "rebuilt")
    assert rebuilt["osm_subdivisions"] == ["000"]
    assert rebuilt["sources"]["osm"]["feature_count"] == 1


def test_gdal_osm_parser_retains_source_tags_and_way_identity(tmp_path):
    source = tmp_path / "source.osm"
    source.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="synthetic-test">
<node id="1" lat="52.2694" lon="10.5194"/>
<node id="2" lat="52.2694" lon="10.5204"/>
<node id="3" lat="52.2704" lon="10.5204"/>
<node id="4" lat="52.2704" lon="10.5194"/>
<way id="100"><nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
<tag k="building" v="hospital"/><tag k="height" v="18"/>
<tag k="building:levels" v="5"/><tag k="name" v="Test &quot;hospital&quot;"/>
<tag k="description" v="First&#10;Second"/></way>
<way id="101"><nd ref="1"/><nd ref="2"/><tag k="highway" v="service"/>
<tag k="surface" v="asphalt"/></way></osm>""",
        encoding="utf-8",
    )
    area = study.StudyRegion(10.519, 52.269, 10.522, 52.272)
    frame, _ = study.pbf_frame(source, area)
    building = frame.loc[frame["osm_id"] == 100].iloc[0]
    assert building["element_type"] == "way"
    assert building.geometry.equals(box(10.5194, 52.2694, 10.5204, 52.2704))
    tags = building["_source_tags"]
    assert tags["building"] == "hospital"
    assert tags["height"] == "18"
    assert tags["building:levels"] == "5"
    assert tags["name"] == 'Test "hospital"'
    assert tags["description"] == "First\nSecond"
    road = frame.loc[frame["osm_id"] == 101].iloc[0]
    assert road["_source_tags"]["highway"] == "service"
    assert road["_source_tags"]["surface"] == "asphalt"


def test_publisher_osm_workflow_checksum_coverage_and_offline_rebuild(
    source_case, tmp_path, monkeypatch
):
    config, _, download = source_case
    config.update(
        osm_format="geofabrik-pbf",
        osm_pbf_url="https://download.geofabrik.de/europe/germany/niedersachsen-261003.osm.pbf",
    )
    xml = b"""<?xml version="1.0"?><osm version="0.6" generator="synthetic-test">
<node id="1" lat="52.27" lon="10.52"><tag k="natural" v="tree"/></node></osm>"""

    def publisher(target, request):
        if target.name == "osm-source.osm.pbf":
            target.write_bytes(xml)  # GDAL supports XML and binary OSM through the same driver.
        elif target.name == "osm-source.md5":
            target.write_text(hashlib.md5(xml).hexdigest() + "  source.osm.pbf\n")
        elif target.name == "osm-source.poly":
            target.write_text(
                "extract\n1\n10.51 52.26\n10.53 52.26\n10.53 52.28\n"
                "10.51 52.28\n10.51 52.26\nEND\nEND\n"
            )
        else:
            return download(target, request)
        return {"retrieved_at_utc": "2026-10-05T00:00:00Z"}

    monkeypatch.setattr(study.PayloadStore, "_download", staticmethod(publisher))
    output = tmp_path / "publisher"
    result = study.acquire_study(config, output)
    assert result["sources"]["osm"]["source_format"] == "geofabrik-pbf"
    frame, metadata = load_dataset(output / "osm")
    assert frame.iloc[0]["natural"] == "tree"
    assert metadata["source"] == "OpenStreetMap via Geofabrik/GDAL"
    assert study.rebuild_study(output, tmp_path / "rebuilt")["sources"]["osm"]["feature_count"] == 1
    manifest = read_json(output / "study.json")
    changed = tmp_path / "bad-coverage.poly"
    changed.write_text("extract\n1\n9 52\n9.01 52\n9.01 52.01\n9 52.01\n9 52\nEND\nEND\n")
    assert not study.extract_polygon(changed).covers(box(*study.validate_study(config).as_tuple()))
    assert manifest["sources"]["osm"]["feature_count"] == 1
