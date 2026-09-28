"""Isolated real API for Playwright; invoked only by the smoke-test configuration."""

from pathlib import Path
from tempfile import TemporaryDirectory

import geopandas as gpd
import uvicorn
from shapely.geometry import box

from uas_planner.api.app import create_app
from uas_planner.cli import main
from uas_planner.core.area import BoundingBox
from uas_planner.storage.dataset import save_dataset

if __name__ == "__main__":
    cache = Path(__file__).resolve().parents[2] / ".cache"
    cache.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="smoke-", dir=cache) as directory:
        root = Path(directory)
        if main(["sample", "--output", str(root / "offline-sample")]) != 0:
            raise SystemExit("Could not prepare the smoke sample")
        frame = gpd.GeoDataFrame(
            {
                "element_type": ["way"] * 7,
                "osm_id": list(range(100, 107)),
                "building": [
                    "house",
                    "school",
                    "unmapped_type",
                    "kindergarten",
                    "hut",
                    "yes",
                    "no",
                ],
                "landuse": ["industrial", None, None, None, None, None, "grass"],
                "name": [
                    "House",
                    "School",
                    "Unknown",
                    "Kindergarten",
                    "Hut",
                    "Generic",
                    "Not building",
                ],
                "amenity": [None, None, None, None, None, "school", None],
                "addr:street": ["<img src=x onerror=alert(1)>"] + [None] * 6,
            },
            geometry=[
                box(10.52 + i * 0.0002, 52.27, 10.52015 + i * 0.0002, 52.27015) for i in range(7)
            ],
            crs=4326,
        )
        save_dataset(
            frame,
            root / "z-cost-analysis",
            BoundingBox(10.519, 52.269, 10.522, 52.272),
            {},
            synthetic=True,
        )
        uvicorn.run(create_app(root), host="127.0.0.1", port=8011)
