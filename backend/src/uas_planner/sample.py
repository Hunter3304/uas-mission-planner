"""A fixed, synthetic three-feature example for network-free demonstrations."""

from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon

from uas_planner.core.area import BoundingBox
from uas_planner.storage.dataset import save_dataset


def create_sample(directory: Path):
    area = BoundingBox(10.519, 52.269, 10.522, 52.272)
    frame = gpd.GeoDataFrame(
        {
            "element_type": ["node", "way", "way"],
            "osm_id": [1, 2, 3],
            "name": ["Sample tree", "Sample path", "Sample building"],
            "natural": ["tree", None, None],
            "highway": [None, "footway", None],
            "building": [None, None, "yes"],
            "landuse": [None, None, "residential"],
        },
        geometry=[
            Point(10.5195, 52.2695),
            LineString([(10.52, 52.2695), (10.52, 52.2715)]),
            Polygon(
                [
                    (10.5205, 52.27),
                    (10.5215, 52.27),
                    (10.5215, 52.271),
                    (10.5205, 52.271),
                    (10.5205, 52.27),
                ]
            ),
        ],
        crs=4326,
    )
    return save_dataset(
        frame,
        directory,
        area,
        {"building": True, "highway": True, "landuse": True, "natural": True},
        synthetic=True,
    )
