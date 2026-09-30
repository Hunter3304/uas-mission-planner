import shutil
import zipfile

import pytest
import requests
from experiment_fixture import create_experiment_fixture

from uas_planner.acquisition import external
from uas_planner.core.experiment import load_experiment, read_json, write_json


def test_bounded_acquisition_and_explicit_verified_resume(tmp_path, monkeypatch):
    source = tmp_path / "fixture"
    fixture = create_experiment_fixture(source)
    output = tmp_path / "acquired"
    calls = []
    fail_once = True

    def fake_download(url, path, params=None):
        nonlocal fail_once
        calls.append(path.name)
        if path.name == "dgm-capabilities.xml" and fail_once:
            fail_once = False
            raise RuntimeError("Simulated interrupted service")
        if path.name == "ghsl.zip":
            with zipfile.ZipFile(path, "w") as archive:
                archive.write(source / "ghsl.tif", "native.tif")
        elif path.name == "terrain.tif":
            assert dict(params)["coverageId"] == "ni_dgm1"
            assert len([v for k, v in params if k == "subset"]) == 2
            shutil.copyfile(source / "terrain.tif", path)
        elif path.name == "dipul-capabilities.xml":
            path.write_text(
                '<FeatureTypeList xmlns="http://www.opengis.net/wfs/2.0">'
                + "".join(f"<Name>dipul:{name}</Name>" for name in external.ZONE_TYPES)
                + "</FeatureTypeList>"
            )
        elif path.suffix == ".geojson":
            assert params["count"] == 10000
            assert params["bbox"].endswith("urn:ogc:def:crs:OGC:1.3:CRS84")
            shutil.copyfile(source / "zones.geojson", path)
        else:
            path.write_text("<metadata/>")
        return {
            "url": requests.Request("GET", url, params=params).prepare().url,
            "retrieved_at_utc": "2026-09-29T10:00:00Z",
        }

    monkeypatch.setattr(external, "download", fake_download)
    with pytest.raises(RuntimeError, match="interrupted"):
        external.acquire_experiment(fixture["config"], output)
    assert not (output / "experiment.json").exists()
    assert (output / "population.tif").exists()
    manifest = external.acquire_experiment(fixture["config"], output, resume=True)
    assert calls.count("ghsl.zip") == 1
    assert manifest == load_experiment(output)
    assert len(manifest["sources"]["dipul"]["responses"]) == 4
    with pytest.raises(FileExistsError):
        external.acquire_experiment(fixture["config"], output)


def test_resume_rejects_changed_config_or_bytes(tmp_path, monkeypatch):
    source = tmp_path / "fixture"
    fixture = create_experiment_fixture(source)
    path = tmp_path / "partial"
    path.mkdir()
    (path / "raw").mkdir()
    (path / "raw/source").write_text("corrupt")
    write_json(
        path / "acquisition-progress.json",
        {
            "config": fixture["config"],
            "files": [{"path": "raw/source", "sha256": "0" * 64}],
        },
    )
    monkeypatch.setattr(external, "download", lambda *a, **k: pytest.fail("Unexpected network"))
    with pytest.raises(ValueError, match="checksum"):
        external.acquire_experiment(fixture["config"], path, resume=True)
    progress = read_json(path / "acquisition-progress.json")
    progress["config"]["agl_m"] = 70
    write_json(path / "acquisition-progress.json", progress)
    with pytest.raises(ValueError, match="configuration"):
        external.acquire_experiment(fixture["config"], path, resume=True)
