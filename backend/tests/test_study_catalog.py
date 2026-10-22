"""Map metadata reads must not materialize or claim to verify regional payloads."""

import copy
import json
from pathlib import Path

from fastapi.testclient import TestClient

from uas_planner.acquisition import study
from uas_planner.api.app import create_app


def test_catalog_is_bounded_unverified_metadata_and_full_inspection_stays_default(
    tmp_path, monkeypatch
):
    config = json.loads(
        (Path(__file__).parents[2] / "doc/experiments/iteration-008/hannover-study.json").read_text(
            encoding="utf-8"
        )
    )
    directory = tmp_path / "regional"
    directory.mkdir()
    manifest = {
        "schema_version": 1,
        "kind": "regional-source-study",
        "config": config,
        "sources": {"osm": {"attribution": "Saved OSM", "responses": ["large payload"]}},
        "files": [{"path": "deliberately-absent-source", "sha256": "not-verified"}],
    }
    target = directory / "study.json"
    target.write_text(json.dumps(manifest), encoding="utf-8")
    calls = []

    def full(path):
        calls.append(path)
        raise ValueError("Full source verification failed")

    monkeypatch.setattr(study, "inspect_study", full)
    with TestClient(create_app(tmp_path)) as client:
        url = "/api/datasets/regional/study"
        response = client.get(url, params={"catalog_only": True})
        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is False
        assert data["verification_scope"] == "validated_catalog_metadata_only"
        assert data["config"] == {"bounds": config["bounds"], "locations": config["locations"]}
        assert data["sources"]["osm"] == {"attribution": "Saved OSM"}
        assert "files" not in data
        assert calls == []
        assert client.get(url).status_code == 422
        assert calls == [directory]
        assert client.get("/api/datasets/missing/study?catalog_only=true").status_code == 404
        for change in ("locations", "bounds", "oversized", "schema", "config", "sources"):
            invalid = copy.deepcopy(manifest)
            if change == "locations":
                invalid["config"]["locations"][0]["longitude"] = 0
            elif change == "bounds":
                invalid["config"]["bounds"]["west"] = 0
            elif change == "oversized":
                invalid["config"]["locations"] *= 65
            elif change == "schema":
                invalid["schema_version"] = 9
            else:
                invalid[change] = []
            target.write_text(json.dumps(invalid), encoding="utf-8")
            assert client.get(url, params={"catalog_only": True}).status_code == 422
        target.write_text(" " * (4 * 1024 * 1024 + 1), encoding="utf-8")
        assert client.get(url, params={"catalog_only": True}).status_code == 422
