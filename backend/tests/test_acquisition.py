from unittest.mock import patch

import geopandas as gpd
import pandas as pd
import pytest
from osmnx._errors import InsufficientResponseError
from requests.exceptions import Timeout
from shapely.geometry import Point

from uas_planner.acquisition.osm import TAGS, AcquisitionError, acquire
from uas_planner.core.area import BoundingBox


@pytest.mark.parametrize(
    "bounds",
    [
        (11, 52, 10, 53),
        (10, 53, 11, 52),
        (0, 0, 360, 1),
        (0, 86, 0.01, 87),
        (10, 52, float("nan"), 53),
        (10, 52, 10.5, 52.5),
        (0, 0, 0, 0),
    ],
)
def test_invalid_bounds(bounds):
    with pytest.raises(ValueError):
        BoundingBox(*bounds)


@pytest.mark.parametrize("names", [["element", "id"], ["element_type", "osmid"]])
def test_acquisition_preserves_identity_and_bbox_order(tmp_path, names):
    index = pd.MultiIndex.from_tuples([("node", 123)], names=names)
    fixture = gpd.GeoDataFrame(
        {"natural": ["tree"]}, geometry=[Point(10.52, 52.27)], index=index, crs=4326
    )
    area = BoundingBox(10.519, 52.269, 10.521, 52.271)
    with patch("uas_planner.acquisition.osm.ox.features_from_bbox", return_value=fixture) as fetch:
        result = acquire(area, tmp_path)
    fetch.assert_called_once_with((10.519, 52.269, 10.521, 52.271), tags=TAGS)
    assert result.loc[0, "osm_id"] == 123
    assert result.loc[0, "element_type"] == "node"
    assert result.loc[0, "natural"] == "tree"
    assert result.crs.to_epsg() == 4326


@pytest.mark.parametrize(
    "error", [Timeout("timed out"), InsufficientResponseError("No data elements")]
)
def test_network_and_malformed_response_are_not_empty_success(tmp_path, error):
    with patch("uas_planner.acquisition.osm.ox.features_from_bbox", side_effect=error):
        with pytest.raises(AcquisitionError):
            acquire(BoundingBox(10.519, 52.269, 10.521, 52.271), tmp_path)


def test_empty_matches_are_valid(tmp_path):
    with patch(
        "uas_planner.acquisition.osm.ox.features_from_bbox",
        side_effect=InsufficientResponseError("No matching features. Check query."),
    ):
        result = acquire(BoundingBox(10.519, 52.269, 10.521, 52.271), tmp_path)
    assert result.empty
    assert result.crs.to_epsg() == 4326
