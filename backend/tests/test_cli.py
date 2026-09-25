import json
from unittest.mock import patch

import geopandas as gpd
from shapely.geometry import Point

from uas_planner.cli import main


def test_fetch_then_inspect_without_network(tmp_path, capsys):
    frame = gpd.GeoDataFrame(
        {"element_type": ["node"], "osm_id": [123], "natural": ["tree"]},
        geometry=[Point(10.52, 52.27)],
        crs=4326,
    )
    destination = tmp_path / "sample"
    with patch("uas_planner.acquisition.osm.acquire", return_value=frame):
        assert (
            main(
                [
                    "fetch",
                    "--west",
                    "10.519",
                    "--south",
                    "52.269",
                    "--east",
                    "10.521",
                    "--north",
                    "52.271",
                    "--output",
                    str(destination),
                ]
            )
            == 0
        )
    first = json.loads(capsys.readouterr().out)
    with patch(
        "requests.sessions.Session.request", side_effect=AssertionError("Network prohibited")
    ):
        assert main(["inspect", str(destination)]) == 0
    second = json.loads(capsys.readouterr().out)
    assert first == second
    assert second["feature_count"] == 1


def test_invalid_bounds_fail_before_network(tmp_path, capsys):
    with patch("uas_planner.acquisition.osm.acquire") as acquire:
        assert (
            main(
                [
                    "fetch",
                    "--west",
                    "11",
                    "--south",
                    "52",
                    "--east",
                    "10",
                    "--north",
                    "53",
                    "--output",
                    str(tmp_path / "invalid"),
                ]
            )
            == 1
        )
        acquire.assert_not_called()
    assert "west < east" in capsys.readouterr().err


def test_existing_output_fails_before_network(tmp_path):
    with patch("uas_planner.acquisition.osm.acquire") as acquire:
        assert (
            main(
                [
                    "fetch",
                    "--west",
                    "10.519",
                    "--south",
                    "52.269",
                    "--east",
                    "10.521",
                    "--north",
                    "52.271",
                    "--output",
                    str(tmp_path),
                ]
            )
            == 1
        )
        acquire.assert_not_called()
