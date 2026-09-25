import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from uas_planner.api.app import create_app
from uas_planner.cli import main
from uas_planner.storage.dataset import load_dataset


def test_offline_sample_roundtrip_and_api(tmp_path, capsys):
    destination = tmp_path / "sample"
    with patch(
        "requests.sessions.Session.request", side_effect=AssertionError("Network prohibited")
    ):
        assert main(["sample", "--output", str(destination)]) == 0
        created = json.loads(capsys.readouterr().out)
        assert main(["inspect", str(destination)]) == 0
        assert json.loads(capsys.readouterr().out) == created
        frame, metadata = load_dataset(destination)
        assert list(frame.geom_type) == ["Point", "LineString", "Polygon"]
        assert metadata["synthetic"] is True
        assert metadata["source"] == "Synthetic demonstration sample"
        original = (destination / "features.gpkg").read_bytes()
        assert main(["sample", "--output", str(destination)]) == 1
        assert (destination / "features.gpkg").read_bytes() == original
        client = TestClient(create_app(tmp_path))
        details = client.get("/api/datasets/sample").json()
        assert details["feature_count"] == 3
        assert details["synthetic"] is True
        assert details["layer_counts"] == {"building": 1, "highway": 1, "landuse": 1, "natural": 1}
        assert len(client.get("/api/datasets/sample/download/geojson").json()["features"]) == 3
        assert client.get("/api/datasets/sample/download/gpkg").content == original
